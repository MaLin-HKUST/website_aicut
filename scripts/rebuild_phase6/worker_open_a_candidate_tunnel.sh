#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${KEY_PATH:-/home/malin/website_aicut_worker_prod/tools/a_machine_rebuild_key}"
KNOWN_HOSTS="${KNOWN_HOSTS:-/home/malin/website_aicut_worker_prod/tools/known_hosts}"
LOG_PATH="${LOG_PATH:-/home/malin/website_aicut_worker_prod/logs/a_machine_candidate_tunnel.log}"
PID_PATH="${PID_PATH:-/home/malin/website_aicut_worker_prod/logs/a_machine_candidate_tunnel.pid}"

A_HOST="${A_HOST:-14.103.249.104}"
REMOTE_PG_PORT="${REMOTE_PG_PORT:-55433}"
REMOTE_API_PORT="${REMOTE_API_PORT:-18001}"
LOCAL_PG_PORT="${LOCAL_PG_PORT:-65433}"
LOCAL_API_PORT="${LOCAL_API_PORT:-61001}"

mkdir -p "$(dirname "$LOG_PATH")" "$(dirname "$PID_PATH")" "$(dirname "$KNOWN_HOSTS")"
chmod 600 "$KEY_PATH"

pkill -f "${LOCAL_PG_PORT}:127.0.0.1:${REMOTE_PG_PORT}" >/dev/null 2>&1 || true
pkill -f "${LOCAL_API_PORT}:127.0.0.1:${REMOTE_API_PORT}" >/dev/null 2>&1 || true

nohup ssh \
  -N \
  -i "$KEY_PATH" \
  -o ExitOnForwardFailure=yes \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile="$KNOWN_HOSTS" \
  -L "${LOCAL_PG_PORT}:127.0.0.1:${REMOTE_PG_PORT}" \
  -L "${LOCAL_API_PORT}:127.0.0.1:${REMOTE_API_PORT}" \
  "malin@${A_HOST}" \
  >"$LOG_PATH" 2>&1 </dev/null &

echo $! >"$PID_PATH"
sleep 2

python3 - <<PY
import socket, sys
checks = [("127.0.0.1", int("${LOCAL_PG_PORT}")), ("127.0.0.1", int("${LOCAL_API_PORT}"))]
failures = []
for host, port in checks:
    s = socket.socket()
    s.settimeout(5)
    try:
        s.connect((host, port))
        print(f"tunnel_ok {host}:{port}")
    except Exception as exc:
        failures.append(f"tunnel_fail {host}:{port} {exc}")
    finally:
        s.close()
if failures:
    for item in failures:
        print(item)
    sys.exit(1)
PY

echo "pid_path=$PID_PATH"
echo "log_path=$LOG_PATH"
