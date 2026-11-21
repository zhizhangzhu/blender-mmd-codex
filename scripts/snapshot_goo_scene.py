"""Compact migration evidence: complete curve data/geometry and sampled evaluated poses."""
import argparse
import hashlib
import json
import sys
from array import array
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))


def numbers(collection, field, width):
    values = array('f', [0.0]) * (len(collection) * width)
    collection.foreach_get(field, values)
    return values.tobytes()


def capture():
    actions = {}
    for action in bpy.data.actions:
        digest = hashlib.sha256()
        keys = curves = 0
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    digest.update(str(bag.slot_handle).encode())
                    for curve in bag.fcurves:
                        curves += 1
                        keys += len(curve.keyframe_points)
                        digest.update(f'{curve.data_path}|{curve.array_index}|{curve.extrapolation}'.encode())
                        for field in ('co', 'handle_left', 'handle_right'):
                            digest.update(numbers(curve.keyframe_points, field, 2))
                        digest.update(str([(k.interpolation, k.handle_left_type, k.handle_right_type) for k in curve.keyframe_points]).encode())
        actions[action.name] = {'sha256': digest.hexdigest(), 'curves': curves, 'keys': keys, 'slots': len(action.slots)}
    geometry = {m.name: {'vertices': len(m.vertices), 'sha256': hashlib.sha256(numbers(m.vertices, 'co', 3)).hexdigest(),
                         'polygons': len(m.polygons)} for m in bpy.data.meshes}
    scene = bpy.context.scene
    samples = {}
    for frame in (4140, 4218, 4290, 4370, 4438):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        samples[str(frame)] = {'lens': scene.camera.data.lens,
                              'camera': [x for row in scene.camera.matrix_world for x in row],
                              'bones': {f'{o.name}/{b.name}': [x for row in b.matrix for x in row]
                                        for o in scene.objects if o.type == 'ARMATURE' for b in o.pose.bones},
                              'shapes': {k.name: [b.value for b in k.key_blocks] for k in bpy.data.shape_keys}}
    scene.frame_set(4290)
    return {'objects': sorted(o.name for o in scene.objects), 'actions': actions, 'geometry': geometry,
            'images': sorted((i.name, bool(i.packed_file), list(i.size)) for i in bpy.data.images),
            'samples': samples, 'engine': scene.render.engine, 'fps': scene.render.fps}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--project', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--goo', action='store_true')
    args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.goo:
        from goo_runtime import register_addons
        register_addons()
    else:
        bpy.ops.wm.read_userpref()
        bpy.ops.preferences.addon_enable(module='bl_ext.blender_org.mmd_tools')
    bpy.ops.wm.open_mainfile(filepath=args.project, load_ui=False, use_scripts=False)
    result = capture()
    result['binary'] = bpy.app.binary_path
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    print('GOO_SNAPSHOT_COMPLETE', path, flush=True)


if __name__ == '__main__':
    main()
