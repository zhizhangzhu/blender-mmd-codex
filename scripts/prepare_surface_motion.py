"""Extend the reviewed surface scene to an eight-second portrait camera study."""

import argparse
import json
import sys
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_tutorial_lab import portrait_camera
from mmd_surface_refine import head_up_controller
from mmd_quality_lab import position_hash, pose_hash

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output-dir", type=Path, required=True)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
args.output_dir.mkdir(parents=True, exist_ok=False)
s = bpy.context.scene
source = bpy.data.filepath
for n in list(s.compositing_node_group.nodes):
    if n.bl_idname == "CompositorNodeOutputFile":
        s.compositing_node_group.nodes.remove(n)
mesh = next(
    o
    for o in s.objects
    if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
)
arm = next(o for o in s.objects if o.type == "ARMATURE")
before = position_hash(mesh)
poses = {f: pose_hash(s, arm, f) for f in [421, 660, 780, 900]}
s.frame_start = 421
s.frame_end = 900
head_up_controller(s)
camera = portrait_camera(s, arm, 421, 900)
assert before == position_hash(mesh) and all(
    pose_hash(s, arm, f) == h for f, h in poses.items()
)
s.render.resolution_x = 720
s.render.resolution_y = 1280
s.render.resolution_percentage = 100
s.eevee.taa_render_samples = 64
s.frame_set(421)
bpy.ops.wm.save_as_mainfile(filepath=str(args.output_dir / "surface-portrait.blend"))
report = {
    "source": source,
    "camera": camera,
    "head_direction_frames": [421, 900],
    "geometry_and_pose_hashes_unchanged": True,
    "quality": {"width": 720, "height": 1280, "samples": 64},
    "surface_settings": json.loads(s["surface_refinement"]),
}
(args.output_dir / "preparation-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("SURFACE_MOTION_PREPARED", json.dumps(report), flush=True)
