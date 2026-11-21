"""Isolate baked hair translation errors; render still-only controls."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

register_addons()
SOURCE = Path(
    "D:/codex/output/MMD-Jelly-Eyes-v1/production-v16/Franken_Duet_Goo_Eye_Hair_Stage.blend"
)
ROOT = Path("D:/codex/output/MMD-Ikhor-Hair-Alignment-v1/controls-v3")
ROOT.mkdir(parents=True, exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
arm = bpy.data.objects["Ikhor | mesh | Ikhor_mesh"].find_armature()
names = [b.name for b in arm.pose.bones if b.name.startswith("Bone_Hair")]
scene.frame_set(4290)
bpy.context.view_layer.update()
print("HAIR_SCENE_READY", flush=True)
for marker in scene.timeline_markers:
    marker.camera = None
cam = bpy.data.objects.new(
    "Hair alignment diagnostic", bpy.data.cameras.new("Hair alignment diagnostic")
)
scene.collection.objects.link(cam)
head = scene.objects["Eye hair v1 | ikhor eye L"].matrix_world
eyes = [
    scene.objects["Eye hair v1 | ikhor eye " + side].matrix_world.translation
    for side in ("L", "R")
]
center = (eyes[0] + eyes[1]) * 0.5
forward = (head.to_3x3() @ Vector((0, -1, 0))).normalized()
up = (head.to_3x3() @ Vector((0, 0, 1))).normalized()
cam.location = center + forward * 0.48 + up * 0.035
cam.rotation_euler = (
    (center + up * 0.015 - cam.location).to_track_quat("-Z", "Y").to_euler()
)
cam.data.lens = 65
cam.data.dof.use_dof = False
scene.camera = cam
scene.render.resolution_x = scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 24
scene.render.image_settings.file_format = "JPEG"
original = {n: arm.pose.bones[n].matrix_basis.copy() for n in names}
print("HAIR_CAMERA_READY", list(cam.location), flush=True)
for variant in ("before", "anchored", "rest-hair"):
    if variant != "before":
        count = 0
        for action in bpy.data.actions:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in getattr(strip, "channelbags", ()):
                        for fc in bag.fcurves:
                            if not fc.data_path.startswith('pose.bones["Bone_Hair'):
                                continue
                            if fc.data_path.endswith(".location") or (
                                variant == "rest-hair" and "rotation_" in fc.data_path
                            ):
                                target = (
                                    1
                                    if fc.data_path.endswith("rotation_quaternion")
                                    and fc.array_index == 0
                                    else 0
                                )
                                for k in fc.keyframe_points:
                                    k.co[1] = k.handle_left[1] = k.handle_right[1] = (
                                        target
                                    )
                                fc.update()
                                count += 1
        print("HAIR_CURVES_CORRECTED", variant, count, flush=True)
    scene.frame_set(4290)
    for name in names:
        b = arm.pose.bones[name]
        if variant != "before":
            b.location = (0, 0, 0)
        if variant == "rest-hair":
            b.rotation_quaternion = (1, 0, 0, 0)
            b.rotation_euler = (0, 0, 0)
            b.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    scene.camera = cam
    print(
        "ACTUAL_HAIR_LOCATION",
        variant,
        list(arm.pose.bones[names[0]].location),
        flush=True,
    )
    scene.render.filepath = str(ROOT / f"{variant}-4290.jpg")
    bpy.ops.render.render(write_still=True)
    print("HAIR_ALIGNMENT_CONTROL", variant, flush=True)
(ROOT / "diagnosis.json").write_text(
    json.dumps(
        {
            "source": str(SOURCE),
            "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "bones": names,
            "translation_m": {n: list(original[n].translation) for n in names},
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
