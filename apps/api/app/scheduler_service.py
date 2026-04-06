from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from . import models
from .scheduler_domain import (
    AlarmRecord,
    DeviceRecord,
    DeviceStatus,
    TaskRecord,
    TaskStatus,
    abandon_task,
    a_mark_task_failed,
    a_mark_task_running,
    a_progress_after_post,
    assign_task_to_worker,
    close_expired_task,
    complete_post_task,
    continue_task,
    create_task,
    dispatch_pending_tasks,
    find_resume_task,
    handshake_alarm,
    heartbeat_alarm,
    post_stalled_alarm,
    suspend_task,
    worker_accept_task,
    worker_complete_execution,
    worker_fail_task,
    worker_release_device,
    worker_start_task,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def serialize_json(value: dict | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def deserialize_json(value: str | None) -> dict | None:
    if not value:
        return None
    return json.loads(value)


def task_to_domain(task: models.SchedulerTask) -> TaskRecord:
    return TaskRecord(
        task_id=task.task_id,
        user_id=task.user_id,
        page_key=task.page_key,
        task_type=task.task_type,
        status=TaskStatus(task.status),
        created_at=task.created_at,
        updated_at=task.updated_at,
        step_index=task.step_index,
        step_total=task.step_total,
        assigned_worker_id=task.assigned_worker_id,
        workspace_uri=task.workspace_uri,
        keep_until=task.keep_until,
        needs_post=task.needs_post,
        input_payload=deserialize_json(task.input_payload),
        output_payload=deserialize_json(task.output_payload),
        last_error_code=task.last_error_code,
        last_error_message=task.last_error_message,
    )


def device_to_domain(worker: models.SchedulerWorker) -> DeviceRecord:
    return DeviceRecord(
        worker_id=worker.worker_id,
        worker_name=worker.worker_name,
        supported_task_types=tuple(worker.supported_task_types or []),
        status=DeviceStatus(worker.status),
        heartbeat_at=worker.heartbeat_at,
        current_task_id=worker.current_task_id,
    )


def apply_task_domain(task: models.SchedulerTask, domain: TaskRecord) -> None:
    task.status = domain.status.value
    task.updated_at = domain.updated_at
    task.step_index = domain.step_index
    task.step_total = domain.step_total
    task.assigned_worker_id = domain.assigned_worker_id
    task.workspace_uri = domain.workspace_uri
    task.keep_until = domain.keep_until
    task.needs_post = domain.needs_post
    task.input_payload = serialize_json(domain.input_payload)
    task.output_payload = serialize_json(domain.output_payload)
    task.last_error_code = domain.last_error_code
    task.last_error_message = domain.last_error_message


def apply_device_domain(worker: models.SchedulerWorker, domain: DeviceRecord) -> None:
    worker.worker_name = domain.worker_name
    worker.supported_task_types = list(domain.supported_task_types)
    worker.status = domain.status.value
    worker.heartbeat_at = domain.heartbeat_at
    worker.current_task_id = domain.current_task_id


def create_alarm(db: DbSession, alarm: AlarmRecord) -> models.SchedulerAlarm:
    row = models.SchedulerAlarm(
        alarm_type=alarm.alarm_type.value,
        task_id=alarm.task_id,
        worker_id=alarm.worker_id,
        current_state=alarm.current_state,
        message=alarm.message,
        created_at=alarm.created_at,
        handled=False,
    )
    db.add(row)
    return row


def get_scheduler_task(db: DbSession, task_id: str) -> models.SchedulerTask | None:
    return db.scalar(select(models.SchedulerTask).where(models.SchedulerTask.task_id == task_id))


def get_worker(db: DbSession, worker_id: str) -> models.SchedulerWorker | None:
    return db.scalar(select(models.SchedulerWorker).where(models.SchedulerWorker.worker_id == worker_id))


def list_tasks(db: DbSession) -> list[models.SchedulerTask]:
    return list(db.scalars(select(models.SchedulerTask).order_by(models.SchedulerTask.created_at.asc(), models.SchedulerTask.task_id.asc())))


def list_workers(db: DbSession) -> list[models.SchedulerWorker]:
    return list(db.scalars(select(models.SchedulerWorker).order_by(models.SchedulerWorker.worker_id.asc())))


def list_alarms(db: DbSession) -> list[models.SchedulerAlarm]:
    return list(db.scalars(select(models.SchedulerAlarm).order_by(models.SchedulerAlarm.created_at.asc(), models.SchedulerAlarm.id.asc())))


def create_scheduler_task(
    db: DbSession,
    *,
    user_id: int,
    page_key: str,
    task_type: str,
    step_total: int = 1,
    needs_post: bool = False,
    input_payload: dict | None = None,
    now: datetime | None = None,
    commit: bool = True,
) -> models.SchedulerTask:
    current_now = now or utcnow()
    task_id = f"task-{uuid4().hex[:12]}"
    domain = create_task(
        task_id=task_id,
        user_id=user_id,
        page_key=page_key,
        task_type=task_type,
        created_at=current_now,
        step_total=step_total,
        needs_post=needs_post,
        input_payload=input_payload,
    )
    row = models.SchedulerTask(
        task_id=domain.task_id,
        user_id=domain.user_id,
        page_key=domain.page_key,
        task_type=domain.task_type,
        status=domain.status.value,
        assigned_worker_id=domain.assigned_worker_id,
        step_index=domain.step_index,
        step_total=domain.step_total,
        workspace_uri=domain.workspace_uri,
        input_payload=serialize_json(domain.input_payload),
        output_payload=serialize_json(domain.output_payload),
        created_at=domain.created_at,
        updated_at=domain.updated_at,
        keep_until=domain.keep_until,
        needs_post=domain.needs_post,
        last_error_code=domain.last_error_code,
        last_error_message=domain.last_error_message,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    return row


def register_worker(
    db: DbSession,
    *,
    worker_id: str,
    worker_name: str,
    supported_task_types: list[str],
    now: datetime | None = None,
) -> models.SchedulerWorker:
    row = get_worker(db, worker_id)
    current_now = now or utcnow()
    if row is None:
        row = models.SchedulerWorker(
            worker_id=worker_id,
            worker_name=worker_name,
            supported_task_types=supported_task_types,
            status=DeviceStatus.IDLE.value,
            heartbeat_at=current_now,
            current_task_id=None,
        )
        db.add(row)
    else:
        row.worker_name = worker_name
        row.supported_task_types = supported_task_types
        row.heartbeat_at = current_now
    db.commit()
    db.refresh(row)
    return row


def dispatch_tick(db: DbSession, *, now: datetime | None = None) -> list[models.SchedulerTask]:
    current_now = now or utcnow()
    tasks = list_tasks(db)
    workers = list_workers(db)
    decisions = dispatch_pending_tasks([task_to_domain(task) for task in tasks], [device_to_domain(worker) for worker in workers], current_now)
    updated: list[models.SchedulerTask] = []
    for decision in decisions:
        if decision.task is None:
            continue
        row = get_scheduler_task(db, decision.task.task_id)
        if row is None:
            continue
        apply_task_domain(row, decision.task)
        updated.append(row)
    db.commit()
    for row in updated:
        db.refresh(row)
    return updated


def reconcile_tick(db: DbSession, *, now: datetime | None = None) -> list[models.SchedulerTask]:
    current_now = now or utcnow()
    updated: list[models.SchedulerTask] = []
    tasks_by_id = {task.task_id: task for task in list_tasks(db)}
    workers_by_id = {worker.worker_id: worker for worker in list_workers(db)}

    for task in tasks_by_id.values():
        domain_task = task_to_domain(task)
        if not task.assigned_worker_id:
            continue
        worker = workers_by_id.get(task.assigned_worker_id)
        if worker is None:
            continue
        domain_worker = device_to_domain(worker)

        result = None
        if domain_task.status == TaskStatus.ASSIGNED and domain_worker.status == DeviceStatus.RUNNING:
            result = a_mark_task_running(domain_task, domain_worker, current_now)
        elif domain_task.status == TaskStatus.RUNNING and domain_worker.status == DeviceStatus.POST:
            result = a_progress_after_post(domain_task, domain_worker, current_now)
        elif domain_task.status in {TaskStatus.ASSIGNED, TaskStatus.RUNNING} and domain_worker.status == DeviceStatus.ERROR:
            result = a_mark_task_failed(domain_task, domain_worker, current_now)

        if result is None or result.task is None:
            continue
        apply_task_domain(task, result.task)
        for alarm in result.alarms:
            create_alarm(db, alarm)
        updated.append(task)

    db.commit()
    for task in updated:
        db.refresh(task)
    return updated


def get_resume_entry(db: DbSession, *, user_id: int, page_key: str, now: datetime | None = None) -> models.SchedulerTask | None:
    current_now = now or utcnow()
    tasks = [task_to_domain(task) for task in list_tasks(db)]
    candidate = find_resume_task(tasks, user_id=user_id, page_key=page_key, now=current_now)
    if candidate is None:
        return None
    return get_scheduler_task(db, candidate.task_id)


def continue_scheduler_task(db: DbSession, *, task_id: str, user_id: int, now: datetime | None = None) -> models.SchedulerTask:
    row = get_scheduler_task(db, task_id)
    if row is None:
        raise ValueError("task not found")
    if row.user_id != user_id:
        raise ValueError("task does not belong to user")
    result = continue_task(task_to_domain(row), now or utcnow())
    if result.task is None:
        raise ValueError("continue produced no task result")
    apply_task_domain(row, result.task)
    db.commit()
    db.refresh(row)
    return row


def suspend_scheduler_task(db: DbSession, *, task_id: str, user_id: int, now: datetime | None = None) -> models.SchedulerTask:
    row = get_scheduler_task(db, task_id)
    if row is None:
        raise ValueError("task not found")
    if row.user_id != user_id:
        raise ValueError("task does not belong to user")
    result = suspend_task(task_to_domain(row), now or utcnow())
    if result.task is None:
        raise ValueError("suspend produced no task result")
    apply_task_domain(row, result.task)
    db.commit()
    db.refresh(row)
    return row


def abandon_scheduler_task(db: DbSession, *, task_id: str, user_id: int, now: datetime | None = None) -> models.SchedulerTask:
    row = get_scheduler_task(db, task_id)
    if row is None:
        raise ValueError("task not found")
    if row.user_id != user_id:
        raise ValueError("task does not belong to user")
    result = abandon_task(task_to_domain(row), now or utcnow())
    if result.task is None:
        raise ValueError("abandon produced no task result")
    apply_task_domain(row, result.task)
    db.commit()
    db.refresh(row)
    return row


def close_expired_tasks(db: DbSession, *, now: datetime | None = None) -> list[models.SchedulerTask]:
    current_now = now or utcnow()
    updated: list[models.SchedulerTask] = []
    for row in list_tasks(db):
        if row.status != TaskStatus.SUSPENDED.value:
            continue
        try:
            result = close_expired_task(task_to_domain(row), current_now)
        except ValueError:
            continue
        if result.task is None:
            continue
        apply_task_domain(row, result.task)
        updated.append(row)
    db.commit()
    for row in updated:
        db.refresh(row)
    return updated


def complete_post(db: DbSession, *, task_id: str, now: datetime | None = None) -> models.SchedulerTask:
    row = get_scheduler_task(db, task_id)
    if row is None:
        raise ValueError("task not found")
    result = complete_post_task(task_to_domain(row), now or utcnow())
    if result.task is None:
        raise ValueError("post completion produced no task result")
    apply_task_domain(row, result.task)
    db.commit()
    db.refresh(row)
    return row


def record_worker_status(
    db: DbSession,
    *,
    worker_id: str,
    new_status: DeviceStatus,
    current_task_id: str | None = None,
    worker_name: str | None = None,
    supported_task_types: list[str] | None = None,
    now: datetime | None = None,
) -> models.SchedulerWorker:
    row = get_worker(db, worker_id)
    if row is None:
        if new_status != DeviceStatus.IDLE:
            raise ValueError("worker must be registered before active transitions")
        row = register_worker(
            db,
            worker_id=worker_id,
            worker_name=worker_name or worker_id,
            supported_task_types=supported_task_types or [],
            now=now,
        )
        return row

    current_now = now or utcnow()
    row_domain = device_to_domain(row)
    task = get_scheduler_task(db, current_task_id or row.current_task_id or "")
    task_domain = task_to_domain(task) if task is not None else None

    if new_status == DeviceStatus.IDLE:
        if row_domain.status != DeviceStatus.IDLE:
            if task_domain is None:
                raise ValueError("active worker requires task context to release")
            result = worker_release_device(task_domain, row_domain, current_now)
            if result.device is None:
                raise ValueError("release produced no device result")
            apply_device_domain(row, result.device)
    elif new_status == DeviceStatus.ASSIGN:
        if task_domain is None:
            raise ValueError("assign requires current_task_id")
        result = worker_accept_task(task_domain, row_domain, current_now)
        if result.device is None:
            raise ValueError("accept produced no device result")
        apply_device_domain(row, result.device)
    elif new_status == DeviceStatus.RUNNING:
        if task_domain is None:
            raise ValueError("running requires current_task_id")
        result = worker_start_task(task_domain, row_domain, current_now)
        if result.device is None:
            raise ValueError("start produced no device result")
        apply_device_domain(row, result.device)
    elif new_status == DeviceStatus.POST:
        if task_domain is None:
            raise ValueError("post requires current_task_id")
        result = worker_complete_execution(task_domain, row_domain, current_now)
        if result.device is None:
            raise ValueError("post produced no device result")
        apply_device_domain(row, result.device)
    elif new_status == DeviceStatus.ERROR:
        if task_domain is None:
            raise ValueError("error requires current_task_id")
        result = worker_fail_task(task_domain, row_domain, current_now)
        if result.device is None:
            raise ValueError("error produced no device result")
        apply_device_domain(row, result.device)
    else:
        raise ValueError("unsupported device status")

    db.commit()
    db.refresh(row)
    return row


def emit_connection_alarm(
    db: DbSession,
    *,
    worker_id: str,
    kind: str,
    task_id: str | None = None,
    now: datetime | None = None,
) -> models.SchedulerAlarm:
    current_now = now or utcnow()
    if kind == "heartbeat":
        alarm = heartbeat_alarm(worker_id=worker_id, task_id=task_id, now=current_now)
    elif kind == "handshake":
        alarm = handshake_alarm(worker_id=worker_id, task_id=task_id, now=current_now)
    else:
        raise ValueError("unsupported alarm kind")
    row = create_alarm(db, alarm)
    db.commit()
    db.refresh(row)
    return row


def inspect_post_stalled_tasks(db: DbSession, *, now: datetime | None = None, threshold_hours: int = 24) -> list[models.SchedulerAlarm]:
    current_now = now or utcnow()
    rows: list[models.SchedulerAlarm] = []
    for task in list_tasks(db):
        alarm = post_stalled_alarm(task_to_domain(task), current_now, threshold_hours=threshold_hours)
        if alarm is None:
            continue
        rows.append(create_alarm(db, alarm))
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows
