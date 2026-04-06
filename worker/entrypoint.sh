#!/usr/bin/env bash
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PYTHONPATH="/app/aicut2602:/app/aicut2602/libs/cut_breakpoints/online_version:${PYTHONPATH:-}"

mkdir -p /data/smart-cut

if [ -d /app/website_aicut/tests/test_cujiian ]; then
  mkdir -p /app/website_aicut/tests/test_cujiian/output
  mkdir -p /app/website_aicut/tests/test_cujiian/fake_tos
fi

exec "$@"
