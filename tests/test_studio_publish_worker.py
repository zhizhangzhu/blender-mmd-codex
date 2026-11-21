"""Pure worker guard checks; these do not establish Blender artwork quality."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch

class PublishWorkerTests(unittest.TestCase):
    def setUp(self):
        bpy = ModuleType('bpy')
        bpy.types = NS(ID=type('FakeID', (), {}))
        bpy.data = NS(materials={}, objects={})
        self.bpy = bpy
        path = Path(__file__).resolve().parents[1] / 'scripts/studio_publish_worker.py'
        spec = importlib.util.spec_from_file_location('isolated_publish_worker', path)
        self.w = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'bpy': bpy}): spec.loader.exec_module(self.w)
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('MMD_TEST_TEMP', 'D:/codex/temp'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'source.blend'; self.source.write_bytes(b'original')
        self.runtime = self.root / 'runtime.json'; self.runtime.write_text('{}', encoding='utf-8')
        self.profile = {'source': self.pin(self.source), 'runtime': str(self.runtime), 'render': {'dof': 'source', 'motion_blur': False}, 'cases': [{'id': 'selected', 'frame': 4290, 'overrides': [{'switch': 'light', 'value': 2}]}], 'switches': {'light': {'kind': 'light_energy', 'object': 'Light', 'expected': 1}}}
        self.profilepath = self.root / 'profile.json'
        self.save_profile()
        self.request = {'schema_version': 1, 'mode': 'publish', 'profile': self.pin(self.profilepath), 'runtime': self.pin(self.runtime), 'expected_source': self.pin(self.source), 'case_id': 'selected', 'pins': {key: self.pin(path) for key, path in [('worker', self.w.__file__), ('benchworker', self.w.bench.__file__), ('contract', self.w.contract.__file__)]}, 'reopen_tolerance': {'max_abs': .005, 'mean_abs': .0001}}
        self.validation = patch.object(self.w.contract, 'validate', return_value=[]).start()
        self.addCleanup(patch.stopall)
    def pin(self, path):
        path = Path(path).resolve()
        return {'path': str(path), 'sha256': self.w.contract.digest(path)}
    def save_profile(self):
        self.profilepath.write_text(json.dumps(self.profile), encoding='utf-8')
        if hasattr(self, 'request'): self.request['profile'] = self.pin(self.profilepath)
    def validate(self): return self.w.validate_request(self.request, self.root / 'request.json')
    def test_valid_pinned_request(self):
        profile, case, runtime, source = self.validate()
        self.assertEqual(source, self.source)
        self.assertEqual(case['frame'], 4290)
        self.validation.assert_called_once_with(profile, check_source=True)
    def test_modified_source_refused(self):
        self.source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): self.validate()
    def test_correct_hash_wrong_worker_path_refused(self):
        impostor = self.root / 'worker.py'; impostor.write_text('# harmless', encoding='utf-8')
        self.request['pins']['worker'] = self.pin(impostor)
        with self.assertRaisesRegex(ValueError, 'Unexpected pinned worker'): self.validate()
    def test_modified_profile_refused(self):
        self.profilepath.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'profile hash mismatch'): self.validate()
    def test_exact_frame_required(self):
        self.profile['cases'][0]['frame'] = 4291; self.save_profile()
        with self.assertRaisesRegex(ValueError, '4290'): self.validate()
    def test_hidden_geometry_controls_refused(self):
        for kind in ('object_hide', 'modifier_enabled', 'unknown'):
            with self.subTest(kind=kind):
                self.profile['switches']['light']['kind'] = kind; self.save_profile()
                with self.assertRaisesRegex(ValueError, 'scope exceeded'): self.validate()
    def test_tolerance_caps_types_and_finiteness(self):
        for key, bad in [('max_abs', .0051), ('mean_abs', .00011), ('max_abs', -1), ('max_abs', True), ('mean_abs', float('nan')), ('mean_abs', float('inf'))]:
            with self.subTest(key=key, bad=bad):
                request = copy.deepcopy(self.request); request['reopen_tolerance'][key] = bad
                with self.assertRaisesRegex(ValueError, 'tolerance'): self.w.validate_request(request, self.root / 'request.json')
    def test_source_dof_and_no_motion_blur_required(self):
        for setting, bad in [('dof', False), ('motion_blur', True)]:
            profile = copy.deepcopy(self.profile); profile['render'][setting] = bad
            self.profilepath.write_text(json.dumps(profile), encoding='utf-8'); self.request['profile'] = self.pin(self.profilepath)
            with self.assertRaisesRegex(ValueError, 'DOF'): self.validate()
    def test_reviewed_selection_must_match(self):
        (self.root / 'manifest.json').write_text('{}', encoding='utf-8')
        (self.root / 'lesson.json').write_text('{"selection":"other"}', encoding='utf-8')
        self.request['iteration'] = {'path': str(self.root), 'manifest_sha256': self.w.contract.digest(self.root / 'manifest.json'), 'lesson_sha256': self.w.contract.digest(self.root / 'lesson.json')}
        with self.assertRaisesRegex(ValueError, 'reviewed selection'): self.validate()
    def test_reopen_binding_changes_only_declared_expectations(self):
        original = copy.deepcopy(self.profile)
        candidate = {'path': 'candidate.blend', 'sha256': 'a'*64}
        derived = self.w.candidate_profile(self.profile, self.profile['cases'][0], candidate)
        self.assertEqual(derived['source'], candidate)
        self.assertEqual(derived['switches']['light']['expected'], 2)
        self.assertEqual(self.profile, original)
        self.assertEqual(derived['cases'], original['cases'])
    def test_masks_only_selected_socket_and_light_datablock(self):
        self.profile['switches']['socket'] = {'kind': 'node_input', 'material': 'Face', 'node': 'Shade', 'socket': 'Value'}
        self.profile['switches']['glow'] = {'kind': 'glow_bypass', 'nodes': []}
        case = {'overrides': [{'switch': 'socket'}, {'switch': 'light'}, {'switch': 'glow'}]}
        self.bpy.data.materials['Face'] = NS(node_tree=NS(name='FaceTree', as_pointer=lambda: 101, nodes={'Shade': object()}))
        self.bpy.data.objects['Light'] = NS(data=NS(name='LightData'))
        with patch.object(self.w.bench, 'find_socket', return_value=NS(identifier='Value_001')):
            mats, lights = self.w.selected_masks(self.profile, case)
        self.assertEqual(mats, {101: {('Shade', 'Value_001')}})
        self.assertEqual(lights, {'LightData'})
    def test_masks_refuse_geometry_before_modifying_anything(self):
        self.profile['switches']['light']['kind'] = 'object_hide'
        with self.assertRaisesRegex(ValueError, 'Unsupported publish control'):
            self.w.selected_masks(self.profile, self.profile['cases'][0])
    def test_custom_id_properties_are_retained(self):
        owner = {'artist_note': 'keep', 'weights': [1., .25], 'nested': {'enabled': True}}
        self.assertEqual(self.w.custom(owner), owner)
        owner['weights'][1] = .5
        self.assertEqual(self.w.custom(owner)['weights'], [1., .5])
    def test_custom_known_unsupported_idproperties_is_empty(self):
        class UnsupportedModifier:
            def keys(self):
                raise TypeError("bpy_struct.keys(): this type doesn't support IDProperties")
        self.assertEqual(self.w.custom(UnsupportedModifier()), {})
    def test_custom_unrelated_typeerror_is_not_swallowed(self):
        class BrokenOwner:
            def keys(self): raise TypeError('unexpected RNA corruption')
        with self.assertRaisesRegex(TypeError, 'unexpected RNA corruption'):
            self.w.custom(BrokenOwner())
    def test_custom_getitem_failure_is_not_swallowed(self):
        class BrokenValue:
            def keys(self): return ['important_property']
            def __getitem__(self, key): raise TypeError('failed to decode protected property')
        with self.assertRaisesRegex(TypeError, 'failed to decode protected property'):
            self.w.custom(BrokenValue())
    def test_nonfinite_protection_value_refused(self):
        with self.assertRaisesRegex(ValueError, 'Nonfinite'): self.w.plain(float('nan'))
    def test_settings_force_final_still_without_changing_dof(self):
        scene = NS(render=NS(engine='BLENDER_EEVEE', image_settings=NS()), eevee=NS(), camera=NS(dof=NS(use_dof=True)))
        result = self.w.settings(scene, self.root, 'selected.png')
        self.assertEqual((scene.render.resolution_x, scene.render.resolution_y, scene.eevee.taa_render_samples), (1920, 1080, 64))
        self.assertEqual((scene.frame_start, scene.frame_end), (4290, 4290))
        self.assertFalse(scene.render.use_motion_blur)
        self.assertTrue(scene.camera.dof.use_dof)
        self.assertEqual(result['dof'], 'source')
    def key_collection(self, fallback=False):
        def prop(name, kind, width=1, readonly=False):
            return NS(identifier=name, type=kind, is_readonly=readonly, is_array=width > 1, array_length=width, is_enum_flag=False, enum_items=[NS(identifier='AUTO', value=0), NS(identifier='EASE_IN', value=1)])
        properties = [prop('co', 'FLOAT', 2, True), prop('co_ui', 'FLOAT', 2), prop('handle_left', 'FLOAT', 2, True), prop('handle_right', 'FLOAT', 2, True), prop('easing', 'ENUM'), prop('select_control_point', 'BOOLEAN'), prop('amplitude', 'FLOAT')]
        item = NS(bl_rna=NS(identifier='TestKeyframe', properties=properties), co=[1., 2.], co_ui=[1., 2.], handle_left=[.5, 2.], handle_right=[1.5, 2.], easing='AUTO', select_control_point=False, amplitude=.25)
        class Collection(list):
            def foreach_get(self, name, target):
                if fallback: raise TypeError('RNA alias without bulk getter')
                values = []
                for entry in self:
                    value = getattr(entry, name)
                    values.extend(value if isinstance(value, list) else [value])
                for i, value in enumerate(values): target[i] = value
        return Collection([item])
    def test_all_authored_key_fields_change_fingerprint(self):
        keys = self.key_collection()
        before = self.w.collection_record(keys)
        for name, value in [('co', [1., 3.]), ('co_ui', [1., 3.]), ('handle_left', [.4, 2.]), ('handle_right', [1.6, 2.]), ('easing', 'EASE_IN'), ('select_control_point', True), ('amplitude', .5)]:
            with self.subTest(field=name):
                old = getattr(keys[0], name)
                setattr(keys[0], name, value)
                after = self.w.collection_record(keys)
                self.assertNotEqual(before, after)
                changed = [a['name'] for a, b in zip(before['fields'], after['fields']) if a['sha256'] != b['sha256']]
                self.assertEqual(changed, [name])
                setattr(keys[0], name, old)
    def test_numeric_alias_fallback_matches_bulk_fingerprint(self):
        self.assertEqual(self.w.collection_record(self.key_collection()), self.w.collection_record(self.key_collection(fallback=True)))
    def test_unknown_key_enum_refused(self):
        keys = self.key_collection(); keys[0].easing = 'NEW_UNSUPPORTED'
        with self.assertRaisesRegex(ValueError, 'Unknown protected enum'): self.w.collection_record(keys)
    def test_unknown_writable_key_structure_refused(self):
        keys = self.key_collection()
        keys[0].bl_rna.identifier = 'UnsupportedKeyframe'
        keys[0].bl_rna.properties.append(NS(identifier='new_pointer', type='POINTER', is_readonly=False))
        with self.assertRaisesRegex(ValueError, 'Unsupported writable protected'): self.w.collection_record(keys)
    def test_curve_record_preserves_samples_and_modifier_settings(self):
        keys = self.key_collection()
        curve = NS(keyframe_points=keys, sampled_points=self.key_collection(), modifiers=[NS(strength=1.)])
        with patch.object(self.w, 'rna', side_effect=lambda x: {'strength': x.strength} if hasattr(x, 'strength') else {}):
            before = self.w.curve_record(curve)
            curve.sampled_points[0].co[1] += 1
            self.assertNotEqual(before, self.w.curve_record(curve))
            curve.sampled_points[0].co[1] -= 1
            curve.modifiers[0].strength = 2.
            self.assertNotEqual(before, self.w.curve_record(curve))
    def test_layered_curve_alias_dedup_does_not_drop_keys(self):
        keys = self.key_collection()
        curve = NS(as_pointer=lambda: 101, keyframe_points=keys, sampled_points=[], modifiers=[])
        bag = NS(slot_handle=3, fcurves=[curve, curve], groups=[])
        strip = NS(channelbags=[bag])
        layer = NS(strips=[strip])
        action = NS(name='Dance', layers=[layer], slots=[], fcurves=[curve])
        self.bpy.data.actions = [action]
        with patch.object(self.w, 'rna', return_value={}), patch.object(self.w, 'progress'):
            before = self.w.actions_record()
            counts = dict(self.w._ACTION_COUNTS)
            self.assertEqual(counts['unique_curves'], 1)
            self.assertEqual(counts['curve_aliases'], 1)
            self.assertEqual(counts['keys'], 1)
            keys[0].handle_right[1] += .5
            self.assertNotEqual(before, self.w.actions_record())
            self.assertEqual(before['Dance']['legacy_curves'], [])
    def test_key_collection_field_count_and_empty_samples_preserved(self):
        keys = self.key_collection()
        before = self.w.collection_record(keys)
        keys.append(copy.deepcopy(keys[0]))
        after = self.w.collection_record(keys)
        self.assertEqual((before['count'], after['count']), (1, 2))
        self.assertNotEqual(before, after)
        self.assertEqual(self.w.collection_record([]), {'count': 0, 'fields': []})
    def test_same_named_embedded_trees_protected_and_masked_by_identity(self):
        class Named(list):
            def __getitem__(self, key):
                return next(x for x in self if x.name == key) if isinstance(key, str) else super().__getitem__(key)
        def tree(pointer, value):
            socket = NS(identifier='Value', name='Value', default_value=value, enabled=True)
            node = NS(name='Shade', inputs=[socket], outputs=[])
            return NS(name='IdenticalTree', name_full='IdenticalTree', as_pointer=lambda: pointer, nodes=Named([node]), links=[])
        first, second, shared = tree(101, 1.), tree(202, 1.), tree(303, 7.)
        self.bpy.data.materials = Named([NS(name='Face', node_tree=first), NS(name='Dress', node_tree=second)])
        for field in ('worlds', 'lights', 'scenes', 'cameras', 'collections'): setattr(self.bpy.data, field, [])
        self.profile['switches'] = {'socket': {'kind': 'node_input', 'material': 'Face', 'node': 'Shade', 'socket': 'Value', 'socket_match': 'identifier'}}
        case = {'overrides': [{'switch': 'socket', 'value': 2.}]}
        with patch.object(self.w, 'progress'), patch.object(self.w, 'rna', return_value={}), patch.object(self.w, 'animation', return_value=None), patch.object(self.w, 'actions_record', return_value={}), patch.object(self.w, 'object_records', return_value={}), patch.object(self.w, 'actor_meshes', return_value={}), patch.object(self.w, 'image_records', return_value={}), patch.object(self.w.bench, 'find_socket', side_effect=lambda n, s, exact: n.inputs[0]) as lookup, patch.object(self.w.bench, 'walk_trees', side_effect=lambda root: [root, shared]), patch.object(self.w, 'tree_record', wraps=self.w.tree_record) as record:
            before = self.w.protection(self.profile, case)
            self.assertEqual(record.call_count, 3)  # two distinct embedded roots plus one shared group
            lookup.assert_called_with(first.nodes[0], 'Value', True)
            first.nodes[0].inputs[0].default_value = 2.
            self.assertEqual(before['node_graphs'], self.w.protection(self.profile, case)['node_graphs'])
            second.nodes[0].inputs[0].default_value = 2.
            self.assertNotEqual(before['node_graphs'], self.w.protection(self.profile, case)['node_graphs'])
            second.nodes[0].inputs[0].default_value = 1.
            shared.nodes[0].inputs[0].default_value = 8.
            self.assertNotEqual(before['node_graphs'], self.w.protection(self.profile, case)['node_graphs'])
    def image_fixture(self, name='Texture', source='FILE', packed=b'packed bytes'):
        class Image:
            @property
            def pixels(self):
                raise AssertionError('Packed/external pixels must never be expanded or read')
        image = Image()
        image.name, image.source, image.type = name, source, 'IMAGE'
        image.filepath, image.library, image.size = '', None, [2, 2]
        image.colorspace_settings = NS(bl_rna=NS(properties=[]))
        image.bl_rna = NS(properties=[NS(identifier='pixels', is_readonly=False, type='FLOAT'), NS(identifier='source', is_readonly=False, type='ENUM')])
        image.packed_files = []
        image.packed_file = NS(data=packed) if packed is not None else None
        return image
    def test_packed_image_avoids_pixel_expansion_but_hashes_payload(self):
        import hashlib
        image = self.image_fixture()
        self.bpy.data.images = [image]
        with patch.object(self.w, 'rna', wraps=self.w.rna) as rna:
            before = self.w.image_records()
            rna.assert_any_call(image, {'pixels'})
            self.assertEqual(before['Texture']['packed'][0]['sha256'], hashlib.sha256(b'packed bytes').hexdigest())
            image.packed_file.data = b'changed packed bytes'
            self.assertNotEqual(before, self.w.image_records())
    def test_multifile_packed_image_payloads_remain_protected(self):
        image = self.image_fixture(packed=None)
        image.packed_files = [NS(filepath='tile1001.png', packed_file=NS(data=b'first')), NS(filepath='tile1002.png', packed_file=NS(data=b'second'))]
        self.bpy.data.images = [image]
        before = self.w.image_records()
        self.assertEqual([x['path'] for x in before['Texture']['packed']], ['tile1001.png', 'tile1002.png'])
        image.packed_files[1].packed_file.data = b'changed second'
        after = self.w.image_records()
        self.assertEqual(before['Texture']['packed'][0], after['Texture']['packed'][0])
        self.assertNotEqual(before['Texture']['packed'][1], after['Texture']['packed'][1])
    def test_external_image_hash_preserved_without_reading_pixels(self):
        path = self.root / 'external.png'; path.write_bytes(b'external source')
        image = self.image_fixture(packed=None); image.filepath = str(path)
        self.bpy.data.images = [image]
        self.bpy.path = NS(abspath=lambda value, library=None: value)
        before = self.w.image_records()
        self.assertEqual(before['Texture']['external_sha256'], self.w.contract.digest(path))
        path.write_bytes(b'changed external source')
        self.assertNotEqual(before, self.w.image_records())
    def test_generated_image_hash_uses_raw_buffer_not_python_pixel_iteration(self):
        from array import array
        import hashlib
        class Pixels:
            def __init__(self): self.values = [0., .25, .5, 1.]; self.calls = 0
            def __len__(self): return len(self.values)
            def __iter__(self): raise AssertionError('Do not expand pixel floats in Python')
            def foreach_get(self, buffer):
                self.calls += 1
                for i, value in enumerate(self.values): buffer[i] = value
        pixels = Pixels()
        image = self.image_fixture(source='GENERATED', packed=None)
        # Replace only the raising property with the bulk RNA collection.
        image = NS(**image.__dict__, pixels=pixels)
        self.bpy.data.images = [image]
        before = self.w.image_records()
        self.assertEqual(before['Texture']['pixels'], hashlib.sha256(array('f', pixels.values).tobytes()).hexdigest())
        self.assertEqual(pixels.calls, 1)
        pixels.values[1] = .75
        self.assertNotEqual(before, self.w.image_records())
        self.assertEqual(pixels.calls, 2)
    def test_int16_pair_mesh_attribute_is_not_skipped(self):
        class Data(list):
            def foreach_get(self, field, buffer):
                for i, value in enumerate([1, 2, 3, 4]): buffer[i] = value
        data = Data([object(), object()])
        attribute = NS(name='short_pairs', data_type='INT16_2D', domain='POINT', data=data)
        record = self.w.mesh_attributes(NS(attributes=[attribute]))['short_pairs']
        self.assertEqual((record['length'], record['type']), (2, 'INT16_2D'))
        self.assertEqual(len(record['sha256']), 64)
    def test_unreviewed_engine_refused(self):
        with self.assertRaisesRegex(ValueError, 'EEVEE'):
            self.w.settings(NS(render=NS(engine='CYCLES')), self.root, 'selected.png')

if __name__ == '__main__': unittest.main()
