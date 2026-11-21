"""Compare true same-camera renders and measure actor/background brightness."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--actor-mask", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    before = Image.open(args.before).convert("RGB")
    after = Image.open(args.after).convert("RGB")
    mask = np.asarray(Image.open(args.actor_mask).convert("L")) / 255
    assert before.size == after.size == (mask.shape[1], mask.shape[0])
    sheet = Image.new("RGB", (1600, 510), "#161c28")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 26)
    for i, (im, title) in enumerate(
        [
            (before, "旧版：上一轮 20 秒样片的着色"),
            (after, "改版：窗光／人物与场景分开调色"),
        ]
    ):
        draw.text((i * 800 + 15, 12), title, font=font, fill="white")
        sheet.paste(im.resize((800, 450), Image.Resampling.LANCZOS), (i * 800, 60))
    sheet.save(args.output_dir / "Lighting_Before_After.jpg", quality=96)
    regions = {
        "whole_frame": np.ones(mask.shape, dtype=bool),
        "actor_interior": mask > 0.98,
        "background": mask < 0.02,
    }
    report = {}
    for label, im in [("before", before), ("after", after)]:
        pixels = np.asarray(im, dtype=float)
        y = pixels @ np.array([0.2126, 0.7152, 0.0722])
        report[label] = {
            name: {
                "mean_display_luma": float(y[region].mean()),
                "p10_p50_p90": np.percentile(y[region], [10, 50, 90]).tolist(),
                "fraction_channel_at_254": float((pixels.max(2)[region] >= 254).mean()),
            }
            for name, region in regions.items()
        }
    report["note"] = (
        "Display-referred brightness comparison, not a perceptual-quality score; AOV mask visually checked"
    )
    (args.output_dir / "brightness-comparison.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
