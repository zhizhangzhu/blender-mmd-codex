"""Reopen the integrated master, validate scene persistence and archive naming."""

import argparse
import json
import sys
from pathlib import Path

import bpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
args.output_dir.mkdir(parents=True, exist_ok=False)
scene = bpy.context.scene
assert bpy.data.scenes.get("Quality | native actor RGBA")
assert bpy.data.scenes.get("Quality | clean stage")
images = [im for im in bpy.data.images if im.source == "FILE"]
assert all(im.packed_file for im in images)
node = scene.compositing_node_group.nodes["Quality | scene-linear EXR archive"]
node.file_name = "duet_####"
scene.frame_set(4140)
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "16"
scene.render.filepath = str(args.output_dir / "reopened-4140.png")
bpy.ops.render.render(write_still=True)
archive = Path(node.directory) / "duet_4140.exr"
assert archive.is_file(), list(Path(node.directory).glob("*.exr"))
project = args.output_dir / "Franken_Duet_Quality_Master.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
(args.output_dir / "reopen-verification.json").write_text(
    json.dumps(
        {
            "native_scenes_retained": True,
            "all_file_images_packed": True,
            "file_image_count": len(images),
            "frame_numbered_archive": str(archive),
            "project": str(project),
        },
        indent=2,
    ),
    encoding="utf-8",
)
print("QUALITY_MASTER_REOPENED", str(project), flush=True)
