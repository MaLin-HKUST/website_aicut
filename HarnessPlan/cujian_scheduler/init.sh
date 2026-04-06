#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/malin13/Documents/trae_projects/website_aicut"
HARNESS_DIR="$ROOT_DIR/HarnessPlan/cujian_scheduler"
DOC_DIR="$ROOT_DIR/doc/cujiian/粗剪的调度的测试"
PLAN_FILE="$DOC_DIR/粗剪SmartCut调度实施计划.md"
CHECKLIST_FILE="$DOC_DIR/真实数据上线验收测试用例清单.md"
RECORD_FILE="$DOC_DIR/真实数据上线验收执行记录表.md"
FEATURE_LIST="$HARNESS_DIR/feature_list.json"
FAKE_TOS_ROOT="/Volumes/XIAOMA-A-1T/docker_hub/FakeTos"
WORKER_TAR="/Volumes/XIAOMA-A-1T/docker_hub/play_gound/website_aicut-smart_cut_worker_latest.tar.gz"

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
path = Path("/Users/malin13/Documents/trae_projects/website_aicut/HarnessPlan/cujian_scheduler/feature_list.json")
data = json.loads(path.read_text())
for feat in data.get("features", []):
    if feat.get("status") == "pending":
        print(f"{feat['id']}: {feat['title']}")
        break
else:
    print("All features completed")
PY
}

status() {
  echo "Cujian Scheduler Harness status"
  check_dir "$ROOT_DIR"
  check_dir "$HARNESS_DIR"
  check_file "$HARNESS_DIR/app_spec.txt"
  check_file "$HARNESS_DIR/feature_list.json"
  check_file "$HARNESS_DIR/claude-progress.txt"
  check_file "$HARNESS_DIR/init.sh"
  check_file "$HARNESS_DIR/README.md"
  check_file "$HARNESS_DIR/case_catalog.yaml"
  check_file "$HARNESS_DIR/reports/RESULT_TEMPLATE.md"
  check_file "$HARNESS_DIR/run_release_gate.py"
  check_file "$PLAN_FILE"
  check_file "$CHECKLIST_FILE"
  check_file "$RECORD_FILE"
  check_file "$WORKER_TAR"
  check_dir "$FAKE_TOS_ROOT"
  echo ""
  echo "Next recommended feature: $(get_next_pending_feature)"
}

repo_check() {
  echo "Cujian Scheduler Harness repo-check"
  check_file "$ROOT_DIR/README.md"
  check_dir "$ROOT_DIR/apps/api"
  check_dir "$ROOT_DIR/worker"
  check_dir "$ROOT_DIR/tests/test_cujiian"
  check_file "$PLAN_FILE"
  check_file "$CHECKLIST_FILE"
  check_file "$RECORD_FILE"
  check_file "$WORKER_TAR"
}

smoke_test() {
  echo "Cujian Scheduler Harness smoke-test"
  cd "$ROOT_DIR"
  python -m pytest apps/api/tests/test_scheduler_domain.py apps/api/tests/test_scheduler_api.py -q
}

release_gate() {
  echo "Cujian Scheduler Harness release-gate"
  cd "$HARNESS_DIR"
  python run_release_gate.py --mode auto
}

cleanup() {
  echo "Cujian Scheduler Harness cleanup"
  "$HARNESS_DIR/scripts/cleanup_fake_tos.sh"
}

usage() {
  echo "Usage: ./init.sh {status|repo-check|smoke-test|release-gate|cleanup}"
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
  release-gate)
    release_gate
    ;;
  cleanup)
    cleanup
    ;;
  *)
    usage
    exit 1
    ;;
esac
