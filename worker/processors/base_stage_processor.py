"""Base Stage Processor - 阶段处理器基类

提供 async/await 风格的阶段处理器接口
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import logging

from apps.models.scheduler_task import SchedulerTask
from worker.services import GatewayFileTransport, SmartCutJobContract


logger = logging.getLogger(__name__)


class BaseStageProcessor(ABC):
    """阶段处理器基类
    
    所有具体的阶段处理器（analyze、preview、finalize）都需要继承此类，
    并实现三个核心 async 方法：
    - prepare_input: 准备输入文件
    - execute: 执行核心算法
    - upload_output: 上传产物并更新数据库
    """
    
    # TOS bucket 名称
    BUCKET = "smart-cut"
    
    def __init__(self, tos_service: Any, workspace: str):
        """初始化处理器
        
        Args:
            tos_service: TOS 服务对象，用于文件上传下载
            workspace: 工作目录路径
        """
        self.tos_service = tos_service
        self.workspace = workspace
        self._current_task: Optional[SchedulerTask] = None
        self._progress_callback: Optional[callable] = None
        self._work_dir: Optional[Any] = None
        self._task_id: Optional[str] = None
        self.file_transport = GatewayFileTransport(
            tos_service=tos_service,
            workspace=workspace,
            bucket=self.BUCKET,
        )
        self.job_contract = SmartCutJobContract(workspace=workspace)
    
    def set_task(self, task: SchedulerTask) -> None:
        """设置当前任务
        
        Args:
            task: 调度任务对象
        """
        self._current_task = task
        self._task_id = task.business_task_id
    
    def set_progress_callback(self, callback: callable) -> None:
        """设置进度回调函数
        
        Args:
            callback: 进度回调函数，接收 progress: float 参数
        """
        self._progress_callback = callback
    
    def set_work_dir(self, work_dir: Any) -> None:
        """设置工作目录
        
        Args:
            work_dir: 工作目录路径 (Path 对象)
        """
        self._work_dir = work_dir
    
    def update_progress(self, progress: float) -> None:
        """更新任务进度
        
        Args:
            progress: 进度值 (0.0 - 1.0)
        """
        progress = max(0.0, min(1.0, progress))
        logger.debug(f"Task progress: {progress * 100:.1f}%")
        
        if self._progress_callback:
            try:
                self._progress_callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    @abstractmethod
    async def prepare_input(self) -> None:
        """准备输入文件
        
        从 scheduler_task.payload 获取 tos_keys，
        使用 tos_service.download_file 下载到 work_dir/input/
        
        Raises:
            ValueError: 缺少必要的输入参数
            RuntimeError: 下载失败
        """
        pass
    
    @abstractmethod
    async def execute(self) -> dict:
        """执行核心算法
        
        调用算法脚本，解析产物文件
        
        Returns:
            dict: 产物信息，包含解析后的数据
            
        Raises:
            RuntimeError: 算法执行失败
        """
        pass
    
    @abstractmethod
    async def upload_output(self, result: dict) -> None:
        """上传产物并更新数据库
        
        上传产物到 TOS，更新 SmartCutTask 和 SmartCutEdit 记录
        
        Args:
            result: execute 方法返回的产物信息
            
        Raises:
            RuntimeError: 上传失败
        """
        pass
    
    async def process(self, task: SchedulerTask, workspace: str) -> dict[str, Any]:
        """处理任务 - 主入口
        
        按顺序调用 prepare_input -> execute -> upload_output
        
        Args:
            task: 调度任务对象
            workspace: 工作目录路径
            
        Returns:
            dict: 处理结果
            
        Raises:
            Exception: 处理失败时抛出异常
        """
        from pathlib import Path
        
        self.set_task(task)
        work_dir = Path(workspace) / task.business_task_id
        work_dir.mkdir(parents=True, exist_ok=True)
        self.set_work_dir(work_dir)
        
        logger.info(f"Processing task: {task.id}, business_task: {task.business_task_id}")
        
        try:
            # Phase 1: 准备输入
            self.update_progress(0.1)
            await self.prepare_input()
            logger.info("Input prepared")
            
            # Phase 2: 执行算法
            self.update_progress(0.3)
            result = await self.execute()
            logger.info("Algorithm execution completed")
            
            # Phase 3: 上传产物
            self.update_progress(0.8)
            await self.upload_output(result)
            logger.info("Output uploaded")
            
            self.update_progress(1.0)
            
            return {
                "status": "success",
                **result
            }
            
        except Exception as e:
            logger.exception(f"Task failed: {task.id}, error: {e}")
            await self._handle_failure(str(e))
            raise
    
    async def _handle_failure(self, error_message: str) -> None:
        """处理失败情况 - 子类可以重写
        
        Args:
            error_message: 错误信息
        """
        logger.error(f"Task failed: {error_message}")
    
    def _download_from_tos(self, key: str, local_path: Any) -> None:
        """从 TOS 下载文件
        
        Args:
            key: TOS 对象 key
            local_path: 本地保存路径 (Path 对象)
        """
        self.file_transport.download_input_sync(key, local_path)
    
    def _upload_to_tos(self, local_path: Any, key: str) -> None:
        """上传文件到 TOS
        
        Args:
            local_path: 本地文件路径 (Path 对象)
            key: TOS 对象 key
        """
        self.file_transport.upload_output_sync(local_path, key)
