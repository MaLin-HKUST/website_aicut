#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${1:-/app/website_aicut/tests/test_cujiian/manual_case_config.example.json}"

cd /app/website_aicut

python tests/test_cujiian/step01_analyze.py --config "$CONFIG_PATH"
python tests/test_cujiian/step02_preview.py --config "$CONFIG_PATH"
python tests/test_cujiian/step03_finalize_original.py --config "$CONFIG_PATH"
python tests/test_cujiian/step04_finalize_vertical.py --config "$CONFIG_PATH"
python tests/test_cujiian/step05_groundtruth.py --config "$CONFIG_PATH"

echo
echo "智能剪口播气口第一层测试已执行完成。"
echo "输出目录: /app/website_aicut/tests/test_cujiian/output"
