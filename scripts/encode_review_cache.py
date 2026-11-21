"""Encode native display-sRGB beauty caches with an explicit SDR color contract."""

import argparse
import subprocess
from pathlib import Path

import numpy as np
from composite_duet_official_captions import picture
from review_video_color import encoder_arguments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--start", type=int, default=4140)
    parser.add_argument("--frames", type=int, default=300)
    args = parser.parse_args()
    assert not args.output.exists() and args.frames > 0
    numbers = range(args.start, args.start + args.frames)
    paths = [args.cache / "beauty" / f"frame_{n:04d}beauty.png" for n in numbers]
    assert all(p.is_file() for p in paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    height, width = picture(paths[0]).shape[:2]
    process = subprocess.Popen(
        [
            str(args.ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-n",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-r",
            "60",
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "17",
            *encoder_arguments(),
            "-movflags",
            "+faststart",
            str(args.output),
        ],
        stdin=subprocess.PIPE,
    )
    try:
        for path in paths:
            rgb = np.rint(np.clip(picture(path), 0, 1) * 255).astype(np.uint8)
            process.stdin.write(rgb.tobytes())
        process.stdin.close()
        assert process.wait() == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    print("REVIEW_CACHE_ENCODED", args.output, flush=True)


if __name__ == "__main__":
    main()
