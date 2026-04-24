"""Smart Cut API - 任务管理路由

F06: POST /api/smart-cut/tasks - 创建任务
F14: GET /api/smart-cut/tasks/{task_id} - 查询任务详情
F24: POST /api/smart-cut/tasks/{task_id}/abandon - 放弃任务
F25: Fake TOS 实现
F26: Cleanup 机制
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from typing import Any, Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from configs.database import get_db
from apps.models.task import SmartCutTask, TaskStatus, CurrentStage
from apps.models.edit import SmartCutEdit
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskType, SchedulerTaskStatus
from apps.models.task_run import SmartCutTaskRun, TaskRunType, TaskRunStatus
from apps.api.dependencies import get_tos_service
from apps.api.models.schemas import (
    SmartCutEditRead,
    SmartCutTaskSummaryRead,
    TaskCenterTaskRead,
    TaskCreateRequest,
    TaskCreateData,
    TaskCreateResponse,
    DraftCurrentResponse,
    DraftEnsureRequest,
    DraftEnsureResponse,
    TaskStartRequest,
    TaskStartResponse,
    TaskRunRead,
    TaskStatusData,
    TaskStatusResponse,
    PresignedUrlData,
    PresignedUrlResponse,
    TaskDetailResponse,
    TaskAbandonResponse,
    TaskNotFoundError,
    TaskCannotAbandonError,
)
from apps.services.tos_service import TOSService
from apps.services.cleanup_service import create_cleanup_service
from apps.services.smart_cut_contract import resolve_session_scope_id


router = APIRouter(
    prefix="/api/smart-cut/tasks",
    tags=["tasks"],
    responses={404: {"model": TaskNotFoundError, "description": "任务不存在"}}
)

TOS_BUCKET = os.getenv("TOS_BUCKET", "smart-cut")


def _script_to_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("segments"), list):
        parts: list[str] = []
        for segment in value["segments"]:
            if isinstance(segment, str):
                parts.append(segment)
            elif isinstance(segment, dict):
                parts.append(str(segment.get("text", "")))
        if parts:
            return "".join(parts)
    return json.dumps(value, ensure_ascii=False)


def _basename(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    parsed = urlparse(value)
    source = parsed.path or value
    return source.rstrip("/").split("/")[-1] or fallback


def _latest_scheduler_task(db: Session, task_id: str) -> SchedulerTask | None:
    return db.execute(
        select(SchedulerTask)
        .where(SchedulerTask.business_task_id == task_id)
        .order_by(desc(SchedulerTask.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _task_error_message(task: SmartCutTask, scheduler_task: SchedulerTask | None) -> str | None:
    if scheduler_task and scheduler_task.error_message:
        return scheduler_task.error_message
    if task.status in {
        TaskStatus.ANALYZE_FAILED,
        TaskStatus.PREVIEW_FAILED,
        TaskStatus.FINALIZE_FAILED,
    }:
        return f"{task.status.value} without detailed scheduler error"
    return None


def _build_task_detail(
    db: Session,
    task: SmartCutTask,
) -> TaskDetailResponse:
    current_edited_script: Any = None
    audio_b_url: str | None = None
    error_message: str | None = None

    edit = None
    if task.active_edit_id:
        edit = db.query(SmartCutEdit).filter(SmartCutEdit.id == task.active_edit_id).first()
    elif task.edits:
        edit = (
            db.query(SmartCutEdit)
            .filter(SmartCutEdit.task_id == task.id)
            .order_by(desc(SmartCutEdit.version_number))
            .first()
        )

    if edit:
        current_edited_script = edit.edited_script
        audio_b_url = edit.audio_b_url

    scheduler_task = _latest_scheduler_task(db, task.id)
    error_message = error_message or _task_error_message(task, scheduler_task)
    groundtruth_saved = bool(task.groundtruth_url and task.groundtruth_upload_status == "completed")
    final_video_url = task.final_video_url if task.status == TaskStatus.SUCCESS else None

    return TaskDetailResponse(
        id=task.id,
        user_id=task.user_id,
        company_id=task.company_id,
        status=task.status.value,
        current_stage=task.current_stage.value,
        task_title=task.task_title,
        visible_in_task_center=task.visible_in_task_center,
        session_scope_id=task.session_scope_id,
        current_run_id=task.current_run_id,
        latest_successful_run_id=task.latest_successful_run_id,
        failed_stage=task.failed_stage,
        revision_count=task.revision_count,
        created_at=task.created_at,
        updated_at=task.updated_at,
        original_video_url=task.original_video_url,
        reference_text_url=task.reference_text_url,
        analyze_script=task.analyze_script,
        asr_result_tos_key=task.asr_result_tos_key,
        active_edit_id=task.active_edit_id,
        current_edited_script=current_edited_script,
        audio_b_url=audio_b_url,
        final_video_url=final_video_url,
        groundtruth_url=task.groundtruth_url,
        groundtruth_saved=groundtruth_saved,
        error_message=error_message,
    )


def _build_task_summary(task: SmartCutTask) -> SmartCutTaskSummaryRead:
    return SmartCutTaskSummaryRead(
        id=task.id,
        company_id=task.company_id,
        status=task.status.value,
        current_stage=task.current_stage.value if task.current_stage else None,
        active_edit_id=task.active_edit_id,
        visible_in_task_center=task.visible_in_task_center,
        session_scope_id=task.session_scope_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _serialize_edit(edit: SmartCutEdit) -> SmartCutEditRead:
    return SmartCutEditRead(
        id=edit.id,
        task_id=edit.task_id,
        edited_script=edit.edited_script,
        status=edit.status.value,
        audio_a_url=edit.audio_a_url,
        audio_b_url=edit.audio_b_url,
        edited_delay_cuts_tos_key=edit.delay_cuts_tos_key,
        pause_cuts_on_original_tos_key=edit.pause_cuts_tos_key,
        error_message=None,
        version_number=edit.version_number,
        created_at=edit.created_at,
        updated_at=edit.updated_at,
    )


def _serialize_run(run: SmartCutTaskRun) -> TaskRunRead:
    return TaskRunRead(
        id=run.id,
        task_id=run.task_id,
        run_type=run.run_type.value,
        status=run.status.value,
        sequence_number=run.sequence_number,
        scheduler_task_id=run.scheduler_task_id,
        source_edit_id=run.source_edit_id,
        payload_snapshot=run.payload_snapshot,
        result_snapshot=run.result_snapshot,
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        updated_at=run.updated_at,
    )


def _task_center_status(task: SmartCutTask) -> str:
    if task.status == TaskStatus.SUCCESS:
        return "finished"
    if task.status in {TaskStatus.ANALYZE_FAILED, TaskStatus.PREVIEW_FAILED, TaskStatus.FINALIZE_FAILED, TaskStatus.ABANDONED}:
        return "failed"
    if task.status in {TaskStatus.WAITING_UPLOAD, TaskStatus.READY_ANALYZE}:
        return "queued"
    if task.status == TaskStatus.WAITING_USER:
        return "waiting"
    return "running"


def _task_center_progress(task: SmartCutTask) -> tuple[int, str]:
    mapping = {
        TaskStatus.WAITING_UPLOAD: (5, "Waiting for upload"),
        TaskStatus.READY_ANALYZE: (15, "Ready for analyze"),
        TaskStatus.ANALYZING: (35, "Analyze running"),
        TaskStatus.WAITING_USER: (65, "Waiting for user confirmation"),
        TaskStatus.PREVIEWING: (75, "Preview rendering"),
        TaskStatus.FINALIZING: (90, "Final video rendering"),
        TaskStatus.SUCCESS: (100, "Done"),
        TaskStatus.ANALYZE_FAILED: (35, "Analyze failed"),
        TaskStatus.PREVIEW_FAILED: (75, "Preview failed"),
        TaskStatus.FINALIZE_FAILED: (90, "Finalize failed"),
        TaskStatus.ABANDONED: (0, "Abandoned"),
    }
    return mapping.get(task.status, (0, task.status.value))


def _normalize_scheduler_status(value: object | None) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(getattr(value, "value")).lower()
    return str(value).lower()


def build_task_center_item(
    db: Session,
    task: SmartCutTask,
    *,
    include_admin_fields: bool,
    queue_position: int | None = None,
) -> TaskCenterTaskRead:
    scheduler_task = _latest_scheduler_task(db, task.id)
    progress, progress_detail = _task_center_progress(task)
    title = task.task_title or _basename(task.original_video_url, f"smart-cut-{task.id[:8]}")
    input_files = [
        _basename(task.original_video_url, "source_video"),
        _basename(task.reference_text_url, "reference.txt"),
    ]
    output_files: list[str] = []
    if task.asr_result_tos_key:
        output_files.append(_basename(task.asr_result_tos_key, "asr_result.json"))
    if task.final_video_url:
        output_files.append(_basename(task.final_video_url, "final_video.mp4"))

    task_center_status = _task_center_status(task)
    scheduler_status = _normalize_scheduler_status(scheduler_task.status if scheduler_task else None)
    if scheduler_status == "pending":
        task_center_status = "queued"
        progress = 20
        progress_detail = "Queued for worker"
    elif scheduler_status in {"assigned", "running", "post"}:
        task_center_status = "running"

    return TaskCenterTaskRead(
        id=task.id,
        title=title,
        task_type="smart_cut",
        status=task_center_status,
        current_stage=task.current_stage.value if task.current_stage else task.status.value,
        progress=progress,
        progress_detail=progress_detail,
        updated_at=task.updated_at,
        created_at=task.created_at,
        queue_position=queue_position if task_center_status == "queued" else None,
        download_url=task.final_video_url,
        error_message=_task_error_message(task, scheduler_task),
        input_files=[item for item in input_files if item],
        output_files=output_files,
        user_id=task.user_id if include_admin_fields else None,
        company_id=task.company_id if (include_admin_fields or task.company_id is not None) else None,
        scheduler_task_id=scheduler_task.id if include_admin_fields and scheduler_task else None,
        scheduler_status=scheduler_status if include_admin_fields and scheduler_task else None,
        worker_id=scheduler_task.assigned_worker_id if include_admin_fields and scheduler_task else None,
    )


def _next_run_sequence(db: Session, task_id: str) -> int:
    latest = db.execute(
        select(SmartCutTaskRun)
        .where(SmartCutTaskRun.task_id == task_id)
        .order_by(desc(SmartCutTaskRun.sequence_number))
        .limit(1)
    ).scalar_one_or_none()
    if latest is None:
        return 1
    return latest.sequence_number + 1


def _default_task_title() -> str:
    return f"智能剪气口-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


# ============ F06: 创建任务 ============

@router.post(
    "/start",
    response_model=TaskStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="显式开启 Smart Cut 主任务",
    description="任务卡模型入口：显式创建一个可见主任务卡，并初始化首条 upload run。",
)
async def start_task(
    payload: TaskStartRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TaskStartResponse:
    title = payload.task_title or _default_task_title()
    task = SmartCutTask(
        user_id=payload.user_id,
        company_id=payload.company_id,
        status=TaskStatus.WAITING_UPLOAD,
        current_stage=CurrentStage.UPLOAD,
        task_title=title,
        visible_in_task_center=True,
        revision_count=0,
    )
    db.add(task)
    db.flush()

    run = SmartCutTaskRun(
        task_id=task.id,
        run_type=TaskRunType.UPLOAD,
        status=TaskRunStatus.CREATED,
        sequence_number=_next_run_sequence(db, task.id),
        payload_snapshot={"source": "start_task"},
    )
    db.add(run)
    db.flush()

    task.current_run_id = run.id
    db.commit()
    db.refresh(task)

    return TaskStartResponse(
        task_id=task.id,
        status=task.status.value,
        current_stage=task.current_stage.value,
        company_id=task.company_id,
        task_title=task.task_title or title,
        created_at=task.created_at,
    )

@router.post(
    "",
    response_model=TaskCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建 Smart Cut 任务",
    description="""
    创建一个新的 Smart Cut 任务。
    
    任务创建后初始状态为 `waiting_upload`，用户需要：
    1. 调用获取上传 URL 接口上传视频和文案
    2. 确认上传完成后，任务状态会自动变为 `ready_analyze`
    3. 系统会自动开始分析处理
    
    **注意**: 当前版本 user_id 暂时使用 "anonymous"，后续版本将接入用户认证系统。
    """,
    responses={
        201: {"description": "任务创建成功"},
        500: {"description": "服务器内部错误"},
    },
)
async def create_task(
    http_request: Request,
    request: TaskCreateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TaskCreateResponse:
    """创建新的 Smart Cut 任务
    
    Args:
        request: 创建任务请求，包含可选的 user_id
        db: 数据库会话
        
    Returns:
        TaskCreateResponse: 包含新创建任务的 ID、状态和创建时间
        
    Raises:
        HTTPException: 当数据库操作失败时抛出 500 错误
    """
    try:
        session_scope_id = resolve_session_scope_id(
            request=http_request,
            explicit_scope_id=request.session_scope_id,
            required=False,
        )

        # 创建新任务
        task = SmartCutTask(
            user_id=request.user_id,
            status=TaskStatus.WAITING_UPLOAD,
            current_stage=CurrentStage.UPLOAD,
            visible_in_task_center=False,
            session_scope_id=session_scope_id,
        )
        
        # 保存到数据库
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # 构建响应
        return TaskCreateResponse(
            code=0,
            message="success",
            data=TaskCreateData(
                task_id=task.id,
                status=task.status.value,
                created_at=task.created_at,
            )
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@router.get(
    "/draft/current",
    response_model=DraftCurrentResponse,
    summary="[已废弃] 查询当前登录会话草稿",
    description="此接口已退役。请使用 POST /api/smart-cut/tasks/start 替代。",
    deprecated=True,
)
async def get_current_draft(
    http_request: Request,
    db: Annotated[Session, Depends(get_db)],
    user_id: str = Query(..., description="用户 ID"),
) -> DraftCurrentResponse:
    raise HTTPException(
        status_code=410,
        detail="This endpoint is retired. Use POST /api/smart-cut/tasks/start instead.",
    )


@router.post(
    "/draft/current/ensure",
    response_model=DraftEnsureResponse,
    summary="[已废弃] 确保当前登录会话草稿存在",
    description="此接口已退役。请使用 POST /api/smart-cut/tasks/start 替代。",
    deprecated=True,
)
async def ensure_current_draft(
    payload: DraftEnsureRequest,
    http_request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> DraftEnsureResponse:
    raise HTTPException(
        status_code=410,
        detail="This endpoint is retired. Use POST /api/smart-cut/tasks/start instead.",
    )


@router.get(
    "",
    response_model=list[SmartCutTaskSummaryRead],
    summary="列出 Smart Cut 任务",
    description="用于 Smart Cut landing 的轻量任务列表。",
)
async def list_tasks(
    db: Annotated[Session, Depends(get_db)],
    user_id: str | None = Query(default=None, description="用户 ID；为空时返回全部任务"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SmartCutTaskSummaryRead]:
    stmt = select(SmartCutTask).order_by(desc(SmartCutTask.updated_at)).limit(limit)
    if user_id:
        stmt = stmt.where(SmartCutTask.user_id == user_id)
    tasks = list(db.execute(stmt).scalars().all())
    return [_build_task_summary(task) for task in tasks]


@router.get(
    "/{task_id}/edits",
    response_model=list[SmartCutEditRead],
    summary="列出任务的编辑历史",
)
async def list_task_edits(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[SmartCutEditRead]:
    task = db.get(SmartCutTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    edits = list(
        db.execute(
            select(SmartCutEdit)
            .where(SmartCutEdit.task_id == task_id)
            .order_by(desc(SmartCutEdit.version_number))
        ).scalars().all()
    )
    return [_serialize_edit(edit) for edit in edits]


@router.get(
    "/{task_id}/runs",
    response_model=list[TaskRunRead],
    summary="列出任务的子执行记录",
)
async def list_task_runs(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[TaskRunRead]:
    task = db.get(SmartCutTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    runs = list(
        db.execute(
            select(SmartCutTaskRun)
            .where(SmartCutTaskRun.task_id == task_id)
            .order_by(SmartCutTaskRun.sequence_number.asc(), SmartCutTaskRun.created_at.asc())
        ).scalars().all()
    )
    return [_serialize_run(run) for run in runs]


@router.post(
    "/{task_id}/upload-direct",
    response_model=TaskDetailResponse,
    summary="直接上传输入文件",
    description="为前端提供一跳式上传接口，内部完成 TOS 上传并推进到 ready_analyze。",
)
async def upload_direct(
    task_id: str,
    video_file: UploadFile = File(...),
    reference_file: UploadFile = File(...),
    db: Annotated[Session, Depends(get_db)] = None,
    tos: Annotated[TOSService, Depends(get_tos_service)] = None,
) -> TaskDetailResponse:
    task = db.get(SmartCutTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.status != TaskStatus.WAITING_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务状态不正确，当前状态: {task.status.value}，期望状态: waiting_upload",
        )

    video_suffix = os.path.splitext(video_file.filename or "source_video.mp4")[1] or ".mp4"
    video_key = f"smart-cut/{task_id}/input/source_video{video_suffix}"
    text_key = f"smart-cut/{task_id}/input/reference.txt"

    temp_paths: list[str] = []
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=video_suffix) as video_tmp:
            video_tmp.write(await video_file.read())
            temp_paths.append(video_tmp.name)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as text_tmp:
            text_tmp.write(await reference_file.read())
            temp_paths.append(text_tmp.name)

        video_result = tos.upload_file(TOS_BUCKET, video_key, temp_paths[0])
        if not video_result.success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=video_result.error)
        text_result = tos.upload_file(TOS_BUCKET, text_key, temp_paths[1])
        if not text_result.success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=text_result.error)

        task.original_video_url = video_key
        task.reference_text_url = text_key
        task.status = TaskStatus.ANALYZING
        task.current_stage = CurrentStage.ANALYZE
        task.updated_at = datetime.utcnow()

        upload_run = (
            db.query(SmartCutTaskRun)
            .filter(
                SmartCutTaskRun.task_id == task_id,
                SmartCutTaskRun.run_type == TaskRunType.UPLOAD,
            )
            .order_by(desc(SmartCutTaskRun.sequence_number))
            .first()
        )
        if upload_run is None:
            upload_run = SmartCutTaskRun(
                task_id=task_id,
                run_type=TaskRunType.UPLOAD,
                status=TaskRunStatus.SUCCESS,
                sequence_number=_next_run_sequence(db, task_id),
                payload_snapshot={
                    "video_file": video_file.filename,
                    "reference_file": reference_file.filename,
                },
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

        scheduler_task = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
            status=SchedulerTaskStatus.PENDING,
            business_task_id=task_id,
            payload={
                "smart_cut_task_id": task_id,
                "original_video_tos_key": task.original_video_url,
                "reference_text_tos_key": task.reference_text_url,
            },
        )
        db.add(scheduler_task)
        db.flush()

        analyze_run = SmartCutTaskRun(
            task_id=task_id,
            run_type=TaskRunType.ANALYZE,
            status=TaskRunStatus.QUEUED,
            sequence_number=_next_run_sequence(db, task_id),
            scheduler_task_id=scheduler_task.id,
            payload_snapshot=dict(scheduler_task.payload),
        )
        db.add(analyze_run)
        db.flush()

        task.current_run_id = analyze_run.id
        task.latest_successful_run_id = upload_run.id
        db.commit()
        db.refresh(task)
        return _build_task_detail(db, task)
    finally:
        for path in temp_paths:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass


@router.get(
    "/{task_id}/status",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="查询任务状态",
    description="获取指定任务的详细状态和当前阶段信息",
    responses={
        200: {"description": "查询成功"},
        404: {"description": "任务不存在"},
    },
)
async def get_task_status(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> TaskStatusResponse:
    """查询任务状态
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        
    Returns:
        TaskStatusResponse: 任务详细信息
        
    Raises:
        HTTPException: 当任务不存在时抛出 404 错误
    """
    task = db.query(SmartCutTask).filter(SmartCutTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}"
        )
    
    return TaskStatusResponse(
        code=0,
        message="success",
        data=TaskStatusData(
            task_id=task.id,
            status=task.status.value,
            current_stage=task.current_stage.value,
            created_at=task.created_at,
            updated_at=task.updated_at,
            original_video_url=task.original_video_url,
            reference_text_url=task.reference_text_url,
            final_video_url=task.final_video_url,
        )
    )


@router.get(
    "/{task_id}/upload-url",
    response_model=PresignedUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="获取视频上传 URL",
    description="获取用于上传原始视频的预签名 URL",
    responses={
        200: {"description": "获取成功"},
        404: {"description": "任务不存在"},
    },
)
async def get_video_upload_url(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
    tos: Annotated[TOSService, Depends(get_tos_service)],
) -> PresignedUrlResponse:
    """获取视频上传 URL
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        tos: TOS 服务实例
        
    Returns:
        PresignedUrlResponse: 预签名上传 URL
    """
    # 验证任务存在
    task = db.query(SmartCutTask).filter(SmartCutTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}"
        )
    
    # 生成上传 key
    key = f"tasks/{task_id}/original_video.mp4"
    
    # 生成预签名 URL
    result = tos.generate_upload_url(
        bucket="smart-cut-uploads",
        key=key,
        expires=3600,
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {result.error}"
        )
    
    return PresignedUrlResponse(
        code=0,
        message="success",
        data=PresignedUrlData(
            url=result.data["url"],
            expires_at=result.metadata.get("expires_at", ""),
            key=key,
        )
    )


# ============ F14: 查询任务详情 ============

@router.get(
    "/{task_id}",
    response_model=TaskDetailResponse,
    summary="查询任务详情",
    description="获取指定任务的完整信息，包括基本信息、输入文件、各阶段产物等",
    responses={
        200: {"description": "查询成功", "model": TaskDetailResponse},
        404: {"description": "任务不存在", "model": TaskNotFoundError}
    }
)
async def get_task_detail(
    task_id: str,
    db: Session = Depends(get_db)
) -> TaskDetailResponse:
    """F14: 查询任务详情
    
    Args:
        task_id: 任务唯一标识
        db: 数据库会话
        
    Returns:
        TaskDetailResponse: 完整的任务详情
        
    Raises:
        HTTPException 404: 任务不存在
    """
    task = db.query(SmartCutTask).filter(SmartCutTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    return _build_task_detail(db, task)


# ============ F24: 放弃任务 ============

@router.post(
    "/{task_id}/abandon",
    response_model=TaskAbandonResponse,
    summary="放弃任务",
    description="放弃指定任务。终态任务（success, abandoned, failed 等）不能放弃",
    responses={
        200: {"description": "放弃成功", "model": TaskAbandonResponse},
        400: {"description": "任务已处于终态，无法放弃", "model": TaskCannotAbandonError},
        404: {"description": "任务不存在", "model": TaskNotFoundError}
    }
)
async def abandon_task(
    task_id: str,
    db: Session = Depends(get_db)
) -> TaskAbandonResponse:
    """F24: 放弃任务
    
    校验任务状态，更新为 abandoned，并触发 workspace 清理 (F26)。
    
    Args:
        task_id: 任务唯一标识
        db: 数据库会话
        
    Returns:
        TaskAbandonResponse: 放弃确认信息
        
    Raises:
        HTTPException 404: 任务不存在
        HTTPException 400: 任务已处于终态，无法放弃
    """
    # 查询任务
    task = db.query(SmartCutTask).filter(SmartCutTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 校验任务状态 - 终态不能放弃
    if task.is_terminal():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务已处于终态 ({task.status.value})，无法放弃"
        )
    
    # 更新任务状态
    task.status = TaskStatus.ABANDONED
    task.current_stage = CurrentStage.COMPLETE
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    # F26: 触发 workspace 清理 (异步)
    asyncio.create_task(cleanup_workspace_async(task))
    
    return TaskAbandonResponse(
        task_id=task.id,
        status=task.status.value,
        abandoned_at=task.updated_at
    )


async def cleanup_workspace_async(task: SmartCutTask) -> None:
    """异步清理 workspace (F26 实现)
    
    使用 CleanupService 清理放弃任务的资源。
    
    Args:
        task: SmartCutTask 对象
    """
    try:
        # 创建清理服务实例
        cleanup_service = create_cleanup_service()
        
        # 执行清理
        result = cleanup_service.cleanup_abandoned_task(task)
        
        # 记录清理结果
        print(f"[CLEANUP] Task {task.id} cleanup result: {result}")
        
    except Exception as e:
        # 清理失败不影响主流程，但应记录错误
        print(f"[CLEANUP ERROR] Failed to cleanup task {task.id}: {e}")
