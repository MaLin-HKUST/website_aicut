#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001}"
VIDEO_PATH="${1:?video path required}"
TEXT_PATH="${2:?reference text path required}"
WORK_DIR="${3:?work dir required}"
USER_ID="${USER_ID:-rel0415-real-user}"
EDITED_SCRIPT_FILE="${4:-}"

mkdir -p "$WORK_DIR"

task_id="$(
  curl -s -X POST "$API_BASE/api/smart-cut/tasks" \
    -H 'Content-Type: application/json' \
    -d "{\"user_id\":\"$USER_ID\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["task_id"])'
)"
echo "TASK_ID=$task_id"

curl -s -X POST "$API_BASE/api/smart-cut/tasks/$task_id/upload-direct" \
  -F "video_file=@$VIDEO_PATH;type=video/mp4" \
  -F "reference_file=@$TEXT_PATH;type=text/plain" >"$WORK_DIR/upload_response.json"

for _ in $(seq 1 40); do
  status="$(curl -s "$API_BASE/api/smart-cut/tasks/$task_id" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status"))')"
  echo "ANALYZE_STATUS=$status"
  if [ "$status" = "waiting_user" ] || [ "$status" = "analyze_failed" ]; then
    break
  fi
  if [ "$status" = "ready_analyze" ]; then
    curl -s -X POST "$API_BASE/api/smart-cut/tasks/$task_id/analyze" >/dev/null
  fi
  sleep 2
done

if [ "${EDITED_SCRIPT_FILE}" != "" ]; then
  edited_script="$(python3 - <<'PY' "$EDITED_SCRIPT_FILE"
import json,sys
print(json.load(open(sys.argv[1], 'r', encoding='utf-8'))['edited_script'])
PY
)"

  curl -s -X POST "$API_BASE/api/smart-cut/tasks/$task_id/preview" \
    -H 'Content-Type: application/json' \
    -d "{\"edited_script\":\"$edited_script\"}" >"$WORK_DIR/preview_response.json"

  for _ in $(seq 1 40); do
    status="$(curl -s "$API_BASE/api/smart-cut/tasks/$task_id" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status"))')"
    echo "PREVIEW_STATUS=$status"
    if [ "$status" = "waiting_user" ] || [ "$status" = "preview_failed" ]; then
      break
    fi
    sleep 2
  done

  curl -s -X POST "$API_BASE/api/smart-cut/tasks/$task_id/finalize" \
    -H 'Content-Type: application/json' \
    -d '{"output_mode":"original","feed_to_ai":true}' >"$WORK_DIR/finalize_response.json"

  for _ in $(seq 1 50); do
    status="$(curl -s "$API_BASE/api/smart-cut/tasks/$task_id" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status"))')"
    echo "FINALIZE_STATUS=$status"
    if [ "$status" = "success" ] || [ "$status" = "finalize_failed" ]; then
      break
    fi
    sleep 2
  done
fi

curl -s "$API_BASE/api/smart-cut/tasks/$task_id" >"$WORK_DIR/task_detail.json"
curl -s "$API_BASE/api/smart-cut/tasks/$task_id/edits" >"$WORK_DIR/edits.json"
curl -s "$API_BASE/api/task-center/tasks?user_id=$USER_ID" >"$WORK_DIR/task_center_user.json"
curl -s "$API_BASE/api/admin/task-center/tasks" >"$WORK_DIR/task_center_admin.json"

ls -lh "$WORK_DIR"
