#!/usr/bin/env bash
set -euo pipefail

CONF="/etc/nginx/sites-enabled/xiaomajianji.cn"
BACKUP_DIR="/home/malin/release_0415_slot/nginx_backups"
WEB_TARGET="${WEB_TARGET:-http://192.168.92.197:3001}"
LEGACY_WEB_TARGET="${LEGACY_WEB_TARGET:-http://127.0.0.1:3000}"

mkdir -p "$BACKUP_DIR"
cp "$CONF" "$BACKUP_DIR/xiaomajianji.cn.$(date +%Y%m%d_%H%M%S).bak"

cat >"$CONF" <<EOF
server {
    listen 80;
    server_name xiaomajianji.cn www.xiaomajianji.cn;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl;
    server_name xiaomajianji.cn www.xiaomajianji.cn;

    ssl_certificate /etc/letsencrypt/live/xiaomajianji.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xiaomajianji.cn/privkey.pem;

    location /api/proxy/ {
        proxy_pass ${WEB_TARGET}/api/proxy/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /_next/static/ {
        proxy_pass ${WEB_TARGET}/_next/static/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /welcome {
        proxy_pass ${WEB_TARGET}/welcome;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /smart-cut {
        proxy_pass ${WEB_TARGET}/smart-cut;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location ^~ /smart-cut/ {
        proxy_pass ${WEB_TARGET}/smart-cut/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /tasks {
        proxy_pass ${WEB_TARGET}/tasks;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location ^~ /tasks/ {
        proxy_pass ${WEB_TARGET}/tasks/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /admin/tasks {
        proxy_pass ${WEB_TARGET}/admin/tasks;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location ^~ /admin/tasks/ {
        proxy_pass ${WEB_TARGET}/admin/tasks/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        proxy_pass ${LEGACY_WEB_TARGET};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

nginx -t
systemctl reload nginx
