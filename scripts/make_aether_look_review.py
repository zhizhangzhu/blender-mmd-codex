"""Arrange faithfully rendered before/after portraits for material review."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portraits", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 30)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    before = Image.open(args.portraits / "before-portrait.png").convert("RGB")
    after = Image.open(args.portraits / "after-portrait.png").convert("RGB")
    assert before.size == after.size == (1000, 1000)
    sheet = Image.new("RGB", (1600, 900), "#171b27")
    draw = ImageDraw.Draw(sheet)
    for index, (im, title) in enumerate(
        [(before, "旧版"), (after, "空：肤色／分区材质／眼睛与黑线修订")]
    ):
        draw.text((index * 800 + 20, 15), title, font=font, fill="white")
        sheet.paste(im.resize((800, 800), Image.Resampling.LANCZOS), (index * 800, 60))
    draw.text(
        (20, 865),
        "同一姿态、诊断相机与背景；实际 Blender 渲染。静帧比较不代表全曲已验收。",
        font=small,
        fill="#c5cedd",
    )
    sheet.save(args.output_dir / "Aether_Before_After.jpg", quality=96)
    details = Image.new("RGB", (1200, 940), "#171b27")
    draw = ImageDraw.Draw(details)
    for row, (name, rect) in enumerate(
        [
            ("眼睛、肤色与脸部黑线", (330, 500, 655, 765)),
            ("金属、布料与皮革", (225, 735, 700, 995)),
        ]
    ):
        for col, im in enumerate([before, after]):
            crop = im.crop(rect)
            crop = crop.resize(
                (580, round(crop.height * 580 / crop.width)), Image.Resampling.LANCZOS
            )
            x, y = col * 600 + 10, row * 550 + 50
            details.paste(crop, (x, y))
            draw.text(
                (col * 600 + 10, row * 550 + 10),
                ("旧版：" if col == 0 else "修订：") + name,
                font=small,
                fill="white",
            )
    details.save(args.output_dir / "Aether_Material_Details.jpg", quality=96)


if __name__ == "__main__":
    main()
