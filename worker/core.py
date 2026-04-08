"""Worker Core - SmartCut Worker 主流程实现

实现 Worker 的生命周期管理、任务轮询和执行。
"""

import asyncio
import logging
import signal
import socket
from typing import Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from configs.database import check_database_connection, get_missing_tables
from apps.models.device import SmartCutDevice, DeviceStatus
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus, SchedulerTaskType
from apps.services.device_service import DeviceService
from worker.base_processor import BaseProcessor


logger = logging.getLogger(__name__)

# Worker 版本号
WORKER_VERSION = "1.0.0"
REQUIRED_WORKER_TABLES = (
    "scheduler_tasks",
    "smart_cut_devices",
    "smart_cut_tasks",
    "smart_cut_edits",
)


class SmartCutWorker:
    """Smart Cut Worker 主类
    
    负责任务：
    1. 向 A 端注册设备
    2. 定期发送心跳
    3. 轮询并执行分配的任务
    4. 状态管理和优雅退出
    
    Attributes:
        worker_id: Worker 唯一标识
        worker_name: Worker 显示名称
        supported_task_types: 支持的任务类型列表
        status: 当前状态
        current_task: 当前执行的任务
    """
    
    def __init__(
        self,
        worker_id: str,
        api_base_url: str,
        tos_service: Any,
        workspace: str,
        worker_name: Optional[str] = None,
        supported_task_types: Optional[list[str]] = None,
        db_url: Optional[str] = None,
        heartbeat_interval: float = 10.0,
        poll_interval: float = 5.0,
    ):
        """初始化 Worker
        
        Args:
            worker_id: Worker 唯一标识，如 "worker-001"
            api_base_url: A 端 API 基础 URL
            tos_service: TOS 服务对象，用于文件上传下载
            workspace: 工作目录路径
            db_url: 数据库 URL，默认使用内存数据库
            heartbeat_interval: 心跳间隔（秒），默认 10 秒
            poll_interval: 任务轮询间隔（秒），默认 5 秒
        """
        self.worker_id = worker_id
        self.api_base_url = api_base_url.rstrip('/')
        self.tos_service = tos_service
        self.workspace = workspace
        self.heartbeat_interval = heartbeat_interval
        self.poll_interval = poll_interval
        
        # 支持的任务类型
        self.supported_task_types = supported_task_types or [
            SchedulerTaskType.SMART_CUT_ANALYZE.value,
            SchedulerTaskType.SMART_CUT_PREVIEW.value,
            SchedulerTaskType.SMART_CUT_FINALIZE.value,
        ]
        
        # Worker 信息
        self.worker_name = worker_name or f"SmartCut Worker {worker_id}"
        self.worker_version = WORKER_VERSION
        self.hostname = socket.gethostname()
        
        # 数据库配置
        self._init_database(db_url)
        
        # 状态管理
        self._status = DeviceStatus.IDLE
        self._current_task: Optional[SchedulerTask] = None
        self._shutdown_event = asyncio.Event()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 处理器注册表
        self._processors: dict[str, Any] = {}
    
    def _init_database(self, db_url: Optional[str]) -> None:
        """初始化数据库连接
        
        Args:
            db_url: 共享调度数据库 URL，必须显式提供 PostgreSQL DSN
        """
        if not db_url:
            raise ValueError(
                "Worker gateway requires an explicit PostgreSQL DATABASE_URL"
            )
        if db_url.startswith("sqlite"):
            raise ValueError(
                "Worker gateway must use the shared PostgreSQL scheduler database; SQLite is not allowed on the formal runtime path"
            )

        engine_kwargs: dict[str, Any] = {}
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 3600

        self.engine = create_engine(db_url, **engine_kwargs)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        check_database_connection(self.engine)
        missing_tables = get_missing_tables(self.engine, REQUIRED_WORKER_TABLES)
        if missing_tables:
            raise RuntimeError(
                "Worker gateway database is missing required tables: "
                + ", ".join(missing_tables)
            )

        logger.info("Worker gateway database verified: %s", db_url)
    
    def _get_db(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    @property
    def status(self) -> DeviceStatus:
        """获取当前状态"""
        return self._status
    
    def register_processor(self, task_type: str, processor: Any) -> None:
        """注册任务处理器
        
        Args:
            task_type: 任务类型，如 "smart_cut_analyze"
            processor: 处理器实例
        """
        self._processors[task_type] = processor
        logger.info(f"Registered processor for {task_type}")
    
    def register(self) -> SmartCutDevice:
        """向 A 端注册设备
        
        调用 DeviceService.register_device 完成设备注册或更新。
        
        Returns:
            SmartCutDevice: 注册/更新后的设备对象
        """
        db = self._get_db()
        try:
            device_service = DeviceService(db)
            
            device = device_service.register_device(
                worker_id=self.worker_id,
                worker_name=self.worker_name,
                supported_task_types=self.supported_task_types,
                worker_version=self.worker_version,
                ip_address=self._get_ip_address(),
                hostname=self.hostname,
            )
            
            logger.info(f"Worker registered: {self.worker_id}")
            return device
            
        finally:
            db.close()
    
    def _get_ip_address(self) -> str:
        """获取本机 IP 地址"""
        try:
            # 尝试获取外网 IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    async def heartbeat_loop(self) -> None:
        """心跳循环（异步）
        
        定期上报 Worker 状态，直到收到关闭信号。
        """
        logger.info(f"Heartbeat loop started, interval: {self.heartbeat_interval}s")
        
        while not self._shutdown_event.is_set():
            try:
                self._send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
            
            # 等待下一次心跳或关闭信号
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.heartbeat_interval
                )
            except asyncio.TimeoutError:
                continue
        
        logger.info("Heartbeat loop stopped")
    
    def _send_heartbeat(self) -> Optional[SmartCutDevice]:
        """发送心跳
        
        Returns:
            SmartCutDevice: 更新后的设备对象
        """
        db = self._get_db()
        try:
            device_service = DeviceService(db)
            
            current_task_id = self._current_task.id if self._current_task else None
            
            device = device_service.heartbeat(
                worker_id=self.worker_id,
                status=self._status,
                current_task_id=current_task_id,
            )
            
            if device:
                logger.debug(f"Heartbeat sent: {self.worker_id}, status: {self._status.value}")
            
            return device
            
        finally:
            db.close()
    
    def find_assigned_task(self) -> Optional[SchedulerTask]:
        """查找分配给当前 Worker 的任务
        
        查询数据库中状态为 ASSIGNED 且 assigned_worker_id 匹配的任务。
        
        Returns:
            SchedulerTask: 分配的任务，如果没有则返回 None
        """
        db = self._get_db()
        try:
            from sqlalchemy import select, and_
            
            stmt = select(SchedulerTask).where(
                and_(
                    SchedulerTask.assigned_worker_id == self.worker_id,
                    SchedulerTask.status == SchedulerTaskStatus.ASSIGNED
                )
            )
            
            task = db.execute(stmt).scalar_one_or_none()
            
            if task:
                logger.info(f"Found assigned task: {task.id}, type: {task.task_type.value}")
            
            return task
            
        finally:
            db.close()
    
    async def execute_task(self, scheduler_task: SchedulerTask) -> bool:
        """执行调度任务
        
        流程：
        1. 更新设备状态为 running
        2. 根据 task_type 调用对应处理器
        3. 执行完成后更新设备状态为 post
        
        Args:
            scheduler_task: 调度任务对象
            
        Returns:
            bool: 是否执行成功
        """
        task_id = scheduler_task.id
        task_type = scheduler_task.task_type.value
        
        logger.info(f"Starting task execution: {task_id}, type: {task_type}")
        
        # 更新状态为 running
        self._update_status(DeviceStatus.RUNNING, scheduler_task)
        
        try:
            # 标记任务为执行中
            self._mark_task_running(scheduler_task)
            
            # 获取处理器
            processor = self._get_processor(task_type)
            if processor is None:
                raise RuntimeError(f"No processor found for task type: {task_type}")
            
            # 设置任务和回调
            processor.set_task(scheduler_task)
            processor.set_progress_callback(
                lambda p: self._on_progress_update(scheduler_task, p)
            )
            
            # 执行任务 (processor.process 是 async 方法)
            result = await processor.process(scheduler_task, self.workspace)
            
            # 标记任务完成
            self._mark_task_completed(scheduler_task, result)
            
            # 更新状态为 post
            self._update_status(DeviceStatus.POST, scheduler_task)
            
            logger.info(f"Task completed successfully: {task_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Task execution failed: {task_id}, error: {e}")
            self._mark_task_failed(scheduler_task, str(e))
            self._update_status(DeviceStatus.IDLE)
            return False
            
        finally:
            self._current_task = None
    
    def _get_processor(self, task_type: str) -> Optional[Any]:
        """获取任务处理器
        
        Args:
            task_type: 任务类型
            
        Returns:
            BaseProcessor: 处理器实例，未找到返回 None
        """
        # 先从注册表查找
        if task_type in self._processors:
            return self._processors[task_type]
        
        # 没有注册处理器，返回 None
        return None
    
    def _update_status(
        self,
        status: DeviceStatus,
        task: Optional[SchedulerTask] = None
    ) -> None:
        """更新 Worker 状态
        
        Args:
            status: 新状态
            task: 当前任务（可选）
        """
        self._status = status
        
        db = self._get_db()
        try:
            device_service = DeviceService(db)
            device_service.update_device_status(
                worker_id=self.worker_id,
                status=status,
                current_task_id=task.id if task else None
            )
            logger.info(f"Worker status updated: {status.value}")
        finally:
            db.close()
    
    def _mark_task_running(self, task: SchedulerTask) -> None:
        """标记任务为执行中"""
        db = self._get_db()
        try:
            task_db = db.query(SchedulerTask).filter_by(id=task.id).first()
            if task_db:
                task_db.mark_running()
                db.commit()
        finally:
            db.close()
    
    def _mark_task_completed(
        self,
        task: SchedulerTask,
        result: dict[str, Any]
    ) -> None:
        """标记任务为完成"""
        db = self._get_db()
        try:
            task_db = db.query(SchedulerTask).filter_by(id=task.id).first()
            if task_db:
                task_db.mark_completed(result)
                db.commit()
        finally:
            db.close()
    
    def _mark_task_failed(self, task: SchedulerTask, error_message: str) -> None:
        """标记任务为失败"""
        db = self._get_db()
        try:
            task_db = db.query(SchedulerTask).filter_by(id=task.id).first()
            if task_db:
                task_db.mark_failed(error_message)
                db.commit()
        finally:
            db.close()
    
    def _on_progress_update(self, task: SchedulerTask, progress: float) -> None:
        """进度更新回调
        
        Args:
            task: 当前任务
            progress: 进度值 (0.0 - 1.0)
        """
        logger.info(f"Task {task.id} progress: {progress * 100:.1f}%")
        # TODO: 可以通过 API 上报进度到 A 端
    
    async def run(self) -> None:
        """主循环
        
        流程：
        1. 注册设备
        2. 启动心跳循环
        3. 轮询任务并执行
        4. 处理优雅退出
        """
        logger.info(f"Starting SmartCut Worker: {self.worker_id}")
        
        # 注册设备
        try:
            self.register()
        except Exception as e:
            logger.error(f"Failed to register worker: {e}")
            return
        
        self._running = True
        
        # 启动心跳循环
        self._heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        
        # 设置信号处理
        self._setup_signal_handlers()
        
        logger.info("Worker main loop started")
        
        try:
            while self._running and not self._shutdown_event.is_set():
                # 查找分配的任务
                task = self.find_assigned_task()
                
                if task:
                    # 执行任务
                    self._current_task = task
                    await self.execute_task(task)
                else:
                    # 没有任务，等待轮询间隔
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.poll_interval
                        )
                    except asyncio.TimeoutError:
                        continue
                        
        except asyncio.CancelledError:
            logger.info("Worker main loop cancelled")
        except Exception as e:
            logger.exception(f"Worker main loop error: {e}")
        finally:
            await self.shutdown()
    
    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._signal_handler)
        except NotImplementedError:
            # Windows 不支持 add_signal_handler
            signal.signal(signal.SIGINT, self._sync_signal_handler)
            signal.signal(signal.SIGTERM, self._sync_signal_handler)
    
    def _signal_handler(self) -> None:
        """异步信号处理器"""
        logger.info("Received shutdown signal")
        self._shutdown_event.set()
        self._running = False

    def request_shutdown(self) -> None:
        """公开的关闭入口，供 runtime 包装层或测试触发。"""
        self._signal_handler()
    
    def _sync_signal_handler(self, signum, frame) -> None:
        """同步信号处理器（Windows 兼容）"""
        self._signal_handler()
    
    async def shutdown(self) -> None:
        """优雅关闭
        
        1. 停止心跳循环
        2. 更新设备状态为 offline
        3. 清理资源
        """
        logger.info("Shutting down worker...")
        
        # 设置关闭标志
        self._shutdown_event.set()
        self._running = False
        
        # 等待心跳循环结束
        if self._heartbeat_task and not self._heartbeat_task.done():
            try:
                await asyncio.wait_for(self._heartbeat_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
        
        # 更新设备状态为 offline
        try:
            db = self._get_db()
            device_service = DeviceService(db)
            device_service.update_device_status(
                worker_id=self.worker_id,
                status=DeviceStatus.OFFLINE
            )
            db.close()
            logger.info("Worker status set to offline")
        except Exception as e:
            logger.error(f"Failed to update offline status: {e}")
        
        logger.info("Worker shutdown complete")


async def main() -> int:
    """兼容旧入口，委托给正式 runtime 模块。"""
    from worker.main import run_from_cli

    return await run_from_cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
