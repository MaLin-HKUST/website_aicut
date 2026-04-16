#!/bin/bash
set -e

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="${VERSION:-0.0.3}"
OUTPUT_DIR="${OUTPUT_DIR:-/Volumes/XIAOMA-A-1T/docker_hub/WorkerGateway_and_Ascheduler}"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-${PROJECT_ROOT}/HarnessPlan/scheduler_AandW/artifacts}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
SHORT_SHA="${SHORT_SHA:-$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD 2>/dev/null || echo nogit)}"
IMAGE_TAG="${IMAGE_TAG:-smart-cut-worker-gateway:${VERSION}-dev}"
ARCHIVE_NAME="worker-gateway_${VERSION}_${TIMESTAMP}_${SHORT_SHA}.tar.gz"
ARCHIVE_PATH="${OUTPUT_DIR}/${ARCHIVE_NAME}"
BUILD_COMMAND="docker build -f worker/Dockerfile -t ${IMAGE_TAG} . && docker save ${IMAGE_TAG} | gzip > ${ARCHIVE_PATH}"

echo "=========================================="
echo "🔨 Building Smart Cut Worker Gateway Image"
echo "=========================================="
echo "Project root: ${PROJECT_ROOT}"
echo "Dockerfile: ${SCRIPT_DIR}/Dockerfile"
echo "Output dir: ${OUTPUT_DIR}"
echo "Artifacts dir: ${ARTIFACTS_DIR}"
echo ""

cd "${PROJECT_ROOT}"

mkdir -p "${OUTPUT_DIR}"

if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "DRY_RUN=1"
    echo "Image: ${IMAGE_TAG}"
    echo "Archive: ${ARCHIVE_PATH}"
    exit 0
fi

echo "🐳 Building image: ${IMAGE_TAG}"
echo "=========================================="

# 构建镜像
docker build \
    -f worker/Dockerfile \
    -t "${IMAGE_TAG}" \
    .

echo ""
echo "📦 Exporting image archive: ${ARCHIVE_PATH}"
echo "=========================================="

docker save "${IMAGE_TAG}" | gzip > "${ARCHIVE_PATH}"

RECORD_PATH="$(bash "${PROJECT_ROOT}/scripts/record_artifact.sh" \
    "${ARTIFACTS_DIR}" \
    "worker-gateway" \
    "${VERSION}" \
    "${TIMESTAMP}" \
    "${SHORT_SHA}" \
    "${ARCHIVE_PATH}" \
    "${BUILD_COMMAND}" \
    "not-run"
)"

echo ""
echo "=========================================="
echo "✅ Build complete!"
echo "=========================================="
echo "Image: ${IMAGE_TAG}"
echo "Archive: ${ARCHIVE_PATH}"
echo "Record: ${RECORD_PATH}"
echo ""
echo "To run the container:"
echo "  docker run -e WORKER_ID=worker_01 -e DATABASE_URL=postgresql+psycopg2://scheduler:scheduler@host.docker.internal:55432/scheduler ${IMAGE_TAG}"
echo ""
echo "Or use docker-compose:"
echo "  docker-compose -f worker/docker-compose.test.yml up"
