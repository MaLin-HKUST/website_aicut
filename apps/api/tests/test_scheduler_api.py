from __future__ import annotations

from datetime import timedelta

from app.scheduler_domain import DeviceStatus, TaskStatus
from app.scheduler_service import (
    close_expired_tasks,
    create_scheduler_task,
    get_scheduler_task,
    list_alarms,
    record_worker_status,
    reconcile_tick,
    register_worker,
)


def create_task_via_api(client, *, page_key="page-a", task_type="cut", step_total=1, needs_post=False):
    response = client.post(
        "/scheduler/tasks",
        json={
            "page_key": page_key,
            "task_type": task_type,
            "step_total": step_total,
            "needs_post": needs_post,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_user_resume_and_abandon_flow(api_client, db_session, as_user):
    created = create_scheduler_task(
        db_session,
        user_id=as_user.id,
        page_key="page-a",
        task_type="cut",
        step_total=2,
        now=None,
    )
    created.status = TaskStatus.SUSPENDED.value
    from app.scheduler_service import utcnow

    created.keep_until = utcnow() + timedelta(hours=72)
    db_session.commit()

    response = api_client.get("/scheduler/resume-entry", params={"page_key": "page-a"})
    assert response.status_code == 200
    assert response.json()["has_resume_task"] is True
    assert response.json()["task"]["task_id"] == created.task_id

    continue_response = api_client.post(f"/scheduler/tasks/{created.task_id}/continue")
    assert continue_response.status_code == 200
    assert continue_response.json()["status"] == TaskStatus.PENDING.value

    db_task = get_scheduler_task(db_session, created.task_id)
    assert db_task is not None
    db_task.status = TaskStatus.SUSPENDED.value
    from app.scheduler_service import utcnow as service_now

    db_task.keep_until = service_now() + timedelta(hours=72)
    db_session.commit()

    abandon_response = api_client.post(f"/scheduler/tasks/{created.task_id}/abandon")
    assert abandon_response.status_code == 200
    assert abandon_response.json()["status"] == TaskStatus.ABANDONED.value


def test_user_create_dispatch_worker_reconcile_and_release(api_client, db_session, as_user, as_admin):
    app_user = as_user
    _ = as_admin
    from app.main import app
    from app.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: app_user
    created = create_task_via_api(api_client, step_total=1, needs_post=False)
    task_id = created["task_id"]

    app.dependency_overrides[get_current_user] = lambda: as_admin
    worker_response = api_client.post(
        "/scheduler/admin/workers",
        json={"worker_id": "worker-001", "worker_name": "worker-001", "supported_task_types": ["cut"]},
    )
    assert worker_response.status_code == 201

    dispatch_response = api_client.post("/scheduler/admin/dispatch-tick")
    assert dispatch_response.status_code == 200
    assert dispatch_response.json()[0]["task_id"] == task_id
    assert dispatch_response.json()[0]["status"] == TaskStatus.ASSIGNED.value

    app.dependency_overrides.clear()
    status_assign = api_client.post(
        "/scheduler/workers/worker-001/status",
        json={"status": DeviceStatus.ASSIGN.value, "current_task_id": task_id},
    )
    assert status_assign.status_code == 200

    status_running = api_client.post(
        "/scheduler/workers/worker-001/status",
        json={"status": DeviceStatus.RUNNING.value, "current_task_id": task_id},
    )
    assert status_running.status_code == 200

    app.dependency_overrides[get_current_user] = lambda: as_admin
    reconcile_running = api_client.post("/scheduler/admin/reconcile-tick")
    assert reconcile_running.status_code == 200
    assert reconcile_running.json()[0]["status"] == TaskStatus.RUNNING.value

    app.dependency_overrides.clear()
    status_post = api_client.post(
        "/scheduler/workers/worker-001/status",
        json={"status": DeviceStatus.POST.value, "current_task_id": task_id},
    )
    assert status_post.status_code == 200

    app.dependency_overrides[get_current_user] = lambda: as_admin
    reconcile_finish = api_client.post("/scheduler/admin/reconcile-tick")
    assert reconcile_finish.status_code == 200
    assert reconcile_finish.json()[0]["status"] == TaskStatus.FINISHED.value

    app.dependency_overrides.clear()
    status_idle = api_client.post(
        "/scheduler/workers/worker-001/status",
        json={"status": DeviceStatus.IDLE.value, "current_task_id": task_id},
    )
    assert status_idle.status_code == 200
    assert status_idle.json()["status"] == DeviceStatus.IDLE.value
    app.dependency_overrides.clear()


def test_multistep_suspend_resume_timeout_and_worker_swap(api_client, db_session, as_user, as_admin):
    from app.main import app
    from app.dependencies import get_current_user
    from app.scheduler_service import utcnow

    task = create_scheduler_task(
        db_session,
        user_id=as_user.id,
        page_key="page-a",
        task_type="cut",
        step_total=3,
    )
    register_worker(db_session, worker_id="worker-old", worker_name="old", supported_task_types=["cut"])
    register_worker(db_session, worker_id="worker-new", worker_name="new", supported_task_types=["cut"])

    task.status = TaskStatus.WAITING_USER.value
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: as_user
    suspend_response = api_client.post(f"/scheduler/tasks/{task.task_id}/suspend")
    assert suspend_response.status_code == 200
    assert suspend_response.json()["status"] == TaskStatus.SUSPENDED.value

    app.dependency_overrides[get_current_user] = lambda: as_admin
    first_resume_check = api_client.get("/scheduler/resume-entry", params={"page_key": "page-a"})
    assert first_resume_check.status_code == 200
    assert first_resume_check.json()["has_resume_task"] is False

    app.dependency_overrides[get_current_user] = lambda: as_user
    continue_response = api_client.post(f"/scheduler/tasks/{task.task_id}/continue")
    assert continue_response.status_code == 200
    assert continue_response.json()["status"] == TaskStatus.ASSIGNED.value
    assert continue_response.json()["assigned_worker_id"] == "worker-new"

    db_task = get_scheduler_task(db_session, task.task_id)
    assert db_task is not None
    db_task.status = TaskStatus.SUSPENDED.value
    db_task.keep_until = utcnow() - timedelta(seconds=1)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: as_admin
    closed = api_client.post("/scheduler/admin/tasks/close-expired")
    assert closed.status_code == 200
    assert closed.json()[0]["status"] == TaskStatus.TIMEOUT_CLOSED.value

    app.dependency_overrides[get_current_user] = lambda: as_user
    resume_response = api_client.get("/scheduler/resume-entry", params={"page_key": "page-a"})
    assert resume_response.status_code == 200
    assert resume_response.json()["has_resume_task"] is False
    app.dependency_overrides.clear()


def test_error_and_alarm_endpoints(api_client, db_session, as_user, as_admin):
    from app.main import app
    from app.dependencies import get_current_user
    from app.scheduler_service import utcnow

    task = create_scheduler_task(db_session, user_id=as_user.id, page_key="page-a", task_type="cut")
    register_worker(db_session, worker_id="worker-001", worker_name="worker", supported_task_types=["cut"])
    task.status = TaskStatus.ASSIGNED.value
    task.assigned_worker_id = "worker-001"
    db_session.commit()

    record_worker_status(
        db_session,
        worker_id="worker-001",
        new_status=DeviceStatus.ASSIGN,
        current_task_id=task.task_id,
        now=utcnow(),
    )
    record_worker_status(
        db_session,
        worker_id="worker-001",
        new_status=DeviceStatus.RUNNING,
        current_task_id=task.task_id,
        now=utcnow(),
    )
    reconcile_tick(db_session)
    record_worker_status(
        db_session,
        worker_id="worker-001",
        new_status=DeviceStatus.ERROR,
        current_task_id=task.task_id,
        now=utcnow(),
    )
    reconcile_tick(db_session)

    app.dependency_overrides[get_current_user] = lambda: as_admin
    heartbeat = api_client.post("/scheduler/admin/alarms/connection", params={"worker_id": "worker-001", "kind": "heartbeat"})
    assert heartbeat.status_code == 201

    handshake = api_client.post("/scheduler/admin/alarms/connection", params={"worker_id": "worker-001", "kind": "handshake"})
    assert handshake.status_code == 201

    stale_task = get_scheduler_task(db_session, task.task_id)
    assert stale_task is not None
    stale_task.status = TaskStatus.POST.value
    stale_task.updated_at = utcnow() - timedelta(hours=25)
    db_session.commit()

    post_alarm = api_client.post("/scheduler/admin/alarms/post-stalled", params={"threshold_hours": 24})
    assert post_alarm.status_code == 200
    alarms = api_client.get("/scheduler/admin/alarms")
    assert alarms.status_code == 200
    alarm_types = [item["alarm_type"] for item in alarms.json()]
    assert "execution_failed" in alarm_types
    assert "heartbeat_lost" in alarm_types
    assert "handshake_failed" in alarm_types
    assert "post_stalled" in alarm_types
    app.dependency_overrides.clear()


def test_idempotent_edges_and_visibility(api_client, db_session, as_user, as_admin):
    from app.main import app
    from app.dependencies import get_current_user
    from app.scheduler_service import utcnow

    suspended = create_scheduler_task(db_session, user_id=as_user.id, page_key="page-a", task_type="cut")
    suspended.status = TaskStatus.SUSPENDED.value
    suspended.keep_until = utcnow() + timedelta(hours=72)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: as_user
    first = api_client.post(f"/scheduler/tasks/{suspended.task_id}/abandon")
    second = api_client.post(f"/scheduler/tasks/{suspended.task_id}/abandon")
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == TaskStatus.ABANDONED.value

    finished = create_scheduler_task(db_session, user_id=as_user.id, page_key="page-finished", task_type="cut")
    finished.status = TaskStatus.FINISHED.value
    db_session.commit()
    finished_resume = api_client.get("/scheduler/resume-entry", params={"page_key": "page-finished"})
    assert finished_resume.status_code == 200
    assert finished_resume.json()["has_resume_task"] is False

    abandoned_resume = api_client.get("/scheduler/resume-entry", params={"page_key": "page-a"})
    assert abandoned_resume.status_code == 200
    assert abandoned_resume.json()["has_resume_task"] is False
    app.dependency_overrides.clear()
