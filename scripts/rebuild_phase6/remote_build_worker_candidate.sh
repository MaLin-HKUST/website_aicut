#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/home/malin/website_aicut_worker_prod}"

A_HOST="${A_HOST:-14.103.249.104}"
DB_PORT="${DB_PORT:-55433}"
API_PORT="${API_PORT:-18001}"

CONTAINER_NAME="${CONTAINER_NAME:-worker1-phase6-gateway}"
WORKER_ID="${WORKER_ID:-worker1-phase6}"
WORKER_NAME="${WORKER_NAME:-Worker 1 Phase 6}"

POSTGRES_USER="${POSTGRES_USER:-scheduler}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-scheduler}"
POSTGRES_DB="${POSTGRES_DB:-scheduler}"

TOS_ENDPOINT="${TOS_ENDPOINT:-}"
TOS_REGION="${TOS_REGION:-cn-shanghai}"
TOS_BUCKET="${TOS_BUCKET:-}"
TOS_ACCESS_KEY="${TOS_ACCESS_KEY:-}"
TOS_SECRET_KEY="${TOS_SECRET_KEY:-}"

ALGORITHM_IMAGE="${ALGORITHM_IMAGE:-a-scheduler:0415-af30ae1}"
SUDO_PASSWORD="${SUDO_PASSWORD:-123456}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

CODE_ROOT="$ROOT/code/website_aicut"
AICUT_ROOT="$ROOT/code/aicut2602"
WORK_DIR="$ROOT/worker_data"
TOOLS_ROOT="$ROOT/tools"
LOG_ROOT="$ROOT/logs"
MANIFEST_ROOT="$ROOT/manifests"

HEALTH_PATH="$MANIFEST_ROOT/worker_candidate_health_${TIMESTAMP}.txt"
MANIFEST_PATH="$MANIFEST_ROOT/worker_candidate_manifest.json"

require_dir() {
  local path="$1"
  if [[ ! -d "$path" ]]; then
    echo "required directory missing: $path" >&2
    exit 1
  fi
}

wait_for_health() {
  local name="$1"
  local attempts=0
  while true; do
    attempts=$((attempts + 1))
    status="$(docker_cmd inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$name" 2>/dev/null || true)"
    if [[ "$status" == "healthy" || "$status" == "running" ]]; then
      return 0
    fi
    if (( attempts >= 30 )); then
      echo "timeout waiting for container health: $name" >&2
      docker_cmd logs "$name" 2>&1 || true
      return 1
    fi
    sleep 2
  done
}

docker_cmd() {
  printf '%s\n' "$SUDO_PASSWORD" | sudo -S docker "$@"
}

DOCKER_BIN="$(command -v docker)"
PYTHON_BIN="$(command -v python3)"

mkdir -p "$TOOLS_ROOT" "$LOG_ROOT" "$MANIFEST_ROOT" "$WORK_DIR" "$AICUT_ROOT"

require_dir "$CODE_ROOT/worker"
require_dir "$CODE_ROOT/apps"
require_dir "$CODE_ROOT/configs"
require_dir "$TOOLS_ROOT/tos_uploader"

DATABASE_URL="postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${A_HOST}:${DB_PORT}/${POSTGRES_DB}"
API_BASE_URL="http://${A_HOST}:${API_PORT}"

docker_cmd rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker_cmd run -d \
  --name "$CONTAINER_NAME" \
  --network host \
  -e WORKER_ID="$WORKER_ID" \
  -e WORKER_NAME="$WORKER_NAME" \
  -e DATABASE_URL="$DATABASE_URL" \
  -e API_BASE_URL="$API_BASE_URL" \
  -e USE_FAKE_TOS=false \
  -e TOS_MODE=real \
  -e TOS_ENDPOINT="$TOS_ENDPOINT" \
  -e TOS_REGION="$TOS_REGION" \
  -e TOS_BUCKET="$TOS_BUCKET" \
  -e TOS_ACCESS_KEY="$TOS_ACCESS_KEY" \
  -e TOS_SECRET_KEY="$TOS_SECRET_KEY" \
  -e USE_ALGORITHM_DOCKER_RUNNER=true \
  -e ALGORITHM_IMAGE="$ALGORITHM_IMAGE" \
  -e HOST_WORKER_DATA_BASE="$WORK_DIR" \
  -e HOST_WEBSITE_AICUT_ROOT="$CODE_ROOT" \
  -e HOST_AICUT2602_ROOT="$AICUT_ROOT" \
  -e DOCKER_BIN=/usr/local/bin/docker \
  -e WORKER_DATA_BASE=/data/worker-jobs \
  -v "$WORK_DIR:/data/worker-jobs" \
  -v "$CODE_ROOT/worker:/app/worker:ro" \
  -v "$CODE_ROOT/apps:/app/apps:ro" \
  -v "$CODE_ROOT/configs:/app/configs:ro" \
  -v /usr/bin/docker:/usr/local/bin/docker:ro \
  -v /var/run/docker.sock:/var/run/docker.sock \
  smart-cut-worker-gateway:0.0.3-dev

wait_for_health "$CONTAINER_NAME"

{
  echo "timestamp=$TIMESTAMP"
  echo "container=$CONTAINER_NAME"
  echo "worker_id=$WORKER_ID"
  echo "api_base_url=$API_BASE_URL"
  echo "database_url=$DATABASE_URL"
  echo "algorithm_image=$ALGORITHM_IMAGE"
  echo "docker_bin=$DOCKER_BIN"
  echo "python_bin=$PYTHON_BIN"
  echo
  docker_cmd ps --filter "name=$CONTAINER_NAME"
  echo
  docker_cmd inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CONTAINER_NAME"
} >"$HEALTH_PATH"

cat >"$MANIFEST_PATH" <<EOF
{
  "phase": "6",
  "timestamp": "$TIMESTAMP",
  "worker_host": "$(hostname)",
  "container_name": "$CONTAINER_NAME",
  "worker_id": "$WORKER_ID",
  "worker_name": "$WORKER_NAME",
  "root": "$ROOT",
  "code_root": "$CODE_ROOT",
  "aicut_root": "$AICUT_ROOT",
  "work_dir": "$WORK_DIR",
  "tools_root": "$TOOLS_ROOT",
  "api_base_url": "$API_BASE_URL",
  "database_url": "$DATABASE_URL",
  "algorithm_image": "$ALGORITHM_IMAGE",
  "healthcheck_path": "$HEALTH_PATH"
}
EOF

echo "manifest_path=$MANIFEST_PATH"
echo "healthcheck_path=$HEALTH_PATH"
