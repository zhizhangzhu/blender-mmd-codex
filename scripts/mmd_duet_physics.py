"""Bake both performers' native physics for the full source choreography."""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy
from bpy_extras.anim_utils import BakeOptions, bake_action_objects_iter
from bl_ext.blender_org.mmd_tools.core.model import Model

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_final_scene import retime_actions

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output-dir", type=Path, required=True)
p.add_argument("--end", type=int, default=6368)
p.add_argument("--preroll", type=int, default=120)
p.add_argument("--substeps", type=int, default=6)
p.add_argument("--iterations", type=int, default=30)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
args.output_dir.mkdir(parents=True, exist_ok=False)
scene = bpy.context.scene
arms = [o for o in scene.objects if o.type == "ARMATURE" and o.get("performer_id")]
assert len(arms) == 2 and all(not arm.parent.mmd_root.is_built for arm in arms)
start_time = time.time()
retime_actions(1 - args.preroll, 1)
first, last = 1 + args.preroll, args.end + args.preroll
scene.frame_start, scene.frame_end = 1, last
scene.frame_set(1)
report = {
    "source": bpy.data.filepath,
    "preroll": args.preroll,
    "export_range": [first, last],
    "source_fps": 30,
    "performers": [],
}
for arm in arms:
    root = arm.parent
    muted = []
    for bone in arm.pose.bones:
        for c in bone.constraints:
            if c.type == "IK":
                c.mute = True
                muted.append(bone.name)
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    assert "FINISHED" in bpy.ops.mmd_tools.build_rig()
    names = [
        b.name for b in arm.pose.bones if b.constraints.get("mmd_tools_rigid_track")
    ]
    assert names, "No native physical bones: " + arm.name
    report["performers"].append(
        {"id": arm["performer_id"], "physical_bones": names, "muted_ik": muted}
    )
    print("DUET_PHYSICS_BUILT", arm["performer_id"], len(names), flush=True)
world = scene.rigidbody_world
world.substeps_per_frame = args.substeps
world.solver_iterations = args.iterations
world.time_scale = 1
cache = world.point_cache
cache.frame_start, cache.frame_end = 1, last
print(
    "DUET_SIMULATION_START",
    len(world.collection.objects),
    len(world.constraints.objects),
    last,
    flush=True,
)
with bpy.context.temp_override(point_cache=cache):
    result = bpy.ops.ptcache.bake(bake=True)
assert "FINISHED" in result and cache.is_baked
report["simulation_seconds"] = time.time() - start_time
print("DUET_SIMULATION_DONE", report["simulation_seconds"], flush=True)
frames = [first, first + 900, first + 1884, first + 3600, first + 5900, last]
expected = {}
for frame in frames:
    scene.frame_set(frame)
    expected[frame] = {
        arm.name: {
            b.name: b.matrix.copy()
            for b in arm.pose.bones
            if b.name
            in report["performers"][i]["physical_bones"][
                :: max(1, len(report["performers"][i]["physical_bones"]) // 12)
            ]
        }
        for i, arm in enumerate(arms)
    }
pairs = []
for i, arm in enumerate(arms):
    for bone in arm.pose.bones:
        bone.select = bone.name in report["performers"][i]["physical_bones"]
    action = arm.animation_data.action.copy()
    action.name = arm["performer_id"] + " | full body and baked native physics"
    pairs.append((arm, action))
options = BakeOptions(
    only_selected=True,
    do_pose=True,
    do_object=False,
    do_visual_keying=True,
    do_constraint_clear=False,
    do_parents_clear=False,
    do_clean=False,
    do_location=True,
    do_rotation=True,
    do_scale=False,
    do_bbone=False,
    do_custom_props=False,
)
iterator = bake_action_objects_iter(pairs, bake_options=options)
iterator.send(None)
for frame in range(first, last + 1):
    iterator.send(frame)
    if (frame - first) % 300 == 0:
        print(
            "DUET_EXPORT_FRAME", frame, round(time.time() - start_time, 1), flush=True
        )
iterator.send(None)
print("DUET_EXPORT_DONE", flush=True)
garbage = set()
for arm in arms:
    model = Model(arm.parent)
    for group in [
        model.rigidGroupObject(),
        model.jointGroupObject(),
        model.temporaryGroupObject(),
    ]:
        if group:
            garbage.update(group.children_recursive)
            garbage.add(group)
    for bone in arm.pose.bones:
        c = bone.constraints.get("mmd_tools_rigid_track")
        if c:
            bone.constraints.remove(c)
    arm.parent["production_physics_baked"] = True
    arm.parent.mmd_root.is_built = False
bpy.ops.rigidbody.world_remove()
bpy.data.batch_remove(ids=garbage)
errors = []
for frame, actors in expected.items():
    scene.frame_set(frame)
    for arm in arms:
        for name, matrix in actors[arm.name].items():
            now = arm.pose.bones[name].matrix
            errors.append(
                max(abs(now[r][c] - matrix[r][c]) for r in range(4) for c in range(4))
            )
report["maximum_baked_pose_matrix_error"] = max(errors)
assert max(errors) < 0.002, report["maximum_baked_pose_matrix_error"]
scene.frame_start, scene.frame_end = first, last
scene.frame_set(first)
scene["duet_physics_preroll"] = args.preroll
scene["duet_source_first"] = first
bpy.ops.wm.save_as_mainfile(filepath=str(args.output_dir / "duet-portable.blend"))
report.update(
    {
        "substeps": args.substeps,
        "iterations": args.iterations,
        "seconds": time.time() - start_time,
        "runtime_rigidbody_world_removed": scene.rigidbody_world is None,
    }
)
(args.output_dir / "physics-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "DUET_PHYSICS_COMPLETE",
    json.dumps({k: v for k, v in report.items() if k != "performers"}),
    flush=True,
)
