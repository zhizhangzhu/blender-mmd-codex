"""Native regression check of reusable head-axis and stage-import repairs."""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from genshin_material_adapt import head_axes
from integrate_reference_duet import import_hall
from verify_duet_integration import snapshot

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--stage", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
scene = bpy.context.scene
frames = [1, 2100, 4200, 8400, 11899]
before = {}
for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    before[frame] = snapshot(scene)
controls = {}
for arm in scene.objects[:]:
    if arm.type == "ARMATURE" and arm.get("performer_id"):
        controls[arm["performer_id"]] = (arm, head_axes(scene, arm))
axes = []
for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    for actor, (arm, controller) in controls.items():
        head = next(bone for bone in arm.pose.bones if bone.mmd_bone.name_j == "頭")
        for name, axis in [("forward", Vector((0, -1, 0))), ("up", Vector((0, 0, 1)))]:
            expected = (
                arm.matrix_world.to_3x3()
                @ head.matrix.to_3x3()
                @ head.bone.matrix_local.to_3x3().inverted()
                @ arm.matrix_world.to_3x3().inverted()
                @ axis
            )
            error = (
                expected.normalized() - Vector(controller[name]).normalized()
            ).length
            assert error < 0.0001, (frame, actor, name, error)
            axes.append({"frame": frame, "actor": actor, "axis": name, "error": error})
root = next(
    obj
    for obj in scene.objects
    if obj.name.startswith("Duet | selected Hesperides stage | reference rebuild")
)
offset = root.location.copy()
root.name = "Duet | selected Hesperides stage"
hall = import_hall(scene, args.stage)
root = bpy.data.objects["Duet | selected Hesperides stage | reference rebuild"]
settings = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "presets/stages/hesperides-ray-reference-v1.json"
    ).read_text(encoding="utf-8")
)
lights = []
for item in settings["lights"]:
    obj = next(
        obj
        for obj in root.children_recursive
        if obj.type == "LIGHT" and obj.name.startswith("Reference | " + item["name"])
    )
    expected = Vector(item["location"]) + offset
    error = (obj.matrix_world.translation - expected).length
    assert error < 0.0001, (obj.name, error)
    lights.append(
        {
            "name": obj.name,
            "position": list(obj.matrix_world.translation),
            "error": error,
        }
    )
for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    assert before[frame] == snapshot(scene), frame
report = {
    "head_axes": axes,
    "stage_lights": lights,
    "import": hall,
    "animation_camera_unchanged_at_five_frames": True,
    "maximum_axis_error": max(item["error"] for item in axes),
    "maximum_fixture_error": max(item["error"] for item in lights),
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "REUSABLE_REPAIRS_VERIFIED",
    report["maximum_axis_error"],
    report["maximum_fixture_error"],
    flush=True,
)
