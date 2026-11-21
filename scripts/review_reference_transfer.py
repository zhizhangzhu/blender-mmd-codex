"""Measure real native ablations and package same-frame comparison images."""

import argparse
import json
from pathlib import Path

import numpy as np
from package_fox_cinema import panel
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    args = parser.parse_args()
    dest = args.root / "review"
    dest.mkdir(exist_ok=False)
    controls = args.root / "controls-4290"
    complete = np.asarray(
        Image.open(controls / "complete.png").convert("RGB"), dtype=np.float32
    )
    results = []
    for name in [
        "design-off",
        "rim-off",
        "reflection-off",
        "cast-shadows-off",
        "stage-grade-off",
        "material-controls-off",
    ]:
        alternate = np.asarray(
            Image.open(controls / (name + ".png")).convert("RGB"), dtype=np.float32
        )
        assert alternate.shape == complete.shape == (1080, 1920, 3)
        difference = np.abs(complete - alternate)
        row = {
            "case": name,
            "mean_rgb_delta_255": float(difference.mean()),
            "max_rgb_delta_255": float(difference.max()),
            "pixels_delta_over_2": int((difference.max(axis=2) > 2).sum()),
        }
        row["visible_numeric_effect"] = row["max_rgb_delta_255"] > 1
        results.append(row)
    before = args.previous / "review/after-4290.png"
    after = args.root / "production-v3/transfer-4290.png"
    panel(
        [(before, "前版 · 人物分层"), (after, "新版 · 受光与材质移植")],
        dest / "before-after-4290.jpg",
    )
    old_wide = args.previous / "review/native-4250.png"
    new_wide = args.root / "production-v3/transfer-4250.png"
    panel(
        [(old_wide, "前版 · 礼堂远景"), (new_wide, "新版 · 前景分区与阴影")],
        dest / "before-after-4250.jpg",
    )
    report = {
        "passed": all(r["visible_numeric_effect"] for r in results),
        "frame": 4290,
        "resolution": [1920, 1080],
        "controls": results,
        "limits": "Measured effects and comparison packaging only. Different nonphysical controls are not isolated physical passes; visual merit requires human review.",
    }
    with (args.root / "control-verification.json").open(
        "x", encoding="utf-8"
    ) as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
