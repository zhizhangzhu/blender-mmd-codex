"""Measure a typography video's audio offset against the selected original BGM."""

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np


def decode(ffmpeg, path):
    result = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "4000",
            "-f",
            "f32le",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
    )
    audio = np.frombuffer(result.stdout, np.float32)
    # Energy envelopes retain correspondence when the vocal mix differs.
    n = len(audio) // 20
    envelope = np.sqrt(np.mean(audio[: n * 20].reshape(n, 20) ** 2, axis=1))
    return audio, envelope


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--typography", type=Path, required=True)
    parser.add_argument("--bgm", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _, video = decode(args.ffmpeg, args.typography)
    _, bgm = decode(args.ffmpeg, args.bgm)
    results = []
    for start, end in ((10, 30), (60, 80), (120, 140)):
        a = video[start * 200 : end * 200]
        scores = []
        for shift in range(-800, 801):
            begin = start * 200 + shift
            if begin < 0:
                continue
            b = bgm[begin : begin + len(a)]
            if len(b) != len(a):
                continue
            aa, bb = a - a.mean(), b - b.mean()
            score = float(
                np.dot(aa, bb) / max(1e-12, np.linalg.norm(aa) * np.linalg.norm(bb))
            )
            scores.append((score, shift))
        score, shift = max(scores)
        results.append(
            {
                "typography_interval": [start, end],
                "bgm_time_minus_typography_time_seconds": shift / 200,
                "envelope_correlation": score,
            }
        )
    offsets = [r["bgm_time_minus_typography_time_seconds"] for r in results]
    report = {
        "typography": str(args.typography),
        "bgm": str(args.bgm),
        "windows": results,
        "offset_seconds": float(np.median(offsets)),
        "offset_definition": "BGM time = typography time + offset; at a BGM time, read typography at BGM time minus offset",
        "agreement_seconds": max(offsets) - min(offsets),
        "passed": min(r["envelope_correlation"] for r in results) > 0.75
        and max(offsets) - min(offsets) <= 0.02,
        "limits": "Five-millisecond envelope grid, not per-word lyric alignment or choreography sync",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert report["passed"]


if __name__ == "__main__":
    main()
