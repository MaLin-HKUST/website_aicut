#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/malin13/Documents/trae_projects/website_aicut"
HARNESS_DIR="$ROOT_DIR/HarnessPlan/rel0415"
FEATURE_LIST="$HARNESS_DIR/feature_list.json"

check_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "MISSING FILE: $path"
    return 1
  fi
  echo "OK FILE: $path"
}

check_dir() {
  local path="$1"
  if [[ ! -d "$path" ]]; then
    echo "MISSING DIR: $path"
    return 1
  fi
  echo "OK DIR: $path"
}

get_next_pending_feature() {
  python - <<'PY'
import json
from pathlib import Path
path = Path("/Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/rel0415/feature_list.json")
data = json.loads(path.read_text())
for feat in data.get("features", []):
    if feat.get("status") != "done":
        print(f"{feat['id']}: {feat['title']}")
        break
else:
    print("All features completed")
PY
}

status() {
  echo "rel0415 Harness status"
  check_dir "$HARNESS_DIR"
  check_file "$HARNESS_DIR/app_spec.txt"
  check_file "$HARNESS_DIR/feature_list.json"
  check_file "$HARNESS_DIR/claude-progress.txt"
  check_file "$HARNESS_DIR/init.sh"
  check_file "$HARNESS_DIR/README.md"
  check_file "$HARNESS_DIR/case_catalog.yaml"
  check_file "$HARNESS_DIR/run_release_gate.py"
  check_file "$HARNESS_DIR/reports/RESULT_TEMPLATE.md"
  check_file "$HARNESS_DIR/notes/current-status.md"
  check_file "$HARNESS_DIR/handover/README.md"
  check_dir "$HARNESS_DIR/reports"
  check_dir "$HARNESS_DIR/artifacts"
  echo "Version: 0415"
  echo "Next recommended feature: $(get_next_pending_feature)"
}

repo_check() {
  echo "rel0415 repo-check"
  check_dir "$ROOT_DIR/apps/api"
  check_dir "$ROOT_DIR/apps/scheduler"
  check_dir "$ROOT_DIR/apps/models"
  check_dir "$ROOT_DIR/apps/services"
  check_dir "$ROOT_DIR/configs"
  check_dir "$ROOT_DIR/doc/rel-0415-versionbook"
  check_dir "$ROOT_DIR/server_sync/20260415_a_machine_snapshot/code_and_data/apps/web"
}

smoke_test() {
  echo "rel0415 smoke-test"
  cd "$ROOT_DIR"
  python -m compileall apps/api apps/scheduler apps/models apps/services configs
  if [[ -d "$ROOT_DIR/apps/web" ]]; then
    echo "Found apps/web in formal repo path"
  else
    echo "INFO: formal apps/web not yet recovered into the main repo path"
  fi
}

feature_check() {
  local feature_id="${1:-}"
  if [[ -z "$feature_id" ]]; then
    echo "Usage: ./init.sh feature-check F02"
    exit 1
  fi
  python - <<'PY' "$feature_id"
import json
import sys
from pathlib import Path
feature_id = sys.argv[1]
data = json.loads(Path("/Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/rel0415/feature_list.json").read_text())
for feat in data["features"]:
    if feat["id"] == feature_id:
        print(json.dumps(feat, ensure_ascii=False, indent=2))
        break
else:
    raise SystemExit(f"Feature not found: {feature_id}")
PY
}

release_gate() {
  echo "rel0415 release-gate"
  cd "$HARNESS_DIR"
  python run_release_gate.py
}

usage() {
  echo "Usage: ./init.sh {status|repo-check|smoke-test|feature-check <ID>|release-gate}"
}

cmd="${1:-status}"
case "$cmd" in
  status)
    status
    ;;
  repo-check)
    repo_check
    ;;
  smoke-test)
    smoke_test
    ;;
  feature-check)
    shift
    feature_check "${1:-}"
    ;;
  release-gate)
    release_gate
    ;;
  *)
    usage
    exit 1
    ;;
esac
