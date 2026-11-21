"""Keep task navigation scoped and prevent stale or executable-looking references."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.knowledge_route import DEFAULT, select, validate


class KnowledgeRouteTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(DEFAULT.read_text(encoding="utf-8"))

    def test_real_registry_and_keyframing_alias(self):
        self.assertEqual(validate(self.data), [])
        self.assertEqual(select(self.data, " K帧 ")["id"], "motion")
        self.assertEqual(select(self.data, "LIGHTING")["id"], "lighting")
        self.assertIsNone(select(self.data, "unrelated"))

    def test_duplicate_alias_is_ambiguous_and_rejected(self):
        data = copy.deepcopy(self.data)
        data["routes"][1]["aliases"].append("lighting")
        self.assertTrue(any("Duplicate" in e for e in validate(data)))

    def test_stale_and_outside_paths_are_rejected(self):
        data = copy.deepcopy(self.data)
        data["common_read"] = ["missing-route-file.md", "../outside.md"]
        errors = validate(data)
        self.assertTrue(any("Missing" in e for e in errors))
        self.assertTrue(any("escapes" in e for e in errors))

    def test_tool_must_state_mode_and_scope(self):
        data = copy.deepcopy(self.data)
        data["routes"][0]["tools"][0]["mode"] = "ready_to_run"
        self.assertTrue(any("Unclassified" in e for e in validate(data)))

    def test_reference_check_does_not_execute_python(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = copy.deepcopy(self.data)
            data["common_read"] = []
            data["state_contract"]["runtime"] = "do_not_run.py"
            data["routes"] = [copy.deepcopy(data["routes"][-1])]
            data["routes"][0]["read"] = ["do_not_run.py"]
            data["routes"][0]["parameters"] = []
            data["routes"][0]["tools"] = []
            (root / "do_not_run.py").write_text(
                "raise RuntimeError('executed')", encoding="utf-8"
            )
            self.assertEqual(validate(data, root), [])


if __name__ == "__main__":
    unittest.main()
