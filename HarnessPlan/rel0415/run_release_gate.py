from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/Users/malin13/Documents/trae_projects/website_aicut")
HARNESS = ROOT / "HarnessPlan/rel0415"
FEATURE_LIST = HARNESS / "feature_list.json"
REPORTS = HARNESS / "reports"
VERSION = "0415"


def load_feature_data() -> dict:
    return json.loads(FEATURE_LIST.read_text())


def write_feature_data(data: dict) -> None:
    FEATURE_LIST.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def collect_acceptance_reports() -> list[Path]:
    if not REPORTS.exists():
        return []
    return sorted(
        path for path in REPORTS.iterdir()
        if path.is_file()
        and path.suffix == ".md"
        and path.name not in {"RESULT_TEMPLATE.md"}
        and path.name.startswith(("acceptance_", "release_gate_"))
    )


def summarize_features(data: dict) -> tuple[list[dict], list[dict]]:
    done: list[dict] = []
    pending: list[dict] = []

    for feature in data.get("features", []):
        if feature.get("id") == "F13":
            continue
        if feature.get("status") == "done":
            done.append(feature)
        else:
            pending.append(feature)

    return done, pending


def build_decision(done: list[dict], pending: list[dict], reports: list[Path]) -> tuple[str, list[str]]:
    notes: list[str] = []

    if pending:
      notes.append("Pending features remain outside the 0415 release gate.")
      return "FAIL", notes

    if not reports:
      notes.append("No acceptance or release reports were found under HarnessPlan/rel0415/reports.")
      return "FAIL", notes

    notes.append("All prerequisite features F01-F12 are marked done.")
    notes.append("Acceptance or release evidence files are present.")
    return "PASS", notes


def write_report(
    *,
    data: dict,
    done: list[dict],
    pending: list[dict],
    reports: list[Path],
    decision: str,
    decision_notes: list[str],
) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = REPORTS / f"release_gate_{ts}.md"

    lines = [
        "# rel0415 Release Gate",
        "",
        "## Metadata",
        f"- Date: {datetime.now(timezone.utc).isoformat()}",
        f"- Version: {VERSION}",
        "",
        "## Scope",
        "- This gate evaluates F01-F12 as 0415 release prerequisites and records F13 as the release evidence step.",
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
        "## Acceptance / Release Records",
    ])
    if reports:
        for report in reports:
            lines.append(f"- {report}")
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


def maybe_mark_f13_done(data: dict, decision: str) -> bool:
    if decision != "PASS":
        return False

    changed = False
    for feature in data.get("features", []):
        if feature.get("id") == "F13" and feature.get("status") != "done":
            feature["status"] = "done"
            feature["verification"] = [
                "python HarnessPlan/rel0415/run_release_gate.py",
                "release_gate_*.md generated under HarnessPlan/rel0415/reports"
            ]
            feature["result"] = [
                "0415 release gate found all prerequisite features complete",
                "0415 release evidence files are present under HarnessPlan/rel0415/reports"
            ]
            changed = True
            break
    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the rel0415 release gate")
    parser.add_argument(
        "--mark-f13-done",
        action="store_true",
        help="If the gate passes, mark F13 as done in feature_list.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_feature_data()
    done, pending = summarize_features(data)
    reports = collect_acceptance_reports()
    decision, decision_notes = build_decision(done, pending, reports)
    report = write_report(
        data=data,
        done=done,
        pending=pending,
        reports=reports,
        decision=decision,
        decision_notes=decision_notes,
    )

    if args.mark_f13_done and maybe_mark_f13_done(data, decision):
        write_feature_data(data)

    print(f"Completed prerequisites: {len(done)}")
    print(f"Pending prerequisites: {len(pending)}")
    print(f"Reports found: {len(reports)}")
    print(f"Report: {report}")
    print(f"Release Decision: {decision}")
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
