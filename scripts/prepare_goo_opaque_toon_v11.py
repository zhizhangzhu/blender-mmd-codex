"""Restore original opaque hair and add compact toon ramps with face shadow masks."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, ROOT, color, math, node
from prepare_goo_toon_face_hair_study import face_masks
from render_portrait_light_controls import mute_file_outputs

register_addons()
old = ROOT / "production-v5/Franken_Duet_Goo_Eye_Hair_Stage.blend"
production = ROOT / "production-v11"
production.mkdir(exist_ok=False)
masks = production / "shadow-study"
masks.mkdir()
bpy.ops.wm.open_mainfile(filepath=str(old), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
for mat in bpy.data.materials:
    if not mat.node_tree:
        continue
    tree = mat.node_tree
    peek = tree.nodes.get(PREFIX + "eye region bang peek")
    if not peek:
        continue
    for edge in list(peek.inputs[0].links):
        tree.links.remove(edge)
    peek.inputs[0].default_value = 0
    actor = mat["performer_id"]
    form = tree.nodes[PREFIX + "directional head form"].outputs[0]
    ramp = node(tree, "ShaderNodeValToRGB", "compact opaque hair ramp")
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].position = 0.32
    ramp.color_ramp.elements[0].color = (
        (0.62, 0.68, 0.85, 1) if actor == "aksiniya" else (0.72, 0.58, 0.43, 1)
    )
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    tree.links.new(form, ramp.inputs[0])
    surface = (
        tree.nodes.get("Look v3 | NPR surface")
        or tree.nodes["Ikhor character | controlled NPR surface"]
    )
    source = surface.inputs["Color"].links[0].from_socket
    shade = color(
        tree, "MULTIPLY", source, ramp.outputs[0], 1, "compact hair value application"
    )
    tree.links.new(shade, surface.inputs["Color"])
stats = []
for actor, objname, face in (
    ("aksiniya", "阿克西妮娅2_mesh", "颜"),
    ("ikhor", "Ikhor | mesh | Ikhor_mesh", "颜.001"),
):
    shadow, nose, row = face_masks(scene, scene.objects[objname], actor, masks)
    tree = bpy.data.materials[face].node_tree
    uv = node(tree, "ShaderNodeUVMap", "actual face shadow UV")
    uv.uv_map = scene.objects[objname].data.uv_layers.active.name
    sh = node(tree, "ShaderNodeTexImage", "geometry derived hair shadow")
    sh.image = shadow
    no = node(tree, "ShaderNodeTexImage", "authored nose form mask")
    no.image = nose
    tree.links.new(uv.outputs[0], sh.inputs["Vector"])
    tree.links.new(uv.outputs[0], no.inputs["Vector"])
    surface = (
        tree.nodes.get("Look v3 | NPR surface")
        or tree.nodes["Ikhor character | controlled NPR surface"]
    )
    source = surface.inputs["Color"].links[0].from_socket
    shade = color(
        tree,
        "MULTIPLY",
        source,
        (0.93, 0.72, 0.59, 1),
        math(tree, "SUBTRACT", 1, sh.outputs["Color"], "hair shadow coverage"),
        "warm geometric bang shadow",
    )
    shade = color(
        tree,
        "MULTIPLY",
        shade,
        (1, 0.74, 0.60, 1),
        math(tree, "MULTIPLY", no.outputs["Color"], 0.60, "nose shade amount"),
        "warm nose authored form",
    )
    tree.links.new(shade, surface.inputs["Color"])
    stats.append({"actor": actor, **row})
import goo_engine_light_groups

goo_engine_light_groups.sync_light_groups()
project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
scene["eye_see_through"] = (
    "deferred by user; all added hair peek factors disconnected and zero"
)
bpy.ops.wm.save_as_mainfile(filepath=str(project))
prep = json.loads((old.parent / "preparation.json").read_text(encoding="utf-8"))
prep.update(
    source=str(old),
    source_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
    project=str(project),
    project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
    opaque_toon_study=stats,
    eye_see_through="deferred",
)
(production / "preparation.json").write_text(
    json.dumps(prep, ensure_ascii=False, indent=2), encoding="utf-8"
)
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.eevee.taa_render_samples = 16
scene.render.image_settings.file_format = "JPEG"
scene.render.filepath = str(production / "portrait-4290.jpg")
bpy.ops.render.render(write_still=True)
print("OPAQUE_TOON_V11_COMPLETE", flush=True)
