"""Build same-pose style matrices from actual Blender beauty/matte outputs."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from style_presets import ROOT, load_package
from style_post import apply_post


def read(path, gray=False):
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE if gray else cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    if not gray:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image.astype(np.float32) / 255


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    matrix = Image.new("RGB", (1080, 640 + 34 + 203 + 34), "#20202b")
    raw_matrix = matrix.copy()
    report = []
    for row, aspect in enumerate(["portrait", "landscape"]):
        for col, prefix in enumerate(["gosari", "guanhaizi-graphic", "guanhaizi-neon"]):
            name = f"{prefix}-{aspect}-v1"
            recipe = load_package(ROOT / "packages" / (name + ".json"))
            cache = args.cache_root / (name + "-still")
            beauty = read(cache / "beauty" / "frame_0421beauty.png")
            actor = read(cache / "matte" / "frame_0421matte.png", True)
            face = read(cache / "face" / "frame_0421face.png", True)
            result = apply_post(beauty, actor, face, 0, recipe)
            assert result.shape == beauty.shape and np.isfinite(result).all()
            post_image = Image.fromarray((result * 255 + 0.5).astype(np.uint8))
            raw_image = Image.fromarray((beauty * 255 + 0.5).astype(np.uint8))
            post_image.save(args.output_dir / (name + ".png"))
            height = 640 if row == 0 else 203
            y = 0 if row == 0 else 674
            for sheet, image in [(matrix, post_image), (raw_matrix, raw_image)]:
                sheet.paste(image.resize((360, height)), (col * 360, y + 34))
                ImageDraw.Draw(sheet).text((col * 360 + 8, y + 10), name, fill="white")
            report.append(
                {
                    "id": name,
                    "dimensions": list(post_image.size),
                    "post_mean_absolute_delta": float(np.abs(result - beauty).mean()),
                    "camera_and_render_are_actual_blender": True,
                }
            )
    matrix.save(args.output_dir / "style-matrix.jpg", quality=96)
    raw_matrix.save(args.output_dir / "render-only-matrix.jpg", quality=96)
    (args.output_dir / "style-still-verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("STYLE_MATRIX_OK", args.output_dir)


if __name__ == "__main__":
    main()
