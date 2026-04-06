#!/usr/bin/env bash
set -euo pipefail

FAKE_TOS_ROOT="${FAKE_TOS_ROOT:-/Volumes/XIAOMA-A-1T/docker_hub/FakeTos}"
RUN_ID="${1:-${FAKE_TOS_RUN_ID:-}}"
WORK_ROOT="${WORK_ROOT:-/data/smart-cut}"
TASK_ID="${TASK_ID:-}"

if [[ -n "$RUN_ID" ]]; then
  TARGET="$FAKE_TOS_ROOT/$RUN_ID"
  if [[ -d "$TARGET" ]]; then
    rm -rf "$TARGET"
    echo "Removed Fake TOS namespace: $TARGET"
  else
    echo "Fake TOS namespace not found: $TARGET"
  fi
else
  echo "No RUN_ID provided; skipping Fake TOS namespace cleanup."
fi

if [[ -n "$TASK_ID" ]]; then
  TASK_DIR="$WORK_ROOT/$TASK_ID"
  if [[ -d "$TASK_DIR" ]]; then
    rm -rf "$TASK_DIR"
    echo "Removed worker task dir: $TASK_DIR"
  else
    echo "Worker task dir not found: $TASK_DIR"
  fi
else
  echo "No TASK_ID provided; skipping worker local task cleanup."
fi
