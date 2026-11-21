"""Render a bounded duet review clip, reuse verified matching chunks, and verify.

The source choreography/camera use global frames. The assembly manifest uses
local frame numbers so exact gap/overlap validation remains valid.
"""

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*arguments):
    subprocess.run([str(value) for value in arguments], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--frames", type=int, default=1200)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--reuse-manifest", type=Path)
    parser.add_argument("--linear-archive-dir", type=Path)
    parser.add_argument("--caption-cache-dir", type=Path)
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
    assert (
        1 <= args.workers <= 2
        and 1 <= args.start <= args.start + args.frames - 1 <= 11899
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    archive_dir = args.linear_archive_dir or (args.output_dir / "linear")
    if archive_dir.exists():
        raise FileExistsError("Use a new linear archive directory: " + str(archive_dir))
    if args.caption_cache_dir:
        args.caption_cache_dir.mkdir(parents=True, exist_ok=False)
    args.logs.mkdir(parents=True, exist_ok=False)
    pieces = args.output_dir / "chunks"
    pieces.mkdir()
    chunks = []
    cursor = args.start
    if args.reuse_manifest:
        original = json.loads(args.reuse_manifest.read_text(encoding="utf-8"))
        assert Path(original["source_blend"]).resolve() == args.blend.resolve()
        for item in original["chunks"]:
            if item["start"] != cursor or item["end"] >= args.start + args.frames:
                continue
            path = Path(item["path"])
            progress_path = path.with_suffix(".progress.json")
            if not path.is_file() or not progress_path.is_file():
                continue
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            if not progress["complete"]:
                continue
            assert progress["start"] == item["start"] and progress["end"] == item["end"]
            chunks.append(
                {
                    "path": str(path),
                    "start": cursor - args.start + 1,
                    "end": item["end"] - args.start + 1,
                    "source_start": cursor,
                    "source_end": item["end"],
                    "reused": True,
                }
            )
            cursor = item["end"] + 1
    remaining = args.start + args.frames - cursor
    jobs = []
    if remaining:
        step = math.ceil(remaining / args.workers)
        for first in range(cursor, args.start + args.frames, step):
            last = min(first + step - 1, args.start + args.frames - 1)
            index = len(chunks)
            path = pieces / f"part-{index:02d}.mp4"
            item = {
                "path": str(path),
                "start": first - args.start + 1,
                "end": last - args.start + 1,
                "source_start": first,
                "source_end": last,
                "reused": False,
            }
            chunks.append(item)
            jobs.append(item)
    manifest = args.output_dir / "chunks.json"
    manifest.write_text(
        json.dumps(
            {
                "width": 1920,
                "height": 1080,
                "fps": 60,
                "source_blend": str(args.blend.resolve()),
                "linear_archive": str(archive_dir.resolve()),
                "caption_cache": str(args.caption_cache_dir.resolve())
                if args.caption_cache_dir
                else None,
                "chunks": chunks,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    from assemble_render_chunks import validate_manifest

    assert validate_manifest({"chunks": chunks}) == args.frames
    processes = []
    try:
        for item in jobs:
            path = Path(item["path"])
            log = (args.logs / (path.stem + ".log")).open("w", encoding="utf-8")
            command = [
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
                str(path),
                "--progress",
                str(path.with_suffix(".progress.json")),
                "--start",
                str(item["source_start"]),
                "--end",
                str(item["source_end"]),
                "--linear-archive-dir",
                str(archive_dir),
            ]
            if args.caption_cache_dir:
                command += ["--caption-cache-dir", str(args.caption_cache_dir)]
            process = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            processes.append((process, log, item))
            print(
                "SAMPLE_WORKER_STARTED",
                process.pid,
                item["source_start"],
                item["source_end"],
                flush=True,
            )
        last_print = 0
        while any(process.poll() is None for process, _log, _item in processes):
            for process, _log, _item in processes:
                if process.poll() not in (None, 0):
                    raise RuntimeError(
                        f"Sample worker failed: {process.pid}; inspect {args.logs}"
                    )
            if time.time() - last_print >= 45:
                complete = sum(
                    item["end"] - item["start"] + 1 for item in chunks if item["reused"]
                )
                for path in pieces.glob("*.progress.json"):
                    try:
                        value = json.loads(path.read_text())
                        complete += value["last_frame"] - value["start"] + 1
                    except (OSError, ValueError):
                        pass
                print("SAMPLE_PROGRESS", complete, "/", args.frames, flush=True)
                last_print = time.time()
            time.sleep(3)
        assert all(process.returncode == 0 for process, _log, _item in processes)
    except BaseException:
        for process, _log, _item in processes:
            if process.poll() is None:
                process.terminate()
        raise
    finally:
        for _process, log, _item in processes:
            log.close()
    seconds = args.frames / 60
    duration_label = f"{seconds:g}s"
    picture = args.output_dir / f"Aether_Duet_{duration_label}_Picture.mp4"
    movie = args.output_dir / f"Aether_Duet_{duration_label}_REVIEW.mp4"
    run(
        sys.executable,
        ROOT / "scripts/assemble_render_chunks.py",
        "--manifest",
        manifest,
        "--ffmpeg",
        args.ffmpeg,
        "--output",
        picture,
    )
    run(
        sys.executable,
        ROOT / "scripts/mux_production_audio.py",
        "--video",
        picture,
        "--project",
        ROOT / "presets/projects/franken-duet-full-v1.json",
        "--output",
        movie,
        "--audio-start",
        (args.start - 1) / 60,
        "--seconds",
        seconds,
        "--gain",
        0.87,
        "--ffmpeg",
        args.ffmpeg,
    )
    run(
        sys.executable,
        ROOT / "scripts/verify_video.py",
        "--video",
        movie,
        "--output-dir",
        args.output_dir / "video-qa",
        "--width",
        1920,
        "--height",
        1080,
        "--fps",
        60,
        "--seconds",
        seconds,
    )
    run(
        args.blender,
        "--background",
        "--disable-autoexec",
        "--python-exit-code",
        1,
        "--python",
        ROOT / "scripts/verify_audio_blender.py",
        "--",
        "--video",
        movie,
        "--output",
        args.output_dir / "audio-verification.json",
        "--seconds",
        seconds,
    )
    boundaries = [str(item["end"]) for item in chunks[:-1]]
    if boundaries:
        run(
            sys.executable,
            ROOT / "scripts/verify_render_seams.py",
            "--video",
            movie,
            "--output-dir",
            args.output_dir / "seam-qa",
            "--boundaries",
            *boundaries,
        )
    (args.output_dir / "sample-report.json").write_text(
        json.dumps(
            {
                "status": f"{seconds:g}-second review sample rendered and video/audio decode verified; not full-song delivery",
                "movie": str(movie),
                "project": str(args.blend),
                "source_frames": [args.start, args.start + args.frames - 1],
                "frames": args.frames,
                "seconds": seconds,
                "bgm_source_start_seconds": (args.start - 1) / 60,
                "bgm": "User-selected original vocal FLAC; AAC delivery track",
                "camera_motion_changed": False,
                "physics_changed": False,
                "linear_archive_directory": str(archive_dir),
                "caption_cache_directory": str(args.caption_cache_dir)
                if args.caption_cache_dir
                else None,
                "linear_archive_reused_frames_need_separate_validation": any(
                    item["reused"] for item in chunks
                ),
                "note": "Material review sample requested by user; complete movie deferred",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("DUET_SAMPLE_VERIFIED", movie, flush=True)


if __name__ == "__main__":
    main()
