#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001}"
WORK_DIR="${1:-/home/malin/release_0415_slot/happy_path}"
USER_ID="${USER_ID:-release0415-user}"

mkdir -p "$WORK_DIR"
VIDEO_FILE="$WORK_DIR/source_video.mp4"
TEXT_FILE="$WORK_DIR/reference.txt"

printf 'fake-video' >"$VIDEO_FILE"
printf '这是 0415 happy path 测试文案。' >"$TEXT_FILE"

task_id="$(
  curl -s -X POST "$API_BASE/api/smart-cut/tasks" \
    -H 'Content-Type: application/json' \
    -d "{\"user_id\":\"$USER_ID\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["task_id"])'
)"
echo "TASK_ID=$task_id"

curl -s -X POST "$API_BASE/api/smart-cut/tasks/$task_id/upload-direct" \
  -F "video_file=@$VIDEO_FILE;type=video/mp4" \
  -F "reference_file=@$TEXT_FILE;type=text/plain" >/dev/null

curl -s -X POST "$API_BASE/api/smart-cut/tasks/$task_id/analyze" >/dev/null

for _ in $(seq 1 20); do
  status="$(curl -s "$API_BASE/api/smart-cut/tasks/$task_id" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  echo "ANALYZE_STATUS=$status"
  if [ "$status" = "waiting_user" ]; then
    break
  fi
  sleep 2
done

curl -s -X POST "$API_BASE/api/smart-cut/tasks/$task_id/preview" \
  -H 'Content-Type: application/json' \
  -d '{"edited_script":"{这是 0415 happy path 测试文案。}"}' >/dev/null

for _ in $(seq 1 20); do
  status="$(curl -s "$API_BASE/api/smart-cut/tasks/$task_id" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  echo "PREVIEW_STATUS=$status"
  if [ "$status" = "waiting_user" ]; then
    break
  fi
  sleep 2
done

curl -s -X POST "$API_BASE/api/smart-cut/tasks/$task_id/finalize" \
  -H 'Content-Type: application/json' \
  -d '{"output_mode":"original","feed_to_ai":true}' >/dev/null

for _ in $(seq 1 20); do
  status="$(curl -s "$API_BASE/api/smart-cut/tasks/$task_id" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  echo "FINALIZE_STATUS=$status"
  if [ "$status" = "success" ]; then
    break
  fi
  sleep 2
done

curl -s "$API_BASE/api/task-center/tasks?user_id=$USER_ID" >"$WORK_DIR/task_center_user.json"
curl -s "$API_BASE/api/admin/task-center/tasks" >"$WORK_DIR/task_center_admin.json"
curl -s "$API_BASE/api/smart-cut/tasks/$task_id" >"$WORK_DIR/task_detail.json"

echo "Happy path artifacts:"
ls -lh "$WORK_DIR"
