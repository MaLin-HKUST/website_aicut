#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/home/malin/release_0415_slot}"
PORT="${PORT:-3001}"

WEB_RUNTIME_DIR="$ROOT/web_runtime_af30ae1"
WEB_RUNTIME_TGZ="$ROOT/release_0415_web_runtime_af30ae1.tgz"
WEB_LOG="$ROOT/web_${PORT}.log"
WEB_PID="$ROOT/web_${PORT}.pid"

rm -rf "$WEB_RUNTIME_DIR"
mkdir -p "$WEB_RUNTIME_DIR"
tar -xzf "$WEB_RUNTIME_TGZ" -C "$WEB_RUNTIME_DIR"

pkill -f "$WEB_RUNTIME_DIR/server.js" || true

cd "$WEB_RUNTIME_DIR"
nohup env \
  LEGACY_API_BASE_URL="${LEGACY_API_BASE_URL:-http://127.0.0.1:8000}" \
  SMART_CUT_API_BASE_URL="${SMART_CUT_API_BASE_URL:-http://127.0.0.1:8001}" \
  PORT="$PORT" \
  HOSTNAME="${HOSTNAME:-127.0.0.1}" \
  node server.js >"$WEB_LOG" 2>&1 &

echo $! >"$WEB_PID"
sleep 2
cat "$WEB_PID"
curl -I "http://127.0.0.1:${PORT}/login"
