#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-/home/malin/website_aicut_git}"
PROD_ROOT="${2:-/home/malin/website_aicut_prod}"
REF="${REF:-}"
BRANCH="${BRANCH:-}"

LEGACY_API_BASE_URL="${LEGACY_API_BASE_URL:-http://127.0.0.1:8000}"
SMART_CUT_API_PORT="${SMART_CUT_API_PORT:-18001}"
WEB_PORT="${WEB_PORT:-3301}"
PG_PORT="${PG_PORT:-55433}"

PG_CONTAINER="${PG_CONTAINER:-a-machine-phase5-postgres}"
API_CONTAINER="${API_CONTAINER:-a-machine-phase5-api}"
SCHEDULER_CONTAINER="${SCHEDULER_CONTAINER:-a-machine-phase5-scheduler}"
IMAGE_TAG="${IMAGE_TAG:-a-machine-phase5-scheduler}"

POSTGRES_USER="${POSTGRES_USER:-scheduler}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-scheduler}"
POSTGRES_DB="${POSTGRES_DB:-scheduler}"
TOS_ENDPOINT="${TOS_ENDPOINT:-}"
TOS_REGION="${TOS_REGION:-cn-shanghai}"
TOS_BUCKET="${TOS_BUCKET:-}"
TOS_ACCESS_KEY="${TOS_ACCESS_KEY:-}"
TOS_SECRET_KEY="${TOS_SECRET_KEY:-}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BUILD_ID=""

require_file() {
  local path="$1"
  if [[ ! -e "$path" ]]; then
    echo "required path missing: $path" >&2
    exit 1
  fi
}

wait_http() {
  local url="$1"
  local label="$2"
  local attempt=0
  until curl -fsS "$url" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if (( attempt >= 30 )); then
      echo "timeout waiting for ${label}: ${url}" >&2
      return 1
    fi
    sleep 2
  done
}

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "remote repo is not a git checkout: $REPO_DIR" >&2
  exit 1
fi

mkdir -p \
  "$PROD_ROOT"/{logs,manifests,tools,web,postgres-data} \
  "$PROD_ROOT/backups"/{web_runtime,manifests}

cd "$REPO_DIR"

if [[ -n "$REF" ]]; then
  git fetch origin "$REF"
  git checkout --detach FETCH_HEAD
else
  CURRENT_BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
  git fetch origin "$CURRENT_BRANCH"
  git pull --ff-only origin "$CURRENT_BRANCH"
fi

BUILD_ID="$(git rev-parse --short HEAD)"
MANIFEST_PATH="$PROD_ROOT/manifests/a_machine_stable_anchor_2_manifest.json"
HEALTHCHECK_PATH="$PROD_ROOT/manifests/a_machine_candidate_health_${TIMESTAMP}.txt"

if [[ -d /tmp/tos_uploader_runtime ]]; then
  rm -rf "$PROD_ROOT/tools/tos_uploader"
  mkdir -p "$PROD_ROOT/tools/tos_uploader"
  cp -R /tmp/tos_uploader_runtime/. "$PROD_ROOT/tools/tos_uploader/"
fi

npm --prefix apps/web install --no-fund --no-audit
NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=1536}" npm --prefix apps/web run build

TMP_RUNTIME="$PROD_ROOT/backups/web_runtime/release_0415_web_runtime_${BUILD_ID}_${TIMESTAMP}.tgz"
bash "$REPO_DIR/scripts/rel0415/package_web_runtime.sh" "$BUILD_ID" "$TMP_RUNTIME"
cp "$TMP_RUNTIME" "$PROD_ROOT/web/release_0415_web_runtime_af30ae1.tgz"

docker rm -f "$PG_CONTAINER" "$API_CONTAINER" "$SCHEDULER_CONTAINER" >/dev/null 2>&1 || true

docker run -d \
  --name "$PG_CONTAINER" \
  --network host \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v "$PROD_ROOT/postgres-data:/var/lib/postgresql/data" \
  postgres:16-alpine \
  -p "$PG_PORT"

sleep 5
for _ in $(seq 1 30); do
  if docker exec "$PG_CONTAINER" pg_isready -h 127.0.0.1 -p "$PG_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

docker build -f apps/api/Dockerfile -t "$IMAGE_TAG:$BUILD_ID" .

CANDIDATE_DB_URL="postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${PG_PORT}/${POSTGRES_DB}"

docker run -d \
  --name "$API_CONTAINER" \
  --network host \
  -e DATABASE_URL="$CANDIDATE_DB_URL" \
  -e SCHEDULER_DATABASE_URL="$CANDIDATE_DB_URL" \
  -e TOS_MODE=real \
  -e TOS_ENDPOINT="$TOS_ENDPOINT" \
  -e TOS_REGION="$TOS_REGION" \
  -e TOS_BUCKET="$TOS_BUCKET" \
  -e TOS_ACCESS_KEY="$TOS_ACCESS_KEY" \
  -e TOS_SECRET_KEY="$TOS_SECRET_KEY" \
  "$IMAGE_TAG:$BUILD_ID" \
  uvicorn apps.api.main:app --host 0.0.0.0 --port "$SMART_CUT_API_PORT"

docker run -d \
  --name "$SCHEDULER_CONTAINER" \
  --network host \
  -e SCHEDULER_DATABASE_URL="$CANDIDATE_DB_URL" \
  -e TOS_MODE=real \
  -e TOS_ENDPOINT="$TOS_ENDPOINT" \
  -e TOS_REGION="$TOS_REGION" \
  -e TOS_BUCKET="$TOS_BUCKET" \
  -e TOS_ACCESS_KEY="$TOS_ACCESS_KEY" \
  -e TOS_SECRET_KEY="$TOS_SECRET_KEY" \
  "$IMAGE_TAG:$BUILD_ID" \
  python -m apps.scheduler.main

PORT="$WEB_PORT" \
LEGACY_API_BASE_URL="$LEGACY_API_BASE_URL" \
SMART_CUT_API_BASE_URL="http://127.0.0.1:${SMART_CUT_API_PORT}" \
bash "$REPO_DIR/scripts/rel0415/start_web_slot.sh" "$PROD_ROOT/web"

wait_http "http://127.0.0.1:${SMART_CUT_API_PORT}/health" "candidate smart-cut api"
wait_http "http://127.0.0.1:${WEB_PORT}/login" "candidate web login"

{
  echo "build_id=$BUILD_ID"
  echo "legacy_api=$LEGACY_API_BASE_URL"
  echo "smart_cut_api=http://127.0.0.1:${SMART_CUT_API_PORT}"
  echo "web=http://127.0.0.1:${WEB_PORT}"
  echo "postgres_port=$PG_PORT"
  echo "image_tag=$IMAGE_TAG:$BUILD_ID"
  echo "timestamp=$TIMESTAMP"
  echo
  echo "# smart-cut api"
  curl -fsS "http://127.0.0.1:${SMART_CUT_API_PORT}/health"
  echo
  echo "# web login headers"
  curl -I "http://127.0.0.1:${WEB_PORT}/login"
} >"$HEALTHCHECK_PATH"

cat >"$MANIFEST_PATH" <<EOF
{
  "phase": "5",
  "timestamp": "$TIMESTAMP",
  "commit": "$(git rev-parse HEAD)",
  "build_id": "$BUILD_ID",
  "prod_root": "$PROD_ROOT",
  "legacy_api_base_url": "$LEGACY_API_BASE_URL",
  "smart_cut_api_base_url": "http://127.0.0.1:${SMART_CUT_API_PORT}",
  "web_base_url": "http://127.0.0.1:${WEB_PORT}",
  "postgres_port": $PG_PORT,
  "containers": {
    "postgres": "$PG_CONTAINER",
    "api": "$API_CONTAINER",
    "scheduler": "$SCHEDULER_CONTAINER"
  },
  "image_tag": "$IMAGE_TAG:$BUILD_ID",
  "healthcheck_path": "$HEALTHCHECK_PATH",
  "tos_tool_dir": "$PROD_ROOT/tools/tos_uploader"
}
EOF

echo "manifest_path=$MANIFEST_PATH"
echo "healthcheck_path=$HEALTHCHECK_PATH"
