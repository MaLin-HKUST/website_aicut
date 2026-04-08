"""Scheduler Task 模型 - F04 基础实现（供 F05 引用）"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, Any, TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, JSON, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base

if TYPE_CHECKING:
    from .device import SmartCutDevice


class SchedulerTaskStatus(str, PyEnum):
    """调度任务状态枚举"""
    PENDING = "pending"          # 等待分配
    ASSIGNED = "assigned"        # 已分配给 Worker
    RUNNING = "running"          # 执行中
    POST = "post"                # 执行完成，等待确认
    SUCCESS = "success"          # 成功完成
    FAILED = "failed"            # 执行失败
    TIMEOUT = "timeout"          # 执行超时


class SchedulerTaskType(str, PyEnum):
    """调度任务类型枚举"""
    SMART_CUT_ANALYZE = "smart_cut_analyze"
    SMART_CUT_PREVIEW = "smart_cut_preview"
    SMART_CUT_FINALIZE = "smart_cut_finalize"


class SchedulerTask(Base):
    """调度任务模型 - 内部调度使用"""
    
    __tablename__ = "scheduler_tasks"
    
    # ========== 基础字段 ==========
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    task_type: Mapped[SchedulerTaskType] = mapped_column(
        Enum(SchedulerTaskType),
        nullable=False,
        index=True,
        comment="任务类型"
    )
    status: Mapped[SchedulerTaskStatus] = mapped_column(
        Enum(SchedulerTaskStatus),
        nullable=False,
        default=SchedulerTaskStatus.PENDING,
        index=True,
        comment="任务状态"
    )
    
    # ========== 关联字段 ==========
    business_task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("smart_cut_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的业务任务ID"
    )
    assigned_worker_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="分配的Worker ID"
    )
    
    # ========== 任务内容 ==========
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="任务参数(JSON格式)"
    )
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="执行结果(JSON格式)"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息"
    )
    
    # ========== 时间字段 ==========
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间"
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="分配时间"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="开始执行时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="完成时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    
    # ========== 关系 ==========
    business_task: Mapped["SmartCutTask"] = relationship(
        "SmartCutTask",
        back_populates="scheduler_tasks"
    )
    assigned_worker: Mapped[Optional["SmartCutDevice"]] = relationship(
        "SmartCutDevice",
        back_populates="current_task",
        foreign_keys="SmartCutDevice.current_task_id"
    )
    
    def __repr__(self) -> str:
        return (
            f"<SchedulerTask(id={self.id}, "
            f"type={self.task_type.value}, "
            f"status={self.status.value})>"
        )
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "business_task_id": self.business_task_id,
            "assigned_worker_id": self.assigned_worker_id,
            "payload": self.payload,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def assign_to_worker(self, worker_id: str) -> None:
        """将任务分配给 Worker
        
        Args:
            worker_id: Worker ID
        """
        self.assigned_worker_id = worker_id
        self.status = SchedulerTaskStatus.ASSIGNED
        self.assigned_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_running(self) -> None:
        """标记任务为执行中状态"""
        self.status = SchedulerTaskStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_completed(self, result: Optional[dict[str, Any]] = None) -> None:
        """标记任务为完成状态
        
        Args:
            result: 执行结果数据
        """
        self.status = SchedulerTaskStatus.SUCCESS
        self.result = result
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_failed(self, error_message: str) -> None:
        """标记任务为失败状态
        
        Args:
            error_message: 错误信息
        """
        self.status = SchedulerTaskStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_timeout(self) -> None:
        """标记任务为超时状态"""
        self.status = SchedulerTaskStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
