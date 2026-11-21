"""Sample multi-second reference sequences for temporal art-direction review.

Outputs are private research copies. They do not recover author scene settings.
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
    capture = cv2.VideoCapture(str(args.video))
    assert capture.isOpened()
    fps = capture.get(cv2.CAP_PROP_FPS)
    cases = [
        ("stage-entry", 15, 21),
        ("light-pool", 22, 28),
        ("portrait", 39, 45),
        ("duet-focus", 90, 96),
    ]
    records = []
    for name, start, end in cases:
        sheet = Image.new("RGB", (1440, 6 * 228), "#171823")
        draw = ImageDraw.Draw(sheet)
        sequence = []
        for n in range(24):
            seconds = start + n * (end - start) / 24
            frame = round(seconds * fps)
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, pixels = capture.read()
            assert ok
            image = Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB))
            x, y = (n % 4) * 360, (n // 4) * 228
            sheet.paste(image.resize((360, 202)), (x, y))
            draw.text((x + 5, y + 207), f"{seconds:.3f}s / f{frame}", fill="white")
            if n in (0, 6, 12, 18):
                image.save(args.output_dir / f"{name}-{seconds:.3f}.png")
            sequence.append({"frame": frame, "seconds": seconds})
        sheet.save(args.output_dir / f"{name}-sequence.jpg", quality=95)
        records.append(
            {
                "name": name,
                "interval": [start, end],
                "sample_fps": 4,
                "samples": sequence,
            }
        )
    capture.release()
    (args.output_dir / "sequence-observation.json").write_text(
        json.dumps(
            {"source": str(args.video), "sampling_only": True, "cases": records},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
