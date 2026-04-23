"""API 请求/响应模型 - Pydantic Schemas

定义所有 API 端点的请求和响应数据结构。
"""

from datetime import datetime
from typing import Optional, Any, List, TypeVar, Generic
from pydantic import BaseModel, Field


T = TypeVar("T")


# ========== 基础响应封装 ==========

class BaseResponse(BaseModel, Generic[T]):
    """基础响应封装
    
    所有 API 响应的统一包装格式
    
    Attributes:
        code: 业务状态码，0 表示成功
        message: 状态描述信息
        data: 实际响应数据，类型由泛型参数决定
    """
    code: int = Field(default=0, description="业务状态码，0 表示成功")
    message: str = Field(default="success", description="状态描述信息")
    data: Optional[T] = Field(default=None, description="响应数据")

    class Config:
        """Pydantic 配置"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ========== F06: 创建任务相关模型 ==========

class TaskCreateRequest(BaseModel):
    """创建任务请求模型
    
    Attributes:
        user_id: 用户ID，可选，默认为 "anonymous"
    """
    user_id: str = Field(
        default="anonymous",
        description="用户ID，不提供则使用匿名用户"
    )
    session_scope_id: Optional[str] = Field(
        default=None,
        description="可选，显式传入当前登录会话作用域 ID"
    )
    company_id: Optional[int] = Field(
        default=None,
        description="企业ID；任务卡模型预留字段"
    )


class TaskCreateData(BaseModel):
    """创建任务响应数据
    
    Attributes:
        task_id: 任务唯一标识
        status: 任务当前状态
        created_at: 任务创建时间
    """
    task_id: str = Field(..., description="任务唯一标识")
    status: str = Field(..., description="任务当前状态")
    created_at: datetime = Field(..., description="任务创建时间")

    class Config:
        """Pydantic 配置"""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskCreateResponse(BaseResponse[TaskCreateData]):
    """创建任务响应模型
    
    创建任务成功后的标准响应格式
    
    Example:
        {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "waiting_upload",
                "created_at": "2024-01-15T10:30:00"
            }
        }
    """
    pass


class TaskStatusData(BaseModel):
    """任务状态查询响应数据"""
    task_id: str = Field(..., description="任务唯一标识")
    status: str = Field(..., description="任务当前状态")
    current_stage: str = Field(..., description="当前阶段")
    created_at: datetime = Field(..., description="任务创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")
    original_video_url: Optional[str] = Field(None, description="原始视频URL")
    reference_text_url: Optional[str] = Field(None, description="参考文案URL")
    final_video_url: Optional[str] = Field(None, description="最终视频URL")

    class Config:
        """Pydantic 配置"""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskStatusResponse(BaseResponse[TaskStatusData]):
    """任务状态查询响应模型"""
    pass


class PresignedUrlData(BaseModel):
    """预签名 URL 响应数据"""
    url: str = Field(..., description="预签名 URL")
    expires_at: str = Field(..., description="URL 过期时间")
    key: str = Field(..., description="对象在 TOS 中的 key")


class PresignedUrlResponse(BaseResponse[PresignedUrlData]):
    """预签名 URL 响应模型"""
    pass


class UploadUrlInfo(BaseModel):
    """上传URL信息"""
    url: str = Field(..., description="预签名上传URL")
    key: str = Field(..., description="对象在TOS中的key")
    expires_at: str = Field(..., description="URL过期时间(ISO格式)")


class UploadCompleteData(BaseModel):
    """上传完成响应数据"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务新状态")
    original_video_url: str = Field(..., description="原始视频URL")
    reference_text_url: str = Field(..., description="参考文案URL")


# ========== F07: Upload Prepare ==========

class UploadPrepareResponse(BaseModel):
    """F07: 上传准备响应
    
    返回视频和文案的上传 URL 和 key。
    """
    video_upload_url: str = Field(..., description="视频上传 URL（预签名）")
    video_key: str = Field(..., description="视频 TOS key")
    text_upload_url: str = Field(..., description="文案上传 URL（预签名）")
    text_key: str = Field(..., description="文案 TOS key")
    expires_at: datetime = Field(..., description="上传 URL 过期时间")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "video_upload_url": "https://tos.example.com/...",
                "video_key": "smart-cut/task-xxx/input/source_video.mp4",
                "text_upload_url": "https://tos.example.com/...",
                "text_key": "smart-cut/task-xxx/input/reference.txt",
                "expires_at": "2024-01-01T12:00:00"
            }
        }
    }


# ========== F08: Upload Complete ==========

class UploadCompleteRequest(BaseModel):
    """F08: 上传完成请求
    
    用户上传完成后，通知服务端校验文件。
    """
    uploaded_keys: List[str] = Field(
        ...,
        description="已上传的文件 key 列表",
        min_length=1
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "uploaded_keys": [
                    "smart-cut/task-xxx/input/source_video.mp4",
                    "smart-cut/task-xxx/input/reference.txt"
                ]
            }
        }
    }


class UploadCompleteResponse(BaseModel):
    """F08: 上传完成响应
    
    返回状态流转结果和下一步信息。
    """
    status: str = Field(..., description="处理状态: success / failed")
    task_id: str = Field(..., description="任务 ID")
    next_stage: str = Field(..., description="下一阶段: analyze")
    message: Optional[str] = Field(None, description="状态说明")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "task_id": "task-xxx",
                "next_stage": "analyze",
                "message": "上传完成，准备分析"
            }
        }
    }


# ========== F13: Start Analyze ==========

class StartAnalyzeResponse(BaseModel):
    """触发分析响应"""
    scheduler_task_id: str = Field(..., description="调度任务ID")
    status: str = Field(..., description="任务状态")


# ========== F14: Task Detail ==========

class TaskDetailResponse(BaseModel):
    """任务详情响应"""
    # 基本信息
    id: str = Field(..., description="任务ID")
    user_id: str = Field(..., description="用户ID")
    company_id: Optional[int] = Field(None, description="企业ID")
    status: str = Field(..., description="任务状态")
    current_stage: str = Field(..., description="当前阶段")
    task_title: Optional[str] = Field(None, description="任务中心标题")
    visible_in_task_center: bool = Field(False, description="是否在任务中心可见")
    session_scope_id: Optional[str] = Field(None, description="当前登录会话作用域 ID")
    current_run_id: Optional[str] = Field(None, description="当前活跃 run ID")
    latest_successful_run_id: Optional[str] = Field(None, description="最近成功 run ID")
    failed_stage: Optional[str] = Field(None, description="最近失败阶段")
    revision_count: int = Field(0, description="累计修订次数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 输入
    original_video_url: Optional[str] = Field(None, description="原始视频URL")
    reference_text_url: Optional[str] = Field(None, description="参考文案URL")
    
    # Analyze 产物
    analyze_script: Optional[Any] = Field(None, description="分析生成的脚本")
    asr_result_tos_key: Optional[str] = Field(None, description="ASR结果TOS Key")
    
    # 当前 Edit
    active_edit_id: Optional[str] = Field(None, description="当前生效的edit ID")
    current_edited_script: Optional[Any] = Field(None, description="当前编辑的脚本")
    audio_b_url: Optional[str] = Field(None, description="B轨音频URL")
    error_message: Optional[str] = Field(None, description="当前错误信息")
    
    # Finalize 产物
    final_video_url: Optional[str] = Field(None, description="最终视频URL")
    groundtruth_url: Optional[str] = Field(None, description="Ground Truth视频URL")
    groundtruth_saved: bool = Field(False, description="Ground Truth是否已保存")


# ========== F17: Start Preview ==========

class PreviewRequest(BaseModel):
    """触发预览请求"""
    edited_script: str = Field(..., description="用户编辑后的大括号格式脚本")


class PreviewResponse(BaseModel):
    """触发预览响应"""
    edit_id: str = Field(..., description="Edit记录ID")
    scheduler_task_id: str = Field(..., description="调度任务ID")
    status: str = Field(..., description="任务状态")


# ========== F19: Start Finalize ==========

class FinalizeRequest(BaseModel):
    """触发最终生成请求"""
    output_mode: str = Field(..., description="输出模式: original | vertical_1080p")
    feed_to_ai: bool = Field(..., description="是否喂给AI训练")
    edit_id: Optional[str] = Field(None, description="可选，指定使用哪个edit记录，默认使用最后一次成功的edit")


class FinalizeResponse(BaseModel):
    """触发最终生成响应"""
    scheduler_task_id: str = Field(..., description="调度任务ID")
    status: str = Field(..., description="任务状态")
    visible_in_task_center: bool = Field(..., description="任务是否已进入任务中心")
    task_title: str = Field(..., description="最终写入的任务标题")


# ========== F24: Abandon Task ==========

class TaskAbandonResponse(BaseModel):
    """放弃任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    abandoned_at: datetime = Field(..., description="放弃时间")


# ========== 错误响应 ==========

class ErrorResponse(BaseModel):
    """通用错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误描述")
    task_id: Optional[str] = Field(None, description="关联的任务 ID")


class TaskNotFoundError(BaseModel):
    """任务不存在错误"""
    detail: str = Field(..., description="错误详情")


class TaskCannotAbandonError(BaseModel):
    """任务无法放弃错误"""
    detail: str = Field(..., description="错误详情")


class SmartCutTaskSummaryRead(BaseModel):
    """Smart Cut 任务摘要 - 用于 landing 页和轻量列表。"""

    id: str = Field(..., description="任务 ID")
    company_id: Optional[int] = Field(None, description="企业 ID")
    status: str = Field(..., description="任务状态")
    current_stage: Optional[str] = Field(None, description="当前阶段")
    active_edit_id: Optional[str] = Field(None, description="当前 edit ID")
    visible_in_task_center: bool = Field(False, description="是否在任务中心可见")
    session_scope_id: Optional[str] = Field(None, description="当前登录会话作用域 ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class TaskStartRequest(BaseModel):
    """显式开启主任务卡请求。"""

    user_id: str = Field(..., description="用户ID")
    company_id: Optional[int] = Field(None, description="企业ID")
    task_title: Optional[str] = Field(None, description="可选任务标题")


class TaskStartResponse(BaseModel):
    """显式开启主任务卡响应。"""

    task_id: str = Field(..., description="主任务ID")
    status: str = Field(..., description="任务状态")
    current_stage: str = Field(..., description="当前阶段")
    company_id: Optional[int] = Field(None, description="企业ID")
    task_title: str = Field(..., description="任务标题")
    created_at: datetime = Field(..., description="创建时间")


class DraftCurrentResponse(BaseModel):
    """当前登录会话草稿查询结果。"""

    session_scope_id: str = Field(..., description="当前登录会话作用域 ID")
    task: Optional[TaskDetailResponse] = Field(None, description="当前会话的隐藏草稿；为空表示不存在")


class DraftEnsureRequest(TaskCreateRequest):
    """确保当前登录会话草稿存在。"""


class DraftEnsureResponse(BaseModel):
    """确保当前登录会话草稿存在的结果。"""

    session_scope_id: str = Field(..., description="当前登录会话作用域 ID")
    created: bool = Field(..., description="本次是否新建了隐藏草稿")
    task: TaskDetailResponse = Field(..., description="当前登录会话的隐藏草稿")


class SmartCutEditRead(BaseModel):
    """Smart Cut Edit 只读响应。"""

    id: str = Field(..., description="Edit ID")
    task_id: str = Field(..., description="任务 ID")
    edited_script: Any = Field(..., description="编辑后的脚本")
    status: str = Field(..., description="Edit 状态")
    audio_a_url: Optional[str] = Field(None, description="Analyze 阶段音频")
    audio_b_url: Optional[str] = Field(None, description="Preview 阶段音频")
    edited_delay_cuts_tos_key: Optional[str] = Field(None, description="Preview 阶段 delay cuts")
    pause_cuts_on_original_tos_key: Optional[str] = Field(None, description="Preview 阶段 pause cuts")
    error_message: Optional[str] = Field(None, description="错误信息")
    version_number: int = Field(..., description="版本号")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class TaskRunRead(BaseModel):
    """主任务子执行记录。"""

    id: str = Field(..., description="run ID")
    task_id: str = Field(..., description="主任务ID")
    run_type: str = Field(..., description="执行类型")
    status: str = Field(..., description="执行状态")
    sequence_number: int = Field(..., description="顺序号")
    scheduler_task_id: Optional[str] = Field(None, description="底层调度任务ID")
    source_edit_id: Optional[str] = Field(None, description="来源 edit ID")
    payload_snapshot: Any = Field(..., description="请求快照")
    result_snapshot: Optional[Any] = Field(None, description="结果快照")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    updated_at: datetime = Field(..., description="更新时间")


class TaskCenterTaskRead(BaseModel):
    """任务中心列表项。当前版本底层数据源为 Smart Cut。"""

    id: str = Field(..., description="任务 ID")
    title: str = Field(..., description="任务标题")
    task_type: str = Field(..., description="任务类型")
    status: str = Field(..., description="任务中心状态")
    current_stage: str = Field(..., description="当前阶段")
    progress: int = Field(..., ge=0, le=100, description="进度百分比")
    progress_detail: Optional[str] = Field(None, description="详细进度描述")
    updated_at: datetime = Field(..., description="更新时间")
    created_at: datetime = Field(..., description="创建时间")
    queue_position: Optional[int] = Field(None, description="队列位置")
    download_url: Optional[str] = Field(None, description="下载地址")
    error_message: Optional[str] = Field(None, description="错误信息")
    input_files: List[str] = Field(default_factory=list, description="输入文件摘要")
    output_files: List[str] = Field(default_factory=list, description="输出文件摘要")
    user_id: Optional[str] = Field(None, description="用户 ID（admin 可见）")
    company_id: Optional[int] = Field(None, description="企业 ID（admin 或新任务卡模型可见）")
    scheduler_task_id: Optional[str] = Field(None, description="最近一次调度任务 ID（admin 可见）")
    scheduler_status: Optional[str] = Field(None, description="最近一次调度任务状态（admin 可见）")
    worker_id: Optional[str] = Field(None, description="当前/最近一次 Worker（admin 可见）")
