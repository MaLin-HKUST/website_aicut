#!/bin/bash
set -euo pipefail

# Admin Merge Deployment Script
# Run this on the server after code is uploaded

REMOTE_HOST="14.103.249.104"
REMOTE_USER="malin"
REMOTE_DIR="/home/malin/website_aicut"
LOCAL_DIR="/Users/malin13/Documents/trae_projects/website_aicut"

echo "=== Admin Merge Deployment ==="

# Step 1: Push code to server
echo "[1/6] Pushing code to server..."
rsync -avz --exclude='.git' --exclude='node_modules' --exclude='.next' \
  "$LOCAL_DIR/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

# Step 2: SSH to server and deploy
echo "[2/6] Deploying on server..."
ssh "$REMOTE_USER@$REMOTE_HOST" << 'SSH_EOF'
  cd /home/malin/website_aicut

  # Step 3: Stop existing services
  echo "[3/6] Stopping existing services..."
  docker-compose down 2>/dev/null || true

  # Step 4: Build new images on server
  echo "[4/6] Building API image..."
  cd apps/api
  docker build -t website_aicut-api:sqlite-admin .
  cd ../..

  echo "[4/6] Building Web image..."
  cd apps/web
  docker build -t website_aicut-web:admin .
  cd ../..

  # Step 5: Initialize SQLite database
  echo "[5/6] Initializing SQLite database..."
  mkdir -p data
  python3 scripts/migrate_pg_to_sqlite.py --sqlite-path data/website_aicut.db \
    --admin-username admin --admin-password Malin123456

  # Step 6: Start services
  echo "[6/6] Starting services..."
  docker-compose up -d

  echo ""
  echo "=== Deployment Complete ==="
  docker-compose ps
SSH_EOF

echo ""
echo "Deployment complete! Please verify:"
echo "  - Admin login: http://14.103.249.104/admin"
echo "  - API health: http://14.103.249.104/api/health"
