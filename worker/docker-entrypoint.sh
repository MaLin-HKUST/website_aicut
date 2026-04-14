#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Smart Cut Worker Gateway Starting..."
echo "=========================================="
echo "WORKER_ID: ${WORKER_ID:-not_set}"
echo "WORKER_NAME: ${WORKER_NAME:-not_set}"
echo "PYTHONPATH: ${PYTHONPATH}"
echo "WORKER_DATA_BASE: ${WORKER_DATA_BASE:-/data/worker-jobs}"
echo ""

# 检查必要的环境变量
if [ -z "$WORKER_ID" ]; then
    echo "❌ Error: WORKER_ID environment variable is required"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL environment variable is required"
    exit 1
fi

# 创建工作目录
mkdir -p "${WORKER_DATA_BASE:-/data/worker-jobs}"
echo "✅ Work directory created: ${WORKER_DATA_BASE:-/data/worker-jobs}"

echo "ℹ️  Gateway mode: Smart-Cut algorithm image runs separately"

echo ""
echo "🎯 Starting Worker Gateway..."
echo "=========================================="

# 启动 Worker Gateway
exec python -m worker.main
