"""Scheduler Service - 调度服务

提供任务调度和分配功能。
"""

from typing import Optional
from sqlalchemy.orm import Session

from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus
from apps.models.device import SmartCutDevice, DeviceStatus
from apps.services.device_service import DeviceService


class SchedulerService:
    """调度服务类
    
    负责任务的分配和调度策略。
    """
    
    def __init__(self, db: Session):
        """初始化服务
        
        Args:
            db: SQLAlchemy 数据库会话
        """
        self.db = db
        self.device_service = DeviceService(db)
    
    def get_pending_task(self) -> Optional[SchedulerTask]:
        """获取待处理的任务
        
        Returns:
            SchedulerTask: 待处理的任务，如果没有则返回 None
        """
        from sqlalchemy import select
        
        stmt = (
            select(SchedulerTask)
            .where(SchedulerTask.status == SchedulerTaskStatus.PENDING)
            .order_by(SchedulerTask.created_at.asc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()
    
    def assign_task_to_worker(
        self,
        task: SchedulerTask,
        worker: SmartCutDevice
    ) -> bool:
        """将任务分配给 Worker
        
        Args:
            task: 调度任务
            worker: Worker 设备
            
        Returns:
            bool: 是否分配成功
        """
        if not worker.is_available():
            return False
        
        if not worker.can_handle(task.task_type.value):
            return False
        
        # 分配任务
        task.assign_to_worker(worker.worker_id)
        
        # 更新 Worker 状态
        self.device_service.update_device_status(
            worker_id=worker.worker_id,
            status=DeviceStatus.IDLE,  # 保持 idle，等待 Worker 认领
            current_task_id=task.id
        )
        
        self.db.commit()
        return True
    
    def schedule_pending_tasks(self) -> list[tuple[SchedulerTask, SmartCutDevice]]:
        """调度所有待处理任务
        
        将待处理任务分配给空闲的 Worker。
        
        Returns:
            list: 成功分配的任务和 Worker 列表
        """
        results = []
        
        while True:
            # 获取待处理任务
            task = self.get_pending_task()
            if task is None:
                break
            
            # 查找可用的 Worker
            workers = self.device_service.get_idle_workers(
                task_type=task.task_type.value
            )
            
            if not workers:
                # 没有可用 Worker，停止调度
                break
            
            # 选择第一个可用的 Worker
            worker = workers[0]
            
            # 分配任务
            if self.assign_task_to_worker(task, worker):
                results.append((task, worker))
        
        return results
