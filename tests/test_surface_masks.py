import unittest
import tempfile
from pathlib import Path
import numpy as np
from scripts.make_surface_masks import control_map
from scripts.typography_composite import infer_end_frame


class SurfaceMaskTests(unittest.TestCase):
    def test_eight_second_cache_is_not_silently_truncated_to_four_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            beauty = Path(tmp) / "beauty"
            beauty.mkdir()
            for frame in [421, 660, 900]:
                (beauty / f"frame_{frame:04d}beauty.png").touch()
            self.assertEqual(infer_end_frame(Path(tmp), 421), 900)

    def test_empty_cache_cannot_determine_a_clip_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "No beauty"):
                infer_end_frame(Path(tmp), 421)

    def test_blue_and_white_do_not_become_metal(self):
        swatches = np.array([[[0.15, 0.20, 0.50], [1, 1, 1], [0, 0, 0]]], np.float32)
        result = control_map(swatches)
        np.testing.assert_array_equal(result[..., 0], 0)

    def test_gold_gets_distinct_surface_response(self):
        swatches = np.array([[[0.75, 0.65, 0.33], [0.15, 0.20, 0.50]]], np.float32)
        result = control_map(swatches)
        self.assertGreater(float(result[0, 0, 0]), 0.9)
        self.assertLess(float(result[0, 0, 1]), float(result[0, 1, 1]))

    def test_control_channels_stay_in_valid_range(self):
        rgb = np.random.default_rng(42).random((30, 30, 3), dtype=np.float32)
        result = control_map(rgb)
        self.assertEqual(result.shape, rgb.shape)
        self.assertTrue(np.isfinite(result).all())
        self.assertGreaterEqual(float(result.min()), 0)
        self.assertLessEqual(float(result.max()), 1)


if __name__ == "__main__":
    unittest.main()
