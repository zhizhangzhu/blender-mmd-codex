"""Render the saved v2 opening frame and a full-body lighting diagnostic."""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

register_addons()
root = Path("D:/codex/output/MMD-Goo-Wedding-v2/production-v1")
bpy.ops.wm.open_mainfile(
    filepath=str(root / "Franken_Duet_Goo_Daylight.blend"),
    load_ui=False,
    use_scripts=False,
)
s = bpy.context.scene
mute_file_outputs()
s.frame_set(4140)
s.render.filepath = str(root / "opening-4140.png")
bpy.ops.render.render(write_still=True)
for marker in s.timeline_markers:
    marker.camera = None
s.frame_set(4290)
s.camera = bpy.data.objects["Goo daylight v2 | full body opening"]
s.render.filepath = str(root / "fullbody-light-study-4290.png")
bpy.ops.render.render(write_still=True)
print("GOO_DAYLIGHT_V2_OPENING_STUDY_COMPLETE", flush=True)
