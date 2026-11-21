"""Build PMX rigid bodies, simulate sequentially, and export portable pose keys.

Run in Blender after loading the import baseline. Uses an in-memory native cache
to avoid a scene-cache disk-toggle crash observed in Blender 5.2.2. Saves only a
new output file; --export-start/--export-end make it independent of live physics.
"""

import argparse
import bpy
import json
import sys
import time
from pathlib import Path
from collections import Counter

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output-dir", type=Path, required=True)
p.add_argument("--end", type=int, default=6368)
p.add_argument("--substeps", type=int, default=4)
p.add_argument("--iterations", type=int, default=20)
p.add_argument("--export-start", type=int)
p.add_argument("--export-end", type=int)
p.add_argument("--sim-start", type=int, default=1)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
args.output_dir.mkdir(parents=True, exist_ok=False)
scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
root = arm.parent
scene.frame_set(args.sim_start)
muted = []
for bone in arm.pose.bones:
    for constraint in bone.constraints:
        if constraint.type == "IK":
            constraint.mute = True
            muted.append(bone.name)
bpy.ops.object.select_all(action="DESELECT")
root.select_set(True)
bpy.context.view_layer.objects.active = root
result = bpy.ops.mmd_tools.build_rig()
assert "FINISHED" in result and root.mmd_root.is_built
world = scene.rigidbody_world
world.substeps_per_frame = args.substeps
world.solver_iterations = args.iterations
world.time_scale = 1.0
cache = world.point_cache
cache.frame_start = args.sim_start
cache.frame_end = args.end
scene.frame_start, scene.frame_end = args.sim_start, args.end
path = args.output_dir / "physics-baked.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(path))
# Blender 5.2.2 crashes in BKE_ptcache_toggle_disk_cache for this scene-level
# rigid body cache. Keep the native in-memory cache and export motion later.
start = time.time()
print("PHYSICS_BAKE_START", len(world.collection.objects), args.end, flush=True)
with bpy.context.temp_override(point_cache=cache):
    result = bpy.ops.ptcache.bake(bake=True)
print("PHYSICS_BAKE_DONE", result, cache.is_baked, time.time() - start, flush=True)
assert cache.is_baked
names = [
    b.name
    for b in arm.pose.bones
    if any(
        c.type in {"COPY_TRANSFORMS", "COPY_ROTATION"} and c.name.startswith("mmd")
        for c in b.constraints
    )
]
rigids = [o for o in scene.objects if getattr(o, "mmd_type", "") == "RIGID_BODY"]
samples = []
for frame in sorted(
    set(
        [
            args.sim_start,
            min(args.sim_start + 60, args.end),
            min(args.sim_start + 180, args.end),
            args.end,
        ]
    )
):
    scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    dynamic = [o for o in rigids if o.mmd_rigid.type != "0"]
    coords = [o.evaluated_get(graph).matrix_world.translation for o in dynamic]
    samples.append(
        {
            "frame": frame,
            "max_abs_coordinate": max(abs(v) for pt in coords for v in pt),
            "head": list(arm.pose.bones["頭"].matrix.translation),
            "physics_bones": {
                n: list(arm.pose.bones[n].matrix.translation)
                for n in ["qun_0_5", "pj_0_5", "Bone_HairB01_L"]
                if n in arm.pose.bones
            },
        }
    )
if args.export_start is not None:
    first, last = args.export_start, args.export_end or args.end
    physical_bones = [
        b for b in arm.pose.bones if "mmd_tools_rigid_track" in b.constraints
    ]
    arm.animation_data.action = arm.animation_data.action.copy()
    arm.animation_data.action.name = (
        "Aksiniya | body and baked native hair-cloth physics"
    )
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    for b in arm.pose.bones:
        b.select = False
    for b in physical_bones:
        b.select = True
    bpy.ops.object.mode_set(mode="POSE")
    print("BONE_EXPORT_START", len(physical_bones), first, last, flush=True)
    result = bpy.ops.nla.bake(
        frame_start=first,
        frame_end=last,
        step=1,
        only_selected=True,
        visual_keying=True,
        clear_constraints=False,
        use_current_action=True,
        clean_curves=False,
        bake_types={"POSE"},
        channel_types={"LOCATION", "ROTATION"},
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    assert "FINISHED" in result
    for b in physical_bones:
        b.constraints["mmd_tools_rigid_track"].mute = True
    world.enabled = False
    scene.frame_start, scene.frame_end = first, last
    print("BONE_EXPORT_DONE", len(physical_bones), flush=True)
scene.frame_set(args.export_start or 1)
bpy.ops.wm.save_as_mainfile(filepath=str(path))
report = {
    "built": root.mmd_root.is_built,
    "baked": cache.is_baked,
    "cache_info": cache.info,
    "rigid_bodies": len(rigids),
    "types": dict(Counter(o.mmd_rigid.type for o in rigids)),
    "constraints": len(world.constraints.objects),
    "substeps": args.substeps,
    "iterations": args.iterations,
    "frame_range": [args.sim_start, args.end],
    "muted_ik": muted,
    "seconds": time.time() - start,
    "samples": samples,
}
report["portable_bone_export"] = (
    {
        "range": [args.export_start, args.export_end],
        "physics_bone_count": len(physical_bones),
    }
    if args.export_start is not None
    else None
)
(args.output_dir / "physics-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("PHYSICS_REPORT", json.dumps(report, ensure_ascii=False), flush=True)
