from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path("/Users/malin13/Documents/trae_projects/website_aicut")
HARNESS = ROOT / "HarnessPlan/rel0415-ui"
FEATURE_LIST = HARNESS / "feature_list.json"
REPORTS = HARNESS / "reports"


def run(cmd: list[str], cwd: Path = ROOT) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def main() -> int:
  data = json.loads(FEATURE_LIST.read_text())
  done = sum(1 for feat in data["features"] if feat["status"] == "done")
  total = len(data["features"])

  build_code, build_output = run(["npm", "--prefix", "apps/web", "run", "build"])

  lines = [
      "# rel0415-ui Release Gate",
      "",
      f"- Completed features: {done}/{total}",
      f"- Build status: {'pass' if build_code == 0 else 'fail'}",
      "",
      "## Build Output",
      "```text",
      build_output[:12000],
      "```",
  ]

  REPORTS.mkdir(parents=True, exist_ok=True)
  (REPORTS / "latest_result.md").write_text("\n".join(lines) + "\n")
  return build_code


if __name__ == "__main__":
  raise SystemExit(main())
