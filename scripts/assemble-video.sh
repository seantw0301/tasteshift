#!/usr/bin/env bash
# Opening (30 s, voiced) + product demo (voiced) → final submission video, 1280x720.
#   scripts/assemble-video.sh [intro.mp4] [demo.mp4] [out.mp4]
set -euo pipefail
cd "$(dirname "$0")/.."
INTRO="${1:-artifacts/intro-voice.mp4}"; MAIN="${2:-artifacts/tasteshift-demo-audio.mp4}"; OUT="${3:-artifacts/tasteshift-final.mp4}"
FADE_AT=$(echo "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$INTRO") - 0.35" | bc -l)
ffmpeg -y -loglevel error -i "$INTRO" -i "$MAIN" -filter_complex "
  [0:v]scale=1280:720,fps=30,format=yuv420p,fade=t=out:st=${FADE_AT}:d=0.35[v0];
  [0:a]aresample=44100,aformat=channel_layouts=stereo[a0];
  [1:v]scale=1280:720,fps=30,format=yuv420p,fade=t=in:st=0:d=0.35[v1];
  [1:a]aresample=44100,aformat=channel_layouts=stereo[a1];
  [v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart "$OUT"
LEN=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
printf 'Wrote %s — %d:%02d (limit 3:00)\n' "$OUT" "$(echo "$LEN/60" | bc)" "$(echo "$LEN%60/1" | bc)"
