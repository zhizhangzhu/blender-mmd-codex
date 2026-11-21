"""Decode every output frame; verify timing, image dimensions, and MP4 streams.

Requires OpenCV/Pillow (system Python on this workstation). No external ffprobe.
"""

from __future__ import annotations
import argparse
import cv2
import hashlib
import json
import math
import struct
from pathlib import Path
from PIL import Image, ImageDraw


def boxes(data, start=0, end=None):
    end = len(data) if end is None else end
    cursor = start
    while cursor + 8 <= end:
        size, kind = struct.unpack_from(">I4s", data, cursor)
        header = 8
        if size == 1:
            if cursor + 16 > end:
                raise ValueError("Truncated extended MP4 box")
            size = struct.unpack_from(">Q", data, cursor + 8)[0]
            header = 16
        if size == 0:
            size = end - cursor
        if size < header or cursor + size > end:
            raise ValueError("Invalid MP4 box bounds")
        yield kind, cursor + header, cursor + size
        cursor += size


def stream_types(path):
    data = path.read_bytes()
    types = []
    for kind, start, end in boxes(data):
        if kind != b"moov":
            continue
        for tk, ts, te in boxes(data, start, end):
            if tk != b"trak":
                continue
            for mk, ms, me in boxes(data, ts, te):
                if mk != b"mdia":
                    continue
                for hk, hs, he in boxes(data, ms, me):
                    if hk == b"hdlr" and hs + 12 <= he:
                        types.append(data[hs + 8 : hs + 12].decode("ascii"))
    return types


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--fps", type=float, default=60)
    p.add_argument("--seconds", type=float, default=20)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    cap = cv2.VideoCapture(str(args.video))
    assert cap.isOpened(), "Video decoder failed"
    fps = cap.get(cv2.CAP_PROP_FPS)
    declared = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = (
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    targets = {round((i + 0.5) * declared / 12) for i in range(12)}
    decoded = 0
    previous = None
    freeze = 0
    maxfreeze = 0
    lumas = []
    differences = []
    stills = []
    thumb_width = 480 if width > height else 270
    thumb_height = round(thumb_width * height / width)
    cell_height = thumb_height + 30
    sheet = Image.new("RGB", (thumb_width * 4, cell_height * 3), "#20202b")
    draw = ImageDraw.Draw(sheet)
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.cvtColor(cv2.resize(frame, (90, 160)), cv2.COLOR_BGR2GRAY)
        lumas.append(float(small.mean()))
        if previous is not None:
            d = float(cv2.absdiff(small, previous).mean())
            differences.append(d)
            freeze = freeze + 1 if d < 0.005 else 0
            maxfreeze = max(maxfreeze, freeze)
        previous = small
        if decoded in targets:
            name = f"video-frame-{decoded:04d}.png"
            cv2.imencode(".png", frame)[1].tofile(str(args.output_dir / name))
            i = len(stills)
            x = i % 4 * thumb_width
            y = i // 4 * cell_height
            thumb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize(
                (thumb_width, thumb_height)
            )
            sheet.paste(thumb, (x, y))
            draw.text((x + 6, y + thumb_height + 6), f"{decoded / fps:.3f}s", fill="white")
            stills.append(name)
        decoded += 1
    cap.release()
    sheet.save(args.output_dir / "video-contact-sheet.jpg", quality=94)
    streams = stream_types(args.video)
    report = {
        "video": str(args.video),
        "sha256": hashlib.sha256(args.video.read_bytes()).hexdigest(),
        "width": width,
        "height": height,
        "fps": fps,
        "declared_frames": declared,
        "decoded_frames": decoded,
        "seconds": decoded / fps,
        "mp4_stream_types": streams,
        "minimum_mean_luma": min(lumas),
        "maximum_still_run_frames": maxfreeze,
        "representative_frames": stills,
    }
    report["passed"] = (
        width == args.width
        and height == args.height
        and abs(fps - args.fps) < 0.01
        and decoded == declared
        and abs(decoded / fps - args.seconds) < 0.02
        and "vide" in streams
        and "soun" in streams
        and min(lumas) > 5
        and maxfreeze < 60
    )
    (args.output_dir / "video-verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert report["passed"], "Output video verification failed"


if __name__ == "__main__":
    main()
