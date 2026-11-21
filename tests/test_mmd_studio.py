"""Integration contracts for current context, evidence and read-only studio entry."""

import copy
import io
from contextlib import redirect_stdout
from unittest.mock import patch
import os
import tempfile
import unittest
from pathlib import Path

from scripts import mmd_studio, studio_registry


class StudioEntryTests(unittest.TestCase):
    def test_real_registry_context_preserves_current_scope(self):
        path = mmd_studio.ROOT / "catalog/current_state.json"
        before = path.read_bytes()
        result = mmd_studio.context("reference", "白衣 发束")
        self.assertTrue(result["capabilities"])
        self.assertEqual("reference", result["route"]["id"])
        self.assertEqual("stills_only", result["state_summary"]["render_delivery_policy"]["default"])
        self.assertEqual("pending", result["reference_studies"][0]["brief"]["review"]["art_status"])
        self.assertEqual(before, path.read_bytes())

    @patch('scripts.mmd_studio.studio_lessons.retrieve')
    def test_context_lesson_route_and_query(self, retrieve):
        retrieve.return_value={'lessons':[{'id':'bounded'}], 'skipped':[]}
        result=mmd_studio.context('lighting','face',limit=1)
        self.assertEqual(result['lessons'],[{'id':'bounded'}])
        self.assertEqual(retrieve.call_args.kwargs['route'],'lighting')
        self.assertEqual(retrieve.call_args.kwargs['query'],'face')

    @patch('scripts.mmd_studio.studio_lessons.retrieve')
    def test_audit_rejects_skipped_lessons(self,retrieve):
        retrieve.return_value={'lessons':[], 'skipped':[{'id':'changed','error':'hash mismatch'}]}
        result=mmd_studio.audit()
        self.assertFalse(result['passed'])
        self.assertIn('Lesson changed: hash mismatch',result['errors'])

    @patch('scripts.mmd_studio.audit',return_value={'passed':True})
    @patch('scripts.mmd_studio.studio_lessons.retrieve',return_value={'lessons':[],'skipped':[]})
    def test_lessons_command_read_only(self,retrieve,audit):
        with redirect_stdout(io.StringIO()) as output:
            code=mmd_studio.main(['lessons','--task','lighting','--query','face'])
        self.assertEqual(code,0)
        self.assertIn('lessons',output.getvalue())
        self.assertEqual(retrieve.call_args.args[1:3],('face','lighting'))

    def test_unknown_route_is_rejected(self):
        with self.assertRaises(ValueError):
            mmd_studio.context("invented-route")

    def test_current_artifact_verification_detects_tampering(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("MMD_TEST_TEMP")) as directory:
            project = Path(directory) / "fixture.blend"
            project.write_bytes(b"synthetic input")
            state = {"active_iteration": {"project": str(project), "project_sha256": studio_registry.digest(project), "art_status": "pending", "user_art_approval": False}}
            self.assertEqual([], mmd_studio.inspect_state(state, check_artifacts=True))
            project.write_bytes(b"changed")
            self.assertTrue(mmd_studio.inspect_state(state, check_artifacts=True))

    def test_art_status_cannot_be_approved_by_checks(self):
        state = {"active_iteration": {"project": "fixture.blend", "project_sha256": "0" * 64, "art_status": "pending", "user_art_approval": True}}
        self.assertTrue(mmd_studio.inspect_state(state))


if __name__ == "__main__":
    unittest.main()
