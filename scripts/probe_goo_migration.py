"""Read-only Goo runtime/add-on and project compatibility probe; no preferences saved."""
import argparse
import importlib
import json
import sys
import traceback
from pathlib import Path

import bpy

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--project')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
base = Path('C:/Users/Administrator/AppData/Roaming/Blender Foundation/Blender/5.2')
bundled = Path(bpy.app.binary_path).parent / '5.2/scripts/addons'
if (bundled / 'mmd_tools').is_dir():
    sys.path.insert(0, str(bundled))
else:
    sys.path.insert(0, str(base / 'scripts/addons'))
    sys.path.insert(0, str(base / 'extensions/blender_org'))
report = {'version': bpy.app.version_string, 'binary': bpy.app.binary_path,
          'build_hash': bpy.app.build_hash.decode(), 'user_config': bpy.utils.user_resource('CONFIG'), 'addons': {}, 'limits': 'Independent factory-startup process; no preferences saved'}
for name in ('mmd_tools', 'mmd_kafei_tools', 'Paperzhu_animehelper_extension', 'MikuMikuRig'):
    try:
        module = importlib.import_module(name)
        module.register()
        report['addons'][name] = {'registered': True, 'path': module.__file__}
    except Exception:  # noqa: BLE001 - preserve arbitrary add-on registration tracebacks
        report['addons'][name] = {'registered': False, 'error': traceback.format_exc()}
report['goo_node_types'] = [n for n in dir(bpy.types) if n.startswith('ShaderNode') and any(s in n.lower() for s in ('info', 'depth', 'curvature', 'lightgroup'))]
tree = bpy.data.node_groups.new('Goo runtime API probe', 'ShaderNodeTree')
report['native_node_api'] = {}
for kind in ('ShaderNodeShaderInfo', 'ShaderNodeCurvature', 'ShaderNodeLightInfo', 'ShaderNodeBsdfToon', 'ShaderNodeCel', 'ShaderNodeAnimeLine'):
    try:
        node = tree.nodes.new(kind)
        report['native_node_api'][kind] = {'inputs': [(s.name, s.identifier) for s in node.inputs], 'outputs': [(s.name, s.identifier) for s in node.outputs],
                                         'properties': [p.identifier for p in node.bl_rna.properties if not p.is_readonly]}
    except Exception as e:  # noqa: BLE001 - unsupported native node types are probe results
        report['native_node_api'][kind] = {'error': str(e)}
bpy.data.node_groups.remove(tree)
report['render_engines'] = [v.identifier for v in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
if args.project:
    try:
        bpy.ops.wm.open_mainfile(filepath=args.project, load_ui=False, use_scripts=False)
        scene = bpy.context.scene
        scene.frame_set(4290)
        bpy.context.view_layer.update()
        trees = list(bpy.data.node_groups) + [m.node_tree for m in bpy.data.materials if m.use_nodes] + [w.node_tree for w in bpy.data.worlds if w.use_nodes]
        report['project'] = {'path': args.project, 'objects': len(bpy.data.objects), 'materials': len(bpy.data.materials),
                             'actions': [{'name': a.name, 'fcurves': sum(len(bag.fcurves) for layer in a.layers for strip in layer.strips for bag in getattr(strip, 'channelbags', ())) if hasattr(a, 'layers') else len(a.fcurves), 'slots': len(a.slots) if hasattr(a, 'slots') else None} for a in bpy.data.actions],
                             'images': len(bpy.data.images), 'packed': sum(bool(i.packed_file) for i in bpy.data.images),
                             'camera_lens': scene.camera.data.lens if scene.camera else None, 'engine': scene.render.engine,
                             'undefined_nodes': [(t.name, n.name, n.bl_idname) for t in trees if t for n in t.nodes if n.bl_idname == 'NodeUndefined'],
                             'compositor_nodes': len(scene.compositing_node_group.nodes) if getattr(scene, 'compositing_node_group', None) else len(scene.node_tree.nodes) if getattr(scene, 'node_tree', None) else 0}
    except Exception:  # noqa: BLE001 - record forward-compatibility failures without saving
        report['project_error'] = traceback.format_exc()
path = Path(args.output)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('GOO_PROBE_COMPLETE', path, flush=True)
