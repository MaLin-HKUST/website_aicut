#!/bin/bash
set -e

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=========================================="
echo "🔨 Building Smart Cut Worker Gateway Image"
echo "=========================================="
echo "Project root: ${PROJECT_ROOT}"
echo "Dockerfile: ${SCRIPT_DIR}/Dockerfile"
echo ""

cd "${PROJECT_ROOT}"

IMAGE_TAG="smart-cut-worker-gateway:0.0.3-dev"

echo "🐳 Building image: ${IMAGE_TAG}"
echo "=========================================="

# 构建镜像
docker build \
    -f worker/Dockerfile \
    -t "${IMAGE_TAG}" \
    .

echo ""
echo "=========================================="
echo "✅ Build complete!"
echo "=========================================="
echo "Image: ${IMAGE_TAG}"
echo ""
echo "To run the container:"
echo "  docker run -e WORKER_ID=worker_01 -e DATABASE_URL=postgresql+psycopg2://scheduler:scheduler@host.docker.internal:55432/scheduler ${IMAGE_TAG}"
echo ""
echo "Or use docker-compose:"
echo "  docker-compose -f worker/docker-compose.test.yml up"
