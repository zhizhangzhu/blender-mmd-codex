"""Synthetic-only checks; these do not validate any real Bilibili transcript."""

import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.ingest_bilibili_subtitles import (
    REPOSITORY_ROOT,
    ManifestOnlyError,
    SubtitleInputError,
    extract_body,
    ingest_subtitles,
    main,
    normalize_cues,
)


def temporary_directory():
    """Root can set CODEX_TEST_TEMP_DIR to the user's D:\\codex\\temp."""
    return tempfile.TemporaryDirectory(
        prefix="subtitle-ingest-", dir=os.environ.get("CODEX_TEST_TEMP_DIR")
    )


class SubtitleIngestTests(unittest.TestCase):
    @staticmethod
    def cue(start=0, end=1, content="合成字幕"):
        return {"from": start, "to": end, "content": content}

    def save(self, root, document, *, bom=False):
        path = Path(root) / "synthetic-input.json"
        raw = json.dumps(document, ensure_ascii=False).encode("utf-8")
        if bom:
            raw = b"\xef\xbb\xbf" + raw
        path.write_bytes(raw)
        return path, raw

    def test_supported_containers_are_explicit(self):
        cues = [self.cue()]
        for document, expected in (
            (cues, "$"),
            ({"body": cues}, "$.body"),
            ({"data": {"body": cues}}, "$.data.body"),
            ({"subtitle": {"body": cues}}, "$.subtitle.body"),
            ({"data": {"subtitle": {"body": cues}}}, "$.data.subtitle.body"),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(extract_body(document), (cues, expected))
        with self.assertRaises(SubtitleInputError):
            extract_body({"arbitrary": {"body": cues}})
        with self.assertRaises(SubtitleInputError):
            extract_body({"body": cues, "data": {"body": cues}})

    def test_full_outputs_preserve_original_text_order_duplicates_and_raw_hash(self):
        text = "  原识别，錯字保持\r\n第二行 `片段`\n\n```\n<script>不执行</script>  "
        duplicate = {**self.cue(5, 8, text), "location": 2}
        document = {
            "body": [duplicate, self.cue(1, 3, "先前时间"), duplicate],
            "cookie": "synthetic-secret-do-not-copy",
            "signed_url": "https://example.invalid/?token=synthetic",
        }
        with temporary_directory() as temporary:
            input_path, raw = self.save(temporary, document, bom=True)
            output = Path(temporary) / "delivery"
            report = ingest_subtitles(
                input_path,
                output,
                source_url="https://www.bilibili.com/video/BV1Synthetic/?p=2",
                source_label="合成AI字幕",
            )
            normalized = json.loads(
                (output / "subtitles.normalized.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                normalized["subtitles"],
                [
                    self.cue(5, 8, text),
                    self.cue(1, 3, "先前时间"),
                    self.cue(5, 8, text),
                ],
            )
            self.assertEqual(
                normalized["source"]["input_sha256"], hashlib.sha256(raw).hexdigest()
            )
            self.assertEqual(report["input_bytes"], len(raw))
            self.assertEqual(report["statistics"]["exact_duplicate_groups"], [[1, 3]])
            self.assertEqual(
                report["statistics"]["srt_content_with_blank_lines_indices"], [1, 3]
            )
            self.assertEqual(input_path.read_bytes(), raw)
            self.assertEqual(
                {path.name for path in output.iterdir()}, set(report["files"])
            )
            products = "".join(
                path.read_text(encoding="utf-8") for path in output.iterdir()
            )
            self.assertNotIn("synthetic-secret-do-not-copy", products)
            self.assertNotIn("token=synthetic", products)
            self.assertNotIn('"location"', products)
            srt = (output / "subtitles.srt").read_text(encoding="utf-8")
            self.assertTrue(srt.startswith("1\n00:00:05,000 --> 00:00:08,000\n"))
            self.assertIn(text.replace("\r\n", "\n"), srt)
            markdown = (output / "subtitles.md").read_text(encoding="utf-8")
            self.assertIn("````text\n" + text.replace("\r\n", "\n"), markdown)
            self.assertEqual(set(normalized), {"schema_version", "source", "subtitles"})

    def test_order_overlap_and_union_coverage_are_observations(self):
        body = [
            self.cue(5, 8, "A"),
            self.cue(1, 3, "B"),
            self.cue(2, 4, "C"),
            self.cue(5, 8, "A"),
            self.cue(10, 11, "D"),
        ]
        with temporary_directory() as temporary:
            input_path, _ = self.save(temporary, {"data": {"body": body}})
            report = ingest_subtitles(
                input_path, Path(temporary) / "delivery", expected_duration=15
            )
        stats = report["statistics"]
        self.assertEqual(stats["input_cue_count"], 5)
        self.assertEqual(stats["output_cue_count"], 5)
        self.assertEqual(stats["input_first_start_seconds"], 5)
        self.assertEqual(stats["minimum_start_seconds"], 1)
        self.assertEqual(stats["maximum_end_seconds"], 11)
        self.assertEqual(stats["covered_seconds"], 7)
        self.assertEqual(stats["coverage_span_seconds"], 10)
        self.assertEqual(
            stats["internal_gaps"],
            [{"from": 4, "to": 5, "seconds": 1}, {"from": 8, "to": 10, "seconds": 2}],
        )
        self.assertEqual(stats["internal_gap_seconds"], 3)
        self.assertEqual(stats["start_regression_input_indices"], [2])
        self.assertEqual(stats["exact_duplicate_groups"], [[1, 4]])
        self.assertEqual(
            stats["overlap_witnesses"],
            [
                {"input_index": 3, "against_input_index": 2, "from": 2, "to": 3},
                {"input_index": 4, "against_input_index": 1, "from": 5, "to": 8},
            ],
        )
        self.assertEqual(stats["trailing_gap_to_expected_seconds"], 4)
        self.assertEqual(stats["completeness"], "unassessed")

    def test_zero_to_duration_and_touching_cues_do_not_prove_completeness(self):
        with temporary_directory() as temporary:
            input_path, _ = self.save(temporary, [self.cue(0, 1), self.cue(1, 2)])
            report = ingest_subtitles(
                input_path, Path(temporary) / "delivery", expected_duration=2
            )
        stats = report["statistics"]
        self.assertEqual(stats["internal_gaps"], [])
        self.assertEqual(stats["overlap_witnesses"], [])
        self.assertEqual(stats["covered_seconds"], 2)
        self.assertEqual(stats["trailing_gap_to_expected_seconds"], 0)
        self.assertEqual(stats["completeness"], "unassessed")

    def test_manifest_is_rejected_without_fetch_or_false_transcript(self):
        manifests = [
            {
                "data": {
                    "subtitle": {
                        "subtitles": [
                            {
                                "subtitle_url": "//example.invalid/subtitle.json?token=synthetic-secret"
                            }
                        ]
                    }
                }
            },
            ["https://example.invalid/subtitle.json?token=synthetic-secret"],
            [
                {
                    "subtitle_url": "//example.invalid/subtitle.json?token=synthetic-secret"
                }
            ],
            {
                "body": [
                    {
                        "subtitle_url": "//example.invalid/subtitle.json?token=synthetic-secret"
                    }
                ]
            },
        ]
        with temporary_directory() as temporary:
            for index, manifest in enumerate(manifests):
                with self.subTest(index=index):
                    input_path, _ = self.save(temporary, manifest)
                    output = Path(temporary) / f"delivery-{index}"
                    with self.assertRaises(ManifestOnlyError) as raised:
                        ingest_subtitles(input_path, output)
                    self.assertNotIn("synthetic-secret", str(raised.exception))
                    self.assertFalse(output.exists())

    def test_invalid_cues_abort_whole_export_without_dropping_bad_rows(self):
        invalid = [
            self.cue(-1, 1),
            self.cue(0, -1),
            self.cue(1, 1),
            self.cue(2, 1),
            self.cue(True, 2),
            self.cue(0, False),
            self.cue("0", 1),
            self.cue(float("nan"), 1),
            self.cue(0, float("inf")),
            self.cue(0, 1, 123),
            {"from": 0, "to": 1},
            "not an object",
        ]
        with temporary_directory() as temporary:
            for index, bad in enumerate(invalid):
                with self.subTest(index=index):
                    input_path, _ = self.save(temporary, {"body": [self.cue(), bad]})
                    output = Path(temporary) / f"delivery-{index}"
                    with self.assertRaises(SubtitleInputError):
                        ingest_subtitles(input_path, output)
                    self.assertFalse(output.exists())

    def test_empty_wrong_type_or_ambiguous_body_is_never_successful(self):
        with temporary_directory() as temporary:
            for index, document in enumerate(
                (
                    [],
                    {"body": []},
                    {"data": {"body": "[]"}},
                    {"body": [self.cue()], "data": {"body": [self.cue()]}},
                )
            ):
                with self.subTest(index=index):
                    input_path, _ = self.save(temporary, document)
                    output = Path(temporary) / f"delivery-{index}"
                    with self.assertRaises(SubtitleInputError):
                        ingest_subtitles(input_path, output)
                    self.assertFalse(output.exists())

    def test_rounding_tiny_cues_and_whitespace_text_are_preserved_and_reported(self):
        body = [self.cue(0.0005, 0.0006, " "), self.cue(59.9995, 60.0005, "毫秒边界")]
        with temporary_directory() as temporary:
            input_path, _ = self.save(temporary, {"body": body})
            output = Path(temporary) / "delivery"
            report = ingest_subtitles(input_path, output)
            srt = (output / "subtitles.srt").read_text(encoding="utf-8")
            normalized = json.loads(
                (output / "subtitles.normalized.json").read_text(encoding="utf-8")
            )
        self.assertIn("00:00:00,001 --> 00:00:00,002\n \n", srt)
        self.assertIn("00:01:00,000 --> 00:01:00,001", srt)
        self.assertEqual(normalized["subtitles"], body)
        self.assertEqual(
            report["srt_export"]["extended_to_one_millisecond_input_indices"], [1]
        )
        self.assertEqual(report["statistics"]["whitespace_only_content_indices"], [1])

    def test_existing_file_and_directory_are_never_overwritten(self):
        with temporary_directory() as temporary:
            input_path, _ = self.save(temporary, {"body": [self.cue()]})
            directory = Path(temporary) / "existing-directory"
            directory.mkdir()
            sentinel = directory / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            existing_file = Path(temporary) / "existing-file"
            existing_file.write_text("keep", encoding="utf-8")
            for target in (directory, existing_file):
                with self.subTest(target=target), self.assertRaises(FileExistsError):
                    ingest_subtitles(input_path, target)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertEqual(existing_file.read_text(encoding="utf-8"), "keep")
            self.assertEqual(list(directory.iterdir()), [sentinel])

    def test_repository_output_is_rejected_before_any_write(self):
        with temporary_directory() as temporary:
            input_path, _ = self.save(temporary, {"body": [self.cue()]})
            target = (
                REPOSITORY_ROOT / "__synthetic_subtitle_output_must_not_be_created__"
            )
            self.assertFalse(target.exists())
            with self.assertRaises(ValueError):
                ingest_subtitles(input_path, target)
            self.assertFalse(target.exists())

    def test_signed_subtitle_urls_and_non_video_sources_are_not_accepted(self):
        with temporary_directory() as temporary:
            input_path, _ = self.save(temporary, {"body": [self.cue()]})
            for index, url in enumerate(
                (
                    "https://example.invalid/subtitle.json?auth_key=synthetic",
                    "https://www.bilibili.com/video/BV1Synthetic/?token=synthetic",
                    "https://user:password@www.bilibili.com/video/BV1Synthetic/",
                )
            ):
                with self.subTest(index=index):
                    output = Path(temporary) / f"delivery-{index}"
                    with self.assertRaises(SubtitleInputError):
                        ingest_subtitles(input_path, output, source_url=url)
                    self.assertFalse(output.exists())

    def test_invalid_expected_duration_is_rejected_and_video_overrun_is_reported(self):
        with temporary_directory() as temporary:
            input_path, _ = self.save(temporary, {"body": [self.cue(1, 3)]})
            for index, duration in enumerate((0, -1, float("nan"), float("inf"), True)):
                with self.subTest(index=index):
                    output = Path(temporary) / f"invalid-{index}"
                    with self.assertRaises(SubtitleInputError):
                        ingest_subtitles(input_path, output, expected_duration=duration)
                    self.assertFalse(output.exists())
            report = ingest_subtitles(
                input_path, Path(temporary) / "overrun", expected_duration=2
            )
            self.assertEqual(report["statistics"]["end_beyond_expected_seconds"], 1)
            self.assertEqual(report["statistics"]["completeness"], "unassessed")

    def test_malformed_utf8_json_and_duplicate_keys_are_rejected(self):
        cases = [
            b"\xff\xfe",
            b"<html>not subtitles</html>",
            b'{"body": [], "body": [{"from": 0, "to": 1, "content": "x"}]}',
            b'{"body": [{"from": 0, "from": 1, "to": 2, "content": "x"}]}',
            b'{"body": [{"from": 0, "to": 1, "content": "\\ud800"}]}',
        ]
        with temporary_directory() as temporary:
            path = Path(temporary) / "synthetic-input.json"
            for index, raw in enumerate(cases):
                with self.subTest(index=index):
                    path.write_bytes(raw)
                    output = Path(temporary) / f"delivery-{index}"
                    with self.assertRaises(SubtitleInputError):
                        ingest_subtitles(path, output)
                    self.assertFalse(output.exists())

    def test_cli_logs_only_compact_summary_not_subtitle_text(self):
        with temporary_directory() as temporary:
            input_path, _ = self.save(
                temporary, {"body": [self.cue(content="合成全文不出现在日志")]}
            )
            output = Path(temporary) / "delivery"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(["--input", str(input_path), "--output-dir", str(output)])
            self.assertEqual(result, 0)
            self.assertNotIn("合成全文不出现在日志", stdout.getvalue())
            self.assertEqual(json.loads(stdout.getvalue())["cue_count"], 1)
            with (
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                main(["--input", str(input_path), "--output-dir", str(output)])
            self.assertEqual(raised.exception.code, 2)

    def test_numeric_strings_are_not_silently_coerced(self):
        with self.assertRaises(SubtitleInputError):
            normalize_cues([self.cue("0.5", 1)])


if __name__ == "__main__":
    unittest.main()
