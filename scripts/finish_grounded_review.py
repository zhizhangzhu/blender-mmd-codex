"""Composite, encode and verify a bounded 300-frame duet SDR review."""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FFMPEG = Path(
    "D:/codex/temp/blender-mmd-video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
)
BLENDER = Path("E:/tools/Blender Foundation/Blender 5.2/blender.exe")


def run(script, *arguments, blender=False):
    prefix = (
        [
            str(BLENDER),
            "--background",
            "--disable-autoexec",
            "--python-exit-code",
            "1",
            "--python",
        ]
        if blender
        else [sys.executable]
    )
    command = prefix + [str(ROOT / "scripts" / script)]
    if blender:
        command += ["--"]
    subprocess.run(command + [str(a) for a in arguments], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--native-sample", default="lighting-sample-5s-v2")
    parser.add_argument("--caption-dir", default="captions-5s-v2")
    parser.add_argument("--review-name", default="Grounded")
    parser.add_argument("--wait-seconds", type=int, default=14400)
    args = parser.parse_args()
    deadline = time.monotonic() + args.wait_seconds
    while not (args.root / args.native_sample / "sample-report.json").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("Native sample exceeded the configured wait deadline")
        time.sleep(10)
    dest = args.root / args.caption_dir
    profile = ROOT / "presets/typography/duet-blue-gold-wedding-v1.json"
    run(
        "composite_duet_official_captions.py",
        "--cache-dir",
        args.cache,
        "--profile",
        profile,
        "--output-dir",
        dest,
        "--ffmpeg",
        FFMPEG,
    )
    assert args.review_name.replace("_", "").isalnum(), "Use a short filename label"
    bare = dest / (args.review_name + "_NoCaptions_Picture.mp4")
    run(
        "encode_review_cache.py",
        "--cache",
        args.cache,
        "--output",
        bare,
        "--ffmpeg",
        FFMPEG,
    )
    movies = []
    for picture, name, qa in [
        (
            dest / "Duet_Captions_Picture.mp4",
            f"Franken_Duet_5s_{args.review_name}_Wedding_REVIEW.mp4",
            "video-qa",
        ),
        (bare, f"Franken_Duet_5s_{args.review_name}_NoCaptions.mp4", "bare-video-qa"),
    ]:
        movie = dest / name
        run(
            "mux_production_audio.py",
            "--video",
            picture,
            "--project",
            ROOT / "presets/projects/franken-duet-full-v1.json",
            "--output",
            movie,
            "--audio-start",
            4139 / 60,
            "--seconds",
            5,
            "--gain",
            0.87,
            "--ffmpeg",
            FFMPEG,
        )
        run(
            "verify_video.py",
            "--video",
            movie,
            "--output-dir",
            dest / qa,
            "--width",
            1920,
            "--height",
            1080,
            "--fps",
            60,
            "--seconds",
            5,
        )
        run(
            "verify_audio_blender.py",
            "--video",
            movie,
            "--output",
            dest / (qa + "-audio.json"),
            "--seconds",
            5,
            blender=True,
        )
        movies.append(movie)
    run(
        "verify_review_color.py",
        "--video",
        dest / "Duet_Captions_Picture.mp4",
        bare,
        *movies,
        "--ffmpeg",
        FFMPEG,
        "--output",
        dest / "color-verification.json",
    )
    run(
        "audit_review_color.py",
        "--video",
        movies[0],
        "--cache",
        args.cache,
        "--profile",
        profile,
        "--ffmpeg",
        FFMPEG,
        "--output-dir",
        dest / "color-roundtrip",
        "--frame",
        4250,
    )
    run(
        "verify_render_seams.py",
        "--video",
        movies[0],
        "--output-dir",
        dest / "seam-qa",
        "--boundaries",
        150,
    )
    print("BOUNDED_REVIEW_TECHNICAL_QA_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
