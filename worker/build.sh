#!/bin/bash
set -e

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================="
echo "🔨 Building Smart Cut Worker Image"
echo "=========================================="
echo "Project root: ${PROJECT_ROOT}"
echo "Dockerfile: ${SCRIPT_DIR}/Dockerfile.combined"
echo ""

cd "${PROJECT_ROOT}"

# 检查基础镜像是否存在
if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "website_aicut-smart_cut_worker:latest"; then
    echo "⚠️  Base image 'website_aicut-smart_cut_worker:latest' not found"
    echo "   Loading from tar.gz file..."
    
    TAR_FILE="/Volumes/XIAOMA-A-1T/docker_hub/play_gound/website_aicut-smart_cut_worker_latest.tar.gz"
    if [ -f "$TAR_FILE" ]; then
        echo "   Loading: ${TAR_FILE}"
        docker load -i "$TAR_FILE"
    else
        echo "❌ Tar file not found: ${TAR_FILE}"
        echo "   Please ensure the base image is available"
        exit 1
    fi
fi

echo "✅ Base image verified"
echo ""
echo "🐳 Building image: smart-cut-worker-combined:latest"
echo "=========================================="

# 构建镜像
docker build \
    -f worker/Dockerfile.combined \
    -t smart-cut-worker-combined:latest \
    .

echo ""
echo "=========================================="
echo "✅ Build complete!"
echo "=========================================="
echo "Image: smart-cut-worker-combined:latest"
echo ""
echo "To run the container:"
echo "  docker run -e WORKER_ID=worker_01 -e DATABASE_URL=sqlite:///./test.db smart-cut-worker-combined:latest"
echo ""
echo "Or use docker-compose:"
echo "  docker-compose -f worker/docker-compose.test.yml up"
