"""Reference preparation must not fabricate inspection, causal proof, or approval."""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.reference_study import brief, extract, main, scaffold, validate


class ReferenceStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("MMD_TEST_TEMP"))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "reference.png"
        self.source.write_bytes(b"synthetic image fixture")
        self.data = scaffold(self.source, "image", "test reference", "test")

    def analyzed(self):
        data = copy.deepcopy(self.data)
        data.update(status="analyzed", observations=[{"id": "o1", "dimension": "value", "description": "face brighter than background", "locator": "face ROI", "seen": True}],
            hypotheses=[{"id": "h1", "observation_ids": ["o1"], "explanation": "selective lighting", "test": "toggle fill", "prediction": "background unchanged", "status": "untested", "evidence_refs": []}],
            targets=[{"id": "t1", "observation_ids": ["o1"], "priority": 0, "visual_goal": "face focus", "controls": ["key/fill"], "check": "thumbnail", "reject_if": "flat skin"}])
        data["intent"]["borrow"] = ["value hierarchy"]
        return data

    def test_scaffold_is_draft_with_no_invented_observations(self):
        self.assertEqual([], validate(self.data, check_artifacts=True))
        self.assertEqual([], self.data["observations"])
        self.assertEqual("draft", self.data["status"])
        self.assertEqual("unstarted", self.data["implementation"]["status"])

    def test_analysis_requires_seen_observation_and_actionable_hypothesis(self):
        data = self.analyzed()
        self.assertEqual([], validate(data))
        data["observations"][0]["seen"] = False
        self.assertTrue(any("inspected" in e for e in validate(data)))
        data["hypotheses"][0]["prediction"] = ""
        self.assertTrue(any("prediction" in e for e in validate(data)))

    def test_unknown_observation_cannot_support_target(self):
        data = self.analyzed()
        data["targets"][0]["observation_ids"] = ["missing"]
        self.assertTrue(validate(data))

    def test_art_and_reconstruction_claims_need_provenance(self):
        self.data["review"]["art_status"] = "approved"
        self.data["implementation"]["status"] = "transferred"
        errors = validate(self.data)
        self.assertTrue(any("feedback" in e for e in errors))
        self.assertTrue(any("evidence" in e for e in errors))

    def test_tampered_source_stops_extraction_before_output_creation(self):
        self.source.write_bytes(b"changed")
        output = self.root / "extract"
        with self.assertRaises(ValueError):
            extract(self.data, output)
        self.assertFalse(output.exists())

    def test_image_extract_keeps_inspection_false_and_does_not_overwrite(self):
        output = self.root / "frames"
        manifest = extract(self.data, output)
        self.assertFalse(manifest["frames"][0]["seen"])
        self.assertTrue((output / "contact.html").is_file())
        self.assertEqual([], self.data["observations"])
        with self.assertRaises(FileExistsError):
            extract(self.data, output)

    def test_video_sampling_is_bounded_and_temporal_claims_need_scope(self):
        data = self.data
        data["kind"] = "video"
        data["shots"] = [{"id": "shot1", "start_seconds": 1, "end_seconds": 2,
            "sample_times": [0, 1.5], "events": [], "review": {"continuous": True, "scope": ""}}]
        self.assertTrue(any("outside" in e for e in validate(data)))
        self.assertTrue(any("scope" in e for e in validate(data)))
        data["shots"][0].update(sample_times=[1.1, 1.2], review={"continuous": False, "scope": ""})
        with self.assertRaises(ValueError):
            extract(data, self.root / "frames", max_frames=1)

    def test_brief_separates_untested_hypothesis_from_implementation(self):
        result = brief(self.analyzed())
        self.assertEqual("untested", result["hypotheses"][0]["status"])
        self.assertEqual("unstarted", result["implementation"]["status"])

    def test_transfer_cannot_use_duplicate_artifacts_or_invent_audio_review(self):
        self.data["implementation"].update(status="transferred", transfer_scope="new actor",
            evidence=[self.data["source"], self.data["source"]])
        self.assertTrue(any("multiple artifacts" in e for e in validate(self.data)))
        self.data["media_review"]["audio"] = {"status": "reviewed", "scope": ""}
        self.assertTrue(any("audio" in e for e in validate(self.data)))

    def test_cli_returns_json_errors_for_malformed_input_and_no_clobber(self):
        source = self.root / "bad.json"
        source.write_text("[]", encoding="utf-8")
        with patch("builtins.print"):
            self.assertEqual(1, main(["check", "--study", str(source)]))
        output = self.root / "existing.json"
        output.write_text("keep", encoding="utf-8")
        with patch("builtins.print"):
            self.assertEqual(1, main(["init", "--source", str(self.source), "--kind", "image", "--title", "test", "--id", "test", "--output", str(output)]))
        self.assertEqual("keep", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
