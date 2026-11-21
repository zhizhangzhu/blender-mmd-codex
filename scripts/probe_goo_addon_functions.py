"""Exercise selected add-on operations in a disposable Goo scene, without rendering."""
import json
import sys
import traceback
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

report = {'registration': register_addons(), 'operations': {}, 'production_modified': False}


def test(name, fn):
    try:
        report['operations'][name] = {'result': fn()}
    except Exception:  # noqa: BLE001 - diagnostic records arbitrary third-party operator failures
        report['operations'][name] = {'error': traceback.format_exc()}


bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8)
sphere = bpy.context.object
material = bpy.data.materials.new('Disposable plugin test')
material.use_nodes = True
sphere.data.materials.append(material)
for kind in ('outline', 'toon_shadow', 'skin', 'glow', 'color', 'skybox'):
    test('paper_helper.apply_' + kind, lambda k=kind: list(getattr(bpy.ops.paper_helper, 'apply_' + k)()))
    remover = 'restore_skybox' if kind == 'skybox' else 'remove_' + kind
    test('paper_helper.' + remover, lambda k=remover: list(getattr(bpy.ops.paper_helper, k)()))


def mmd_and_cafei():
    folder = Path('E:/tools/franken/阿克西妮娅2_by_神秘会员卡_85ba1d1257580930c054ba5201e4a36d')
    pmx = next(folder.rglob('*.pmx'))
    before = set(bpy.data.objects)
    result = bpy.ops.mmd_tools.import_model(filepath=str(pmx), scale=.08, clean_model=False, remove_doubles=False,
                                             save_log=False, types={'MESH', 'ARMATURE', 'MORPHS', 'DISPLAY'})
    imported = set(bpy.data.objects) - before
    root = next(o for o in imported if o.mmd_type == 'ROOT')
    mesh = next(o for o in imported if o.type == 'MESH')
    copies = {}
    for obj in imported:
        duplicate = obj.copy()
        if obj.data:
            duplicate.data = obj.data.copy()
        bpy.context.scene.collection.objects.link(duplicate)
        copies[obj] = duplicate
    for original, duplicate in copies.items():
        duplicate.parent = copies.get(original.parent)
    target = copies[root]
    for obj in copies.values():
        if obj.type == 'MESH':
            for i, mat in enumerate(obj.data.materials):
                if mat:
                    obj.data.materials[i] = mat.copy()
    props = bpy.context.scene.mmd_kafei_tools_transfer_preset
    props.direction = 'PMX2PMX'
    props.source, props.target = root, target
    props.material_flag = True
    props.uv_flag = props.vgs_flag = props.modifiers_flag = props.normal_flag = False
    props.toon_shading_flag = False
    transfer = bpy.ops.mmd_kafei_tools.transfer_preset()
    linked = copies[mesh].data.materials[0] == mesh.data.materials[0]
    assert linked, 'Material transfer returned without matching the test pair'
    return {'pmx_import': list(result), 'imported_objects': len(imported), 'cafei_transfer': list(transfer),
            'first_material_actually_linked': linked, 'physics_built': False}


test('mmd_import_and_cafei_material_transfer', mmd_and_cafei)
report['mmr_scope'] = 'Registration and operator availability only; no re-rigging of the already baked production characters.'
out = Path('D:/codex/output/MMD-Goo-Wedding-v1/plugin-function-probe.json')
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('GOO_ADDON_FUNCTION_PROBE_COMPLETE', out, flush=True)
