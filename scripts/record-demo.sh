#!/usr/bin/env bash
# Record the full submission video against the live site (or BASE_URL) -> artifacts/tasteshift-final.mp4
# 30 s opening (problem / solution / full picture) + narrated product demo. See docs/demo-video.md.
set -euo pipefail
cd "$(dirname "$0")/.."
KOKORO_ENV="${KOKORO_ENV:-/Users/seantw/case2026/Claude/IntentChain/video/tts-env}"
PY="$KOKORO_ENV/bin/python"
mkdir -p artifacts
(cd demo && [ -d node_modules ] || npm install --silent)

# 1. opening: record silent animation, trim to 30.5 s, add voice
(cd demo && node record-intro.mjs)
ffmpeg -y -loglevel error -ss "$(cat artifacts/intro-lead.txt)" -i artifacts/intro-raw.webm -t 30.5 -an \
  -c:v libx264 -pix_fmt yuv420p -r 30 artifacts/intro-silent.mp4
"$PY" -I scripts/voice.py artifacts/intro-silent.mp4 artifacts/intro-voice.mp4 demo/intro/narration-intro.json

# 2. product demo: voice clips first (their lengths set the holds), then record, cut the agent wait, mix
"$PY" -I scripts/voice.py --clips demo/narration.json artifacts/audio >/dev/null
(cd demo && npx playwright test)
python3 scripts/mux-audio.py

# 3. opening + demo
scripts/assemble-video.sh
