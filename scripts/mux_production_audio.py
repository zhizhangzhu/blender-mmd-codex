"""Mix a selected BGM segment into an existing video without rerendering.

Needs an FFmpeg executable supplied by --ffmpeg or imageio_ffmpeg. Does not
replace either source. Timing is a source-time selection, not manual beat sync.
"""

from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def project_audio(project_path):
    project = json.loads(project_path.read_text(encoding="utf-8"))
    settings = project.get("audio", {})
    if not settings.get("bgm"):
        raise ValueError(
            "Project has no selected audio.bgm; do not fall back to accompaniment"
        )
    source = Path(settings["bgm"])
    if not source.is_file():
        raise FileNotFoundError(source)
    expected = settings.get("bgm_sha256")
    if expected and hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError("Project BGM checksum changed")
    return source


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    audio_group = p.add_mutually_exclusive_group(required=True)
    audio_group.add_argument("--audio", type=Path)
    audio_group.add_argument(
        "--project", type=Path, help="Use the selected audio.bgm from a project recipe"
    )
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audio-start", type=float, required=True)
    p.add_argument("--seconds", type=float, default=20)
    p.add_argument("--gain", type=float, default=1.0)
    p.add_argument("--ffmpeg", type=Path)
    args = p.parse_args()
    audio = project_audio(args.project) if args.project else args.audio
    if args.output.exists():
        raise FileExistsError(args.output)
    if not args.video.is_file() or not audio.is_file():
        raise FileNotFoundError("Missing source media")
    if args.ffmpeg:
        executable = str(args.ffmpeg)
    else:
        import imageio_ffmpeg

        executable = imageio_ffmpeg.get_ffmpeg_exe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            executable,
            "-hide_banner",
            "-nostdin",
            "-n",
            "-i",
            str(args.video),
            "-ss",
            str(args.audio_start),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-af",
            f"volume={args.gain}",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-ar",
            "48000",
            "-t",
            str(args.seconds),
            "-movflags",
            "+faststart",
            str(args.output),
        ],
        check=True,
    )
    print("PRODUCTION_AUDIO_MUX_OK", args.output)


if __name__ == "__main__":
    main()
