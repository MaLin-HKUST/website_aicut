"""
智能剪口播数据模型

包含 SmartCutTask 和 SmartCutEdit 模型定义。
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid


class TaskStatus(str, Enum):
    """任务状态枚举"""
    CREATED = "created"
    INPUT_UPLOADING = "input_uploading"
    INPUT_UPLOADED = "input_uploaded"
    ANALYZING = "analyzing"
    ANALYZE_SUCCESS = "analyze_success"
    ANALYZE_FAILED = "analyze_failed"
    PREVIEWING = "previewing"
    PREVIEW_SUCCESS = "preview_success"
    PREVIEW_FAILED = "preview_failed"
    FINALIZING = "finalizing"
    FINALIZE_SUCCESS = "finalize_success"
    FINALIZE_FAILED = "finalize_failed"
    SUCCESS = "success"


class UploadStatus(str, Enum):
    """上传状态枚举"""
    PENDING = "pending"
    UPLOADING = "uploading"
    SUCCESS = "success"
    FAILED = "failed"


class OutputMode(str, Enum):
    """输出模式枚举"""
    ORIGINAL = "original"
    VERTICAL_1080P = "vertical_1080p"


class SmartCutTaskMixin:
    """SmartCutTask 模型的 Mixin 类，便于集成到现有数据库"""
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # 用户关联
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    
    # 任务状态
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TaskStatus.CREATED.value,
    )
    
    # 输入文件信息
    original_video_url: Mapped[str] = mapped_column(Text, nullable=False)
    original_video_tos_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_text_url: Mapped[str] = mapped_column(Text, nullable=False)
    reference_text_tos_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_upload_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        default=UploadStatus.PENDING.value,
    )
    
    # Analyze 阶段产物
    analyze_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analyze_script_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analyze_audio_a_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analyze_asr_result_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analyze_delay_cuts_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 当前活跃编辑状态（最后一次成功的 preview）
    active_edited_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active_edit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    active_delay_cuts_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active_audio_a_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active_pause_cuts_audio_a_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active_pause_cuts_original_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active_audio_b_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Finalize 配置
    final_output_mode: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        default=OutputMode.ORIGINAL.value,
    )
    feed_to_ai: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    finalize_source_edit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    
    # 最终产物
    final_video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_video_tos_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_upload_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    normalized_video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_process_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_cut_plan_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # GroundTruth
    groundtruth_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    groundtruth_tos_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    groundtruth_upload_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    
    # 工作目录和处理参数
    work_dir: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    input_media_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    encoding_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 错误信息
    error_stage: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class SmartCutEditMixin:
    """SmartCutEdit 模型的 Mixin 类，用于记录每次编辑历史"""
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # 关联任务
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    
    # 编辑内容
    edited_script: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 产物 URL
    delay_cuts_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_a_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pause_cuts_audio_a_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pause_cuts_original_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_b_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_b_tos_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TaskStatus.PREVIEWING.value,
    )
    
    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# SQLAlchemy 模型定义（用于直接创建表）
# 这些可以被复制到主项目的 models.py 中

SMART_CUT_TASK_SQL = """
CREATE TABLE IF NOT EXISTS smart_cut_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL,
    company_id INTEGER,
    status VARCHAR(32) NOT NULL DEFAULT 'created',
    
    original_video_url TEXT NOT NULL,
    original_video_tos_key TEXT,
    reference_text_url TEXT NOT NULL,
    reference_text_tos_key TEXT,
    input_upload_status VARCHAR(32) DEFAULT 'pending',
    
    analyze_script TEXT,
    analyze_script_url TEXT,
    analyze_audio_a_url TEXT,
    analyze_asr_result_url TEXT,
    analyze_delay_cuts_url TEXT,
    
    active_edited_script TEXT,
    active_edit_id UUID,
    active_delay_cuts_url TEXT,
    active_audio_a_url TEXT,
    active_pause_cuts_audio_a_url TEXT,
    active_pause_cuts_original_url TEXT,
    active_audio_b_url TEXT,
    
    final_output_mode VARCHAR(32) DEFAULT 'original',
    feed_to_ai BOOLEAN DEFAULT TRUE,
    finalize_source_edit_id UUID,
    
    final_video_url TEXT,
    final_video_tos_key TEXT,
    final_upload_status VARCHAR(32),
    normalized_video_url TEXT,
    normalized_process_url TEXT,
    final_cut_plan_url TEXT,
    
    groundtruth_url TEXT,
    groundtruth_tos_key TEXT,
    groundtruth_upload_status VARCHAR(32),
    
    work_dir TEXT,
    processing_params JSONB,
    input_media_info JSONB,
    encoding_params JSONB,
    
    error_stage VARCHAR(32),
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_smart_cut_tasks_user_id ON smart_cut_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_smart_cut_tasks_company_id ON smart_cut_tasks(company_id);
CREATE INDEX IF NOT EXISTS idx_smart_cut_tasks_status ON smart_cut_tasks(status);
"""

SMART_CUT_EDIT_SQL = """
CREATE TABLE IF NOT EXISTS smart_cut_edits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL,
    edited_script TEXT NOT NULL,
    
    delay_cuts_url TEXT,
    audio_a_url TEXT,
    pause_cuts_audio_a_url TEXT,
    pause_cuts_original_url TEXT,
    audio_b_url TEXT,
    audio_b_tos_key TEXT,
    
    status VARCHAR(32) NOT NULL DEFAULT 'previewing',
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_task FOREIGN KEY (task_id) REFERENCES smart_cut_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_smart_cut_edits_task_id ON smart_cut_edits(task_id);
"""
