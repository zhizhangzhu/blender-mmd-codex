"""Protect current art feedback and portable research links from regressions."""

import copy
import os
import tempfile
import unittest
from pathlib import Path

from scripts.build_gallery import ROOT, apply_current_state, document_html


class KnowledgeRegistryTests(unittest.TestCase):
    def test_legacy_packager_cannot_erase_revision_request_or_approve_latest(self):
        catalog = {
            "entries": [
                {"id": "latest", "adopted": True, "limits": ["Old pending review"]},
                {"id": "older", "adopted": True, "limits": []},
            ]
        }
        state = {
            "as_of": "2026-11-13",
            "latest_review": {
                "entry_id": "latest",
                "art_status": "revision_requested",
                "user_feedback": "Improve character lighting",
            },
        }
        apply_current_state(catalog, state)
        first = copy.deepcopy(catalog)
        apply_current_state(catalog, state)
        self.assertEqual(first, catalog)
        self.assertFalse(catalog["entries"][0]["adopted"])
        self.assertTrue(catalog["entries"][1]["adopted"])
        self.assertEqual(
            catalog["entries"][0]["art_review"]["status"], "revision_requested"
        )

    def test_research_ledger_is_an_actual_packaged_download(self):
        with tempfile.TemporaryDirectory(
            dir=os.environ.get("MMD_TEST_TEMP")
        ) as directory:
            output = Path(directory)
            rendered = document_html(
                "[ledger](research/CHARACTER_SOURCE_LEDGER.json)", output
            )
            target = output / "downloads/docs/research/CHARACTER_SOURCE_LEDGER.json"
            self.assertIn(
                'href="downloads/docs/research/CHARACTER_SOURCE_LEDGER.json"', rendered
            )
            self.assertEqual(
                target.read_bytes(),
                (ROOT / "docs/research/CHARACTER_SOURCE_LEDGER.json").read_bytes(),
            )

    def test_unknown_local_or_executable_links_are_not_enabled(self):
        rendered = document_html("[bad](../../missing.json) [script](javascript:alert)")
        self.assertNotIn("href=", rendered)
        self.assertIn('aria-disabled="true"', rendered)

    def test_external_markdown_is_not_mistaken_for_a_local_document(self):
        rendered = document_html("[source](https://example.org/QUALITY_GATES.md)")
        self.assertIn('href="https://example.org/QUALITY_GATES.md"', rendered)
        self.assertNotIn("#learn/", rendered)


if __name__ == "__main__":
    unittest.main()
