"""Render the open draft's frame range as a small, silent H.264 camera preview.

Run inside Blender after loading a draft, then -- --output <new.mp4>.
Does not save the modified render settings back into the source project.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main():
    import bpy

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=360)
    parser.add_argument("--height", type=int, default=640)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.output.suffix.lower() != ".mp4" or args.width < 2 or args.height < 2 or args.width % 2 or args.height % 2:
        raise ValueError("Use an MP4 output and positive even dimensions")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = args.width, args.height
    scene.render.resolution_percentage = 100
    settings = scene.render.image_settings
    if hasattr(settings, "media_type"):
        settings.media_type = "VIDEO"
    settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.audio_codec = "NONE"
    scene.render.filepath = str(args.output)
    scene.render.use_sequencer = False
    bpy.ops.render.render(animation=True)
    print("CAMERA_PREVIEW_OK", args.output)


if __name__ == "__main__":
    main()
