#!/usr/bin/env bash
set -euo pipefail

echo "Fake TOS gate scaffold"
echo
echo "This gate is intentionally scaffolded only."
echo "Target Fake TOS root: /Volumes/XIAOMA-A-1T/docker_hub/FakeTos"
echo "Worker image tar: /Volumes/XIAOMA-A-1T/docker_hub/play_gound/website_aicut-smart_cut_worker_latest.tar.gz"
echo
echo "Planned flow:"
echo "1. prepare_fake_tos.sh <run_id>"
echo "2. load_worker_image.sh"
echo "3. start API + scheduler + worker with /fake-tos mount"
echo "4. execute Fake TOS integration cases from case_catalog.yaml"
echo "5. cleanup_fake_tos.sh <run_id>"
exit 2
