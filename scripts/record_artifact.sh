#!/bin/bash
set -euo pipefail

if [ "$#" -lt 8 ]; then
  echo "Usage: $0 <artifacts_dir> <component> <version> <timestamp> <short_sha> <archive_path> <build_command> <verification_result>"
  exit 1
fi

ARTIFACTS_DIR="$1"
COMPONENT="$2"
VERSION="$3"
TIMESTAMP="$4"
SHORT_SHA="$5"
ARCHIVE_PATH="$6"
BUILD_COMMAND="$7"
VERIFICATION_RESULT="$8"

mkdir -p "$ARTIFACTS_DIR"

RECORD_PATH="${ARTIFACTS_DIR}/${COMPONENT}_${VERSION}_${TIMESTAMP}_${SHORT_SHA}.md"

cat > "$RECORD_PATH" <<EOF
# Artifact Record

- component: ${COMPONENT}
- version: ${VERSION}
- timestamp: ${TIMESTAMP}
- commit_sha: ${SHORT_SHA}
- archive_path: ${ARCHIVE_PATH}
- build_command: \`${BUILD_COMMAND}\`
- verification_result: ${VERIFICATION_RESULT}
EOF

echo "$RECORD_PATH"
