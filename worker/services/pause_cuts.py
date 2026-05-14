"""Pause cut generation helpers shared by Smart Cut preview runners."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


def _ensure_aicut_import_path(aicut_root: str | Path) -> Path:
    root = Path(aicut_root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def _get_media_duration(media_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _load_delay_cut_segments(delay_cuts_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(delay_cuts_path.read_text(encoding="utf-8"))
    segments = payload.get("segments", payload.get("cut_segments", []))
    return [dict(segment) for segment in segments]


def generate_pause_cuts_from_delay_audio(
    *,
    original_video: Path,
    edited_delay_cuts_path: Path,
    audio_path: Path,
    pause_cuts_path: Path,
    aicut_root: str | Path,
    source: str,
) -> dict[str, Any]:
    """Generate DirectCutter-compatible pause cuts from post-DelayCut audio.

    The audio input must be the audio after DelayCut has been applied. Pause
    detection runs on that audio and maps detected valleys back to the original
    video timeline via the edited delay cuts.
    """
    root = _ensure_aicut_import_path(aicut_root)
    try:
        from libs.cut_breakpoints.src.pause_detect_valley import (
            build_keep_segments_from_delay_cuts,
            detect_valley_pause_cuts,
            load_valley_pause_config,
        )
    except ImportError:
        from pause_detect_valley import (  # type: ignore
            build_keep_segments_from_delay_cuts,
            detect_valley_pause_cuts,
            load_valley_pause_config,
        )

    if not audio_path.exists():
        raise FileNotFoundError(f"Post-DelayCut audio does not exist: {audio_path}")
    if audio_path.stat().st_size <= 0:
        raise RuntimeError(f"Post-DelayCut audio is empty: {audio_path}")

    config_path = root / "libs/cut_breakpoints/src/pause_detector_config.yaml"
    valley_config = load_valley_pause_config(str(config_path) if config_path.exists() else None)
    video_duration = _get_media_duration(original_video)
    delay_segments = _load_delay_cut_segments(edited_delay_cuts_path)
    keep_segments = build_keep_segments_from_delay_cuts(delay_segments, video_duration)
    payload = detect_valley_pause_cuts(
        audio_a_path=audio_path,
        keep_segments=keep_segments,
        config=valley_config,
    )
    payload.setdefault("metadata", {})
    payload["metadata"].update(
        {
            "source": source,
            "delay_cuts_path": str(edited_delay_cuts_path),
        }
    )

    pause_cuts_path.parent.mkdir(parents=True, exist_ok=True)
    pause_cuts_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "Pause cuts generated: path=%s source=%s segments=%s duration_ms=%s",
        pause_cuts_path,
        source,
        payload.get("total_cut_segments"),
        payload.get("total_cut_duration"),
    )
    return payload


def generate_preview_pause_cuts(
    *,
    original_video: Path,
    edited_delay_cuts_path: Path,
    audio_b_path: Path,
    pause_cuts_path: Path,
    aicut_root: str | Path,
) -> dict[str, Any]:
    """Generate pause cuts for a preview active edit."""
    return generate_pause_cuts_from_delay_audio(
        original_video=original_video,
        edited_delay_cuts_path=edited_delay_cuts_path,
        audio_path=audio_b_path,
        pause_cuts_path=pause_cuts_path,
        aicut_root=aicut_root,
        source="smart_cut_preview",
    )
