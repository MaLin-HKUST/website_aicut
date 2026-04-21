"""API Models 包初始化

导出所有 API 相关的 Pydantic 模型。
"""

from apps.api.models.schemas import (
    # F06: 创建任务
    BaseResponse,
    TaskCreateRequest,
    TaskCreateData,
    TaskCreateResponse,
    DraftCurrentResponse,
    DraftEnsureRequest,
    DraftEnsureResponse,
    TaskStatusData,
    TaskStatusResponse,
    PresignedUrlData,
    PresignedUrlResponse,
    UploadUrlInfo,
    UploadCompleteData,
    # F07/F08: 上传
    UploadPrepareResponse,
    UploadCompleteRequest,
    UploadCompleteResponse,
    # F13/F17/F19: 阶段触发
    StartAnalyzeResponse,
    PreviewRequest,
    PreviewResponse,
    FinalizeRequest,
    FinalizeResponse,
    # F14/F24: 任务详情和放弃
    TaskDetailResponse,
    TaskAbandonResponse,
    TaskNotFoundError,
    TaskCannotAbandonError,
    # 通用
    ErrorResponse,
)

__all__ = [
    # F06
    "BaseResponse",
    "TaskCreateRequest",
    "TaskCreateData",
    "TaskCreateResponse",
    "DraftCurrentResponse",
    "DraftEnsureRequest",
    "DraftEnsureResponse",
    "TaskStatusData",
    "TaskStatusResponse",
    "PresignedUrlData",
    "PresignedUrlResponse",
    "UploadUrlInfo",
    "UploadCompleteData",
    # F07/F08
    "UploadPrepareResponse",
    "UploadCompleteRequest",
    "UploadCompleteResponse",
    # F13/F17/F19
    "StartAnalyzeResponse",
    "PreviewRequest",
    "PreviewResponse",
    "FinalizeRequest",
    "FinalizeResponse",
    # F14/F24
    "TaskDetailResponse",
    "TaskAbandonResponse",
    "TaskNotFoundError",
    "TaskCannotAbandonError",
    # 通用
    "ErrorResponse",
]
