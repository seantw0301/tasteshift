#!/usr/bin/env bash
# Unit tests, then hit a running backend (start it with scripts/dev.sh first).
set -euo pipefail
cd "$(dirname "$0")/.."
(cd backend && .venv/bin/python -m pytest -q)
API=${API:-http://localhost:8000}
for ev in evt_anime_music evt_family_fair; do
  curl -fsS -X POST "$API/api/evaluation/ablation" -H 'Content-Type: application/json' \
    -d "{\"event_id\":\"$ev\"}" | python3 -c 'import json,sys; r=json.load(sys.stdin); print(r["event_id"], "profit delta", r["delta"]["expected_profit"], "win rate", r["qloo_on_win_rate"])'
done
