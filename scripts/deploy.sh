#!/usr/bin/env bash
# Build the static front end for a sub-path and copy front end + backend to the demo server.
# Reads DEPLOY_HOST, DEPLOY_PORT, DEPLOY_WEB_DIR, DEPLOY_API_DIR, DEPLOY_BASE_PATH from .env.
# Does not touch nginx or systemd; see docs/deploy.md for the one-time server setup.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a && . ./.env && set +a
: "${DEPLOY_HOST:?}" "${DEPLOY_WEB_DIR:?}" "${DEPLOY_API_DIR:?}"
BASE=${DEPLOY_BASE_PATH:-/tasteshift}
SSH="ssh -p ${DEPLOY_PORT:-22}"

(cd backend && .venv/bin/python -m pytest -q)
(cd frontend && rm -rf out && STATIC_EXPORT=1 NEXT_PUBLIC_BASE_PATH="$BASE" NEXT_PUBLIC_API_BASE="$BASE" npm run build)

rsync -az --delete -e "$SSH" frontend/out/ "$DEPLOY_HOST:$DEPLOY_WEB_DIR/"
rsync -az --delete -e "$SSH" --exclude .venv --exclude __pycache__ --exclude .pytest_cache backend/ "$DEPLOY_HOST:$DEPLOY_API_DIR/"
echo "Copied. Restart the API on the server: systemctl restart tasteshift-api"
