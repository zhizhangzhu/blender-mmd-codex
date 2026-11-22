"""Automated hard-metric QC, sparse multiframe checks, low-res temporal diagnostics and judge calibration.

Read-only image/sequence analyzer. Never modifies .blend files, never renders video deliveries,
and never grants user art approval (SPEC ART-01 / QC-01 / SCOPE-01).
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRESET = ROOT / "presets/qc/auto-qc-v1.json"
LIMITS = (
    "Automated hard metrics and diagnostic calibration only; screens obvious defects and ranks candidates. "
    "Cannot certify artistic quality or replace user approval (ART-01); diagnostic plans are not video deliveries (SCOPE-01)."
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rgb_float(path):
    """Load an image as float32 RGB in [0, 1]."""
    img = Image.open(Path(path)).convert("RGB")
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr


def rgb_to_luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def rgb_to_saturation(rgb):
    cmax = np.max(rgb, axis=-1)
    cmin = np.min(rgb, axis=-1)
    delta = cmax - cmin
    return np.where(cmax > 1e-6, delta / np.maximum(cmax, 1e-6), 0.0)


def parse_roi(spec):
    parts = [float(x.strip()) for x in spec.split(",")]
    if len(parts) != 4:
        raise ValueError(f"ROI must have 4 comma-separated normalized numbers x,y,w,h: {spec}")
    x, y, w, h = parts
    if not (0.0 <= x < 1.0 and 0.0 <= y < 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
        raise ValueError(f"ROI out of [0,1] bounds: {spec}")
    return [x, y, w, h]


def build_subject_mask(height, width, rois=None, mask_path=None):
    if mask_path:
        m = Image.open(Path(mask_path)).convert("L")
        if m.size != (width, height):
            m = m.resize((width, height), Image.NEAREST)
        return (np.asarray(m, dtype=np.float32) / 255.0) >= 0.5
    if not rois:
        return None
    mask = np.zeros((height, width), dtype=bool)
    for x, y, w, h in rois:
        x0 = max(0, min(width - 1, int(round(x * width))))
        y0 = max(0, min(height - 1, int(round(y * height))))
        x1 = max(x0 + 1, min(width, int(round((x + w) * width))))
        y1 = max(y0 + 1, min(height, int(round((y + h) * height))))
        mask[y0:y1, x0:x1] = True
    return mask


def compute_still_metrics(rgb, cfg, subject_mask=None):
    luma = rgb_to_luma(rgb)
    sat = rgb_to_saturation(rgb)
    p01, p05, p50, p95 = [float(v) for v in np.percentile(luma, [1, 5, 50, 95])]
    luma_mean = float(np.mean(luma))
    luma_std = float(np.std(luma))
    dr = p95 - p05
    clip_thr = float(cfg.get("clipped_white_threshold", 0.985))
    hi_thr = float(cfg.get("highlight_threshold", 0.85))
    clipped_white = float(np.mean(luma >= clip_thr))
    highlight_ratio = float(np.mean(luma >= hi_thr))
    sat_mean = float(np.mean(sat))
    sat_p90 = float(np.percentile(sat, 90))

    # Edge / dark outline proxy & sharpness via Sobel + Laplacian on luma
    gx = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.hypot(gx, gy)
    dark_edge_density = float(np.mean((grad >= 0.18) & (luma <= 0.48)))
    lap = cv2.Laplacian(luma, cv2.CV_32F, ksize=3)
    lap_var = float(np.var(lap))

    metrics = {
        "width": int(rgb.shape[1]),
        "height": int(rgb.shape[0]),
        "luma_mean": round(luma_mean, 5),
        "luma_std": round(luma_std, 5),
        "luma_p01": round(p01, 5),
        "luma_p05": round(p05, 5),
        "luma_p50": round(p50, 5),
        "luma_p95": round(p95, 5),
        "dynamic_range_p95_p05": round(dr, 5),
        "clipped_white_ratio": round(clipped_white, 5),
        "highlight_ratio": round(highlight_ratio, 5),
        "saturation_mean": round(sat_mean, 5),
        "saturation_p90": round(sat_p90, 5),
        "dark_edge_density": round(dark_edge_density, 5),
        "laplacian_sharpness": round(lap_var, 6),
    }

    if subject_mask is not None and np.any(subject_mask) and np.any(~subject_mask):
        subj_luma = luma[subject_mask]
        bg_luma = luma[~subject_mask]
        subj_mean = float(np.mean(subj_luma))
        bg_mean = float(np.mean(bg_luma))
        metrics["subject_luma_mean"] = round(subj_mean, 5)
        metrics["subject_luma_p90"] = round(float(np.percentile(subj_luma, 90)), 5)
        metrics["background_luma_mean"] = round(bg_mean, 5)
        metrics["subject_bg_luma_separation"] = round(abs(subj_mean - bg_mean), 5)
        metrics["subject_clipped_white_ratio"] = round(float(np.mean(subj_luma >= clip_thr)), 5)
        metrics["subject_coverage"] = round(float(np.mean(subject_mask)), 5)
    return metrics


def evaluate_still_metrics(metrics, cfg):
    checks = []
    defects = []

    def check_min(name, val, limit, tag, severity="fail"):
        ok = val >= limit
        checks.append({"metric": name, "value": val, "op": ">=", "limit": limit, "passed": ok, "severity": "ok" if ok else severity})
        if not ok:
            defects.append(tag)

    def check_max(name, val, limit, tag, severity="fail"):
        ok = val <= limit
        checks.append({"metric": name, "value": val, "op": "<=", "limit": limit, "passed": ok, "severity": "ok" if ok else severity})
        if not ok:
            defects.append(tag)

    check_min("luma_mean", metrics["luma_mean"], cfg["luma_mean_min"], "too_dark")
    check_max("luma_mean", metrics["luma_mean"], cfg["luma_mean_max"], "overbright_global")
    check_max("luma_p01", metrics["luma_p01"], cfg["luma_p01_max"], "washed_out_blacks_hazy")
    check_max("luma_p05", metrics["luma_p05"], cfg["luma_p05_max"], "lifted_shadow_floor", severity="warn")
    check_min("luma_p95", metrics["luma_p95"], cfg["luma_p95_min"], "dull_highlights_not_bright")
    check_min("dynamic_range_p95_p05", metrics["dynamic_range_p95_p05"], cfg["dynamic_range_p95_p05_min"], "flat_hazy_contrast")
    check_min("luma_std", metrics["luma_std"], cfg["luma_std_min"], "low_tonal_separation")
    check_max("clipped_white_ratio", metrics["clipped_white_ratio"], cfg["clipped_white_ratio_max"], "clipped_white_overbright")
    check_min("highlight_ratio", metrics["highlight_ratio"], cfg["highlight_ratio_min"], "missing_highlights_or_rim", severity="warn")
    check_max("highlight_ratio", metrics["highlight_ratio"], cfg["highlight_ratio_max"], "excessive_bright_wash")
    check_min("saturation_mean", metrics["saturation_mean"], cfg["saturation_mean_min"], "desaturated_gray_cast")
    check_max("saturation_mean", metrics["saturation_mean"], cfg["saturation_mean_max"], "oversaturated_neon", severity="warn")
    check_min("saturation_p90", metrics["saturation_p90"], cfg["saturation_p90_min"], "weak_color_accents", severity="warn")
    check_min("dark_edge_density", metrics["dark_edge_density"], cfg["dark_edge_density_min"], "weak_dark_outline_proxy", severity="warn")
    check_min("laplacian_sharpness", metrics["laplacian_sharpness"], cfg["laplacian_sharpness_min"], "soft_or_overbloomed_image")

    if "subject_luma_mean" in metrics:
        check_min("subject_luma_mean", metrics["subject_luma_mean"], cfg["subject_luma_mean_min"], "subject_too_dark")
        check_max("subject_luma_mean", metrics["subject_luma_mean"], cfg["subject_luma_mean_max"], "subject_overbright")
        check_min("subject_luma_p90", metrics["subject_luma_p90"], cfg["subject_luma_p90_min"], "subject_dull_or_hazy")
        check_max("subject_clipped_white_ratio", metrics["subject_clipped_white_ratio"], cfg["subject_clipped_white_ratio_max"], "subject_clipped_white")
        check_min("subject_bg_luma_separation", metrics["subject_bg_luma_separation"], cfg["subject_bg_luma_separation_min"], "weak_subject_stage_separation")

    fails = [c for c in checks if not c["passed"] and c["severity"] == "fail"]
    warns = [c for c in checks if not c["passed"] and c["severity"] == "warn"]
    total = len(checks)
    score = round(max(0.0, 100.0 * (total - len(fails) - 0.35 * len(warns)) / max(1, total)), 2)
    status = "fail" if fails else ("warn" if warns else "pass")
    return {
        "status": status,
        "passed": len(fails) == 0,
        "score": score,
        "fail_count": len(fails),
        "warn_count": len(warns),
        "defect_tags": sorted(set(defects)),
        "checks": checks,
    }


def eval_still(image_path, preset, rois=None, mask_path=None):
    path = Path(image_path)
    rgb = load_rgb_float(path)
    mask = build_subject_mask(rgb.shape[0], rgb.shape[1], rois=rois, mask_path=mask_path)
    cfg = preset["still_hard_metrics"]
    metrics = compute_still_metrics(rgb, cfg, subject_mask=mask)
    verdict = evaluate_still_metrics(metrics, cfg)
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "metrics": metrics,
        **verdict,
        "user_approval": False,
    }


def eval_sparse(image_paths, preset, rois=None, mask_path=None):
    paths = [Path(p) for p in image_paths]
    if not paths:
        raise ValueError("eval_sparse requires at least one image path")
    scfg = preset["sparse_multiframe"]
    frame_results = [eval_still(p, preset, rois=rois, mask_path=mask_path) for p in paths]
    count = len(frame_results)
    fail_ratio = sum(1 for r in frame_results if not r["passed"]) / count
    luma_means = [r["metrics"]["luma_mean"] for r in frame_results]
    luma_drift = round(max(luma_means) - min(luma_means), 5)
    worst_clip = round(max(r["metrics"]["clipped_white_ratio"] for r in frame_results), 5)
    worst_frame = min(frame_results, key=lambda r: r["score"])

    checks = [
        {
            "metric": "sparse_frame_count",
            "value": count,
            "op": ">=",
            "limit": scfg["min_frames"],
            "passed": count >= scfg["min_frames"],
            "severity": "ok" if count >= scfg["min_frames"] else "fail",
        },
        {
            "metric": "frame_fail_ratio",
            "value": round(fail_ratio, 4),
            "op": "<=",
            "limit": scfg["max_frame_fail_ratio"],
            "passed": fail_ratio <= scfg["max_frame_fail_ratio"],
            "severity": "ok" if fail_ratio <= scfg["max_frame_fail_ratio"] else "fail",
        },
        {
            "metric": "luma_mean_drift",
            "value": luma_drift,
            "op": "<=",
            "limit": scfg["luma_mean_drift_max"],
            "passed": luma_drift <= scfg["luma_mean_drift_max"],
            "severity": "ok" if luma_drift <= scfg["luma_mean_drift_max"] else "warn",
        },
        {
            "metric": "worst_clipped_white_ratio",
            "value": worst_clip,
            "op": "<=",
            "limit": scfg["worst_clipped_white_ratio_max"],
            "passed": worst_clip <= scfg["worst_clipped_white_ratio_max"],
            "severity": "ok" if worst_clip <= scfg["worst_clipped_white_ratio_max"] else "fail",
        },
    ]
    fails = [c for c in checks if not c["passed"] and c["severity"] == "fail"]
    warns = [c for c in checks if not c["passed"] and c["severity"] == "warn"]
    return {
        "schema_version": 1,
        "kind": "sparse_multiframe_qc",
        "preset_id": preset["id"],
        "counts_as_video_delivery": False,
        "user_approval": False,
        "frame_count": count,
        "status": "fail" if fails else ("warn" if warns else "pass"),
        "passed": len(fails) == 0,
        "summary": {
            "mean_score": round(sum(r["score"] for r in frame_results) / count, 2),
            "frame_fail_ratio": round(fail_ratio, 4),
            "luma_mean_min": round(min(luma_means), 5),
            "luma_mean_max": round(max(luma_means), 5),
            "luma_mean_drift": luma_drift,
            "worst_clipped_white_ratio": worst_clip,
            "worst_frame": {"path": worst_frame["path"], "score": worst_frame["score"], "defect_tags": worst_frame["defect_tags"]},
        },
        "checks": checks,
        "frames": frame_results,
        "limits": LIMITS,
    }


def eval_temporal(image_paths, preset, fps=30.0):
    paths = [Path(p) for p in image_paths]
    if len(paths) < 3:
        raise ValueError("eval_temporal requires at least 3 consecutive frames")
    tcfg = preset["temporal_diagnostic"]
    luma_means = []
    edges_prev = None
    edge_diffs = []
    luma_jumps = []
    resolutions = set()

    for p in paths:
        rgb = load_rgb_float(p)
        resolutions.add((int(rgb.shape[1]), int(rgb.shape[0])))
        luma = rgb_to_luma(rgb)
        luma_means.append(float(np.mean(luma)))
        gx = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
        edge_map = (np.hypot(gx, gy) >= 0.18).astype(np.float32)
        if edges_prev is not None:
            if edge_map.shape != edges_prev.shape:
                raise ValueError("All temporal diagnostic frames must share the same resolution")
            edge_diffs.append(float(np.mean(np.abs(edge_map - edges_prev))))
            luma_jumps.append(abs(luma_means[-1] - luma_means[-2]))
        edges_prev = edge_map

    # Second-order temporal difference isolates flicker from smooth lighting transitions
    second_diffs = [
        abs(luma_means[i] - 2.0 * luma_means[i - 1] + luma_means[i - 2])
        for i in range(2, len(luma_means))
    ]
    flicker_p95 = float(np.percentile(second_diffs, 95))
    flicker_max = float(max(second_diffs))
    edge_jitter_mean = float(np.mean(edge_diffs))
    edge_jitter_max = float(max(edge_diffs))
    jump_thr = float(tcfg["hard_luma_jump_threshold"])
    hard_jump_ratio = float(sum(1 for d in luma_jumps if d > jump_thr) / len(luma_jumps))
    duration_sec = round(len(paths) / float(fps), 3)

    worst_flicker_idx = int(np.argmax(second_diffs)) + 1
    worst_edge_idx = int(np.argmax(edge_diffs)) + 1

    checks = [
        {
            "metric": "luma_flicker_p95",
            "value": round(flicker_p95, 5),
            "op": "<=",
            "limit": tcfg["luma_flicker_p95_max"],
            "passed": flicker_p95 <= tcfg["luma_flicker_p95_max"],
            "severity": "ok" if flicker_p95 <= tcfg["luma_flicker_p95_max"] else "fail",
        },
        {
            "metric": "edge_jitter_mean",
            "value": round(edge_jitter_mean, 5),
            "op": "<=",
            "limit": tcfg["edge_jitter_mean_max"],
            "passed": edge_jitter_mean <= tcfg["edge_jitter_mean_max"],
            "severity": "ok" if edge_jitter_mean <= tcfg["edge_jitter_mean_max"] else "fail",
        },
        {
            "metric": "hard_luma_jump_ratio",
            "value": round(hard_jump_ratio, 5),
            "op": "<=",
            "limit": tcfg["hard_luma_jump_ratio_max"],
            "passed": hard_jump_ratio <= tcfg["hard_luma_jump_ratio_max"],
            "severity": "ok" if hard_jump_ratio <= tcfg["hard_luma_jump_ratio_max"] else "fail",
        },
    ]
    fails = [c for c in checks if not c["passed"]]
    defects = []
    if not checks[0]["passed"]:
        defects.append("temporal_luma_flicker")
    if not checks[1]["passed"]:
        defects.append("temporal_edge_or_shadow_jitter")
    if not checks[2]["passed"]:
        defects.append("temporal_hard_luma_jump")

    return {
        "schema_version": 1,
        "kind": "temporal_diagnostic_qc",
        "preset_id": preset["id"],
        "counts_as_video_delivery": False,
        "user_approval": False,
        "frame_count": len(paths),
        "fps": float(fps),
        "duration_seconds": duration_sec,
        "resolution": list(next(iter(resolutions))),
        "status": "fail" if fails else "pass",
        "passed": len(fails) == 0,
        "defect_tags": defects,
        "metrics": {
            "luma_flicker_p95": round(flicker_p95, 5),
            "luma_flicker_max": round(flicker_max, 5),
            "edge_jitter_mean": round(edge_jitter_mean, 5),
            "edge_jitter_max": round(edge_jitter_max, 5),
            "hard_luma_jump_ratio": round(hard_jump_ratio, 5),
            "worst_flicker_frame": str(paths[worst_flicker_idx]),
            "worst_edge_pair": [str(paths[worst_edge_idx - 1]), str(paths[worst_edge_idx])],
        },
        "checks": checks,
        "limits": LIMITS,
    }


def plan_diagnostics(start_frame, end_frame, fps, preset, sparse_count=None, anchor_frame=None, temporal_seconds=None):
    if end_frame <= start_frame:
        raise ValueError("end_frame must be greater than start_frame")
    if fps <= 0:
        raise ValueError("fps must be positive")
    scfg = preset["sparse_multiframe"]
    tcfg = preset["temporal_diagnostic"]
    n = int(sparse_count if sparse_count is not None else scfg["recommended_frames"])
    if not (scfg["min_frames"] <= n <= scfg["max_frames"]):
        raise ValueError(f"sparse_count must be in [{scfg['min_frames']}, {scfg['max_frames']}]")
    dur = float(temporal_seconds if temporal_seconds is not None else tcfg["default_duration_seconds"])
    if not (tcfg["duration_seconds_min"] <= dur <= tcfg["duration_seconds_max"]):
        raise ValueError(f"temporal_seconds must be in [{tcfg['duration_seconds_min']}, {tcfg['duration_seconds_max']}]")

    # Evenly spread sparse frames avoiding absolute endpoints (5%..95%) plus optional anchor
    span = end_frame - start_frame
    lo = start_frame + int(round(span * 0.05))
    hi = end_frame - int(round(span * 0.05))
    if hi <= lo:
        lo, hi = start_frame, end_frame
    raw = [int(round(lo + i * (hi - lo) / max(1, n - 1))) for i in range(n)]
    sparse_frames = sorted(set(raw))
    if anchor_frame is not None and start_frame <= anchor_frame <= end_frame and anchor_frame not in sparse_frames:
        # Replace nearest frame to keep exact count within [min, max]
        nearest = min(sparse_frames, key=lambda f: abs(f - anchor_frame))
        sparse_frames[sparse_frames.index(nearest)] = int(anchor_frame)
        sparse_frames = sorted(set(sparse_frames))

    diag_fps = float(tcfg["default_fps"])
    frame_step = max(1, int(round(fps / diag_fps)))
    clip_frame_count = max(3, int(round(dur * diag_fps)))
    center = int(anchor_frame) if anchor_frame is not None else (start_frame + end_frame) // 2
    half_span = ((clip_frame_count - 1) * frame_step) // 2
    t_start = max(start_frame, center - half_span)
    t_end = min(end_frame, t_start + (clip_frame_count - 1) * frame_step)
    t_start = max(start_frame, t_end - (clip_frame_count - 1) * frame_step)
    temporal_frames = list(range(t_start, t_end + 1, frame_step))

    return {
        "schema_version": 1,
        "kind": "standard_qc_diagnostic_plan",
        "preset_id": preset["id"],
        "counts_as_video_delivery": False,
        "encode_as_review_video": False,
        "source_range": {"start_frame": int(start_frame), "end_frame": int(end_frame), "fps": float(fps)},
        "sparse_multiframe": {
            "count": len(sparse_frames),
            "frames": sparse_frames,
            "purpose": "跨全曲关键姿态／景别／光照分布静帧硬指标检查",
        },
        "temporal_diagnostic": {
            "duration_seconds": round(len(temporal_frames) / diag_fps, 3),
            "diagnostic_fps": diag_fps,
            "source_frame_step": frame_step,
            "resolution": list(tcfg["recommended_resolution"]),
            "frame_count": len(temporal_frames),
            "start_frame": temporal_frames[0],
            "end_frame": temporal_frames[-1],
            "frames": temporal_frames,
            "purpose": "低分辨率帧序列时序闪烁／阴影跳变／描边抖动诊断（非视频交付）",
        },
        "limits": LIMITS,
    }


def build_vlm_judge_packet(still_reports, preset, references=None, studio_preferences=None):
    return {
        "schema_version": 1,
        "kind": "vlm_judge_packet",
        "preset_id": preset["id"],
        "reviewer_role": "supervisor",
        "auto_api_call": False,
        "user_approval": False,
        "candidates": [
            {
                "path": r["path"],
                "sha256": r["sha256"],
                "hard_qc_status": r["status"],
                "hard_qc_score": r["score"],
                "hard_qc_defect_tags": r["defect_tags"],
                "key_metrics": {
                    k: r["metrics"][k]
                    for k in ("luma_mean", "luma_p05", "luma_p95", "dynamic_range_p95_p05", "clipped_white_ratio", "saturation_mean", "dark_edge_density")
                },
            }
            for r in still_reports
        ],
        "references": list(references or []),
        "user_preferences": list(studio_preferences or []),
        "rubric": preset["vlm_judge_protocol"],
        "required_output_schema": {
            "schema_version": 1,
            "judge_identity": "<actual model name>",
            "user_approval": False,
            "rankings": ["<best_path>", "..."],
            "per_candidate": [
                {
                    "path": "<candidate_path>",
                    "verdict": "pass|borderline|reject",
                    "scores": {d["id"]: "1..5" for d in preset["vlm_judge_protocol"]["dimensions"]},
                    "defect_tags": ["<tag>"],
                    "observations": ["<region-grounded visual observation>"],
                }
            ],
        },
        "limits": LIMITS,
    }


def calibrate_predictions(labeled_cases, preset):
    """Evaluate hard-QC or VLM-judge predictions against ground-truth user feedback labels.

    Each item in labeled_cases:
      {id, user_verdict: 'reject'|'accept', predicted_verdict: 'reject'|'accept', provenance: str}
    """
    if not labeled_cases:
        raise ValueError("labeled_cases must not be empty")
    gate = preset["vlm_judge_protocol"]["calibration_gate"]
    tp = fp = tn = fn = 0
    details = []
    for item in labeled_cases:
        uv = item.get("user_verdict")
        pv = item.get("predicted_verdict")
        if uv not in ("reject", "accept") or pv not in ("reject", "accept"):
            raise ValueError(f"Invalid verdict in calibration case {item.get('id')}: user={uv}, pred={pv}")
        if not item.get("provenance"):
            raise ValueError(f"Missing feedback provenance in calibration case {item.get('id')}")
        # Positive class = "reject" (catching user rejections is the critical safety objective)
        if uv == "reject" and pv == "reject":
            tp += 1
            match = True
        elif uv == "accept" and pv == "reject":
            fp += 1
            match = False
        elif uv == "accept" and pv == "accept":
            tn += 1
            match = True
        else:
            fn += 1
            match = False
        details.append({"id": item.get("id"), "user_verdict": uv, "predicted_verdict": pv, "matched": match, "provenance": item["provenance"]})

    total = len(labeled_cases)
    reject_total = tp + fn
    reject_recall = round(tp / reject_total, 4) if reject_total else None
    reject_precision = round(tp / (tp + fp), 4) if (tp + fp) else None
    accuracy = round((tp + tn) / total, 4)

    enough_cases = total >= gate["min_labeled_cases"]
    recall_ok = (reject_recall is not None) and (reject_recall >= gate["min_reject_recall"])
    acc_ok = accuracy >= gate["min_overall_accuracy"]
    passed = enough_cases and recall_ok and acc_ok

    return {
        "schema_version": 1,
        "kind": "qc_judge_calibration",
        "preset_id": preset["id"],
        "user_approval": False,
        "total_cases": total,
        "confusion_matrix": {"true_reject": tp, "false_reject": fp, "true_accept": tn, "false_accept": fn},
        "metrics": {
            "reject_recall": reject_recall,
            "reject_precision": reject_precision,
            "overall_accuracy": accuracy,
        },
        "gate": gate,
        "gate_checks": {
            "min_labeled_cases": enough_cases,
            "min_reject_recall": recall_ok,
            "min_overall_accuracy": acc_ok,
        },
        "calibration_passed": passed,
        "details": details,
        "limits": LIMITS,
    }


def _write_if_requested(payload, output_path):
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", type=Path, default=DEFAULT_PRESET)
    parser.add_argument("--output", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)

    p_still = sub.add_parser("eval-still", help="Evaluate one or more still frames against hard QC metrics")
    p_still.add_argument("images", nargs="+", type=Path)
    p_still.add_argument("--subject-roi", action="append", default=[], help="Normalized x,y,w,h subject ROI")
    p_still.add_argument("--subject-mask", type=Path)

    p_sparse = sub.add_parser("eval-sparse", help="Evaluate 8-12 sparse multiframe samples across a sequence")
    p_sparse.add_argument("images", nargs="+", type=Path)
    p_sparse.add_argument("--subject-roi", action="append", default=[])
    p_sparse.add_argument("--subject-mask", type=Path)

    p_temp = sub.add_parser("eval-temporal", help="Evaluate 1-2s low-res diagnostic frame sequence for flicker/jitter")
    p_temp.add_argument("images", nargs="+", type=Path)
    p_temp.add_argument("--fps", type=float, default=30.0)

    p_plan = sub.add_parser("plan-diagnostics", help="Generate deterministic 8-12 sparse frame list & 1-2s low-res temporal plan")
    p_plan.add_argument("--start-frame", type=int, required=True)
    p_plan.add_argument("--end-frame", type=int, required=True)
    p_plan.add_argument("--fps", type=float, default=60.0)
    p_plan.add_argument("--sparse-count", type=int)
    p_plan.add_argument("--anchor-frame", type=int)
    p_plan.add_argument("--temporal-seconds", type=float)

    p_vlm = sub.add_parser("vlm-packet", help="Build supervisor VLM judge packet from still frames + hard QC")
    p_vlm.add_argument("images", nargs="+", type=Path)
    p_vlm.add_argument("--subject-roi", action="append", default=[])
    p_vlm.add_argument("--reference", action="append", default=[])

    p_cal = sub.add_parser("calibrate", help="Backtest hard-QC or VLM-judge predictions against labeled user feedback")
    p_cal.add_argument("--cases", type=Path, required=True)

    args = parser.parse_args(argv)
    preset = load_json(args.preset)

    if args.command == "eval-still":
        rois = [parse_roi(r) for r in args.subject_roi]
        results = [eval_still(img, preset, rois=rois, mask_path=args.subject_mask) for img in args.images]
        ranked = sorted(results, key=lambda r: (r["passed"], r["score"]), reverse=True)
        payload = {
            "schema_version": 1,
            "kind": "still_hard_qc",
            "preset_id": preset["id"],
            "user_approval": False,
            "ranked_paths": [r["path"] for r in ranked],
            "results": results,
            "limits": LIMITS,
        }
    elif args.command == "eval-sparse":
        rois = [parse_roi(r) for r in args.subject_roi]
        payload = eval_sparse(args.images, preset, rois=rois, mask_path=args.subject_mask)
    elif args.command == "eval-temporal":
        payload = eval_temporal(args.images, preset, fps=args.fps)
    elif args.command == "plan-diagnostics":
        payload = plan_diagnostics(
            args.start_frame,
            args.end_frame,
            args.fps,
            preset,
            sparse_count=args.sparse_count,
            anchor_frame=args.anchor_frame,
            temporal_seconds=args.temporal_seconds,
        )
    elif args.command == "vlm-packet":
        rois = [parse_roi(r) for r in args.subject_roi]
        results = [eval_still(img, preset, rois=rois) for img in args.images]
        prefs = []
        studio_path = ROOT / "catalog/studio.json"
        if studio_path.is_file():
            prefs = load_json(studio_path).get("preferences", [])
        payload = build_vlm_judge_packet(results, preset, references=args.reference, studio_preferences=prefs)
    else:
        cases = load_json(args.cases)
        if isinstance(cases, dict):
            cases = cases.get("cases", [])
        payload = calibrate_predictions(cases, preset)

    _write_if_requested(payload, args.output)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
