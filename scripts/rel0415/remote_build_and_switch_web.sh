#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-/home/malin/website_aicut_git}"
SLOT_ROOT="${2:-/home/malin/release_0415_slot}"
REF="${REF:-}"
BRANCH="${BRANCH:-}"

BACKUP_DIR="$SLOT_ROOT/backups/web_runtime"
RUNTIME_NAME="release_0415_web_runtime_af30ae1.tgz"
RUNTIME_PATH="$SLOT_ROOT/$RUNTIME_NAME"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "remote repo is not a git checkout: $REPO_DIR" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

cd "$REPO_DIR"

if [[ -n "$REF" ]]; then
  git fetch origin "$REF"
  git checkout --detach FETCH_HEAD
else
  CURRENT_BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"
  git fetch origin "$CURRENT_BRANCH"
  git pull --ff-only origin "$CURRENT_BRANCH"
fi

if [[ ! -x "$REPO_DIR/apps/web/node_modules/.bin/next" ]]; then
  npm --prefix apps/web install
fi

npm --prefix apps/web run build

BUILD_ID="$(git rev-parse --short HEAD)"
TMP_RUNTIME="$REPO_DIR/release_0415_web_runtime_${BUILD_ID}.tgz"
bash "$REPO_DIR/scripts/rel0415/package_web_runtime.sh" "$BUILD_ID" "$TMP_RUNTIME"

if [[ -f "$RUNTIME_PATH" ]]; then
  cp "$RUNTIME_PATH" "$BACKUP_DIR/${TIMESTAMP}_${RUNTIME_NAME}"
fi

cp "$TMP_RUNTIME" "$RUNTIME_PATH"
bash "$SLOT_ROOT/start_web_slot.sh" "$SLOT_ROOT"

echo "deployed_commit=$(git rev-parse HEAD)"
echo "backup_runtime=${BACKUP_DIR}/${TIMESTAMP}_${RUNTIME_NAME}"
