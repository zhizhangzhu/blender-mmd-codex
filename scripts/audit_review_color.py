"""Compare actual compositor RGB with explicitly decoded video color matrices."""

import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from composite_duet_official_captions import picture, render_frame
from PIL import Image
from stable_caption_layers import cue_at


def decode(ffmpeg, movie, frame, matrix):
    filters = f"select=eq(n\\,{frame}),scale=in_color_matrix={matrix}:in_range=tv:out_range=pc,format=rgb24"
    result = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(movie),
            "-vf",
            filters,
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
    )
    return np.frombuffer(result.stdout, np.uint8).reshape(1080, 1920, 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame", type=int)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    number = args.frame or (
        profile["render_start_frame"] + profile["render_frames"] - 1
    )
    index = number - profile["render_start_frame"]
    assert 0 <= index < profile["render_frames"]
    source_number = profile["source_start_frame"] + index
    source = cv2.VideoCapture(profile["source"])
    source.set(cv2.CAP_PROP_POS_FRAMES, source_number)
    ok, pixels = source.read()
    source.release()
    assert ok
    source_rgb = pixels[:, :, ::-1].astype(np.float32) / 255
    base = picture(args.cache / "beauty" / f"frame_{number:04d}beauty.png")
    actor = picture(args.cache / "actor" / f"frame_{number:04d}actor.png")
    reference, _, _ = render_frame(
        base, actor, source_rgb, profile, cue_at(profile, source_number)
    )
    reference = np.rint(np.clip(reference, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(reference).save(args.output_dir / f"reference-{number}.png")
    measurements = []
    for matrix in ("bt601", "bt709"):
        rgb = decode(args.ffmpeg, args.video, index, matrix)
        difference = rgb.astype(np.float32) - reference.astype(np.float32)
        measurements.append(
            {
                "forced_decode_matrix": matrix,
                "mean_absolute_rgb_error": float(abs(difference).mean()),
                "rgb_rmse": float(np.sqrt((difference * difference).mean())),
                "mean_rgb_bias": difference.mean((0, 1)).tolist(),
            }
        )
        Image.fromarray(rgb).save(args.output_dir / f"decoded-{matrix}.png")
    metadata = subprocess.run(
        [
            str(args.ffmpeg),
            "-hide_banner",
            "-i",
            str(args.video),
            "-vf",
            "showinfo",
            "-frames:v",
            "1",
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    lines = [s.strip() for s in metadata.stderr.splitlines() if "color_range:" in s]
    report = {
        "video": str(args.video),
        "reference_global_frame": number,
        "reference_typography_frame": source_number,
        "metadata": lines,
        "matrix_comparisons": measurements,
        "best_reconstruction_matrix": min(measurements, key=lambda r: r["rgb_rmse"])[
            "forced_decode_matrix"
        ],
        "scope": "This finds the encoding matrix from actual pixels; it does not reveal PotPlayer renderer settings, display ICC/HDR or GPU video enhancements",
    }
    (args.output_dir / "color-audit.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
