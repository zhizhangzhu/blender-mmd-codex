"""Protect deduplication, bounded resumption and evidence-based stage claims."""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.learning_queue import (
    DEFAULT,
    blocked,
    canonical_url,
    digest,
    main,
    plan,
    validate,
)


class LearningQueueTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(DEFAULT.read_text(encoding="utf-8"))

    def test_current_queue_is_valid_and_does_not_claim_unrun_experiments(self):
        self.assertEqual([], validate(self.data))
        self.assertTrue(all(c["status"] == "hypothesis" for c in self.data["cards"]))
        self.assertTrue(all(not c["evidence"] for c in self.data["cards"]))

    def test_tracking_and_sections_do_not_make_new_sources_but_versions_do(self):
        url = "https://github.com/owner/repo/blob/v1/a.md"
        self.assertEqual(url, canonical_url(url + "?utm_source=study#hair"))
        self.assertEqual(
            url, canonical_url("https://raw.githubusercontent.com/owner/repo/v1/a.md")
        )
        self.assertNotEqual(
            canonical_url(url), canonical_url(url.replace("/v1/", "/v2/"))
        )
        self.assertNotEqual(
            canonical_url(url + "?version=1"), canonical_url(url + "?version=2")
        )

    def test_duplicate_source_is_detected_across_raw_and_blob_forms(self):
        duplicate = copy.deepcopy(self.data["sources"][3])
        duplicate["id"] = "duplicate"
        duplicate["url"] = (
            duplicate["url"]
            .replace("github.com/", "raw.githubusercontent.com/")
            .replace("/blob/", "/")
            + "#outline"
        )
        self.data["sources"].append(duplicate)
        self.assertTrue(any("Duplicate canonical" in e for e in validate(self.data)))

    def test_cannot_skip_from_reading_to_motion_without_frozen_inputs_and_outputs(self):
        card = self.data["cards"][0]
        card["status"] = "motion_passed"
        # Make the missing-input condition explicit; newly researched cards can
        # legitimately already point at a frozen production baseline.
        card["baseline"]["sha256"] = None
        errors = validate(self.data)
        self.assertTrue(any("baseline SHA256" in e for e in errors))
        self.assertTrue(any("missing evidence kinds" in e for e in errors))

    def test_passed_stage_checks_actual_file_hashes(self):
        with tempfile.TemporaryDirectory(
            dir=os.environ.get("MMD_TEST_TEMP")
        ) as directory:
            baseline = Path(directory) / "baseline.blend"
            report = Path(directory) / "still.json"
            artifact = Path(directory) / "frame.png"
            baseline.write_bytes(b"synthetic-input-not-a-blend")
            artifact.write_bytes(b"synthetic-output-not-a-png")
            card = self.data["cards"][0]
            report.write_text(
                json.dumps(
                    {
                        "card_id": card["id"],
                        "baseline_sha256": digest(baseline),
                        "stage": "still",
                        "result": "passed",
                        "scope": "synthetic unit fixture only",
                        "artifacts": [
                            {"path": str(artifact), "sha256": digest(artifact)}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            card.update(
                status="still_passed",
                baseline={
                    "kind": "production_blend",
                    "path": str(baseline),
                    "sha256": digest(baseline),
                },
                evidence=[
                    {"kind": "still", "path": str(report), "sha256": digest(report)}
                ],
            )
            self.assertEqual([], validate(self.data, check_artifacts=True))
            wrong = json.loads(report.read_text(encoding="utf-8"))
            wrong.update(card_id="other-card", result="failed")
            report.write_text(json.dumps(wrong), encoding="utf-8")
            card["evidence"][0]["sha256"] = digest(report)
            self.assertTrue(
                any(
                    "this card/baseline/stage" in e
                    for e in validate(self.data, check_artifacts=True)
                )
            )
            report.write_text("changed", encoding="utf-8")
            self.assertTrue(
                any(
                    "evidence hash mismatch" in e
                    for e in validate(self.data, check_artifacts=True)
                )
            )
            # Integrity cannot certify art; fixture is intentionally not a Blender experiment.

    def test_copied_implementation_requires_version_and_license_before_passing(self):
        card = self.data["cards"][0]
        card["status"] = "still_passed"
        card["implementation_sources"] = [card["source_ids"][0]]
        self.assertTrue(any("revision/license" in e for e in validate(self.data)))
        self.data["sources"][0]["revision_locked"] = True
        self.assertTrue(any("locked revision needs" in e for e in validate(self.data)))

    def test_selection_manifest_and_unread_sources_cannot_support_passed_stage(self):
        card = self.data["cards"][-1]
        card["status"] = "still_passed"
        card["baseline"]["kind"] = "selection_manifest"
        source = next(
            s for s in self.data["sources"] if s["id"] == card["source_ids"][0]
        )
        source["reading"]["level"] = "discovered"
        errors = validate(self.data)
        self.assertTrue(any("selection manifest" in e for e in errors))
        self.assertTrue(any("unread sources" in e for e in errors))

    def test_unknown_or_cyclic_dependencies_are_rejected(self):
        a, b = self.data["cards"][:2]
        a["depends_on"] = [b["id"]]
        b["depends_on"] = [a["id"]]
        self.assertTrue(any("Cyclic" in e for e in validate(self.data)))
        b["depends_on"] = ["missing"]
        self.assertTrue(
            any("unknown/duplicate dependency" in e for e in validate(self.data))
        )

    def test_plan_is_bounded_and_skips_closed_or_waiting_work(self):
        self.assertEqual(3, len(plan(self.data)))
        first, second = self.data["cards"][:2]
        first["status"] = "rejected"
        second["depends_on"] = [first["id"]]
        ids = {c["id"] for c in plan(self.data, 10)}
        self.assertNotIn(first["id"], ids)
        self.assertNotIn(second["id"], ids)
        self.assertEqual(
            first["status"], blocked(self.data)[0]["waiting_for"][0]["status"]
        )

    def test_next_action_advances_to_the_next_stage(self):
        first = self.data["cards"][0]
        first["status"] = "still_passed"
        actions = {
            c["id"]: c["next_action"] for c in plan(self.data, len(self.data["cards"]))
        }
        self.assertTrue(actions[first["id"]].startswith("motion:"))

    def test_report_never_overwrites_an_existing_file(self):
        with tempfile.TemporaryDirectory(
            dir=os.environ.get("MMD_TEST_TEMP")
        ) as directory:
            path = Path(directory) / "report.json"
            path.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                main(["check", "--output", str(path)])
            self.assertEqual("existing", path.read_text(encoding="utf-8"))

    def test_static_plan_skips_motion_without_upgrading_evidence(self):
        first = self.data["cards"][0]
        first["status"] = "still_passed"
        before = copy.deepcopy(self.data)
        selected = next(c for c in plan(self.data, 10, "stills") if c["id"] == first["id"])
        self.assertTrue(selected["next_action"].startswith("reopen:"))
        self.assertTrue(selected["motion_not_implied"])
        self.assertEqual(self.data, before)

    def test_static_reopen_requires_real_reports_but_not_motion(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("MMD_TEST_TEMP")) as directory:
            baseline = Path(directory) / "baseline.blend"
            artifact = Path(directory) / "frame.png"
            baseline.write_bytes(b"synthetic input")
            artifact.write_bytes(b"synthetic image")
            card = self.data["cards"][0]
            card.update(validation_scope="stills", status="reopen_passed",
                        baseline={"kind": "production_blend", "path": str(baseline), "sha256": digest(baseline)}, evidence=[])
            card["checks"].pop("motion", None)
            for stage in ("still", "reopen"):
                report = Path(directory) / f"{stage}.json"
                report.write_text(json.dumps({"card_id": card["id"], "baseline_sha256": digest(baseline),
                    "stage": stage, "result": "passed", "scope": "synthetic static-only fixture",
                    "artifacts": [{"path": str(artifact), "sha256": digest(artifact)}]}), encoding="utf-8")
                card["evidence"].append({"kind": stage, "path": str(report), "sha256": digest(report)})
            self.assertEqual([], validate(self.data, check_artifacts=True))
            card["validation_scope"] = "motion"
            self.assertTrue(any("missing evidence kinds" in e for e in validate(self.data)))


if __name__ == "__main__":
    unittest.main()
