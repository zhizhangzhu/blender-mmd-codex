"""Migrate the pinned daylight wedding to Goo, reusing the existing look and native Goo outputs."""
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from portrait_key_fill import TARGETS
from render_portrait_light_controls import mute_file_outputs

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('D:/codex/output/MMD-Goo-Wedding-v1/production-v1')
PREFIX = 'Goo portrait | '


def node(tree, kind, name):
    result = tree.nodes.new(kind)
    result.name = result.label = PREFIX + name
    return result


def main():
    spec = json.loads((REPO / 'presets/lighting/goo-wedding-v1.json').read_text(encoding='utf-8'))
    source = Path(spec['source'])
    assert hashlib.sha256(source.read_bytes()).hexdigest() == spec['source_sha256']
    ROOT.mkdir(parents=True, exist_ok=False)
    report = {'source': str(source), 'source_sha256': spec['source_sha256'], 'settings': spec,
              'addons': register_addons(), 'runtime': bpy.app.binary_path, 'runtime_build': bpy.app.build_hash.decode(),
              'runtime_origin': 'NaMgAl-Studio community port of DillonGoo Studios Goo Engine; not the original official binary',
              'materials': [], 'new_physics': False, 'mme_executed': False}
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    assert abs(scene.camera.data.lens - 61.734649658203125) < .0001
    mute_file_outputs()
    for actor in TARGETS:
        lamp = bpy.data.objects[f'Reference duet | {actor} | key'].data
        lamp.light_groups.groups.add().name = 'Goo portrait key | ' + actor
        # Retain default membership for the existing Blender surface shaders.
        lamp.light_groups.use_default = True
        for name, (_, role) in TARGETS[actor].items():
            material = bpy.data.materials[name]
            tree = material.node_tree
            assert not any(n.name.startswith(PREFIX) for n in tree.nodes)
            info = node(tree, 'ShaderNodeShaderInfo', 'native key light information')
            info.use_own_light_groups = True
            info.light_groups.use_default = False
            info.light_groups.groups.add().name = 'Goo portrait key | ' + actor
            response = tree.nodes['Portrait relight | keyfill | form times occlusion']
            old_response = response.inputs[1].links[0].from_socket
            visibility = node(tree, 'ShaderNodeMapRange', 'separate cast shadow response')
            visibility.clamp = True
            lo, hi = spec['native_cast_shadow_endpoints'][role]
            visibility.inputs['From Min'].default_value = 0
            visibility.inputs['From Max'].default_value = 1
            visibility.inputs['To Min'].default_value = lo
            visibility.inputs['To Max'].default_value = hi
            tree.links.new(info.outputs['Cast Shadows'], visibility.inputs['Value'])
            tree.links.new(visibility.outputs['Result'], response.inputs[1])
            if role not in ('face', 'skin'):
                old_form = response.inputs[0].links[0].from_socket
                form = node(tree, 'ShaderNodeMixRGB', 'native Half Lambert and authored form')
                form.inputs[0].default_value = spec['native_half_lambert_blend']
                tree.links.new(old_form, form.inputs[1])
                tree.links.new(info.outputs['Half-lambert factor'], form.inputs[2])
                tree.links.new(form.outputs[0], response.inputs[0])
            report['materials'].append({'name': name, 'actor': actor, 'role': role,
                                        'previous_response': old_response.node.name, 'cast_shadow_endpoints': [lo, hi],
                                        'half_lambert_blend': spec['native_half_lambert_blend'] if role not in ('face', 'skin') else 0})
    import goo_engine_light_groups
    goo_engine_light_groups.sync_light_groups()
    scene['production_runtime'] = 'Goo 5.2.1 community port 0051aee03764'
    scene['goo_wedding_profile'] = str(REPO / 'presets/lighting/goo-wedding-v1.json')
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 24
    scene.render.use_motion_blur = False
    scene.camera.data.dof.use_dof = True
    scene.render.use_sequencer = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(ROOT / 'complete-4290.png')
    project = ROOT / 'Franken_Duet_Goo_Wedding.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report.update(project=str(project), project_sha256=hashlib.sha256(project.read_bytes()).hexdigest())
    (ROOT / 'preparation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    started = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    report['still_render_seconds'] = time.perf_counter() - started
    (ROOT / 'preparation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('GOO_WEDDING_MIGRATION_STILL_COMPLETE', project, flush=True)


if __name__ == '__main__':
    main()
