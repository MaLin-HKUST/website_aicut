"""Shared directory and manifest contract for gateway <-> algorithm exchange."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from apps.models.scheduler_task import SchedulerTask


MANIFEST_VERSION = "1.0"
DEFAULT_WORKER_JOBS_DIR = "/data/worker-jobs"


class SmartCutJobContract:
    """Own the shared work directory layout and manifest read/write contract."""

    def __init__(self, workspace: str):
        self.workspace = Path(workspace)

    def ensure_layout(self, task_id: str) -> dict[str, Path]:
        root = self.workspace / task_id
        layout = {
            "root_dir": root,
            "input_dir": root / "input",
            "analyze_dir": root / "analyze",
            "preview_dir": root / "preview",
            "finalize_dir": root / "finalize",
            "groundtruth_dir": root / "groundtruth",
            "task_manifest_path": root / "task_manifest.json",
            "result_manifest_path": root / "result_manifest.json",
        }
        for key, path in layout.items():
            if key.endswith("_dir"):
                path.mkdir(parents=True, exist_ok=True)
        return layout

    def write_task_manifest(
        self,
        task: SchedulerTask,
        *,
        stage: str,
        inputs: dict[str, dict[str, str]],
        expected_outputs: list[dict[str, str]],
        payload: dict[str, Any],
        edit_id: Optional[str] = None,
    ) -> Path:
        layout = self.ensure_layout(task.business_task_id)
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "task_id": task.business_task_id,
            "scheduler_task_id": task.id,
            "task_type": task.task_type.value,
            "stage": stage,
            "edit_id": edit_id,
            "work_dir": str(layout["root_dir"]),
            "directories": {
                key: str(path)
                for key, path in layout.items()
                if key.endswith("_dir")
            },
            "inputs": inputs,
            "expected_outputs": expected_outputs,
            "payload": payload,
        }
        manifest_path = layout["task_manifest_path"]
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest_path

    def write_result_manifest(
        self,
        task_id: str,
        *,
        scheduler_task_id: str,
        stage: str,
        status: str,
        outputs: dict[str, dict[str, Any]],
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Path:
        layout = self.ensure_layout(task_id)
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "task_id": task_id,
            "scheduler_task_id": scheduler_task_id,
            "stage": stage,
            "status": status,
            "outputs": outputs,
            "error_message": error_message,
            "metadata": metadata or {},
        }
        manifest_path = layout["result_manifest_path"]
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest_path

    def read_result_manifest(self, task_id: str) -> dict[str, Any]:
        layout = self.ensure_layout(task_id)
        manifest_path = layout["result_manifest_path"]
        if not manifest_path.exists():
            raise FileNotFoundError(f"result_manifest.json not found for task {task_id}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.validate_result_manifest(data)
        return data

    def validate_task_manifest(self, data: dict[str, Any]) -> None:
        required = {
            "manifest_version",
            "task_id",
            "scheduler_task_id",
            "task_type",
            "stage",
            "work_dir",
            "directories",
            "inputs",
            "expected_outputs",
            "payload",
        }
        missing = required - set(data)
        if missing:
            raise ValueError(f"task_manifest.json missing fields: {sorted(missing)}")

    def validate_result_manifest(self, data: dict[str, Any]) -> None:
        required = {
            "manifest_version",
            "task_id",
            "scheduler_task_id",
            "stage",
            "status",
            "outputs",
            "metadata",
        }
        missing = required - set(data)
        if missing:
            raise ValueError(f"result_manifest.json missing fields: {sorted(missing)}")
