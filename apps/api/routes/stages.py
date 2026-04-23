"""阶段触发 API 路由 - F13, F17, F19

实现 Smart Cut 三阶段流程的触发接口:
- F13: POST /api/smart-cut/tasks/{task_id}/analyze
- F17: POST /api/smart-cut/tasks/{task_id}/preview
- F19: POST /api/smart-cut/tasks/{task_id}/finalize
"""

import json
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from configs.database import get_db
from apps.models.task import SmartCutTask, TaskStatus, CurrentStage
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskType, SchedulerTaskStatus
from apps.models.edit import SmartCutEdit, EditStatus
from apps.models.task_run import SmartCutTaskRun, TaskRunType, TaskRunStatus
from apps.api.models.schemas import (
    StartAnalyzeResponse,
    PreviewRequest,
    PreviewResponse,
    FinalizeRequest,
    FinalizeResponse,
)
from apps.services.smart_cut_contract import build_smart_cut_task_title

router = APIRouter(prefix="/api/smart-cut", tags=["stages"])


def _next_run_sequence(db: Session, task_id: str) -> int:
    latest = (
        db.query(SmartCutTaskRun)
        .filter(SmartCutTaskRun.task_id == task_id)
        .order_by(SmartCutTaskRun.sequence_number.desc())
        .first()
    )
    return 1 if latest is None else latest.sequence_number + 1


def get_scheduler_service(db: Session = Depends(get_db)) -> Any:
    """获取调度服务实例（简化版本，直接操作数据库）"""
    return db


def _coerce_script_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for segment in value:
            if isinstance(segment, str):
                parts.append(segment)
            elif isinstance(segment, dict):
                parts.append(str(segment.get("text", "")))
            else:
                parts.append(str(segment))
        return "".join(parts)
    if isinstance(value, dict) and isinstance(value.get("segments"), list):
        parts: list[str] = []
        for segment in value["segments"]:
            if isinstance(segment, str):
                parts.append(segment)
            elif isinstance(segment, dict):
                parts.append(str(segment.get("text", "")))
            else:
                parts.append(str(segment))
        return "".join(parts)
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)


def _strip_brace_markers(script: str) -> str:
    return "".join(char for char in script if char not in "{}")


def _validate_brace_script(script: str) -> None:
    if not script.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="edited_script cannot be empty",
        )

    depth = 0
    for char in script:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="edited_script contains invalid brace markers",
                )
    if depth != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="edited_script contains invalid brace markers",
        )


def _validate_preview_script_against_task(task: SmartCutTask, edited_script: str) -> None:
    _validate_brace_script(edited_script)

    baseline_script = _coerce_script_text(task.analyze_script)
    if not baseline_script:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analyze script not available, preview baseline missing",
        )

    if _strip_brace_markers(edited_script) != _strip_brace_markers(baseline_script):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "edited_script must preserve the current task script text; "
                "preview only supports adjusting deletion ranges"
            ),
        )


# ========== F13: Trigger Analyze ==========

@router.post(
    "/tasks/{task_id}/analyze",
    response_model=StartAnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="触发分析阶段",
    description="从 ready_analyze 状态推进到 analyzing，创建 analyze 调度任务",
)
async def start_analyze(
    task_id: str,
    db: Session = Depends(get_db),
) -> StartAnalyzeResponse:
    """
    触发 Analyze 阶段处理
    
    流程:
    1. 校验 task.status == ready_analyze
    2. 创建 SchedulerTask (type=smart_cut_analyze)
    3. 推进 task.status = analyzing
    4. 返回 scheduler_task_id
    """
    # 查询任务
    task = db.get(SmartCutTask, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}"
        )
    
    # 校验状态: 必须是 ready_analyze
    if task.status != TaskStatus.READY_ANALYZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task status: {task.status.value}, expected: {TaskStatus.READY_ANALYZE.value}"
        )
    
    # 检查必要的TOS key
    if not task.original_video_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Original video not uploaded"
        )
    if not task.reference_text_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reference text not uploaded"
        )
    
    # 从URL中提取TOS key
    original_video_tos_key = task.original_video_url
    reference_text_tos_key = task.reference_text_url
    
    # 创建 SchedulerTask
    scheduler_task = SchedulerTask(
        task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
        status=SchedulerTaskStatus.PENDING,
        business_task_id=task_id,
        payload={
            "smart_cut_task_id": task_id,
            "original_video_tos_key": original_video_tos_key,
            "reference_text_tos_key": reference_text_tos_key,
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
    
    # 推进任务状态
    task.status = TaskStatus.ANALYZING
    task.current_stage = CurrentStage.ANALYZE
    task.current_run_id = analyze_run.id
    
    db.commit()
    db.refresh(scheduler_task)
    
    return StartAnalyzeResponse(
        scheduler_task_id=scheduler_task.id,
        status=task.status.value,
    )


# ========== F17: Trigger Preview ==========

@router.post(
    "/tasks/{task_id}/preview",
    response_model=PreviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="触发预览阶段",
    description="创建新的 Edit 记录并启动 preview 任务",
)
async def start_preview(
    task_id: str,
    req: PreviewRequest,
    db: Session = Depends(get_db),
) -> PreviewResponse:
    """
    触发 Preview 阶段处理
    
    流程:
    1. 校验 task.status == waiting_user
    2. 创建新的 SmartCutEdit 记录 (version_number 递增)
    3. 创建 SchedulerTask (type=smart_cut_preview)
    4. 推进 task.status = previewing
    5. 返回 edit_id 和 scheduler_task_id
    """
    # 查询任务
    task = db.get(SmartCutTask, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}"
        )
    
    # 校验状态: 必须是 waiting_user
    if task.status not in {TaskStatus.WAITING_USER, TaskStatus.PREVIEW_FAILED, TaskStatus.SUCCESS}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task status: {task.status.value}, expected: waiting_user, preview_failed or success"
        )
    
    # 检查是否有 analyze 产物
    if not task.asr_result_tos_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ASR result not available, analyze not completed"
        )

    _validate_preview_script_against_task(task, req.edited_script)
    
    # 获取下一个版本号
    next_version = SmartCutEdit.get_next_version_number(db, task_id)
    
    # 创建 SmartCutEdit 记录
    edit = SmartCutEdit(
        task_id=task_id,
        edited_script=req.edited_script,
        status=EditStatus.PROCESSING,  # 直接进入 processing 状态
        version_number=next_version,
    )
    db.add(edit)
    db.flush()  # 获取 edit.id
    
    # 获取原始视频 TOS key
    original_video_tos_key = task.original_video_url or ""
    asr_result_tos_key = task.asr_result_tos_key
    
    # 创建 SchedulerTask
    scheduler_task = SchedulerTask(
        task_type=SchedulerTaskType.SMART_CUT_PREVIEW,
        status=SchedulerTaskStatus.PENDING,
        business_task_id=task_id,
        payload={
            "smart_cut_task_id": task_id,
            "edit_id": edit.id,
            "edited_script": req.edited_script,
            "original_video_tos_key": original_video_tos_key,
            "asr_result_tos_key": asr_result_tos_key,
        },
    )
    db.add(scheduler_task)
    db.flush()

    preview_run = SmartCutTaskRun(
        task_id=task_id,
        run_type=TaskRunType.PREVIEW,
        status=TaskRunStatus.QUEUED,
        sequence_number=_next_run_sequence(db, task_id),
        scheduler_task_id=scheduler_task.id,
        source_edit_id=edit.id,
        payload_snapshot=dict(scheduler_task.payload),
    )
    db.add(preview_run)
    
    # 推进任务状态
    task.status = TaskStatus.PREVIEWING
    task.current_stage = CurrentStage.PREVIEW
    task.active_edit_id = edit.id
    task.current_run_id = preview_run.id
    task.revision_count = max(task.revision_count, next_version)
    
    db.commit()
    db.refresh(edit)
    db.refresh(scheduler_task)
    
    return PreviewResponse(
        edit_id=edit.id,
        scheduler_task_id=scheduler_task.id,
        status=task.status.value,
    )


# ========== F19: Trigger Finalize ==========

@router.post(
    "/tasks/{task_id}/finalize",
    response_model=FinalizeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="触发最终生成阶段",
    description="使用最后一次成功的 edit（或指定的 edit_id）启动 finalize 任务",
)
async def start_finalize(
    task_id: str,
    req: FinalizeRequest,
    db: Session = Depends(get_db),
) -> FinalizeResponse:
    """
    触发 Finalize 阶段处理
    
    流程:
    1. 校验 task.status == waiting_user
    2. 读取最后一次成功的 edit (或请求中指定的 edit_id)
    3. 创建 SchedulerTask (type=smart_cut_finalize)
    4. 推进 task.status = finalizing
    5. 返回 scheduler_task_id
    """
    # 查询任务
    task = db.get(SmartCutTask, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}"
        )
    
    # 校验状态: 必须是 waiting_user
    if task.status not in {TaskStatus.WAITING_USER, TaskStatus.SUCCESS}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task status: {task.status.value}, expected: waiting_user or success"
        )
    
    # 获取要使用的 edit
    edit: SmartCutEdit | None = None
    
    if req.edit_id:
        # 使用指定的 edit_id
        edit = db.get(SmartCutEdit, req.edit_id)
        if not edit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Edit not found: {req.edit_id}"
            )
        if edit.task_id != task_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Edit does not belong to this task"
            )
        if edit.status != EditStatus.SUCCESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Edit status is {edit.status.value}, expected: success"
            )
    else:
        # 查找最后一次成功的 edit
        stmt = (
            select(SmartCutEdit)
            .where(
                SmartCutEdit.task_id == task_id,
                SmartCutEdit.status == EditStatus.SUCCESS
            )
            .order_by(desc(SmartCutEdit.version_number))
            .limit(1)
        )
        edit = db.execute(stmt).scalar_one_or_none()
        
        if not edit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No successful edit found for this task"
            )
    
    # 检查必要的产物
    if not edit.delay_cuts_tos_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delay cuts not available for the selected edit"
        )
    
    # 获取原始视频 TOS key
    original_video_tos_key = task.original_video_url or ""
    
    # 创建 SchedulerTask
    task_title = task.task_title or build_smart_cut_task_title()
    scheduler_task = SchedulerTask(
        task_type=SchedulerTaskType.SMART_CUT_FINALIZE,
        status=SchedulerTaskStatus.PENDING,
        business_task_id=task_id,
        payload={
            "smart_cut_task_id": task_id,
            "edit_id": edit.id,
            "original_video_tos_key": original_video_tos_key,
            "edited_delay_cuts_tos_key": edit.delay_cuts_tos_key,
            "pause_cuts_on_original_tos_key": edit.pause_cuts_tos_key,
            "output_mode": req.output_mode,
            "feed_to_ai": req.feed_to_ai,
        },
    )
    db.add(scheduler_task)
    db.flush()

    finalize_run = SmartCutTaskRun(
        task_id=task_id,
        run_type=TaskRunType.FINALIZE,
        status=TaskRunStatus.QUEUED,
        sequence_number=_next_run_sequence(db, task_id),
        scheduler_task_id=scheduler_task.id,
        source_edit_id=edit.id,
        payload_snapshot=dict(scheduler_task.payload),
    )
    db.add(finalize_run)
    
    # 推进任务状态
    task.task_title = task_title
    task.visible_in_task_center = True
    task.status = TaskStatus.FINALIZING
    task.current_stage = CurrentStage.FINALIZE
    task.active_edit_id = edit.id
    task.current_run_id = finalize_run.id
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(scheduler_task)
    db.refresh(task)
    
    return FinalizeResponse(
        scheduler_task_id=scheduler_task.id,
        status=task.status.value,
        visible_in_task_center=task.visible_in_task_center,
        task_title=task.task_title or task_title,
    )
