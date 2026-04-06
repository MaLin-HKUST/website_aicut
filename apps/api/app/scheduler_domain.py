from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum


WORKSPACE_RETENTION_HOURS = 72


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    WAITING_USER = "waiting_user"
    SUSPENDED = "suspended"
    POST = "post"
    FINISHED = "finished"
    FAILED = "failed"
    ABANDONED = "abandoned"
    TIMEOUT_CLOSED = "timeout_closed"


class DeviceStatus(str, Enum):
    IDLE = "idle"
    ASSIGN = "assign"
    RUNNING = "running"
    POST = "post"
    ERROR = "error"


class AlarmType(str, Enum):
    EXECUTION_FAILED = "execution_failed"
    HEARTBEAT_LOST = "heartbeat_lost"
    HANDSHAKE_FAILED = "handshake_failed"
    POST_STALLED = "post_stalled"


class WorkspaceActionType(str, Enum):
    KEEP = "keep"
    DELETE = "delete"


@dataclass(slots=True)
class TaskRecord:
    task_id: str
    user_id: int
    page_key: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    step_index: int = 0
    step_total: int = 1
    assigned_worker_id: str | None = None
    workspace_uri: str | None = None
    keep_until: datetime | None = None
    needs_post: bool = False
    input_payload: dict | None = None
    output_payload: dict | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None


@dataclass(slots=True)
class DeviceRecord:
    worker_id: str
    worker_name: str
    supported_task_types: tuple[str, ...]
    status: DeviceStatus
    heartbeat_at: datetime
    current_task_id: str | None = None


@dataclass(slots=True)
class AlarmRecord:
    alarm_type: AlarmType
    created_at: datetime
    message: str
    current_state: str
    worker_id: str | None = None
    task_id: str | None = None


@dataclass(slots=True)
class WorkspaceAction:
    action: WorkspaceActionType
    workspace_uri: str
    reason: str


@dataclass(slots=True)
class TransitionResult:
    task: TaskRecord | None = None
    device: DeviceRecord | None = None
    alarms: list[AlarmRecord] = field(default_factory=list)
    workspace_actions: list[WorkspaceAction] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


def build_workspace_uri(task_id: str) -> str:
    return f"workspace://scheduler/{task_id}"


def retention_deadline(now: datetime, hours: int = WORKSPACE_RETENTION_HOURS) -> datetime:
    return ensure_utc(now) + timedelta(hours=hours)


def create_task(
    *,
    task_id: str,
    user_id: int,
    page_key: str,
    task_type: str,
    created_at: datetime,
    step_total: int = 1,
    needs_post: bool = False,
    workspace_uri: str | None = None,
    input_payload: dict | None = None,
) -> TaskRecord:
    now = ensure_utc(created_at)
    return TaskRecord(
        task_id=task_id,
        user_id=user_id,
        page_key=page_key,
        task_type=task_type,
        status=TaskStatus.PENDING,
        created_at=now,
        updated_at=now,
        step_total=step_total,
        needs_post=needs_post,
        workspace_uri=workspace_uri or build_workspace_uri(task_id),
        input_payload=input_payload,
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def assign_task_to_worker(task: TaskRecord, worker_id: str, now: datetime) -> TransitionResult:
    _assert(task.status == TaskStatus.PENDING, "only pending tasks can be assigned")
    assigned = replace(
        task,
        status=TaskStatus.ASSIGNED,
        assigned_worker_id=worker_id,
        updated_at=ensure_utc(now),
    )
    return TransitionResult(task=assigned, trace=[f"{task.task_id}: pending -> assigned"])


def dispatch_pending_tasks(tasks: list[TaskRecord], devices: list[DeviceRecord], now: datetime) -> list[TransitionResult]:
    ordered_tasks = sorted(tasks, key=lambda item: (ensure_utc(item.created_at), item.task_id))
    idle_devices = sorted(
        [device for device in devices if device.status == DeviceStatus.IDLE],
        key=lambda item: item.worker_id,
    )
    reserved_workers: set[str] = set()
    results: list[TransitionResult] = []

    for task in ordered_tasks:
        if task.status != TaskStatus.PENDING:
            continue
        worker = next(
            (
                device
                for device in idle_devices
                if device.worker_id not in reserved_workers and task.task_type in device.supported_task_types
            ),
            None,
        )
        if worker is None:
            continue
        reserved_workers.add(worker.worker_id)
        results.append(assign_task_to_worker(task, worker.worker_id, now))

    return results


def worker_accept_task(task: TaskRecord, device: DeviceRecord, now: datetime) -> TransitionResult:
    _assert(task.status == TaskStatus.ASSIGNED, "worker can only accept assigned tasks")
    _assert(task.assigned_worker_id == device.worker_id, "worker must match assigned_worker_id")
    _assert(device.status == DeviceStatus.IDLE, "worker must be idle before accept")
    accepted = replace(
        device,
        status=DeviceStatus.ASSIGN,
        current_task_id=task.task_id,
        heartbeat_at=ensure_utc(now),
    )
    return TransitionResult(device=accepted, trace=[f"{device.worker_id}: idle -> assign"])


def worker_start_task(task: TaskRecord, device: DeviceRecord, now: datetime) -> TransitionResult:
    _assert(task.status == TaskStatus.ASSIGNED, "task must remain assigned until A observes running")
    _assert(device.status == DeviceStatus.ASSIGN, "worker must move from assign to running")
    _assert(device.current_task_id == task.task_id, "device current_task_id must match task")
    started = replace(device, status=DeviceStatus.RUNNING, heartbeat_at=ensure_utc(now))
    return TransitionResult(device=started, trace=[f"{device.worker_id}: assign -> running"])


def a_mark_task_running(task: TaskRecord, device: DeviceRecord, now: datetime) -> TransitionResult:
    _assert(task.status == TaskStatus.ASSIGNED, "task must be assigned before running")
    _assert(device.status == DeviceStatus.RUNNING, "A can only mark running after device is running")
    _assert(task.assigned_worker_id == device.worker_id, "device must match assigned worker")
    _assert(device.current_task_id == task.task_id, "device current_task_id must match task")
    running = replace(task, status=TaskStatus.RUNNING, updated_at=ensure_utc(now))
    return TransitionResult(task=running, trace=[f"{task.task_id}: assigned -> running"])


def worker_complete_execution(task: TaskRecord, device: DeviceRecord, now: datetime) -> TransitionResult:
    _assert(task.status == TaskStatus.RUNNING, "task must be running when execution completes")
    _assert(device.status == DeviceStatus.RUNNING, "device must be running before post")
    _assert(device.current_task_id == task.task_id, "device current_task_id must match task")
    posted = replace(device, status=DeviceStatus.POST, heartbeat_at=ensure_utc(now))
    return TransitionResult(device=posted, trace=[f"{device.worker_id}: running -> post"])


def a_progress_after_post(task: TaskRecord, device: DeviceRecord, now: datetime) -> TransitionResult:
    _assert(task.status == TaskStatus.RUNNING, "task must be running before post reconciliation")
    _assert(device.status == DeviceStatus.POST, "device must reach post before task completion advances")
    _assert(device.current_task_id == task.task_id, "device current_task_id must match task")

    completed_step = task.step_index + 1
    if completed_step < task.step_total:
        status = TaskStatus.WAITING_USER
    elif task.needs_post:
        status = TaskStatus.POST
    else:
        status = TaskStatus.FINISHED

    updated = replace(
        task,
        status=status,
        step_index=completed_step,
        updated_at=ensure_utc(now),
    )
    return TransitionResult(task=updated, trace=[f"{task.task_id}: running -> {status.value}"])


def complete_post_task(task: TaskRecord, now: datetime) -> TransitionResult:
    _assert(task.status == TaskStatus.POST, "only post tasks can be completed manually")
    finished = replace(task, status=TaskStatus.FINISHED, updated_at=ensure_utc(now))
    return TransitionResult(task=finished, trace=[f"{task.task_id}: post -> finished"])


def suspend_task(task: TaskRecord, now: datetime) -> TransitionResult:
    _assert(task.status == TaskStatus.WAITING_USER, "only waiting_user tasks can be suspended")
    suspended = replace(
        task,
        status=TaskStatus.SUSPENDED,
        keep_until=retention_deadline(now),
        updated_at=ensure_utc(now),
    )
    keep = []
    if suspended.workspace_uri:
        keep.append(
            WorkspaceAction(
                action=WorkspaceActionType.KEEP,
                workspace_uri=suspended.workspace_uri,
                reason="suspended_retention",
            )
        )
    return TransitionResult(task=suspended, workspace_actions=keep, trace=[f"{task.task_id}: waiting_user -> suspended"])


def continue_task(task: TaskRecord, now: datetime) -> TransitionResult:
    current_now = ensure_utc(now)
    if task.status == TaskStatus.WAITING_USER:
        resumed = replace(task, status=TaskStatus.PENDING, updated_at=current_now)
        return TransitionResult(task=resumed, trace=[f"{task.task_id}: waiting_user -> pending"])
    _assert(task.status == TaskStatus.SUSPENDED, "continue is only valid for waiting_user or suspended tasks")
    _assert(task.keep_until is not None, "suspended task must have keep_until")
    _assert(current_now <= ensure_utc(task.keep_until), "suspended task is already expired")
    resumed = replace(
        task,
        status=TaskStatus.PENDING,
        assigned_worker_id=None,
        updated_at=current_now,
    )
    return TransitionResult(task=resumed, trace=[f"{task.task_id}: suspended -> pending"])


def abandon_task(task: TaskRecord, now: datetime) -> TransitionResult:
    if task.status == TaskStatus.ABANDONED:
        return TransitionResult(task=task, trace=[f"{task.task_id}: abandoned (idempotent)"])
    _assert(
        task.status in {TaskStatus.SUSPENDED, TaskStatus.WAITING_USER, TaskStatus.PENDING},
        "abandon is only valid for suspended, waiting_user, or pending tasks",
    )
    abandoned = replace(task, status=TaskStatus.ABANDONED, updated_at=ensure_utc(now))
    actions: list[WorkspaceAction] = []
    if abandoned.workspace_uri:
        actions.append(
            WorkspaceAction(
                action=WorkspaceActionType.DELETE,
                workspace_uri=abandoned.workspace_uri,
                reason="user_abandoned",
            )
        )
    return TransitionResult(task=abandoned, workspace_actions=actions, trace=[f"{task.task_id}: suspended -> abandoned"])


def close_expired_task(task: TaskRecord, now: datetime) -> TransitionResult:
    _assert(task.status == TaskStatus.SUSPENDED, "only suspended tasks can timeout close")
    _assert(task.keep_until is not None, "suspended task must have keep_until")
    current_now = ensure_utc(now)
    _assert(current_now > ensure_utc(task.keep_until), "task has not expired yet")
    closed = replace(task, status=TaskStatus.TIMEOUT_CLOSED, updated_at=current_now)
    actions: list[WorkspaceAction] = []
    if closed.workspace_uri:
        actions.append(
            WorkspaceAction(
                action=WorkspaceActionType.DELETE,
                workspace_uri=closed.workspace_uri,
                reason="retention_expired",
            )
        )
    return TransitionResult(task=closed, workspace_actions=actions, trace=[f"{task.task_id}: suspended -> timeout_closed"])


def worker_fail_task(task: TaskRecord, device: DeviceRecord, now: datetime) -> TransitionResult:
    _assert(device.status == DeviceStatus.RUNNING, "device must be running before entering error")
    _assert(device.current_task_id == task.task_id, "device current_task_id must match task")
    errored = replace(device, status=DeviceStatus.ERROR, heartbeat_at=ensure_utc(now))
    return TransitionResult(device=errored, trace=[f"{device.worker_id}: running -> error"])


def a_mark_task_failed(
    task: TaskRecord,
    device: DeviceRecord,
    now: datetime,
    *,
    error_code: str | None = None,
    error_message: str = "worker execution failed",
) -> TransitionResult:
    _assert(task.status in {TaskStatus.ASSIGNED, TaskStatus.RUNNING}, "task must be active before failure")
    _assert(device.status == DeviceStatus.ERROR, "device must reach error before task failure")
    _assert(device.current_task_id == task.task_id, "device current_task_id must match task")
    failed = replace(
        task,
        status=TaskStatus.FAILED,
        updated_at=ensure_utc(now),
        keep_until=retention_deadline(now),
        last_error_code=error_code,
        last_error_message=error_message,
    )
    alarms = [
        AlarmRecord(
            alarm_type=AlarmType.EXECUTION_FAILED,
            created_at=ensure_utc(now),
            task_id=task.task_id,
            worker_id=device.worker_id,
            current_state=TaskStatus.FAILED.value,
            message=error_message,
        )
    ]
    actions: list[WorkspaceAction] = []
    if failed.workspace_uri:
        actions.append(
            WorkspaceAction(
                action=WorkspaceActionType.KEEP,
                workspace_uri=failed.workspace_uri,
                reason="failure_retention",
            )
        )
    return TransitionResult(
        task=failed,
        alarms=alarms,
        workspace_actions=actions,
        trace=[f"{task.task_id}: active -> failed"],
    )


def worker_release_device(task: TaskRecord, device: DeviceRecord, now: datetime) -> TransitionResult:
    _assert(device.current_task_id == task.task_id, "device current_task_id must match task")
    allowed_after_post = task.status in {TaskStatus.WAITING_USER, TaskStatus.POST, TaskStatus.FINISHED}
    allowed_after_error = task.status == TaskStatus.FAILED
    if device.status == DeviceStatus.POST:
        _assert(allowed_after_post, "task must advance before device can leave post")
    elif device.status == DeviceStatus.ERROR:
        _assert(allowed_after_error, "task must fail before device can leave error")
    else:
        raise ValueError("device can only release from post or error")
    idle = replace(
        device,
        status=DeviceStatus.IDLE,
        current_task_id=None,
        heartbeat_at=ensure_utc(now),
    )
    return TransitionResult(device=idle, trace=[f"{device.worker_id}: {device.status.value} -> idle"])


def heartbeat_alarm(*, worker_id: str, now: datetime, task_id: str | None = None, message: str = "heartbeat lost") -> AlarmRecord:
    return AlarmRecord(
        alarm_type=AlarmType.HEARTBEAT_LOST,
        created_at=ensure_utc(now),
        worker_id=worker_id,
        task_id=task_id,
        current_state="connection",
        message=message,
    )


def handshake_alarm(*, worker_id: str, now: datetime, task_id: str | None = None, message: str = "handshake failed") -> AlarmRecord:
    return AlarmRecord(
        alarm_type=AlarmType.HANDSHAKE_FAILED,
        created_at=ensure_utc(now),
        worker_id=worker_id,
        task_id=task_id,
        current_state="connection",
        message=message,
    )


def post_stalled_alarm(task: TaskRecord, now: datetime, threshold_hours: int = 24) -> AlarmRecord | None:
    if task.status != TaskStatus.POST:
        return None
    if ensure_utc(now) <= ensure_utc(task.updated_at) + timedelta(hours=threshold_hours):
        return None
    return AlarmRecord(
        alarm_type=AlarmType.POST_STALLED,
        created_at=ensure_utc(now),
        worker_id=task.assigned_worker_id,
        task_id=task.task_id,
        current_state=task.status.value,
        message="post processing stalled",
    )


def find_resume_task(tasks: list[TaskRecord], *, user_id: int, page_key: str, now: datetime) -> TaskRecord | None:
    current_now = ensure_utc(now)
    candidates = [
        task
        for task in tasks
        if task.user_id == user_id
        and task.page_key == page_key
        and task.status == TaskStatus.SUSPENDED
        and task.keep_until is not None
        and current_now <= ensure_utc(task.keep_until)
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (ensure_utc(item.updated_at), item.task_id), reverse=True)[0]
