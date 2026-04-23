from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from apps.api.routes.stages import router as stages_router
from apps.models.edit import EditStatus, SmartCutEdit
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus, SchedulerTaskType
from apps.models.task import CurrentStage, SmartCutTask, TaskStatus
from configs.database import Base, build_engine, get_db
from worker.processors.preview_processor import PreviewProcessor


@pytest.fixture
def preview_client(tmp_path: Path):
    db_path = tmp_path / "preview_validation.db"
    engine = build_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = FastAPI()
    app.include_router(stages_router)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session_local


def _create_waiting_user_task(session_local, *, analyze_script: str = "今天{先删掉这句}继续讲重点。") -> str:
    with session_local() as db:
        task = SmartCutTask(
            user_id="alice",
            status=TaskStatus.WAITING_USER,
            current_stage=CurrentStage.USER_SELECT,
            analyze_script=analyze_script,
            asr_result_tos_key="smart-cut/demo/analyze/asr.json",
            original_video_url="smart-cut/demo/input/source_video.mp4",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task.id


def test_preview_accepts_same_visible_text_with_different_delete_ranges(preview_client):
    client, session_local = preview_client
    task_id = _create_waiting_user_task(session_local)

    response = client.post(
        f"/api/smart-cut/tasks/{task_id}/preview",
        json={"edited_script": "今天先删掉这句继续讲{重点。}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "previewing"

    with session_local() as db:
        edit = db.query(SmartCutEdit).filter_by(id=payload["edit_id"]).first()
        scheduler_task = db.query(SchedulerTask).filter_by(id=payload["scheduler_task_id"]).first()
        task = db.get(SmartCutTask, task_id)

        assert edit is not None
        assert edit.task_id == task_id
        assert edit.edited_script == "今天先删掉这句继续讲{重点。}"
        assert edit.status == EditStatus.PROCESSING
        assert scheduler_task is not None
        assert scheduler_task.task_type == SchedulerTaskType.SMART_CUT_PREVIEW
        assert scheduler_task.status == SchedulerTaskStatus.PENDING
        assert task.status == TaskStatus.PREVIEWING
        assert task.active_edit_id == edit.id


def test_preview_rejects_rewritten_script_text(preview_client):
    client, session_local = preview_client
    task_id = _create_waiting_user_task(session_local)

    response = client.post(
        f"/api/smart-cut/tasks/{task_id}/preview",
        json={"edited_script": "今天我们已经完全换了一版稿子。"},
    )

    assert response.status_code == 400
    assert "preserve the current task script text" in response.json()["detail"]


def test_preview_allows_retry_from_preview_failed(preview_client):
    client, session_local = preview_client

    with session_local() as db:
        task = SmartCutTask(
            user_id="alice",
            status=TaskStatus.PREVIEW_FAILED,
            current_stage=CurrentStage.USER_SELECT,
            analyze_script="今天先删掉这句继续讲重点。",
            asr_result_tos_key="smart-cut/demo/analyze/asr.json",
            original_video_url="smart-cut/demo/input/source_video.mp4",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

    response = client.post(
        f"/api/smart-cut/tasks/{task_id}/preview",
        json={"edited_script": "今天先删掉这句继续讲{重点。}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "previewing"


def test_preview_allows_reediting_completed_task(preview_client):
    client, session_local = preview_client

    with session_local() as db:
        task = SmartCutTask(
            user_id="alice",
            status=TaskStatus.SUCCESS,
            current_stage=CurrentStage.COMPLETE,
            analyze_script="今天先删掉这句继续讲重点。",
            asr_result_tos_key="smart-cut/demo/analyze/asr.json",
            original_video_url="smart-cut/demo/input/source_video.mp4",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

    response = client.post(
        f"/api/smart-cut/tasks/{task_id}/preview",
        json={"edited_script": "今天先删掉这句继续讲{重点。}"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "previewing"


def test_preview_rejects_invalid_brace_markers(preview_client):
    client, session_local = preview_client
    task_id = _create_waiting_user_task(session_local)

    response = client.post(
        f"/api/smart-cut/tasks/{task_id}/preview",
        json={"edited_script": "今天{先删掉这句继续讲重点。"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "edited_script contains invalid brace markers"


def test_preview_processor_rejects_cross_task_edit(tmp_path: Path, preview_client):
    _, session_local = preview_client
    workspace = tmp_path / "worker-jobs"
    workspace.mkdir(parents=True, exist_ok=True)

    with session_local() as db:
        task = SmartCutTask(
            user_id="alice",
            status=TaskStatus.PREVIEWING,
            current_stage=CurrentStage.PREVIEW,
            analyze_script="今天{先删掉这句}继续讲重点。",
            asr_result_tos_key="smart-cut/demo/analyze/asr.json",
            original_video_url="smart-cut/demo/input/source_video.mp4",
        )
        other_task = SmartCutTask(
            user_id="bob",
            status=TaskStatus.WAITING_USER,
            current_stage=CurrentStage.USER_SELECT,
            analyze_script="另一条任务的脚本。",
            asr_result_tos_key="smart-cut/demo/analyze/other_asr.json",
            original_video_url="smart-cut/demo/input/other_source_video.mp4",
        )
        db.add(task)
        db.add(other_task)
        db.flush()

        edit = SmartCutEdit(
            task_id=other_task.id,
            edited_script="另一条任务的脚本。",
            status=EditStatus.PROCESSING,
            version_number=1,
        )
        db.add(edit)
        db.flush()

        scheduler_task = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_PREVIEW,
            status=SchedulerTaskStatus.PENDING,
            business_task_id=task.id,
            payload={"edit_id": edit.id},
        )
        db.add(scheduler_task)
        db.commit()
        db.refresh(scheduler_task)

    processor = PreviewProcessor(tos_service=None, workspace=str(workspace))
    processor.set_db_session_factory(session_local)
    processor.set_task(scheduler_task)

    with pytest.raises(ValueError, match="does not belong to business task"):
        asyncio.run(processor.prepare_input())
