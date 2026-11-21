"""Require explicit decoded SDR review metadata, including after audio muxing."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from review_video_color import CONTRACT


def inspect(ffmpeg, video):
    result = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-i",
            str(video),
            "-vf",
            "showinfo",
            "-frames:v",
            "1",
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    lines = [
        line.strip() for line in result.stderr.splitlines() if "color_range:" in line
    ]
    assert lines, "No decoded color metadata"
    for line in lines:
        for expected in (
            "color_range:tv",
            "color_space:bt709",
            "color_primaries:bt709",
            "color_trc:iec61966-2-1",
        ):
            assert expected in line, (video, expected, line)
    return {
        "video": str(video),
        "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "decoded_color_metadata": lines,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, nargs="+", required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    reports = [inspect(args.ffmpeg, video) for video in args.video]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {"contract": CONTRACT, "videos": reports, "passed": True},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("REVIEW_COLOR_VERIFIED", flush=True)


if __name__ == "__main__":
    main()
