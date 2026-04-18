#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-14.103.249.104}"
REMOTE_USER="${REMOTE_USER:-malin}"
REMOTE_REPO_DIR="${REMOTE_REPO_DIR:-/home/malin/website_aicut_git}"
REMOTE_BARE_REPO="${REMOTE_BARE_REPO:-/home/malin/website_aicut_repo.git}"
CURRENT_BRANCH="${CURRENT_BRANCH:-$(git branch --show-current)}"

ssh "$REMOTE_USER@$REMOTE_HOST" "
  set -euo pipefail
  if [ ! -d '$REMOTE_BARE_REPO' ]; then
    git init --bare '$REMOTE_BARE_REPO'
  fi
"

git push "ssh://$REMOTE_USER@$REMOTE_HOST$REMOTE_BARE_REPO" "HEAD:refs/heads/$CURRENT_BRANCH"

ssh "$REMOTE_USER@$REMOTE_HOST" "
  set -euo pipefail
  if [ ! -d '$REMOTE_REPO_DIR/.git' ]; then
    git clone '$REMOTE_BARE_REPO' '$REMOTE_REPO_DIR'
  fi
  cd '$REMOTE_REPO_DIR'
  git remote set-url origin '$REMOTE_BARE_REPO'
  git fetch origin '$CURRENT_BRANCH'
  git checkout '$CURRENT_BRANCH'
"
