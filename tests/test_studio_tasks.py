import copy
import unittest
from scripts import studio_tasks as s


class StudioTasksTests(unittest.TestCase):
    def setUp(self):
        self.policy = dict(schema_version=1, roles=dict(supervisor=dict(model='gpt-6.1-sol', reasoning_effort='xhigh'), executor=dict(model='gpt-6.1-sol', reasoning_effort='low')), task_kinds=dict(risky='supervisor', art='supervisor', research='supervisor', simple='executor'), escalation=dict(max_attempts=2, conditions=['uncertain']), principles=['planning only'])

    def packet(self, **kwargs):
        return s.build_packet(self.policy, 'Simple task', 'simple', ['input'], ['scripts/example.py'], ['result'], ['verified'], **kwargs)

    def test_recommendations(self):
        for kind in ('risky', 'art', 'research'):
            self.assertEqual(s.recommend(self.policy, kind)['role'], 'supervisor')
        self.assertEqual(s.recommend(self.policy, 'simple')['role'], 'executor')
        self.assertEqual(s.recommend(self.policy, 'simple', attempts=2)['role'], 'supervisor')
        self.assertEqual(s.recommend(self.policy, 'simple', 'exploratory')['role'], 'supervisor')

    def test_scope_and_execution(self):
        with self.assertRaises(ValueError):
            s.build_packet(self.policy, 'Empty', 'simple', [], [], [], [])
        p = self.packet()
        self.assertEqual(p['execution']['status'], 'not_dispatched')
        self.assertIsNone(p['execution']['actual_model'])
        self.assertEqual(s.validate_packet(p, policy=self.policy), [])
        p['execution']['status'] = 'completed'
        self.assertTrue(s.validate_packet(p, policy=self.policy))

    def test_references_and_approval(self):
        for ref in ('../README.md', '/README.md', 'missing-file-zzz'):
            with self.assertRaises(ValueError):
                self.packet(context_refs=[ref])
        p = self.packet(context_refs=['README.md'])
        p['review']['user_approval'] = True
        self.assertTrue(s.validate_packet(p, policy=self.policy))
        p['review']['user_feedback_provenance'] = 'README.md'
        self.assertEqual(s.validate_packet(p, policy=self.policy), [])

    def test_reject_tampered_assignment(self):
        p = self.packet(uncertainty='exploratory')
        p['assignment'] = dict(role='executor', **self.policy['roles']['executor'])
        self.assertTrue(s.validate_packet(p, policy=self.policy))

    def test_reject_invented_execution_evidence(self):
        for key, value in [('actual_model', 'gpt-6.1-sol'), ('actual_reasoning_effort', 'low'), ('elapsed_seconds', 1), ('cost', 1), ('attempts', 1)]:
            p = self.packet()
            p['execution'][key] = value
            self.assertTrue(s.validate_packet(p, policy=self.policy), key)
        for value in (-1, float('nan'), True):
            p = self.packet()
            p['execution'].update(status='failed', cost=value)
            self.assertTrue(s.validate_packet(p, policy=self.policy))

    def test_configurable_models_preserve_assignment_integrity(self):
        self.policy['roles']['supervisor'] = dict(model='future-supervisor', reasoning_effort='max')
        self.policy['roles']['executor'] = dict(model='future-executor', reasoning_effort='low')
        self.assertEqual(s.validate_policy(self.policy), [])
        p = self.packet()
        self.assertEqual(p['assignment']['model'], 'future-executor')
        self.assertEqual(s.validate_packet(p, policy=self.policy), [])
        p['assignment']['model'] = 'unconfigured-model'
        self.assertTrue(s.validate_packet(p, policy=self.policy))
        self.assertEqual(s.recommend(self.policy, 'research')['model'], 'future-supervisor')

    def test_no_clobber(self):
        from unittest.mock import patch
        from pathlib import Path
        with patch.object(s, 'load_policy', return_value=self.policy), patch.object(Path, 'open', side_effect=FileExistsError('exists')):
            self.assertEqual(s.main(['packet', '--title', 'test', '--kind', 'simple', '--input', 'i', '--allow', 'p', '--deliverable', 'd', '--accept', 'a', '--output', 'existing']), 1)


if __name__ == '__main__':
    unittest.main()
