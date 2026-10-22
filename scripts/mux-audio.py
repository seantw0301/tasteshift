#!/usr/bin/env python3
"""Cut the agent wait out of the recorded demo and mix narration at the recorded timestamps.

Reads artifacts/tasteshift-demo.webm and artifacts/audio/timeline.json ([{"key", "t"}]; __cut_start/__cut_end mark the wait).
Writes artifacts/tasteshift-demo-audio.mp4.
"""
import json
import subprocess
from pathlib import Path

A = Path(__file__).resolve().parent.parent / "artifacts"
tl = json.loads((A / "audio" / "timeline.json").read_text())
marks = {e["key"]: e["t"] for e in tl if e["key"].startswith("__")}
cs, ce = marks.get("__cut_start"), marks.get("__cut_end")
cut = (ce - cs) if cs is not None and ce is not None else 0.0
lines = [dict(e, t=e["t"] - cut if cut and e["t"] >= ce else e["t"]) for e in tl if not e["key"].startswith("__")]

cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(A / "tasteshift-demo.webm")]
for e in lines:
    cmd += ["-i", str(A / "audio" / f"{e['key']}.wav")]
if cut:
    video = (f"[0:v]trim=0:{cs},setpts=PTS-STARTPTS[v0];[0:v]trim=start={ce},setpts=PTS-STARTPTS[v1];"
             f"[v0][v1]concat=n=2:v=1:a=0,fps=30,format=yuv420p[vout]")
else:
    video = "[0:v]fps=30,format=yuv420p[vout]"
parts = [f"[{i + 1}:a]aresample=44100,adelay={int(e['t'] * 1000)}:all=1[a{i}]" for i, e in enumerate(lines)]
mix = "".join(f"[a{i}]" for i in range(len(lines))) + \
      f"amix=inputs={len(lines)}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,aformat=channel_layouts=stereo[aout]"
cmd += ["-filter_complex", ";".join([video] + parts + [mix]), "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
        str(A / "tasteshift-demo-audio.mp4")]
subprocess.run(cmd, check=True)
print(f"wrote {A / 'tasteshift-demo-audio.mp4'} (cut {cut:.1f}s of agent wait)")
