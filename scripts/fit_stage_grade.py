"""Fit global, monotonic RGB grading curves from a stage render and reference.

This matches channel distributions, not image content or spatial patches. Use
only after matching camera/materials; it cannot create missing lighting detail.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def linear(value):
    return np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    a = (
        np.asarray(
            Image.open(args.render).convert("RGB").resize((1280, 720)), dtype=float
        )
        / 255
    )
    b = (
        np.asarray(
            Image.open(args.reference).convert("RGB").resize((1280, 720)), dtype=float
        )
        / 255
    )
    quantiles = [
        0.005,
        0.02,
        0.05,
        0.1,
        0.2,
        0.35,
        0.5,
        0.65,
        0.8,
        0.9,
        0.95,
        0.98,
        0.995,
    ]
    curves = []
    for channel in range(3):
        x = np.r_[0, np.quantile(a[:, :, channel], quantiles), 1]
        y = np.r_[0, np.quantile(b[:, :, channel], quantiles), 1]
        x, indices = np.unique(x, return_index=True)
        curves.append(np.stack([linear(x), linear(y[indices])], axis=1).tolist())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "method": "Global per-channel quantile curves; not spatial reference projection or image detail replacement",
                "render": str(args.render),
                "reference": str(args.reference),
                "curves": curves,
                "working_space": "scene-linear under Standard, exposure zero",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
