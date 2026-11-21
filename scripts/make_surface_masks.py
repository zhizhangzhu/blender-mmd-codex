"""Create explicitly heuristic control maps from the model's actual atlases.

These are art masks, not recovered game metallic/roughness/ILM maps. Material
gating in Blender excludes skin, eyes and ink even if atlas pixels are golden.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def smooth(lo, hi, value):
    x = np.clip((value - lo) / (hi - lo), 0, 1)
    return x * x * (3 - 2 * x)


def control_map(rgb):
    hsv = cv2.cvtColor(rgb.astype(np.float32), cv2.COLOR_RGB2HSV)
    h, s, v = hsv.transpose(2, 0, 1)
    gold = smooth(30, 39, h) * (1 - smooth(64, 78, h))
    gold *= smooth(0.08, 0.23, s) * smooth(0.15, 0.45, v)
    roughness = 0.82 * (1 - gold) + 0.25 * gold
    light_paint = smooth(
        0.72, 0.96, rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    )
    return np.stack([gold, roughness, light_paint], axis=2)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    inv = json.loads(args.inventory.read_text(encoding="utf-8"))
    mapping = []
    sheet = Image.new("RGB", (768, 3 * 280), "#20202b")
    names = [
        "NPC_Female_Body018_Snezhnaya_Aksinya01_01_Tex_Diffuse.png",
        "NPC_ItemDynamic_Aksinya01_FemaleBody018_Tex_Diffuse.png",
        "NPC_Female_Hair206_Tex_Diffuse.png",
    ]
    for index, name in enumerate(names):
        item = next(i for i in inv["images"] if i["name"] == name)
        with Image.open(item["extracted"]) as im:
            rgb = np.asarray(im.convert("RGB"), np.float32) / 255
        masks = control_map(rgb)
        target = args.output_dir / f"control-{index:02d}.png"
        Image.fromarray((masks * 255 + 0.5).astype(np.uint8)).save(target)
        source = Image.fromarray((rgb * 255 + 0.5).astype(np.uint8))
        metal = Image.fromarray((masks[..., 0] * 255 + 0.5).astype(np.uint8)).convert(
            "RGB"
        )
        highlight = Image.fromarray(
            (masks[..., 2] * 255 + 0.5).astype(np.uint8)
        ).convert("RGB")
        for col, (im, label) in enumerate(
            [
                (source, "source"),
                (metal, "R: gold candidates"),
                (highlight, "B: painted lights"),
            ]
        ):
            sheet.paste(im.resize((256, 256)), (col * 256, index * 280 + 24))
            ImageDraw.Draw(sheet).text(
                (col * 256 + 6, index * 280 + 6), f"{index:02d} {label}", fill="white"
            )
        mapping.append(
            {
                "source_image": name,
                "mask": str(target.resolve()),
                "gold_fraction": float((masks[..., 0] > 0.5).mean()),
            }
        )
    sheet.save(args.output_dir / "atlas-mask-review.jpg", quality=96)
    (args.output_dir / "mask-manifest.json").write_text(
        json.dumps(
            {
                "method": "color-derived art masks; not original PBR data",
                "channels": {
                    "R": "gold candidate",
                    "G": "roughness art control",
                    "B": "painted highlight control",
                },
                "maps": mapping,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("SURFACE_MASKS_OK", len(mapping))


if __name__ == "__main__":
    main()
