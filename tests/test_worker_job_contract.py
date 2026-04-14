import json
from pathlib import Path

from apps.models.scheduler_task import SchedulerTask, SchedulerTaskType
from worker.main import WorkerRuntimeConfig
from worker.services import DEFAULT_WORKER_JOBS_DIR, SmartCutJobContract


def test_worker_runtime_default_workspace_is_worker_jobs(monkeypatch) -> None:
    monkeypatch.delenv("WORKER_DATA_BASE", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/db")

    config = WorkerRuntimeConfig.from_env()

    assert config.workspace == DEFAULT_WORKER_JOBS_DIR


def test_job_contract_creates_fixed_layout(tmp_path: Path) -> None:
    contract = SmartCutJobContract(str(tmp_path / "worker-jobs"))

    layout = contract.ensure_layout("task-123")

    assert layout["root_dir"] == tmp_path / "worker-jobs" / "task-123"
    assert layout["input_dir"].is_dir()
    assert layout["analyze_dir"].is_dir()
    assert layout["preview_dir"].is_dir()
    assert layout["finalize_dir"].is_dir()
    assert layout["groundtruth_dir"].is_dir()
    assert layout["task_manifest_path"].name == "task_manifest.json"
    assert layout["result_manifest_path"].name == "result_manifest.json"


def test_job_contract_writes_task_and_result_manifests(tmp_path: Path) -> None:
    contract = SmartCutJobContract(str(tmp_path / "worker-jobs"))
    task = SchedulerTask(
        id="scheduler-1",
        task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
        business_task_id="task-1",
        payload={"original_video_tos_key": "smart-cut/task-1/input/source_video.mp4"},
    )

    task_manifest = contract.write_task_manifest(
        task,
        stage="analyze",
        inputs={
            "original_video": {
                "source": "smart-cut/task-1/input/source_video.mp4",
                "local_path": "/data/worker-jobs/task-1/input/source_video.mp4",
            }
        },
        expected_outputs=[
            {
                "name": "script",
                "path": "/data/worker-jobs/task-1/analyze/output/task_task-1_Script1.txt",
            }
        ],
        payload=task.payload,
    )
    task_data = json.loads(task_manifest.read_text(encoding="utf-8"))
    contract.validate_task_manifest(task_data)
    assert task_data["directories"]["input_dir"].endswith("/task-1/input")

    result_manifest = contract.write_result_manifest(
        "task-1",
        scheduler_task_id="scheduler-1",
        stage="analyze",
        status="success",
        outputs={
            "script": {
                "local_path": "/data/worker-jobs/task-1/analyze/output/task_task-1_Script1.txt",
                "tos_key": "smart-cut/task-1/analyze/script.json",
            }
        },
        metadata={"note": "ok"},
    )
    result_data = json.loads(result_manifest.read_text(encoding="utf-8"))
    contract.validate_result_manifest(result_data)
    assert contract.read_result_manifest("task-1")["status"] == "success"
