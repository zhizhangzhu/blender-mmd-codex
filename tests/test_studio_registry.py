import copy
import unittest
from scripts import studio_registry as registry

class RegistryTests(unittest.TestCase):

    def setUp(self):
        self.data = {'schema_version': 1, 'preferences': [], 'curriculum': [], 'capabilities': [{'id': 'a', 'title': '脸影 SDF', 'route': 'render', 'tags': ['脸影'], 'problem': 'shadow', 'when_to_use': 'still', 'avoid_when': [], 'method': ['compare'], 'entrypoints': ['README.md'], 'knowledge': [], 'evidence': [{'dimension': 'still', 'result': 'passed', 'scope': '4290 only', 'provenance': 'README.md', 'artifacts': [{'path': 'README.md', 'sha256': registry.digest(registry.ROOT / 'README.md')}]}], 'art_status': 'pending', 'user_feedback_provenance': None, 'transfer_level': 'single_case', 'next_exercise': 'compare'}]}

    def test_static_only(self):
        self.assertEqual([], registry.validate(self.data, check_artifacts=True))

    def test_tampering(self):
        self.data['capabilities'][0]['evidence'][0]['artifacts'][0]['sha256'] = '0' * 64
        self.assertEqual([], registry.validate(self.data))
        self.assertTrue(registry.validate(self.data, check_artifacts=True))

    def test_approval(self):
        self.data['capabilities'][0]['art_status'] = 'approved'
        self.assertTrue(registry.validate(self.data))

    def test_malformed(self):
        for value in (None, [], {'schema_version': 1, 'capabilities': [None, {'id': []}], 'preferences': {}, 'curriculum': [False]}):
            self.assertTrue(registry.validate(value))

    def test_cycle(self):
        self.data['curriculum'] = [{'id': i, 'title': 'lesson', 'route': 'render', 'prerequisites': [j], 'exercise': 'test', 'acceptance': ['look'], 'capability_ids': ['a']} for i, j in [('x', 'y'), ('y', 'x')]]
        self.assertTrue(any(('cyclic' in e for e in registry.validate(self.data))))

    def test_retrieval_and_context(self):
        other = copy.deepcopy(self.data['capabilities'][0])
        other['id'] = 'b'
        other['route'] = 'lighting'
        self.data['capabilities'].append(other)
        self.assertEqual(['a', 'b'], [c['id'] for c in registry.select_capabilities(self.data, '脸影')])
        self.assertEqual(['b'], [c['id'] for c in registry.select_capabilities(self.data, route='lighting')])
        self.assertEqual([], registry.select_capabilities(self.data, 'missing'))
        state = {'active_iteration': {'id': 'frozen'}, 'render_delivery_policy': {'default': 'stills_only'}}
        self.assertEqual(state['active_iteration'], registry.context(self.data, state)['state_summary']['active_iteration'])

    def test_natural_chinese_query(self):
        self.data['capabilities'][0]['tags'] = ['白衣', '太亮']
        selected = registry.select_capabilities(self.data, '伊科尔白衣太亮应该怎么处理')
        self.assertEqual(['a'], [c['id'] for c in selected])
        self.assertEqual([], registry.select_capabilities(self.data, '白衣太亮', route='motion'))

    def test_same_class_requires_transfer(self):
        cap = self.data['capabilities'][0]
        cap['transfer_level'] = 'same_class'
        self.assertTrue(any(('transfer' in error for error in registry.validate(self.data))))
        transfer = copy.deepcopy(cap['evidence'][0])
        transfer['dimension'] = 'transfer'
        transfer['artifacts'].append({'path': 'AGENTS.md', 'sha256': registry.digest(registry.ROOT / 'AGENTS.md')})
        cap['evidence'].append(transfer)
        self.assertEqual([], registry.validate(self.data, check_artifacts=True))

    def test_escape_and_transfer(self):
        self.data['capabilities'][0]['entrypoints'] = ['../outside']
        self.data['capabilities'][0]['transfer_level'] = 'cross_project'
        self.assertGreaterEqual(len(registry.validate(self.data)), 2)
if __name__ == '__main__':
    unittest.main()
