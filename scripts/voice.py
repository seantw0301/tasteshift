#!/usr/bin/env python3
"""Neural (Kokoro, open model, runs locally) narration for a cue sheet, mixed onto a video.

  $KOKORO_ENV/bin/python scripts/voice.py <video-in> <video-out> <cuesheet.json>
  $KOKORO_ENV/bin/python scripts/voice.py --clips <cuesheet.json> <outdir>     # only write clips + lengths

Cue sheet: {"voice": "af_heart", "speed": 1.0, "cues": [{"at": seconds, "text": "..."}]}
A line that would run into the next cue is re-synthesized slightly faster (max 1.3x).
KOKORO_ENV must contain bin/python (with kokoro_onnx, soundfile) and model/{kokoro-v1.0.onnx,voices-v1.0.bin}.
See docs/demo-video.md.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro

ENV = Path(os.environ.get("KOKORO_ENV", "/Users/seantw/case2026/Claude/IntentChain/video/tts-env"))
GAP, MAX_SPEED = 0.35, 1.3
_k = None


def speakable(t: str) -> str:
    t = t.replace("Qloo", "Clue")  # brand is pronounced "clue"
    return t.replace("→", "to").replace("×", " times").replace("·", ",").replace("—", ",").replace("“", "").replace("”", "")


def tts(text: str, voice: str, speed: float, out: Path) -> float:
    global _k
    if _k is None:
        _k = Kokoro(str(ENV / "model/kokoro-v1.0.onnx"), str(ENV / "model/voices-v1.0.bin"))
    samples, rate = _k.create(speakable(text), voice=voice, speed=speed, lang="en-us")
    sf.write(str(out), samples, rate)
    return len(samples) / rate


def fit(cues, total, voice, base_speed, outdir: Path):
    clips = []
    for i, c in enumerate(cues):
        slot = (cues[i + 1]["at"] if i + 1 < len(cues) else total) - c["at"] - GAP
        f = outdir / f"{i:02d}.wav"
        speed, length = base_speed, tts(c["text"], voice, base_speed, f)
        for _ in range(3):
            if length <= slot or speed >= MAX_SPEED:
                break
            speed = min(MAX_SPEED, speed * length / slot + 0.03)
            length = tts(c["text"], voice, speed, f)
        flag = f"  OVERRUNS by {length - slot:.1f}s" if length > slot else ""
        print(f"{c['at']:6.1f}s  {length:4.1f}s of {slot:4.1f}s  speed {speed:.2f}{flag}", flush=True)
        clips.append({"at": c["at"], "file": f, "length": length})
    return clips


def probe(path: str) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True, check=True).stdout)


if sys.argv[1] == "--clips":
    sheet = json.loads(Path(sys.argv[2]).read_text())
    out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    res = {}
    for key, cue in sheet.items():
        res[key] = round(tts(cue["text"], cue.get("voice", "af_heart"), cue.get("speed", 1.0), out / f"{key}.wav"), 2)
    (out / "durations.json").write_text(json.dumps(res, indent=1))
    print(res)
    sys.exit()

vin, vout, sheet_path = sys.argv[1:4]
sheet = json.loads(Path(sheet_path).read_text())
total = probe(vin)
tmp = Path(tempfile.mkdtemp())
clips = fit(sheet["cues"], total, sheet.get("voice", "af_heart"), sheet.get("speed", 1.0), tmp)
cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", vin]
for c in clips:
    cmd += ["-i", str(c["file"])]
mix = ";".join(f"[{i + 1}:a]aresample=44100,adelay={int(c['at'] * 1000)}:all=1[a{i}]" for i, c in enumerate(clips))
mix += ";" + "".join(f"[a{i}]" for i in range(len(clips))) + \
       f"amix=inputs={len(clips)}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,aformat=channel_layouts=stereo[a]"
cmd += ["-filter_complex", mix, "-map", "0:v", "-map", "[a]", "-c:v", "copy" if vin.endswith(".mp4") else "libx264",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", str(total), "-movflags", "+faststart", vout]
subprocess.run(cmd, check=True)
print("wrote", vout)
