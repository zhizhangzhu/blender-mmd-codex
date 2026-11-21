"""Read colored on-screen annotations from a local tutorial at sampled times.

This is sparse OCR of visible video overlays, not a complete subtitle track.
Keep third-party tutorial text private and verify against the original frames.
"""

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--period", type=float, default=30)
    args = parser.parse_args()
    if args.period < 1:
        parser.error("period must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    cap = cv2.VideoCapture(str(args.video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise RuntimeError("Cannot read tutorial")
    seconds = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    engine = RapidOCR(intra_op_num_threads=4, inter_op_num_threads=1)
    start = time.perf_counter()
    rows = []
    with (args.output_dir / "observed-annotations.jsonl").open(
        "w", encoding="utf-8"
    ) as ledger:
        for timestamp in np.arange(0, seconds, args.period):
            cap.set(cv2.CAP_PROP_POS_MSEC, float(timestamp) * 1000)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot read {timestamp}")
            # The supplied teacher uses saturated red/pink overlays. Remove
            # most of the Blender UI text without changing the source media.
            b, g, r = cv2.split(frame)
            mask = (
                (r.astype(float) > g.astype(float) * 1.35)
                & (r > 135)
                & (g < 155)
                & (r.astype(float) > b.astype(float) * 1.05)
            ).astype(np.uint8) * 255
            text_image = cv2.cvtColor(255 - mask, cv2.COLOR_GRAY2BGR)
            result, _elapsed = engine(text_image, use_cls=False)
            annotations = [
                {"text": item[1], "score": float(item[2]), "box": item[0]}
                for item in (result or [])
                if item[2] >= 0.7
            ]
            row = {
                "seconds": float(timestamp),
                "annotations": annotations,
                "source": "sampled overlay OCR; verify spelling and scope",
            }
            rows.append(row)
            ledger.write(json.dumps(row, ensure_ascii=False) + "\n")
            ledger.flush()
            if len(rows) % 10 == 0:
                print(
                    "OCR_PROGRESS",
                    round(float(timestamp), 1),
                    "/",
                    round(seconds, 1),
                    flush=True,
                )
    cap.release()
    (args.output_dir / "report.json").write_text(
        json.dumps(
            {
                "video": str(args.video),
                "seconds": seconds,
                "sample_period_seconds": args.period,
                "frames_read": len(rows),
                "elapsed_seconds": time.perf_counter() - start,
                "complete": True,
                "limitations": "sampled visible annotations only; not full narration or a platform subtitle track",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("OCR_COMPLETE", len(rows), flush=True)


if __name__ == "__main__":
    main()
