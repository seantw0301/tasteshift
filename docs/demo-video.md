# Demo video

Final video = **30 s opening** (problem → solution → full picture) + **narrated product demo** on the live site, ≤ 3:00.

Opening rules (first-30-seconds guide, also in the Obsidian global vault: `global/Video/Demo 影片前 30 秒（三段原則）`):

- 10 / 10 / 10 s, one message per scene
- Scene title = first spoken sentence
- Readable with the sound off
- Same data as the product: every number and name on screen comes from live Qloo calls or the evaluation in [agent-evaluation.md](agent-evaluation.md)
- Colors: green = good, red = problem, teal = Qloo

## Opening (30 s)

| Scene | Time | Title (= first spoken sentence) | Shows |
|---|---|---|---|
| Problem | 0–10 s | You stock your booth before the crowd arrives — and you guess. | Anime Music Festival, Taipei, 8,000 people, NT$20,000 → 12-SKU catalog → "A guess" (red). "Who is actually coming?" |
| Solution | 10–20 s | Ask Qloo who the crowd is. Let the agent stock for them. | Qloo films, age skew (35–44 +0.60, 24 and younger −0.19), taste tags (Cafe, Fashion, Afternoon Tea Set) → agent → cited decisions. 17 of 20 runs, mean +NT$552 (simulated demand). |
| Full picture | 20–30 s | Who's coming, what they like, what to stock. | ASK → RESOLVE (find_tags) → RECOMMEND (recommend, rank) → **PROFILE (demographics, entity tags)** → DECIDE (agent) → OPTIMIZE (TasteShift). |

## Product demo

Captions and narration: [demo/narration.json](../demo/narration.json). Beats: culture comparison → Qloo evidence → Qloo on vs off → decision audit → plans and rain scenario → live ops restock → agent request → (agent wait cut, captioned "≈ 1 minute later") → tool calls → per-SKU Qloo citations → without-Qloo arm → profit comparison → close.

The agent results in the demo are whatever the live run returns; they vary between runs.

## Files

| File | Purpose |
|---|---|
| `demo/intro/intro.html` | Self-animating 30 s opening (`?t=15` jumps for preview) |
| `demo/intro/narration-intro.json` | Opening cue sheet |
| `demo/record-intro.mjs` | Records the opening |
| `demo/demo-recording.spec.ts` | Records the product demo with captions and a timeline |
| `scripts/voice.py` | Kokoro neural TTS (local, open model) → clips or a voiced video |
| `scripts/mux-audio.py` | Cuts the agent wait, places narration at recorded timestamps |
| `scripts/assemble-video.sh` | Opening + demo → `artifacts/tasteshift-final.mp4` |
| `scripts/record-demo.sh` | Runs all of the above |

## Build

Needs ffmpeg, Node, and a Python env with `kokoro-onnx` + `soundfile` plus the model files in `$KOKORO_ENV/model`.

```bash
export KOKORO_ENV=/path/to/tts-env
scripts/record-demo.sh            # → artifacts/tasteshift-final.mp4
BASE_URL=http://localhost:3000/ scripts/record-demo.sh   # against a local stack
```
