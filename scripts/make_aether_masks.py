"""Derive reviewed, Aether-specific artistic controls from supplied textures."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def smooth(lo, hi, value):
    x = np.clip((value - lo) / (hi - lo), 0, 1)
    return x * x * (3 - 2 * x)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    body = (
        np.asarray(Image.open(args.source / "服.png").convert("RGB"), dtype=np.float32)
        / 255
    )
    hsv = cv2.cvtColor(body, cv2.COLOR_RGB2HSV)
    h, s, v = hsv.transpose(2, 0, 1)
    gold = (
        smooth(25, 34, h)
        * (1 - smooth(53, 65, h))
        * smooth(0.12, 0.32, s)
        * smooth(0.24, 0.52, v)
    )
    rough = 0.78 * (1 - gold) + 0.24 * gold
    control = np.stack((gold, rough, np.zeros_like(gold)), axis=2)
    Image.fromarray((control * 255 + 0.5).astype(np.uint8)).save(
        args.output / "body-control.png"
    )
    face = (
        np.asarray(Image.open(args.source / "面.png").convert("RGB"), dtype=np.float32)
        / 255
    )
    height, width = face.shape[:2]
    y, x = np.mgrid[0:height, 0:width]
    u, v = x / width, 1 - y / height
    gate = (u > 0.44) & (u < 0.57) & (v > 0.30) & (v < 0.35)
    mouth = (
        gate
        * (1 - smooth(0.72, 0.88, face.max(axis=2)))
        * smooth(0.04, 0.12, face[..., 0] - face[..., 1])
    )
    Image.fromarray((mouth * 255 + 0.5).astype(np.uint8)).save(
        args.output / "face-crease.png"
    )
    Image.fromarray((gold * 255 + 0.5).astype(np.uint8)).save(
        args.output / "gold-review.png"
    )
    hair = (
        np.asarray(Image.open(args.source / "发.png").convert("RGB"), dtype=np.float32)
        / 255
    )
    hh, hw = hair.shape[:2]
    yy, xx = np.mgrid[0:hh, 0:hw]
    roi = (xx < hw * 0.21) & (yy > hh * 0.33) & (yy < hh * 0.55)
    dark = (roi & (hair.max(axis=2) < 0.60)).astype(np.uint8)
    _count, _labels, stats, _centers = cv2.connectedComponentsWithStats(dark)
    component = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    bx, by, bw, bh, _area = stats[component]
    cx, cy = bx + bw / 2, by + bh / 2
    nx = (xx - cx) / (bw / 2) * 0.52
    ny = -(yy - cy) / (bh / 2) * 0.52
    inside = ((xx - cx) / (bw / 2)) ** 2 + ((yy - cy) / (bh / 2)) ** 2 < 1
    nx, ny = np.where(inside, nx, 0), np.where(inside, ny, 0)
    nz = np.sqrt(np.maximum(0.01, 1 - nx * nx - ny * ny))
    normals = np.stack((nx, ny, nz), axis=2) * 0.5 + 0.5
    Image.fromarray((normals * 255 + 0.5).astype(np.uint8)).save(
        args.output / "iris-normal.png"
    )
    (args.output / "mask-report.json").write_text(
        json.dumps(
            {
                "source_body": "服.png",
                "source_face": "面.png",
                "method": "Aether-specific color-derived art controls; not original game PBR/ILM maps",
                "metal_allowed_materials": ["身体", "手套", "手套.001", "发饰", "耳饰"],
                "excluded_gold_fabric_materials": ["披风", "围巾"],
                "excluded_skin_materials": ["肌", "面1", "面2", "口舌"],
                "gold_fraction": float((gold > 0.5).mean()),
                "mouth_pixels": int((mouth > 0.1).sum()),
                "iris_normal_region_pixels": [int(bx), int(by), int(bw), int(bh)],
                "iris_normal_status": "procedural convex optical control; not an original game normal map",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
