"""Build labelled equal-camera crops from our rendered stills for visual review."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

ROOT = Path("D:/codex/output/MMD-MME-Reference-Light-v1")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--revision", type=int, choices=(5, 6), default=6)
args = parser.parse_args()
OUT = ROOT / f"production-v{args.revision}"
OUT.mkdir(exist_ok=True)
try:
    FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
except OSError:
    FONT = ImageFont.load_default()


def panel(paths, labels, box, target):
    imgs = [Image.open(p).convert("RGB").crop(box) for p in paths]
    w, h = imgs[0].size
    result = Image.new("RGB", (w * len(imgs), h + 40), (30, 35, 46))
    draw = ImageDraw.Draw(result)
    for i, (im, label) in enumerate(zip(imgs, labels)):
        result.paste(im, (i * w, 40))
        draw.text((i * w + 12, 6), label, font=FONT, fill=(255, 255, 255))
    result.save(target)
    diff = ImageStat.Stat(ImageChops.difference(imgs[0], imgs[1]))
    return {"mean_absolute_display_rgb_difference": diff.mean, "pixel_crop": box}


stats = {}
if args.revision == 5:
    stats["aksiniya_before_to_v3"] = panel(
        [
            ROOT / "production-v3/before-double-4290.jpg",
            ROOT / "production-v3/clear-double-4290.jpg",
        ],
        ["Before", "Previous MME (v3)"],
        (130, 60, 465, 650),
        OUT / "aksiniya-before-v3-comparison.png",
    )
if (OUT / "ikhor-balanced-hero-4290.jpg").is_file():
    previous = 3 if args.revision == 5 else 5
    before_file = (
        "ikhor-clear-hero-4290.jpg" if previous == 3 else "ikhor-balanced-hero-4290.jpg"
    )
    stats[f"ikhor_v{previous}_to_v{args.revision}"] = panel(
        [
            ROOT / f"production-v{previous}" / before_file,
            OUT / "ikhor-balanced-hero-4290.jpg",
        ],
        [f"Previous (v{previous})", f"Lower brightness (v{args.revision})"],
        (210, 85, 760, 945),
        OUT / f"ikhor-v{previous}-v{args.revision}-comparison.png",
    )
(OUT / "comparison-notes.json").write_text(
    json.dumps(stats, indent=2), encoding="utf-8"
)
print(json.dumps(stats))
