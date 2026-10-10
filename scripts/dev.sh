#!/usr/bin/env bash
# Start backend (:8000) and frontend (:3000). Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
(cd backend && .venv/bin/uvicorn app.main:app --port 8000 --reload) &
trap 'kill $!' EXIT
cd frontend && npm run dev
