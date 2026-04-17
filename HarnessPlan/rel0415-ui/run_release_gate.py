from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path("/Users/malin13/Documents/trae_projects/website_aicut")
HARNESS = ROOT / "HarnessPlan/rel0415-ui"
FEATURE_LIST = HARNESS / "feature_list.json"
REPORTS = HARNESS / "reports"


def run(cmd: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> tuple[int, str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=merged_env)
    return result.returncode, (result.stdout + result.stderr).strip()


def main() -> int:
  data = json.loads(FEATURE_LIST.read_text())
  done = sum(1 for feat in data["features"] if feat["status"] == "done")
  total = len(data["features"])

  build_code, build_output = run(["npm", "--prefix", "apps/web", "run", "build"])
  playwright_env = {
      "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH": "/Users/malin13/Library/Caches/ms-playwright/chromium-1217/chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
  }
  test_cmd = [
      "npx",
      "playwright",
      "test",
      "tests/rel0415-live-routes.spec.ts",
      "tests/rel0415-user-navigation.spec.ts",
      "tests/smart-cut.spec.ts",
  ]
  test_code, test_output = run(test_cmd, cwd=ROOT / "apps/web", env=playwright_env)
  overall_code = 0 if build_code == 0 and test_code == 0 else 1

  lines = [
      "# rel0415-ui Release Gate",
      "",
      f"- Completed features: {done}/{total}",
      f"- Build status: {'pass' if build_code == 0 else 'fail'}",
      f"- Playwright status: {'pass' if test_code == 0 else 'fail'}",
      "",
      "## Build Output",
      "```text",
      build_output[:12000],
      "```",
      "",
      "## Playwright Output",
      "```text",
      test_output[:12000],
      "```",
  ]

  REPORTS.mkdir(parents=True, exist_ok=True)
  (REPORTS / "latest_result.md").write_text("\n".join(lines) + "\n")
  return overall_code


if __name__ == "__main__":
  raise SystemExit(main())
