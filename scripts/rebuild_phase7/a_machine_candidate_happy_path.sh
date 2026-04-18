#!/usr/bin/env bash
set -euo pipefail

PROD_ROOT="${1:-/home/malin/website_aicut_prod}"
API_BASE="${2:-http://127.0.0.1:18001}"
RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
ARTIFACT_DIR="$PROD_ROOT/manifests/phase7_happy_path_${RUN_ID}"
mkdir -p "$ARTIFACT_DIR"

json_get() {
  local file="$1"
  local expr="$2"
  python3 - "$file" "$expr" <<'PY'
import json, sys
path, expr = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
for part in expr.split("."):
    if part:
        data = data[part]
if isinstance(data, (dict, list)):
    print(json.dumps(data, ensure_ascii=False))
else:
    print(data)
PY
}

poll_task_until() {
  local task_id="$1"
  local expected_status="$2"
  local expected_stage="$3"
  local label="$4"
  local attempt=0
  while true; do
    attempt=$((attempt + 1))
    curl -fsS "$API_BASE/api/smart-cut/tasks/$task_id" >"$ARTIFACT_DIR/${label}_status_${attempt}.json"
    local status
    local stage
    status="$(json_get "$ARTIFACT_DIR/${label}_status_${attempt}.json" "status")"
    stage="$(json_get "$ARTIFACT_DIR/${label}_status_${attempt}.json" "current_stage")"
    printf '%s %s %s\n' "$attempt" "$status" "$stage" >>"$ARTIFACT_DIR/${label}_poll.log"
    if [[ "$status" == "$expected_status" && "$stage" == "$expected_stage" ]]; then
      echo "$ARTIFACT_DIR/${label}_status_${attempt}.json"
      return 0
    fi
    if [[ "$status" == "analyze_failed" || "$status" == "preview_failed" || "$status" == "finalize_failed" || "$status" == "failed" ]]; then
      echo "task entered failure state during $label: $status/$stage" >&2
      return 1
    fi
    if (( attempt >= 60 )); then
      echo "timeout waiting for $label -> $expected_status/$expected_stage" >&2
      return 1
    fi
    sleep 2
  done
}

curl -fsS -X POST \
  "$API_BASE/api/smart-cut/tasks" \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"phase7-happy-path","task_name":"phase7 happy path"}' \
  >"$ARTIFACT_DIR/create.json"

TASK_ID="$(json_get "$ARTIFACT_DIR/create.json" "data.task_id")"
echo "$TASK_ID" >"$ARTIFACT_DIR/task_id.txt"

printf 'phase7 sample video bytes\n' >"$ARTIFACT_DIR/source_video.mp4"
cat >"$ARTIFACT_DIR/reference.txt" <<'EOF'
这是阶段七的参考文案。
请使用稳定、清晰的语气完成示例流程。
EOF

curl -fsS -X POST \
  "$API_BASE/api/smart-cut/tasks/$TASK_ID/upload-direct" \
  -F "video_file=@$ARTIFACT_DIR/source_video.mp4" \
  -F "reference_file=@$ARTIFACT_DIR/reference.txt" \
  >"$ARTIFACT_DIR/upload.json"

curl -fsS -X POST \
  "$API_BASE/api/smart-cut/tasks/$TASK_ID/analyze" \
  >"$ARTIFACT_DIR/analyze.json"

ANALYZE_STATUS_JSON="$(poll_task_until "$TASK_ID" "waiting_user" "user_select" "analyze")"
cp "$ANALYZE_STATUS_JSON" "$ARTIFACT_DIR/analyze_complete.json"

python3 - "$ARTIFACT_DIR/analyze_complete.json" >"$ARTIFACT_DIR/preview_request.json" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)
edited = data.get("current_edited_script") or data.get("analyze_script")
if edited is None:
    raise SystemExit("missing edited/analyze script for preview")
json.dump({"edited_script": edited}, sys.stdout, ensure_ascii=False)
PY

curl -fsS -X POST \
  "$API_BASE/api/smart-cut/tasks/$TASK_ID/preview" \
  -H 'Content-Type: application/json' \
  --data-binary @"$ARTIFACT_DIR/preview_request.json" \
  >"$ARTIFACT_DIR/preview.json"

PREVIEW_STATUS_JSON="$(poll_task_until "$TASK_ID" "waiting_user" "user_select" "preview")"
cp "$PREVIEW_STATUS_JSON" "$ARTIFACT_DIR/preview_complete.json"

python3 - "$ARTIFACT_DIR/preview_complete.json" >"$ARTIFACT_DIR/finalize_request.json" <<'PY'
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)
json.dump({
    "output_mode": "original",
    "feed_to_ai": False,
    "edit_id": data.get("active_edit_id"),
}, sys.stdout, ensure_ascii=False)
PY

curl -fsS -X POST \
  "$API_BASE/api/smart-cut/tasks/$TASK_ID/finalize" \
  -H 'Content-Type: application/json' \
  --data-binary @"$ARTIFACT_DIR/finalize_request.json" \
  >"$ARTIFACT_DIR/finalize.json"

FINAL_STATUS_JSON="$(poll_task_until "$TASK_ID" "success" "completed" "finalize")"
cp "$FINAL_STATUS_JSON" "$ARTIFACT_DIR/final_success.json"

python3 - "$ARTIFACT_DIR/final_success.json" <<'PY' >"$ARTIFACT_DIR/summary.txt"
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)
print(f"task_id={data['id']}")
print(f"status={data['status']}")
print(f"current_stage={data['current_stage']}")
print(f"final_video_url={data.get('final_video_url')}")
print(f"groundtruth_url={data.get('groundtruth_url')}")
PY

echo "$ARTIFACT_DIR"
