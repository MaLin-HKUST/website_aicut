#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/home/malin/release_0415_slot}"
PORT="${PORT:-3001}"

cat "$ROOT/web_${PORT}.pid" 2>/dev/null || true
if [ -f "$ROOT/web_${PORT}.pid" ]; then
  PID="$(cat "$ROOT/web_${PORT}.pid")"
  ps -fp "$PID" || true
fi
curl -I "http://127.0.0.1:${PORT}/login" || true
tail -n 40 "$ROOT/web_${PORT}.log" 2>/dev/null || true
