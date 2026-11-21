"""Factory-only positive control for Goo direct volume light support."""

import json
from pathlib import Path

import bpy
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 320
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 16
scene.eevee.use_volumetric_shadows = True
scene.world = bpy.data.worlds.new("Black")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
bpy.ops.object.camera_add(location=(5, -7, 3))
camera = bpy.context.object
camera.rotation_euler = (
    (Vector((0, 0, 1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
)
camera.data.type, camera.data.ortho_scale = "ORTHO", 7
scene.camera = camera
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1.5))
bpy.context.object.scale = (3, 3, 2)
material = bpy.data.materials.new("Volume positive control")
material.use_nodes = True
tree = material.node_tree
tree.nodes.clear()
scatter = tree.nodes.new("ShaderNodeVolumeScatter")
scatter.inputs["Density"].default_value = 0.06
out = tree.nodes.new("ShaderNodeOutputMaterial")
tree.links.new(scatter.outputs[0], out.inputs["Volume"])
bpy.context.object.data.materials.append(material)
bpy.ops.object.light_add(type="SPOT", location=(-2, 1, 4))
light = bpy.context.object
light.data.energy = 3000
light.data.spot_size, light.data.spot_blend = 0.4, 0.3
light.data.volume_factor = 5
light.rotation_euler = (
    (Vector((1, 0, 0)) - light.location).to_track_quat("-Z", "Y").to_euler()
)
import goo_engine_light_groups

goo_engine_light_groups.sync_light_groups()
folder = Path("D:/codex/temp/MMD-Goo-Rim-Glow-v1/volume-positive")
folder.mkdir(exist_ok=False)
for label, factor in (("diffuse0", 0), ("diffuse1", 1)):
    light.data.diffuse_factor = factor
    scene.render.filepath = str(folder / (label + ".png"))
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("VOLUME_POSITIVE", label, flush=True)
(folder / "settings.json").write_text(
    json.dumps(
        {
            "build": bpy.app.build_hash.decode(),
            "light_bits": list(light.data.light_group_bits),
            "material_bits": list(material.light_group_bits),
        }
    ),
    encoding="utf-8",
)
