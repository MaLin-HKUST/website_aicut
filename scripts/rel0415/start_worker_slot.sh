#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/home/malin/release_0415_slot}"
CONTAINER_NAME="${CONTAINER_NAME:-release0415_worker}"
DB_URL="${DB_URL:-postgresql+psycopg2://scheduler:scheduler@127.0.0.1:55432/scheduler}"
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8001}"
FAKE_TOS_HOST_DIR="${FAKE_TOS_HOST_DIR:-$ROOT/fake_tos}"
WORK_DIR="${WORK_DIR:-$ROOT/worker_data}"
HOST_WEBSITE_AICUT_ROOT="${HOST_WEBSITE_AICUT_ROOT:-$ROOT/src_af30ae1}"
HOST_AICUT2602_ROOT="${HOST_AICUT2602_ROOT:-$ROOT/mock_aicut2602}"
ALGORITHM_IMAGE="${ALGORITHM_IMAGE:-website_aicut-smart_cut_worker:latest}"

mkdir -p "$FAKE_TOS_HOST_DIR" "$WORK_DIR" "$HOST_AICUT2602_ROOT"

printf '123456\n' | sudo -S docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
printf '123456\n' | sudo -S docker run -d \
  --name "$CONTAINER_NAME" \
  --network host \
  -e WORKER_ID=release0415-worker \
  -e WORKER_NAME='Release 0415 Worker' \
  -e DATABASE_URL="$DB_URL" \
  -e API_BASE_URL="$API_BASE_URL" \
  -e USE_FAKE_TOS=true \
  -e FAKE_TOS_BASE_PATH=/tmp/fake_tos \
  -e USE_ALGORITHM_DOCKER_RUNNER=true \
  -e ALGORITHM_IMAGE="$ALGORITHM_IMAGE" \
  -e HOST_WORKER_DATA_BASE="$WORK_DIR" \
  -e HOST_WEBSITE_AICUT_ROOT="$HOST_WEBSITE_AICUT_ROOT" \
  -e HOST_AICUT2602_ROOT="$HOST_AICUT2602_ROOT" \
  -e DOCKER_BIN=/usr/local/bin/docker \
  -e WORKER_DATA_BASE=/data/worker-jobs \
  -v "$FAKE_TOS_HOST_DIR:/tmp/fake_tos" \
  -v "$WORK_DIR:/data/worker-jobs" \
  -v "$HOST_WEBSITE_AICUT_ROOT/worker:/app/worker:ro" \
  -v "$HOST_WEBSITE_AICUT_ROOT/apps:/app/apps:ro" \
  -v "$HOST_WEBSITE_AICUT_ROOT/configs:/app/configs:ro" \
  -v /usr/bin/docker:/usr/local/bin/docker:ro \
  -v /var/run/docker.sock:/var/run/docker.sock \
  smart-cut-worker-gateway:0.0.3-dev

sleep 3
printf '123456\n' | sudo -S docker ps --filter "name=$CONTAINER_NAME"
