"""Combine the observed actor-specific fringe settings and render only stills."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-Citlali-Fringe-Shadow-v1")
OUT = ROOT / "production-v3"
OUT.mkdir(exist_ok=False)
SOURCE = ROOT / "production-v2/Franken_Citlali_Fringe_Shadow_Still.blend"
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
tree = bpy.data.materials["颜"].node_tree
image = bpy.data.images.load(
    str(ROOT / "production-v1/aksiniya_narrow_hair_visibility.png"),
    check_existing=False,
)
image.colorspace_settings.name = "Non-Color"
image.pack()
tree.nodes[PREFIX + "geometry derived hair shadow"].image = image
tree.nodes[PREFIX + "warm geometric bang shadow"].inputs[2].default_value = (
    1,
    0.64,
    0.38,
    1,
)
project = OUT / "Franken_Citlali_Fringe_Shadow_Still.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
report = json.loads((SOURCE.parent / "study.json").read_text(encoding="utf-8"))
report.update(
    source=str(SOURCE),
    source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    project=str(project),
    project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
    per_actor={
        "aksiniya": {
            "up": 0.20,
            "shadow_multiplier": [1, 0.64, 0.38],
            "mask_origin": "production-v1",
        },
        "ikhor": {
            "up": 0.35,
            "shadow_multiplier": [0.98, 0.53, 0.25],
            "mask_origin": "production-v2",
        },
    },
)
report.pop("shadow_color_multiplier", None)
first = json.loads((ROOT / "production-v1/study.json").read_text(encoding="utf-8"))
report["actors"] = [
    next(r for r in first["actors"] if r["actor"] == "aksiniya"),
    next(r for r in report["actors"] if r["actor"] == "ikhor"),
]
report["independent_reopen_passed"] = False
(OUT / "study.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
bpy.ops.wm.open_mainfile(filepath=str(project), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
data = {
    o.name: [list(b.matrix[i]) for b in o.pose.bones for i in range(4)]
    for o in scene.objects
    if o.type == "ARMATURE"
}
assert (
    hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    == report["pose_hash"]
)
assert (
    bpy.data.materials["颜"]
    .node_tree.nodes[PREFIX + "geometry derived hair shadow"]
    .image.packed_file
)
assert (
    bpy.data.materials["颜.001"]
    .node_tree.nodes[PREFIX + "geometry derived hair shadow"]
    .image.packed_file
)
report["independent_reopen_passed"] = True
(OUT / "study.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
for marker in scene.timeline_markers:
    marker.camera = None
cam = bpy.data.objects.new(
    "Final fringe still", bpy.data.cameras.new("Final fringe still")
)
scene.collection.objects.link(cam)
cam.data.lens = 65
cam.data.dof.use_dof = False
scene.render.resolution_x = scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 32
scene.render.image_settings.file_format = "JPEG"
for actor in ("ikhor", "aksiniya"):
    helper = scene.objects[PREFIX + actor + " eye L"]
    rot = helper.matrix_world.to_3x3()
    center = (
        helper.matrix_world.translation
        + scene.objects[PREFIX + actor + " eye R"].matrix_world.translation
    ) * 0.5
    up = (rot @ Vector((0, 0, 1))).normalized()
    forward = (rot @ Vector((0, -1, 0))).normalized()
    cam.location = center + forward * 0.55 + up * 0.025
    cam.rotation_euler = (
        (center + up * 0.01 - cam.location).to_track_quat("-Z", "Y").to_euler()
    )
    scene.camera = cam
    scene.render.filepath = str(OUT / f"{actor}-warm-contact-4290.jpg")
    bpy.ops.render.render(write_still=True)
    print("FINAL_FRINGE_STILL", actor, flush=True)
shutil.copy2(
    ROOT / "production-v2/ikhor-before-4290.jpg", OUT / "ikhor-before-4290.jpg"
)
print("FINAL_FRINGE_STILLS_COMPLETE", flush=True)
