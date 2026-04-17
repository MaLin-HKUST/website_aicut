#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001}"
TASK_ID="${1:?task id required}"

curl -s -X POST "$API_BASE/api/smart-cut/tasks/$TASK_ID/finalize" \
  -H 'Content-Type: application/json' \
  -d '{"output_mode":"original","feed_to_ai":true}'
echo

for _ in $(seq 1 25); do
  status="$(curl -s "$API_BASE/api/smart-cut/tasks/$TASK_ID" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status"))')"
  echo "FINALIZE_STATUS=$status"
  if [ "$status" = "success" ] || [ "$status" = "finalize_failed" ]; then
    break
  fi
  sleep 2
done

echo "---DETAIL---"
curl -s "$API_BASE/api/smart-cut/tasks/$TASK_ID"
echo
echo "---TASK_CENTER_USER---"
curl -s "$API_BASE/api/task-center/tasks?user_id=release0415-user"
