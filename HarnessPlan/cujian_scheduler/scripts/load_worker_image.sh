#!/usr/bin/env bash
set -euo pipefail

WORKER_TAR="${1:-/Volumes/XIAOMA-A-1T/docker_hub/play_gound/website_aicut-smart_cut_worker_latest.tar.gz}"

if [[ ! -f "$WORKER_TAR" ]]; then
  echo "Worker image tar not found: $WORKER_TAR" >&2
  exit 1
fi

echo "Loading worker image from: $WORKER_TAR"
echo "Command:"
echo "  docker load -i \"$WORKER_TAR\""
