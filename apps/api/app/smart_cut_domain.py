"""
Smart Cut 调度领域逻辑模块

对应实施计划：
- 业务任务与调度任务分层
- analyze / preview / finalize 三阶段状态机
- 状态推进规则

状态机：
    created -> waiting_upload -> ready_analyze -> analyzing -> waiting_user
                                           ^                |
                                           |                v
                                    previewing <- previewing <-
                                           |
                                           v
                                    ready_finalize -> finalizing -> success
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Literal


class SmartCutStatus(str, Enum):
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


class SmartCutErrorStage(str, Enum):
    """失败阶段细分"""
    INPUT_UPLOAD_FAILED = "input_upload_failed"
    ANALYZE_FAILED = "analyze_failed"
    PREVIEW_FAILED = "preview_failed"
    PREVIEW_UPLOAD_FAILED = "preview_upload_failed"
    FINALIZE_FAILED = "finalize_failed"
    FINAL_UPLOAD_FAILED = "final_upload_failed"
    GROUNDTRUTH_UPLOAD_FAILED = "groundtruth_upload_failed"


class EditStatus(str, Enum):
    """Edit 记录状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class OutputMode(str, Enum):
    """输出模式"""
    ORIGINAL = "original"
    VERTICAL_1080P = "vertical_1080p"


@dataclass(slots=True)
class SmartCutTaskRecord:
    """Smart Cut 业务任务领域对象"""
    id: str
    user_id: int
    status: SmartCutStatus
    created_at: datetime
    updated_at: datetime

    # 阶段
    current_stage: str | None = None
    error_stage: SmartCutErrorStage | None = None
    error_message: str | None = None

    # 输入
    original_video_tos_key: str | None = None
    reference_text_tos_key: str | None = None

    # analyze 产物
    analyze_script: str | None = None
    analyze_script_tos_key: str | None = None
    asr_result_tos_key: str | None = None

    # edit 关联
    active_edit_id: str | None = None
    finalize_source_edit_id: str | None = None

    # finalize 产物
    final_video_tos_key: str | None = None
    groundtruth_tos_key: str | None = None

    # 配置
    feed_to_ai: bool = False
    output_mode: OutputMode = OutputMode.ORIGINAL

    # 调度关联
    last_scheduler_task_id: str | None = None


@dataclass(slots=True)
class SmartCutEditRecord:
    """Smart Cut Edit 领域对象"""
    id: str
    task_id: str
    edited_script: str
    status: EditStatus
    created_at: datetime
    updated_at: datetime

    # 产物
    audio_b_tos_key: str | None = None
    edited_delay_cuts_tos_key: str | None = None
    pause_cuts_on_original_tos_key: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class TransitionResult:
    """状态转换结果"""
    task: SmartCutTaskRecord | None = None
    edit: SmartCutEditRecord | None = None
    new_edit: SmartCutEditRecord | None = None  # 用于 preview 创建新 edit
    scheduler_task_type: str | None = None  # 需要创建的调度任务类型
    scheduler_payload: dict | None = None  # 调度任务 payload
    trace: list[str] = field(default_factory=list)


def ensure_utc(value: datetime) -> datetime:
    """确保时间为 UTC"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_task(*, task_id: str, user_id: int, created_at: datetime) -> TransitionResult:
    """创建业务任务 -> created -> waiting_upload"""
    now = ensure_utc(created_at)
    task = SmartCutTaskRecord(
        id=task_id,
        user_id=user_id,
        status=SmartCutStatus.WAITING_UPLOAD,
        created_at=now,
        updated_at=now,
    )
    return TransitionResult(
        task=task,
        trace=[f"{task_id}: created -> waiting_upload"],
    )


def bind_input(
    task: SmartCutTaskRecord,
    *,
    video_tos_key: str,
    text_tos_key: str,
    now: datetime,
) -> TransitionResult:
    """
    绑定输入文件 -> waiting_upload -> ready_analyze

    前置条件:
        - task.status == waiting_upload
        - key 属于当前任务
    """
    if task.status != SmartCutStatus.WAITING_UPLOAD:
        raise ValueError(f"Cannot bind input from status {task.status}")

    updated = replace(
        task,
        status=SmartCutStatus.READY_ANALYZE,
        original_video_tos_key=video_tos_key,
        reference_text_tos_key=text_tos_key,
        updated_at=ensure_utc(now),
    )
    return TransitionResult(
        task=updated,
        trace=[f"{task.id}: waiting_upload -> ready_analyze"],
    )


def start_analyze(
    task: SmartCutTaskRecord,
    *,
    scheduler_task_id: str,
    now: datetime,
) -> TransitionResult:
    """
    启动 analyze 阶段 -> ready_analyze -> analyzing

    创建 scheduler task payload:
        - task_type: smart_cut_analyze
        - payload: {smart_cut_task_id, original_video_tos_key, reference_text_tos_key}
    """
    if task.status != SmartCutStatus.READY_ANALYZE:
        raise ValueError(f"Cannot start analyze from status {task.status}")

    updated = replace(
        task,
        status=SmartCutStatus.ANALYZING,
        last_scheduler_task_id=scheduler_task_id,
        updated_at=ensure_utc(now),
    )

    payload = {
        "smart_cut_task_id": task.id,
        "original_video_tos_key": task.original_video_tos_key,
        "reference_text_tos_key": task.reference_text_tos_key,
    }

    return TransitionResult(
        task=updated,
        scheduler_task_type="smart_cut_analyze",
        scheduler_payload=payload,
        trace=[f"{task.id}: ready_analyze -> analyzing"],
    )


def complete_analyze(
    task: SmartCutTaskRecord,
    *,
    script: str,
    script_tos_key: str,
    asr_result_tos_key: str,
    now: datetime,
) -> TransitionResult:
    """
    analyze 成功 -> analyzing -> waiting_user

    Worker 上传产物后调用此函数推进业务状态
    """
    if task.status != SmartCutStatus.ANALYZING:
        raise ValueError(f"Cannot complete analyze from status {task.status}")

    updated = replace(
        task,
        status=SmartCutStatus.WAITING_USER,
        analyze_script=script,
        analyze_script_tos_key=script_tos_key,
        asr_result_tos_key=asr_result_tos_key,
        current_stage="analyze_done",
        updated_at=ensure_utc(now),
    )
    return TransitionResult(
        task=updated,
        trace=[f"{task.id}: analyzing -> waiting_user"],
    )


def fail_analyze(
    task: SmartCutTaskRecord,
    *,
    error_message: str,
    now: datetime,
) -> TransitionResult:
    """analyze 失败 -> analyzing -> failed"""
    if task.status != SmartCutStatus.ANALYZING:
        raise ValueError(f"Cannot fail analyze from status {task.status}")

    updated = replace(
        task,
        status=SmartCutStatus.FAILED,
        error_stage=SmartCutErrorStage.ANALYZE_FAILED,
        error_message=error_message,
        updated_at=ensure_utc(now),
    )
    return TransitionResult(
        task=updated,
        trace=[f"{task.id}: analyzing -> failed (analyze_failed)"],
    )


def start_preview(
    task: SmartCutTaskRecord,
    *,
    edit_id: str,
    edited_script: str,
    scheduler_task_id: str,
    now: datetime,
) -> TransitionResult:
    """
    启动 preview 阶段 -> waiting_user -> previewing

    创建新的 edit 记录和 scheduler task
    """
    if task.status != SmartCutStatus.WAITING_USER:
        raise ValueError(f"Cannot start preview from status {task.status}")

    now_utc = ensure_utc(now)

    # 创建新 edit 记录
    new_edit = SmartCutEditRecord(
        id=edit_id,
        task_id=task.id,
        edited_script=edited_script,
        status=EditStatus.PROCESSING,
        created_at=now_utc,
        updated_at=now_utc,
    )

    # 更新任务状态
    updated = replace(
        task,
        status=SmartCutStatus.PREVIEWING,
        active_edit_id=edit_id,
        last_scheduler_task_id=scheduler_task_id,
        updated_at=now_utc,
    )

    # 构建 scheduler payload
    payload = {
        "smart_cut_task_id": task.id,
        "edit_id": edit_id,
        "edited_script": edited_script,
        "original_video_tos_key": task.original_video_tos_key,
        "asr_result_tos_key": task.asr_result_tos_key,
    }

    return TransitionResult(
        task=updated,
        new_edit=new_edit,
        scheduler_task_type="smart_cut_preview",
        scheduler_payload=payload,
        trace=[f"{task.id}: waiting_user -> previewing (edit_id={edit_id})"],
    )


def complete_preview(
    task: SmartCutTaskRecord,
    edit: SmartCutEditRecord,
    *,
    audio_b_tos_key: str,
    edited_delay_cuts_tos_key: str,
    pause_cuts_on_original_tos_key: str,
    now: datetime,
) -> TransitionResult:
    """
    preview 成功 -> previewing -> waiting_user

    Worker 上传产物后调用
    """
    if task.status != SmartCutStatus.PREVIEWING:
        raise ValueError(f"Cannot complete preview from status {task.status}")
    if edit.status != EditStatus.PROCESSING:
        raise ValueError(f"Edit must be in processing state, got {edit.status}")

    now_utc = ensure_utc(now)

    # 更新 edit
    updated_edit = replace(
        edit,
        status=EditStatus.SUCCESS,
        audio_b_tos_key=audio_b_tos_key,
        edited_delay_cuts_tos_key=edited_delay_cuts_tos_key,
        pause_cuts_on_original_tos_key=pause_cuts_on_original_tos_key,
        updated_at=now_utc,
    )

    # 更新任务状态
    updated = replace(
        task,
        status=SmartCutStatus.WAITING_USER,
        finalize_source_edit_id=edit.id,  # 记录最后一次成功 preview
        current_stage="preview_done",
        updated_at=now_utc,
    )

    return TransitionResult(
        task=updated,
        edit=updated_edit,
        trace=[f"{task.id}: previewing -> waiting_user (edit_id={edit.id} success)"],
    )


def fail_preview(
    task: SmartCutTaskRecord,
    edit: SmartCutEditRecord,
    *,
    error_message: str,
    upload_failed: bool = False,
    now: datetime,
) -> TransitionResult:
    """preview 失败 -> previewing -> waiting_user (edit 标记为失败)"""
    if task.status != SmartCutStatus.PREVIEWING:
        raise ValueError(f"Cannot fail preview from status {task.status}")

    now_utc = ensure_utc(now)

    error_stage = (
        SmartCutErrorStage.PREVIEW_UPLOAD_FAILED
        if upload_failed
        else SmartCutErrorStage.PREVIEW_FAILED
    )

    # 更新 edit
    updated_edit = replace(
        edit,
        status=EditStatus.FAILED,
        error_message=error_message,
        updated_at=now_utc,
    )

    # 任务回到 waiting_user，但 finalize_source_edit_id 不更新
    updated = replace(
        task,
        status=SmartCutStatus.WAITING_USER,
        error_stage=error_stage,
        error_message=error_message,
        updated_at=now_utc,
    )

    return TransitionResult(
        task=updated,
        edit=updated_edit,
        trace=[f"{task.id}: previewing -> waiting_user (edit_id={edit.id} failed)"],
    )


def start_finalize(
    task: SmartCutTaskRecord,
    *,
    scheduler_task_id: str,
    output_mode: OutputMode = OutputMode.ORIGINAL,
    feed_to_ai: bool = False,
    now: datetime,
) -> TransitionResult:
    """
    启动 finalize 阶段 -> waiting_user -> finalizing

    必须基于最后一次成功的 preview (finalize_source_edit_id)
    """
    if task.status != SmartCutStatus.WAITING_USER:
        raise ValueError(f"Cannot start finalize from status {task.status}")
    if task.finalize_source_edit_id is None:
        raise ValueError("Cannot finalize without a successful preview")

    # 需要查找最后一次成功 preview 的产物
    # 这里假设调用方已经验证 edit 存在且成功

    updated = replace(
        task,
        status=SmartCutStatus.FINALIZING,
        output_mode=output_mode,
        feed_to_ai=feed_to_ai,
        last_scheduler_task_id=scheduler_task_id,
        updated_at=ensure_utc(now),
    )

    # Scheduler payload 需要包含 finalize 所需的所有输入
    payload = {
        "smart_cut_task_id": task.id,
        "edit_id": task.finalize_source_edit_id,
        "original_video_tos_key": task.original_video_tos_key,
        # finalize 阶段需要的产物 key 会在调度时从 edit 表获取
        "output_mode": output_mode.value,
        "feed_to_ai": feed_to_ai,
    }

    return TransitionResult(
        task=updated,
        scheduler_task_type="smart_cut_finalize",
        scheduler_payload=payload,
        trace=[f"{task.id}: waiting_user -> finalizing (based on edit_id={task.finalize_source_edit_id})"],
    )


def complete_finalize(
    task: SmartCutTaskRecord,
    *,
    final_video_tos_key: str,
    groundtruth_tos_key: str | None,
    now: datetime,
) -> TransitionResult:
    """finalize 成功 -> finalizing -> success"""
    if task.status != SmartCutStatus.FINALIZING:
        raise ValueError(f"Cannot complete finalize from status {task.status}")

    updated = replace(
        task,
        status=SmartCutStatus.SUCCESS,
        final_video_tos_key=final_video_tos_key,
        groundtruth_tos_key=groundtruth_tos_key,
        updated_at=ensure_utc(now),
    )
    return TransitionResult(
        task=updated,
        trace=[f"{task.id}: finalizing -> success"],
    )


def fail_finalize(
    task: SmartCutTaskRecord,
    *,
    error_message: str,
    upload_failed: bool = False,
    now: datetime,
) -> TransitionResult:
    """finalize 失败 -> finalizing -> failed"""
    if task.status != SmartCutStatus.FINALIZING:
        raise ValueError(f"Cannot fail finalize from status {task.status}")

    error_stage = (
        SmartCutErrorStage.FINAL_UPLOAD_FAILED
        if upload_failed
        else SmartCutErrorStage.FINALIZE_FAILED
    )

    updated = replace(
        task,
        status=SmartCutStatus.FAILED,
        error_stage=error_stage,
        error_message=error_message,
        updated_at=ensure_utc(now),
    )
    return TransitionResult(
        task=updated,
        trace=[f"{task.id}: finalizing -> failed ({error_stage.value})"],
    )


def generate_input_keys(task_id: str) -> tuple[str, str]:
    """
    生成输入文件的 TOS key

    固定格式：
        - video: smart-cut/{task_id}/input/source_video.{ext} (ext 由客户端决定)
        - text: smart-cut/{task_id}/input/reference.txt
    """
    # 返回基础 key，扩展名由上传时决定
    video_base = f"smart-cut/{task_id}/input/source_video"
    text_key = f"smart-cut/{task_id}/input/reference.txt"
    return video_base, text_key


def validate_upload_keys(task_id: str, video_key: str, text_key: str) -> bool:
    """
    验证 upload-complete 的 key 是否属于当前任务

    规则：
        - key 必须以 smart-cut/{task_id}/ 开头
        - video 必须在 input/ 下
        - text 必须匹配 reference.txt
    """
    prefix = f"smart-cut/{task_id}/"
    if not video_key.startswith(prefix):
        return False
    if not text_key.startswith(prefix):
        return False
    if not video_key.startswith(f"{prefix}input/"):
        return False
    if not text_key.endswith("/input/reference.txt"):
        return False
    return True
