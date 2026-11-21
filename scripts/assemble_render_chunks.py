"""Join independently rendered, contiguous video chunks without recompression.

Manifest: {"fps":60,"width":1080,"height":1920,"chunks":[
  {"path":"D:/.../part.mp4","start":1,"end":200}, ... ]}
Requires OpenCV and an explicitly supplied FFmpeg executable. Chunk bounds are
source Blender frames, inclusive; each chunk must retain exactly those frames.
"""

import argparse
import json
import math
import subprocess
from pathlib import Path


def validate_manifest(manifest):
    chunks = manifest["chunks"]
    if not chunks:
        raise ValueError("No chunks supplied")
    previous_end = 0
    for chunk in chunks:
        if chunk["start"] != previous_end + 1 or chunk["end"] < chunk["start"]:
            raise ValueError(
                "Chunks must cover frame 1 onward without gaps or overlaps"
            )
        previous_end = chunk["end"]
    return previous_end


def main():
    import cv2

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--ffmpeg", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    total = validate_manifest(manifest)
    lines = []
    for chunk in manifest["chunks"]:
        path = Path(chunk["path"]).resolve(strict=True)
        cap = cv2.VideoCapture(str(path))
        try:
            assert cap.isOpened(), f"Cannot decode {path}"
            assert (
                int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                == chunk["end"] - chunk["start"] + 1
            )
            assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == manifest["width"]
            assert int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) == manifest["height"]
            assert math.isclose(
                cap.get(cv2.CAP_PROP_FPS), manifest["fps"], abs_tol=0.001
            )
        finally:
            cap.release()
        quoted = path.as_posix().replace("'", "'\\''")
        lines.append(f"file '{quoted}'\n")
    concat_list = args.manifest.with_suffix(".ffconcat.txt")
    with concat_list.open("x", encoding="utf-8", newline="\n") as stream:
        stream.writelines(lines)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(args.ffmpeg),
            "-hide_banner",
            "-nostdin",
            "-n",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-map",
            "0:v:0",
            "-c:v",
            "copy",
            "-an",
            "-video_track_timescale",
            "15360",
            "-movflags",
            "+faststart",
            str(args.output),
        ],
        check=True,
    )
    print("RENDER_CHUNKS_JOINED", total, "frames", args.output)


if __name__ == "__main__":
    main()
