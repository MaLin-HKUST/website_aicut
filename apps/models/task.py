"""Smart Cut Task 模型 - F02 实现

smart_cut_tasks 表 - 业务任务主表
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Optional, List

from sqlalchemy import String, Text, DateTime, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base


class TaskStatus(str, PyEnum):
    """任务状态枚举"""
    # 初始状态
    WAITING_UPLOAD = "waiting_upload"      # 等待用户上传视频和文案
    READY_ANALYZE = "ready_analyze"        # 已上传，准备分析
    
    # 分析阶段
    ANALYZING = "analyzing"                # 分析中
    ANALYZE_FAILED = "analyze_failed"      # 分析失败
    
    # 用户交互阶段
    WAITING_USER = "waiting_user"          # 分析完成，等待用户选择
    
    # 预览阶段
    PREVIEWING = "previewing"              # 预览视频生成中
    PREVIEW_FAILED = "preview_failed"      # 预览生成失败
    
    # 最终生成阶段
    FINALIZING = "finalizing"              # 最终视频生成中
    FINALIZE_FAILED = "finalize_failed"    # 最终生成失败
    
    # 终态
    SUCCESS = "success"                    # 完成
    ABANDONED = "abandoned"                # 用户放弃


class CurrentStage(str, PyEnum):
    """当前阶段枚举"""
    UPLOAD = "upload"
    ANALYZE = "analyze"
    USER_SELECT = "user_select"
    PREVIEW = "preview"
    FINALIZE = "finalize"
    COMPLETE = "complete"


class SmartCutTask(Base):
    """Smart Cut 业务任务表
    
    对外暴露的业务任务，包含完整的三阶段处理流程
    """
    
    __tablename__ = "smart_cut_tasks"
    
    # 主键 - UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # 用户关联
    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="用户ID"
    )
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # 任务状态
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
        default=TaskStatus.WAITING_UPLOAD,
        nullable=False
    )
    
    # 当前阶段
    current_stage: Mapped[CurrentStage] = mapped_column(
        Enum(CurrentStage),
        nullable=False,
        default=CurrentStage.UPLOAD,
        comment="当前阶段"
    )

    task_title: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="任务中心展示标题"
    )

    visible_in_task_center: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="是否在任务中心可见"
    )

    session_scope_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="当前登录会话的服务端作用域 ID"
    )
    
    # 输入文件
    original_video_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="原始视频URL"
    )
    reference_text_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="参考文案URL"
    )
    
    # Analyze 产物
    analyze_script: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="分析生成的脚本"
    )
    asr_result_tos_key: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="ASR结果TOS Key"
    )
    
    # Preview 关联
    active_edit_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="当前生效的edit ID"
    )
    
    # Finalize 产物
    final_video_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="最终视频URL"
    )
    groundtruth_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Ground Truth 视频URL"
    )
    groundtruth_upload_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Ground Truth 上传状态"
    )
    
    # 关系 - 关联的调度任务（延迟导入避免循环依赖）
    scheduler_tasks: Mapped[Optional[List["SchedulerTask"]]] = relationship(
        "SchedulerTask",
        back_populates="business_task",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # 关系 - 关联的 Edit 记录 (F03)
    edits: Mapped[Optional[List["SmartCutEdit"]]] = relationship(
        "SmartCutEdit",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="SmartCutEdit.version_number"
    )
    
    def __repr__(self) -> str:
        return (
            f"<SmartCutTask("
            f"id={self.id!r}, "
            f"user_id={self.user_id!r}, "
            f"status={self.status.value!r}, "
            f"stage={self.current_stage.value!r}"
            f")>"
        )
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status.value,
            "current_stage": self.current_stage.value,
            "task_title": self.task_title,
            "visible_in_task_center": self.visible_in_task_center,
            "session_scope_id": self.session_scope_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "original_video_url": self.original_video_url,
            "reference_text_url": self.reference_text_url,
            "analyze_script": self.analyze_script,
            "asr_result_tos_key": self.asr_result_tos_key,
            "active_edit_id": self.active_edit_id,
            "final_video_url": self.final_video_url,
            "groundtruth_url": self.groundtruth_url,
            "groundtruth_upload_status": self.groundtruth_upload_status,
        }
    
    def is_terminal(self) -> bool:
        """检查是否处于终态"""
        return self.status in {
            TaskStatus.SUCCESS,
            TaskStatus.ABANDONED,
            TaskStatus.ANALYZE_FAILED,
            TaskStatus.PREVIEW_FAILED,
            TaskStatus.FINALIZE_FAILED,
        }
    
    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """检查状态转换是否合法"""
        # 终态不能再转换
        if self.is_terminal():
            return False
        
        # 定义合法的状态转换
        valid_transitions: dict[TaskStatus, set[TaskStatus]] = {
            TaskStatus.WAITING_UPLOAD: {TaskStatus.READY_ANALYZE, TaskStatus.ABANDONED},
            TaskStatus.READY_ANALYZE: {TaskStatus.ANALYZING, TaskStatus.ABANDONED},
            TaskStatus.ANALYZING: {TaskStatus.WAITING_USER, TaskStatus.ANALYZE_FAILED},
            TaskStatus.WAITING_USER: {TaskStatus.PREVIEWING, TaskStatus.ABANDONED},
            TaskStatus.PREVIEWING: {TaskStatus.WAITING_USER, TaskStatus.PREVIEW_FAILED, TaskStatus.FINALIZING},
            TaskStatus.PREVIEW_FAILED: {TaskStatus.PREVIEWING, TaskStatus.ABANDONED},
            TaskStatus.FINALIZING: {TaskStatus.SUCCESS, TaskStatus.FINALIZE_FAILED},
            TaskStatus.FINALIZE_FAILED: {TaskStatus.FINALIZING, TaskStatus.ABANDONED},
        }
        
        allowed = valid_transitions.get(self.status, set())
        return new_status in allowed
