"""Create a labeled stage comparison and compare independent reopen renders."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    args = parser.parse_args()
    folder = args.study
    report = json.loads((folder / "stage-report.json").read_text(encoding="utf-8"))
    images = {}
    for name in [
        "baseline",
        "material-refined",
        "lighting-refined",
        "aisle-refined",
        "reopen-check",
    ]:
        image = Image.open(folder / (name + ".png")).convert("RGB")
        image.load()
        assert list(image.size) == report["resolution"], (name, image.size)
        images[name] = image
    a = np.asarray(images["aisle-refined"], dtype=np.float32)
    b = np.asarray(images["reopen-check"], dtype=np.float32)
    difference = float(np.abs(a - b).mean())
    qa = {
        "image_sizes_match": True,
        "independent_reopen_mae_8bit": difference,
        "reopen_tolerance_8bit": 2.0,
        "reopen_image_matches": difference <= 2,
        "source_sha256": {},
    }
    source = Path(report["source"])
    for path in [source, source.with_suffix(".pmx"), source.parent / "readme.txt"]:
        with path.open("rb") as stream:
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        qa["source_sha256"][path.name] = digest.hexdigest()
    if not qa["reopen_image_matches"]:
        raise RuntimeError("Independent reopen differs: " + str(difference))
    width, height = images["baseline"].size
    canvas = Image.new("RGB", (width * 2, height + 115), (15, 22, 36))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 30)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    for column, (name, label) in enumerate(
        [
            ("baseline", "原材质 · 同一主灯与相机"),
            ("lighting-refined", "Blender 适配 · 材质 / 间接光 / 烛光 / 薄体积"),
        ]
    ):
        x = column * width
        canvas.paste(images[name], (x, 64))
        draw.text((x + 22, 14), label, font=font, fill=(228, 235, 248))
    draw.text(
        (22, height + 78),
        "赫斯珀利德斯之馆-礼堂  |  模型 miHoYo / 改造 paierer  |  场景研究，尚非双人全曲成片",
        font=small,
        fill=(186, 199, 218),
    )
    destination = folder / "before-after.png"
    if destination.exists():
        raise FileExistsError(destination)
    canvas.save(destination)
    (folder / "verification.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
