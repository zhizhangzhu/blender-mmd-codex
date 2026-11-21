"""Keep the editorial front/behind choice distinct from protection policies."""

import unittest
import numpy as np

from scripts.typography_composite import over, protect_layer, validate_profile


class TypographyLayerTests(unittest.TestCase):
    def setUp(self):
        self.base = np.full((1, 3, 3), 0.2, np.float32)
        self.color = np.full_like(self.base, 0.4)
        self.alpha = np.full((1, 3), 0.5, np.float32)
        self.actor = np.array([[1, 1, 0]], np.float32)
        self.face = np.array([[1, 0, 0]], np.float32)

    def test_behind_preserves_character_and_changes_background(self):
        color, alpha = protect_layer(
            self.color, self.alpha, self.actor, self.face, "behind", "none"
        )
        out = over(self.base, color, alpha)
        np.testing.assert_array_equal(out[:, 0:2], self.base[:, 0:2])
        self.assertTrue((out[:, 2] > self.base[:, 2]).all())

    def test_front_can_intentionally_cover_character(self):
        color, alpha = protect_layer(
            self.color, self.alpha, self.actor, self.face, "front", "none"
        )
        self.assertTrue((over(self.base, color, alpha) > self.base).all())

    def test_face_protection_does_not_protect_clothes(self):
        color, alpha = protect_layer(
            self.color, self.alpha, self.actor, self.face, "front", "face"
        )
        out = over(self.base, color, alpha)
        np.testing.assert_array_equal(out[:, 0], self.base[:, 0])
        self.assertTrue((out[:, 1] > self.base[:, 1]).all())

    def test_rejects_cue_overlap_and_invalid_mode(self):
        for cues in [
            [
                {"start": 0, "end": 2, "order": "front", "protect": "none"},
                {"start": 1, "end": 3, "order": "behind", "protect": "face"},
            ],
            [{"start": 0, "end": 1, "order": "invalid", "protect": "none"}],
        ]:
            with self.assertRaises(ValueError):
                validate_profile({"cues": cues})


if __name__ == "__main__":
    unittest.main()
