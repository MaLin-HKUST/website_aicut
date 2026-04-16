from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_gate_module():
    path = Path("HarnessPlan/scheduler_AandW/run_release_gate.py")
    spec = importlib.util.spec_from_file_location("run_release_gate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_release_gate_decision_fails_without_artifacts(tmp_path: Path) -> None:
    gate = load_gate_module()
    done = [{"id": f"F{i:02d}", "title": "done"} for i in range(1, 15)]
    pending = []
    decision, notes = gate.build_decision(done, pending, [])
    assert decision == "FAIL"
    assert any("artifact" in note.lower() for note in notes)


def test_release_gate_marks_f15_done_on_pass(tmp_path: Path) -> None:
    gate = load_gate_module()
    data = {
        "features": [
            {"id": "F14", "title": "Artifacts", "status": "done"},
            {"id": "F15", "title": "Release Gate", "status": "pending"},
        ]
    }
    changed = gate.maybe_mark_f15_done(data, "PASS")
    assert changed is True
    f15 = next(item for item in data["features"] if item["id"] == "F15")
    assert f15["status"] == "done"
    assert "verification" in f15
    assert "result" in f15


def test_release_gate_collects_artifact_records(tmp_path: Path) -> None:
    gate = load_gate_module()
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "README.md").write_text("ignore", encoding="utf-8")
    record = artifacts_dir / "worker-gateway_0.0.3_20260416_120000_abc1234.md"
    record.write_text("# Artifact Record", encoding="utf-8")
    original = gate.ARTIFACTS
    gate.ARTIFACTS = artifacts_dir
    try:
        records = gate.collect_artifact_records()
    finally:
        gate.ARTIFACTS = original
    assert records == [record]
