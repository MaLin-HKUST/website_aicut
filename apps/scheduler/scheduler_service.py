"""Scheduler Service - 调度器核心服务

实现 FCFS (First-Come-First-Served) 调度策略，负责任务分配、
状态机推进、超时处理和心跳检测等功能。
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Any

from sqlalchemy import select, and_, asc
from sqlalchemy.orm import Session

from apps.models.scheduler_task import (
    SchedulerTask,
    SchedulerTaskType,
    SchedulerTaskStatus,
)
from apps.models.task import SmartCutTask, TaskStatus, CurrentStage
from apps.models.device import SmartCutDevice, DeviceStatus
from apps.models.edit import SmartCutEdit, EditStatus
from apps.models.task_run import SmartCutTaskRun, TaskRunStatus, TaskRunType
from apps.services.device_service import DeviceService

logger = logging.getLogger(__name__)


def _task_type_to_run_type(task_type: SchedulerTaskType) -> TaskRunType:
    mapping = {
        SchedulerTaskType.SMART_CUT_ANALYZE: TaskRunType.ANALYZE,
        SchedulerTaskType.SMART_CUT_PREVIEW: TaskRunType.PREVIEW,
        SchedulerTaskType.SMART_CUT_FINALIZE: TaskRunType.FINALIZE,
    }
    return mapping[task_type]


class SchedulerService:
    """调度器服务类
    
    实现任务调度、状态管理和 Worker 管理的核心逻辑。
    使用 FCFS 策略进行任务分配。
    """
    
    def __init__(
        self,
        db_session: Session,
        device_service: DeviceService,
        check_interval: int = 5,
    ):
        """初始化调度器服务
        
        Args:
            db_session: SQLAlchemy 数据库会话
            device_service: 设备管理服务实例
            check_interval: 调度循环检查间隔（秒），默认 5 秒
        """
        self.db = db_session
        self.device_service = device_service
        self.check_interval = check_interval
        self.worker_timeout_seconds = int(os.environ.get("SCHEDULER_WORKER_TIMEOUT_SECONDS", "300"))
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def run_cycle(self) -> dict[str, int]:
        """执行单次调度循环。

        Returns:
            各步骤处理结果统计
        """
        reconciled_count = self.reconcile_orphaned_business_tasks()
        assigned_count = self.schedule_pending_tasks()
        advanced_count = self.check_device_status_and_advance()
        timeout_count = self.handle_timeouts()
        offline_count = self.check_worker_heartbeats(timeout_seconds=self.worker_timeout_seconds)

        cycle_stats = {
            "reconciled": reconciled_count,
            "assigned": assigned_count,
            "advanced": advanced_count,
            "timeouts": timeout_count,
            "offline_workers": offline_count,
        }
        logger.debug("Scheduler cycle stats: %s", cycle_stats)
        return cycle_stats
    
    async def run_scheduler_loop(self) -> None:
        """运行调度主循环（异步，可停止）
        
        持续执行以下操作：
        1. 分配待处理任务给空闲 Worker
        2. 检查设备状态并推进业务任务状态机
        3. 检测并处理超时任务
        4. 检查 Worker 心跳超时
        """
        self._running = True
        logger.info(f"Scheduler loop started with {self.check_interval}s interval")
        
        while self._running:
            try:
                self.run_cycle()
                
            except Exception as e:
                logger.exception(f"Error in scheduler loop: {e}")
            
            # 等待下一次检查
            await asyncio.sleep(self.check_interval)
        
        logger.info("Scheduler loop stopped")

    def reconcile_orphaned_business_tasks(self) -> int:
        """回收没有可执行调度真相的业务任务。

        处理典型 ghost task：
        - 业务任务显示为 analyzing / previewing / finalizing
        - 但没有对应的 pending/assigned/running/post scheduler_task
        """
        count = 0
        active_statuses = {TaskStatus.ANALYZING, TaskStatus.PREVIEWING, TaskStatus.FINALIZING}
        tasks = list(
            self.db.execute(
                select(SmartCutTask).where(SmartCutTask.status.in_(active_statuses))
            ).scalars().all()
        )

        for task in tasks:
            scheduler_tasks = list(
                self.db.execute(
                    select(SchedulerTask).where(SchedulerTask.business_task_id == task.id)
                ).scalars().all()
            )
            active_scheduler = any(
                scheduler_task.status in {
                    SchedulerTaskStatus.PENDING,
                    SchedulerTaskStatus.ASSIGNED,
                    SchedulerTaskStatus.RUNNING,
                    SchedulerTaskStatus.POST,
                }
                for scheduler_task in scheduler_tasks
            )
            if active_scheduler:
                continue

            if task.status == TaskStatus.ANALYZING:
                if task.analyze_script or task.active_edit_id:
                    task.status = TaskStatus.WAITING_USER
                    task.current_stage = CurrentStage.USER_SELECT
                else:
                    task.status = TaskStatus.WAITING_UPLOAD
                    task.current_stage = CurrentStage.UPLOAD
                task.failed_stage = "analyze"
            elif task.status in {TaskStatus.PREVIEWING, TaskStatus.FINALIZING}:
                failed_stage = "preview" if task.status == TaskStatus.PREVIEWING else "finalize"
                task.status = TaskStatus.WAITING_USER
                task.current_stage = CurrentStage.USER_SELECT
                task.failed_stage = failed_stage

            task.current_run_id = None
            task.updated_at = datetime.utcnow()
            count += 1

        if count:
            self.db.commit()
            logger.warning("Reconciled %s orphaned business tasks", count)

        return count
    
    def stop(self) -> None:
        """停止调度循环
        
        设置停止标志，调度循环将在下一次迭代时退出。
        """
        self._running = False
        logger.info("Scheduler stop requested")
    
    def schedule_pending_tasks(self) -> int:
        """FCFS 调度策略 - 分配待处理任务给空闲 Worker
        
        查询 status=pending 的调度任务，按 created_at 排序（FCFS），
        查找 status=idle 且在线的 Worker，进行能力匹配后分配任务。
        
        Returns:
            成功分配的任务数量
        """
        assigned_count = 0
        
        # 查询所有 pending 状态的调度任务，按创建时间升序（FCFS）
        stmt = (
            select(SchedulerTask)
            .where(SchedulerTask.status == SchedulerTaskStatus.PENDING)
            .order_by(asc(SchedulerTask.created_at))
        )
        pending_tasks = list(self.db.execute(stmt).scalars().all())
        
        if not pending_tasks:
            return 0
        
        # 查询所有 idle 状态的 Worker（已包含在线检查）
        stmt = (
            select(SmartCutDevice)
            .where(
                and_(
                    SmartCutDevice.status == DeviceStatus.IDLE,
                    SmartCutDevice.heartbeat_at.isnot(None)
                )
            )
        )
        idle_workers = list(self.db.execute(stmt).scalars().all())
        
        if not idle_workers:
            logger.debug("No idle workers available")
            return 0
        
        # 为每个待处理任务尝试分配 Worker
        for scheduler_task in pending_tasks:
            task_type = scheduler_task.task_type.value
            
            # 查找支持该任务类型的 Worker
            compatible_workers = [
                w for w in idle_workers
                if w.can_handle(task_type)
            ]
            
            if not compatible_workers:
                logger.debug(
                    f"No compatible worker for task {scheduler_task.id} "
                    f"(type: {task_type})"
                )
                continue
            
            # FCFS: 选择第一个兼容的 Worker（最早心跳的优先）
            worker = compatible_workers[0]
            
            # 分配任务给 Worker
            self._assign_task_to_worker(scheduler_task, worker)
            assigned_count += 1
            
            # 从可用 Worker 列表中移除已分配的 Worker
            idle_workers.remove(worker)
            
            if not idle_workers:
                break
        
        if assigned_count > 0:
            logger.info(f"Assigned {assigned_count} tasks to workers")
        
        return assigned_count
    
    def _assign_task_to_worker(
        self,
        scheduler_task: SchedulerTask,
        worker: SmartCutDevice
    ) -> None:
        """将调度任务分配给 Worker 并更新业务任务状态
        
        Args:
            scheduler_task: 调度任务对象
            worker: Worker 设备对象
        """
        # 更新调度任务状态
        scheduler_task.assign_to_worker(worker.worker_id)
        
        # 更新 Worker 状态
        worker.status = DeviceStatus.IDLE  # 保持 idle，等待 Worker 领取
        worker.current_task_id = scheduler_task.id
        worker.updated_at = datetime.utcnow()
        
        # 根据任务类型更新业务任务状态
        business_task = scheduler_task.business_task
        if business_task:
            self._update_business_task_on_assign(business_task, scheduler_task.task_type)
            run = self._get_or_create_run_for_scheduler_task(business_task.id, scheduler_task)
            if run:
                run.status = TaskRunStatus.QUEUED
                run.scheduler_task_id = scheduler_task.id
                run.updated_at = datetime.utcnow()
                business_task.current_run_id = run.id

        self.db.commit()
        self.db.refresh(scheduler_task)
        self.db.refresh(worker)
        
        logger.info(
            f"Task {scheduler_task.id} assigned to worker {worker.worker_id}"
        )
    
    def _update_business_task_on_assign(
        self,
        business_task: SmartCutTask,
        task_type: SchedulerTaskType
    ) -> None:
        """根据调度任务类型更新业务任务状态
        
        Args:
            business_task: 业务任务对象
            task_type: 调度任务类型
        """
        if task_type == SchedulerTaskType.SMART_CUT_ANALYZE:
            if business_task.status == TaskStatus.READY_ANALYZE:
                business_task.status = TaskStatus.ANALYZING
                business_task.current_stage = CurrentStage.ANALYZE
        
        elif task_type == SchedulerTaskType.SMART_CUT_PREVIEW:
            if business_task.status == TaskStatus.WAITING_USER:
                business_task.status = TaskStatus.PREVIEWING
                business_task.current_stage = CurrentStage.PREVIEW
        
        elif task_type == SchedulerTaskType.SMART_CUT_FINALIZE:
            if business_task.status in (TaskStatus.WAITING_USER, TaskStatus.PREVIEWING):
                business_task.status = TaskStatus.FINALIZING
                business_task.current_stage = CurrentStage.FINALIZE
        
        business_task.updated_at = datetime.utcnow()
    
    def check_device_status_and_advance(self) -> int:
        """状态机推进 - 检查 Worker 状态并推进业务任务
        
        - Worker running -> 调度任务 running，业务任务推进到相应 running 状态
        - Worker post -> 根据任务类型推进业务任务到终态或 waiting_user
        
        Returns:
            成功推进的任务数量
        """
        advanced_count = 0
        
        # 查询 running 状态的 Worker
        stmt = select(SmartCutDevice).where(SmartCutDevice.status == DeviceStatus.RUNNING)
        running_workers = list(self.db.execute(stmt).scalars().all())
        
        for worker in running_workers:
            if worker.current_task_id:
                # 查询调度任务
                scheduler_task = self.db.execute(
                    select(SchedulerTask).where(SchedulerTask.id == worker.current_task_id)
                ).scalar_one_or_none()
                
                if scheduler_task and scheduler_task.status == SchedulerTaskStatus.ASSIGNED:
                    # Worker 开始执行，更新调度任务状态
                    scheduler_task.mark_running()
                    run = self._get_or_create_run_for_scheduler_task(scheduler_task.business_task_id, scheduler_task)
                    if run:
                        run.status = TaskRunStatus.RUNNING
                        run.started_at = run.started_at or datetime.utcnow()
                        run.updated_at = datetime.utcnow()
                    self.db.commit()
                    advanced_count += 1
                    logger.info(f"Task {scheduler_task.id} is now running")
        
        # 查询 post 状态的 Worker
        stmt = select(SmartCutDevice).where(SmartCutDevice.status == DeviceStatus.POST)
        post_workers = list(self.db.execute(stmt).scalars().all())
        
        for worker in post_workers:
            if worker.current_task_id:
                # 查询调度任务
                scheduler_task = self.db.execute(
                    select(SchedulerTask).where(SchedulerTask.id == worker.current_task_id)
                ).scalar_one_or_none()
                
                if scheduler_task and scheduler_task.status == SchedulerTaskStatus.RUNNING:
                    # Worker 执行完成，推进业务任务状态机
                    self._advance_business_task_on_post(scheduler_task, worker)
                    advanced_count += 1
        
        return advanced_count
    
    def _advance_business_task_on_post(
        self,
        scheduler_task: SchedulerTask,
        worker: SmartCutDevice
    ) -> None:
        """Worker 进入 post 状态时推进业务任务状态机
        
        Args:
            scheduler_task: 调度任务对象
            worker: Worker 设备对象
        """
        # 显式查询业务任务
        business_task = self.db.execute(
            select(SmartCutTask).where(SmartCutTask.id == scheduler_task.business_task_id)
        ).scalar_one_or_none()
        
        if not business_task:
            return
        
        task_type = scheduler_task.task_type
        
        if task_type == SchedulerTaskType.SMART_CUT_ANALYZE:
            # analyze 完成 -> waiting_user
            business_task.status = TaskStatus.WAITING_USER
            business_task.current_stage = CurrentStage.USER_SELECT
            
            # 如果有 analyze 结果，更新到业务任务
            if scheduler_task.result:
                if "script" in scheduler_task.result:
                    business_task.analyze_script = scheduler_task.result["script"]
                if "asr_result_tos_key" in scheduler_task.result:
                    business_task.asr_result_tos_key = scheduler_task.result["asr_result_tos_key"]
        
        elif task_type == SchedulerTaskType.SMART_CUT_PREVIEW:
            # preview 完成 -> waiting_user，更新 active_edit_id
            business_task.status = TaskStatus.WAITING_USER
            business_task.current_stage = CurrentStage.USER_SELECT
            
            # 从 payload 中获取 edit_id 更新到业务任务
            if scheduler_task.payload and "edit_id" in scheduler_task.payload:
                business_task.active_edit_id = scheduler_task.payload["edit_id"]
            
            # 更新 Edit 记录状态为 success
            if scheduler_task.payload and "edit_id" in scheduler_task.payload:
                edit_id = scheduler_task.payload["edit_id"]
                edit = self.db.execute(
                    select(SmartCutEdit).where(SmartCutEdit.id == edit_id)
                ).scalar_one_or_none()
                if edit:
                    edit.status = EditStatus.SUCCESS
                    if scheduler_task.result:
                        if "audio_b_url" in scheduler_task.result:
                            edit.audio_b_url = scheduler_task.result["audio_b_url"]
                        if "edited_delay_cuts_tos_key" in scheduler_task.result:
                            edit.delay_cuts_tos_key = scheduler_task.result["edited_delay_cuts_tos_key"]
                        elif "delay_cuts_tos_key" in scheduler_task.result:
                            edit.delay_cuts_tos_key = scheduler_task.result["delay_cuts_tos_key"]
                        if "pause_cuts_tos_key" in scheduler_task.result:
                            edit.pause_cuts_tos_key = scheduler_task.result["pause_cuts_tos_key"]
        
        elif task_type == SchedulerTaskType.SMART_CUT_FINALIZE:
            # finalize 完成 -> success
            business_task.status = TaskStatus.SUCCESS
            business_task.current_stage = CurrentStage.COMPLETE
            
            # 如果有 finalize 结果，更新到业务任务
            if scheduler_task.result:
                if "final_video_url" in scheduler_task.result:
                    business_task.final_video_url = scheduler_task.result["final_video_url"]
                if "groundtruth_url" in scheduler_task.result:
                    business_task.groundtruth_url = scheduler_task.result["groundtruth_url"]
                    business_task.groundtruth_upload_status = "completed"
        
        business_task.updated_at = datetime.utcnow()
        run = self._get_or_create_run_for_scheduler_task(business_task.id, scheduler_task)
        if run:
            run.status = TaskRunStatus.SUCCESS
            run.result_snapshot = scheduler_task.result
            run.completed_at = datetime.utcnow()
            run.updated_at = datetime.utcnow()
            business_task.latest_successful_run_id = run.id
            business_task.current_run_id = None
        if task_type == SchedulerTaskType.SMART_CUT_ANALYZE:
            latest_edit = (
                self.db.query(SmartCutEdit)
                .filter(SmartCutEdit.task_id == business_task.id)
                .order_by(SmartCutEdit.version_number.desc())
                .first()
            )
            if latest_edit:
                business_task.active_edit_id = latest_edit.id
        
        # 更新调度任务状态为 success
        scheduler_task.mark_completed(scheduler_task.result)
        
        # 释放 Worker
        worker.status = DeviceStatus.IDLE
        worker.current_task_id = None
        worker.updated_at = datetime.utcnow()
        
        self.db.commit()
        logger.info(
            f"Task {scheduler_task.id} completed, business task {business_task.id} "
            f"advanced to {business_task.status.value}"
        )
    
    def handle_timeouts(self, timeout_hours: int = 72) -> int:
        """超时处理 - 标记运行超过指定时间的任务为超时
        
        Args:
            timeout_hours: 超时时间（小时），默认 72 小时
            
        Returns:
            标记为超时的任务数量
        """
        timeout_count = 0
        cutoff_time = datetime.utcnow() - timedelta(hours=timeout_hours)
        
        # 查找运行超过指定时间的任务
        stmt = select(SchedulerTask).where(
            and_(
                SchedulerTask.status.in_([
                    SchedulerTaskStatus.ASSIGNED,
                    SchedulerTaskStatus.RUNNING
                ]),
                SchedulerTask.started_at < cutoff_time
            )
        )
        timeout_tasks = list(self.db.execute(stmt).scalars().all())
        
        for scheduler_task in timeout_tasks:
            # 标记调度任务为超时
            scheduler_task.mark_timeout()
            
            # 显式查询业务任务并更新状态为失败
            business_task = self.db.execute(
                select(SmartCutTask).where(SmartCutTask.id == scheduler_task.business_task_id)
            ).scalar_one_or_none()
            if business_task:
                self._mark_business_task_failed_by_timeout(
                    business_task, scheduler_task.task_type
                )
            
            # 释放 Worker
            if scheduler_task.assigned_worker_id:
                worker = self.db.execute(
                    select(SmartCutDevice).where(
                        SmartCutDevice.worker_id == scheduler_task.assigned_worker_id
                    )
                ).scalar_one_or_none()
                if worker:
                    worker.status = DeviceStatus.IDLE
                    worker.current_task_id = None
                    worker.updated_at = datetime.utcnow()
            
            timeout_count += 1
            logger.warning(f"Task {scheduler_task.id} marked as timeout")
        
        if timeout_count > 0:
            self.db.commit()
            logger.info(f"Marked {timeout_count} tasks as timeout")
        
        return timeout_count
    
    def _mark_business_task_failed_by_timeout(
        self,
        business_task: SmartCutTask,
        task_type: SchedulerTaskType
    ) -> None:
        """根据任务类型标记业务任务为失败
        
        Args:
            business_task: 业务任务对象
            task_type: 调度任务类型
        """
        if task_type == SchedulerTaskType.SMART_CUT_ANALYZE:
            business_task.status = TaskStatus.ANALYZE_FAILED
            business_task.current_stage = CurrentStage.ANALYZE
        elif task_type == SchedulerTaskType.SMART_CUT_PREVIEW:
            business_task.status = TaskStatus.WAITING_USER
            business_task.current_stage = CurrentStage.USER_SELECT
        elif task_type == SchedulerTaskType.SMART_CUT_FINALIZE:
            business_task.status = TaskStatus.WAITING_USER
            business_task.current_stage = CurrentStage.USER_SELECT
        
        business_task.failed_stage = _task_type_to_run_type(task_type).value
        run = (
            self.db.query(SmartCutTaskRun)
            .filter(SmartCutTaskRun.scheduler_task_id == scheduler_task.id)
            .order_by(SmartCutTaskRun.sequence_number.desc())
            .first()
        )
        if run:
            run.status = TaskRunStatus.FAILED
            run.error_message = scheduler_task.error_message
            run.completed_at = datetime.utcnow()
            run.updated_at = datetime.utcnow()
        business_task.current_run_id = None
        business_task.updated_at = datetime.utcnow()

    def _get_or_create_run_for_scheduler_task(
        self,
        business_task_id: str,
        scheduler_task: SchedulerTask,
    ) -> SmartCutTaskRun | None:
        run = (
            self.db.query(SmartCutTaskRun)
            .filter(SmartCutTaskRun.scheduler_task_id == scheduler_task.id)
            .order_by(SmartCutTaskRun.sequence_number.desc())
            .first()
        )
        if run:
            return run

        task = self.db.query(SmartCutTask).filter(SmartCutTask.id == business_task_id).first()
        if not task:
            return None

        latest = (
            self.db.query(SmartCutTaskRun)
            .filter(SmartCutTaskRun.task_id == business_task_id)
            .order_by(SmartCutTaskRun.sequence_number.desc())
            .first()
        )
        next_sequence = 1 if latest is None else latest.sequence_number + 1
        run = SmartCutTaskRun(
            task_id=business_task_id,
            run_type=_task_type_to_run_type(scheduler_task.task_type),
            status=TaskRunStatus.CREATED,
            sequence_number=next_sequence,
            scheduler_task_id=scheduler_task.id,
            payload_snapshot=dict(scheduler_task.payload or {}),
        )
        self.db.add(run)
        self.db.flush()
        return run
    
    def check_worker_heartbeats(self, timeout_seconds: int = 60) -> int:
        """检查 Worker 心跳超时
        
        使用 device_service.check_offline_workers() 检测并标记离线 Worker。
        
        Args:
            timeout_seconds: 心跳超时时间（秒），默认 60 秒
            
        Returns:
            被标记为离线的 Worker 数量
        """
        # 先查询即将离线的 Worker，保存它们的任务 ID
        cutoff_time = datetime.utcnow() - timedelta(seconds=timeout_seconds)
        stmt = select(SmartCutDevice).where(
            and_(
                SmartCutDevice.status != DeviceStatus.OFFLINE,
                SmartCutDevice.heartbeat_at.is_(None) | 
                (SmartCutDevice.heartbeat_at < cutoff_time)
            )
        )
        soon_offline_workers = list(self.db.execute(stmt).scalars().all())
        
        # 保存 Worker ID 到任务 ID 的映射（在清空之前）
        worker_task_map = {
            w.worker_id: w.current_task_id 
            for w in soon_offline_workers 
            if w.current_task_id is not None
        }
        
        # 标记 Worker 为离线（这会清空 current_task_id）
        offline_workers = self.device_service.check_offline_workers(timeout_seconds)
        
        # 处理离线 Worker 的当前任务
        for worker in offline_workers:
            task_id = worker_task_map.get(worker.worker_id)
            if task_id:
                # 将任务重新置为 pending 状态等待重新分配
                scheduler_task = self.db.execute(
                    select(SchedulerTask).where(SchedulerTask.id == task_id)
                ).scalar_one_or_none()
                
                if scheduler_task:
                    # 重置任务状态
                    scheduler_task.status = SchedulerTaskStatus.PENDING
                    scheduler_task.assigned_worker_id = None
                    scheduler_task.assigned_at = None
                    scheduler_task.started_at = None
                    scheduler_task.updated_at = datetime.utcnow()
                    
                    logger.warning(
                        f"Task {scheduler_task.id} reset to pending due to worker "
                        f"{worker.worker_id} offline"
                    )
        
        if offline_workers:
            self.db.commit()
            logger.info(f"Marked {len(offline_workers)} workers as offline")
        
        return len(offline_workers)
