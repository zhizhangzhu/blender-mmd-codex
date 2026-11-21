"""Restore original hair bind pose in a still-only, independently saved project."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX
from prepare_goo_toon_face_hair_study import face_masks
from render_portrait_light_controls import mute_file_outputs

register_addons()
SOURCE = Path(
    "D:/codex/output/MMD-Jelly-Eyes-v1/production-v16/Franken_Duet_Goo_Eye_Hair_Stage.blend"
)
OUT = Path("D:/codex/output/MMD-Ikhor-Hair-Alignment-v1/production-v1")
OUT.mkdir(exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
obj = bpy.data.objects["Ikhor | mesh | Ikhor_mesh"]
arm = obj.find_armature()
old = arm.animation_data.action
fixed = old.copy()
fixed.name = "Ikhor | hair bind restoration | still only"
arm.animation_data.action = fixed
names = [b.name for b in arm.pose.bones if b.name.startswith("Bone_Hair")]


def signature(action, exclude_hair=False):
    rows = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                for fc in bag.fcurves:
                    if exclude_hair and fc.data_path.startswith(
                        'pose.bones["Bone_Hair'
                    ):
                        continue
                    rows.append(
                        [
                            fc.data_path,
                            fc.array_index,
                            [
                                [*k.co, *k.handle_left, *k.handle_right]
                                for k in fc.keyframe_points
                            ],
                        ]
                    )
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


before = signature(old, True)
changed = 0
for layer in fixed.layers:
    for strip in layer.strips:
        for bag in getattr(strip, "channelbags", ()):
            for fc in bag.fcurves:
                if not fc.data_path.startswith('pose.bones["Bone_Hair'):
                    continue
                target = (
                    1
                    if fc.data_path.endswith(".scale")
                    or (
                        fc.data_path.endswith(".rotation_quaternion")
                        and fc.array_index == 0
                    )
                    else 0
                )
                for k in fc.keyframe_points:
                    k.co[1] = k.handle_left[1] = k.handle_right[1] = target
                fc.update()
                changed += 1
assert signature(fixed, True) == before
scene.frame_set(4290)
bpy.context.view_layer.update()
for name in names:
    b = arm.pose.bones[name]
    assert b.location.length < 1e-6 and b.matrix_basis.to_quaternion().angle < 1e-4, (
        name
    )
shadow, nose, stats = face_masks(scene, obj, "ikhor", OUT)
tree = bpy.data.materials["颜.001"].node_tree
tree.nodes[PREFIX + "geometry derived hair shadow"].image = shadow
shadow.pack()
bpy.data.images.remove(nose)
scene["ikhor_hair_alignment_scope"] = (
    "Static4290: original hair bind restored; bad hair bake isolated; no new physics or video validation"
)
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.eevee.taa_render_samples = 24
scene.render.image_settings.file_format = "JPEG"
scene.render.filepath = str(OUT / "scene-4290.jpg")
project = OUT / "Ikhor_Hair_Aligned_Still.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
report = {
    "source": str(SOURCE),
    "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "project": str(project),
    "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
    "hair_bones": names,
    "changed_curves": changed,
    "non_hair_channels_preserved": signature(fixed, True) == before,
    "original_action_retained": old.name,
    "face_shadow_recomputed_for_frame": 4290,
    "scope": "still only; hair bind pose follows head; no new hair physics or video",
    "shadow_stats": stats,
}
(OUT / "repair.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
# Independent reopen before rendering; diagnostic cameras are never saved into the master.
bpy.ops.wm.open_mainfile(filepath=str(project), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
arm = bpy.data.objects["Ikhor | mesh | Ikhor_mesh"].find_armature()
assert all(arm.pose.bones[n].location.length < 1e-6 for n in names)
report["reopened_bind_alignment_passed"] = True
(OUT / "repair.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
bpy.ops.render.render(write_still=True)
for marker in scene.timeline_markers:
    marker.camera = None
cam = bpy.data.objects.new(
    "Hair corrected closeup", bpy.data.cameras.new("Hair corrected closeup")
)
scene.collection.objects.link(cam)
helper = scene.objects["Eye hair v1 | ikhor eye L"]
center = (
    helper.matrix_world.translation
    + scene.objects["Eye hair v1 | ikhor eye R"].matrix_world.translation
) * 0.5
rot = helper.matrix_world.to_3x3()
forward = (rot @ Vector((0, -1, 0))).normalized()
up = (rot @ Vector((0, 0, 1))).normalized()
right = (rot @ Vector((1, 0, 0))).normalized()
cam.data.lens = 50
cam.data.dof.use_dof = False
scene.render.resolution_x = scene.render.resolution_y = 1000
scene.eevee.taa_render_samples = 32
for label, side in (("front", 0), ("three-quarter", 0.26)):
    cam.location = center + forward * 0.70 + up * 0.045 + right * side
    cam.rotation_euler = (
        (center + up * 0.035 - cam.location).to_track_quat("-Z", "Y").to_euler()
    )
    scene.camera = cam
    scene.render.filepath = str(OUT / f"hair-{label}-4290.jpg")
    bpy.ops.render.render(write_still=True)
    print("HAIR_FIXED_STILL", label, flush=True)
