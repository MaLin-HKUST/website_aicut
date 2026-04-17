#!/usr/bin/env bash
set -euo pipefail

CONF="/etc/nginx/sites-enabled/xiaomajianji.cn"
BACKUP_DIR="/home/malin/release_0415_slot/nginx_backups"
LATEST_BACKUP="$(ls -1t "$BACKUP_DIR"/xiaomajianji.cn.*.bak | head -n 1)"

if [ -z "${LATEST_BACKUP:-}" ]; then
  echo "No nginx backup found in $BACKUP_DIR" >&2
  exit 1
fi

cp "$LATEST_BACKUP" "$CONF"
nginx -t
systemctl reload nginx
