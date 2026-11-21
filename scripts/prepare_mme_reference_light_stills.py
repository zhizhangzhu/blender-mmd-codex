"""MME-inspired light/palette/diffusion adaptation; native Goo stills only."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import color, math, node, remap
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-MME-Reference-Light-v1")
OUT = ROOT / "production-v1"
OUT.mkdir(parents=True, exist_ok=False)
SOURCE = Path(
    "D:/codex/output/MMD-Citlali-Fringe-Shadow-v1/production-v3/Franken_Citlali_Fringe_Shadow_Still.blend"
)
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()


def pose_hash():
    return hashlib.sha256(
        json.dumps(
            {
                o.name: [list(b.matrix[i]) for b in o.pose.bones for i in range(4)]
                for o in scene.objects
                if o.type == "ARMATURE"
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()


before = pose_hash()
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 24
scene.render.image_settings.file_format = "JPEG"
scene.render.filepath = str(OUT / "before-double-4290.jpg")
bpy.ops.render.render(write_still=True)
lights = []
for actor in ("aksiniya", "ikhor"):
    helper = scene.objects["Eye hair v1 | " + actor + " eye L"]
    rot = helper.matrix_world.to_3x3()
    center = (
        helper.matrix_world.translation
        + scene.objects["Eye hair v1 | " + actor + " eye R"].matrix_world.translation
    ) * 0.5
    forward = (rot @ Vector((0, -1, 0))).normalized()
    right = (rot @ Vector((1, 0, 0))).normalized()
    up = (rot @ Vector((0, 0, 1))).normalized()
    for name, watts, size, offset in (
        (f"Reference duet | {actor} | key", 560, 0.80, (-0.70, 0.95, 0.85)),
        (f"Eye hair v1 | {actor} directional head key", 220, 0.55, (-0.55, 0.95, 0.75)),
    ):
        lamp = scene.objects[name]
        lamp.location = (
            center + right * offset[0] + forward * offset[1] + up * offset[2]
        )
        lamp.rotation_euler = (
            (center - lamp.location).to_track_quat("-Z", "Y").to_euler()
        )
        lamp.data.energy = watts
        lamp.data.size = size
        lamp.data.color = (1, 0.94, 0.91)
        lights.append(
            {
                "name": name,
                "watts": watts,
                "size": size,
                "position": list(lamp.location),
            }
        )
for name, gain in (
    ("Softlight | front soft fill", 0.42),
    ("Softlight | hall ceiling bounce", 0.70),
    ("Portrait day stage | high diffuse bounce", 0.72),
):
    lamp = scene.objects.get(name)
    if lamp:
        lamp.data.energy *= gain
import goo_engine_light_groups

goo_engine_light_groups.sync_light_groups()
bpy.context.view_layer.update()
materials = []
for mat in bpy.data.materials:
    actor = mat.get("performer_id")
    if (
        actor not in ("aksiniya", "ikhor")
        or not mat.node_tree
        or mat.name.startswith("mmd_edge")
    ):
        continue
    tree = mat.node_tree
    surface = tree.nodes.get("Look v3 | NPR surface") or tree.nodes.get(
        "Ikhor character | controlled NPR surface"
    )
    if not surface or not surface.inputs["Color"].is_linked:
        continue
    role = (
        mat.get("look_category", "")
        if actor == "aksiniya"
        else mat.get("ikhor_material_role", "")
    )
    face = mat.name in ("颜", "颜.001")
    skin = face or "skin" in role or mat.name in ("首", "手", "首.001", "手.001")
    if mat.name in ("目", "目.002", "目2") or any(
        x in mat.name for x in ("睫", "眉", "口")
    ):
        continue
    info = next(
        (
            n
            for n in tree.nodes
            if n.bl_idname == "ShaderNodeShaderInfo" and n.use_own_light_groups
        ),
        None,
    )
    if info is None:
        continue
    old = surface.inputs["Color"].links[0].from_socket
    form = remap(
        tree,
        info.outputs["Half-lambert factor"],
        0.22,
        0.82,
        0,
        1,
        "MME study directional key ramp",
    )
    ramp = node(tree, "ShaderNodeValToRGB", "MME study warm lit cool shadow")
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].position = 0.23
    ramp.color_ramp.elements[1].position = 0.70
    if skin:
        dark = (1.02, 0.82, 0.89, 1)
        lit = (1.06, 1.015, 1.02, 1)
        amount = 0.56
    elif role == "hair":
        dark = (0.82, 0.79, 0.91, 1)
        lit = (1.12, 1.08, 1.04, 1)
        amount = 0.40
    else:
        dark = (0.64, 0.77, 1.02, 1)
        lit = (1.13, 1.19, 1.30, 1)
        amount = 0.60
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].color = lit
    tree.links.new(form, ramp.inputs[0])
    result = color(
        tree,
        "MULTIPLY",
        old,
        ramp.outputs[0],
        amount,
        "MME study retained surface plus key colour",
    )
    # Neutral bright cloth gets a separate base/highlight palette, preserving golden trim and printed motifs.
    if not skin and role != "hair" and tree.nodes.get("mmd_shader"):
        base = tree.nodes["mmd_shader"].outputs["Color"]
        hsv = node(
            tree, "ShaderNodeSeparateColor", "MME study white textile permission"
        )
        hsv.mode = "HSV"
        tree.links.new(base, hsv.inputs[0])
        neutral = remap(
            tree, hsv.outputs[1], 0.10, 0.32, 1, 0, "MME study exclude golden trim"
        )
        bright = remap(
            tree, hsv.outputs[2], 0.45, 0.78, 0, 1, "MME study preserve printed details"
        )
        permission = math(
            tree, "MULTIPLY", neutral, bright, "MME study white cloth mask"
        )
        white = node(tree, "ShaderNodeValToRGB", "MME study blue white textile ramp")
        white.color_ramp.interpolation = "EASE"
        white.color_ramp.elements[0].position = 0.23
        white.color_ramp.elements[0].color = (0.58, 0.73, 1.0, 1)
        white.color_ramp.elements[1].position = 0.70
        white.color_ramp.elements[1].color = (1.65, 1.68, 1.76, 1)
        tree.links.new(form, white.inputs[0])
        clean = color(
            tree,
            "MULTIPLY",
            base,
            white.outputs[0],
            1,
            "MME study cloth base with retained texture",
        )
        result = color(
            tree,
            "MIX",
            result,
            clean,
            math(tree, "MULTIPLY", permission, 0.48, "MME study cloth palette weight"),
            "MME study separated white cloth response",
        )
    tree.links.new(result, surface.inputs["Color"])
    materials.append({"name": mat.name, "role": role, "skin": skin})
# Existing actor-protected stage correction receives a cool-blue background palette.
comp = scene.compositing_node_group
grade = comp.nodes.get("Reference | stage-only reference grade")
if grade:
    grade.inputs["Factor"].default_value = 0.70
    for index, pairs in enumerate(
        (
            ((0.18, 0.15), (0.55, 0.51)),
            ((0.18, 0.20), (0.55, 0.57)),
            ((0.18, 0.24), (0.55, 0.64)),
        )
    ):
        for x, y in pairs:
            grade.mapping.curves[index].points.new(x, y)
    grade.mapping.update()
for name, strength, size in (
    ("Goo window wrap | tight white edge bloom", 1.6, 0.014),
    ("Goo window wrap | soft outer edge diffusion", 0.42, 0.042),
):
    n = comp.nodes[name]
    n.inputs["Strength"].default_value = strength
    n.inputs["Size"].default_value = size
render = next(n for n in comp.nodes if n.type == "R_LAYERS")
tone = comp.nodes["Goo Tyndall | compress highlights after glow"]
previous = tone.inputs[1].links[0].from_socket
glow = node(comp, "CompositorNodeGlare", "MME study selective bright diffusion")
for key, val in (
    ("Type", "Fog Glow"),
    ("Quality", "High"),
    ("Threshold", 1.2),
    ("Strength", 0.10),
    ("Size", 0.018),
):
    glow.inputs[key].default_value = val
comp.links.new(render.outputs["Image"], glow.inputs["Image"])
combined = color(
    comp,
    "ADD",
    previous,
    glow.outputs["Glare"],
    1,
    "MME study diffusion before highlight shoulder",
)
comp.links.new(combined, tone.inputs[1])
comp.links.new(combined, comp.nodes["Goo Tyndall | linear luminance"].inputs[0])
assert pose_hash() == before
project = OUT / "Franken_MME_Reference_Light_Still.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
report = {
    "source": str(SOURCE),
    "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "project": str(project),
    "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
    "scope": "Static4290 only; MME-inspired native Goo adaptation, not original .fx execution",
    "pose_hash": before,
    "lights": lights,
    "materials": materials,
    "physics_changed": False,
    "video_created": False,
}
(OUT / "preparation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
bpy.ops.wm.open_mainfile(filepath=str(project), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
assert pose_hash() == before
report["independent_reopen_passed"] = True
(OUT / "preparation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
scene.render.filepath = str(OUT / "after-double-4290.jpg")
bpy.ops.render.render(write_still=True)
for marker in scene.timeline_markers:
    marker.camera = None
cam = bpy.data.objects.new(
    "MME light portrait", bpy.data.cameras.new("MME light portrait")
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
    print("MME_REFERENCE_STILL", actor, flush=True)
print("MME_REFERENCE_STILLS_COMPLETE", flush=True)
