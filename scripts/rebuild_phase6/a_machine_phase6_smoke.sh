#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:18001}"
WORK_ROOT="${WORK_ROOT:-/home/malin/website_aicut_prod/manifests}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
WORK_DIR="$WORK_ROOT/phase6_smoke_$TIMESTAMP"

mkdir -p "$WORK_DIR"

printf 'fake video bytes for phase6\n' > "$WORK_DIR/source_video.mp4"
printf 'phase6 reference text\n' > "$WORK_DIR/reference.txt"

curl -sS -X POST "$API_BASE_URL/api/smart-cut/tasks" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"phase6-smoke"}' >"$WORK_DIR/create.json"

TASK_ID="$(python3 - <<PY
import json
from pathlib import Path
payload = json.loads(Path("$WORK_DIR/create.json").read_text())
print(payload["data"]["task_id"])
PY
)"

echo "$TASK_ID" >"$WORK_DIR/task_id.txt"

curl -sS -X POST "$API_BASE_URL/api/smart-cut/tasks/$TASK_ID/upload-direct" \
  -F "video_file=@$WORK_DIR/source_video.mp4" \
  -F "reference_file=@$WORK_DIR/reference.txt" >"$WORK_DIR/upload.json"

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
