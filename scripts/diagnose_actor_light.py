"""Measure the actual unclipped native actor illumination and material classes."""

import sys
from pathlib import Path

import bpy

scene = bpy.context.scene
directory = Path(sys.argv[-1])
directory.mkdir(parents=True, exist_ok=False)
for other in bpy.data.scenes:
    if other.compositing_node_group:
        for node in other.compositing_node_group.nodes:
            if node.type == "OUTPUT_FILE":
                node.mute = True
layer = bpy.context.view_layer
for name in ("ActorRawLight", "ActorLightClass"):
    aov = layer.aovs.add()
    aov.name, aov.type = name, "VALUE"
layer.update_render_passes()
for mat in bpy.data.materials:
    if not mat.node_tree or not mat.get("performer_id"):
        continue
    tree = mat.node_tree
    response = tree.nodes.get("Quality | bounded real illumination")
    if not response:
        continue
    raw = tree.nodes.new("ShaderNodeOutputAOV")
    raw.aov_name = "ActorRawLight"
    tree.links.new(response.inputs["Value"].links[0].from_socket, raw.inputs["Value"])
    name = mat.get("source_mmd_material_name", mat.name).split(".")[0]
    cls = tree.nodes.new("ShaderNodeOutputAOV")
    cls.aov_name = "ActorLightClass"
    cls.inputs["Value"].default_value = (
        1
        if name in {"颜", "面1", "面2"}
        else 2
        if name == "肌"
        else 3
        if "发" in name
        else 4
    )
tree = scene.compositing_node_group
render = next(
    n for n in tree.nodes if n.type == "R_LAYERS" and (not n.scene or n.scene == scene)
)
output = tree.nodes.new("CompositorNodeOutputFile")
output.directory, output.file_name = str(directory), "probe_####"
output.format.file_format = "OPEN_EXR_MULTILAYER"
output.format.color_depth = "32"
output.save_as_render = False
for name in ("ActorRawLight", "ActorLightClass"):
    output.file_output_items.new("FLOAT", name)
    tree.links.new(render.outputs[name], output.inputs[name])
scene.frame_set(4290)
scene.render.resolution_percentage = 67
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(directory / "beauty.png")
bpy.ops.render.render(write_still=True)
print("ACTOR_LIGHT_MEASURED", flush=True)
