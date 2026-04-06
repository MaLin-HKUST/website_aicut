from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.scheduler_domain import (
    AlarmType,
    DeviceRecord,
    DeviceStatus,
    TaskRecord,
    TaskStatus,
    WorkspaceActionType,
    a_mark_task_failed,
    a_mark_task_running,
    a_progress_after_post,
    abandon_task,
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


def now() -> datetime:
    return datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc)


def make_task(
    *,
    task_id: str = "task-001",
    status: TaskStatus = TaskStatus.PENDING,
    step_index: int = 0,
    step_total: int = 1,
    needs_post: bool = False,
    assigned_worker_id: str | None = None,
    keep_until: datetime | None = None,
    updated_at: datetime | None = None,
) -> TaskRecord:
    created = now()
    return TaskRecord(
        task_id=task_id,
        user_id=101,
        page_key="page-a",
        task_type="cut",
        status=status,
        created_at=created,
        updated_at=updated_at or created,
        step_index=step_index,
        step_total=step_total,
        needs_post=needs_post,
        assigned_worker_id=assigned_worker_id,
        workspace_uri=f"workspace://{task_id}",
        keep_until=keep_until,
    )


def make_device(
    *,
    worker_id: str = "worker-001",
    status: DeviceStatus = DeviceStatus.IDLE,
    task_type: str = "cut",
    current_task_id: str | None = None,
) -> DeviceRecord:
    return DeviceRecord(
        worker_id=worker_id,
        worker_name=worker_id,
        supported_task_types=(task_type,),
        status=status,
        heartbeat_at=now(),
        current_task_id=current_task_id,
    )


def test_p0_task_001_create_task_is_pending():
    task = create_task(
        task_id="task-001",
        user_id=101,
        page_key="page-a",
        task_type="cut",
        created_at=now(),
    )

    assert task.status == TaskStatus.PENDING
    assert task.task_id == "task-001"
    assert task.created_at == now()


@pytest.mark.parametrize(
    "case_id,transition,expected_status",
    [
        ("P0-TASK-002", "assign", TaskStatus.ASSIGNED),
        ("P0-TASK-003", "running", TaskStatus.RUNNING),
        ("P0-TASK-004", "waiting", TaskStatus.WAITING_USER),
        ("P0-TASK-005", "post", TaskStatus.POST),
        ("P0-TASK-006", "finished", TaskStatus.FINISHED),
        ("P0-TASK-007", "failed", TaskStatus.FAILED),
        ("P0-TASK-008", "suspended", TaskStatus.SUSPENDED),
        ("P0-TASK-009", "resume", TaskStatus.PENDING),
        ("P0-TASK-010", "abandon", TaskStatus.ABANDONED),
        ("P0-TASK-011", "timeout", TaskStatus.TIMEOUT_CLOSED),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_task_state_machine_cases(case_id, transition, expected_status):
    base_now = now()
    if transition == "assign":
        result = assign_task_to_worker(make_task(), "worker-001", base_now)
        assert result.task is not None
        assert result.task.status == expected_status
        assert result.task.assigned_worker_id == "worker-001"
    elif transition == "running":
        task = make_task(status=TaskStatus.ASSIGNED, assigned_worker_id="worker-001")
        device = make_device(status=DeviceStatus.RUNNING, current_task_id=task.task_id)
        result = a_mark_task_running(task, device, base_now)
        assert result.task is not None
        assert result.task.status == expected_status
    elif transition == "waiting":
        task = make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001", step_total=3)
        device = make_device(status=DeviceStatus.POST, current_task_id=task.task_id)
        result = a_progress_after_post(task, device, base_now)
        assert result.task is not None
        assert result.task.status == expected_status
        assert result.task.step_index == 1
    elif transition == "post":
        task = make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001", needs_post=True)
        device = make_device(status=DeviceStatus.POST, current_task_id=task.task_id)
        result = a_progress_after_post(task, device, base_now)
        assert result.task is not None
        assert result.task.status == expected_status
    elif transition == "finished":
        task = make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001", needs_post=False)
        device = make_device(status=DeviceStatus.POST, current_task_id=task.task_id)
        result = a_progress_after_post(task, device, base_now)
        assert result.task is not None
        assert result.task.status == expected_status
    elif transition == "failed":
        task = make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001")
        device = make_device(status=DeviceStatus.ERROR, current_task_id=task.task_id)
        result = a_mark_task_failed(task, device, base_now)
        assert result.task is not None
        assert result.task.status == expected_status
        assert result.alarms[0].alarm_type == AlarmType.EXECUTION_FAILED
    elif transition == "suspended":
        task = make_task(status=TaskStatus.WAITING_USER)
        result = suspend_task(task, base_now)
        assert result.task is not None
        assert result.task.status == expected_status
        assert result.task.keep_until == base_now + timedelta(hours=72)
    elif transition == "resume":
        task = make_task(status=TaskStatus.SUSPENDED, keep_until=base_now + timedelta(hours=72))
        result = continue_task(task, base_now)
        assert result.task is not None
        assert result.task.status == expected_status
    elif transition == "abandon":
        task = make_task(status=TaskStatus.SUSPENDED, keep_until=base_now + timedelta(hours=72))
        result = abandon_task(task, base_now)
        assert result.task is not None
        assert result.task.status == expected_status
        assert result.workspace_actions[0].action == WorkspaceActionType.DELETE
    elif transition == "timeout":
        task = make_task(status=TaskStatus.SUSPENDED, keep_until=base_now - timedelta(seconds=1))
        result = close_expired_task(task, base_now)
        assert result.task is not None
        assert result.task.status == expected_status
        assert result.workspace_actions[0].action == WorkspaceActionType.DELETE
    else:
        raise AssertionError(f"unhandled case {case_id}")


@pytest.mark.parametrize(
    "case_id,transition,expected_status",
    [
        ("P0-DEV-001", "accept", DeviceStatus.ASSIGN),
        ("P0-DEV-002", "start", DeviceStatus.RUNNING),
        ("P0-DEV-003", "post", DeviceStatus.POST),
        ("P0-DEV-004", "error", DeviceStatus.ERROR),
        ("P0-DEV-005", "release_post", DeviceStatus.IDLE),
        ("P0-DEV-006", "release_error", DeviceStatus.IDLE),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_device_state_machine_cases(case_id, transition, expected_status):
    base_now = now()
    task = make_task(status=TaskStatus.ASSIGNED, assigned_worker_id="worker-001")
    if transition == "accept":
        result = worker_accept_task(task, make_device(), base_now)
        assert result.device is not None
        assert result.device.status == expected_status
        assert result.device.current_task_id == task.task_id
    elif transition == "start":
        device = make_device(status=DeviceStatus.ASSIGN, current_task_id=task.task_id)
        result = worker_start_task(task, device, base_now)
        assert result.device is not None
        assert result.device.status == expected_status
    elif transition == "post":
        run_task = make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001")
        device = make_device(status=DeviceStatus.RUNNING, current_task_id=run_task.task_id)
        result = worker_complete_execution(run_task, device, base_now)
        assert result.device is not None
        assert result.device.status == expected_status
    elif transition == "error":
        run_task = make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001")
        device = make_device(status=DeviceStatus.RUNNING, current_task_id=run_task.task_id)
        result = worker_fail_task(run_task, device, base_now)
        assert result.device is not None
        assert result.device.status == expected_status
    elif transition == "release_post":
        wait_task = make_task(status=TaskStatus.WAITING_USER, assigned_worker_id="worker-001")
        device = make_device(status=DeviceStatus.POST, current_task_id=wait_task.task_id)
        result = worker_release_device(wait_task, device, base_now)
        assert result.device is not None
        assert result.device.status == expected_status
    elif transition == "release_error":
        failed_task = make_task(status=TaskStatus.FAILED, assigned_worker_id="worker-001")
        device = make_device(status=DeviceStatus.ERROR, current_task_id=failed_task.task_id)
        result = worker_release_device(failed_task, device, base_now)
        assert result.device is not None
        assert result.device.status == expected_status
    else:
        raise AssertionError(f"unhandled case {case_id}")


def test_p0_link_001_and_002_and_003_and_004_and_005_and_008():
    task = make_task()
    device = make_device()

    with pytest.raises(ValueError):
        worker_accept_task(task, device, now())

    assigned = assign_task_to_worker(task, device.worker_id, now()).task
    assert assigned is not None
    accept_result = worker_accept_task(assigned, device, now())
    assert assigned.status == TaskStatus.ASSIGNED

    running_device = worker_start_task(assigned, accept_result.device, now()).device
    assert running_device is not None
    running_task = a_mark_task_running(assigned, running_device, now()).task
    assert running_task is not None
    assert running_task.status == TaskStatus.RUNNING

    post_device = worker_complete_execution(running_task, running_device, now()).device
    assert post_device is not None
    waiting_task = a_progress_after_post(
        make_task(
            task_id=running_task.task_id,
            status=TaskStatus.RUNNING,
            assigned_worker_id=device.worker_id,
            step_total=2,
        ),
        post_device,
        now(),
    ).task
    assert waiting_task is not None
    assert waiting_task.status == TaskStatus.WAITING_USER

    with pytest.raises(ValueError):
        worker_release_device(make_task(status=TaskStatus.RUNNING, assigned_worker_id=device.worker_id), post_device, now())

    released = worker_release_device(waiting_task, post_device, now()).device
    assert released is not None
    assert released.status == DeviceStatus.IDLE
    assert assigned.assigned_worker_id == device.worker_id


def test_p0_link_006_and_007_responsibility_boundaries_are_structural():
    task = make_task(status=TaskStatus.ASSIGNED, assigned_worker_id="worker-001")
    device = make_device(status=DeviceStatus.RUNNING, current_task_id=task.task_id)
    task_result = a_mark_task_running(task, device, now())
    device_result = worker_complete_execution(
        make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001"),
        make_device(status=DeviceStatus.RUNNING, current_task_id=task.task_id),
        now(),
    )

    assert task_result.task is not None and task_result.device is None
    assert device_result.device is not None and device_result.task is None


def test_p0_link_009_single_worker_single_task():
    worker = make_device(worker_id="worker-001")
    tasks = [
        make_task(task_id="task-001"),
        make_task(task_id="task-002"),
    ]
    results = dispatch_pending_tasks(tasks, [worker], now())

    assert [result.task.task_id for result in results if result.task is not None] == ["task-001"]


def test_dispatch_rules_fcfs_capability_busy_and_recovery():
    base_now = now()
    tasks = [
        make_task(task_id="task-001"),
        make_task(task_id="task-002"),
        make_task(task_id="task-003", updated_at=base_now + timedelta(seconds=10)),
    ]
    workers = [
        make_device(worker_id="worker-a"),
        make_device(worker_id="worker-b"),
        make_device(worker_id="worker-c", task_type="tts"),
    ]

    results = dispatch_pending_tasks(tasks[:2], [workers[0]], base_now)
    assert [item.task.task_id for item in results if item.task is not None] == ["task-001"]

    parallel_results = dispatch_pending_tasks(tasks, workers, base_now)
    assigned_ids = [item.task.task_id for item in parallel_results if item.task is not None]
    assigned_workers = [item.task.assigned_worker_id for item in parallel_results if item.task is not None]
    assert assigned_ids[:2] == ["task-001", "task-002"]
    assert assigned_workers == ["worker-a", "worker-b"]

    busy_worker = make_device(worker_id="worker-a", status=DeviceStatus.RUNNING)
    no_assign = dispatch_pending_tasks([make_task(task_id="task-009")], [busy_worker], base_now)
    assert no_assign == []

    resumed = continue_task(
        make_task(status=TaskStatus.SUSPENDED, keep_until=base_now + timedelta(hours=72), assigned_worker_id="worker-old"),
        base_now,
    ).task
    assert resumed is not None
    resumed_results = dispatch_pending_tasks([resumed], [make_device(worker_id="worker-new")], base_now)
    assert resumed_results[0].task is not None
    assert resumed_results[0].task.assigned_worker_id == "worker-new"


def test_business_closure_single_step_post_multistep_and_direct_finish():
    base_now = now()

    single_step = make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001")
    device = make_device(status=DeviceStatus.POST, current_task_id=single_step.task_id)
    finished = a_progress_after_post(single_step, device, base_now).task
    assert finished is not None
    assert finished.status == TaskStatus.FINISHED

    post_task = make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001", needs_post=True)
    post_result = a_progress_after_post(post_task, device, base_now).task
    assert post_result is not None
    assert post_result.status == TaskStatus.POST
    assert complete_post_task(post_result, base_now).task.status == TaskStatus.FINISHED

    multi = make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001", step_total=3)
    step1 = a_progress_after_post(multi, device, base_now).task
    assert step1 is not None
    assert step1.status == TaskStatus.WAITING_USER
    assert worker_release_device(step1, device, base_now).device.status == DeviceStatus.IDLE

    resumed = continue_task(step1, base_now).task
    assert resumed is not None
    assert resumed.status == TaskStatus.PENDING


def test_user_recovery_timeout_and_resume_lookup():
    base_now = now()
    suspended = suspend_task(make_task(status=TaskStatus.WAITING_USER), base_now).task
    assert suspended is not None
    assert suspended.keep_until == base_now + timedelta(hours=72)

    found = find_resume_task([suspended], user_id=101, page_key="page-a", now=base_now + timedelta(hours=1))
    assert found is not None
    assert found.task_id == suspended.task_id

    expired = close_expired_task(suspended, base_now + timedelta(hours=72, seconds=1)).task
    assert expired is not None
    assert expired.status == TaskStatus.TIMEOUT_CLOSED

    not_found = find_resume_task([expired], user_id=101, page_key="page-a", now=base_now + timedelta(hours=73))
    assert not_found is None


def test_error_alarm_and_workspace_retention_cases():
    base_now = now()
    task = make_task(status=TaskStatus.RUNNING, assigned_worker_id="worker-001")
    device = make_device(status=DeviceStatus.ERROR, current_task_id=task.task_id)
    result = a_mark_task_failed(task, device, base_now, error_message="boom")

    assert result.task is not None
    assert result.task.status == TaskStatus.FAILED
    assert result.workspace_actions[0].action == WorkspaceActionType.KEEP
    assert result.alarms[0].message == "boom"
    assert heartbeat_alarm(worker_id="worker-001", now=base_now).alarm_type == AlarmType.HEARTBEAT_LOST
    assert handshake_alarm(worker_id="worker-001", now=base_now).alarm_type == AlarmType.HANDSHAKE_FAILED

    post_alarm = post_stalled_alarm(
        make_task(status=TaskStatus.POST, updated_at=base_now - timedelta(hours=25), assigned_worker_id="worker-001"),
        base_now,
        threshold_hours=24,
    )
    assert post_alarm is not None
    assert post_alarm.alarm_type == AlarmType.POST_STALLED


def test_idempotent_abandon_and_boundary_recovery_rules():
    suspended = make_task(status=TaskStatus.SUSPENDED, keep_until=now() + timedelta(hours=72))
    once = abandon_task(suspended, now()).task
    assert once is not None and once.status == TaskStatus.ABANDONED
    twice = abandon_task(once, now()).task
    assert twice is not None and twice.status == TaskStatus.ABANDONED

    finished = make_task(status=TaskStatus.FINISHED)
    assert find_resume_task([finished], user_id=101, page_key="page-a", now=now()) is None
    abandoned = make_task(status=TaskStatus.ABANDONED)
    assert find_resume_task([abandoned], user_id=101, page_key="page-a", now=now()) is None
