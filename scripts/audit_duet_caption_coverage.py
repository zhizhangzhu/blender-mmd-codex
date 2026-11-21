"""Read-only semantic head/body ROI audit for a duet caption actor cache.

Projects original MMD pose bones by performer_id. Fixed thresholds come from
two explicitly supplied correct frames, never from each tested frame/cache.
This checks missing performers, not pixel-perfect edge/opacity equivalence.
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view

REPO = Path(__file__).resolve().parents[1]


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(data)
    return value.hexdigest()


def actor_dir(path):
    return path / "actor" if (path / "actor").is_dir() else path


def mask(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = "Non-Color"
    width, height = image.size
    values = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(values)
    pixels = values.reshape(height, width, -1)
    result = pixels[::-1, :, : min(3, pixels.shape[2])].max(axis=2).copy()
    bpy.data.images.remove(image)
    assert np.isfinite(result).all(), str(path)
    return result


def bone(arm, name):
    return next((b for b in arm.pose.bones if b.mmd_bone.name_j == name), None)


def points(arm):
    head, neck = bone(arm, "頭"), bone(arm, "首")
    eyes = [bone(arm, n) for n in ["左目", "右目"]]
    upper = next(
        (bone(arm, n) for n in ["上半身2", "上半身1", "上半身"] if bone(arm, n)), None
    )
    assert head and neck and upper, arm.name
    if all(eyes):
        eye_center = (eyes[0].head + eyes[1].head) * 0.5
        head_point = eye_center * 0.7 + head.head * 0.3
        head_method = "0.70*mean(left/right eye heads)+0.30*head base"
    else:
        head_point = head.head * 0.45 + head.tail * 0.55
        head_method = "head bone midpoint fallback"
    return {
        "head": (
            arm.matrix_world @ head_point,
            arm.matrix_world @ head.head,
            head_method,
        ),
        "body": (
            arm.matrix_world @ ((upper.head + neck.head) * 0.5),
            arm.matrix_world @ neck.head,
            "midpoint(upper torso bone head,neck bone head)",
        ),
    }


def measure(scene, arms, pixels):
    height, width = pixels.shape
    records = []
    for actor, arm in arms.items():
        for region, (point, anchor, method) in points(arm).items():
            projected = world_to_camera_view(scene, scene.camera, point)
            other = world_to_camera_view(scene, scene.camera, anchor)
            finite = all(math.isfinite(float(v)) for v in [*point, *projected, *other])
            visible = (
                finite
                and projected.z > 0
                and 0 <= projected.x < 1
                and 0 <= projected.y < 1
            )
            row = {
                "actor": actor,
                "armature": arm.name,
                "region": region,
                "method": method,
                "world": list(point),
                "camera_ndc": list(projected),
                "finite": finite,
                "projected_on_screen": visible,
            }
            if visible:
                x, y = int(projected.x * width), int((1 - projected.y) * height)
                separation = math.hypot(
                    (projected.x - other.x) * width, (projected.y - other.y) * height
                )
                radius = int(np.clip(round(separation * 0.18), 2, 6))
                x0, y0, x1, y1 = (
                    max(0, x - radius),
                    max(0, y - radius),
                    min(width, x + radius + 1),
                    min(height, y + radius + 1),
                )
                values = pixels[y0:y1, x0:x1]
                row.update(
                    {
                        "roi_xyxy": [x0, y0, x1, y1],
                        "radius_px": radius,
                        "mean": float(values.mean()),
                        "nonzero_fraction": float((values > 1e-5).mean()),
                        "max": float(values.max()),
                        "pixel_count": int(values.size),
                    }
                )
            records.append(row)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--calibration-cache", type=Path, required=True)
    parser.add_argument("--calibration-frames", default="4250,4290")
    parser.add_argument("--frames", default="4140:4439")
    parser.add_argument(
        "--profile",
        type=Path,
        default=REPO / "presets/typography/duet-blue-gold-wedding-v1.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect", choices=["pass", "fail"], default="pass")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    assert not args.output.exists(), args.output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.blend), load_ui=False)
    scene = bpy.context.scene
    assert scene.camera
    arms = {}
    for actor in ["aksiniya", "ikhor"]:
        matches = [
            o
            for o in scene.objects
            if o.type == "ARMATURE" and o.get("performer_id") == actor
        ]
        assert len(matches) == 1, (actor, len(matches))
        arms[actor] = matches[0]
    cache, correct = actor_dir(args.cache), actor_dir(args.calibration_cache)
    calibration = []
    for frame in [int(v) for v in args.calibration_frames.split(",")]:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        path = correct / f"frame_{frame:04d}actor.png"
        calibration.append(
            {
                "frame": frame,
                "path": str(path),
                "sha256": sha(path),
                "regions": measure(scene, arms, mask(path)),
            }
        )
    thresholds = {}
    for actor in arms:
        for region in ["head", "body"]:
            samples = [
                r["mean"]
                for c in calibration
                for r in c["regions"]
                if r["actor"] == actor
                and r["region"] == region
                and r["projected_on_screen"]
            ]
            assert len(samples) == len(calibration) and min(samples) > 0.5, (
                actor,
                region,
                samples,
                "Calibration point needs visual review",
            )
            thresholds[f"{actor}:{region}"] = {
                "correct_sample_means": samples,
                "minimum_mean": max(0.05, min(0.20, min(samples) * 0.25)),
            }
    frames = (
        list(range(*[int(v) for v in args.frames.split(":")]))
        if ":" in args.frames
        else [int(v) for v in args.frames.split(",")]
    )
    if ":" in args.frames:
        frames.append(int(args.frames.split(":")[1]))
    profile = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    records = []
    failures = []
    skipped = []
    for frame in frames:
        path = cache / f"frame_{frame:04d}actor.png"
        source_frame = (
            profile["source_start_frame"] + frame - profile["render_start_frame"]
        )
        cue = next(
            (
                c
                for c in profile["cues"]
                if c["start_frame"] <= source_frame < c["end_frame"]
            ),
            None,
        )
        if not path.is_file():
            failures.append(
                {"frame": frame, "reason": "missing_png", "path": str(path)}
            )
            continue
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        rows = measure(scene, arms, mask(path))
        for row in rows:
            row["minimum_mean"] = thresholds[f"{row['actor']}:{row['region']}"][
                "minimum_mean"
            ]
            row["passed"] = row["finite"] and (
                not row["projected_on_screen"] or row["mean"] >= row["minimum_mean"]
            )
            if not row["passed"]:
                failures.append({"frame": frame, **row})
            if not row["projected_on_screen"]:
                skipped.append(
                    {"frame": frame, "actor": row["actor"], "region": row["region"]}
                )
        records.append(
            {
                "frame": frame,
                "source_typography_frame": source_frame,
                "cue": cue["id"] if cue else None,
                "order": cue["order"] if cue else None,
                "regions": rows,
            }
        )
        if len(records) % 25 == 0:
            print("CAPTION_ROI_PROGRESS", len(records), len(frames), flush=True)
    distributions = {}
    for key in thresholds:
        actor, region = key.split(":")
        means = [
            r["mean"]
            for f in records
            for r in f["regions"]
            if r["actor"] == actor
            and r["region"] == region
            and r["projected_on_screen"]
        ]
        distributions[key] = {
            "count": len(means),
            "min": min(means) if means else None,
            "p05": float(np.quantile(means, 0.05)) if means else None,
            "median": float(np.median(means)) if means else None,
            "max": max(means) if means else None,
        }
    passed = not failures and len(records) == len(frames)
    report = {
        "project": str(args.blend),
        "project_sha256": sha(args.blend),
        "cache": str(cache),
        "passed": passed,
        "expected_result": args.expect,
        "expected_result_observed": passed == (args.expect == "pass"),
        "frame_range": [min(frames), max(frames)],
        "expected_frames": len(frames),
        "tested_frames": len(records),
        "behind_frames_tested": sum(r["order"] == "behind" for r in records),
        "performer_armatures": {a: o.name for a, o in arms.items()},
        "calibration": calibration,
        "fixed_thresholds": thresholds,
        "mean_distributions": distributions,
        "failures": failures,
        "projected_offscreen_regions": skipped,
        "records": records,
        "saved_blend": False,
        "rendered": False,
        "cache_modified": False,
        "limits": [
            "Semantic projected interior ROIs detect a missing character; they do not certify exact silhouette pixels, motion blur, transparent edges or all occlusions.",
            "Visibility here means projected in front of camera and inside image. A true stage/other-character occlusion can legitimately require manual classification.",
            "Thresholds are fixed from the explicitly supplied correct cache samples, not adapted per tested frame. No left/right position assumption is used.",
        ],
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print("CAPTION_ROI_AUDIT_COMPLETE", passed, len(failures), args.output, flush=True)
    assert report["expected_result_observed"], args.output


if __name__ == "__main__":
    main()
