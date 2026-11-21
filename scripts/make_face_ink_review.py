"""Build aspect-preserving crops from reference and actual A/B renders."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--previous-cache", type=Path, required=True)
    p.add_argument("--reference-root", type=Path, required=True)
    args = p.parse_args()
    dest = args.output_root / "review"
    dest.mkdir(exist_ok=False)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 21)
    stills = args.output_root / "stills-v2"
    canvas = Image.new("RGB", (1260, 1420), (25, 25, 32))
    draw = ImageDraw.Draw(canvas)
    stats = []
    for row, frame in enumerate([661, 781, 900]):
        matte = np.array(
            Image.open(
                args.previous_cache / "face" / f"frame_{frame:04d}face.png"
            ).convert("L")
        )
        y, x = np.where(matte > 20)
        if len(x) == 0:
            raise ValueError("Face matte is empty")
        box = (
            max(0, int(x.min()) - 24),
            max(0, int(y.min()) - 28),
            min(matte.shape[1], int(x.max()) + 25),
            min(matte.shape[0], int(y.max()) + 29),
        )
        images = {}
        for col, (mode, title) in enumerate(
            [
                ("previous", "原版：暖色细线"),
                ("face-black", "新版：清晰脸线 + 五官内线"),
                ("face-black-wide", "粗线对照：未选用"),
            ]
        ):
            im = Image.open(stills / mode / f"frame-{frame:04d}.png").convert("RGB")
            images[mode] = np.array(im).astype(np.int16)
            crop = ImageOps.contain(im.crop(box), (400, 420), Image.Resampling.LANCZOS)
            canvas.paste(
                crop,
                (
                    col * 420 + (420 - crop.width) // 2,
                    row * 470 + 44 + (420 - crop.height) // 2,
                ),
            )
            draw.text(
                (col * 420 + 12, row * 470 + 8),
                f"{title} | {frame}",
                font=font,
                fill="white",
            )
        ablation = np.array(
            Image.open(
                stills / "face-features-only" / f"frame-{frame:04d}.png"
            ).convert("RGB")
        ).astype(np.int16)
        selected = images["face-black"]
        edge = np.abs(selected - ablation).max(axis=2) > 5
        rgb = selected[edge]
        previous_delta = np.abs(selected - images["previous"]).max(axis=2) > 5
        stats.append(
            {
                "frame": frame,
                "face_crop_xyxy": box,
                "face_shell_ablation_changed_pixels_over_5": int(edge.sum()),
                "face_shell_ablation_changed_pixels_min_rgb": rgb.min(axis=0).tolist()
                if len(rgb)
                else None,
                "changed_pixels_from_previous_over_5": int(previous_delta.sum()),
                "edge_cryptomatte_not_used_for_measurement": True,
            }
        )
        if not edge.any():
            raise ValueError("Face-shell ablation produced no visible difference")
    canvas.save(dest / "face-comparison.png")
    refs = [
        (
            "guanhaizi-cherry-reference-v001",
            "frame-09-17.650s.png",
            (620, 610, 1580, 1410),
            "观海子 Cherry | 17.650s",
        ),
        (
            "guanhaizi-cherry-reference-v001",
            "frame-12-24.083s.png",
            (590, 850, 1700, 1910),
            "观海子 Cherry | 24.083s",
        ),
        (
            "guanhaizi-fox-reference-v001",
            "frame-11-106.183s.png",
            (350, 230, 565, 455),
            "观海子 小狐狸 | 106.183s",
        ),
    ]
    board = Image.new("RGB", (1440, 580), (25, 25, 32))
    draw = ImageDraw.Draw(board)
    ref_manifest = []
    for i, (folder, name, box, title) in enumerate(refs):
        source = args.reference_root / folder / name
        crop = Image.open(source).convert("RGB").crop(box)
        crop.save(dest / f"reference-face-{i + 1:02d}.png")
        fitted = ImageOps.contain(crop, (460, 510), Image.Resampling.LANCZOS)
        board.paste(
            fitted,
            (i * 480 + (480 - fitted.width) // 2, 48 + (510 - fitted.height) // 2),
        )
        draw.text((i * 480 + 10, 12), title, font=font, fill="white")
        ref_manifest.append(
            {
                "source": str(source),
                "native_crop_xyxy": box,
                "display": "crop and uniform scaling only; no recoloring/sharpening",
            }
        )
    board.save(dest / "reference-faces.png")
    (dest / "visual-evidence.json").write_text(
        json.dumps(
            {"renders": stats, "references": ref_manifest}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
