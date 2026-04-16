from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_tos_service
from apps.api.routes.task_center import router as task_center_router
from apps.api.routes.tasks import router as tasks_router
from apps.models.edit import EditStatus, SmartCutEdit
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus, SchedulerTaskType
from apps.models.task import CurrentStage, SmartCutTask, TaskStatus
from apps.services.tos_service import TOSService
from configs.database import Base, build_engine, get_db


@pytest.fixture
def api_client(tmp_path: Path):
    db_path = tmp_path / "rel0415.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = FastAPI()
    app.include_router(tasks_router)
    app.include_router(task_center_router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fake_tos = TOSService(use_fake=True, fake_base_path=str(tmp_path / "fake_tos"))
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tos_service] = lambda: fake_tos

    client = TestClient(app)
    return client, TestingSessionLocal


def test_rel0415_list_and_detail_routes(api_client):
    client, _SessionLocal = api_client

    response = client.post("/api/smart-cut/tasks", json={"user_id": "alice"})
    assert response.status_code == 201
    task_id = response.json()["data"]["task_id"]

    list_response = client.get("/api/smart-cut/tasks", params={"user_id": "alice"})
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["id"] == task_id
    assert items[0]["status"] == "waiting_upload"

    detail_response = client.get(f"/api/smart-cut/tasks/{task_id}")
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["id"] == task_id
    assert payload["status"] == "waiting_upload"
    assert payload["current_stage"] == "upload"


def test_rel0415_upload_direct_transitions_to_ready_analyze(api_client, tmp_path: Path):
    client, _SessionLocal = api_client

    create_response = client.post("/api/smart-cut/tasks", json={"user_id": "alice"})
    task_id = create_response.json()["data"]["task_id"]

    video_path = tmp_path / "source.mp4"
    video_path.write_bytes(b"fake-video")
    text_path = tmp_path / "reference.txt"
    text_path.write_text("hello", encoding="utf-8")

    with video_path.open("rb") as video_fp, text_path.open("rb") as text_fp:
        response = client.post(
            f"/api/smart-cut/tasks/{task_id}/upload-direct",
            files={
                "video_file": ("source.mp4", video_fp, "video/mp4"),
                "reference_file": ("reference.txt", text_fp, "text/plain"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready_analyze"
    assert payload["current_stage"] == "analyze"
    assert payload["original_video_url"].endswith("/input/source_video.mp4")
    assert payload["reference_text_url"].endswith("/input/reference.txt")


def test_rel0415_edits_and_task_center_routes(api_client):
    client, SessionLocal = api_client

    with SessionLocal() as db:
        task = SmartCutTask(
            user_id="alice",
            status=TaskStatus.WAITING_USER,
            current_stage=CurrentStage.USER_SELECT,
            original_video_url="smart-cut/demo/input/source_video.mp4",
            reference_text_url="smart-cut/demo/input/reference.txt",
            analyze_script="{demo}",
            asr_result_tos_key="smart-cut/demo/analyze/asr.json",
        )
        db.add(task)
        db.flush()

        edit = SmartCutEdit(
            task_id=task.id,
            edited_script="{demo}",
            status=EditStatus.SUCCESS,
            audio_b_url="smart-cut/demo/preview/edit-1/audio_b.mp3",
            delay_cuts_tos_key="smart-cut/demo/preview/edit-1/edited_delay_cuts.json",
            pause_cuts_tos_key="smart-cut/demo/preview/edit-1/pause_cuts_on_original.json",
            version_number=1,
        )
        db.add(edit)
        db.flush()

        task.active_edit_id = edit.id

        scheduler_task = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_PREVIEW,
            status=SchedulerTaskStatus.POST,
            business_task_id=task.id,
            assigned_worker_id="worker-01",
            payload={"edit_id": edit.id},
            result={"audio_b_url": edit.audio_b_url},
        )
        db.add(scheduler_task)
        db.commit()

        task_id = task.id
        edit_id = edit.id
        scheduler_task_id = scheduler_task.id

    edits_response = client.get(f"/api/smart-cut/tasks/{task_id}/edits")
    assert edits_response.status_code == 200
    edits_payload = edits_response.json()
    assert edits_payload[0]["id"] == edit_id
    assert edits_payload[0]["audio_b_url"].endswith("audio_b.mp3")

    user_center = client.get("/api/task-center/tasks", params={"user_id": "alice"})
    assert user_center.status_code == 200
    user_payload = user_center.json()
    assert user_payload[0]["id"] == task_id
    assert user_payload[0]["status"] == "waiting"
    assert user_payload[0]["scheduler_task_id"] is None

    admin_center = client.get("/api/admin/task-center/tasks")
    assert admin_center.status_code == 200
    admin_payload = admin_center.json()
    assert admin_payload[0]["id"] == task_id
    assert admin_payload[0]["scheduler_task_id"] == scheduler_task_id
    assert admin_payload[0]["worker_id"] == "worker-01"
