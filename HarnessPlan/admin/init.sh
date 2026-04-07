#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/malin13/Documents/trae_projects/website_aicut"
HARNESS_DIR="$ROOT_DIR/HarnessPlan/admin"
SPEC_FILE="$ROOT_DIR/doc/admin/implementation_plan.md"

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

status() {
  echo "=== Admin Merge Harness Status ==="
  echo ""
  check_dir "$ROOT_DIR"
  check_dir "$HARNESS_DIR"
  check_file "$HARNESS_DIR/app_spec.txt"
  check_file "$HARNESS_DIR/feature_list.json"
  check_file "$HARNESS_DIR/init.sh"
  check_dir "$HARNESS_DIR/cases"
  check_dir "$HARNESS_DIR/configs"
  check_dir "$HARNESS_DIR/scripts"
  check_dir "$HARNESS_DIR/reports"
  check_file "$SPEC_FILE"
  check_dir "$ROOT_DIR/apps/api"
  check_dir "$ROOT_DIR/apps/web"
  check_file "$ROOT_DIR/docker-compose.yml"
  echo ""
  echo "Git branch: $(cd $ROOT_DIR && git branch --show-current)"
  echo ""
  
  # Show feature status
  echo "=== Feature Status ==="
  if command -v python3 &> /dev/null; then
    python3 "$HARNESS_DIR/scripts/show_features.py" "$HARNESS_DIR/feature_list.json"
  fi
}

repo_check() {
  echo "=== Repo Check ==="
  check_file "$ROOT_DIR/README.md"
  check_dir "$ROOT_DIR/apps/api"
  check_dir "$ROOT_DIR/apps/web"
  check_file "$ROOT_DIR/docker-compose.yml"
  check_file "$ROOT_DIR/apps/api/app/models.py"
  check_file "$ROOT_DIR/apps/api/app/schemas.py"
  check_file "$ROOT_DIR/apps/api/app/crud.py"
  check_file "$ROOT_DIR/apps/api/app/main.py"
  check_file "$ROOT_DIR/apps/web/app/admin/page.tsx"
}

usage() {
  echo "Usage: ./init.sh {status|repo-check}"
}

cmd="${1:-status}"
case "$cmd" in
  status)
    status
    ;;
  repo-check)
    repo_check
    ;;
  *)
    usage
    exit 1
    ;;
esac
