"""Render full-song chunks, validate/join them, mux selected FLAC, then verify.

No source media is overwritten. Output directory and logs must be fresh.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make_ranges(review_start=0, review_frames=120):
    cuts = {1, 121, 11900}
    cuts.update(range(1321, 11900, 1200))
    if review_start:
        if not (1 <= review_start < review_start + review_frames <= 11900):
            raise ValueError("Review segment is outside the full-song frame range")
        cuts.update((review_start, review_start + review_frames))
    ordered = sorted(cuts)
    return [(ordered[i], ordered[i + 1] - 1) for i in range(len(ordered) - 1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--review-start", type=int, default=0)
    parser.add_argument("--review-frames", type=int, default=120)
    parser.add_argument(
        "--blender",
        type=Path,
        default=Path("E:/tools/Blender Foundation/Blender 5.2/blender.exe"),
    )
    parser.add_argument(
        "--ffmpeg",
        type=Path,
        default=Path(
            "D:/codex/temp/blender-mmd-video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
        ),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    args.logs.mkdir(parents=True, exist_ok=False)
    pieces = args.output_dir / "chunks"
    pieces.mkdir()
    ranges = make_ranges(args.review_start, args.review_frames)
    jobs = []
    chunks = []
    for i, (first, last) in enumerate(ranges):
        destination = pieces / f"part-{i:02d}.mp4"
        jobs.append({"path": str(destination), "start": first, "end": last, "index": i})
        chunks.append({"path": str(destination), "start": first, "end": last})
    manifest = args.output_dir / "chunks.json"
    manifest.write_text(
        json.dumps(
            {
                "width": 1920,
                "height": 1080,
                "fps": 60,
                "chunks": chunks,
                "source_blend": str(args.blend.resolve()),
                "review_segment": [
                    args.review_start,
                    args.review_start + args.review_frames - 1,
                ]
                if args.review_start
                else None,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if args.review_start:
        jobs.sort(
            key=lambda job: (
                not (
                    args.review_start
                    <= job["start"]
                    < args.review_start + args.review_frames
                )
            )
        )
    active = []
    started = time.time()
    last_print = 0
    while jobs or active:
        while jobs and len(active) < args.workers:
            job = jobs.pop(0)
            log = (args.logs / f"part-{job['index']:02d}.log").open(
                "w", encoding="utf-8"
            )
            progress = pieces / f"part-{job['index']:02d}.progress.json"
            cmd = [
                str(args.blender),
                "--background",
                "--disable-autoexec",
                "--threads",
                "6",
                str(args.blend),
                "--python-exit-code",
                "1",
                "--python",
                str(ROOT / "scripts/render_duet_chunk.py"),
                "--",
                "--output",
                job["path"],
                "--progress",
                str(progress),
                "--start",
                str(job["start"]),
                "--end",
                str(job["end"]),
            ]
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            active.append((job, process, log))
            print(
                "CHUNK_STARTED",
                job["index"],
                job["start"],
                job["end"],
                process.pid,
                flush=True,
            )
        for item in list(active):
            job, process, log = item
            code = process.poll()
            if code is None:
                continue
            log.close()
            active.remove(item)
            if code:
                for _job, other, _log in active:
                    other.terminate()
                raise RuntimeError(f"Chunk {job['index']} failed; inspect {args.logs}")
            print("CHUNK_FINISHED", job["index"], flush=True)
        if time.time() - last_print >= 45:
            completed = 0
            for path in pieces.glob("*.progress.json"):
                try:
                    p = json.loads(path.read_text(encoding="utf-8"))
                    completed += p["last_frame"] - p["start"] + 1
                except (ValueError, OSError):
                    pass
            print(
                "DUET_TOTAL_PROGRESS",
                completed,
                "/ 11899",
                "elapsed",
                round(time.time() - started),
                flush=True,
            )
            last_print = time.time()
        time.sleep(3)
    picture = args.output_dir / "Franken_Duet_Picture_Master.mp4"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/assemble_render_chunks.py"),
            "--manifest",
            str(manifest),
            "--ffmpeg",
            str(args.ffmpeg),
            "--output",
            str(picture),
        ],
        check=True,
    )
    final = args.output_dir / "Franken_Duet_FULL_FINAL.mp4"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/mux_production_audio.py"),
            "--video",
            str(picture),
            "--project",
            str(ROOT / "presets/projects/franken-duet-full-v1.json"),
            "--output",
            str(final),
            "--audio-start",
            "0",
            "--seconds",
            "198.3158125",
            "--gain",
            "0.87",
            "--ffmpeg",
            str(args.ffmpeg),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/verify_video.py"),
            "--video",
            str(final),
            "--output-dir",
            str(args.output_dir / "video-qa"),
            "--width",
            "1920",
            "--height",
            "1080",
            "--fps",
            "60",
            "--seconds",
            "198.3158125",
        ],
        check=True,
    )
    subprocess.run(
        [
            str(args.blender),
            "--background",
            "--disable-autoexec",
            "--python-exit-code",
            "1",
            "--python",
            str(ROOT / "scripts/verify_audio_blender.py"),
            "--",
            "--video",
            str(final),
            "--output",
            str(args.output_dir / "audio-verification.json"),
            "--seconds",
            "198.3158125",
        ],
        check=True,
    )
    print(
        "DUET_FINAL_VERIFIED",
        str(final),
        "wall_seconds",
        time.time() - started,
        flush=True,
    )


if __name__ == "__main__":
    main()
