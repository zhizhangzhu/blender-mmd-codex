import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.style_presets import ROOT, load_package
from scripts.style_post import apply_post


class StyleRecipeTests(unittest.TestCase):
    def test_catalog_contains_both_aspects_for_each_variant(self):
        catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
        for family in catalog["families"].values():
            for paths in family["variants"].values():
                recipes = [load_package(ROOT / p) for p in paths]
                self.assertEqual(
                    {r["aspect"] for r in recipes}, {"portrait", "landscape"}
                )

    def test_rejects_camera_aspect_mismatch(self):
        path = ROOT / "packages" / "gosari-portrait-v1.json"
        package = json.loads(path.read_text(encoding="utf-8"))
        for key in ["render", "post", "typography"]:
            package[key] = str((path.parent / package[key]).resolve())
        package["camera"]["strategy"] = "landscape"
        with tempfile.TemporaryDirectory() as tmp:
            wrong = Path(tmp) / "wrong.json"
            wrong.write_text(json.dumps(package), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Camera"):
                load_package(wrong)

    def test_graphic_background_preserves_opaque_subject_without_grade(self):
        recipe = load_package(ROOT / "packages" / "guanhaizi-graphic-landscape-v1.json")
        recipe["post"]["grade"]["mix"] = 0
        recipe["layout"]["border_height"] = 0
        rgb = np.full((90, 160, 3), 0.35, np.float32)
        matte = np.zeros((90, 160), np.float32)
        matte[20:70, 60:100] = 1
        out = apply_post(rgb, matte, matte, 0, recipe)
        np.testing.assert_allclose(out[matte == 1], rgb[matte == 1], atol=1e-6)
        self.assertGreater(float(np.abs(out[matte == 0] - rgb[matte == 0]).mean()), 0.1)

    def test_post_rejects_using_portrait_recipe_on_landscape_picture(self):
        recipe = load_package(ROOT / "packages" / "guanhaizi-graphic-portrait-v1.json")
        image = np.zeros((90, 160, 3), np.float32)
        matte = np.zeros((90, 160), np.float32)
        with self.assertRaisesRegex(ValueError, "aspect"):
            apply_post(image, matte, matte, 0, recipe)


if __name__ == "__main__":
    unittest.main()
