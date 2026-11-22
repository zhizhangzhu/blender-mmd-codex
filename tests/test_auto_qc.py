"""Tests for automated QC hard metrics, sparse multiframe, temporal flicker and calibration."""

import json
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from scripts import auto_qc


def _save_rgb(path, arr):
    img = Image.fromarray(np.clip(arr * 255.0, 0, 255).astype(np.uint8))
    img.save(path)


def _make_clean_toon_still(h=180, w=320):
    """Synthetic high-clarity toon-like frame: dark cool stage, crisp dark outlines, layered bright subject."""
    img = np.zeros((h, w, 3), dtype=np.float32)
    # Cool deep background with gradient
    y = np.linspace(0.06, 0.22, h, dtype=np.float32)[:, None]
    img[..., 0] = y * 0.45
    img[..., 1] = y * 0.65
    img[..., 2] = y * 1.15
    # Window glow highlight area (controlled, not clipped white)
    img[12:48, 230:295] = [0.78, 0.86, 0.94]
    # Subject torso/head region with layered shading + color accents + dark ink border
    img[30:160, 100:220] = [0.76, 0.78, 0.84]  # shaded cloth
    img[40:120, 120:195] = [0.88, 0.76, 0.70]  # warm skin/lit area
    img[115:155, 110:210] = [0.22, 0.50, 0.82]  # saturated blue accent
    img[55:75, 130:185] = [0.88, 0.72, 0.28]   # gold accent
    # Crisp dark outline grid around subject & interior folds
    for bx in (100, 101, 120, 155, 195, 219, 220):
        img[30:160, bx] = [0.05, 0.05, 0.08]
    for by in (30, 31, 75, 115, 159):
        img[by, 100:220] = [0.05, 0.05, 0.08]
    # Controlled rim highlight
    img[35:110, 214:218] = [0.92, 0.95, 0.97]
    return img


class AutoQCTests(unittest.TestCase):
    def setUp(self):
        self.preset = auto_qc.load_json(auto_qc.DEFAULT_PRESET)

    def test_clean_still_passes_and_never_approves_art(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("MMD_TEST_TEMP")) as tmp:
            p = Path(tmp) / "clean.png"
            _save_rgb(p, _make_clean_toon_still())
            res = auto_qc.eval_still(p, self.preset, rois=[[0.31, 0.16, 0.38, 0.72]])
            self.assertTrue(res["passed"], res)
            self.assertFalse(res["user_approval"])
            self.assertGreater(res["metrics"]["subject_bg_luma_separation"], 0.1)

    def test_hazy_flat_image_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("MMD_TEST_TEMP")) as tmp:
            p = Path(tmp) / "hazy.png"
            arr = np.full((180, 320, 3), 0.42, dtype=np.float32)
            arr[40:140, 100:220] = 0.50
            _save_rgb(p, arr)
            res = auto_qc.eval_still(p, self.preset)
            self.assertFalse(res["passed"])
            self.assertIn("washed_out_blacks_hazy", res["defect_tags"])
            self.assertIn("flat_hazy_contrast", res["defect_tags"])
            self.assertIn("desaturated_gray_cast", res["defect_tags"])

    def test_overbright_clipped_subject_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("MMD_TEST_TEMP")) as tmp:
            p = Path(tmp) / "overbright.png"
            arr = _make_clean_toon_still()
            arr[30:160, 100:220] = 1.0  # completely blown-out subject
            _save_rgb(p, arr)
            res = auto_qc.eval_still(p, self.preset, rois=[[0.31, 0.16, 0.38, 0.72]])
            self.assertFalse(res["passed"])
            self.assertIn("clipped_white_overbright", res["defect_tags"])
            self.assertIn("subject_clipped_white", res["defect_tags"])
            self.assertIn("subject_overbright", res["defect_tags"])

    def test_sparse_multiframe_enforces_minimum_count_and_non_video_flag(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("MMD_TEST_TEMP")) as tmp:
            paths = []
            for i in range(4):
                p = Path(tmp) / f"f{i:02d}.png"
                _save_rgb(p, _make_clean_toon_still())
                paths.append(p)
            too_few = auto_qc.eval_sparse(paths, self.preset)
            self.assertFalse(too_few["passed"])
            self.assertFalse(too_few["counts_as_video_delivery"])

            for i in range(4, 9):
                p = Path(tmp) / f"f{i:02d}.png"
                _save_rgb(p, _make_clean_toon_still())
                paths.append(p)
            ok = auto_qc.eval_sparse(paths, self.preset)
            self.assertTrue(ok["passed"], ok)
            self.assertFalse(ok["counts_as_video_delivery"])
            self.assertFalse(ok["user_approval"])

    def test_temporal_distinguishes_smooth_fade_from_flicker(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("MMD_TEST_TEMP")) as tmp:
            smooth_paths = []
            base = _make_clean_toon_still()
            for i in range(12):
                p = Path(tmp) / f"smooth_{i:02d}.png"
                _save_rgb(p, np.clip(base * (0.88 + 0.015 * i), 0, 1))
                smooth_paths.append(p)
            smooth = auto_qc.eval_temporal(smooth_paths, self.preset, fps=30)
            self.assertTrue(smooth["passed"], smooth)
            self.assertFalse(smooth["counts_as_video_delivery"])

            flicker_paths = []
            for i in range(12):
                p = Path(tmp) / f"flicker_{i:02d}.png"
                scale = 1.12 if (i % 2 == 0) else 0.72
                _save_rgb(p, np.clip(base * scale, 0, 1))
                flicker_paths.append(p)
            flicker = auto_qc.eval_temporal(flicker_paths, self.preset, fps=30)
            self.assertFalse(flicker["passed"])
            self.assertIn("temporal_luma_flicker", flicker["defect_tags"])

    def test_plan_diagnostics_bounds_and_anchor(self):
        plan = auto_qc.plan_diagnostics(1, 11899, 60.0, self.preset, sparse_count=10, anchor_frame=4290, temporal_seconds=1.5)
        self.assertFalse(plan["counts_as_video_delivery"])
        self.assertFalse(plan["encode_as_review_video"])
        self.assertEqual(plan["sparse_multiframe"]["count"], 10)
        self.assertIn(4290, plan["sparse_multiframe"]["frames"])
        self.assertEqual(plan["temporal_diagnostic"]["resolution"], [640, 360])
        self.assertGreaterEqual(plan["temporal_diagnostic"]["duration_seconds"], 1.0)
        self.assertLessEqual(plan["temporal_diagnostic"]["duration_seconds"], 2.0)

        with self.assertRaises(ValueError):
            auto_qc.plan_diagnostics(1, 1000, 60.0, self.preset, sparse_count=3)
        with self.assertRaises(ValueError):
            auto_qc.plan_diagnostics(1, 1000, 60.0, self.preset, temporal_seconds=5.0)

    def test_calibration_requires_provenance_and_reject_recall(self):
        good_cases = [
            {"id": "c1", "user_verdict": "reject", "predicted_verdict": "reject", "provenance": "2026-11-14 feedback"},
            {"id": "c2", "user_verdict": "reject", "predicted_verdict": "reject", "provenance": "2026-11-17 feedback"},
            {"id": "c3", "user_verdict": "reject", "predicted_verdict": "reject", "provenance": "2026-11-16 feedback"},
            {"id": "c4", "user_verdict": "accept", "predicted_verdict": "accept", "provenance": "historical hall v3"},
        ]
        res_ok = auto_qc.calibrate_predictions(good_cases, self.preset)
        self.assertTrue(res_ok["calibration_passed"])
        self.assertEqual(res_ok["metrics"]["reject_recall"], 1.0)
        self.assertFalse(res_ok["user_approval"])

        bad_recall = [
            {"id": "c1", "user_verdict": "reject", "predicted_verdict": "accept", "provenance": "2026-11-14 feedback"},
            {"id": "c2", "user_verdict": "reject", "predicted_verdict": "accept", "provenance": "2026-11-17 feedback"},
            {"id": "c3", "user_verdict": "reject", "predicted_verdict": "reject", "provenance": "2026-11-16 feedback"},
            {"id": "c4", "user_verdict": "accept", "predicted_verdict": "accept", "provenance": "historical hall v3"},
        ]
        res_bad = auto_qc.calibrate_predictions(bad_recall, self.preset)
        self.assertFalse(res_bad["calibration_passed"])

        with self.assertRaises(ValueError):
            auto_qc.calibrate_predictions(
                [{"id": "no-prov", "user_verdict": "reject", "predicted_verdict": "reject"}],
                self.preset,
            )


if __name__ == "__main__":
    unittest.main()
