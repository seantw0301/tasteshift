#!/usr/bin/env bash
# Fetch live Qloo tag candidates for the demo's concepts (needs `qloo setup --qloo` done first).
set -euo pipefail
cd "$(dirname "$0")/../backend"
exec .venv/bin/python -m app.resolve_tags
