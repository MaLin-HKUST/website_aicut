from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="company")
    materials: Mapped[list["Material"]] = relationship(back_populates="company")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)

    company: Mapped[Company | None] = relationship(back_populates="users")


class Material(TimestampMixin, Base):
    __tablename__ = "materials"
    __table_args__ = (UniqueConstraint("name", "company_id", name="uq_material_name_company"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    company: Mapped[Company] = relationship(back_populates="materials")


class Session(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)


class UserUsageMonthly(TimestampMixin, Base):
    """用户每月 TTS 消耗统计，支持管理员手动调整."""
    __tablename__ = "user_usage_monthly"
    __table_args__ = (UniqueConstraint("user_id", "year_month", name="uq_user_month"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # 格式: 2024-04
    credits_used: Mapped[int] = mapped_column(default=0, nullable=False)  # 本月累计消耗
    credits_limit: Mapped[int | None] = mapped_column(default=None, nullable=True)  # 月度限额（可选）
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SchedulerTask(TimestampMixin, Base):
    __tablename__ = "scheduler_tasks"

    task_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    page_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    assigned_worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    step_index: Mapped[int] = mapped_column(default=0, nullable=False)
    step_total: Mapped[int] = mapped_column(default=1, nullable=False)
    workspace_uri: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    keep_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    needs_post: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class SchedulerWorker(TimestampMixin, Base):
    __tablename__ = "scheduler_workers"

    worker_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    worker_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supported_task_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    current_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SchedulerAlarm(Base):
    __tablename__ = "scheduler_alarms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    alarm_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    current_state: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# ============================================
# Smart Cut Scheduler Models (F02)
# ============================================

class SmartCutTaskStatus:
    """业务任务状态"""
    CREATED = "created"
    WAITING_UPLOAD = "waiting_upload"
    READY_ANALYZE = "ready_analyze"
    ANALYZING = "analyzing"
    WAITING_USER = "waiting_user"
    PREVIEWING = "previewing"
    READY_FINALIZE = "ready_finalize"
    FINALIZING = "finalizing"
    SUCCESS = "success"
    FAILED = "failed"


class SmartCutErrorStage:
    """失败阶段细分"""
    INPUT_UPLOAD_FAILED = "input_upload_failed"
    ANALYZE_FAILED = "analyze_failed"
    PREVIEW_FAILED = "preview_failed"
    PREVIEW_UPLOAD_FAILED = "preview_upload_failed"
    FINALIZE_FAILED = "finalize_failed"
    FINAL_UPLOAD_FAILED = "final_upload_failed"
    GROUNDTRUTH_UPLOAD_FAILED = "groundtruth_upload_failed"


class SmartCutTask(TimestampMixin, Base):
    """Smart Cut 业务任务表 - 对应实施计划 6.1"""
    __tablename__ = "smart_cut_tasks"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # 业务状态
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True, default=SmartCutTaskStatus.CREATED)
    current_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    error_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # upload-prepare 阶段发出的目标 key（用于 bind 校验）
    prepared_video_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    prepared_text_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 输入文件绑定（upload-complete 确认后写入）
    original_video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_video_tos_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_text_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_text_tos_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # analyze 产物
    analyze_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyze_script_tos_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    asr_result_tos_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # edit 关联
    active_edit_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    finalize_source_edit_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # finalize 产物
    final_video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    final_video_tos_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    groundtruth_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    groundtruth_tos_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 配置项
    feed_to_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    output_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)  # original, vertical_1080p

    # 调度关联
    last_scheduler_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 关系
    edits: Mapped[list["SmartCutEdit"]] = relationship(
        back_populates="task",
        order_by="desc(SmartCutEdit.created_at)",
        cascade="all, delete-orphan",
    )


class SmartCutEdit(TimestampMixin, Base):
    """Smart Cut Preview 历史表 - 对应实施计划 6.2"""
    __tablename__ = "smart_cut_edits"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("smart_cut_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 用户编辑的 script
    edited_script: Mapped[str] = mapped_column(Text, nullable=False)

    # 状态
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")  # pending, processing, success, failed

    # preview 产物
    audio_b_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_b_tos_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    edited_delay_cuts_tos_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pause_cuts_on_original_tos_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 错误信息
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 关系
    task: Mapped[SmartCutTask] = relationship(back_populates="edits")
