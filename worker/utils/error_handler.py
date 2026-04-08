"""Error Handler - 错误处理和超时检测 (F23)

提供统一的错误处理机制：
1. 失败阶段分类和记录
2. 任务超时检测（72小时）
3. 错误日志和报警
4. 数据库状态更新

失败阶段:
- analyze_failed: 分析阶段失败
- preview_failed: 预览阶段失败
- preview_upload_failed: 预览产物上传失败
- finalize_failed: 最终生成失败
- final_upload_failed: 最终视频上传失败
- groundtruth_upload_failed: GroundTruth上传失败（非阻塞）
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


logger = logging.getLogger(__name__)


class StageFailureType(str, Enum):
    """阶段失败类型枚举"""
    ANALYZE_FAILED = "analyze_failed"
    PREVIEW_FAILED = "preview_failed"
    PREVIEW_UPLOAD_FAILED = "preview_upload_failed"
    FINALIZE_FAILED = "finalize_failed"
    FINAL_UPLOAD_FAILED = "final_upload_failed"
    GROUNDTRUTH_UPLOAD_FAILED = "groundtruth_upload_failed"


class ErrorHandler:
    """错误处理器
    
    统一处理 Worker 各阶段的错误和超时。
    """
    
    # 任务超时时间（72小时）
    TASK_TIMEOUT_HOURS = 72
    
    def __init__(self, db_session_factory=None, alert_callback=None):
        """初始化错误处理器
        
        Args:
            db_session_factory: 数据库会话工厂，用于更新状态
            alert_callback: 报警回调函数，接收 (task_id, stage, error) 参数
        """
        self.db_session_factory = db_session_factory
        self.alert_callback = alert_callback
    
    def handle_stage_failure(
        self,
        task_id: str,
        stage: StageFailureType,
        error: Exception,
        business_task_id: Optional[str] = None,
        update_db: bool = True
    ) -> dict[str, Any]:
        """处理阶段失败
        
        Args:
            task_id: 调度任务ID
            stage: 失败阶段
            error: 异常对象
            business_task_id: 业务任务ID
            update_db: 是否更新数据库
            
        Returns:
            dict: 处理结果
        """
        error_message = str(error)
        
        # 记录错误日志
        logger.error(
            f"Stage failure: task_id={task_id}, stage={stage.value}, "
            f"error={error_message}",
            exc_info=error
        )
        
        # 更新数据库状态
        if update_db and business_task_id:
            self._update_task_status(business_task_id, stage, error_message)
        
        # 触发报警（如果需要）
        if self._should_alert(stage):
            self._send_alert(task_id, stage, error_message)
        
        return {
            "success": False,
            "task_id": task_id,
            "stage": stage.value,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def _update_task_status(
        self,
        business_task_id: str,
        stage: StageFailureType,
        error_message: str
    ) -> bool:
        """更新任务状态
        
        Args:
            business_task_id: 业务任务ID
            stage: 失败阶段
            error_message: 错误信息
            
        Returns:
            bool: 是否成功更新
        """
        if not self.db_session_factory:
            logger.warning("No DB session factory, skipping status update")
            return False
        
        try:
            from apps.models.task import SmartCutTask, TaskStatus
            
            db = self.db_session_factory()
            try:
                task = db.query(SmartCutTask).filter_by(id=business_task_id).first()
                if not task:
                    logger.error(f"Task not found: {business_task_id}")
                    return False
                
                # 根据阶段设置对应的状态
                status_map = {
                    StageFailureType.ANALYZE_FAILED: TaskStatus.ANALYZE_FAILED,
                    StageFailureType.PREVIEW_FAILED: TaskStatus.PREVIEW_FAILED,
                    StageFailureType.PREVIEW_UPLOAD_FAILED: TaskStatus.PREVIEW_FAILED,
                    StageFailureType.FINALIZE_FAILED: TaskStatus.FINALIZE_FAILED,
                    StageFailureType.FINAL_UPLOAD_FAILED: TaskStatus.FINALIZE_FAILED,
                    StageFailureType.GROUNDTRUTH_UPLOAD_FAILED: None,  # 不更新状态
                }
                
                new_status = status_map.get(stage)
                if new_status:
                    task.status = new_status
                    logger.info(f"Task {business_task_id} status updated to {new_status.value}")
                
                db.commit()
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            return False
    
    def _should_alert(self, stage: StageFailureType) -> bool:
        """判断是否需要报警
        
        Args:
            stage: 失败阶段
            
        Returns:
            bool: 是否需要报警
        """
        # GroundTruth 上传失败不报警（非阻塞）
        if stage == StageFailureType.GROUNDTRUTH_UPLOAD_FAILED:
            return False
        
        # 其他失败都需要报警
        return True
    
    def _send_alert(self, task_id: str, stage: StageFailureType, error_message: str) -> None:
        """发送报警
        
        Args:
            task_id: 任务ID
            stage: 失败阶段
            error_message: 错误信息
        """
        if self.alert_callback:
            try:
                self.alert_callback(task_id, stage, error_message)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
        else:
            # 默认报警方式：记录到日志
            logger.warning(
                f"ALERT: task_id={task_id}, stage={stage.value}, error={error_message}"
            )
    
    def check_task_timeout(self, task) -> bool:
        """检查任务是否超时
        
        Args:
            task: 业务任务对象 (SmartCutTask) 或调度任务对象 (SchedulerTask)
            
        Returns:
            bool: 是否超时
        """
        # 获取任务创建时间
        if hasattr(task, 'created_at'):
            created_at = task.created_at
        elif hasattr(task, 'started_at') and task.started_at:
            created_at = task.started_at
        else:
            # 无法判断，返回 False
            return False
        
        if not created_at:
            return False
        
        # 计算超时时间
        timeout_threshold = datetime.utcnow() - timedelta(hours=self.TASK_TIMEOUT_HOURS)
        
        is_timeout = created_at < timeout_threshold
        
        if is_timeout:
            logger.warning(
                f"Task timeout detected: task_id={getattr(task, 'id', 'unknown')}, "
                f"created_at={created_at}, threshold={timeout_threshold}"
            )
        
        return is_timeout
    
    def handle_timeout(
        self,
        task,
        update_db: bool = True
    ) -> dict[str, Any]:
        """处理任务超时
        
        Args:
            task: 任务对象
            update_db: 是否更新数据库
            
        Returns:
            dict: 处理结果
        """
        task_id = getattr(task, 'id', 'unknown')
        
        logger.error(f"Task timeout: {task_id}")
        
        # 更新数据库状态
        if update_db:
            self._mark_task_timeout(task)
        
        # 发送报警
        self._send_alert(task_id, StageFailureType.ANALYZE_FAILED, "Task timeout (72 hours)")
        
        return {
            "success": False,
            "task_id": task_id,
            "error": "Task timeout (72 hours)",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def _mark_task_timeout(self, task) -> bool:
        """标记任务为超时状态"""
        if not self.db_session_factory:
            return False
        
        try:
            from apps.models.task import SmartCutTask, TaskStatus
            from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus
            
            db = self.db_session_factory()
            try:
                task_id = getattr(task, 'id', None)
                if not task_id:
                    return False
                
                # 首先尝试作为业务任务处理
                task_db = db.query(SmartCutTask).filter_by(id=task_id).first()
                if task_db:
                    # 业务任务超时
                    # 根据当前阶段设置失败状态
                    if task_db.current_stage.value in ['analyze', 'preview', 'finalize']:
                        if task_db.current_stage.value == 'analyze':
                            task_db.status = TaskStatus.ANALYZE_FAILED
                        elif task_db.current_stage.value == 'preview':
                            task_db.status = TaskStatus.PREVIEW_FAILED
                        elif task_db.current_stage.value == 'finalize':
                            task_db.status = TaskStatus.FINALIZE_FAILED
                    
                    db.commit()
                    logger.info(f"Business task marked as timeout: {task_id}")
                    return True
                
                # 尝试作为调度任务处理
                scheduler_task_db = db.query(SchedulerTask).filter_by(id=task_id).first()
                if scheduler_task_db:
                    scheduler_task_db.mark_timeout()
                    db.commit()
                    logger.info(f"Scheduler task marked as timeout: {task_id}")
                    return True
                
                return False
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to mark task timeout: {e}")
            return False
    
    def cleanup_stalled_tasks(self, db_session) -> int:
        """清理卡住的任务
        
        查找所有超时任务并标记为失败。
        
        Args:
            db_session: 数据库会话
            
        Returns:
            int: 清理的任务数量
        """
        from apps.models.task import SmartCutTask, TaskStatus
        from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus
        
        timeout_threshold = datetime.utcnow() - timedelta(hours=self.TASK_TIMEOUT_HOURS)
        cleaned_count = 0
        
        try:
            # 查找超时的业务任务
            stalled_tasks = db_session.query(SmartCutTask).filter(
                SmartCutTask.created_at < timeout_threshold,
                SmartCutTask.status.notin_([
                    TaskStatus.SUCCESS,
                    TaskStatus.ABANDONED,
                    TaskStatus.ANALYZE_FAILED,
                    TaskStatus.PREVIEW_FAILED,
                    TaskStatus.FINALIZE_FAILED,
                ])
            ).all()
            
            for task in stalled_tasks:
                # 根据阶段设置失败状态
                if task.current_stage.value == 'analyze':
                    task.status = TaskStatus.ANALYZE_FAILED
                elif task.current_stage.value == 'preview':
                    task.status = TaskStatus.PREVIEW_FAILED
                elif task.current_stage.value == 'finalize':
                    task.status = TaskStatus.FINALIZE_FAILED
                
                cleaned_count += 1
                logger.info(f"Cleaned up stalled task: {task.id}")
            
            # 查找超时的调度任务
            stalled_scheduler_tasks = db_session.query(SchedulerTask).filter(
                SchedulerTask.created_at < timeout_threshold,
                SchedulerTask.status.in_([
                    SchedulerTaskStatus.PENDING,
                    SchedulerTaskStatus.ASSIGNED,
                    SchedulerTaskStatus.RUNNING,
                ])
            ).all()
            
            for task in stalled_scheduler_tasks:
                task.mark_timeout()
                cleaned_count += 1
                logger.info(f"Cleaned up stalled scheduler task: {task.id}")
            
            db_session.commit()
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to cleanup stalled tasks: {e}")
        
        return cleaned_count


class TimeoutHandler:
    """超时处理器
    
    专门处理超时任务的后台服务。
    可以作为一个定时任务运行。
    """
    
    def __init__(self, db_session_factory, check_interval_minutes: int = 60):
        """初始化超时处理器
        
        Args:
            db_session_factory: 数据库会话工厂
            check_interval_minutes: 检查间隔（分钟）
        """
        self.db_session_factory = db_session_factory
        self.check_interval = check_interval_minutes
        self.error_handler = ErrorHandler(db_session_factory)
    
    def run_cleanup(self) -> int:
        """运行清理任务
        
        Returns:
            int: 清理的任务数量
        """
        db = self.db_session_factory()
        try:
            count = self.error_handler.cleanup_stalled_tasks(db)
            if count > 0:
                logger.info(f"Timeout cleanup completed: {count} tasks cleaned")
            return count
        finally:
            db.close()
    
    async def start_monitoring(self):
        """启动后台监控（异步）"""
        import asyncio
        
        logger.info(f"Timeout monitoring started, interval={self.check_interval}min")
        
        while True:
            try:
                self.run_cleanup()
            except Exception as e:
                logger.error(f"Timeout monitoring error: {e}")
            
            # 等待下一次检查
            await asyncio.sleep(self.check_interval * 60)


# 便捷函数
def create_error_handler(db_session_factory=None, alert_callback=None) -> ErrorHandler:
    """创建错误处理器的工厂函数"""
    return ErrorHandler(db_session_factory, alert_callback)


def create_timeout_handler(db_session_factory, check_interval_minutes: int = 60) -> TimeoutHandler:
    """创建超时处理器的工厂函数"""
    return TimeoutHandler(db_session_factory, check_interval_minutes)
