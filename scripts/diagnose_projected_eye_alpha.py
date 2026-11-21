"""Measure actual eye-peek, native head shadows and raw/final alpha response."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, ROOT
from render_portrait_light_controls import mute_file_outputs

register_addons()
bpy.ops.wm.open_mainfile(
    filepath=str(ROOT / "production-v5/Franken_Duet_Goo_Eye_Hair_Stage.blend"),
    load_ui=False,
    use_scripts=False,
)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
directory = ROOT / "production-v5/alpha-diagnosis"
directory.mkdir(exist_ok=True)
report = {"materials": {}, "compositor": []}
for material in bpy.data.materials:
    if material.get("performer_id") != "ikhor" or not material.node_tree:
        continue
    tree = material.node_tree
    if tree.nodes.get(PREFIX + "projected bang transparency"):
        report["materials"][material.name] = {
            "surface_render_method": material.surface_render_method,
            "centers": [
                {"name": n.name, "values": [s.default_value for s in n.inputs]}
                for n in tree.nodes
                if n.name.startswith(PREFIX) and n.type == "COMBXYZ"
            ],
            "info": [
                {"name": n.name, "groups": [g.name for g in n.light_groups.groups]}
                for n in tree.nodes
                if n.bl_idname == "ShaderNodeShaderInfo"
            ],
        }
        for output_name, node_name in (
            ("HeadHalfLambert", "Goo daylight v2 | Goo portrait key | ikhor"),
        ):
            if not any(a.name == output_name for a in scene.view_layers[0].aovs):
                aov = scene.view_layers[0].aovs.add()
                aov.name, aov.type = output_name, "VALUE"
            info = tree.nodes.get(node_name)
            if info:
                export = tree.nodes.new("ShaderNodeOutputAOV")
                export.aov_name = output_name
                tree.links.new(
                    info.outputs["Half-lambert factor"], export.inputs["Value"]
                )
tree = scene.compositing_node_group
for n in tree.nodes:
    report["compositor"].append(
        {
            "name": n.name,
            "type": n.bl_idname,
            "inputs": [
                {
                    "name": s.name,
                    "source": s.links[0].from_node.name,
                    "socket": s.links[0].from_socket.name,
                }
                for s in n.inputs
                if s.is_linked
            ],
        }
    )
scene.view_layers[0].update_render_passes()
bpy.context.view_layer.update()
render = next(n for n in tree.nodes if n.type == "R_LAYERS")
outputs = []
for name, kind in (
    ("Image", "RGBA"),
    ("BangPeek", "FLOAT"),
    ("HairVisibility", "FLOAT"),
    ("HeadHalfLambert", "FLOAT"),
):
    out = tree.nodes.new("CompositorNodeOutputFile")
    out.directory = str(directory)
    out.file_name = name + "_####"
    out.format.media_type = "IMAGE"
    out.format.file_format = "PNG"
    out.format.color_depth = "16"
    out.save_as_render = False
    out.file_output_items.clear()
    out.file_output_items.new(kind, name)
    tree.links.new(render.outputs[name], out.inputs[name])
    outputs.append(out)
camera_data = bpy.data.cameras.new("Alpha diagnostic camera")
camera = bpy.data.objects.new(camera_data.name, camera_data)
scene.collection.objects.link(camera)
for marker in scene.timeline_markers:
    marker.camera = None
helpers = [scene.objects[PREFIX + "ikhor eye " + side] for side in ("L", "R")]
center = (
    helpers[0].matrix_world.translation + helpers[1].matrix_world.translation
) * 0.5
forward = helpers[0].matrix_world.to_3x3() @ Vector((0, -1, 0))
camera.location = center + forward.normalized() * 0.4
camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.lens = 72
scene.camera = camera
scene.render.resolution_x = scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 32
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 96
scene.render.filepath = str(directory / "projected-final.jpg")
bpy.ops.render.render(write_still=True)
for out in outputs:
    out.mute = True
for mat in bpy.data.materials:
    if (
        mat.get("performer_id") == "ikhor"
        and mat.node_tree
        and mat.node_tree.nodes.get(PREFIX + "eye region bang peek")
    ):
        socket = mat.node_tree.nodes[PREFIX + "eye region bang peek"].inputs[0]
        for edge in list(socket.links):
            mat.node_tree.links.remove(edge)
        socket.default_value = 0.85
scene.render.filepath = str(directory / "constant85-final.jpg")
bpy.ops.render.render(write_still=True)
out = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
tree.links.new(render.outputs["Image"], out.inputs["Image"])
scene.render.filepath = str(directory / "constant85-raw.jpg")
bpy.ops.render.render(write_still=True)
(directory / "routes.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("PROJECTED_ALPHA_DIAG_COMPLETE", flush=True)
