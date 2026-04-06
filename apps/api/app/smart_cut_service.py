"""
Smart Cut 业务服务层

封装 Smart Cut 任务的业务逻辑，包括：
- 任务创建
- upload-prepare / upload-complete
- analyze/preview/finalize 阶段管理
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DbSession

from app import crud, models, smart_cut_domain
from app.smart_cut_domain import (
    SmartCutStatus,
    bind_input,
    create_task,
    generate_input_keys,
    validate_upload_keys,
)
from app.tos_service import FakeTOSClient, get_tos_client, validate_tos_key_belongs_to_task


class SmartCutError(ValueError):
    """Smart Cut 业务错误"""
    pass


def create_smart_cut_task(db: DbSession, user_id: int) -> models.SmartCutTask:
    """
    创建新的 Smart Cut 业务任务

    流程:
        1. 生成 task_id
        2. 创建任务（状态: waiting_upload）
    """
    task_id = f"sct-{uuid.uuid4().hex[:12]}"
    return crud.create_smart_cut_task(db, task_id, user_id)


def prepare_upload(
    db: DbSession,
    task_id: str,
    user_id: int,
    video_ext: str = "mp4",
) -> dict:
    """
    准备上传

    职责:
        1. 验证任务存在且属于当前用户
        2. 验证任务状态为 waiting_upload
        3. 生成确定性的 TOS key
        4. 持久化本次 prepare 的目标 key（用于后续 complete 绑定校验）
        5. 返回上传参数

    Returns:
        {
            "task_id": str,
            "video_upload_key": str,
            "text_upload_key": str,
            "video_content_type": str,
            "text_content_type": str,
        }
    """
    task = crud.get_smart_cut_task(db, task_id)
    if task is None:
        raise SmartCutError(f"Task {task_id} not found")
    if task.user_id != user_id:
        raise SmartCutError(f"Task {task_id} does not belong to user")
    if task.status != SmartCutStatus.WAITING_UPLOAD.value:
        raise SmartCutError(f"Cannot prepare upload for task in status {task.status}")

    # 生成确定性 key
    video_base, text_key = generate_input_keys(task_id)
    video_key = f"{video_base}.{video_ext.lstrip('.')}"

    # 持久化本次 prepare 的目标 key（用于 complete 绑定校验）
    crud.update_smart_cut_task_prepared_keys(db, task_id, video_key, text_key)

    return {
        "task_id": task_id,
        "video_upload_key": video_key,
        "text_upload_key": text_key,
        "video_content_type": f"video/{video_ext.lstrip('.')}",
        "text_content_type": "text/plain",
    }


def complete_upload(
    db: DbSession,
    task_id: str,
    user_id: int,
    video_key: str,
    text_key: str,
    use_fake_tos: bool = True,
) -> models.SmartCutTask:
    """
    完成上传

    职责:
        1. 验证任务存在且属于当前用户
        2. 验证任务状态为 waiting_upload
        3. 验证 key 与 upload-prepare 阶段发出的一致（绑定校验）
        4. 验证 key 属于当前任务
        5. 验证对象存在于 TOS（Fake 或真实）
        6. 更新任务状态为 ready_analyze

    Args:
        db: 数据库会话
        task_id: 任务 ID
        user_id: 用户 ID
        video_key: 视频对象 key（必须与 prepare 发出的一致）
        text_key: 文案对象 key（必须与 prepare 发出的一致）
        use_fake_tos: 使用 Fake TOS 检查对象存在性

    Returns:
        更新后的任务
    """
    task = crud.get_smart_cut_task(db, task_id)
    if task is None:
        raise SmartCutError(f"Task {task_id} not found")
    if task.user_id != user_id:
        raise SmartCutError(f"Task {task_id} does not belong to user")
    if task.status != SmartCutStatus.WAITING_UPLOAD.value:
        raise SmartCutError(f"Cannot complete upload for task in status {task.status}")

    # 验证 key 与 prepare 阶段发出的一致（绑定校验）
    if task.prepared_video_key is None or task.prepared_text_key is None:
        raise SmartCutError("Upload-prepare must be called before upload-complete")
    if video_key != task.prepared_video_key:
        raise SmartCutError(
            f"Video key mismatch: expected {task.prepared_video_key}, got {video_key}"
        )
    if text_key != task.prepared_text_key:
        raise SmartCutError(
            f"Text key mismatch: expected {task.prepared_text_key}, got {text_key}"
        )

    # 验证 key 属于当前任务
    if not validate_tos_key_belongs_to_task(task_id, video_key):
        raise SmartCutError(f"Video key {video_key} does not belong to task {task_id}")
    if not validate_tos_key_belongs_to_task(task_id, text_key):
        raise SmartCutError(f"Text key {text_key} does not belong to task {task_id}")

    # 验证 key 格式
    if not validate_upload_keys(task_id, video_key, text_key):
        raise SmartCutError("Invalid key format")

    # 验证对象存在于 TOS
    tos_client = get_tos_client(use_fake=use_fake_tos)
    if not tos_client.object_exists(video_key):
        raise SmartCutError(f"Video object {video_key} does not exist in TOS")
    if not tos_client.object_exists(text_key):
        raise SmartCutError(f"Text object {text_key} does not exist in TOS")

    # 更新任务状态
    return crud.update_smart_cut_task_input_keys(db, task_id, video_key, text_key)


def get_task_detail(db: DbSession, task_id: str, user_id: int) -> models.SmartCutTask:
    """获取任务详情（验证权限）"""
    task = crud.get_smart_cut_task_with_edits(db, task_id)
    if task is None:
        raise SmartCutError(f"Task {task_id} not found")
    if task.user_id != user_id:
        raise SmartCutError(f"Task {task_id} does not belong to user")
    return task


def list_user_tasks(db: DbSession, user_id: int) -> list[models.SmartCutTask]:
    """获取用户的所有任务"""
    return crud.list_smart_cut_tasks_by_user(db, user_id)


# ============================================
# Stage Management (for F04, F05, F06)
# ============================================


def start_analyze_stage(
    db: DbSession,
    task_id: str,
    user_id: int,
) -> tuple[models.SmartCutTask, models.SchedulerTask]:
    """
    启动 analyze 阶段

    职责:
        1. 验证任务状态为 ready_analyze
        2. 创建 smart_cut_analyze 调度任务
        3. 更新业务任务状态为 analyzing
        4. 触发调度 tick（失败不影响已提交的事务）

    事务行为：
        - 调度任务创建和业务状态更新在同一个事务中
        - dispatch_tick 在事务提交后调用，失败不影响已创建的任务

    Returns:
        (smart_cut_task, scheduler_task)
    """
    from app import scheduler_service

    task = crud.get_smart_cut_task(db, task_id)
    if task is None:
        raise SmartCutError(f"Task {task_id} not found")
    if task.user_id != user_id:
        raise SmartCutError(f"Task {task_id} does not belong to user")
    if task.status != SmartCutStatus.READY_ANALYZE.value:
        raise SmartCutError(f"Cannot start analyze from status {task.status}")

    now = datetime.now(timezone.utc)

    # 创建调度任务 payload
    input_payload = {
        "smart_cut_task_id": task.id,
        "original_video_tos_key": task.original_video_tos_key,
        "reference_text_tos_key": task.reference_text_tos_key,
        "stage": "analyze",
    }

    try:
        # 创建调度任务
        scheduler_task = scheduler_service.create_scheduler_task(
            db,
            user_id=user_id,
            page_key=f"smart-cut-{task.id}",
            task_type="smart_cut_analyze",
            step_total=1,
            needs_post=False,
            input_payload=input_payload,
            now=now,
        )

        # 更新业务任务状态（同一事务）
        task.status = SmartCutStatus.ANALYZING.value
        task.last_scheduler_task_id = scheduler_task.task_id
        task.updated_at = now
        db.commit()
        db.refresh(task)
        db.refresh(scheduler_task)

    except Exception as exc:
        db.rollback()
        raise SmartCutError(f"Failed to create analyze task: {exc}") from exc

    # 触发调度 tick（在事务提交后，失败不影响已创建的任务）
    try:
        scheduler_service.dispatch_tick(db)
    except Exception:
        # dispatch_tick 失败不应影响 API 返回，记录日志即可
        # 调度器会在下次 tick 时处理待分配任务
        pass

    return task, scheduler_task


def complete_analyze_stage(
    db: DbSession,
    task_id: str,
    scheduler_task_id: str,
    worker_id: str,
    worker_token: str,
    script: str,
    script_tos_key: str,
    asr_result_tos_key: str,
) -> models.SmartCutTask:
    """
    Worker 完成 analyze 后调用此函数更新业务任务状态

    安全校验：
        1. 验证 X-Worker-Token 与 Worker 注册时存储的 hashed_token 匹配
        2. 验证 scheduler_task_id 匹配 last_scheduler_task_id
        3. 验证 worker_id 是当前被分配的 worker
        4. 验证业务任务状态为 analyzing

    Args:
        task_id: Smart Cut 业务任务 ID
        scheduler_task_id: 调度任务 ID（用于验证）
        worker_id: Worker ID（用于验证）
        worker_token: Worker Token（从 X-Worker-Token header 获取）
        script: analyze 生成的 script 内容
        script_tos_key: script 在 TOS 中的 key
        asr_result_tos_key: ASR 结果在 TOS 中的 key

    Returns:
        更新后的业务任务

    Raises:
        SmartCutError: 业务逻辑错误
        WorkerTokenError: 安全验证失败
    """
    from app.worker_auth import authenticate_worker_callback, verify_callback_matches_scheduler_task

    task = crud.get_smart_cut_task(db, task_id)
    if task is None:
        raise SmartCutError(f"Task {task_id} not found")
    if task.status != SmartCutStatus.ANALYZING.value:
        raise SmartCutError(f"Task is not in analyzing state, current: {task.status}")

    # 安全验证 1: 回调的调度任务是否匹配
    verify_callback_matches_scheduler_task(db, task, scheduler_task_id)

    # 安全验证 2: Worker 身份和任务分配（包含 Token 验证）
    authenticate_worker_callback(db, worker_id, worker_token, scheduler_task_id)

    now = datetime.now(timezone.utc)

    # 更新任务状态和产物
    task.status = SmartCutStatus.WAITING_USER.value
    task.current_stage = "analyze_done"
    task.analyze_script = script
    task.analyze_script_tos_key = script_tos_key
    task.asr_result_tos_key = asr_result_tos_key
    task.updated_at = now

    db.commit()
    db.refresh(task)

    return task


def fail_analyze_stage(
    db: DbSession,
    task_id: str,
    scheduler_task_id: str,
    worker_id: str,
    worker_token: str,
    error_message: str,
    error_stage: str = "analyze_failed",
) -> models.SmartCutTask:
    """
    Worker analyze 失败时调用此函数更新业务任务状态

    安全校验：
        1. 验证 X-Worker-Token 与 Worker 注册时存储的 hashed_token 匹配
        2. 验证 scheduler_task_id 匹配 last_scheduler_task_id
        3. 验证 worker_id 是当前被分配的 worker

    Args:
        task_id: Smart Cut 业务任务 ID
        scheduler_task_id: 调度任务 ID（用于验证）
        worker_id: Worker ID（用于验证）
        worker_token: Worker Token（从 X-Worker-Token header 获取）
        error_message: 错误信息
        error_stage: 错误阶段

    Returns:
        更新后的业务任务

    Raises:
        SmartCutError: 业务逻辑错误
        WorkerTokenError: 安全验证失败
    """
    from app.worker_auth import authenticate_worker_callback, verify_callback_matches_scheduler_task

    task = crud.get_smart_cut_task(db, task_id)
    if task is None:
        raise SmartCutError(f"Task {task_id} not found")

    # 安全验证 1: 回调的调度任务是否匹配
    verify_callback_matches_scheduler_task(db, task, scheduler_task_id)

    # 安全验证 2: Worker 身份和任务分配（包含 Token 验证）
    authenticate_worker_callback(db, worker_id, worker_token, scheduler_task_id)

    now = datetime.now(timezone.utc)

    # 更新任务状态为失败
    task.status = SmartCutStatus.FAILED.value
    task.error_stage = error_stage
    task.error_message = error_message
    task.updated_at = now

    db.commit()
    db.refresh(task)

    return task


def _to_domain_record(task: models.SmartCutTask) -> smart_cut_domain.SmartCutTaskRecord:
    """将 ORM 模型转换为领域记录"""
    return smart_cut_domain.SmartCutTaskRecord(
        id=task.id,
        user_id=task.user_id,
        status=smart_cut_domain.SmartCutStatus(task.status),
        created_at=task.created_at,
        updated_at=task.updated_at,
        current_stage=task.current_stage,
        error_stage=smart_cut_domain.SmartCutErrorStage(task.error_stage) if task.error_stage else None,
        error_message=task.error_message,
        original_video_tos_key=task.original_video_tos_key,
        reference_text_tos_key=task.reference_text_tos_key,
        analyze_script=task.analyze_script,
        analyze_script_tos_key=task.analyze_script_tos_key,
        asr_result_tos_key=task.asr_result_tos_key,
        active_edit_id=task.active_edit_id,
        finalize_source_edit_id=task.finalize_source_edit_id,
        final_video_tos_key=task.final_video_tos_key,
        groundtruth_tos_key=task.groundtruth_tos_key,
        feed_to_ai=task.feed_to_ai,
        output_mode=smart_cut_domain.OutputMode(task.output_mode) if task.output_mode else smart_cut_domain.OutputMode.ORIGINAL,
        last_scheduler_task_id=task.last_scheduler_task_id,
    )


def _to_domain_edit(edit: models.SmartCutEdit) -> smart_cut_domain.SmartCutEditRecord:
    """将 Edit ORM 模型转换为领域记录"""
    return smart_cut_domain.SmartCutEditRecord(
        id=edit.id,
        task_id=edit.task_id,
        edited_script=edit.edited_script,
        status=smart_cut_domain.EditStatus(edit.status),
        created_at=edit.created_at,
        updated_at=edit.updated_at,
        audio_b_tos_key=edit.audio_b_tos_key,
        edited_delay_cuts_tos_key=edit.edited_delay_cuts_tos_key,
        pause_cuts_on_original_tos_key=edit.pause_cuts_on_original_tos_key,
        error_message=edit.error_message,
    )


def start_preview_stage(
    db: DbSession,
    task_id: str,
    user_id: int,
    edited_script: str,
) -> tuple[models.SmartCutTask, models.SmartCutEdit, models.SchedulerTask]:
    """
    启动 preview 阶段

    职责:
        1. 验证任务状态为 waiting_user
        2. 创建新的 Edit 记录
        3. 创建 smart_cut_preview 调度任务
        4. 更新业务任务状态为 previewing
        5. 触发调度 tick（失败不影响已提交的事务）

    事务行为（真正的原子事务）：
        - 所有数据库操作在同一个事务中，最后统一 commit
        - 如果任何步骤失败，整个事务回滚，不会出现部分提交
        - dispatch_tick 在事务提交后调用，失败不影响已创建的任务

    Returns:
        (smart_cut_task, edit, scheduler_task)
    """
    from app import scheduler_service

    task = crud.get_smart_cut_task(db, task_id)
    if task is None:
        raise SmartCutError(f"Task {task_id} not found")
    if task.user_id != user_id:
        raise SmartCutError(f"Task {task_id} does not belong to user")
    if task.status != SmartCutStatus.WAITING_USER.value:
        raise SmartCutError(f"Cannot start preview from status {task.status}")

    now = datetime.now(timezone.utc)
    edit_id = f"sce-{uuid.uuid4().hex[:12]}"

    # 创建调度任务 payload
    input_payload = {
        "smart_cut_task_id": task.id,
        "edit_id": edit_id,
        "edited_script": edited_script,
        "original_video_tos_key": task.original_video_tos_key,
        "asr_result_tos_key": task.asr_result_tos_key,
        "analyze_script": task.analyze_script,
        "stage": "preview",
    }

    try:
        # 【事务包裹】所有操作在同一个事务中
        # 1. 创建调度任务（不提交）
        scheduler_task = scheduler_service.create_scheduler_task(
            db,
            user_id=user_id,
            page_key=f"smart-cut-{task.id}",
            task_type="smart_cut_preview",
            step_total=1,
            needs_post=False,
            input_payload=input_payload,
            now=now,
            commit=False,  # 关键：不单独提交
        )

        # 2. 创建 Edit 记录（不提交）
        edit = crud.create_smart_cut_edit_no_commit(db, edit_id, task_id, edited_script)
        # 直接更新状态为 processing（不调用会 commit 的 update 函数）
        edit.status = "processing"
        edit.updated_at = now

        # 3. 更新业务任务状态（不提交）
        task.status = SmartCutStatus.PREVIEWING.value
        task.active_edit_id = edit_id
        task.last_scheduler_task_id = scheduler_task.task_id
        task.updated_at = now

        # 4. 【统一提交】真正的原子事务点
        db.commit()
        db.refresh(task)
        db.refresh(edit)
        db.refresh(scheduler_task)

    except Exception as exc:
        db.rollback()
        raise SmartCutError(f"Failed to create preview task: {exc}") from exc

    # 触发调度 tick（在事务提交后，失败不影响已创建的任务）
    try:
        scheduler_service.dispatch_tick(db)
    except Exception:
        # dispatch_tick 失败不应影响 API 返回，记录日志即可
        # 调度器会在下次 tick 时处理待分配任务
        pass

    return task, edit, scheduler_task


def complete_preview_stage(
    db: DbSession,
    task_id: str,
    scheduler_task_id: str,
    worker_id: str,
    worker_token: str,
    edit_id: str,
    audio_b_tos_key: str,
    edited_delay_cuts_tos_key: str,
    pause_cuts_on_original_tos_key: str,
) -> models.SmartCutTask:
    """
    Worker 完成 preview 后调用此函数更新业务任务状态

    安全校验：
        1. 验证 X-Worker-Token 与 Worker 注册时存储的 hashed_token 匹配
        2. 验证 scheduler_task_id 匹配 last_scheduler_task_id
        3. 验证 worker_id 是当前被分配的 worker
        4. 验证 edit_id 是当前的 active_edit_id

    事务行为（真正的原子事务）：
        - Edit 更新、Task 更新、SchedulerTask 完成、Worker 释放都在同一个事务中
        - 如果任何步骤失败，整个事务回滚

    Args:
        task_id: Smart Cut 业务任务 ID
        scheduler_task_id: 调度任务 ID（用于验证）
        worker_id: Worker ID（用于验证）
        worker_token: Worker Token（从 X-Worker-Token header 获取）
        edit_id: Edit 记录 ID
        audio_b_tos_key: Audio B 在 TOS 中的 key
        edited_delay_cuts_tos_key: Edited delay cuts 在 TOS 中的 key
        pause_cuts_on_original_tos_key: Pause cuts on original 在 TOS 中的 key

    Returns:
        更新后的业务任务

    Raises:
        SmartCutError: 业务逻辑错误
        WorkerTokenError: 安全验证失败
    """
    from app.worker_auth import authenticate_worker_callback, verify_callback_matches_scheduler_task
    from app.scheduler_service import (
        get_scheduler_task, get_worker,
        task_to_domain, device_to_domain,
        apply_task_domain, apply_device_domain,
    )
    from app.scheduler_domain import (
        worker_complete_execution,
        a_progress_after_post,
        worker_release_device,
    )

    task = crud.get_smart_cut_task(db, task_id)
    if task is None:
        raise SmartCutError(f"Task {task_id} not found")
    if task.status != SmartCutStatus.PREVIEWING.value:
        raise SmartCutError(f"Task is not in previewing state, current: {task.status}")

    # 验证 edit_id 是当前的 active_edit_id
    if task.active_edit_id != edit_id:
        raise SmartCutError(f"Edit mismatch: active={task.active_edit_id}, got={edit_id}")

    # 安全验证 1: 回调的调度任务是否匹配
    scheduler_task = verify_callback_matches_scheduler_task(db, task, scheduler_task_id)

    # 安全验证 2: Worker 身份和任务分配（包含 Token 验证）
    authenticate_worker_callback(db, worker_id, worker_token, scheduler_task_id)

    # 获取 Worker 对象
    worker = get_worker(db, worker_id)
    if worker is None:
        raise SmartCutError(f"Worker {worker_id} not found")

    now = datetime.now(timezone.utc)

    try:
        # 【事务包裹】所有更新在同一个事务中
        # 1. 获取并更新 Edit 记录（不提交）
        edit = crud.get_smart_cut_edit(db, edit_id)
        if edit is None:
            raise SmartCutError(f"Edit {edit_id} not found")
        
        edit.status = "success"
        edit.audio_b_tos_key = audio_b_tos_key
        edit.edited_delay_cuts_tos_key = edited_delay_cuts_tos_key
        edit.pause_cuts_on_original_tos_key = pause_cuts_on_original_tos_key
        edit.updated_at = now

        # 2. 更新业务任务状态（不提交）
        task.status = SmartCutStatus.WAITING_USER.value
        task.current_stage = "preview_done"
        task.finalize_source_edit_id = edit_id  # 记录最后一次成功 preview
        task.updated_at = now

        # 3. 【新增】完成调度任务（Worker running -> post -> idle, Task running -> finished）
        scheduler_domain_task = task_to_domain(scheduler_task)
        scheduler_domain_worker = device_to_domain(worker)

        # Worker 完成执行 -> POST
        result = worker_complete_execution(
            scheduler_domain_task, scheduler_domain_worker, now
        )
        apply_device_domain(worker, result.device)
        scheduler_domain_worker = result.device  # 更新 domain 对象

        # Task 推进 -> FINISHED (因为 needs_post=False, step_index+1 == step_total)
        result = a_progress_after_post(
            scheduler_domain_task, scheduler_domain_worker, now
        )
        apply_task_domain(scheduler_task, result.task)
        scheduler_domain_task = result.task  # 更新 domain 对象

        # Worker 释放 -> IDLE
        result = worker_release_device(
            scheduler_domain_task, scheduler_domain_worker, now
        )
        apply_device_domain(worker, result.device)

        # 4. 【统一提交】真正的原子事务点
        db.commit()
        db.refresh(task)
        db.refresh(edit)
        db.refresh(scheduler_task)
        db.refresh(worker)

    except Exception as exc:
        db.rollback()
        raise SmartCutError(f"Failed to complete preview: {exc}") from exc

    return task


def fail_preview_stage(
    db: DbSession,
    task_id: str,
    scheduler_task_id: str,
    worker_id: str,
    worker_token: str,
    edit_id: str,
    error_message: str,
    upload_failed: bool = False,
) -> models.SmartCutTask:
    """
    Worker preview 失败时调用此函数更新业务任务状态

    安全校验：
        1. 验证 X-Worker-Token 与 Worker 注册时存储的 hashed_token 匹配
        2. 验证 scheduler_task_id 匹配 last_scheduler_task_id
        3. 验证 worker_id 是当前被分配的 worker
        4. 验证 edit_id 是当前的 active_edit_id

    事务行为（真正的原子事务）：
        - Edit 更新、Task 更新、SchedulerTask 失败、Worker 释放都在同一个事务中
        - 如果任何步骤失败，整个事务回滚

    Args:
        task_id: Smart Cut 业务任务 ID
        scheduler_task_id: 调度任务 ID（用于验证）
        worker_id: Worker ID（用于验证）
        worker_token: Worker Token（从 X-Worker-Token header 获取）
        edit_id: Edit 记录 ID
        error_message: 错误信息
        upload_failed: 是否是上传失败

    Returns:
        更新后的业务任务

    Raises:
        SmartCutError: 业务逻辑错误
        WorkerTokenError: 安全验证失败
    """
    from app.worker_auth import authenticate_worker_callback, verify_callback_matches_scheduler_task
    from app.scheduler_service import (
        get_scheduler_task, get_worker,
        task_to_domain, device_to_domain,
        apply_task_domain, apply_device_domain,
    )
    from app.scheduler_domain import (
        worker_fail_task,
        a_mark_task_failed,
        worker_release_device,
    )

    task = crud.get_smart_cut_task(db, task_id)
    if task is None:
        raise SmartCutError(f"Task {task_id} not found")

    # 验证 edit_id 是当前的 active_edit_id（如果任务还在 previewing 状态）
    if task.status == SmartCutStatus.PREVIEWING.value and task.active_edit_id != edit_id:
        raise SmartCutError(f"Edit mismatch: active={task.active_edit_id}, got={edit_id}")

    # 安全验证 1: 回调的调度任务是否匹配
    scheduler_task = verify_callback_matches_scheduler_task(db, task, scheduler_task_id)

    # 安全验证 2: Worker 身份和任务分配（包含 Token 验证）
    authenticate_worker_callback(db, worker_id, worker_token, scheduler_task_id)

    # 获取 Worker 对象
    worker = get_worker(db, worker_id)
    if worker is None:
        raise SmartCutError(f"Worker {worker_id} not found")

    now = datetime.now(timezone.utc)

    error_stage = (
        "preview_upload_failed" if upload_failed else "preview_failed"
    )

    try:
        # 【事务包裹】所有更新在同一个事务中
        # 1. 获取并更新 Edit 记录为失败（不提交）
        edit = crud.get_smart_cut_edit(db, edit_id)
        if edit is None:
            raise SmartCutError(f"Edit {edit_id} not found")
        
        edit.status = "failed"
        edit.error_message = error_message
        edit.updated_at = now

        # 2. 更新业务任务状态（不提交）
        # 任务回到 waiting_user，但 finalize_source_edit_id 不更新
        task.status = SmartCutStatus.WAITING_USER.value
        task.error_stage = error_stage
        task.error_message = error_message
        task.updated_at = now

        # 3. 【新增】标记调度任务失败（Worker running -> error -> idle, Task running -> failed）
        scheduler_domain_task = task_to_domain(scheduler_task)
        scheduler_domain_worker = device_to_domain(worker)

        # Worker 标记失败 -> ERROR
        result = worker_fail_task(
            scheduler_domain_task, scheduler_domain_worker, now
        )
        apply_device_domain(worker, result.device)
        scheduler_domain_worker = result.device  # 更新 domain 对象

        # Task 标记失败 -> FAILED
        result = a_mark_task_failed(
            scheduler_domain_task, scheduler_domain_worker, now,
            error_code=error_stage,
            error_message=error_message,
        )
        apply_task_domain(scheduler_task, result.task)
        scheduler_domain_task = result.task  # 更新 domain 对象

        # 创建报警记录
        for alarm in result.alarms:
            alarm_row = models.SchedulerAlarm(
                alarm_type=alarm.alarm_type.value,
                task_id=alarm.task_id,
                worker_id=alarm.worker_id,
                current_state=alarm.current_state,
                message=alarm.message,
                created_at=alarm.created_at,
                handled=False,
            )
            db.add(alarm_row)

        # Worker 释放 -> IDLE
        result = worker_release_device(
            scheduler_domain_task, scheduler_domain_worker, now
        )
        apply_device_domain(worker, result.device)

        # 4. 【统一提交】真正的原子事务点
        db.commit()
        db.refresh(task)
        db.refresh(edit)
        db.refresh(scheduler_task)
        db.refresh(worker)

    except Exception as exc:
        db.rollback()
        raise SmartCutError(f"Failed to fail preview: {exc}") from exc

    return task
