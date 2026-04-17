#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/home/malin/release_0415_slot}"
API_PORT="${API_PORT:-8001}"
IMAGE_TAG="${IMAGE_TAG:-a-scheduler:0415-af30ae1}"
CONTAINER_NAME="${CONTAINER_NAME:-release0415_api}"
DB_URL="${DB_URL:-postgresql+psycopg2://scheduler:scheduler@127.0.0.1:55432/scheduler}"
FAKE_TOS_HOST_DIR="${FAKE_TOS_HOST_DIR:-$ROOT/fake_tos}"

mkdir -p "$FAKE_TOS_HOST_DIR"

printf '123456\n' | sudo -S docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
printf '123456\n' | sudo -S docker load -i "$ROOT/a-scheduler_0415_af30ae1.tar.gz"
printf '123456\n' | sudo -S docker run -d \
  --name "$CONTAINER_NAME" \
  --network host \
  -e DATABASE_URL="$DB_URL" \
  -e SCHEDULER_DATABASE_URL="$DB_URL" \
  -e TOS_MODE=fake \
  -e FAKE_TOS_BASE_PATH=/tmp/fake_tos \
  -v "$FAKE_TOS_HOST_DIR:/tmp/fake_tos" \
  "$IMAGE_TAG" \
  uvicorn apps.api.main:app --host 0.0.0.0 --port "$API_PORT"

sleep 3
curl -I "http://127.0.0.1:${API_PORT}/health"
