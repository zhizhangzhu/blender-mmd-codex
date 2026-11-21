"""Inspect decoded frames around known render boundaries for visible jumps.

Boundary N is the last 1-based frame of the preceding segment. This is an
additional continuity check; it does not replace source-range manifests or a
full video decode. Contact sheets require visual inspection.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--boundaries", type=int, nargs="+", required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    cap = cv2.VideoCapture(str(args.video))
    assert cap.isOpened()
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    thumb_width = 320 if width > height else 270
    thumb_height = round(thumb_width * height / width)
    cell_height = thumb_height + 30
    sheet = Image.new(
        "RGB", (thumb_width * 5, cell_height * len(args.boundaries)), "#20202b"
    )
    draw = ImageDraw.Draw(sheet)
    results = []
    for row, boundary in enumerate(args.boundaries):
        images = []
        frames = list(range(boundary - 2, boundary + 3))
        for column, frame in enumerate(frames):
            assert frame >= 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame - 1)
            ok, bgr = cap.read()
            assert ok, f"Cannot decode frame {frame}"
            images.append(bgr.astype(np.float32))
            im = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            sheet.paste(
                im.resize((thumb_width, thumb_height)),
                (column * thumb_width, row * cell_height),
            )
            draw.text(
                (column * thumb_width + 8, row * cell_height + thumb_height + 8),
                f"Frame {frame}",
                fill="white",
            )
        deltas = [
            float(np.abs(images[i] - images[i - 1]).mean())
            for i in range(1, len(images))
        ]
        surrounding = float(np.median([deltas[0], deltas[1], deltas[3]]))
        results.append(
            {
                "boundary": boundary,
                "frames": frames,
                "mean_absolute_differences": deltas,
                "boundary_difference": deltas[2],
                "neighbor_median": surrounding,
                "no_large_jump": deltas[2] < max(10.0, surrounding * 3),
            }
        )
    cap.release()
    sheet.save(args.output_dir / "seam-contact-sheet.jpg", quality=95)
    report = {
        "video": str(args.video),
        "boundaries": results,
        "passed": all(r["no_large_jump"] for r in results),
    }
    (args.output_dir / "seam-verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("RENDER_SEAMS_VERIFIED", json.dumps(report), flush=True)
    assert report["passed"], "Review the render boundary contact sheet"


if __name__ == "__main__":
    main()
