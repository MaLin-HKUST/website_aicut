from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/Users/malin13/Documents/trae_projects/website_aicut")
HARNESS = ROOT / "HarnessPlan/rel0415_acceptance"
FEATURE_LIST = HARNESS / "feature_list.json"
REPORTS = HARNESS / "reports"


def load_feature_data() -> dict:
    return json.loads(FEATURE_LIST.read_text())


def write_feature_data(data: dict) -> None:
    FEATURE_LIST.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def summarize_features(data: dict) -> tuple[list[dict], list[dict]]:
    done = []
    pending = []
    for feature in data.get("features", []):
        if feature.get("id") == "A09":
            continue
        (done if feature.get("status") == "done" else pending).append(feature)
    return done, pending


def collect_reports() -> list[Path]:
    if not REPORTS.exists():
      return []
    return sorted(
        path for path in REPORTS.iterdir()
        if path.is_file()
        and path.suffix == ".md"
        and path.name not in {"RESULT_TEMPLATE.md"}
        and path.name.startswith(("acceptance_", "release_gate_"))
    )


def build_decision(done: list[dict], pending: list[dict], reports: list[Path]) -> tuple[str, list[str]]:
    notes: list[str] = []
    if pending:
        notes.append("Pending acceptance features remain.")
        return "FAIL", notes
    if not reports:
        notes.append("No acceptance verdict report exists yet.")
        return "FAIL", notes
    notes.append("All prerequisite acceptance features are marked done.")
    notes.append("Acceptance evidence files are present.")
    return "PASS", notes


def write_report(data: dict, done: list[dict], pending: list[dict], reports: list[Path], decision: str, notes: list[str]) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = REPORTS / f"release_gate_{ts}.md"
    lines = [
        "# rel0415 Acceptance Release Gate",
        "",
        f"- Date: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Feature Status",
    ]
    for feature in data.get("features", []):
        lines.append(f"- {feature['id']}: {feature['title']} -> {feature.get('status','pending')}")
    lines.extend(["", "## Evidence Files"])
    lines.extend([f"- {path}" for path in reports] or ["- None"])
    lines.extend(["", "## Decision", decision, "", "## Notes"])
    lines.extend([f"- {note}" for note in notes] or ["- None"])
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def maybe_mark_a09_done(data: dict, decision: str) -> bool:
    if decision != "PASS":
        return False
    for feature in data.get("features", []):
        if feature.get("id") == "A09" and feature.get("status") != "done":
            feature["status"] = "done"
            feature["result"] = [
                "Acceptance gate passed for the 0415 final validation round",
                "Merge-back checklist can now be executed against release/0415 and master"
            ]
            return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the rel0415 acceptance gate")
    parser.add_argument("--mark-a09-done", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_feature_data()
    done, pending = summarize_features(data)
    reports = collect_reports()
    decision, notes = build_decision(done, pending, reports)
    report = write_report(data, done, pending, reports, decision, notes)
    if args.mark_a09_done and maybe_mark_a09_done(data, decision):
        write_feature_data(data)
    print(f"Completed prerequisites: {len(done)}")
    print(f"Pending prerequisites: {len(pending)}")
    print(f"Reports found: {len(reports)}")
    print(f"Report: {report}")
    print(f"Release Decision: {decision}")
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
