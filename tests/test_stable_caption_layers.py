"""Regression cases for the reported split-order and black-letter cutout issues."""

import unittest

import numpy as np

from scripts.stable_caption_layers import composite, extract_layer


class StableCaptionTests(unittest.TestCase):
    def test_opaque_card_preserves_black_letter_interior(self):
        source = np.zeros((20, 30, 3), np.float32)
        source[3:17, 3:27] = 1
        source[6:14, 12:17] = 0
        color, alpha = extract_layer(source, "plate", [1, 1, 1])
        self.assertEqual(alpha[9, 14], 1)
        self.assertEqual(float(color[9, 14].max()), 0)
        self.assertEqual(alpha[0, 0], 0)

    def test_glyph_hole_remains_transparent(self):
        source = np.zeros((20, 30, 3), np.float32)
        source[3:17, 3:27] = 1
        source[6:14, 6:24] = 0
        _, alpha = extract_layer(source, "glyph", [1, 1, 1])
        self.assertEqual(alpha[9, 14], 0)

    def test_colored_plate_ink_remains_opaque_and_not_punched_out(self):
        source = np.zeros((20, 30, 3), np.float32)
        source[3:17, 3:27] = 1
        source[3:17, 12:17] = 0
        palette = {
            "light_stops_srgb": [[0.4, 0.7, 1], [1, 0.75, 0.3]],
            "dark_stops_srgb": [[0.03, 0.1, 0.25], [0.3, 0.12, 0.02]],
        }
        color, alpha = extract_layer(source, "plate", [1, 1, 1], palette)
        self.assertEqual(alpha[9, 14], 1)
        self.assertGreater(float(color[9, 14].max()), 0)
        self.assertLess(float(color[9, 14].max()), float(color[9, 7].max()))
        self.assertEqual(alpha[0, 0], 0)

    def test_letter_touching_card_edges_does_not_split_opaque_plate(self):
        source = np.zeros((20, 30, 3), np.float32)
        source[3:17, 3:27] = 1
        source[3:17, 12:17] = 0
        color, alpha = extract_layer(source, "plate", [1, 1, 1])
        self.assertEqual(alpha[9, 14], 1)
        self.assertEqual(float(color[9, 14].max()), 0)

    def test_front_group_is_invariant_to_face_or_actor_coverage(self):
        base = np.full((2, 3, 3), 0.25, np.float32)
        alpha = np.full((2, 3), 0.8, np.float32)
        color = np.full_like(base, 0.5)
        a = composite(base, color, alpha, np.zeros((2, 3), np.float32), "front")
        b = composite(base, color, alpha, np.ones((2, 3), np.float32), "front")
        np.testing.assert_array_equal(a, b)

    def test_behind_protects_opaque_actor_and_has_continuous_edges(self):
        base = np.full((1, 3, 3), 0.25, np.float32)
        alpha = np.ones((1, 3), np.float32)
        color = np.full_like(base, 0.8)
        mask = np.array([[1, 0.49, 0.51]], np.float32)
        output = composite(base, color, alpha, mask, "behind")
        np.testing.assert_allclose(output[0, 0], base[0, 0], atol=1e-6)
        self.assertLess(float(np.abs(output[0, 1] - output[0, 2]).max()), 0.02)


if __name__ == "__main__":
    unittest.main()
