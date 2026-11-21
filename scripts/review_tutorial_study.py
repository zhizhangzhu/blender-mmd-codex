"""Decode the four-second tutorial study and lay out unretouched comparisons."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from verify_video import stream_types


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    steps = [
        ("Baseline v2", "00-baseline-0421.png"),
        ("Light-aware toon", "01-linked-key-0421.png"),
        ("Selective rim", "02-selective-rim-0421.png"),
        ("Thin outlines", "03-thin-edges-0421.png"),
        ("Masked bloom", "04-masked-glow-0421.png"),
    ]
    sheet = Image.new("RGB", (270 * 5, 510), "#20202b")
    face_sheet = Image.new("RGB", (270 * 5, 350), "#20202b")
    for i, (label, filename) in enumerate(steps):
        with Image.open(args.study_dir / filename) as im:
            sheet.paste(im.convert("RGB").resize((270, 480)), (i * 270, 30))
            face = im.crop((265, 55, 730, 610)).convert("RGB").resize((270, 322))
            face_sheet.paste(face, (i * 270, 28))
        ImageDraw.Draw(sheet).text((i * 270 + 8, 10), label, fill="white")
        ImageDraw.Draw(face_sheet).text((i * 270 + 8, 10), label, fill="white")
    sheet.save(args.output_dir / "incremental-comparison.png")
    face_sheet.save(args.output_dir / "face-comparison.png")
    lamp_sheet = Image.new("RGB", (810, 510), "#20202b")
    for i, (label, name) in enumerate(
        [
            ("Key left / 170 W", "01-linked-key-0421.png"),
            ("Key right / 170 W", "01b-key-opposite-side-0421.png"),
            ("Key power 0 / ambient retained", "01c-key-zero-power-0421.png"),
        ]
    ):
        with Image.open(args.study_dir / name) as im:
            lamp_sheet.paste(im.convert("RGB").resize((270, 480)), (i * 270, 30))
        ImageDraw.Draw(lamp_sheet).text((i * 270 + 5, 10), label, fill="white")
    lamp_sheet.save(args.output_dir / "light-response.png")

    def pixels(filename):
        return np.asarray(
            Image.open(args.study_dir / filename).convert("RGB"), dtype=np.float32
        )

    key = pixels("01-linked-key-0421.png")
    opposite = pixels("01b-key-opposite-side-0421.png")
    zero = pixels("01c-key-zero-power-0421.png")
    roi = np.s_[60:500, 265:730]
    measurements = {
        "key_direction_head_roi_difference": float(
            np.abs(key[roi] - opposite[roi]).mean()
        ),
        "key_power_head_roi_difference": float(np.abs(key[roi] - zero[roi]).mean()),
        "glow_mean_image_difference": float(
            np.abs(
                pixels("03-thin-edges-0421.png") - pixels("04-masked-glow-0421.png")
            ).mean()
        ),
    }
    video = args.study_dir / "tutorial-preview-silent.mp4"
    cap = cv2.VideoCapture(str(video))
    assert cap.isOpened()
    fps, count = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = (
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    preview_sheet = Image.new("RGB", (270 * 4, 510 * 2), "#20202b")
    chosen = [0, 30, 60, 90, 119, 120, 180, 239]
    decoded, identical, run = 0, 0, 0
    previous = None
    lumas = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        lumas.append(float(frame.mean()))
        run = run + 1 if previous is not None and np.array_equal(previous, frame) else 0
        identical = max(identical, run)
        previous = frame
        if decoded in chosen:
            i = chosen.index(decoded)
            preview_sheet.paste(
                Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize(
                    (270, 480)
                ),
                ((i % 4) * 270, (i // 4) * 510),
            )
            ImageDraw.Draw(preview_sheet).text(
                ((i % 4) * 270 + 8, (i // 4) * 510 + 488),
                f"{decoded / fps:.3f}s / source {decoded + 421}",
                fill="white",
            )
        decoded += 1
    cap.release()
    preview_sheet.save(args.output_dir / "preview-contact-sheet.jpg", quality=95)
    report = {
        "video": str(video),
        "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "resolution": [width, height],
        "fps": fps,
        "decoded_frames": decoded,
        "declared_frames": count,
        "seconds": decoded / fps,
        "silent": "soun" not in stream_types(video),
        "minimum_mean_pixel_value": min(lumas),
        "maximum_identical_run": identical,
        "measurements": measurements,
    }
    report["passed"] = (
        decoded == count == 240
        and abs(fps - 60) < 0.001
        and [width, height] == [540, 960]
        and report["silent"]
        and min(lumas) > 5
        and identical < 30
        and measurements["key_direction_head_roi_difference"] > 0.1
        and measurements["key_power_head_roi_difference"] > 0.1
        and measurements["glow_mean_image_difference"] > 0
    )
    (args.output_dir / "study-verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("TUTORIAL_REVIEW", json.dumps(report), flush=True)
    assert report["passed"]


if __name__ == "__main__":
    main()
