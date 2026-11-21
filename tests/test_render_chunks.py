"""Catch dropped/duplicated frame ranges before concatenating a long render."""

import unittest

from scripts.assemble_render_chunks import validate_manifest


class ChunkManifestTests(unittest.TestCase):
    def test_contiguous_prefix_and_tail(self):
        self.assertEqual(
            validate_manifest(
                {"chunks": [{"start": 1, "end": 484}, {"start": 485, "end": 1200}]}
            ),
            1200,
        )

    def test_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_manifest(
                {"chunks": [{"start": 1, "end": 484}, {"start": 486, "end": 1200}]}
            )

    def test_overlap_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_manifest(
                {"chunks": [{"start": 1, "end": 484}, {"start": 484, "end": 1200}]}
            )

    def test_empty_or_missing_start_is_rejected(self):
        for chunks in ([], [{"start": 2, "end": 1200}]):
            with self.assertRaises(ValueError):
                validate_manifest({"chunks": chunks})


if __name__ == "__main__":
    unittest.main()
