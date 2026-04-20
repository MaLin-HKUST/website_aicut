"""Run Smart-Cut stages inside the algorithm container."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from worker.services.job_contract import DEFAULT_WORKER_JOBS_DIR, SmartCutJobContract


DEFAULT_ALGORITHM_IMAGE = "website_aicut-smart_cut_worker:latest"


@dataclass
class AlgorithmRunnerConfig:
    enabled: bool
    docker_binary: str
    algorithm_image: str
    host_workspace_base: str
    host_website_root: str
    host_aicut_root: str
    container_workspace_base: str
    stage_runner_path: str

    @classmethod
    def from_env(cls, workspace: str) -> "AlgorithmRunnerConfig":
        repo_root = Path(__file__).resolve().parents[2]
        return cls(
            enabled=os.environ.get("USE_ALGORITHM_DOCKER_RUNNER", "false").lower() == "true",
            docker_binary=os.environ.get("DOCKER_BIN", "docker"),
            algorithm_image=os.environ.get("ALGORITHM_IMAGE", DEFAULT_ALGORITHM_IMAGE),
            host_workspace_base=os.environ.get("HOST_WORKER_DATA_BASE", workspace),
            host_website_root=os.environ.get("HOST_WEBSITE_AICUT_ROOT", str(repo_root)),
            host_aicut_root=os.environ.get("HOST_AICUT2602_ROOT", str(repo_root / "aicut2602")),
            container_workspace_base=os.environ.get("CONTAINER_WORKER_DATA_BASE", DEFAULT_WORKER_JOBS_DIR),
            stage_runner_path="/app/website_aicut/worker/stages/run_stage_from_manifest.py",
        )


class AlgorithmDockerRunner:
    def __init__(self, workspace: str, config: AlgorithmRunnerConfig | None = None):
        self.workspace = workspace
        self.config = config or AlgorithmRunnerConfig.from_env(workspace)
        self.job_contract = SmartCutJobContract(workspace)

    def is_enabled(self) -> bool:
        return self.config.enabled

    def build_command(self, task_id: str, stage: str) -> list[str]:
        task_manifest = (
            Path(self.config.container_workspace_base) / task_id / "task_manifest.json"
        )
        result_manifest = (
            Path(self.config.container_workspace_base) / task_id / "result_manifest.json"
        )
        return [
            self.config.docker_binary,
            "run",
            "--rm",
            "--name",
            f"smart-cut-{stage}-{task_id[:12]}",
            "-e",
            f"WORKER_DATA_BASE={self.config.container_workspace_base}",
            "-e",
            f"BYTEDANCE_ASR_APPID={os.environ.get('BYTEDANCE_ASR_APPID', '')}",
            "-e",
            f"BYTEDANCE_ASR_TOKEN={os.environ.get('BYTEDANCE_ASR_TOKEN', '')}",
            "-v",
            f"{self.config.host_workspace_base}:{self.config.container_workspace_base}",
            "-v",
            f"{self.config.host_website_root}:/app/website_aicut:ro",
            "-v",
            f"{self.config.host_aicut_root}:/app/aicut2602:ro",
            self.config.algorithm_image,
            "python",
            self.config.stage_runner_path,
            "--stage",
            stage,
            "--task-manifest",
            str(task_manifest),
            "--result-manifest",
            str(result_manifest),
        ]

    def run_stage(self, task_id: str, stage: str, *, timeout: int = 3600) -> dict[str, Any]:
        if not self.is_enabled():
            raise RuntimeError("Algorithm Docker runner is disabled")

        command = self.build_command(task_id, stage)
        try:
            subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout,
            )
        except subprocess.CalledProcessError as exc:
            try:
                result_manifest = self.job_contract.read_result_manifest(task_id)
            except Exception:
                raise RuntimeError(
                    exc.stderr.strip()
                    or exc.stdout.strip()
                    or f"Algorithm stage failed: {stage}"
                ) from exc

            metadata = result_manifest.get("metadata") or {}
            debug_path = metadata.get("debug_alignment_failure_path")
            error_message = result_manifest.get("error_message") or f"Algorithm stage failed: {stage}"
            if debug_path:
                error_message = f"{error_message} [debug_alignment_failure_path={debug_path}]"
            raise RuntimeError(error_message) from exc
        return self.job_contract.read_result_manifest(task_id)
