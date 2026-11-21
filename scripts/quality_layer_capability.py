"""Small native EEVEE test for sky suppression and collection holdout."""

import json
import sys
from pathlib import Path

import bpy

root = Path(sys.argv[sys.argv.index("--") + 1])
root.mkdir(parents=True, exist_ok=True)
scene = bpy.data.scenes.new("Layer capability only")
bpy.context.window.scene = scene
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 8
scene.render.resolution_x = scene.render.resolution_y = 128
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
world = bpy.data.worlds.new("Capability world")
world.use_nodes = True
next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs[
    "Color"
].default_value = (0.2, 0.3, 0.5, 1)
scene.world = world
bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
actor = bpy.context.object
actor.name = "Visible actor"
mat = bpy.data.materials.new("Red emission")
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()
emission = nodes.new("ShaderNodeEmission")
emission.inputs[0].default_value = (1, 0.1, 0.1, 1)
out = nodes.new("ShaderNodeOutputMaterial")
mat.node_tree.links.new(emission.outputs[0], out.inputs["Surface"])
actor.data.materials.append(mat)
data = bpy.data.cameras.new("Capability camera")
camera = bpy.data.objects.new("Capability camera", data)
scene.collection.objects.link(camera)
camera.location = (0, -6, 0)
camera.rotation_euler = (1.5707963267948966, 0, 0)
scene.camera = camera
layer = scene.view_layers[0]
results = []
for sky in [True, False]:
    layer.use_sky = sky
    scene.render.filepath = str(root / f"sky-{sky}.png")
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(scene.render.filepath, check_existing=False)
    pixels = list(im.pixels)
    results.append(
        {
            "sky": sky,
            "corner": pixels[:4],
            "center": pixels[(64 * 128 + 64) * 4 : (64 * 128 + 64) * 4 + 4],
        }
    )
    bpy.data.images.remove(im)
(root / "capability.json").write_text(json.dumps(results, indent=2))
print("LAYER_CAPABILITY", json.dumps(results), flush=True)
