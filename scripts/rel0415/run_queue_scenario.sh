#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001}"
WORK_DIR="${1:-/home/malin/release_0415_slot/queue_scenario}"
USER_ID="${USER_ID:-rel0415-queue-user}"

mkdir -p "$WORK_DIR"
VIDEO_FILE="$WORK_DIR/queue_video.mp4"
TEXT_FILE="$WORK_DIR/queue_reference.txt"
printf 'queue-video' >"$VIDEO_FILE"
printf 'queue reference text' >"$TEXT_FILE"

task_ids=()
for idx in 1 2 3; do
  task_id="$(
    curl -s -X POST "$API_BASE/api/smart-cut/tasks" \
      -H 'Content-Type: application/json' \
      -d "{\"user_id\":\"$USER_ID\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["task_id"])'
  )"
  task_ids+=("$task_id")

  curl -s -X POST "$API_BASE/api/smart-cut/tasks/$task_id/upload-direct" \
    -F "video_file=@$VIDEO_FILE;type=video/mp4" \
    -F "reference_file=@$TEXT_FILE;type=text/plain" >/dev/null
  curl -s -X POST "$API_BASE/api/smart-cut/tasks/$task_id/analyze" >/dev/null
done

curl -s "$API_BASE/api/task-center/tasks?user_id=$USER_ID" >"$WORK_DIR/task_center_user_early.json"
curl -s "$API_BASE/api/admin/task-center/tasks" >"$WORK_DIR/task_center_admin_early.json"

sleep 6

curl -s "$API_BASE/api/task-center/tasks?user_id=$USER_ID" >"$WORK_DIR/task_center_user.json"
curl -s "$API_BASE/api/admin/task-center/tasks" >"$WORK_DIR/task_center_admin.json"
printf '%s\n' "${task_ids[@]}" >"$WORK_DIR/task_ids.txt"
ls -lh "$WORK_DIR"
