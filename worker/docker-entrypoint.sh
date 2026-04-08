#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Smart Cut Worker Starting..."
echo "=========================================="
echo "WORKER_ID: ${WORKER_ID:-not_set}"
echo "WORKER_NAME: ${WORKER_NAME:-not_set}"
echo "PYTHONPATH: ${PYTHONPATH}"
echo "WORKER_DATA_BASE: ${WORKER_DATA_BASE:-/data/smart-cut}"
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
mkdir -p "${WORKER_DATA_BASE:-/data/smart-cut}"
echo "✅ Work directory created: ${WORKER_DATA_BASE:-/data/smart-cut}"

# 验证算法脚本存在
if [ -f "/app/aicut2602/libs/cut_breakpoints/src/run_raw_cut.py" ]; then
    echo "✅ Algorithm script found: /app/aicut2602/libs/cut_breakpoints/src/run_raw_cut.py"
else
    echo "⚠️  Warning: Algorithm script not found at /app/aicut2602/libs/cut_breakpoints/src/run_raw_cut.py"
fi

echo ""
echo "🎯 Starting Worker..."
echo "=========================================="

# 启动Worker
exec python -m worker.core
