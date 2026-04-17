#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001}"
TASK_ID="${1:?task id required}"
EDITED_SCRIPT="${2:-{这是 0415 happy path 测试文案。}}"

curl -s -X POST "$API_BASE/api/smart-cut/tasks/$TASK_ID/preview" \
  -H 'Content-Type: application/json' \
  -d "{\"edited_script\":\"$EDITED_SCRIPT\"}"
echo

for _ in $(seq 1 20); do
  status="$(curl -s "$API_BASE/api/smart-cut/tasks/$TASK_ID" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status"))')"
  echo "PREVIEW_STATUS=$status"
  if [ "$status" = "waiting_user" ] || [ "$status" = "preview_failed" ]; then
    break
  fi
  sleep 2
done

curl -s -X POST "$API_BASE/api/smart-cut/tasks/$TASK_ID/finalize" \
  -H 'Content-Type: application/json' \
  -d '{"output_mode":"original","feed_to_ai":true}'
echo

for _ in $(seq 1 20); do
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
echo "---EDITS---"
curl -s "$API_BASE/api/smart-cut/tasks/$TASK_ID/edits"
