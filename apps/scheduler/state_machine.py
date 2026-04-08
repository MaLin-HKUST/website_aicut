"""State Machine Service - F12 状态机推进逻辑

提供 SmartCutTask 的状态流转服务，处理任务各阶段的推进逻辑。
"""

from typing import Optional, Any

from sqlalchemy.orm import Session

from apps.models.task import SmartCutTask, TaskStatus, CurrentStage
from apps.models.device import SmartCutDevice, DeviceStatus
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskType


class StateMachineService:
    """状态机服务类
    
    封装 SmartCutTask 的状态流转逻辑，包括：
    - 根据设备状态推进任务状态
    - 完成当前阶段的状态转换
    - 处理任务失败场景
    """
    
    def __init__(self, db: Session):
        """初始化服务
        
        Args:
            db: SQLAlchemy 数据库会话
        """
        self.db = db
    
    def advance_task_status(
        self,
        task: SmartCutTask,
        device: SmartCutDevice,
        scheduler_task: SchedulerTask
    ) -> None:
        """根据设备状态推进任务状态
        
        Args:
            task: SmartCutTask 业务任务对象
            device: SmartCutDevice 设备对象
            scheduler_task: SchedulerTask 调度任务对象
            
        Raises:
            ValueError: 当设备状态或任务类型无效时
        """
        if device.status == DeviceStatus.RUNNING:
            # 设备正在运行，更新任务状态为对应执行中状态
            if scheduler_task.task_type == SchedulerTaskType.SMART_CUT_ANALYZE:
                task.status = TaskStatus.ANALYZING
                task.current_stage = CurrentStage.ANALYZE
            elif scheduler_task.task_type == SchedulerTaskType.SMART_CUT_PREVIEW:
                task.status = TaskStatus.PREVIEWING
                task.current_stage = CurrentStage.PREVIEW
            elif scheduler_task.task_type == SchedulerTaskType.SMART_CUT_FINALIZE:
                task.status = TaskStatus.FINALIZING
                task.current_stage = CurrentStage.FINALIZE
            else:
                raise ValueError(f"未知的调度任务类型: {scheduler_task.task_type}")
                
        elif device.status == DeviceStatus.POST:
            # 设备执行完成，进入确认阶段
            # 实际的完成处理由 complete_current_stage 处理
            pass
        else:
            # 其他状态不推进
            pass
        
        self.db.commit()
    
    def complete_current_stage(
        self,
        task: SmartCutTask,
        scheduler_task: SchedulerTask,
        result: dict[str, Any]
    ) -> None:
        """完成当前阶段并推进到下一阶段
        
        根据 scheduler_task.task_type 处理不同阶段：
        - smart_cut_analyze: 分析完成 -> waiting_user
        - smart_cut_preview: 预览完成 -> waiting_user
        - smart_cut_finalize: 最终生成完成 -> success
        
        Args:
            task: SmartCutTask 业务任务对象
            scheduler_task: SchedulerTask 调度任务对象
            result: 任务执行结果字典
            
        Raises:
            ValueError: 当任务类型无效时
        """
        if scheduler_task.task_type == SchedulerTaskType.SMART_CUT_ANALYZE:
            self._complete_analyze_stage(task, result)
        elif scheduler_task.task_type == SchedulerTaskType.SMART_CUT_PREVIEW:
            self._complete_preview_stage(task, result)
        elif scheduler_task.task_type == SchedulerTaskType.SMART_CUT_FINALIZE:
            self._complete_finalize_stage(task, result)
        else:
            raise ValueError(f"未知的调度任务类型: {scheduler_task.task_type}")
        
        self.db.commit()
        self.db.refresh(task)
    
    def _complete_analyze_stage(
        self,
        task: SmartCutTask,
        result: dict[str, Any]
    ) -> None:
        """完成分析阶段
        
        Args:
            task: SmartCutTask 业务任务对象
            result: 分析结果，包含 analyze_script 和 asr_result_tos_key
        """
        task.status = TaskStatus.WAITING_USER
        task.current_stage = CurrentStage.USER_SELECT
        
        # 保存分析产物
        if "analyze_script" in result:
            task.analyze_script = result["analyze_script"]
        if "asr_result_tos_key" in result:
            task.asr_result_tos_key = result["asr_result_tos_key"]
    
    def _complete_preview_stage(
        self,
        task: SmartCutTask,
        result: dict[str, Any]
    ) -> None:
        """完成预览阶段
        
        Args:
            task: SmartCutTask 业务任务对象
            result: 预览结果，包含 edit_id
        """
        task.status = TaskStatus.WAITING_USER
        task.current_stage = CurrentStage.USER_SELECT
        
        # 保存当前生效的 edit ID
        if "edit_id" in result:
            task.active_edit_id = result["edit_id"]
    
    def _complete_finalize_stage(
        self,
        task: SmartCutTask,
        result: dict[str, Any]
    ) -> None:
        """完成最终生成阶段
        
        Args:
            task: SmartCutTask 业务任务对象
            result: 最终生成结果，包含 final_video_url 等
        """
        task.status = TaskStatus.SUCCESS
        task.current_stage = CurrentStage.COMPLETE
        
        # 保存最终产物
        if "final_video_url" in result:
            task.final_video_url = result["final_video_url"]
        if "groundtruth_url" in result:
            task.groundtruth_url = result["groundtruth_url"]
        if "groundtruth_upload_status" in result:
            task.groundtruth_upload_status = result["groundtruth_upload_status"]
    
    def handle_stage_failure(
        self,
        task: SmartCutTask,
        scheduler_task: SchedulerTask,
        error: str
    ) -> None:
        """处理阶段失败
        
        根据任务类型设置对应的失败状态：
        - smart_cut_analyze -> analyze_failed
        - smart_cut_preview -> preview_failed
        - smart_cut_finalize -> finalize_failed
        
        Args:
            task: SmartCutTask 业务任务对象
            scheduler_task: SchedulerTask 调度任务对象
            error: 错误信息
            
        Raises:
            ValueError: 当任务类型无效时
        """
        if scheduler_task.task_type == SchedulerTaskType.SMART_CUT_ANALYZE:
            task.status = TaskStatus.ANALYZE_FAILED
        elif scheduler_task.task_type == SchedulerTaskType.SMART_CUT_PREVIEW:
            task.status = TaskStatus.PREVIEW_FAILED
        elif scheduler_task.task_type == SchedulerTaskType.SMART_CUT_FINALIZE:
            task.status = TaskStatus.FINALIZE_FAILED
        else:
            raise ValueError(f"未知的调度任务类型: {scheduler_task.task_type}")
        
        # 保存错误信息到调度任务
        scheduler_task.error_message = error
        
        self.db.commit()
        self.db.refresh(task)
    
    def can_advance(
        self,
        task: SmartCutTask,
        device: SmartCutDevice,
        scheduler_task: SchedulerTask
    ) -> bool:
        """检查是否可以推进任务状态
        
        Args:
            task: SmartCutTask 业务任务对象
            device: SmartCutDevice 设备对象
            scheduler_task: SchedulerTask 调度任务对象
            
        Returns:
            bool: 是否可以推进状态
        """
        # 终态任务不能推进
        if task.is_terminal():
            return False
        
        # 只有 running 或 post 状态的设备可以推进任务
        if device.status not in (DeviceStatus.RUNNING, DeviceStatus.POST):
            return False
        
        # 调度任务必须是 running 状态
        if scheduler_task.status.value != "running":
            return False
        
        return True
