#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/malin13/Documents/trae_projects/website_aicut"
HARNESS_DIR="$ROOT_DIR/HarnessPlan"
SPEC_FILE="$ROOT_DIR/doc/cujian_plan_cx2.md"
AICUT_DIR="/Users/malin13/Documents/trae_projects/aicut2602"

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
  echo "Harness status"
  check_dir "$ROOT_DIR"
  check_dir "$HARNESS_DIR"
  check_file "$HARNESS_DIR/app_spec.txt"
  check_file "$HARNESS_DIR/feature_list.json"
  check_file "$HARNESS_DIR/claude-progress.txt"
  check_file "$HARNESS_DIR/init.sh"
  check_file "$SPEC_FILE"
  check_dir "$ROOT_DIR/apps/api"
  check_dir "$ROOT_DIR/apps/web"
  check_file "$ROOT_DIR/docker-compose.yml"
  check_dir "$AICUT_DIR"
  echo "Next recommended feature: F01"
}

repo_check() {
  echo "Repo check"
  check_file "$ROOT_DIR/README.md"
  check_dir "$ROOT_DIR/apps/api"
  check_dir "$ROOT_DIR/apps/web"
  check_file "$ROOT_DIR/docker-compose.yml"
  check_dir "$AICUT_DIR/libs/cut_breakpoints"
  check_file "$SPEC_FILE"
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
