import json
from pathlib import Path

from apps.models.scheduler_task import SchedulerTask, SchedulerTaskType
from worker.services.algorithm_runner import (
    AlgorithmDockerRunner,
    AlgorithmRunnerConfig,
)
from worker.services.job_contract import SmartCutJobContract


def test_algorithm_runner_builds_deterministic_docker_command(tmp_path: Path) -> None:
    config = AlgorithmRunnerConfig(
        enabled=True,
        docker_binary="docker",
        algorithm_image="algo:test",
        host_workspace_base="/host/jobs",
        host_website_root="/host/website_aicut",
        host_aicut_root="/host/aicut2602",
        container_workspace_base="/data/worker-jobs",
        stage_runner_path="/app/website_aicut/worker/stages/run_stage_from_manifest.py",
    )
    runner = AlgorithmDockerRunner(str(tmp_path / "jobs"), config=config)

    command = runner.build_command("task-1", "analyze")

    assert command[:4] == ["docker", "run", "--rm", "--name"]
    assert "--entrypoint" in command
    assert command[command.index("--entrypoint") + 1] == "python"
    assert "algo:test" in command
    assert "/host/jobs:/data/worker-jobs" in command
    assert "--stage" in command
    assert "analyze" in command


def test_algorithm_runner_reads_result_manifest_after_run(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "jobs"
    contract = SmartCutJobContract(str(workspace))
    task = SchedulerTask(
        id="scheduler-1",
        task_type=SchedulerTaskType.SMART_CUT_ANALYZE,
        business_task_id="task-1",
        payload={},
    )
    contract.write_task_manifest(
        task,
        stage="analyze",
        inputs={},
        expected_outputs=[],
        payload={},
    )

    config = AlgorithmRunnerConfig(
        enabled=True,
        docker_binary="docker",
        algorithm_image="algo:test",
        host_workspace_base=str(workspace),
        host_website_root="/host/website_aicut",
        host_aicut_root="/host/aicut2602",
        container_workspace_base=str(workspace),
        stage_runner_path="/app/website_aicut/worker/stages/run_stage_from_manifest.py",
    )
    runner = AlgorithmDockerRunner(str(workspace), config=config)

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        result_path = workspace / "task-1" / "result_manifest.json"
        result_path.write_text(
            json.dumps(
                {
                    "manifest_version": "1.0",
                    "task_id": "task-1",
                    "scheduler_task_id": "scheduler-1",
                    "stage": "analyze",
                    "status": "success",
                    "outputs": {
                        "script": {"local_path": str(workspace / "task-1" / "analyze" / "output" / "script.txt")}
                    },
                    "error_message": None,
                    "metadata": {},
                }
            ),
            encoding="utf-8",
        )
        return None

    monkeypatch.setattr("worker.services.algorithm_runner.subprocess.run", fake_run)

    result = runner.run_stage("task-1", "analyze")

    assert captured["command"][0] == "docker"
    assert result["status"] == "success"
    assert result["stage"] == "analyze"
