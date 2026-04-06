#!/usr/bin/env bash
set -euo pipefail

FAKE_TOS_ROOT="${FAKE_TOS_ROOT:-/Volumes/XIAOMA-A-1T/docker_hub/FakeTos}"
RUN_ID="${1:-${FAKE_TOS_RUN_ID:-manual-run-001}}"
TARGET="$FAKE_TOS_ROOT/$RUN_ID"

mkdir -p "$FAKE_TOS_ROOT"
rm -rf "$TARGET"
mkdir -p "$TARGET"

echo "Prepared Fake TOS run namespace:"
echo "  $TARGET"
