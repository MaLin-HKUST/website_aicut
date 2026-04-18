#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:18001}"
WORK_ROOT="${WORK_ROOT:-/home/malin/website_aicut_prod/manifests}"
TOS_TOOL_ROOT="${TOS_TOOL_ROOT:-/home/malin/website_aicut_prod/tools/tos_uploader}"
TOS_BUCKET="${TOS_BUCKET:-autocut-malin}"
TOS_ENDPOINT="${TOS_ENDPOINT:-tos-cn-shanghai.volces.com}"
TOS_REGION="${TOS_REGION:-cn-shanghai}"
TOS_ACCESS_KEY="${TOS_ACCESS_KEY:-}"
TOS_SECRET_KEY="${TOS_SECRET_KEY:-}"
SUDO_PASSWORD="${SUDO_PASSWORD:-123456}"
PG_CONTAINER="${PG_CONTAINER:-a-machine-phase5-postgres}"
PG_PORT="${PG_PORT:-55433}"
PG_USER="${PG_USER:-scheduler}"
PG_PASSWORD="${PG_PASSWORD:-scheduler}"
PG_DB="${PG_DB:-scheduler}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
WORK_DIR="$WORK_ROOT/phase6_smoke_via_tos_$TIMESTAMP"
INPUT_DIR="$WORK_DIR/input"

mkdir -p "$INPUT_DIR"

printf 'fake video bytes for phase6 via tos\n' > "$INPUT_DIR/source_video.mp4"
printf 'phase6 reference text via tos\n' > "$INPUT_DIR/reference.txt"

curl -sS -X POST "$API_BASE_URL/api/smart-cut/tasks" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"phase6-smoke-via-tos"}' >"$WORK_DIR/create.json"

TASK_ID="$(python3 - <<PY
import json
from pathlib import Path
payload = json.loads(Path("$WORK_DIR/create.json").read_text())
print(payload["data"]["task_id"])
PY
)"

echo "$TASK_ID" >"$WORK_DIR/task_id.txt"

python3 - <<PY >"$WORK_DIR/tos_upload.log" 2>&1
import json
import sys
from pathlib import Path

sys.path.insert(0, "$TOS_TOOL_ROOT")
from tos_folder_uploader import TOSFolderUploader, TOS_Param

tos_param = TOS_Param(
    ak="$TOS_ACCESS_KEY",
    sk="$TOS_SECRET_KEY",
    endpoint="$TOS_ENDPOINT",
    region="$TOS_REGION",
    bucket_name="$TOS_BUCKET",
)
uploader = TOSFolderUploader(tos_param)
stats = uploader.upload_folder("$INPUT_DIR", prefix="smart-cut/$TASK_ID/input", max_workers=2)
print(json.dumps(stats, ensure_ascii=False))
if stats.get("failed_files"):
    raise SystemExit(1)
PY

VIDEO_KEY="smart-cut/$TASK_ID/input/source_video.mp4"
TEXT_KEY="smart-cut/$TASK_ID/input/reference.txt"

printf '%s\n' "$SUDO_PASSWORD" | sudo -S docker exec -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" \
  psql -h 127.0.0.1 -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
  -c "update smart_cut_tasks set original_video_url='$VIDEO_KEY', reference_text_url='$TEXT_KEY', status='READY_ANALYZE', current_stage='ANALYZE', updated_at=now() where id='$TASK_ID';" \
  >"$WORK_DIR/update_task.sql.log" 2>&1

curl -sS -X POST "$API_BASE_URL/api/smart-cut/tasks/$TASK_ID/analyze" >"$WORK_DIR/analyze.json"

LAST_INDEX=0
for i in $(seq 1 24); do
  curl -sS "$API_BASE_URL/api/smart-cut/tasks/$TASK_ID" >"$WORK_DIR/status_$i.json"
  STATUS="$(python3 - <<PY
import json
from pathlib import Path
payload = json.loads(Path("$WORK_DIR/status_$i.json").read_text())
print(payload["status"])
PY
)"
  echo "$i $STATUS" >>"$WORK_DIR/poll.log"
  LAST_INDEX="$i"
  if [[ "$STATUS" == "waiting_user" || "$STATUS" == "analyze_failed" ]]; then
    break
  fi
  sleep 5
done

echo "work_dir=$WORK_DIR"
echo "task_id=$TASK_ID"
echo "last_index=$LAST_INDEX"
