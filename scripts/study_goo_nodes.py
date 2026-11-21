"""Render a small actual Goo shader/light-group study, separate from production."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

root = Path('D:/codex/output/MMD-Goo-Wedding-v1/studies')
root.mkdir(parents=True, exist_ok=True)
report = {'addons': register_addons()}
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 16
scene.render.resolution_x, scene.render.resolution_y = 1280, 600
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'Standard'
scene.world.color = (.025, .025, .025)
scene.render.image_settings.file_format = 'PNG'
scene.render.use_compositing = False
bpy.ops.object.light_add(type='SUN', location=(-4, -4, 7))
sun = bpy.context.object
sun.data.energy = 3
sun.rotation_euler = (Vector((0, 0, 0)) - sun.location).to_track_quat('-Z', 'Y').to_euler()
sun.data.light_groups.groups.add().name = 'Study key'
sun.data.light_groups.use_default = False
bpy.ops.object.camera_add(location=(0, -12, 6.8))
cam = bpy.context.object
cam.rotation_euler = (Vector((0, 0, .2)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.type, cam.data.ortho_scale = 'ORTHO', 10
scene.camera = cam

for index, kind in enumerate(('Half-lambert factor', 'Cast Shadows', 'Scene Rim', 'Toon combination')):
    x = (index - 1.5) * 2.35
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=.8, location=(x, 0, 1))
    sphere = bpy.context.object
    for p in sphere.data.polygons:
        p.use_smooth = True
    mat = bpy.data.materials.new(kind)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    info = tree.nodes.new('ShaderNodeShaderInfo')
    info.use_own_light_groups = True
    info.light_groups.use_default = False
    info.light_groups.groups.add().name = 'Study key'
    curvature = tree.nodes.new('ShaderNodeCurvature')
    curvature.inputs['Sample Radius'].default_value = 2
    curvature.inputs['Thickness'].default_value = .08
    out = tree.nodes.new('ShaderNodeOutputMaterial')
    emission = tree.nodes.new('ShaderNodeEmission')
    value = info.outputs[kind] if kind in info.outputs else curvature.outputs['Scene Rim']
    if kind == 'Toon combination':
        ramp = tree.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = .26
        ramp.color_ramp.elements[0].color = (.12, .18, .4, 1)
        ramp.color_ramp.elements[1].position = .66
        ramp.color_ramp.elements[1].color = (.74, .84, 1, 1)
        tree.links.new(info.outputs['Half-lambert factor'], ramp.inputs[0])
        multiply = tree.nodes.new('ShaderNodeMixRGB')
        multiply.blend_type = 'MULTIPLY'
        multiply.inputs[0].default_value = .55
        tree.links.new(ramp.outputs[0], multiply.inputs[1])
        tree.links.new(info.outputs['Cast Shadows'], multiply.inputs[2])
        value = multiply.outputs[0]
    tree.links.new(value, emission.inputs[0])
    tree.links.new(emission.outputs[0], out.inputs[0])
    sphere.data.materials.append(mat)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x-.4, -.45, 1.8), scale=(.22, .22, .45))

bpy.ops.mesh.primitive_plane_add(size=200)
plane = bpy.context.object
mat = bpy.data.materials.new('Study floor')
mat.diffuse_color = (.18, .21, .3, 1)
plane.data.materials.append(mat)
import goo_engine_light_groups

goo_engine_light_groups.sync_light_groups()
scene.render.filepath = str(root / 'native-shader-info-curvature.png')
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'Goo_Native_Node_Study.blend'))
bpy.ops.render.render(write_still=True)
report['actual_outputs'] = ['Half-lambert factor', 'Cast Shadows', 'Scene Rim', 'Combined toon; one named light group']
report['limits'] = 'Small primitive study; not character adaptation or MME equivalence.'
(root / 'study.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('GOO_NODE_STUDY_RENDERED', flush=True)
