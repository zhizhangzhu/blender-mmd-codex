"""Create visual inspection sheets and motion-compensated face-change metrics."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = json.loads(
        (args.diagnostics / "diagnostic-records.json").read_text(encoding="utf-8")
    )
    root = Path(source["temporary_frames"])
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 13)
    labels = {
        "head-turn": "固定灯 · 转头",
        "key-orbit": "固定头 · 移灯",
        "camera-orbit": "固定头与灯 · 相机绕拍",
    }
    overview = Image.new("RGB", (1440, 630), "#111722")
    faces = Image.new("RGB", (1440, 690), "#111722")
    records = source["rendered_records"]
    metrics = []
    for case_index, case in enumerate(labels):
        group = [record for record in records if record["case"] == case]
        ImageDraw.Draw(overview).text(
            (12, case_index * 210 + 8), labels[case], font=font, fill="white"
        )
        ImageDraw.Draw(faces).text(
            (12, case_index * 230 + 8),
            labels[case] + " · 左阿克西妮娅／右空",
            font=font,
            fill="white",
        )
        for col, index in enumerate([0, 4, 9, 14, 19, 23]):
            record = group[index]
            im = Image.open(root / case / f"frame-{index:04d}.png").convert("RGB")
            overview.paste(
                im.resize((240, 135), Image.Resampling.LANCZOS),
                (col * 240, case_index * 210 + 42),
            )
            ImageDraw.Draw(overview).text(
                (col * 240 + 8, case_index * 210 + 180),
                f"{record['angle_degrees']:+.1f}°",
                font=small,
                fill="#b8c0d0",
            )
            for actor_index, actor in enumerate(["aksiniya", "aether"]):
                crop = im.crop(tuple(record["actors"][actor]["face_roi"]))
                scale = min(114 / crop.width, 150 / crop.height)
                crop = crop.resize(
                    (round(crop.width * scale), round(crop.height * scale)),
                    Image.Resampling.LANCZOS,
                )
                faces.paste(
                    crop, (col * 240 + actor_index * 118, case_index * 230 + 46)
                )
            ImageDraw.Draw(faces).text(
                (col * 240 + 8, case_index * 230 + 202),
                f"f{index:02d} / {record['angle_degrees']:+.1f}°",
                font=small,
                fill="#b8c0d0",
            )
        for actor in ["aksiniya", "aether"]:
            previous = None
            transitions = []
            for record in group:
                im = Image.open(
                    root / case / f"frame-{record['frame']:04d}.png"
                ).convert("RGB")
                current = np.asarray(
                    im.crop(tuple(record["actors"][actor]["face_roi"])).resize(
                        (128, 128), Image.Resampling.LANCZOS
                    )
                )
                if previous is not None:
                    gray_current = cv2.cvtColor(current, cv2.COLOR_RGB2GRAY)
                    gray_previous = cv2.cvtColor(previous, cv2.COLOR_RGB2GRAY)
                    flow = cv2.calcOpticalFlowFarneback(
                        gray_current, gray_previous, None, 0.5, 3, 15, 3, 5, 1.2, 0
                    )
                    yy, xx = np.mgrid[:128, :128].astype(np.float32)
                    aligned = cv2.remap(
                        previous,
                        xx + flow[..., 0],
                        yy + flow[..., 1],
                        cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REFLECT,
                    )
                    difference = (
                        np.abs(aligned.astype(float) - current.astype(float))[
                            12:-12, 12:-12
                        ]
                        / 255
                    )
                    transitions.append(
                        {
                            "to_frame": record["frame"],
                            "mean_absolute_change": float(difference.mean()),
                            "fraction_above_0_2": float(
                                np.mean(np.max(difference, axis=-1) > 0.2)
                            ),
                        }
                    )
                previous = current
            worst = max(transitions, key=lambda item: item["mean_absolute_change"])
            metrics.append(
                {
                    "case": case,
                    "actor": actor,
                    "worst_transition": worst,
                    "transitions": transitions,
                }
            )
    overview.save(args.output_dir / "diagnostics-overview.jpg", quality=95)
    faces.save(args.output_dir / "diagnostics-faces.jpg", quality=96)
    result = {
        "metrics": metrics,
        "scope": "Motion-compensated crop differences are a screening aid, not proof of no flicker. Inspect the sheets and worst transitions visually.",
        "maximum_axis_error": max(
            axis["error"]
            for record in records
            for actor in record["actors"].values()
            for axis in actor["axes"].values()
        ),
    }
    (args.output_dir / "diagnostic-screening.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "maximum_axis_error": result["maximum_axis_error"],
                "worst_transitions": [
                    {k: v for k, v in item.items() if k != "transitions"}
                    for item in metrics
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
