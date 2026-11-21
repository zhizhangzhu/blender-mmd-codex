"""Extract targeted full frames and consecutive bursts from a supplied reference.

Research copies stay in the caller's temporary directory, not the public gallery.
No author camera, aperture, shutter or renderer is recovered by this process.
"""

import argparse
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    cap = cv2.VideoCapture(str(args.video))
    assert cap.isOpened()
    fps = cap.get(cv2.CAP_PROP_FPS)
    cases = [
        ("floor-shadow", 27.2),
        ("portrait-dof", 42.733),
        ("fast-hand", 73.816),
        ("foreground-dof", 94.533),
        ("wide", 120.433),
    ]
    records = []
    for label, seconds in cases:
        center = round(seconds * fps)
        sheet = Image.new("RGB", (1440, 3 * 232), "#16151e")
        draw = ImageDraw.Draw(sheet)
        case = []
        for j, index in enumerate(range(center - 6, center + 6)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            assert ok
            rgb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if j == 6:
                rgb.save(args.output_dir / f"{label}-{center}.png")
            x, y = (j % 4) * 360, (j // 4) * 232
            sheet.paste(rgb.resize((360, 202)), (x, y))
            draw.text(
                (x + 6, y + 208), f"{index / fps:.4f}s | frame {index}", fill="white"
            )
            case.append(index)
        sheet.save(args.output_dir / f"{label}-burst.jpg", quality=94)
        records.append({"case": label, "seconds": seconds, "frames_zero_based": case})
    cap.release()
    (args.output_dir / "targeted-observation.json").write_text(
        json.dumps(
            {"source": str(args.video), "fps": fps, "cases": records},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
