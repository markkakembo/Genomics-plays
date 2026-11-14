#!/usr/bin/env bash
# Offline end-to-end dry run on the bundled synthetic sample.
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python run.py --raw_materials examples/sample_project/raw_materials --out outputs/sample_mock_run --provider mock --cutoff 2024-11 "$@"
