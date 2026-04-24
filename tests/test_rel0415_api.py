from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_tos_service
from apps.api.routes.task_center import router as task_center_router
from apps.api.routes.stages import router as stages_router
from apps.api.routes.tasks import router as tasks_router
from apps.models.edit import EditStatus, SmartCutEdit
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskType
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
    app.include_router(stages_router)
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


def test_start_task_creates_visible_main_task_and_initial_run(api_client):
    client, SessionLocal = api_client

    response = client.post(
        "/api/smart-cut/tasks/start",
        json={"user_id": "alice", "company_id": 9},
    )
    assert response.status_code == 201
    payload = response.json()
    task_id = payload["task_id"]
    assert payload["status"] == "waiting_upload"
    assert payload["current_stage"] == "upload"
    assert payload["company_id"] == 9
    assert payload["task_title"].startswith("智能剪气口-")

    detail_response = client.get(f"/api/smart-cut/tasks/{task_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["company_id"] == 9
    assert detail_payload["visible_in_task_center"] is True
    assert detail_payload["current_run_id"] is not None
    assert detail_payload["revision_count"] == 0

    runs_response = client.get(f"/api/smart-cut/tasks/{task_id}/runs")
    assert runs_response.status_code == 200
    runs_payload = runs_response.json()
    assert len(runs_payload) == 1
    assert runs_payload[0]["run_type"] == "upload"
    assert runs_payload[0]["status"] == "created"

    with SessionLocal() as db:
        task = db.query(SmartCutTask).filter_by(id=task_id).first()
        assert task is not None
        assert task.company_id == 9


def test_rel0415_upload_direct_auto_transitions_to_analyzing(api_client, tmp_path: Path):
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
    assert payload["status"] == "analyzing"
    assert payload["current_stage"] == "analyze"
    assert payload["original_video_url"].endswith("/input/source_video.mp4")
    assert payload["reference_text_url"].endswith("/input/reference.txt")

    runs_response = client.get(f"/api/smart-cut/tasks/{task_id}/runs")
    assert runs_response.status_code == 200
    runs_payload = runs_response.json()
    assert [run["run_type"] for run in runs_payload] == ["upload", "analyze"]
    assert runs_payload[0]["status"] == "success"
    assert runs_payload[1]["status"] == "queued"


def test_rel0415_edits_and_task_center_routes(api_client):
    client, SessionLocal = api_client

    with SessionLocal() as db:
        hidden_task = SmartCutTask(
            user_id="alice",
            status=TaskStatus.WAITING_USER,
            current_stage=CurrentStage.USER_SELECT,
            visible_in_task_center=False,
            session_scope_id="scs_hidden",
            original_video_url="smart-cut/demo/input/source_video.mp4",
            reference_text_url="smart-cut/demo/input/reference.txt",
            analyze_script="{demo}",
            asr_result_tos_key="smart-cut/demo/analyze/asr.json",
        )
        db.add(hidden_task)
        db.flush()

        edit = SmartCutEdit(
            task_id=hidden_task.id,
            edited_script="{demo}",
            status=EditStatus.SUCCESS,
            audio_b_url="smart-cut/demo/preview/edit-1/audio_b.mp3",
            delay_cuts_tos_key="smart-cut/demo/preview/edit-1/edited_delay_cuts.json",
            pause_cuts_tos_key="smart-cut/demo/preview/edit-1/pause_cuts_on_original.json",
            version_number=1,
        )
        db.add(edit)
        db.flush()

        hidden_task.active_edit_id = edit.id

        visible_task = SmartCutTask(
            user_id="alice",
            company_id=9,
            status=TaskStatus.SUCCESS,
            current_stage=CurrentStage.COMPLETE,
            task_title="智能剪气口-20260421-101010",
            visible_in_task_center=True,
            original_video_url="smart-cut/demo/final/input/source_video.mp4",
            reference_text_url="smart-cut/demo/final/input/reference.txt",
            final_video_url="smart-cut/demo/final/finalize/final_video.mp4",
        )
        other_company_task = SmartCutTask(
            user_id="bob",
            company_id=10,
            status=TaskStatus.SUCCESS,
            current_stage=CurrentStage.COMPLETE,
            task_title="智能剪气口-20260421-111111",
            visible_in_task_center=True,
            original_video_url="smart-cut/demo/other/input/source_video.mp4",
            reference_text_url="smart-cut/demo/other/input/reference.txt",
            final_video_url="smart-cut/demo/other/finalize/final_video.mp4",
        )
        db.add(visible_task)
        db.add(other_company_task)
        db.commit()

        task_id = hidden_task.id
        edit_id = edit.id
        visible_task_id = visible_task.id

    edits_response = client.get(f"/api/smart-cut/tasks/{task_id}/edits")
    assert edits_response.status_code == 200
    edits_payload = edits_response.json()
    assert edits_payload[0]["id"] == edit_id
    assert edits_payload[0]["audio_b_url"].endswith("audio_b.mp3")

    user_center = client.get("/api/task-center/tasks", params={"user_id": "alice"})
    assert user_center.status_code == 200
    user_payload = user_center.json()
    assert [item["id"] for item in user_payload] == [visible_task_id]
    assert user_payload[0]["title"] == "智能剪气口-20260421-101010"
    assert user_payload[0]["status"] == "finished"
    assert user_payload[0]["scheduler_task_id"] is None

    admin_center = client.get("/api/admin/task-center/tasks")
    assert admin_center.status_code == 200
    admin_payload = admin_center.json()
    assert visible_task_id in [item["id"] for item in admin_payload]
    assert admin_payload[0]["status"] == "finished"
    assert admin_payload[0]["download_url"].endswith("final_video.mp4")

    company_center = client.get("/api/task-center/tasks", params={"company_id": 9})
    assert company_center.status_code == 200
    company_payload = company_center.json()
    assert [item["id"] for item in company_payload] == [visible_task_id]
    assert company_payload[0]["company_id"] == 9


def test_current_draft_endpoints_are_scoped_to_login_session(api_client):
    client, SessionLocal = api_client

    # draft/current 系列接口已退役，应返回 410
    ensure_response = client.post(
        "/api/smart-cut/tasks/draft/current/ensure",
        json={"user_id": "alice"},
        cookies={"session_token": "session-a"},
    )
    assert ensure_response.status_code == 410
    assert "retired" in ensure_response.json()["detail"].lower()

    current_response = client.get(
        "/api/smart-cut/tasks/draft/current",
        params={"user_id": "alice"},
        cookies={"session_token": "session-a"},
    )
    assert current_response.status_code == 410
    assert "retired" in current_response.json()["detail"].lower()

    with SessionLocal() as db:
        rows = db.query(SmartCutTask).all()
        assert len(rows) == 0


def test_finalize_allows_analyze_only_without_pause_cuts(api_client):
    client, SessionLocal = api_client

    with SessionLocal() as db:
        task = SmartCutTask(
            user_id="alice",
            company_id=9,
            status=TaskStatus.WAITING_USER,
            current_stage=CurrentStage.USER_SELECT,
            visible_in_task_center=True,
            original_video_url="smart-cut/demo/input/source_video.mp4",
            reference_text_url="smart-cut/demo/input/reference.txt",
            asr_result_tos_key="smart-cut/demo/analyze/asr.json",
        )
        db.add(task)
        db.flush()

        edit = SmartCutEdit(
            task_id=task.id,
            edited_script="今天先删掉这句继续讲重点。",
            status=EditStatus.SUCCESS,
            audio_a_url="smart-cut/demo/analyze/audio_a.mp3",
            delay_cuts_tos_key="smart-cut/demo/analyze/delay_cuts.json",
            pause_cuts_tos_key=None,
            version_number=1,
        )
        db.add(edit)
        db.flush()
        task.active_edit_id = edit.id
        db.commit()
        task_id = task.id
        edit_id = edit.id

    response = client.post(
        f"/api/smart-cut/tasks/{task_id}/finalize",
        json={"output_mode": "original", "feed_to_ai": True},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "finalizing"

    with SessionLocal() as db:
        task = db.query(SmartCutTask).filter_by(id=task_id).first()
        scheduler_task = db.query(SchedulerTask).filter_by(id=payload["scheduler_task_id"]).first()
        assert task is not None
        assert scheduler_task is not None
        assert task.status == TaskStatus.FINALIZING
        assert task.active_edit_id == edit_id
        assert task.visible_in_task_center is True
        assert scheduler_task.payload["pause_cuts_on_original_tos_key"] is None


def test_finalize_allows_completed_task_to_generate_new_version(api_client):
    client, SessionLocal = api_client

    with SessionLocal() as db:
        task = SmartCutTask(
            user_id="alice",
            company_id=9,
            status=TaskStatus.SUCCESS,
            current_stage=CurrentStage.COMPLETE,
            task_title="智能剪气口-已完成任务",
            visible_in_task_center=True,
            original_video_url="smart-cut/demo/input/source_video.mp4",
            reference_text_url="smart-cut/demo/input/reference.txt",
            asr_result_tos_key="smart-cut/demo/analyze/asr.json",
        )
        db.add(task)
        db.flush()

        edit = SmartCutEdit(
            task_id=task.id,
            edited_script="今天先删掉这句继续讲重点。",
            status=EditStatus.SUCCESS,
            audio_a_url="smart-cut/demo/analyze/audio_a.mp3",
            delay_cuts_tos_key="smart-cut/demo/analyze/delay_cuts.json",
            pause_cuts_tos_key=None,
            version_number=1,
        )
        db.add(edit)
        db.flush()
        task.active_edit_id = edit.id
        db.commit()
        task_id = task.id

    response = client.post(
        f"/api/smart-cut/tasks/{task_id}/finalize",
        json={"output_mode": "original", "feed_to_ai": True},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "finalizing"


def test_finalize_promotes_hidden_draft_into_task_center(api_client):
    client, SessionLocal = api_client

    with SessionLocal() as db:
        task = SmartCutTask(
            user_id="alice",
            status=TaskStatus.WAITING_USER,
            current_stage=CurrentStage.USER_SELECT,
            visible_in_task_center=False,
            session_scope_id="scs_manual",
            analyze_script="{demo}",
            asr_result_tos_key="smart-cut/demo/analyze/asr.json",
            original_video_url="smart-cut/demo/input/source_video.mp4",
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
        db.commit()
        task_id = task.id
        edit_id = edit.id

    response = client.post(
        f"/api/smart-cut/tasks/{task_id}/finalize",
        json={"output_mode": "original", "feed_to_ai": True, "edit_id": edit_id},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "finalizing"
    assert payload["visible_in_task_center"] is True
    assert payload["task_title"].startswith("智能剪气口-")

    with SessionLocal() as db:
        task = db.get(SmartCutTask, task_id)
        scheduler_task = db.query(SchedulerTask).filter_by(business_task_id=task_id).one()
        assert task is not None
        assert task.visible_in_task_center is True
        assert task.task_title == payload["task_title"]
        assert task.status == TaskStatus.FINALIZING
        assert task.active_edit_id == edit_id
        assert scheduler_task.task_type == SchedulerTaskType.SMART_CUT_FINALIZE
