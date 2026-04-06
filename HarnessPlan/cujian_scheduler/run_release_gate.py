from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/Users/malin13/Documents/trae_projects/website_aicut")
HARNESS_DIR = ROOT / "HarnessPlan/cujian_scheduler"
CASE_CATALOG = HARNESS_DIR / "case_catalog.yaml"
FEATURE_LIST = HARNESS_DIR / "feature_list.json"
REPORTS_DIR = HARNESS_DIR / "reports"

AUTO_CMD = [
    sys.executable,
    "-m",
    "pytest",
    "apps/api/tests/test_scheduler_domain.py",
    "apps/api/tests/test_scheduler_api.py",
    "-q",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_pending_features() -> list[dict]:
    data = load_json(FEATURE_LIST)
    return [item for item in data.get("features", []) if item.get("status") == "pending"]


def get_cases() -> list[dict]:
    data = load_json(CASE_CATALOG)
    return data.get("cases", [])


def run_command(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def count_cases(cases: list[dict], mode: str) -> dict:
    relevant = []
    for case in cases:
      if mode == "auto" and case["layer"] == "auto":
          relevant.append(case)
      elif mode == "fake_tos" and case.get("supports_fake_tos"):
          relevant.append(case)
      elif mode == "real_tos" and case["layer"] == "real_tos":
          relevant.append(case)

    counts = {"P0": 0, "P1": 0, "P2": 0, "total": len(relevant)}
    for case in relevant:
        priority = case.get("priority")
        if priority in counts:
            counts[priority] += 1
    return counts


def build_report(mode: str, decision: str, counts: dict, command: str, output: str, error: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "# Cujian Scheduler Release Gate Result",
            "",
            "## Metadata",
            f"- Date: {now}",
            f"- Executor: harness-runner",
            f"- Mode: {mode}",
            f"- Code Version: planning-stage",
            f"- Worker Image Tar: /Volumes/XIAOMA-A-1T/docker_hub/play_gound/website_aicut-smart_cut_worker_latest.tar.gz",
            f"- Fake TOS Root: /Volumes/XIAOMA-A-1T/docker_hub/FakeTos",
            "",
            "## Summary",
            f"- Total Cases: {counts['total']}",
            f"- P0 Total: {counts['P0']}",
            f"- P1 Total: {counts['P1']}",
            f"- P2 Total: {counts['P2']}",
            f"- Release Decision: {decision}",
            "",
            "## Commands",
            "```bash",
            command,
            "```",
            "",
            "## Output",
            "```",
            output.strip(),
            "```",
            "",
            "## Error",
            "```",
            error.strip(),
            "```",
            "",
            "## Notes",
            f"- Pending features: {', '.join(item['id'] for item in get_pending_features()) or 'none'}",
            "- Execution record updated: no",
            "- Cleanup verified: no",
        ]
    )


def save_report(mode: str, report: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_file = REPORTS_DIR / f"{mode}_release_gate_{timestamp}.md"
    report_file.write_text(report, encoding="utf-8")
    latest = REPORTS_DIR / "latest_result.md"
    latest.write_text(report, encoding="utf-8")
    return report_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Cujian Scheduler Release Gate Runner")
    parser.add_argument("--mode", choices=["auto", "fake_tos", "real_tos"], default="auto")
    args = parser.parse_args()

    cases = get_cases()
    counts = count_cases(cases, args.mode)

    if args.mode == "auto":
        result = run_command(AUTO_CMD, ROOT)
        decision = "PASS" if result.returncode == 0 else "FAIL"
        command = " ".join(AUTO_CMD)
        report = build_report(args.mode, decision, counts, command, result.stdout, result.stderr)
        report_file = save_report(args.mode, report)
        print(report)
        print()
        print(f"Report saved to: {report_file}")
        return result.returncode

    script = HARNESS_DIR / "scripts" / ("run_fake_tos_gate.sh" if args.mode == "fake_tos" else "run_real_tos_gate.sh")
    command = str(script)
    decision = "BLOCKED"
    output = (
        "This gate is scaffolded but not yet implemented.\n"
        f"Requested mode: {args.mode}\n"
        "Follow feature_list.json and implement pending features before executing this gate."
    )
    error = ""
    report = build_report(args.mode, decision, counts, command, output, error)
    report_file = save_report(args.mode, report)
    print(report)
    print()
    print(f"Report saved to: {report_file}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
