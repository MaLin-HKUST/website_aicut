#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="${VERSION:-0.0.3}"
OUTPUT_DIR="${OUTPUT_DIR:-/Volumes/XIAOMA-A-1T/docker_hub/WorkerGateway_and_Ascheduler}"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-${PROJECT_ROOT}/HarnessPlan/scheduler_AandW/artifacts}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
SHORT_SHA="$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD 2>/dev/null || echo nogit)"
IMAGE_TAG="${IMAGE_TAG:-a-scheduler:${VERSION}-dev}"
ARCHIVE_NAME="a-scheduler_${VERSION}_${TIMESTAMP}_${SHORT_SHA}.tar.gz"
ARCHIVE_PATH="${OUTPUT_DIR}/${ARCHIVE_NAME}"
BUILD_COMMAND="docker build -f apps/api/Dockerfile -t ${IMAGE_TAG} . && docker save ${IMAGE_TAG} | gzip > ${ARCHIVE_PATH}"

echo "=========================================="
echo "🔨 Building A-Scheduler Image"
echo "=========================================="
echo "Project root: ${PROJECT_ROOT}"
echo "Dockerfile: ${PROJECT_ROOT}/apps/api/Dockerfile"
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

docker build \
    -f apps/api/Dockerfile \
    -t "${IMAGE_TAG}" \
    .

docker save "${IMAGE_TAG}" | gzip > "${ARCHIVE_PATH}"

RECORD_PATH="$("${PROJECT_ROOT}/scripts/record_artifact.sh" \
    "${ARTIFACTS_DIR}" \
    "a-scheduler" \
    "${VERSION}" \
    "${TIMESTAMP}" \
    "${SHORT_SHA}" \
    "${ARCHIVE_PATH}" \
    "${BUILD_COMMAND}" \
    "not-run"
)"

echo "=========================================="
echo "✅ Build complete!"
echo "=========================================="
echo "Image: ${IMAGE_TAG}"
echo "Archive: ${ARCHIVE_PATH}"
echo "Record: ${RECORD_PATH}"
