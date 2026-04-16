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
from worker.processors.finalize_processor import FinalizeProcessor
from worker.stages.run_stage_from_manifest import _load_json, _write_json, run_finalize


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is required for PostgreSQL-backed finalize e2e",
)
def test_finalize_e2e_through_shared_postgres(tmp_path: Path, monkeypatch) -> None:
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
    reference_source = tmp_path / "reference.txt"
    reference_source.write_text("reference text", encoding="utf-8")
    delay_source = tmp_path / "edited_delay_cuts.json"
    delay_source.write_text('{"cut_segments": []}', encoding="utf-8")
    pause_source = tmp_path / "pause_cuts_on_original.json"
    pause_source.write_text('{"cut_segments": []}', encoding="utf-8")
    asr_source = tmp_path / "asr.json"
    asr_source.write_text('{"utterances": []}', encoding="utf-8")

    task_key_prefix = "smart-cut/e2e"
    tos.upload_file("smart-cut", f"{task_key_prefix}/input/source_video.mp4", str(video_source))
    tos.upload_file("smart-cut", f"{task_key_prefix}/input/reference.txt", str(reference_source))
    tos.upload_file("smart-cut", f"{task_key_prefix}/preview/edit-1/edited_delay_cuts.json", str(delay_source))
    tos.upload_file("smart-cut", f"{task_key_prefix}/preview/edit-1/pause_cuts_on_original.json", str(pause_source))
    tos.upload_file("smart-cut", f"{task_key_prefix}/analyze/asr.json", str(asr_source))

    video_url = tos.generate_download_url(
        bucket="smart-cut",
        key=f"{task_key_prefix}/input/source_video.mp4",
    ).data["url"]
    reference_url = tos.generate_download_url(
        bucket="smart-cut",
        key=f"{task_key_prefix}/input/reference.txt",
    ).data["url"]
    delay_url = tos.generate_download_url(
        bucket="smart-cut",
        key=f"{task_key_prefix}/preview/edit-1/edited_delay_cuts.json",
    ).data["url"]
    pause_url = tos.generate_download_url(
        bucket="smart-cut",
        key=f"{task_key_prefix}/preview/edit-1/pause_cuts_on_original.json",
    ).data["url"]
    asr_url = tos.generate_download_url(
        bucket="smart-cut",
        key=f"{task_key_prefix}/analyze/asr.json",
    ).data["url"]

    init_scheduler_db(db_url)
    session_factory = create_session_factory(db_url)

    worker = SmartCutWorker(
        worker_id="worker-e2e-finalize",
        worker_name="Worker E2E Finalize",
        api_base_url="http://localhost:8000",
        tos_service=tos,
        workspace=str(workspace),
        db_url=db_url,
        supported_task_types=[SchedulerTaskType.SMART_CUT_FINALIZE.value],
    )
    worker.register_processor(
        SchedulerTaskType.SMART_CUT_FINALIZE.value,
        FinalizeProcessor(tos, str(workspace)),
    )
    worker.register()

    with session_factory() as db:
        business_task = SmartCutTask(
            user_id="e2e-user",
            status=TaskStatus.WAITING_USER,
            current_stage=CurrentStage.USER_SELECT,
            original_video_url=video_url,
            reference_text_url=reference_url,
            asr_result_tos_key=asr_url,
        )
        db.add(business_task)
        db.commit()
        db.refresh(business_task)

        edit = SmartCutEdit(
            task_id=business_task.id,
            edited_script={"segments": [{"text": "edited"}]},
            status=EditStatus.SUCCESS,
            delay_cuts_tos_key=delay_url,
            pause_cuts_tos_key=pause_url,
            version_number=1,
        )
        db.add(edit)
        db.commit()
        db.refresh(edit)

        business_task.active_edit_id = edit.id
        db.commit()

        scheduler_task = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_FINALIZE,
            status=SchedulerTaskStatus.PENDING,
            business_task_id=business_task.id,
            payload={
                "smart_cut_task_id": business_task.id,
                "edit_id": edit.id,
                "original_video_tos_key": video_url,
                "edited_delay_cuts_tos_key": delay_url,
                "pause_cuts_on_original_tos_key": pause_url,
                "output_mode": "original",
                "feed_to_ai": True,
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
        outputs = run_finalize(task_manifest)
        _write_json(
            result_manifest_path,
            {
                "manifest_version": task_manifest["manifest_version"],
                "task_id": task_manifest["task_id"],
                "scheduler_task_id": task_manifest["scheduler_task_id"],
                "stage": "finalize",
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
        device_row = DeviceService(db).get_device("worker-e2e-finalize")

        assert task_row.status == TaskStatus.SUCCESS
        assert task_row.current_stage == CurrentStage.COMPLETE
        assert task_row.final_video_url == f"smart-cut/{assigned.business_task_id}/finalize/final_video.mp4"
        assert task_row.groundtruth_url is not None
        assert task_row.groundtruth_upload_status == "completed"
        assert scheduler_row.status == SchedulerTaskStatus.SUCCESS
        assert device_row.status == DeviceStatus.IDLE

    fake_objects = tos.list_objects("smart-cut", prefix=f"smart-cut/{assigned.business_task_id}/finalize")
    uploaded_keys = {item["key"] for item in fake_objects.data["objects"]}
    assert f"smart-cut/{assigned.business_task_id}/finalize/final_video.mp4" in uploaded_keys

    gt_objects = tos.list_objects("smart-cut", prefix="cujian_input_data/")
    assert gt_objects.data["count"] > 0
