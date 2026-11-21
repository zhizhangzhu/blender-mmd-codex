"""Decode bounded three-axis tests and export face strips for honest visual QA."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    metadata = json.loads(
        (args.diagnostics / "diagnostic-records.json").read_text(encoding="utf-8")
    )
    records = metadata["rendered_records"]
    cases = ["head-turn", "key-orbit", "camera-orbit"]
    results = []
    for case in cases:
        clip = args.diagnostics / (case + ".mp4")
        capture = cv2.VideoCapture(str(clip))
        assert capture.isOpened()
        frames = []
        while True:
            ok, pixels = capture.read()
            if not ok:
                break
            frames.append(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB))
        fps = capture.get(cv2.CAP_PROP_FPS)
        capture.release()
        assert len(frames) == metadata["frames_per_case"] and fps == metadata["fps"]
        assert [frames[0].shape[1], frames[0].shape[0]] == metadata["resolution"]
        hashes = {hashlib.sha256(frame.tobytes()).hexdigest() for frame in frames}
        assert len(hashes) == len(frames), (
            case,
            "Unexpected duplicated diagnostic frames",
        )
        local = [r for r in records if r["case"] == case]
        max_error = max(
            axis["error"]
            for r in local
            for a in r["actors"].values()
            for axis in a["axes"].values()
        )
        assert max_error < 0.0001
        selected = [0, 4, 9, 14, 19, len(frames) - 1]
        canvas = Image.new("RGB", (6 * 240, 2 * 270), "#151b28")
        draw = ImageDraw.Draw(canvas)
        for row, actor in enumerate(sorted(local[0]["actors"])):
            for col, index in enumerate(selected):
                x0, y0, x1, y1 = local[index]["actors"][actor]["face_roi"]
                margin = 12
                roi = Image.fromarray(frames[index]).crop(
                    (
                        int(x0) - margin,
                        int(y0) - margin,
                        int(x1) + margin,
                        int(y1) + margin,
                    )
                )
                roi.thumbnail((228, 225), Image.Resampling.LANCZOS)
                canvas.paste(roi, (col * 240 + (240 - roi.width) // 2, row * 270 + 5))
                draw.text(
                    (col * 240 + 5, row * 270 + 235),
                    f"{actor} / frame {index:02d}",
                    fill="white",
                )
                draw.text(
                    (col * 240 + 5, row * 270 + 250),
                    f"angle {local[index]['angle_degrees']:.1f}",
                    fill="white",
                )
        canvas.save(args.output_dir / (case + "-face-strip.jpg"), quality=96)
        changes = [
            float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())
            for a, b in zip(frames, frames[1:])  # noqa: RUF007 -- system Python 3.9
        ]
        results.append(
            {
                "case": case,
                "sha256": hashlib.sha256(clip.read_bytes()).hexdigest(),
                "decoded_frames": len(frames),
                "fps": fps,
                "unique_frames": len(hashes),
                "max_axis_error": max_error,
                "adjacent_mean_rgb_deltas_255": changes,
                "visual_strip_indices": selected,
            }
        )
    report = {
        "passed": True,
        "cases": results,
        "neutral": metadata["neutral"],
        "limits": "Technical decode/axis checks and exported representative face strips; does not certify style or absence of all temporal artifacts.",
    }
    (args.output_dir / "diagnostics-verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("CHARACTER_DIAGNOSTICS_VERIFIED", flush=True)


if __name__ == "__main__":
    main()
