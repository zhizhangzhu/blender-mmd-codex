"""Check current actor PNGs at SHA-bound, inherited identical-camera/pose ROIs.

This avoids reopening Blender for each mask check. It accepts only this frozen
material-only revision plus its explicitly checked two hidden effect curves.
"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

PROJECT_SHA = "0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4"
PARENT_SHA = "8425c1827fd296fe19e17225e5e1e748de249bf11cae25ff888c6b010242f993"
POSE_SOURCE_SHA = "f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--roi-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, nargs="*")
    args = parser.parse_args()
    assert not args.output.exists()
    project = args.root / "production-v2/Franken_Duet_Clean_Game.blend"
    assert sha(project) == PROJECT_SHA
    material_report = args.root / "production-v1/master-verification.json"
    arc_report = args.root / "production-v2/master-verification.json"
    a, b = read(material_report), read(arc_report)
    assert (
        a["passed"]
        and a["project_sha256"] == PARENT_SHA
        and a["source_sha256"] == POSE_SOURCE_SHA
    )
    assert b["passed"] and b["project_sha256"] == PROJECT_SHA
    inherited = read(args.roi_report)
    assert inherited["passed"] and inherited["project_sha256"] == POSE_SOURCE_SHA
    frames = args.frames or list(range(4140, 4440))
    items = {item["frame"]: item for item in inherited["records"]}
    records, failures = [], []
    for frame in frames:
        path = args.cache / "actor" / f"frame_{frame:04d}actor.png"
        pixels = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        assert (
            pixels is not None
            and pixels.dtype == np.uint16
            and pixels.shape == (1080, 1920)
        )
        row = {"frame": frame, "sha256": sha(path), "regions": []}
        assert {region["actor"] for region in items[frame]["regions"]} == {
            "aksiniya",
            "ikhor",
        }
        for source in items[frame]["regions"]:
            assert source["projected_on_screen"] and source["finite"]
            x0, y0, x1, y1 = source["roi_xyxy"]
            patch = pixels[y0:y1, x0:x1].astype(np.float32) / 65535
            mean = float(patch.mean())
            good = bool(np.isfinite(patch).all() and mean >= source["minimum_mean"])
            value = {
                "actor": source["actor"],
                "region": source["region"],
                "roi_xyxy": source["roi_xyxy"],
                "mean": mean,
                "minimum_mean": source["minimum_mean"],
                "passed": good,
            }
            row["regions"].append(value)
            if not good:
                failures.append({"frame": frame, **value})
        records.append(row)
    report = {
        "passed": not failures,
        "project_sha256": PROJECT_SHA,
        "cache": str(args.cache),
        "frames": len(frames),
        "source_frames": frames,
        "roi_source": str(args.roi_report),
        "roi_source_sha256": sha(args.roi_report),
        "pose_source_sha256": POSE_SOURCE_SHA,
        "static_inheritance_reports": [
            {"path": str(p), "sha256": sha(p)} for p in (material_report, arc_report)
        ],
        "records": records,
        "failures": failures,
        "scope": "Current PNG16 masks measured at inherited projected head/body ROIs. Complete actions/geometry/camera were independently held identical through these frozen revisions; only materials and two non-actor curve visibility flags changed. Missing-person detection, not exact edge certification.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("CLEAN_ACTOR_COVERAGE", report["passed"], len(frames), len(failures))
    assert report["passed"]


if __name__ == "__main__":
    main()
