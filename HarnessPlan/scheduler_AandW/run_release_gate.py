from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/Users/malin13/Documents/trae_projects/website_aicut")
HARNESS = ROOT / "HarnessPlan/scheduler_AandW"
FEATURE_LIST = HARNESS / "feature_list.json"
REPORTS = HARNESS / "reports"


def load_features() -> dict:
    return json.loads(FEATURE_LIST.read_text())


def summarize(data: dict) -> tuple[list[dict], list[dict]]:
    done = []
    pending = []
    for feature in data.get("features", []):
        if feature.get("status") == "done":
            done.append(feature)
        else:
            pending.append(feature)
    return done, pending


def write_report(done: list[dict], pending: list[dict]) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = REPORTS / f"release_gate_{ts}.md"
    lines = [
        "# Worker Gateway + A-Scheduler Harness Gate",
        "",
        f"- Date: {datetime.now(timezone.utc).isoformat()}",
        "- Version: 0.0.3",
        "",
        "## Completed Features",
    ]
    if done:
        lines.extend([f"- {item['id']}: {item['title']}" for item in done])
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Pending Features",
    ])
    if pending:
        lines.extend([f"- {item['id']}: {item['title']}" for item in pending])
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Decision",
        "FAIL" if pending else "PASS",
        "",
        "## Notes",
        "This gate is feature-completion based. It is not the final stage runtime acceptance gate.",
    ])
    out.write_text("\n".join(lines))
    return out


def main() -> int:
    data = load_features()
    done, pending = summarize(data)
    report = write_report(done, pending)
    print(f"Completed: {len(done)}")
    print(f"Pending: {len(pending)}")
    print(f"Report: {report}")
    if pending:
        print("Release Decision: FAIL")
        return 1
    print("Release Decision: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
