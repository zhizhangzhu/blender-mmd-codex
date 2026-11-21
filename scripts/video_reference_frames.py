"""Extract timestamped local reference frames and a contact sheet (OpenCV/Pillow).

Use a Python environment with cv2 and PIL. Output must be a new directory.
This reads rendered video; it does not recover camera or animation source data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def main():
    import cv2
    from PIL import Image, ImageDraw

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.count <= 30:
        parser.error("count must be between 1 and 30")
    video = args.video.resolve(strict=True)
    cap = cv2.VideoCapture(str(video))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Cannot decode video: {video}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or count <= 0:
            raise RuntimeError("Invalid video duration/fps")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        args.output_dir.mkdir(parents=True, exist_ok=False)
        columns = min(4, args.count)
        cell_width = 360
        cell_height = round(cell_width * height / width)
        sheet = Image.new("RGB", (columns * cell_width, math.ceil(args.count / columns) * (cell_height + 30)), "#171b24")
        draw = ImageDraw.Draw(sheet)
        frames = []
        for index in range(args.count):
            frame_index = round((index + 0.25) * (count - 1) / args.count)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {frame_index}")
            seconds = frame_index / fps
            filename = f"frame-{index + 1:02d}-{seconds:06.3f}s.png"
            ok, encoded = cv2.imencode(".png", frame)
            if not ok:
                raise RuntimeError("PNG encoding failed")
            encoded.tofile(str(args.output_dir / filename))
            thumbnail = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((cell_width, cell_height))
            x = (index % columns) * cell_width
            y = (index // columns) * (cell_height + 30)
            sheet.paste(thumbnail, (x, y))
            draw.text((x + 8, y + cell_height + 8), f"{index + 1:02d}  {seconds:.3f}s  frame {frame_index}", fill="white")
            frames.append({"file": filename, "frame_index_zero_based": frame_index, "seconds": seconds})
        sheet.save(args.output_dir / "contact-sheet.jpg", quality=94)
        report = {"video": str(video), "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                  "width": width, "height": height, "fps_reported": fps,
                  "frame_count": count, "duration_seconds": count / fps, "frames": frames,
                  "limits": ["OpenCV metadata; variable frame rate timestamps may require ffprobe for exact timing.",
                             "Frames are visual reference only, not recovered material/camera settings."]}
        (args.output_dir / "reference-metadata.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        cap.release()


if __name__ == "__main__":
    main()
