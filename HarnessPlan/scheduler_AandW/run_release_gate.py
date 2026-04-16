from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/Users/malin13/Documents/trae_projects/website_aicut")
HARNESS = ROOT / "HarnessPlan/scheduler_AandW"
FEATURE_LIST = HARNESS / "feature_list.json"
REPORTS = HARNESS / "reports"
ARTIFACTS = HARNESS / "artifacts"
VERSION = "0.0.3"


def load_feature_data() -> dict:
    return json.loads(FEATURE_LIST.read_text())


def write_feature_data(data: dict) -> None:
    FEATURE_LIST.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def collect_artifact_records() -> list[Path]:
    if not ARTIFACTS.exists():
        return []
    return sorted(
        path for path in ARTIFACTS.iterdir()
        if path.is_file() and path.suffix == ".md" and path.name != "README.md"
    )


def summarize_features(data: dict) -> tuple[list[dict], list[dict], list[dict]]:
    done: list[dict] = []
    pending: list[dict] = []
    release_scope: list[dict] = []

    for feature in data.get("features", []):
        if feature.get("id") == "F15":
            continue
        release_scope.append(feature)
        if feature.get("status") == "done":
            done.append(feature)
        else:
            pending.append(feature)

    return done, pending, release_scope


def build_decision(done: list[dict], pending: list[dict], artifact_records: list[Path]) -> tuple[str, list[str]]:
    notes: list[str] = []

    if pending:
        notes.append("Pending features remain outside the release gate.")
        return "FAIL", notes

    if not artifact_records:
        notes.append("No artifact record markdown files were found under HarnessPlan/scheduler_AandW/artifacts.")
        return "FAIL", notes

    notes.append("All prerequisite features F01-F14 are marked done.")
    notes.append("Artifact record files are present.")
    return "PASS", notes


def write_report(
    *,
    data: dict,
    done: list[dict],
    pending: list[dict],
    release_scope: list[dict],
    artifact_records: list[Path],
    decision: str,
    decision_notes: list[str],
) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = REPORTS / f"release_gate_{ts}.md"

    lines = [
        "# Worker Gateway + A-Scheduler Release Gate",
        "",
        "## Metadata",
        f"- Date: {datetime.now(timezone.utc).isoformat()}",
        f"- Version: {VERSION}",
        "",
        "## Scope",
        "- This gate evaluates F01-F14 as release prerequisites and records F15 as the release evidence step.",
        "",
        "## Feature Status",
    ]

    for feature in data.get("features", []):
        lines.append(f"- {feature['id']}: {feature['title']} -> {feature.get('status', 'pending')}")

    lines.extend([
        "",
        "## Verification Evidence",
    ])
    for feature in done:
        lines.append(f"### {feature['id']} {feature['title']}")
        for item in feature.get("verification", []):
            lines.append(f"- {item}")
        for item in feature.get("result", []):
            lines.append(f"- Evidence: {item}")

    if pending:
        lines.extend([
            "",
            "## Pending Features",
        ])
        for feature in pending:
            lines.append(f"- {feature['id']}: {feature['title']}")

    lines.extend([
        "",
        "## Artifact Records",
    ])
    if artifact_records:
        for record in artifact_records:
            lines.append(f"- {record}")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Decision",
        decision,
        "",
        "## Notes",
    ])
    lines.extend([f"- {note}" for note in decision_notes] or ["- None"])

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def maybe_mark_f15_done(data: dict, decision: str) -> bool:
    if decision != "PASS":
        return False

    changed = False
    for feature in data.get("features", []):
        if feature.get("id") == "F15" and feature.get("status") != "done":
            feature["status"] = "done"
            feature["verification"] = [
                "python HarnessPlan/scheduler_AandW/run_release_gate.py",
                "release_gate_*.md generated under HarnessPlan/scheduler_AandW/reports",
            ]
            feature["result"] = [
                "Release report now records F01-F14 verification evidence and artifact record links",
                "Release decision is PASS when all prerequisite features are done and artifact records exist",
            ]
            changed = True
            break
    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the scheduler_AandW release gate")
    parser.add_argument(
        "--mark-f15-done",
        action="store_true",
        help="If the gate passes, mark F15 as done in feature_list.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_feature_data()
    done, pending, release_scope = summarize_features(data)
    artifact_records = collect_artifact_records()
    decision, decision_notes = build_decision(done, pending, artifact_records)
    report = write_report(
        data=data,
        done=done,
        pending=pending,
        release_scope=release_scope,
        artifact_records=artifact_records,
        decision=decision,
        decision_notes=decision_notes,
    )

    if args.mark_f15_done and maybe_mark_f15_done(data, decision):
        write_feature_data(data)

    print(f"Completed prerequisites: {len(done)}")
    print(f"Pending prerequisites: {len(pending)}")
    print(f"Artifact records: {len(artifact_records)}")
    print(f"Report: {report}")
    print(f"Release Decision: {decision}")
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
