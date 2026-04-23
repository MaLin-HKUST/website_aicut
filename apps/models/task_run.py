"""Smart Cut task run 模型。

主任务卡重构引入的子执行记录表：
- upload
- analyze
- preview
- finalize
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base

if TYPE_CHECKING:
    from .task import SmartCutTask


class TaskRunType(str, PyEnum):
    UPLOAD = "upload"
    ANALYZE = "analyze"
    PREVIEW = "preview"
    FINALIZE = "finalize"


class TaskRunStatus(str, PyEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ABANDONED = "abandoned"


class SmartCutTaskRun(Base):
    __tablename__ = "smart_cut_task_runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("smart_cut_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联主任务ID",
    )
    run_type: Mapped[TaskRunType] = mapped_column(
        Enum(TaskRunType, native_enum=False),
        nullable=False,
        index=True,
        comment="子执行类型",
    )
    status: Mapped[TaskRunStatus] = mapped_column(
        Enum(TaskRunStatus, native_enum=False),
        nullable=False,
        default=TaskRunStatus.CREATED,
        index=True,
        comment="子执行状态",
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="主任务内的顺序号",
    )
    scheduler_task_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="底层调度任务ID",
    )
    source_edit_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("smart_cut_edits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="来源编辑版本ID",
    )
    payload_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="执行请求快照",
    )
    result_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="执行结果快照",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="失败错误信息",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    task: Mapped["SmartCutTask"] = relationship(
        "SmartCutTask",
        back_populates="task_runs",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<SmartCutTaskRun(id={self.id}, task_id={self.task_id}, "
            f"type={self.run_type.value}, status={self.status.value}, seq={self.sequence_number})>"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "run_type": self.run_type.value,
            "status": self.status.value,
            "sequence_number": self.sequence_number,
            "scheduler_task_id": self.scheduler_task_id,
            "source_edit_id": self.source_edit_id,
            "payload_snapshot": self.payload_snapshot,
            "result_snapshot": self.result_snapshot,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
