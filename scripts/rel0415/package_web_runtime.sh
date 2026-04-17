#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB_DIR="$ROOT/apps/web"
BUILD_ID="${1:-af30ae1}"
OUTPUT_TGZ="${2:-$ROOT/release_0415_web_runtime_${BUILD_ID}.tgz}"
STAGE_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$STAGE_DIR"
}
trap cleanup EXIT

if [[ ! -f "$WEB_DIR/.next/standalone/server.js" ]]; then
  echo "missing $WEB_DIR/.next/standalone/server.js; run npm --prefix apps/web run build first" >&2
  exit 1
fi

if [[ ! -d "$WEB_DIR/.next/static" ]]; then
  echo "missing $WEB_DIR/.next/static; run npm --prefix apps/web run build first" >&2
  exit 1
fi

cp -R "$WEB_DIR/.next/standalone/." "$STAGE_DIR/"
mkdir -p "$STAGE_DIR/.next"
cp -R "$WEB_DIR/.next/static" "$STAGE_DIR/.next/static"

if [[ -d "$WEB_DIR/public" ]]; then
  cp -R "$WEB_DIR/public" "$STAGE_DIR/public"
fi

mkdir -p "$(dirname "$OUTPUT_TGZ")"
tar -czf "$OUTPUT_TGZ" -C "$STAGE_DIR" .
echo "$OUTPUT_TGZ"
