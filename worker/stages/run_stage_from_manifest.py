"""Run one Smart-Cut stage inside the algorithm container using manifests."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _output_path(task: dict[str, Any], name: str, default: Path) -> Path:
    for item in task.get("expected_outputs", []):
        if item.get("name") == name:
            return Path(item["path"])
    return default


def run_analyze(task: dict[str, Any]) -> dict[str, Any]:
    task_id = task["task_id"]
    work_dir = Path(task["work_dir"])
    prefix = f"task_{task_id}"
    output_dir = work_dir / "analyze" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    script_path = _output_path(task, "script", output_dir / f"{prefix}_Script1.txt")
    asr_path = _output_path(task, "asr_result", output_dir / f"{prefix}_ASR.Result.json")
    delay_path = _output_path(task, "delay_cuts", output_dir / f"{prefix}_DelayCutSegments.json")
    audio_path = _output_path(task, "audio_a", output_dir / f"{prefix}_audio_a.mp3")

    script_path.write_text("mock analyze script", encoding="utf-8")
    _write_json(asr_path, {"task_id": task_id, "stage": "analyze"})
    _write_json(delay_path, {"cut_segments": []})
    audio_path.write_bytes(b"mock-audio-a")

    return {
        "script": {"local_path": str(script_path)},
        "asr_result": {"local_path": str(asr_path)},
        "delay_cuts": {"local_path": str(delay_path)},
        "audio_a": {"local_path": str(audio_path)},
    }


def run_preview(task: dict[str, Any]) -> dict[str, Any]:
    work_dir = Path(task["work_dir"])
    preview_dir = work_dir / "preview" / (task.get("edit_id") or "default")
    preview_dir.mkdir(parents=True, exist_ok=True)

    delay_path = _output_path(task, "edited_delay_cuts", preview_dir / "edited_delay_cuts.json")
    pause_path = _output_path(task, "pause_cuts_on_original", preview_dir / "pause_cuts_on_original.json")
    audio_path = _output_path(task, "audio_b", preview_dir / "audio_b.mp3")

    _write_json(delay_path, {"cut_segments": []})
    _write_json(pause_path, {"cut_segments": []})
    audio_path.write_bytes(b"mock-audio-b")

    return {
        "edited_delay_cuts": {"local_path": str(delay_path)},
        "pause_cuts_on_original": {"local_path": str(pause_path)},
        "audio_b": {"local_path": str(audio_path)},
    }


def run_finalize(task: dict[str, Any]) -> dict[str, Any]:
    work_dir = Path(task["work_dir"])
    finalize_dir = work_dir / "finalize"
    finalize_dir.mkdir(parents=True, exist_ok=True)

    final_video_path = _output_path(task, "final_video", finalize_dir / "final_video.mp4")
    original_video_input = Path(task["inputs"]["original_video"]["local_path"])
    if original_video_input.exists():
        shutil.copy2(original_video_input, final_video_path)
    else:
        final_video_path.write_bytes(b"mock-final-video")

    return {
        "final_video": {"local_path": str(final_video_path)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Smart-Cut stage from manifests")
    parser.add_argument("--stage", required=True, choices=["analyze", "preview", "finalize"])
    parser.add_argument("--task-manifest", required=True)
    parser.add_argument("--result-manifest", required=True)
    args = parser.parse_args()

    task_manifest = _load_json(Path(args.task_manifest))

    if args.stage == "analyze":
        outputs = run_analyze(task_manifest)
    elif args.stage == "preview":
        outputs = run_preview(task_manifest)
    else:
        outputs = run_finalize(task_manifest)

    result_manifest = {
        "manifest_version": task_manifest["manifest_version"],
        "task_id": task_manifest["task_id"],
        "scheduler_task_id": task_manifest["scheduler_task_id"],
        "stage": args.stage,
        "status": "success",
        "outputs": outputs,
        "error_message": None,
        "metadata": {},
    }
    _write_json(Path(args.result_manifest), result_manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
