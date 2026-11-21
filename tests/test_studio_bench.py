import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from scripts import studio_bench as bench


class BenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'source.blend'
        self.source.write_bytes(b'protected')
        self.profile = self.base / 'profile.json'
        self.profile.write_text('{}')
        self.output = self.base / 'new'
        executable = self.base / 'blender.exe'
        executable.write_bytes(b'fake')
        self.runtime = dict(executable=str(executable), user_config=str(self.base), user_scripts=str(self.base), version='5.3', build_hash='abc')

    def run_dispatch(self, **kwargs):
        return bench.dispatch(self.runtime, 'inspect', self.profile, self.source, self.output, **kwargs)

    def test_command(self):
        args, env = bench.command(self.runtime, 'render', self.profile, self.output)
        self.assertEqual(args[1:8], ['--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', str(bench.WORKER)])
        self.assertEqual(env['BLENDER_USER_CONFIG'], str(self.base))
        self.assertNotIn(str(self.source), args)

    @patch.object(bench.subprocess, 'run')
    def test_plan_does_not_execute_or_write(self, run):
        self.assertEqual(self.run_dispatch()['execution'], 'not_dispatched')
        run.assert_not_called()
        self.assertFalse(self.output.exists())

    @patch.object(bench.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', ''))
    def test_missing_report_fails(self, run):
        self.assertFalse(self.run_dispatch(execute=True)['passed'])
        self.assertTrue((self.output / 'launch.json').exists())

    @patch.object(bench.subprocess, 'run', side_effect=subprocess.TimeoutExpired([], 1))
    def test_timeout_preserves_source(self, run):
        report = self.run_dispatch(execute=True)
        self.assertTrue(report['timeout'])
        self.assertFalse(report['passed'])
        self.assertEqual(self.source.read_bytes(), b'protected')

    def test_no_overwrite_or_ancestor(self):
        self.output.mkdir()
        with self.assertRaises(ValueError):
            self.run_dispatch(execute=True)
        with self.assertRaises(ValueError):
            bench.dispatch(self.runtime, 'inspect', self.profile, self.source, self.base, execute=True)

    @patch.object(bench.subprocess, 'run')
    def test_worker_success_and_source_change(self, run):
        def process(*args, **kwargs):
            (self.output / 'report.json').write_text(json.dumps({'passed': True}))
            self.source.write_bytes(b'changed')
            return subprocess.CompletedProcess([], 0, '', '')
        run.side_effect = process
        self.assertFalse(self.run_dispatch(execute=True)['passed'])

    def test_invalid_timeouts(self):
        for timeout in (True, False, float('nan'), float('inf'), 0, 3601):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.run_dispatch(timeout=timeout)

    @patch.object(bench.subprocess, 'run')
    def test_profile_change_and_unicode_output(self, run):
        def process(*args, **kwargs):
            self.assertEqual(kwargs['encoding'], 'utf-8')
            self.assertEqual(kwargs['errors'], 'replace')
            (self.output / 'report.json').write_text('{"passed": true}')
            self.profile.write_text('{"changed": true}')
            return subprocess.CompletedProcess([], 0, '\u4e2d\u6587', '')
        run.side_effect = process
        self.assertFalse(self.run_dispatch(execute=True)['passed'])
        self.assertEqual((self.output / 'stdout.log').read_text(encoding='utf-8'), '\u4e2d\u6587')
