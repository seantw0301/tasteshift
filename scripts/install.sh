#!/usr/bin/env bash
# One-shot install: Python venv + backend deps, frontend deps.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv backend/.venv
backend/.venv/bin/pip install -q -r backend/requirements.txt
(cd frontend && npm install)
