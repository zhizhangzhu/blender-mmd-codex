"""Publication launcher isolation and provenance tests, without Blender."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from scripts import studio_publish as pub

class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('MMD_TEST_TEMP', 'D:/codex/temp'))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        (self.repo / 'scripts').mkdir(parents=True)
        for name in ('studio_publish_worker.py', 'studio_scene_worker.py', 'studio_scene_contract.py'):
            (self.repo / 'scripts' / name).write_text('# fixture', encoding='utf-8')
        self.runtime = self.repo / 'runtime.json'
        exe = self.repo / 'blender.exe'; exe.write_bytes(b'fake')
        config = self.repo / 'config'; config.mkdir()
        scripts = self.repo / 'scripts'
        pub.iteration.write(self.runtime, {'executable': str(exe), 'user_config': str(config), 'user_scripts': str(scripts)})
        self.source = self.base / 'source.blend'; self.source.write_bytes(b'original')
        self.d = self.base / 'iteration'; self.d.mkdir()
        self.profile = {'source': pub.pin(self.source), 'runtime': 'runtime.json', 'switches': {'light': {'kind': 'light_energy'}}, 'cases': [{'id': 'selected', 'frame': 42, 'overrides': [{'switch': 'light', 'value': 3}]}], 'render': {'width': 640, 'height': 360, 'samples': 8, 'dof': False, 'motion_blur': False}}
        for name, value in [('manifest.json', {}), ('lesson.json', {'selection': 'selected'}), ('close-link.json', {}), ('compiled-profile.json', self.profile)]:
            pub.iteration.write(self.d / name, value)
        self.out = self.base / 'published'
        patch.object(pub, 'ROOT', self.repo).start()
        patch.object(pub, 'WORKER', self.repo / 'scripts/studio_publish_worker.py').start()
        self.check = patch.object(pub.iteration, 'check', return_value=[]).start()
        self.process = patch.object(pub.subprocess, 'run', side_effect=self.worker).start()
        self.addCleanup(patch.stopall)
    def worker(self, command, **kwargs):
        self.assertFalse(kwargs['shell'])
        self.assertEqual(kwargs['env']['BLENDER_USER_CONFIG'], str(self.repo / 'config'))
        out = Path(command[-1]); request = pub.load(out / 'request.json')
        candidate = out / 'Candidate.blend'
        if request['mode'] == 'publish': candidate.write_bytes(b'candidate')
        else: candidate = Path(request['expected_source']['path'])
        image = out / 'selected.png'; image.write_bytes(b'png')
        report = {'passed': True, 'mode': request['mode'], 'case_id': request['case_id'], 'source': request['expected_source'], 'candidate': pub.pin(candidate), 'image': pub.pin(image), 'request_sha256': pub.sha256(out / 'request.json')}
        report.update({key: request[key] for key in ('profile', 'runtime', 'pins', 'reopen_tolerance')})
        pub.iteration.write(out / ('publish-report.json' if request['mode'] == 'publish' else 'reopen-report.json'), report)
        return subprocess.CompletedProcess(command, 0, 'ok', '')
    def rewrite(self, path, fn):
        value = pub.load(path); fn(value); Path(path).write_text(json.dumps(value), encoding='utf-8')
    def test_dryrun_no_writes_process(self):
        result = pub.dispatch(self.d, 'selected', self.out)
        self.assertFalse(self.out.exists()); self.process.assert_not_called()
        self.assertEqual(result['profile']['render']['width'], 1920)
        self.assertEqual(pub.load(self.d / 'compiled-profile.json')['render']['width'], 640)
    def test_publish_success(self):
        result = pub.dispatch(self.d, 'selected', self.out, execute=True)
        self.assertTrue(result['passed']); self.assertTrue((self.out / 'Candidate.blend').exists())
        self.assertEqual(self.source.read_bytes(), b'original')
    def test_reopen_success(self):
        pub.dispatch(self.d, 'selected', self.out, execute=True)
        result = pub.dispatch(self.d, 'selected', self.base / 'reopened', mode='reopen', publish_report=self.out / 'publish-report.json', execute=True)
        self.assertTrue(result['passed'])
        request = pub.load(self.base / 'reopened/request.json')
        self.assertEqual(request['expected_source']['path'], str((self.out / 'Candidate.blend').resolve()))
    def test_existing_output_refused(self):
        self.out.mkdir()
        with self.assertRaises(ValueError): pub.dispatch(self.d, 'selected', self.out, execute=True)
        self.process.assert_not_called()
    def test_source_parent_refused(self):
        with self.assertRaises(ValueError): pub.plan(self.d, 'selected', self.source.parent)
    def test_repo_output_refused(self):
        with self.assertRaises(ValueError): pub.plan(self.d, 'selected', self.repo / 'output')
    def test_failed_iteration_refused(self):
        self.check.return_value = ['changed']
        with self.assertRaises(ValueError): pub.plan(self.d, 'selected', self.out)
    def test_unselected_case_refused(self):
        with self.assertRaises(ValueError): pub.plan(self.d, 'other', self.out)
    def test_unsafe_switch_refused(self):
        self.rewrite(self.d / 'compiled-profile.json', lambda x: x['switches']['light'].update(kind='object_hide'))
        with self.assertRaises(ValueError): pub.plan(self.d, 'selected', self.out)
    def test_missing_report_retained_failure(self):
        self.process.side_effect = None
        self.process.return_value = subprocess.CompletedProcess([], 0, '', '')
        result = pub.dispatch(self.d, 'selected', self.out, execute=True)
        self.assertFalse(result['passed']); self.assertTrue((self.out / 'launch.json').is_file())
    def test_timeout_retained_failure(self):
        self.process.side_effect = subprocess.TimeoutExpired([], 1)
        result = pub.dispatch(self.d, 'selected', self.out, execute=True)
        self.assertTrue(result['timeout']); self.assertFalse(result['passed'])
    def test_source_changed_during_process(self):
        def change(*args, **kwargs):
            result = self.worker(*args, **kwargs); self.source.write_bytes(b'changed'); return result
        self.process.side_effect = change
        self.assertFalse(pub.dispatch(self.d, 'selected', self.out, execute=True)['passed'])
    def test_request_changed_during_process(self):
        def change(*args, **kwargs):
            result = self.worker(*args, **kwargs)
            (self.out / 'request.json').write_bytes(b'{}'); return result
        self.process.side_effect = change
        self.assertFalse(pub.dispatch(self.d, 'selected', self.out, execute=True)['passed'])
    def test_candidate_tamper_refused_reopen(self):
        pub.dispatch(self.d, 'selected', self.out, execute=True)
        (self.out / 'Candidate.blend').write_bytes(b'changed')
        with self.assertRaises(ValueError): pub.plan(self.d, 'selected', self.base / 'reopen', 'reopen', self.out / 'publish-report.json')
    def test_publish_provenance_tamper_refused(self):
        pub.dispatch(self.d, 'selected', self.out, execute=True)
        self.rewrite(self.out / 'request.json', lambda x: x.update(case_id='other'))
        with self.assertRaises(ValueError): pub.plan(self.d, 'selected', self.base / 'reopen', 'reopen', self.out / 'publish-report.json')
    def test_publish_report_tamper_refused_reopen(self):
        pub.dispatch(self.d, 'selected', self.out, execute=True)
        self.rewrite(self.out / 'publish-report.json', lambda x: x.update(extra='changed'))
        with self.assertRaises(ValueError): pub.plan(self.d, 'selected', self.base / 'reopen', 'reopen', self.out / 'publish-report.json')
    def test_worker_pin_changed_during_process(self):
        def change(*args, **kwargs):
            result = self.worker(*args, **kwargs)
            pub.WORKER.write_text('# changed', encoding='utf-8')
            return result
        self.process.side_effect = change
        self.assertFalse(pub.dispatch(self.d, 'selected', self.out, execute=True)['passed'])
    def test_invalid_timeout(self):
        for timeout in (True, 0, 3601, float('nan')):
            with self.assertRaises(ValueError): pub.dispatch(self.d, 'selected', self.out, timeout=timeout)

if __name__ == '__main__': unittest.main()
