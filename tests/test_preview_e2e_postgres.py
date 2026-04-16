import asyncio
import os
from pathlib import Path

import pytest

from apps.models.device import DeviceStatus
from apps.models.edit import EditStatus, SmartCutEdit
from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus, SchedulerTaskType
from apps.models.task import CurrentStage, SmartCutTask, TaskStatus
from apps.scheduler.scheduler_service import SchedulerService
from apps.services.device_service import DeviceService
from apps.services.tos_service import TOSService
from configs.database import create_session_factory, init_scheduler_db
from worker.core import SmartCutWorker
from worker.processors.preview_processor import PreviewProcessor
from worker.stages.run_stage_from_manifest import _load_json, _write_json, run_preview


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is required for PostgreSQL-backed preview e2e",
)
def test_preview_e2e_through_shared_postgres(tmp_path: Path, monkeypatch) -> None:
    db_url = os.environ["TEST_DATABASE_URL"]
    monkeypatch.setenv("USE_ALGORITHM_DOCKER_RUNNER", "true")
    host_workspace_base = Path(os.environ.get("TEST_WORKER_DATA_BASE", str(tmp_path / "worker-jobs")))
    container_workspace_base = os.environ.get("CONTAINER_WORKER_DATA_BASE", str(host_workspace_base))

    fake_tos_root = tmp_path / "fake_tos"
    workspace = host_workspace_base
    workspace.mkdir(parents=True, exist_ok=True)
    tos = TOSService(use_fake=True, fake_base_path=str(fake_tos_root))

    video_source = tmp_path / "source_video.mp4"
    video_source.write_bytes(b"video-bytes")
    asr_source = tmp_path / "asr.json"
    asr_source.write_text('{"utterances": []}', encoding="utf-8")

    tos.upload_file("smart-cut", "smart-cut/e2e/input/source_video.mp4", str(video_source))
    tos.upload_file("smart-cut", "smart-cut/e2e/analyze/asr.json", str(asr_source))
    video_url = tos.generate_download_url(
        bucket="smart-cut",
        key="smart-cut/e2e/input/source_video.mp4",
    ).data["url"]
    asr_url = tos.generate_download_url(
        bucket="smart-cut",
        key="smart-cut/e2e/analyze/asr.json",
    ).data["url"]

    init_scheduler_db(db_url)
    session_factory = create_session_factory(db_url)

    worker = SmartCutWorker(
        worker_id="worker-e2e-preview",
        worker_name="Worker E2E Preview",
        api_base_url="http://localhost:8000",
        tos_service=tos,
        workspace=str(workspace),
        db_url=db_url,
        supported_task_types=[SchedulerTaskType.SMART_CUT_PREVIEW.value],
    )
    worker.register_processor(
        SchedulerTaskType.SMART_CUT_PREVIEW.value,
        PreviewProcessor(tos, str(workspace)),
    )
    worker.register()

    with session_factory() as db:
        business_task = SmartCutTask(
            user_id="e2e-user",
            status=TaskStatus.WAITING_USER,
            current_stage=CurrentStage.USER_SELECT,
            original_video_url=video_url,
            asr_result_tos_key=asr_url,
        )
        db.add(business_task)
        db.commit()
        db.refresh(business_task)

        edit = SmartCutEdit(
            task_id=business_task.id,
            edited_script={"segments": [{"text": "edited"}]},
            status=EditStatus.PROCESSING,
            version_number=1,
        )
        db.add(edit)
        db.commit()
        db.refresh(edit)
        edit_id = edit.id

        scheduler_task = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_PREVIEW,
            status=SchedulerTaskStatus.PENDING,
            business_task_id=business_task.id,
            payload={
                "smart_cut_task_id": business_task.id,
                "edit_id": edit_id,
                "edited_script": edit.edited_script,
                "original_video_tos_key": video_url,
                "asr_result_tos_key": asr_url,
            },
        )
        db.add(scheduler_task)
        db.commit()
        db.refresh(scheduler_task)

        scheduler = SchedulerService(db, DeviceService(db))
        assert scheduler.schedule_pending_tasks() == 1

    def fake_docker_run(command, **kwargs):
        task_manifest_path = Path(command[command.index("--task-manifest") + 1])
        result_manifest_path = Path(command[command.index("--result-manifest") + 1])
        task_manifest_path = Path(
            str(task_manifest_path).replace(container_workspace_base, str(host_workspace_base), 1)
        )
        result_manifest_path = Path(
            str(result_manifest_path).replace(container_workspace_base, str(host_workspace_base), 1)
        )
        task_manifest = _load_json(task_manifest_path)
        outputs = run_preview(task_manifest)
        _write_json(
            result_manifest_path,
            {
                "manifest_version": task_manifest["manifest_version"],
                "task_id": task_manifest["task_id"],
                "scheduler_task_id": task_manifest["scheduler_task_id"],
                "stage": "preview",
                "status": "success",
                "outputs": outputs,
                "error_message": None,
                "metadata": {"edit_id": task_manifest.get("edit_id")},
            },
        )
        return None

    monkeypatch.setattr("worker.services.algorithm_runner.subprocess.run", fake_docker_run)

    assigned = worker.find_assigned_task()
    assert assigned is not None
    assert asyncio.run(worker.execute_task(assigned)) is True

    with session_factory() as db:
        scheduler = SchedulerService(db, DeviceService(db))
        assert scheduler.check_device_status_and_advance() >= 1

        task_row = db.query(SmartCutTask).filter_by(id=assigned.business_task_id).first()
        scheduler_row = db.query(SchedulerTask).filter_by(id=assigned.id).first()
        device_row = DeviceService(db).get_device("worker-e2e-preview")
        edit_row = db.query(SmartCutEdit).filter_by(id=assigned.payload["edit_id"]).first()

        assert task_row.status == TaskStatus.WAITING_USER
        assert task_row.current_stage == CurrentStage.USER_SELECT
        assert task_row.active_edit_id == edit_row.id
        assert scheduler_row.status == SchedulerTaskStatus.SUCCESS
        assert device_row.status == DeviceStatus.IDLE
        assert edit_row.status == EditStatus.SUCCESS
        assert edit_row.audio_b_url == f"smart-cut/{assigned.business_task_id}/preview/{edit_row.id}/audio_b.mp3"
        assert edit_row.delay_cuts_tos_key == (
            f"smart-cut/{assigned.business_task_id}/preview/{edit_row.id}/edited_delay_cuts.json"
        )
        assert edit_row.pause_cuts_tos_key == (
            f"smart-cut/{assigned.business_task_id}/preview/{edit_row.id}/pause_cuts_on_original.json"
        )

    fake_objects = tos.list_objects("smart-cut", prefix=f"smart-cut/{assigned.business_task_id}/preview/{edit_id}")
    uploaded_keys = {item["key"] for item in fake_objects.data["objects"]}
    assert f"smart-cut/{assigned.business_task_id}/preview/{edit_id}/audio_b.mp3" in uploaded_keys
    assert (
        f"smart-cut/{assigned.business_task_id}/preview/{edit_id}/edited_delay_cuts.json" in uploaded_keys
    )
    assert (
        f"smart-cut/{assigned.business_task_id}/preview/{edit_id}/pause_cuts_on_original.json" in uploaded_keys
    )
