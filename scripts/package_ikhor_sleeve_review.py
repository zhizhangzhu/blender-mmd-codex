"""Encode the diagnostic wrists and make explicitly sampled contact sheets."""

import argparse
import json
import subprocess
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

FFMPEG = Path(
    "D:/codex/temp/blender-mmd-video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--frames", type=int, nargs="+", required=True)
    args = parser.parse_args()
    report = json.loads((args.root / "wrist-review.json").read_text(encoding="utf-8"))
    frames = report["frames"]
    assert frames == list(range(4140, 4440))
    selected = sorted(set(args.frames))
    assert all(frame in frames for frame in selected)
    movie = args.root / "Both_Wrists_Unblurred_5s.mp4"
    assert not movie.exists()
    command = [str(FFMPEG), "-v", "error", "-n"]
    for side in ("right", "left"):
        command += [
            "-framerate",
            "60",
            "-start_number",
            "4140",
            "-i",
            str(args.root / side / "%06d.png"),
        ]
        assert all(
            (args.root / side / f"{frame:06d}.png").is_file() for frame in frames
        )
    command += [
        "-filter_complex",
        "[0:v][1:v]hstack=inputs=2,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]",
        "-map",
        "[v]",
        "-frames:v",
        "300",
        "-c:v",
        "libx264",
        "-crf",
        "16",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "iec61966-2-1",
        "-colorspace",
        "bt709",
        "-color_range",
        "tv",
        "-movflags",
        "+faststart",
        str(movie),
    ]
    subprocess.run(command, check=True)
    sheets = []
    for side in ("right", "left"):
        for offset in range(0, len(selected), 12):
            subset = selected[offset : offset + 12]
            canvas = Image.new("RGB", (1120, 4 * 302), "#121824")
            draw = ImageDraw.Draw(canvas)
            for index, frame in enumerate(subset):
                x, y = (index % 4) * 280, (index // 4) * 302
                with Image.open(args.root / side / f"{frame:06d}.png") as image:
                    canvas.paste(
                        image.resize((280, 280), Image.Resampling.LANCZOS), (x, y)
                    )
                draw.text((x + 6, y + 282), f"{side} / source {frame}", fill="white")
            path = args.root / f"{side}-contact-{offset // 12:02d}.jpg"
            canvas.save(path, quality=95)
            sheets.append(str(path))
    capture = cv2.VideoCapture(str(movie))
    decoded, size = 0, None
    while True:
        ok, image = capture.read()
        if not ok:
            break
        decoded += 1
        size = [image.shape[1], image.shape[0]]
    fps = capture.get(cv2.CAP_PROP_FPS)
    capture.release()
    assert decoded == 300 and size == [960, 480] and fps == 60
    result = {
        "source_sha256": report["source_sha256"],
        "decoded_frames": decoded,
        "fps": fps,
        "size": size,
        "video": str(movie),
        "contact_sheet_frames": selected,
        "contact_sheets": sheets,
        "geometry_and_art_approval": None,
        "scope": "Encoded continuous 300-frame two-wrist diagnostic. Contact sheets are samples, not a claim of manually viewing all 600 images.",
    }
    (args.root / "wrist-video-verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("IKHOR_WRIST_VIDEO_DECODED", decoded, flush=True)


if __name__ == "__main__":
    main()
