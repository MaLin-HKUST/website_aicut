"""
Smart Cut Edit 模型 - F03 实现
Preview 历史表，记录每次编辑和预览的结果
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String, DateTime, JSON, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# 从 configs.database 导入 Base 以保持与 F02 一致
try:
    from configs.database import Base
except ImportError:
    # 如果 configs.database 不存在，创建自己的 Base
    from sqlalchemy.orm import DeclarativeBase
    
    class Base(DeclarativeBase):
        pass


if TYPE_CHECKING:
    from .task import SmartCutTask


class EditStatus(str, Enum):
    """Edit 记录状态枚举"""
    EDITING = "editing"       # 用户正在编辑
    PROCESSING = "processing" # 正在处理中
    SUCCESS = "success"       # 处理成功
    FAILED = "failed"         # 处理失败


class SmartCutEdit(Base):
    """
    Smart Cut Edit 模型
    
    对应数据库表: smart_cut_edits
    记录每次用户对文案的编辑和对应的 preview 结果
    
    外键关联:
        - task_id -> smart_cut_tasks.id (String(36))
    """
    
    __tablename__ = "smart_cut_edits"
    
    # ========================================
    # 基础字段
    # ========================================
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Edit 记录唯一标识 (UUID)"
    )
    
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("smart_cut_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的业务任务ID"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )
    
    # ========================================
    # 编辑内容
    # ========================================
    
    edited_script: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="用户编辑后的文案内容，JSON格式"
    )
    
    # ========================================
    # 状态
    # ========================================
    
    status: Mapped[EditStatus] = mapped_column(
        SQLEnum(EditStatus, native_enum=False, length=20),
        nullable=False,
        default=EditStatus.EDITING,
        index=True,
        comment="Edit 状态: editing/processing/success/failed"
    )
    
    # ========================================
    # Analyze 阶段产物 (从 Worker 获取)
    # ========================================
    
    audio_a_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="原始音频URL (analyze阶段生成)"
    )
    
    delay_cuts_tos_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="延迟切割配置TOS Key (analyze阶段生成)"
    )
    
    # ========================================
    # Preview 阶段产物
    # ========================================
    
    audio_b_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="预览音频URL (preview阶段生成)"
    )
    
    pause_cuts_tos_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="停顿切割配置TOS Key (preview阶段生成)"
    )
    
    # ========================================
    # 版本控制
    # ========================================
    
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="版本号，表示第几次编辑"
    )
    
    # ========================================
    # 关系定义
    # ========================================
    
    task: Mapped["SmartCutTask"] = relationship(
        "SmartCutTask",
        back_populates="edits",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return (
            f"<SmartCutEdit("
            f"id={self.id}, "
            f"task_id={self.task_id}, "
            f"version={self.version_number}, "
            f"status={self.status.value}"
            f")>"
        )
    
    def to_dict(self) -> dict[str, Any]:
        """将模型转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "edited_script": self.edited_script,
            "status": self.status.value,
            "audio_a_url": self.audio_a_url,
            "delay_cuts_tos_key": self.delay_cuts_tos_key,
            "audio_b_url": self.audio_b_url,
            "pause_cuts_tos_key": self.pause_cuts_tos_key,
            "version_number": self.version_number,
        }
    
    @classmethod
    def get_next_version_number(cls, session, task_id: str) -> int:
        """
        获取指定任务的下一个版本号
        
        Args:
            session: SQLAlchemy session
            task_id: 任务ID (str)
            
        Returns:
            下一个版本号
        """
        from sqlalchemy import select, func as sql_func
        
        stmt = select(sql_func.coalesce(sql_func.max(cls.version_number), 0) + 1).where(
            cls.task_id == task_id
        )
        result = session.execute(stmt).scalar()
        return result or 1
