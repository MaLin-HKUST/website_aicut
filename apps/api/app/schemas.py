from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Role = Literal["admin", "user"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class AuthUser(BaseModel):
    id: int
    username: str
    role: Role
    company_id: int | None
    company_name: str | None = None


class AuthResponse(BaseModel):
    user: AuthUser


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=200)
    role: Role = "user"
    company_id: int | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role
    company_id: int | None
    company_name: str | None = None
    created_at: datetime


class MaterialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    company_id: int
    remark: str | None = Field(default=None, max_length=1000)


class MaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company_id: int
    company_name: str
    remark: str | None
    created_at: datetime


class TTSGenerateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=9999)


class TTSGenerateResponse(BaseModel):
    audio_base64: str
    mime_type: str
    file_name: str
    usage_credits: int
    usage_characters: int
    monthly_total_used: int  # 本月累计消耗
    monthly_limit: int | None  # 月度限额（如果有）


# User Usage Monthly
class UserUsageMonthlyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    year_month: str
    credits_used: int
    credits_limit: int | None
    created_at: datetime
    last_updated: datetime


class UserUsageMonthlyUpdate(BaseModel):
    """管理员更新用户月度限额."""
    credits_limit: int | None = None


class UserUsageMonthlyAdjust(BaseModel):
    """管理员手动调整用户已消耗额度（正数为增加，负数为减少）."""
    delta: int = Field(..., description="调整值（正数为增加，负数为减少）")


class SchedulerTaskCreate(BaseModel):
    page_key: str = Field(min_length=1, max_length=100)
    task_type: str = Field(min_length=1, max_length=100)
    step_total: int = Field(default=1, ge=1, le=20)
    needs_post: bool = False
    input_payload: dict | None = None


class SchedulerTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    user_id: int
    page_key: str
    task_type: str
    status: str
    assigned_worker_id: str | None
    step_index: int
    step_total: int
    workspace_uri: str | None
    input_payload: dict | None = None
    output_payload: dict | None = None
    keep_until: datetime | None
    needs_post: bool
    last_error_code: str | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime


class SchedulerResumeEntry(BaseModel):
    has_resume_task: bool
    task: SchedulerTaskRead | None = None


class SchedulerWorkerCreate(BaseModel):
    worker_id: str = Field(min_length=1, max_length=100)
    worker_name: str = Field(min_length=1, max_length=255)
    supported_task_types: list[str] = Field(default_factory=list)


class SchedulerWorkerStatusUpdate(BaseModel):
    status: str
    current_task_id: str | None = None


class SchedulerWorkerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    worker_id: str
    worker_name: str
    supported_task_types: list[str]
    status: str
    current_task_id: str | None
    heartbeat_at: datetime
    created_at: datetime


class SchedulerAlarmRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alarm_type: str
    task_id: str | None
    worker_id: str | None
    current_state: str
    message: str
    handled: bool
    created_at: datetime


# ============================================
# Smart Cut Scheduler Schemas (F02)
# ============================================

class SmartCutTaskCreate(BaseModel):
    """创建 Smart Cut 业务任务"""
    user_id: int


class SmartCutTaskRead(BaseModel):
    """读取 Smart Cut 业务任务"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    status: str
    current_stage: str | None
    error_stage: str | None
    error_message: str | None

    # 输入
    original_video_url: str | None
    original_video_tos_key: str | None
    reference_text_url: str | None
    reference_text_tos_key: str | None

    # analyze 产物
    analyze_script: str | None
    analyze_script_tos_key: str | None
    asr_result_tos_key: str | None

    # edit 关联
    active_edit_id: str | None
    finalize_source_edit_id: str | None

    # finalize 产物
    final_video_url: str | None
    final_video_tos_key: str | None
    groundtruth_url: str | None
    groundtruth_tos_key: str | None

    # 配置
    feed_to_ai: bool
    output_mode: str | None

    # 调度关联
    last_scheduler_task_id: str | None

    created_at: datetime
    updated_at: datetime


class SmartCutTaskSummary(BaseModel):
    """任务列表摘要"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    current_stage: str | None
    active_edit_id: str | None
    created_at: datetime
    updated_at: datetime


class SmartCutUploadPrepareResponse(BaseModel):
    """upload-prepare 返回的上传参数"""
    task_id: str
    video_upload_key: str
    text_upload_key: str
    upload_url: str | None = None  # 真实 TOS 预签名 URL


class SmartCutUploadCompleteRequest(BaseModel):
    """upload-complete 请求"""
    video_key: str
    text_key: str


class SmartCutUploadCompleteResponse(BaseModel):
    """upload-complete 响应"""
    success: bool
    message: str


class SmartCutAnalyzeRequest(BaseModel):
    """触发 analyze 阶段"""
    pass


class SmartCutPreviewRequest(BaseModel):
    """触发 preview 阶段"""
    edited_script: str = Field(min_length=1)


class SmartCutFinalizeRequest(BaseModel):
    """触发 finalize 阶段"""
    output_mode: Literal["original", "vertical_1080p"] = "original"
    feed_to_ai: bool = False


class SmartCutEditRead(BaseModel):
    """读取 Preview Edit 记录"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    edited_script: str
    status: str
    audio_b_url: str | None
    audio_b_tos_key: str | None
    edited_delay_cuts_tos_key: str | None
    pause_cuts_on_original_tos_key: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class SmartCutEditSummary(BaseModel):
    """Edit 列表摘要"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    created_at: datetime
    updated_at: datetime


class SmartCutTaskDetailWithEdits(SmartCutTaskRead):
    """任务详情包含 edits 历史"""
    edits: list[SmartCutEditSummary] = []
