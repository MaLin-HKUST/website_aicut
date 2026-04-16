import asyncio
import json
import os
from pathlib import Path

import pytest

from apps.models.scheduler_task import SchedulerTask, SchedulerTaskStatus, SchedulerTaskType
from apps.models.task import CurrentStage, SmartCutTask, TaskStatus
from apps.models.device import DeviceStatus
from apps.scheduler.scheduler_service import SchedulerService
from apps.services.device_service import DeviceService
from apps.services.tos_service import TOSService
from configs.database import create_session_factory, init_scheduler_db
from worker.core import SmartCutWorker
from worker.processors.analyze_processor import AnalyzeProcessor
from worker.stages.run_stage_from_manifest import _load_json, _write_json, run_analyze


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is required for PostgreSQL-backed analyze e2e",
)
def test_analyze_e2e_through_shared_postgres(tmp_path: Path, monkeypatch) -> None:
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
    text_source = tmp_path / "reference.txt"
    text_source.write_text("reference", encoding="utf-8")

    tos.upload_file("smart-cut", "smart-cut/e2e/input/source_video.mp4", str(video_source))
    tos.upload_file("smart-cut", "smart-cut/e2e/input/reference.txt", str(text_source))
    video_url = tos.generate_download_url(
        bucket="smart-cut",
        key="smart-cut/e2e/input/source_video.mp4",
    ).data["url"]
    text_url = tos.generate_download_url(
        bucket="smart-cut",
        key="smart-cut/e2e/input/reference.txt",
    ).data["url"]

    init_scheduler_db(db_url)
    session_factory = create_session_factory(db_url)

    worker = SmartCutWorker(
        worker_id="worker-e2e-analyze",
        worker_name="Worker E2E Analyze",
        api_base_url="http://localhost:8000",
        tos_service=tos,
        workspace=str(workspace),
        db_url=db_url,
        supported_task_types=[SchedulerTaskType.SMART_CUT_ANALYZE.value],
    )
    worker.register_processor(
        SchedulerTaskType.SMART_CUT_ANALYZE.value,
        AnalyzeProcessor(tos, str(workspace)),
    )
    worker.register()

    with session_factory() as db:
        business_task = SmartCutTask(
            user_id="e2e-user",
            status=TaskStatus.READY_ANALYZE,
            current_stage=CurrentStage.ANALYZE,
            original_video_url=video_url,
            reference_text_url=text_url,
        )
        db.add(business_task)
        db.commit()
        db.refresh(business_task)

        scheduler_task = SchedulerTask(
            task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
            status=SchedulerTaskStatus.PENDING,
            business_task_id=business_task.id,
            payload={
                "smart_cut_task_id": business_task.id,
                "original_video_tos_key": video_url,
                "reference_text_tos_key": text_url,
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
        outputs = run_analyze(task_manifest)
        _write_json(
            result_manifest_path,
            {
                "manifest_version": task_manifest["manifest_version"],
                "task_id": task_manifest["task_id"],
                "scheduler_task_id": task_manifest["scheduler_task_id"],
                "stage": "analyze",
                "status": "success",
                "outputs": outputs,
                "error_message": None,
                "metadata": {},
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
        device_row = DeviceService(db).get_device("worker-e2e-analyze")

        assert task_row.status == TaskStatus.WAITING_USER
        assert task_row.current_stage == CurrentStage.USER_SELECT
        assert scheduler_row.status == SchedulerTaskStatus.SUCCESS
        assert device_row.status == DeviceStatus.IDLE

    fake_objects = tos.list_objects("smart-cut", prefix=f"smart-cut/{assigned.business_task_id}/analyze")
    uploaded_keys = {item["key"] for item in fake_objects.data["objects"]}
    assert f"smart-cut/{assigned.business_task_id}/analyze/asr.json" in uploaded_keys
    assert f"smart-cut/{assigned.business_task_id}/analyze/delay_cuts.json" in uploaded_keys
