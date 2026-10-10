#!/usr/bin/env bash
# Start only the backend on :8000.
set -euo pipefail
cd "$(dirname "$0")/../backend"
exec .venv/bin/uvicorn app.main:app --port 8000
