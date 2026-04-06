import base64
import os

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from . import crud, models, schemas
from .database import Base, SessionLocal, engine
from .dependencies import get_current_user, get_db, require_admin
from .scheduler_domain import DeviceStatus
from .scheduler_service import (
    abandon_scheduler_task,
    close_expired_tasks,
    complete_post,
    continue_scheduler_task,
    create_scheduler_task,
    deserialize_json,
    dispatch_tick,
    emit_connection_alarm,
    get_resume_entry,
    get_scheduler_task,
    get_worker,
    inspect_post_stalled_tasks,
    list_alarms,
    record_worker_status,
    reconcile_tick,
    register_worker,
    suspend_scheduler_task,
)
from .smart_cut_service import (
    SmartCutError,
    complete_analyze_stage,
    complete_preview_stage,
    complete_upload,
    create_smart_cut_task,
    fail_analyze_stage,
    fail_preview_stage,
    get_task_detail,
    list_user_tasks,
    prepare_upload,
    start_analyze_stage,
    start_preview_stage,
)
from .security import hash_password, new_session_token, verify_password
from .tts import MinimaxAPIError, MinimaxConfigError, MinimaxTTSClient, MinimaxTimeoutError


app = FastAPI(title="website_aicut api")


def serialize_user(user: models.User) -> schemas.AuthUser:
    return schemas.AuthUser(
        id=user.id,
        username=user.username,
        role=user.role,
        company_id=user.company_id,
        company_name=user.company.name if user.company else None,
    )


def serialize_user_read(user: models.User) -> schemas.UserRead:
    return schemas.UserRead(
        id=user.id,
        username=user.username,
        role=user.role,
        company_id=user.company_id,
        company_name=user.company.name if user.company else None,
        created_at=user.created_at,
    )


def serialize_material_read(material: models.Material) -> schemas.MaterialRead:
    return schemas.MaterialRead(
        id=material.id,
        name=material.name,
        company_id=material.company_id,
        company_name=material.company.name,
        remark=material.remark,
        created_at=material.created_at,
    )


def serialize_scheduler_task(task: models.SchedulerTask) -> schemas.SchedulerTaskRead:
    return schemas.SchedulerTaskRead(
        task_id=task.task_id,
        user_id=task.user_id,
        page_key=task.page_key,
        task_type=task.task_type,
        status=task.status,
        assigned_worker_id=task.assigned_worker_id,
        step_index=task.step_index,
        step_total=task.step_total,
        workspace_uri=task.workspace_uri,
        input_payload=deserialize_json(task.input_payload),
        output_payload=deserialize_json(task.output_payload),
        keep_until=task.keep_until,
        needs_post=task.needs_post,
        last_error_code=task.last_error_code,
        last_error_message=task.last_error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def serialize_scheduler_worker(worker: models.SchedulerWorker) -> schemas.SchedulerWorkerRead:
    return schemas.SchedulerWorkerRead(
        worker_id=worker.worker_id,
        worker_name=worker.worker_name,
        supported_task_types=worker.supported_task_types,
        status=worker.status,
        current_task_id=worker.current_task_id,
        heartbeat_at=worker.heartbeat_at,
        created_at=worker.created_at,
    )


def scheduler_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    if "not found" in message:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    if "does not belong" in message:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "Malin123456")

    db = SessionLocal()
    try:
        existing = crud.get_user_by_username(db, admin_username)
        if existing is None:
            admin_user = models.User(
                username=admin_username,
                password_hash=hash_password(admin_password),
                role="admin",
                company_id=None,
            )
            db.add(admin_user)
            db.commit()
    finally:
        db.close()


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


@app.post("/auth/login", response_model=schemas.AuthResponse)
def login(payload: schemas.LoginRequest, response: Response, db: DbSession = Depends(get_db)):
    user = crud.get_user_by_username(db, payload.username.strip())
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = new_session_token()
    crud.create_session(db, token, user.id)

    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
        max_age=60 * 60 * 24 * 7,
    )
    return schemas.AuthResponse(user=serialize_user(user))


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: DbSession = Depends(get_db),
    session_token: str | None = Cookie(default=None),
):
    if session_token:
        crud.delete_session(db, session_token)
    response.delete_cookie("session_token", path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.get("/auth/me", response_model=schemas.AuthResponse)
def me(user: models.User = Depends(get_current_user)):
    return schemas.AuthResponse(user=serialize_user(user))


@app.post("/user/tts/generate", response_model=schemas.TTSGenerateResponse)
def generate_tts(
    payload: schemas.TTSGenerateRequest,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    try:
        result = MinimaxTTSClient().synthesize(payload.text)
    except MinimaxConfigError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except MinimaxTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except MinimaxAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    # 更新用户累计消耗
    usage_record = crud.add_user_usage(db, user.id, result.usage_characters)
    
    audio_base64 = base64.b64encode(result.audio_bytes).decode("ascii")
    return schemas.TTSGenerateResponse(
        audio_base64=audio_base64,
        mime_type=result.mime_type,
        file_name=result.file_name,
        usage_credits=result.usage_characters,
        usage_characters=result.usage_characters,
        monthly_total_used=usage_record.credits_used,
        monthly_limit=usage_record.credits_limit,
    )


@app.get("/admin/companies", response_model=list[schemas.CompanyRead])
def list_companies(_: models.User = Depends(require_admin), db: DbSession = Depends(get_db)):
    return crud.list_companies(db)


@app.post("/admin/companies", response_model=schemas.CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: schemas.CompanyCreate,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    if crud.get_company_by_name(db, payload.name.strip()) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company name already exists")
    return crud.create_company(db, payload.name)


@app.get("/admin/users", response_model=list[schemas.UserRead])
def list_users(_: models.User = Depends(require_admin), db: DbSession = Depends(get_db)):
    users = crud.list_users(db)
    return [serialize_user_read(user) for user in users]


@app.post("/admin/users", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: schemas.UserCreate,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    if crud.get_user_by_username(db, payload.username.strip()) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    if payload.company_id is not None and db.get(models.Company, payload.company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    user = crud.create_user(
        db=db,
        username=payload.username,
        password=payload.password,
        role=payload.role,
        company_id=payload.company_id,
    )
    return serialize_user_read(user)


@app.get("/admin/materials", response_model=list[schemas.MaterialRead])
def list_materials(_: models.User = Depends(require_admin), db: DbSession = Depends(get_db)):
    materials = crud.list_materials(db)
    return [serialize_material_read(material) for material in materials]


@app.post("/admin/materials", response_model=schemas.MaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: schemas.MaterialCreate,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    company = db.get(models.Company, payload.company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    existing = db.scalar(
        select(models.Material).where(
            models.Material.name == payload.name.strip(),
            models.Material.company_id == payload.company_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Material already exists for company")

    try:
        material = crud.create_material(db, payload.name, payload.company_id, payload.remark)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Material already exists") from exc
    return serialize_material_read(material)


@app.post("/scheduler/tasks", response_model=schemas.SchedulerTaskRead, status_code=status.HTTP_201_CREATED)
def create_scheduler_task_endpoint(
    payload: schemas.SchedulerTaskCreate,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    task = create_scheduler_task(
        db,
        user_id=user.id,
        page_key=payload.page_key,
        task_type=payload.task_type,
        step_total=payload.step_total,
        needs_post=payload.needs_post,
        input_payload=payload.input_payload,
    )
    return serialize_scheduler_task(task)


@app.get("/scheduler/tasks/{task_id}", response_model=schemas.SchedulerTaskRead)
def get_scheduler_task_endpoint(
    task_id: str,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    task = get_scheduler_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    if user.role != "admin" and task.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="task does not belong to user")
    return serialize_scheduler_task(task)


@app.get("/scheduler/resume-entry", response_model=schemas.SchedulerResumeEntry)
def get_scheduler_resume_entry(
    page_key: str,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    task = get_resume_entry(db, user_id=user.id, page_key=page_key)
    if task is None:
        return schemas.SchedulerResumeEntry(has_resume_task=False, task=None)
    return schemas.SchedulerResumeEntry(has_resume_task=True, task=serialize_scheduler_task(task))


@app.post("/scheduler/tasks/{task_id}/continue", response_model=schemas.SchedulerTaskRead)
def continue_scheduler_task_endpoint(
    task_id: str,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    try:
        task = continue_scheduler_task(db, task_id=task_id, user_id=user.id)
    except ValueError as exc:
        raise scheduler_error(exc) from exc
    dispatch_tick(db)
    refreshed = get_scheduler_task(db, task.task_id)
    assert refreshed is not None
    return serialize_scheduler_task(refreshed)


@app.post("/scheduler/tasks/{task_id}/suspend", response_model=schemas.SchedulerTaskRead)
def suspend_scheduler_task_endpoint(
    task_id: str,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    try:
        task = suspend_scheduler_task(db, task_id=task_id, user_id=user.id)
    except ValueError as exc:
        raise scheduler_error(exc) from exc
    return serialize_scheduler_task(task)


@app.post("/scheduler/tasks/{task_id}/abandon", response_model=schemas.SchedulerTaskRead)
def abandon_scheduler_task_endpoint(
    task_id: str,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    try:
        task = abandon_scheduler_task(db, task_id=task_id, user_id=user.id)
    except ValueError as exc:
        raise scheduler_error(exc) from exc
    return serialize_scheduler_task(task)


@app.post("/scheduler/admin/workers", response_model=schemas.SchedulerWorkerRead, status_code=status.HTTP_201_CREATED)
def register_scheduler_worker(
    payload: schemas.SchedulerWorkerCreate,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    worker = register_worker(
        db,
        worker_id=payload.worker_id,
        worker_name=payload.worker_name,
        supported_task_types=payload.supported_task_types,
    )
    return serialize_scheduler_worker(worker)


@app.get("/scheduler/admin/workers/{worker_id}", response_model=schemas.SchedulerWorkerRead)
def get_scheduler_worker(
    worker_id: str,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    worker = get_worker(db, worker_id)
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="worker not found")
    return serialize_scheduler_worker(worker)


@app.post("/scheduler/admin/dispatch-tick", response_model=list[schemas.SchedulerTaskRead])
def dispatch_scheduler_tick(
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    return [serialize_scheduler_task(task) for task in dispatch_tick(db)]


@app.post("/scheduler/admin/reconcile-tick", response_model=list[schemas.SchedulerTaskRead])
def reconcile_scheduler_tick(
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    return [serialize_scheduler_task(task) for task in reconcile_tick(db)]


@app.post("/scheduler/admin/tasks/{task_id}/complete-post", response_model=schemas.SchedulerTaskRead)
def complete_scheduler_post(
    task_id: str,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    try:
        task = complete_post(db, task_id=task_id)
    except ValueError as exc:
        raise scheduler_error(exc) from exc
    return serialize_scheduler_task(task)


@app.post("/scheduler/admin/tasks/close-expired", response_model=list[schemas.SchedulerTaskRead])
def close_scheduler_expired_tasks(
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    return [serialize_scheduler_task(task) for task in close_expired_tasks(db)]


@app.post("/scheduler/admin/alarms/connection", response_model=schemas.SchedulerAlarmRead, status_code=status.HTTP_201_CREATED)
def create_scheduler_connection_alarm(
    worker_id: str,
    kind: str,
    task_id: str | None = None,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    try:
        alarm = emit_connection_alarm(db, worker_id=worker_id, kind=kind, task_id=task_id)
    except ValueError as exc:
        raise scheduler_error(exc) from exc
    return alarm


@app.post("/scheduler/admin/alarms/post-stalled", response_model=list[schemas.SchedulerAlarmRead])
def create_scheduler_post_stalled_alarm(
    threshold_hours: int = 24,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    return inspect_post_stalled_tasks(db, threshold_hours=threshold_hours)


@app.get("/scheduler/admin/alarms", response_model=list[schemas.SchedulerAlarmRead])
def list_scheduler_alarms(
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    return list_alarms(db)


@app.post("/scheduler/workers/{worker_id}/status", response_model=schemas.SchedulerWorkerRead)
def update_scheduler_worker_status(
    worker_id: str,
    payload: schemas.SchedulerWorkerStatusUpdate,
    db: DbSession = Depends(get_db),
):
    try:
        worker = record_worker_status(
            db,
            worker_id=worker_id,
            new_status=DeviceStatus(payload.status),
            current_task_id=payload.current_task_id,
        )
    except ValueError as exc:
        raise scheduler_error(exc) from exc
    return serialize_scheduler_worker(worker)


# ============ Admin User Usage Management ============

@app.get("/admin/users/{user_id}/usage", response_model=schemas.UserUsageMonthlyRead)
def get_user_usage(
    user_id: int,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    """获取用户本月消耗统计"""
    usage = crud.get_user_usage(db, user_id)
    if not usage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usage record not found")
    return usage


@app.patch("/admin/users/{user_id}/usage", response_model=schemas.UserUsageMonthlyRead)
def update_user_usage_limit(
    user_id: int,
    payload: schemas.UserUsageMonthlyUpdate,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    """管理员调整用户消耗限额"""
    usage = crud.update_user_usage_limit(db, user_id, payload.credits_limit)
    if not usage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usage record not found")
    return usage


@app.post("/admin/users/{user_id}/usage/adjust", response_model=schemas.UserUsageMonthlyRead)
def adjust_user_usage_credits(
    user_id: int,
    payload: schemas.UserUsageMonthlyAdjust,
    _: models.User = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    """管理员手动调整用户已消耗额度（正数为增加，负数为减少）"""
    usage = crud.adjust_user_usage_credits(db, user_id, payload.delta)
    if not usage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usage record not found")
    return usage


@app.get("/user/usage", response_model=schemas.UserUsageMonthlyRead)
def get_current_user_usage(
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    """获取当前用户本月消耗统计"""
    from datetime import datetime
    year_month = datetime.now().strftime("%Y-%m")
    
    usage = crud.get_or_create_user_usage(db, user.id, year_month)
    return usage


# ============================================
# Smart Cut API (F03)
# ============================================


def serialize_smart_cut_task(task: models.SmartCutTask) -> schemas.SmartCutTaskRead:
    """序列化 Smart Cut 任务"""
    return schemas.SmartCutTaskRead(
        id=task.id,
        user_id=task.user_id,
        status=task.status,
        current_stage=task.current_stage,
        error_stage=task.error_stage,
        error_message=task.error_message,
        original_video_url=task.original_video_url,
        original_video_tos_key=task.original_video_tos_key,
        reference_text_url=task.reference_text_url,
        reference_text_tos_key=task.reference_text_tos_key,
        analyze_script=task.analyze_script,
        analyze_script_tos_key=task.analyze_script_tos_key,
        asr_result_tos_key=task.asr_result_tos_key,
        active_edit_id=task.active_edit_id,
        finalize_source_edit_id=task.finalize_source_edit_id,
        final_video_url=task.final_video_url,
        final_video_tos_key=task.final_video_tos_key,
        groundtruth_url=task.groundtruth_url,
        groundtruth_tos_key=task.groundtruth_tos_key,
        feed_to_ai=task.feed_to_ai,
        output_mode=task.output_mode,
        last_scheduler_task_id=task.last_scheduler_task_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def smart_cut_error(exc: SmartCutError) -> HTTPException:
    """Smart Cut 错误转换"""
    message = str(exc)
    if "not found" in message:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    if "does not belong" in message:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


@app.post("/api/smart-cut/tasks", response_model=schemas.SmartCutTaskRead, status_code=status.HTTP_201_CREATED)
def api_create_smart_cut_task(
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    """创建 Smart Cut 业务任务"""
    task = create_smart_cut_task(db, user_id=user.id)
    return serialize_smart_cut_task(task)


@app.get("/api/smart-cut/tasks", response_model=list[schemas.SmartCutTaskSummary])
def api_list_smart_cut_tasks(
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    """获取用户的 Smart Cut 任务列表"""
    tasks = list_user_tasks(db, user_id=user.id)
    return [
        schemas.SmartCutTaskSummary(
            id=task.id,
            status=task.status,
            current_stage=task.current_stage,
            active_edit_id=task.active_edit_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in tasks
    ]


@app.get("/api/smart-cut/tasks/{task_id}", response_model=schemas.SmartCutTaskRead)
def api_get_smart_cut_task(
    task_id: str,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    """获取 Smart Cut 任务详情"""
    try:
        task = get_task_detail(db, task_id=task_id, user_id=user.id)
    except SmartCutError as exc:
        raise smart_cut_error(exc) from exc
    return serialize_smart_cut_task(task)


@app.post("/api/smart-cut/tasks/{task_id}/upload-prepare", response_model=schemas.SmartCutUploadPrepareResponse)
def api_prepare_upload(
    task_id: str,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
    video_ext: str = "mp4",
):
    """
    准备上传

    返回视频和文案的上传 key
    """
    try:
        result = prepare_upload(db, task_id=task_id, user_id=user.id, video_ext=video_ext)
    except SmartCutError as exc:
        raise smart_cut_error(exc) from exc
    return schemas.SmartCutUploadPrepareResponse(
        task_id=result["task_id"],
        video_upload_key=result["video_upload_key"],
        text_upload_key=result["text_upload_key"],
    )


@app.post("/api/smart-cut/tasks/{task_id}/upload-complete", response_model=schemas.SmartCutUploadCompleteResponse)
def api_complete_upload(
    task_id: str,
    payload: schemas.SmartCutUploadCompleteRequest,
    use_fake_tos: bool = True,  # 查询参数，默认使用 Fake TOS
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    """
    完成上传

    验证 key 归属和对象存在性，通过后推进任务到 ready_analyze

    Args:
        use_fake_tos: 使用 Fake TOS（测试模式）还是真实 TOS
                     - true: 使用宿主机挂载的 Fake TOS 目录
                     - false: 使用真实火山引擎 TOS（需要配置环境变量）
    """
    try:
        task = complete_upload(
            db,
            task_id=task_id,
            user_id=user.id,
            video_key=payload.video_key,
            text_key=payload.text_key,
            use_fake_tos=use_fake_tos,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except SmartCutError as exc:
        raise smart_cut_error(exc) from exc
    return schemas.SmartCutUploadCompleteResponse(
        success=True,
        message="Upload completed successfully",
    )


@app.post("/api/smart-cut/tasks/{task_id}/analyze", response_model=schemas.SmartCutTaskRead)
def api_start_analyze(
    task_id: str,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    """
    启动 analyze 阶段

    创建 smart_cut_analyze 调度任务，业务任务进入 analyzing 状态
    """
    try:
        task, scheduler_task = start_analyze_stage(
            db,
            task_id=task_id,
            user_id=user.id,
        )
    except SmartCutError as exc:
        raise smart_cut_error(exc) from exc
    return serialize_smart_cut_task(task)


@app.post("/api/smart-cut/internal/tasks/{task_id}/analyze-complete", response_model=schemas.SmartCutTaskRead)
def api_complete_analyze(
    task_id: str,
    payload: dict,
    request: Request,
    db: DbSession = Depends(get_db),
):
    """
    Worker 完成 analyze 后回调此接口

    内部接口，由 Worker 调用更新业务任务状态
    需要验证：
        - X-Worker-Token header: Worker 注册时获取的 token
        - scheduler_task_id: 必须匹配 last_scheduler_task_id
        - worker_id: 必须是被分配的 worker
    """
    from app.worker_auth import WorkerTokenError

    # 从 Header 获取 Worker Token
    worker_token = request.headers.get("X-Worker-Token", "")
    if not worker_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Worker-Token header",
        )

    # 参数校验
    scheduler_task_id = payload.get("scheduler_task_id")
    worker_id = payload.get("worker_id")
    if not scheduler_task_id or not worker_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: scheduler_task_id, worker_id",
        )

    try:
        task = complete_analyze_stage(
            db,
            task_id=task_id,
            scheduler_task_id=scheduler_task_id,
            worker_id=worker_id,
            worker_token=worker_token,
            script=payload.get("script", ""),
            script_tos_key=payload.get("script_tos_key", ""),
            asr_result_tos_key=payload.get("asr_result_tos_key", ""),
        )
    except WorkerTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except SmartCutError as exc:
        raise smart_cut_error(exc) from exc
    return serialize_smart_cut_task(task)


@app.post("/api/smart-cut/internal/tasks/{task_id}/analyze-fail", response_model=schemas.SmartCutTaskRead)
def api_fail_analyze(
    task_id: str,
    payload: dict,
    request: Request,
    db: DbSession = Depends(get_db),
):
    """
    Worker analyze 失败后回调此接口

    内部接口，由 Worker 调用更新业务任务状态为失败
    需要验证：
        - X-Worker-Token header: Worker 注册时获取的 token
        - scheduler_task_id: 必须匹配 last_scheduler_task_id
        - worker_id: 必须是被分配的 worker
    """
    from app.worker_auth import WorkerTokenError

    # 从 Header 获取 Worker Token
    worker_token = request.headers.get("X-Worker-Token", "")
    if not worker_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Worker-Token header",
        )

    # 参数校验
    scheduler_task_id = payload.get("scheduler_task_id")
    worker_id = payload.get("worker_id")
    if not scheduler_task_id or not worker_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: scheduler_task_id, worker_id",
        )

    try:
        task = fail_analyze_stage(
            db,
            task_id=task_id,
            scheduler_task_id=scheduler_task_id,
            worker_id=worker_id,
            worker_token=worker_token,
            error_message=payload.get("error_message", "Unknown error"),
            error_stage=payload.get("error_stage", "analyze_failed"),
        )
    except WorkerTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except SmartCutError as exc:
        raise smart_cut_error(exc) from exc
    return serialize_smart_cut_task(task)


# ============================================
# F05: Preview Stage And Edit History
# ============================================


@app.post("/api/smart-cut/tasks/{task_id}/preview", response_model=schemas.SmartCutTaskRead)
def api_start_preview(
    task_id: str,
    payload: schemas.SmartCutPreviewRequest,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    """
    启动 preview 阶段

    创建新的 Edit 记录和 smart_cut_preview 调度任务
    业务任务进入 previewing 状态
    """
    try:
        task, edit, scheduler_task = start_preview_stage(
            db,
            task_id=task_id,
            user_id=user.id,
            edited_script=payload.edited_script,
        )
    except SmartCutError as exc:
        raise smart_cut_error(exc) from exc
    return serialize_smart_cut_task(task)


@app.post("/api/smart-cut/internal/tasks/{task_id}/preview-complete", response_model=schemas.SmartCutTaskRead)
def api_complete_preview(
    task_id: str,
    payload: dict,
    request: Request,
    db: DbSession = Depends(get_db),
):
    """
    Worker 完成 preview 后回调此接口

    内部接口，由 Worker 调用更新业务任务状态
    需要验证：
        - X-Worker-Token header: Worker 注册时获取的 token
        - scheduler_task_id: 必须匹配 last_scheduler_task_id
        - worker_id: 必须是被分配的 worker
        - edit_id: 必须匹配 active_edit_id
    """
    from app.worker_auth import WorkerTokenError

    # 从 Header 获取 Worker Token
    worker_token = request.headers.get("X-Worker-Token", "")
    if not worker_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Worker-Token header",
        )

    # 参数校验
    scheduler_task_id = payload.get("scheduler_task_id")
    worker_id = payload.get("worker_id")
    edit_id = payload.get("edit_id")
    if not scheduler_task_id or not worker_id or not edit_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: scheduler_task_id, worker_id, edit_id",
        )

    try:
        task = complete_preview_stage(
            db,
            task_id=task_id,
            scheduler_task_id=scheduler_task_id,
            worker_id=worker_id,
            worker_token=worker_token,
            edit_id=edit_id,
            audio_b_tos_key=payload.get("audio_b_tos_key", ""),
            edited_delay_cuts_tos_key=payload.get("edited_delay_cuts_tos_key", ""),
            pause_cuts_on_original_tos_key=payload.get("pause_cuts_on_original_tos_key", ""),
        )
    except WorkerTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except SmartCutError as exc:
        raise smart_cut_error(exc) from exc
    return serialize_smart_cut_task(task)


@app.post("/api/smart-cut/internal/tasks/{task_id}/preview-fail", response_model=schemas.SmartCutTaskRead)
def api_fail_preview(
    task_id: str,
    payload: dict,
    request: Request,
    db: DbSession = Depends(get_db),
):
    """
    Worker preview 失败后回调此接口

    内部接口，由 Worker 调用更新业务任务状态
    需要验证：
        - X-Worker-Token header: Worker 注册时获取的 token
        - scheduler_task_id: 必须匹配 last_scheduler_task_id
        - worker_id: 必须是被分配的 worker
        - edit_id: 必须匹配 active_edit_id
    """
    from app.worker_auth import WorkerTokenError

    # 从 Header 获取 Worker Token
    worker_token = request.headers.get("X-Worker-Token", "")
    if not worker_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Worker-Token header",
        )

    # 参数校验
    scheduler_task_id = payload.get("scheduler_task_id")
    worker_id = payload.get("worker_id")
    edit_id = payload.get("edit_id")
    if not scheduler_task_id or not worker_id or not edit_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: scheduler_task_id, worker_id, edit_id",
        )

    try:
        task = fail_preview_stage(
            db,
            task_id=task_id,
            scheduler_task_id=scheduler_task_id,
            worker_id=worker_id,
            worker_token=worker_token,
            edit_id=edit_id,
            error_message=payload.get("error_message", "Unknown error"),
            upload_failed=payload.get("upload_failed", False),
        )
    except WorkerTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except SmartCutError as exc:
        raise smart_cut_error(exc) from exc
    return serialize_smart_cut_task(task)


@app.get("/api/smart-cut/tasks/{task_id}/edits", response_model=list[schemas.SmartCutEditRead])
def api_list_edits(
    task_id: str,
    user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    """
    获取任务的 Edit 历史列表

    按时间倒序返回所有 Edit 记录，包含 audio_b 的预签名 URL
    """
    from app.tos_service import get_tos_client

    # 验证任务存在且属于当前用户
    task = crud.get_smart_cut_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    if task.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Task {task_id} does not belong to user",
        )

    # 获取 TOS 客户端生成预签名 URL
    tos_client = get_tos_client(use_fake=True)

    edits = crud.list_smart_cut_edits_by_task(db, task_id)
    result = []
    for edit in edits:
        # 生成 audio_b 的预签名 URL
        audio_b_url = None
        if edit.audio_b_tos_key:
            try:
                audio_b_url = tos_client.generate_presigned_url(edit.audio_b_tos_key)
            except Exception:
                # 如果生成失败，保持 None
                pass
        
        result.append(
            schemas.SmartCutEditRead(
                id=edit.id,
                task_id=edit.task_id,
                edited_script=edit.edited_script,
                status=edit.status,
                audio_b_url=audio_b_url,
                audio_b_tos_key=edit.audio_b_tos_key,
                edited_delay_cuts_tos_key=edit.edited_delay_cuts_tos_key,
                pause_cuts_on_original_tos_key=edit.pause_cuts_on_original_tos_key,
                error_message=edit.error_message,
                created_at=edit.created_at,
                updated_at=edit.updated_at,
            )
        )
    return result
