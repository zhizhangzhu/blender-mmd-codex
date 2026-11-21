"""Create an unretouched same-pose look comparison and a scene QA contact sheet."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--before", type=Path, required=True)
    p.add_argument("--after", type=Path, required=True)
    p.add_argument("--qa-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    sheet = Image.new("RGB", (1080, 1010), "#20202b")
    draw = ImageDraw.Draw(sheet)
    for index, (label, path) in enumerate(
        [("BEFORE - v1", args.before), ("AFTER - v2", args.after)]
    ):
        with Image.open(path) as im:
            sheet.paste(
                im.convert("RGB").resize((540, 960), Image.Resampling.LANCZOS),
                (index * 540, 30),
            )
        draw.text((index * 540 + 16, 10), label, fill="white")
    draw.text(
        (16, 993),
        "Same pose, camera and animation. Frame 421 / 7.0 s. No image color correction.",
        fill="white",
    )
    sheet.save(args.output_dir / "before-after.png")
    faces = Image.new("RGB", (1080, 700), "#20202b")
    draw = ImageDraw.Draw(faces)
    for index, (label, path) in enumerate(
        [("BEFORE - v1", args.before), ("AFTER - v2", args.after)]
    ):
        with Image.open(path) as im:
            # Identical pixel crop of this model-specific diagnostic pose.
            crop = im.crop((265, 55, 730, 610)).convert("RGB")
            faces.paste(ImageOps.contain(crop, (540, 650)), (index * 540, 35))
        draw.text((index * 540 + 16, 10), label, fill="white")
    faces.save(args.output_dir / "face-before-after.png")
    paths = sorted(args.qa_dir.glob("frame-*.png"))
    contact = Image.new("RGB", (270 * 5, 510 * 4), "#20202b")
    draw = ImageDraw.Draw(contact)
    for index, path in enumerate(paths[:20]):
        x, y = (index % 5) * 270, (index // 5) * 510
        with Image.open(path) as im:
            contact.paste(im.convert("RGB").resize((270, 480)), (x, y))
        draw.text((x + 8, y + 488), path.stem, fill="white")
    contact.save(args.output_dir / "scene-contact-sheet.jpg", quality=95)
    print("LOOK_COMPARISON_OK", args.output_dir)


if __name__ == "__main__":
    main()
