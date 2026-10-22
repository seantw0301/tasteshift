#!/usr/bin/env bash
# One-time server setup: API virtualenv, systemd service, nginx proxy for <base>/api/.
# Run after scripts/deploy.sh has copied the backend. Reads DEPLOY_* and DEPLOY_ORIGIN from .env.
# Assumes a BaoTa-style nginx layout with a per-site extension directory (DEPLOY_NGINX_EXT_DIR).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a && . ./.env && set +a
: "${DEPLOY_HOST:?}" "${DEPLOY_API_DIR:?}" "${DEPLOY_ORIGIN:?}" "${DEPLOY_NGINX_EXT_DIR:?}"
BASE=${DEPLOY_BASE_PATH:-/tasteshift}
PORT=${DEPLOY_API_PORT:-8010}

ssh -p "${DEPLOY_PORT:-22}" "$DEPLOY_HOST" bash -s <<REMOTE
set -euo pipefail
cd "$DEPLOY_API_DIR"
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
cat > /etc/systemd/system/tasteshift-api.service <<UNIT
[Unit]
Description=TasteShift API
After=network.target

[Service]
User=www
Group=www
WorkingDirectory=$DEPLOY_API_DIR
Environment=CORS_ORIGINS=$DEPLOY_ORIGIN
ExecStart=$DEPLOY_API_DIR/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
cat > "$DEPLOY_NGINX_EXT_DIR/tasteshift.conf" <<'NGINX'
# TasteShift demo: static front end is served from the web root; proxy only its API.
location ^~ $BASE/api/ {
    proxy_pass http://127.0.0.1:$PORT/api/;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_read_timeout 180s;  # agent compare runs two LLM tool loops
}
NGINX
systemctl daemon-reload
systemctl enable --now tasteshift-api
sleep 2
systemctl is-active tasteshift-api
curl -fsS "http://127.0.0.1:$PORT/api/fixtures" >/dev/null && echo "API answers on :$PORT"
nginx -t && nginx -s reload && echo "nginx reloaded"
REMOTE
