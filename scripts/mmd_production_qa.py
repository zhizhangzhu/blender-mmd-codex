"""Reopen verification and representative-frame QA for a baked production file."""

import argparse
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output-dir", type=Path, required=True)
p.add_argument("--samples", type=int, default=20)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
args.output_dir.mkdir(parents=True, exist_ok=False)
s = bpy.context.scene
arm = next(o for o in s.objects if o.type == "ARMATURE")
head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
meshes = [
    o
    for o in s.objects
    if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
]
frames = sorted(
    set(
        round(s.frame_start + i * (s.frame_end - s.frame_start) / (args.samples - 1))
        for i in range(args.samples)
    )
)
checks = []
for frame in frames:
    s.frame_set(frame)
    hp = world_to_camera_view(s, s.camera, arm.matrix_world @ head.matrix.translation)
    points = [
        o.matrix_world @ Vector(v)
        for m in meshes
        for o in [m.evaluated_get(bpy.context.evaluated_depsgraph_get())]
        for v in o.bound_box
    ]
    max_abs = max(abs(v) for point in points for v in point)
    check = {
        "frame": frame,
        "head_in_frame": 0 < hp.x < 1 and 0 < hp.y < 1 and hp.z > 0,
        "head_projection": list(hp),
        "maximum_mesh_coordinate": max_abs,
        "physics_rotations": {
            name: list(arm.pose.bones[name].rotation_quaternion)
            for name in ["qun_0_5", "pj_0_5", "Bone_HairB01_L"]
            if name in arm.pose.bones
        },
    }
    checks.append(check)
    s.render.resolution_percentage = 25
    s.render.image_settings.media_type = "IMAGE"
    s.render.image_settings.file_format = "PNG"
    s.render.filepath = str(args.output_dir / f"frame-{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
images = [i for i in bpy.data.images if i.source == "FILE"]
report = {
    "project": bpy.data.filepath,
    "fps": s.render.fps,
    "resolution": [s.render.resolution_x, s.render.resolution_y],
    "frames": [s.frame_start, s.frame_end],
    "seconds": (s.frame_end - s.frame_start + 1) / s.render.fps,
    "packed_file_images": sum(bool(i.packed_file) for i in images),
    "file_images": len(images),
    "rigid_world_present": s.rigidbody_world is not None,
    "live_physics_tracks": sum(
        c.name == "mmd_tools_rigid_track" for b in arm.pose.bones for c in b.constraints
    ),
    "baked_action": arm.animation_data.action.name,
    "samples": checks,
    "checks_passed": all(
        x["head_in_frame"]
        and math.isfinite(x["maximum_mesh_coordinate"])
        and x["maximum_mesh_coordinate"] < 10
        for x in checks
    ),
    "audio_strips": [
        {
            "name": a.name,
            "start": a.frame_final_start,
            "end": a.frame_final_end,
            "sound": a.sound.name,
        }
        for a in s.sequence_editor.strips
        if a.type == "SOUND"
    ]
    if s.sequence_editor
    else [],
}
(args.output_dir / "qa-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "PRODUCTION_QA",
    json.dumps({k: v for k, v in report.items() if k != "samples"}, ensure_ascii=False),
    flush=True,
)
assert report["checks_passed"] and report["live_physics_tracks"] == 0
