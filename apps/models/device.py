"""Smart Cut Device 模型 - F05 实现

Worker 设备表 - 记录所有 Smart Cut Worker 的状态和信息
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, Any, TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base

if TYPE_CHECKING:
    from .scheduler_task import SchedulerTask


class DeviceStatus(str, PyEnum):
    """设备状态枚举
    
    - idle: 空闲，可以接收新任务
    - running: 正在执行任务
    - post: 任务执行完成，等待 A 端确认
    - offline: 离线（心跳超时）
    """
    IDLE = "idle"
    RUNNING = "running"
    POST = "post"
    OFFLINE = "offline"


class SmartCutDevice(Base):
    """Smart Cut Worker 设备模型
    
    记录 Worker 的注册信息、状态、能力和当前任务。
    支持动态注册和心跳机制。
    """
    
    __tablename__ = "smart_cut_devices"
    
    # ========== 主键 ==========
    worker_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="Worker 唯一标识，如 worker-001"
    )
    
    # ========== 基础信息 ==========
    worker_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Worker 显示名称"
    )
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus),
        nullable=False,
        default=DeviceStatus.IDLE,
        index=True,
        comment="设备状态: idle/running/post/offline"
    )
    
    # ========== 能力配置 ==========
    supported_task_types: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="支持的任务类型列表，如 [\"smart_cut_analyze\", \"smart_cut_preview\"]"
    )
    
    # ========== 当前任务 ==========
    current_task_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("scheduler_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        unique=True,
        comment="当前执行的任务ID，外键关联 scheduler_tasks"
    )
    
    # ========== 心跳时间 ==========
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
        comment="最后一次心跳时间"
    )
    
    # ========== 元数据 ==========
    worker_version: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Worker 版本号"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Worker IP 地址"
    )
    hostname: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Worker 主机名"
    )
    
    # ========== 时间戳 ==========
    registered_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="注册时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    
    # ========== 关系 ==========
    current_task: Mapped[Optional["SchedulerTask"]] = relationship(
        "SchedulerTask",
        back_populates="assigned_worker",
        foreign_keys=[current_task_id]
    )
    
    def __repr__(self) -> str:
        return (
            f"<SmartCutDevice(worker_id={self.worker_id}, "
            f"name={self.worker_name}, "
            f"status={self.status.value})>"
        )
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "worker_id": self.worker_id,
            "worker_name": self.worker_name,
            "status": self.status.value,
            "supported_task_types": self.supported_task_types,
            "current_task_id": self.current_task_id,
            "heartbeat_at": self.heartbeat_at.isoformat() if self.heartbeat_at else None,
            "worker_version": self.worker_version,
            "ip_address": self.ip_address,
            "hostname": self.hostname,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_available(self) -> bool:
        """检查设备是否可用（空闲且在线）"""
        return self.status == DeviceStatus.IDLE
    
    def can_handle(self, task_type: str) -> bool:
        """检查设备是否能处理指定任务类型"""
        return task_type in self.supported_task_types
    
    def is_offline(self, timeout_seconds: int = 60) -> bool:
        """检查设备是否离线（根据心跳超时）"""
        if self.heartbeat_at is None:
            return True
        elapsed = (datetime.utcnow() - self.heartbeat_at).total_seconds()
        return elapsed > timeout_seconds
