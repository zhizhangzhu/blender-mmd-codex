"""Decode the finished MP4 audio using Blender's Audaspace/FFmpeg runtime."""

import argparse
import aud
import json
import numpy as np
import sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--video", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--seconds", type=float, default=20)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
sound = aud.Sound.file(str(args.video)).cache()
data = np.asarray(sound.data())
rate, channels = sound.specs
report = {
    "video": str(args.video),
    "sample_rate": rate,
    "channels": channels,
    "samples": int(data.shape[0]),
    "seconds": data.shape[0] / rate,
    "expected_seconds": args.seconds,
    "rms": float(np.sqrt(np.mean(data.astype(np.float64) ** 2))),
    "peak": float(np.max(np.abs(data))),
    "nonzero_samples": int(np.count_nonzero(data)),
}
report["passed"] = (
    report["rms"] > 0.0001
    and report["peak"] <= 1.0
    and report["nonzero_samples"] > 1000
    and abs(report["seconds"] - args.seconds) <= 0.2
)
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("x", encoding="utf-8") as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print("AUDIO_VERIFICATION", json.dumps(report), flush=True)
assert report["passed"], "Audio is missing, silent, or wrong length"
