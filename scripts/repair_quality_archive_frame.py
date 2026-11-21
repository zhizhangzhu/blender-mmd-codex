"""Rerender an explicitly requested master frame and its native linear archive."""

import argparse
import sys
from pathlib import Path

import bpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--frame", type=int, required=True)
parser.add_argument("--preview", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
assert 4140 <= args.frame <= 4439
scene = bpy.context.scene
assert scene.get("quality_light_space_revision")
scene.frame_set(args.frame)
scene.render.resolution_percentage = 100
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "16"
args.preview.parent.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(args.preview)
bpy.ops.render.render(write_still=True)
print("QUALITY_ARCHIVE_FRAME_RESTORED", args.frame, flush=True)
