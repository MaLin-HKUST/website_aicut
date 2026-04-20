"""Run Smart-Cut stages inside the algorithm container using real cut pipelines."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


AICUT_ROOT = Path("/app/aicut2602")
RAW_CUT_SCRIPT = AICUT_ROOT / "libs/cut_breakpoints/src/run_raw_cut.py"
SCRIPT_TO_DELAY_CUTS = AICUT_ROOT / "libs/cut_breakpoints/src/script_to_delay_cuts.py"


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


def _run(command: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(AICUT_ROOT)
    subprocess.run(
        command,
        check=True,
        cwd=str(AICUT_ROOT),
        env=env,
    )


def _preview_debug_path(task: dict[str, Any]) -> Path:
    edit_id = task.get("edit_id") or task.get("payload", {}).get("edit_id") or "default"
    return Path(task["work_dir"]) / "preview" / edit_id / "debug_alignment_failure.json"


def _build_failure_metadata(task: dict[str, Any], stage: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if task.get("edit_id"):
        metadata["edit_id"] = task["edit_id"]
    elif task.get("payload", {}).get("edit_id"):
        metadata["edit_id"] = task["payload"]["edit_id"]

    if stage == "preview":
        debug_path = _preview_debug_path(task)
        if debug_path.exists():
            metadata["debug_alignment_failure_path"] = str(debug_path)
            try:
                payload = _load_json(debug_path)
            except Exception:
                payload = None
            if isinstance(payload, dict):
                details = payload.get("details") or {}
                if details.get("marked_content"):
                    metadata["failing_segment"] = details["marked_content"]
    return metadata


def _ensure_runtime_dependencies() -> None:
    env = os.environ.copy()
    subprocess.run(
        [
            "python",
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "tenacity",
            "pyyaml",
            "moviepy",
            "numpy",
            "requests",
        ],
        check=True,
        env=env,
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_script1(script_data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(script_data, str):
        text = script_data
    elif isinstance(script_data, list):
        lines: list[str] = []
        for item in script_data:
            if isinstance(item, dict):
                lines.append(str(item.get("text", "")))
            else:
                lines.append(str(item))
        text = "\n".join(line for line in lines if line)
    else:
        text = json.dumps(script_data, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")


def _build_keep_audio(video_path: Path, delay_cuts_path: Path, audio_path: Path) -> None:
    from importlib.util import module_from_spec, spec_from_file_location

    mod_path = AICUT_ROOT / "libs/cut_breakpoints/src/generate_audio_from_cuts.py"
    spec = spec_from_file_location("generate_audio_from_cuts", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load audio helper: {mod_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    cut_segments = _read_json(delay_cuts_path).get("cut_segments", [])
    result = module.generate_audio_a(
        video_path=str(video_path),
        cut_segments=cut_segments,
        output_path=str(audio_path),
    )
    if not result.get("success", False):
        raise RuntimeError(f"Audio generation failed: {result}")


def run_analyze(task: dict[str, Any]) -> dict[str, Any]:
    _ensure_runtime_dependencies()
    task_id = task["task_id"]
    work_dir = Path(task["work_dir"])
    prefix = f"task_{task_id}"
    output_dir = work_dir / "analyze" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    video_path = Path(task["inputs"]["original_video"]["local_path"])
    reference_path = Path(task["inputs"]["reference_text"]["local_path"])

    script_path = _output_path(task, "script", output_dir / f"{prefix}_Script1.txt")
    asr_path = _output_path(task, "asr_result", output_dir / f"{prefix}_ASR.Result.json")
    delay_path = _output_path(task, "delay_cuts", output_dir / f"{prefix}_DelayCutSegments.json")
    audio_path = _output_path(task, "audio_a", output_dir / f"{prefix}_audio_a.mp3")

    _run(
        [
            "python",
            str(RAW_CUT_SCRIPT),
            "-i",
            str(video_path),
            "-r",
            str(reference_path),
            "-o",
            str(output_dir),
            "-n",
            prefix,
            "--flow-a",
        ]
    )

    return {
        "script": {"local_path": str(script_path)},
        "asr_result": {"local_path": str(asr_path)},
        "delay_cuts": {"local_path": str(delay_path)},
        "audio_a": {"local_path": str(audio_path)},
    }


def run_preview(task: dict[str, Any]) -> dict[str, Any]:
    _ensure_runtime_dependencies()
    task_id = task["task_id"]
    edit_id = task.get("edit_id") or task.get("payload", {}).get("edit_id") or "default"
    work_dir = Path(task["work_dir"])
    preview_dir = work_dir / "preview" / edit_id
    preview_dir.mkdir(parents=True, exist_ok=True)

    original_video = Path(task["inputs"]["original_video"]["local_path"])
    asr_result_path = Path(task["inputs"]["asr_result"]["local_path"])
    edited_script_path = Path(task["inputs"]["edited_script"]["local_path"])

    script1_path = preview_dir / "edited_script.txt"
    edited_delay_path = _output_path(task, "edited_delay_cuts", preview_dir / "edited_delay_cuts.json")
    pause_cuts_path = _output_path(task, "pause_cuts_on_original", preview_dir / "pause_cuts_on_original.json")
    audio_b_path = _output_path(task, "audio_b", preview_dir / "audio_b.mp3")

    edited_script_data = _read_json(edited_script_path)
    _write_script1(edited_script_data, script1_path)
    debug_alignment_path = preview_dir / "debug_alignment_failure.json"

    _run(
        [
            "python",
            str(SCRIPT_TO_DELAY_CUTS),
            "-s",
            str(script1_path),
            "-a",
            str(asr_result_path),
            "-o",
            str(edited_delay_path),
            "--debug-json",
            str(debug_alignment_path),
        ]
    )

    pause_cuts_path.write_text(json.dumps({"cut_segments": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    _build_keep_audio(original_video, edited_delay_path, audio_b_path)

    return {
        "edited_delay_cuts": {"local_path": str(edited_delay_path)},
        "pause_cuts_on_original": {"local_path": str(pause_cuts_path)},
        "audio_b": {"local_path": str(audio_b_path)},
    }


def run_finalize(task: dict[str, Any]) -> dict[str, Any]:
    _ensure_runtime_dependencies()
    task_id = task["task_id"]
    work_dir = Path(task["work_dir"])
    finalize_dir = work_dir / "finalize"
    finalize_dir.mkdir(parents=True, exist_ok=True)

    original_video = Path(task["inputs"]["original_video"]["local_path"])
    edited_delay_path = Path(task["inputs"]["edited_delay_cuts"]["local_path"])
    pause_cuts_path = Path(task["inputs"]["pause_cuts_on_original"]["local_path"])
    final_video_path = _output_path(task, "final_video", finalize_dir / "final_video.mp4")

    base_name = "final_video"
    _run(
        [
            "python",
            str(RAW_CUT_SCRIPT),
            "-i",
            str(original_video),
            "-o",
            str(finalize_dir),
            "-n",
            base_name,
            "--cut-only",
            "--delay-cuts",
            str(edited_delay_path),
            "--pause-cuts",
            str(pause_cuts_path),
        ]
    )

    generated_path = finalize_dir / f"{base_name}_final.mp4"
    if generated_path != final_video_path and generated_path.exists():
        final_video_path.write_bytes(generated_path.read_bytes())

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

    try:
        if args.stage == "analyze":
            outputs = run_analyze(task_manifest)
        elif args.stage == "preview":
            outputs = run_preview(task_manifest)
        else:
            outputs = run_finalize(task_manifest)
    except Exception as exc:
        result_manifest = {
            "manifest_version": task_manifest["manifest_version"],
            "task_id": task_manifest["task_id"],
            "scheduler_task_id": task_manifest["scheduler_task_id"],
            "stage": args.stage,
            "status": "failed",
            "outputs": {},
            "error_message": str(exc),
            "metadata": _build_failure_metadata(task_manifest, args.stage),
        }
        _write_json(Path(args.result_manifest), result_manifest)
        raise

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
