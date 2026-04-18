#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-14.103.249.104}"
REMOTE_USER="${REMOTE_USER:-malin}"
REMOTE_REPO_DIR="${REMOTE_REPO_DIR:-/home/malin/website_aicut_git}"
REMOTE_BARE_REPO="${REMOTE_BARE_REPO:-/home/malin/website_aicut_repo.git}"
SLOT_ROOT="${SLOT_ROOT:-/home/malin/release_0415_slot}"
REF="${1:-}"
CURRENT_BRANCH="${CURRENT_BRANCH:-$(git branch --show-current)}"

if [[ -n "$REF" ]]; then
  git push "ssh://$REMOTE_USER@$REMOTE_HOST$REMOTE_BARE_REPO" "$REF:refs/heads/$CURRENT_BRANCH"
  ssh "$REMOTE_USER@$REMOTE_HOST" "REF='$CURRENT_BRANCH' bash '$REMOTE_REPO_DIR/scripts/rel0415/remote_build_and_switch_web.sh' '$REMOTE_REPO_DIR' '$SLOT_ROOT'"
else
  git push "ssh://$REMOTE_USER@$REMOTE_HOST$REMOTE_BARE_REPO" "HEAD:refs/heads/$CURRENT_BRANCH"
  ssh "$REMOTE_USER@$REMOTE_HOST" "BRANCH='$CURRENT_BRANCH' bash '$REMOTE_REPO_DIR/scripts/rel0415/remote_build_and_switch_web.sh' '$REMOTE_REPO_DIR' '$SLOT_ROOT'"
fi
