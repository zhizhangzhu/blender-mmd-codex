"""Bounded iteration adversarial checks; no Blender process is started."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import studio_iteration as it

class IterationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('MMD_TEST_TEMP', 'D:/codex/temp'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.blend'
        self.source.write_bytes(b'fixture only')
        self.study = {'id': 'study', 'observations': [{'id': 'o', 'seen': True}], 'targets': [{'id': 't', 'observation_ids': ['o']}], 'hypotheses': [{'id': 'h', 'observation_ids': ['o']}]}
        self.profile = {'id': 'profile', 'source': {'path': str(self.source), 'sha256': it.sha256(self.source)}, 'runtime': 'runtime.json', 'scene': {'camera': 'Camera'}, 'cases': [{'id': 'baseline', 'frame': 10, 'overrides': []}]}
        self.plan = {'schema_version': 1, 'id': 'iteration', 'title': 'Bounded experiment', 'baseline_case': 'baseline', 'target_ids': ['t'], 'preserve': ['camera'], 'limits': ['single frame'], 'experiments': [{'id': 'option', 'compare_to': 'baseline', 'hypothesis_id': 'h', 'target_ids': ['t'], 'prediction': 'lighter', 'change_kind': 'ablation', 'overrides': [{'switch': 'light', 'value': 2}]}]}
        for name, data in [('study', self.study), ('profile', self.profile)]:
            path = self.root / (name + '.json')
            it.write(path, data)
            self.plan[name] = {'path': str(path), 'sha256': it.sha256(path)}
        self.planpath = self.root / 'plan.json'
        it.write(self.planpath, self.plan)
        it.write(self.root / 'runtime.json', {})
        self.out = self.root / 'iteration'
        # Input validators have independent suites; isolate iteration semantics here.
        self.study_mock = patch.object(it.study, 'validate', return_value=[]).start()
        self.contract_mock = patch.object(it.contract, 'validate', return_value=[]).start()
        self.addCleanup(patch.stopall)
        it.prepare(self.planpath, self.out, root=self.root)
    def mutate(self, path, fn):
        data = it.load(path)
        fn(data)
        Path(path).write_text(json.dumps(data), encoding='utf-8')
    def fake_run(self, passed=True):
        c = it.load(self.out / 'compiled-profile.json')
        d = self.out / 'run'
        d.mkdir()
        for case in c['cases']:
            image = d / (case['id'] + '.png')
            image.write_bytes(b'fake image')
            case.update(path=str(image), sha256=it.sha256(image), passed=True, camera={'name': 'Camera'}, effective_render={'dimensions': [64, 64]}, color={'view_transform': 'Standard'})
        report = {'passed': passed, 'profile_sha256': it.sha256(self.out / 'compiled-profile.json'), 'source': c['source'], 'source_unchanged': True, 'cases': c['cases']}
        for key, field in [('worker', 'worker_sha256'), ('contract', 'contract_sha256'), ('runtime', 'runtime_config_sha256')]:
            report[field] = it.load(self.out / 'manifest.json')['code_pins'][key]['sha256']
        it.write(d / 'report.json', report)
        it.write(d / 'launch.json', {'passed': passed, 'returncode': 0 if passed else 1, 'source_sha256_after': c['source']['sha256'], 'profile_sha256': report['profile_sha256'], 'source_sha256_before': c['source']['sha256']})
        it.write(self.out / 'run-link.json', {'path': str(d / 'report.json'), 'sha256': it.sha256(d / 'report.json'), 'launch_sha256': it.sha256(d / 'launch.json')})
    def review(self):
        r = {'schema_version': 1, 'iteration_id': 'iteration', 'run_report_sha256': it.load(self.out / 'run-link.json')['sha256'], 'reviewer': {'kind': 'ai', 'identity': 'test', 'scope': 'two stills'}, 'seen_cases': ['baseline', 'option'], 'targets': [{'target_id': 't', 'verdict': 'improved', 'observations': ['left cheek shadow is narrower'], 'tradeoffs': ['less contrast']}], 'hypothesis_outcomes': [{'experiment_id': 'option', 'hypothesis_id': 'h', 'outcome': 'supported', 'reason': 'cheek lighter'}], 'selection': 'option', 'reasons': ['target improved'], 'next_action': 'try another character', 'user_approval': False, 'user_feedback_provenance': None}
        p = self.root / 'review-input.json'
        p.write_text(json.dumps(r), encoding='utf-8')
        return p
    def test_valid_close_single_case(self):
        self.fake_run()
        it.record_review(self.out, self.review())
        (self.out / 'board').mkdir()
        it.write(self.out / 'board/manifest.json', {})
        with patch('scripts.studio_review_board.validate_board', return_value=[]):
            lesson = it.close(self.out)
        self.assertEqual(lesson['transfer_level'], 'single_case')
        self.assertFalse(lesson['user_approval'])
    def test_snapshot_mutation(self):
        self.mutate(self.out / 'inputs/plan.json', lambda x: x.update(title='stale'))
        self.assertTrue(it.check(self.out))
    def test_compiled_mutation(self):
        self.mutate(self.out / 'compiled-profile.json', lambda x: x['cases'].reverse())
        self.assertTrue(it.check(self.out))
    def test_stale_original_pin(self):
        self.mutate(self.planpath, lambda x: x['study'].update(sha256='0'*64))
        with self.assertRaises(ValueError): it.prepare(self.planpath, self.root / 'bad', root=self.root)
    def test_source_mutation(self):
        self.source.write_bytes(b'changed')
        self.assertTrue(it.check(self.out))
    def test_unknown_target(self):
        self.plan['target_ids'] = ['unknown']
        with self.assertRaises(ValueError): it.compile_plan(self.plan, self.study, self.profile)
    def test_unseen_observation(self):
        self.study['observations'][0]['seen'] = False
        with self.assertRaises(ValueError): it.compile_plan(self.plan, self.study, self.profile)
    def test_forward_compare(self):
        self.plan['experiments'][0]['compare_to'] = 'later'
        with self.assertRaises(ValueError): it.compile_plan(self.plan, self.study, self.profile)
    def test_duplicate_case(self):
        self.plan['experiments'][0]['id'] = 'BASELINE'
        with self.assertRaises(ValueError): it.compile_plan(self.plan, self.study, self.profile)
    def test_ai_forged_approval(self):
        self.fake_run()
        p = self.review()
        self.mutate(p, lambda x: x.update(user_approval=True))
        with self.assertRaises(ValueError): it.record_review(self.out, p)
    def test_unseen_selection(self):
        self.fake_run()
        p = self.review()
        self.mutate(p, lambda x: x.update(seen_cases=['baseline']))
        with self.assertRaises(ValueError): it.record_review(self.out, p)
    def test_unknown_review_target(self):
        self.fake_run()
        p = self.review()
        self.mutate(p, lambda x: x['targets'][0].update(target_id='unknown'))
        with self.assertRaises(ValueError): it.record_review(self.out, p)
    def test_failed_run_no_review(self):
        self.fake_run(False)
        with self.assertRaises(ValueError): it.record_review(self.out, self.review())
    def test_report_hash_mutation(self):
        self.fake_run()
        self.mutate(self.out / 'run/report.json', lambda x: x.update(passed=False))
        self.assertTrue(it.check(self.out))
    def test_noclobber(self):
        with self.assertRaises(FileExistsError): it.prepare(self.planpath, self.out, root=self.root)
    def test_changed_image(self):
        self.fake_run()
        (self.out / 'run/option.png').write_bytes(b'changed')
        self.assertTrue(it.check(self.out))
    def test_changed_launch(self):
        self.fake_run()
        self.mutate(self.out / 'run/launch.json', lambda x: x.update(returncode=3))
        self.assertTrue(it.check(self.out))
    def test_changed_frozen_review(self):
        self.fake_run()
        it.record_review(self.out, self.review())
        self.mutate(self.out / 'review.json', lambda x: x.update(next_action='forged'))
        with self.assertRaises(ValueError): it.close(self.out)
    def test_case_reordered_even_with_new_report_pin(self):
        self.fake_run()
        self.mutate(self.out / 'run/report.json', lambda x: x['cases'].reverse())
        self.mutate(self.out / 'run-link.json', lambda x: x.update(sha256=it.sha256(self.out / 'run/report.json')))
        self.assertTrue(it.check(self.out))
    def test_missing_hypothesis_outcome(self):
        self.fake_run()
        p = self.review()
        self.mutate(p, lambda x: x.update(hypothesis_outcomes=[]))
        with self.assertRaises(ValueError): it.record_review(self.out, p)
    def test_wrong_hypothesis_outcome(self):
        self.fake_run()
        p = self.review()
        self.mutate(p, lambda x: x['hypothesis_outcomes'][0].update(hypothesis_id='other'))
        with self.assertRaises(ValueError): it.record_review(self.out, p)
    def test_close_requires_board(self):
        self.fake_run()
        it.record_review(self.out, self.review())
        with self.assertRaises(ValueError): it.close(self.out)
    def test_check_detects_review_tamper(self):
        self.fake_run()
        it.record_review(self.out, self.review())
        self.mutate(self.out / 'review.json', lambda x: x.update(selection='baseline'))
        self.assertTrue(it.check(self.out))
    def test_feedback_after_close_preserves_lesson(self):
        self.fake_run()
        p = self.review()
        it.record_review(self.out, p)
        (self.out / 'board').mkdir()
        it.write(self.out / 'board/manifest.json', {})
        provenance = self.root / 'user-message.txt'
        provenance.write_text('User explicitly approves option', encoding='utf-8')
        with patch('scripts.studio_review_board.validate_board', return_value=[]):
            it.close(self.out)
            before = it.sha256(self.out / 'lesson.json')
            self.mutate(p, lambda x: x.update(reviewer={'kind': 'user', 'identity': 'user', 'scope': 'all cases'}, user_approval=True, user_feedback_provenance=str(provenance), user_feedback_provenance_sha256=it.sha256(provenance)))
            it.record_user_feedback(self.out, p)
            self.assertEqual(before, it.sha256(self.out / 'lesson.json'))
            self.assertFalse(it.load(self.out / 'lesson.json')['user_approval'])
            self.assertTrue(it.load(self.out / 'user-feedback.json')['user_approval'])
            self.assertEqual([], it.check(self.out))
            self.mutate(self.out / 'lesson.json', lambda x: x.update(user_approval=True))
            self.assertTrue(it.check(self.out))
    def test_user_feedback_requires_provenance_even_rejected(self):
        self.fake_run()
        p = self.review()
        self.mutate(p, lambda x: x.update(reviewer={'kind': 'user', 'identity': 'user', 'scope': 'all'}))
        with self.assertRaises((TypeError, ValueError)): it.record_user_feedback(self.out, p)
    def test_dryrun(self):
        with patch.object(it, 'load', side_effect=lambda p: {} if str(p).endswith('runtime.json') else json.loads(Path(p).read_text(encoding='utf-8'))), patch.object(it.studio_bench, 'dispatch', return_value={'passed': False}) as dispatch:
            it.run(self.out)
            self.assertFalse(dispatch.call_args.kwargs['execute'])
            self.assertFalse((self.out / 'run-link.json').exists())

if __name__ == '__main__': unittest.main()
