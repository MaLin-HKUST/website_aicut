#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/malin13/Documents/trae_projects/website_aicut"
HARNESS_DIR="$ROOT_DIR/HarnessPlan/scheduler_plan"
ALG_SPEC="$ROOT_DIR/doc/scheduler/任务调度算法说明_v3.md"
GATE_SPEC="$ROOT_DIR/doc/scheduler/调度系统发布准入测试用例集_v1.md"
API_DIR="$ROOT_DIR/apps/api"
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
  if [[ -f "$FEATURE_LIST" ]]; then
    python3 -c "
import json
import sys
try:
    with open('$FEATURE_LIST') as f:
        data = json.load(f)
    for feat in data.get('features', []):
        if feat.get('status') == 'pending':
            print(f\"{feat['id']}: {feat['title']}\")
            sys.exit(0)
    print('All features completed')
except Exception as e:
    print(f'Error reading feature list: {e}')
    sys.exit(1)
"
  else
    echo "feature_list.json not found"
  fi
}

status() {
  echo "Scheduler Harness status"
  check_dir "$ROOT_DIR"
  check_dir "$HARNESS_DIR"
  check_file "$HARNESS_DIR/app_spec.txt"
  check_file "$HARNESS_DIR/feature_list.json"
  check_file "$HARNESS_DIR/claude-progress.txt"
  check_file "$HARNESS_DIR/init.sh"
  check_file "$HARNESS_DIR/README.md"
  check_file "$HARNESS_DIR/case_catalog.yaml"
  check_file "$HARNESS_DIR/reports/RESULT_TEMPLATE.md"
  check_file "$ALG_SPEC"
  check_file "$GATE_SPEC"
  check_dir "$API_DIR"
  check_file "$API_DIR/requirements.txt"
  echo ""
  echo "Next recommended feature: $(get_next_pending_feature)"
}

repo_check() {
  echo "Scheduler Harness repo-check"
  check_file "$ROOT_DIR/README.md"
  check_file "$ROOT_DIR/docker-compose.yml"
  check_dir "$API_DIR"
  check_dir "$ROOT_DIR/apps/web"
  check_file "$ALG_SPEC"
  check_file "$GATE_SPEC"
}

smoke_test() {
  echo "Scheduler Harness smoke-test"
  cd "$ROOT_DIR"
  python -m pytest apps/api/tests/test_scheduler_domain.py apps/api/tests/test_scheduler_api.py -q
}

release_gate() {
  echo "Running full release gate..."
  cd "$HARNESS_DIR"
  python run_release_gate.py
}

usage() {
  echo "Usage: ./init.sh {status|repo-check|smoke-test|release-gate}"
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
  *)
    usage
    exit 1
    ;;
esac
