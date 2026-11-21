"""Remove failed global grading; retain restrained light and material changes."""

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

ROOT = Path("D:/codex/output/MMD-MME-Reference-Light-v1")
OUT = ROOT / "production-v2"
OUT.mkdir(exist_ok=False)
SOURCE = ROOT / "production-v1/Franken_MME_Reference_Light_Still.blend"
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
scene.compositing_node_group.nodes["Reference | stage-only reference grade"].inputs[
    "Factor"
].default_value = 0
changes = []
for mat in bpy.data.materials:
    if not mat.node_tree:
        continue
    tree = mat.node_tree
    white = tree.nodes.get(PREFIX + "MME study blue white textile ramp")
    if white:
        white.color_ramp.elements[0].color = (0.68, 0.79, 0.98, 1)
        white.color_ramp.elements[1].color = (1.20, 1.23, 1.28, 1)
        tree.nodes[PREFIX + "MME study cloth palette weight"].inputs[
            1
        ].default_value = 0.18
        changes.append(mat.name)
    if mat.get("look_category") == "trim" or mat.get("ikhor_material_role") == "trim":
        old = tree.nodes.get(PREFIX + "MME study retained surface plus key colour")
        surface = tree.nodes.get("Look v3 | NPR surface") or tree.nodes.get(
            "Ikhor character | controlled NPR surface"
        )
        if old and surface:
            tree.links.new(old.inputs[1].links[0].from_socket, surface.inputs["Color"])
project = OUT / "Franken_MME_Reference_Light_Still.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
report = json.loads((SOURCE.parent / "preparation.json").read_text(encoding="utf-8"))
report.update(
    source=str(SOURCE),
    source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    project=str(project),
    project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
    refinements={
        "failed_stage_grade_disabled": True,
        "white_cloth_reconstruction_weight": 0.18,
        "white_ramp_lit": [1.20, 1.23, 1.28],
        "trim_materials_restored": True,
    },
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
scene.render.filepath = str(OUT / "after-double-4290.jpg")
bpy.ops.render.render(write_still=True)
for marker in scene.timeline_markers:
    marker.camera = None
cam = bpy.data.objects.new(
    "MME refined portrait", bpy.data.cameras.new("MME refined portrait")
)
scene.collection.objects.link(cam)
cam.data.lens = 65
cam.data.dof.use_dof = False
scene.render.resolution_x = scene.render.resolution_y = 900
scene.eevee.taa_render_samples = 32
for actor in ("ikhor", "aksiniya"):
    h = scene.objects["Eye hair v1 | " + actor + " eye L"]
    rot = h.matrix_world.to_3x3()
    center = (
        h.matrix_world.translation
        + scene.objects["Eye hair v1 | " + actor + " eye R"].matrix_world.translation
    ) * 0.5
    up = (rot @ Vector((0, 0, 1))).normalized()
    front = (rot @ Vector((0, -1, 0))).normalized()
    cam.location = center + front * 0.55 + up * 0.025
    cam.rotation_euler = (
        (center + up * 0.01 - cam.location).to_track_quat("-Z", "Y").to_euler()
    )
    scene.camera = cam
    scene.render.filepath = str(OUT / f"{actor}-portrait-4290.jpg")
    bpy.ops.render.render(write_still=True)
    print("MME_REFINED_STILL", actor, flush=True)
shutil.copy2(
    ROOT / "production-v1/before-double-4290.jpg", OUT / "before-double-4290.jpg"
)
print("MME_REFINED_STILLS_COMPLETE", flush=True)
