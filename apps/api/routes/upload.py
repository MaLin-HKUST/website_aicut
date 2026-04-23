"""上传相关 API 路由 - F07, F08 实现

F07: POST /api/smart-cut/tasks/{task_id}/upload-prepare
F08: POST /api/smart-cut/tasks/{task_id}/upload-complete
"""

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from configs.database import get_db
from apps.models.task import SmartCutTask, TaskStatus, CurrentStage
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskType, SchedulerTaskStatus
from apps.models.task_run import SmartCutTaskRun, TaskRunStatus, TaskRunType
from apps.services.tos_service import TOSService
from apps.api.models.schemas import (
    UploadPrepareResponse,
    UploadCompleteRequest,
    UploadCompleteResponse,
    ErrorResponse,
)

# 配置
TOS_BUCKET = os.getenv("TOS_BUCKET", "smart-cut")
URL_EXPIRE_SECONDS = int(os.getenv("UPLOAD_URL_EXPIRE_SECONDS", "3600"))

# 创建路由
router = APIRouter(prefix="/api/smart-cut/tasks", tags=["upload"])


def _next_run_sequence(db: Session, task_id: str) -> int:
    latest = (
        db.query(SmartCutTaskRun)
        .filter(SmartCutTaskRun.task_id == task_id)
        .order_by(SmartCutTaskRun.sequence_number.desc())
        .first()
    )
    return 1 if latest is None else latest.sequence_number + 1


def get_tos_service() -> TOSService:
    """获取 TOS 服务实例"""
    use_fake = os.getenv("USE_FAKE_TOS", "false").lower() == "true"
    fake_base_path = os.getenv("FAKE_TOS_BASE_PATH", "/tmp/fake_tos")
    
    if use_fake:
        return TOSService(use_fake=True, fake_base_path=fake_base_path)
    else:
        return TOSService(
            use_fake=False,
            endpoint=os.getenv("TOS_ENDPOINT"),
            region=os.getenv("TOS_REGION", "cn-beijing"),
            access_key=os.getenv("TOS_ACCESS_KEY"),
            secret_key=os.getenv("TOS_SECRET_KEY"),
        )


def _validate_key_prefix(key: str, task_id: str) -> bool:
    """验证 key 前缀是否正确
    
    key 格式必须满足: smart-cut/{task_id}/input/{filename}
    """
    expected_prefix = f"smart-cut/{task_id}/input/"
    return key.startswith(expected_prefix)


def _extract_extension(filename: str) -> str:
    """从文件名中提取扩展名"""
    if "." in filename:
        return filename.split(".")[-1].lower()
    return ""


@router.post(
    "/{task_id}/upload-prepare",
    response_model=UploadPrepareResponse,
    responses={
        404: {"model": ErrorResponse, "description": "任务不存在"},
        400: {"model": ErrorResponse, "description": "任务状态不正确"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
    summary="F07: 准备上传",
    description="为指定任务生成视频和文案的上传 URL",
)
async def upload_prepare(
    task_id: str,
    video_ext: Optional[str] = "mp4",
    db: Session = Depends(get_db),
    tos_service: TOSService = Depends(get_tos_service),
) -> UploadPrepareResponse:
    """准备上传接口
    
    验证任务存在且状态为 waiting_upload，然后生成上传 URL。
    
    Args:
        task_id: 任务 ID
        video_ext: 视频文件扩展名（默认 mp4）
        db: 数据库会话
        tos_service: TOS 服务实例
        
    Returns:
        UploadPrepareResponse: 包含上传 URL 和 key 的响应
        
    Raises:
        HTTPException: 任务不存在或状态不正确时抛出
    """
    # 1. 查询任务
    task = db.query(SmartCutTask).filter(SmartCutTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "TaskNotFound",
                "message": f"任务不存在: {task_id}",
                "task_id": task_id,
            },
        )
    
    # 2. 验证任务状态
    if task.status != TaskStatus.WAITING_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "InvalidTaskStatus",
                "message": f"任务状态不正确，当前状态: {task.status.value}，期望状态: waiting_upload",
                "task_id": task_id,
            },
        )
    
    # 3. 生成 key
    video_key = f"smart-cut/{task_id}/input/source_video.{video_ext}"
    text_key = f"smart-cut/{task_id}/input/reference.txt"
    
    # 4. 生成上传 URL
    video_result = tos_service.generate_upload_url(
        bucket=TOS_BUCKET,
        key=video_key,
        expires=URL_EXPIRE_SECONDS,
    )
    
    if not video_result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GenerateURLFailed",
                "message": f"生成视频上传 URL 失败: {video_result.error}",
                "task_id": task_id,
            },
        )
    
    text_result = tos_service.generate_upload_url(
        bucket=TOS_BUCKET,
        key=text_key,
        expires=URL_EXPIRE_SECONDS,
    )
    
    if not text_result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GenerateURLFailed",
                "message": f"生成文案上传 URL 失败: {text_result.error}",
                "task_id": task_id,
            },
        )
    
    # 5. 解析过期时间
    expires_at_str = video_result.metadata.get("expires_at")
    if expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str)
    else:
        expires_at = datetime.utcnow()
    
    # 6. 记录 prepare 信息到 task（可选，用于追踪）
    # 可以存储在 task 的某个字段中，如 metadata
    
    return UploadPrepareResponse(
        video_upload_url=video_result.data["url"],
        video_key=video_key,
        text_upload_url=text_result.data["url"],
        text_key=text_key,
        expires_at=expires_at,
    )


@router.post(
    "/{task_id}/upload-complete",
    response_model=UploadCompleteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "任务不存在"},
        400: {"model": ErrorResponse, "description": "请求参数错误或文件不存在"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
    summary="F08: 完成上传",
    description="校验已上传文件并推进任务状态到 ready_analyze",
)
async def upload_complete(
    task_id: str,
    request: UploadCompleteRequest,
    db: Session = Depends(get_db),
    tos_service: TOSService = Depends(get_tos_service),
) -> UploadCompleteResponse:
    """完成上传接口
    
    验证任务存在，校验上传的 key 是否合法且文件真实存在，
    通过后推进状态到 ready_analyze。
    
    Args:
        task_id: 任务 ID
        request: 上传完成请求，包含已上传文件的 key 列表
        db: 数据库会话
        tos_service: TOS 服务实例
        
    Returns:
        UploadCompleteResponse: 状态流转结果
        
    Raises:
        HTTPException: 任务不存在、key 不合法或文件不存在时抛出
    """
    # 1. 查询任务
    task = db.query(SmartCutTask).filter(SmartCutTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "TaskNotFound",
                "message": f"任务不存在: {task_id}",
                "task_id": task_id,
            },
        )
    
    # 2. 校验每个 key
    video_key: Optional[str] = None
    text_key: Optional[str] = None
    
    for key in request.uploaded_keys:
        # 2.1 校验 key 前缀
        if not _validate_key_prefix(key, task_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "InvalidKeyPrefix",
                    "message": f"非法的 key 前缀: {key}，必须以 smart-cut/{task_id}/input/ 开头",
                    "task_id": task_id,
                },
            )
        
        # 2.2 校验对象真实存在
        exists_result = tos_service.check_object_exists(
            bucket=TOS_BUCKET,
            key=key,
        )
        
        if not exists_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "CheckObjectFailed",
                    "message": f"检查对象存在性失败: {exists_result.error}",
                    "task_id": task_id,
                },
            )
        
        if not exists_result.data.get("exists"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ObjectNotFound",
                    "message": f"对象不存在: {key}",
                    "task_id": task_id,
                },
            )
        
        # 2.3 识别 key 类型
        if "source_video" in key:
            video_key = key
        elif "reference" in key:
            text_key = key
    
    # 3. 推进状态到 analyzing，并自动创建 analyze run + scheduler task
    if task.status not in {TaskStatus.WAITING_UPLOAD, TaskStatus.READY_ANALYZE}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "InvalidStateTransition",
                "message": f"无法从状态 {task.status.value} 继续上传并自动分析",
                "task_id": task_id,
            },
        )
    
    # 更新 task
    task.status = TaskStatus.ANALYZING
    task.current_stage = CurrentStage.ANALYZE
    
    # 更新 URL（这里使用 TOS key 作为 URL，实际可能需要生成下载 URL）
    if video_key:
        # 生成下载 URL 或直接存储 key
        download_result = tos_service.generate_download_url(
            bucket=TOS_BUCKET,
            key=video_key,
            expires=3600 * 24 * 7,  # 7天有效期
        )
        if download_result.success:
            task.original_video_url = download_result.data["url"]
    
    if text_key:
        download_result = tos_service.generate_download_url(
            bucket=TOS_BUCKET,
            key=text_key,
            expires=3600 * 24 * 7,
        )
        if download_result.success:
            task.reference_text_url = download_result.data["url"]
    
    upload_run = (
        db.query(SmartCutTaskRun)
        .filter(
            SmartCutTaskRun.task_id == task_id,
            SmartCutTaskRun.run_type == TaskRunType.UPLOAD,
        )
        .order_by(SmartCutTaskRun.sequence_number.desc())
        .first()
    )
    if upload_run is None:
        upload_run = SmartCutTaskRun(
            task_id=task_id,
            run_type=TaskRunType.UPLOAD,
            status=TaskRunStatus.SUCCESS,
            sequence_number=_next_run_sequence(db, task_id),
            payload_snapshot={"uploaded_keys": request.uploaded_keys},
            result_snapshot={"video_key": video_key, "text_key": text_key},
            completed_at=datetime.utcnow(),
        )
        db.add(upload_run)
        db.flush()
    else:
        upload_run.status = TaskRunStatus.SUCCESS
        upload_run.result_snapshot = {"video_key": video_key, "text_key": text_key}
        upload_run.completed_at = datetime.utcnow()
        upload_run.updated_at = datetime.utcnow()

    analyze_scheduler_task = SchedulerTask(
        task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
        status=SchedulerTaskStatus.PENDING,
        business_task_id=task_id,
        payload={
            "smart_cut_task_id": task_id,
            "original_video_tos_key": task.original_video_url or video_key,
            "reference_text_tos_key": task.reference_text_url or text_key,
        },
    )
    db.add(analyze_scheduler_task)
    db.flush()

    analyze_run = SmartCutTaskRun(
        task_id=task_id,
        run_type=TaskRunType.ANALYZE,
        status=TaskRunStatus.QUEUED,
        sequence_number=_next_run_sequence(db, task_id),
        scheduler_task_id=analyze_scheduler_task.id,
        payload_snapshot=dict(analyze_scheduler_task.payload),
    )
    db.add(analyze_run)
    db.flush()

    task.current_run_id = analyze_run.id
    task.latest_successful_run_id = upload_run.id

    # 提交事务
    db.commit()
    db.refresh(task)

    return UploadCompleteResponse(
        status="success",
        task_id=task_id,
        next_stage="analyze",
        message="上传完成，已自动开始分析",
    )
