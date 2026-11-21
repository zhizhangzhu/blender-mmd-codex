"""Protect original trim masks and compare restrained versus stronger diffusion."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, color, math, remap
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-MME-Reference-Light-v1")
OUT = ROOT / "production-v3"
OUT.mkdir(exist_ok=False)
SOURCE = ROOT / "production-v2/Franken_MME_Reference_Light_Still.blend"
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
protected = []
for mat in bpy.data.materials:
    if not mat.node_tree or mat.get("performer_id") != "ikhor":
        continue
    tree = mat.node_tree
    start = tree.nodes.get(PREFIX + "MME study retained surface plus key colour")
    surface = tree.nodes.get("Ikhor character | controlled NPR surface")
    if not start or not surface:
        continue
    masks = []
    for suffix in (
        "gold material partition art permission",
        "cyan_gems art permission",
    ):
        n = tree.nodes.get("Ikhor character | " + suffix)
        if n:
            masks.append(
                remap(
                    tree,
                    n.outputs[0],
                    0.001,
                    0.04,
                    0,
                    1,
                    "MME final " + suffix + " exclusion",
                )
            )
    if not masks:
        continue
    mask = masks[0]
    for m in masks[1:]:
        mask = math(tree, "MAXIMUM", mask, m, "MME final trim exclusion union")
    current = surface.inputs["Color"].links[0].from_socket
    original = start.inputs[1].links[0].from_socket
    result = color(
        tree, "MIX", current, original, mask, "MME final original golden and cyan trim"
    )
    tree.links.new(result, surface.inputs["Color"])
    protected.append(mat.name)
project = OUT / "Franken_MME_Clear_Light_Still.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
report = json.loads((SOURCE.parent / "preparation.json").read_text(encoding="utf-8"))
report.update(
    source=str(SOURCE),
    source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    project=str(project),
    project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
    trim_protection_materials=protected,
)
(OUT / "preparation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
bpy.ops.wm.open_mainfile(filepath=str(project), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
pose = {
    o.name: [list(b.matrix[i]) for b in o.pose.bones for i in range(4)]
    for o in scene.objects
    if o.type == "ARMATURE"
}
assert (
    hashlib.sha256(json.dumps(pose, sort_keys=True).encode()).hexdigest()
    == report["pose_hash"]
)
scene.render.filepath = str(OUT / "clear-double-4290.jpg")
bpy.ops.render.render(write_still=True)
comp = scene.compositing_node_group
glow = comp.nodes[PREFIX + "MME study selective bright diffusion"]
outer = comp.nodes["Goo window wrap | soft outer edge diffusion"]
# Save the B alternative with authored camera/markers, before temporary portrait cameras.
glow.inputs["Strength"].default_value = 0.24
glow.inputs["Threshold"].default_value = 1.05
glow.inputs["Size"].default_value = 0.028
outer.inputs["Strength"].default_value = 0.62
outer.inputs["Size"].default_value = 0.055
soft = OUT / "Franken_MME_Soft_Light_Still.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(soft))
report["soft_project"] = str(soft)
report["soft_project_sha256"] = hashlib.sha256(soft.read_bytes()).hexdigest()
report["soft_variant"] = {
    "bright_diffusion_strength": 0.24,
    "threshold": 1.05,
    "size": 0.028,
    "outer_rim_strength": 0.62,
    "outer_rim_size": 0.055,
}
for marker in scene.timeline_markers:
    marker.camera = None


def hero_camera():
    cam = bpy.data.objects.new(
        "MME hero camera", bpy.data.cameras.new("MME hero camera")
    )
    scene.collection.objects.link(cam)
    h = scene.objects["Eye hair v1 | ikhor eye L"]
    rot = h.matrix_world.to_3x3()
    center = (
        h.matrix_world.translation
        + scene.objects["Eye hair v1 | ikhor eye R"].matrix_world.translation
    ) * 0.5
    up = (rot @ Vector((0, 0, 1))).normalized()
    front = (rot @ Vector((0, -1, 0))).normalized()
    target = center - up * 0.18
    cam.location = target + front * 1.1 + up * 0.03
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    cam.data.dof.use_dof = False
    scene.camera = cam
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.render.image_settings.file_format = "JPEG"


hero_camera()
scene.render.filepath = str(OUT / "ikhor-soft-hero-4290.jpg")
bpy.ops.render.render(write_still=True)
glow.inputs["Strength"].default_value = 0.10
glow.inputs["Threshold"].default_value = 1.2
glow.inputs["Size"].default_value = 0.018
outer.inputs["Strength"].default_value = 0.42
outer.inputs["Size"].default_value = 0.042
scene.render.filepath = str(OUT / "ikhor-clear-hero-4290.jpg")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(
    filepath="D:/codex/output/MMD-Citlali-Fringe-Shadow-v1/production-v3/Franken_Citlali_Fringe_Shadow_Still.blend",
    use_scripts=False,
    load_ui=False,
)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
for marker in scene.timeline_markers:
    marker.camera = None
hero_camera()
scene.render.filepath = str(OUT / "ikhor-before-hero-4290.jpg")
bpy.ops.render.render(write_still=True)
report["independent_reopen_passed"] = True
(OUT / "preparation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
shutil.copy2(
    ROOT / "production-v1/before-double-4290.jpg", OUT / "before-double-4290.jpg"
)
print("MME_HERO_STILLS_COMPLETE", flush=True)
