"""Estimate a typography excerpt's origin in a longer typography video.

Matches foreground-bounds-normalized glyph images, not audio, lyrics or motion.
The score is visual similarity, not a probability. Inspect matched frames before
adopting an offset, especially when the song repeats the same typography.
"""

import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np


def sample(path, start, seconds, fps, executable):
    cap = cv2.VideoCapture(str(path))
    assert cap.isOpened()
    width, height = (
        cap.get(cv2.CAP_PROP_FRAME_WIDTH),
        cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
    )
    cap.release()
    scale = 256 / max(width, height)
    w, h = round(width * scale), round(height * scale)
    raw = subprocess.check_output(
        [
            str(executable),
            "-v",
            "error",
            "-ss",
            str(start),
            "-i",
            str(path),
            "-t",
            str(seconds),
            "-vf",
            f"fps={fps},scale={w}:{h}",
            "-pix_fmt",
            "gray",
            "-f",
            "rawvideo",
            "pipe:1",
        ]
    )
    return np.frombuffer(raw, np.uint8).reshape((-1, h, w))


def glyph_feature(image):
    ys, xs = np.nonzero(image > 40)
    if len(xs) < 8:
        return np.zeros(2304, np.float32)
    crop = image[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    vector = (
        cv2.resize(crop, (48, 48), interpolation=cv2.INTER_AREA)
        .astype(np.float32)
        .reshape(-1)
        / 255
    )
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--full", type=Path, required=True)
    p.add_argument("--excerpt", type=Path, required=True)
    p.add_argument("--ffmpeg", type=Path, required=True)
    p.add_argument("--search-start", type=float, required=True)
    p.add_argument("--search-end", type=float, required=True)
    p.add_argument("--excerpt-seconds", type=float, default=29.9)
    p.add_argument("--sample-fps", type=int, default=10)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    assert 0 <= args.search_start < args.search_end and args.sample_fps > 0
    a = sample(
        args.full,
        args.search_start,
        args.search_end - args.search_start + args.excerpt_seconds,
        args.sample_fps,
        args.ffmpeg,
    )
    b = sample(args.excerpt, 0, args.excerpt_seconds, args.sample_fps, args.ffmpeg)
    fa, fb = (
        np.array([glyph_feature(im) for im in a]),
        np.array([glyph_feature(im) for im in b]),
    )
    rows = []
    for tick in range(
        round(args.search_start * args.sample_fps),
        round(args.search_end * args.sample_fps) + 1,
    ):
        ids = np.arange(len(fb)) + tick - round(args.search_start * args.sample_fps)
        valid = (ids >= 0) & (ids < len(fa)) & (fb.sum(axis=1) > 0)
        if valid.sum() < 10:
            continue
        scores = np.sum(fa[ids[valid]] * fb[valid], axis=1)
        rows.append(
            {
                "offset_seconds": tick / args.sample_fps,
                "median_similarity": float(np.median(scores)),
                "mean_similarity": float(np.mean(scores)),
                "compared_nonblank_frames": int(valid.sum()),
            }
        )
    rows.sort(key=lambda r: r["median_similarity"], reverse=True)
    assert rows
    report = {
        "full": str(args.full),
        "excerpt": str(args.excerpt),
        "method": "normalized glyph cosine similarity",
        "resolution_seconds": 1 / args.sample_fps,
        "best_matches": rows[:10],
        "not_audio_or_lyric_sync": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print("TYPOGRAPHY_ALIGNMENT", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
