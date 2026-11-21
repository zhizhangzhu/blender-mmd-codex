"""Match architectural texture features and estimate a research camera pose."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-dir", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--world-matches", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    reference = cv2.imdecode(
        np.fromfile(args.reference, dtype=np.uint8), cv2.IMREAD_COLOR
    )
    reference = cv2.resize(reference, (1280, 720), interpolation=cv2.INTER_AREA)
    if not args.world_matches:
        seed = cv2.imread(str(args.seed_dir / "geometry.png"))
        sift = cv2.SIFT_create(
            nfeatures=14000, contrastThreshold=0.018, edgeThreshold=15
        )
        clahe = cv2.createCLAHE(clipLimit=2, tileGridSize=(8, 8))
        k1, d1 = sift.detectAndCompute(
            clahe.apply(cv2.cvtColor(seed, cv2.COLOR_BGR2GRAY)), None
        )
        k2, d2 = sift.detectAndCompute(
            clahe.apply(cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)), None
        )
        d1 = np.sqrt(d1 / (d1.sum(axis=1, keepdims=True) + 1e-9))
        d2 = np.sqrt(d2 / (d2.sum(axis=1, keepdims=True) + 1e-9))
        matcher = cv2.BFMatcher()
        matches = [
            a for a, b in matcher.knnMatch(d1, d2, k=2) if a.distance < 0.8 * b.distance
        ]
        # Retain only bidirectionally consistent matches.
        back = {
            a.queryIdx: a.trainIdx
            for a, b in matcher.knnMatch(d2, d1, k=2)
            if a.distance < 0.9 * b.distance
        }
        matches = [m for m in matches if back.get(m.trainIdx) == m.queryIdx]
        rows = [
            {
                "seed_pixel": list(k1[m.queryIdx].pt),
                "reference_pixel": list(k2[m.trainIdx].pt),
                "distance": float(m.distance),
            }
            for m in matches
        ]
        (args.output_dir / "feature-matches.json").write_text(
            json.dumps({"matches": rows}, indent=2), encoding="utf-8"
        )
        montage = cv2.drawMatches(
            seed,
            k1,
            reference,
            k2,
            matches[:120],
            None,
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
        )
        cv2.imwrite(str(args.output_dir / "feature-matches.jpg"), montage)
        print("TEXTURE_MATCHES", len(rows), "features", len(k1), len(k2))
        return
    rows = json.loads(args.world_matches.read_text(encoding="utf-8"))["matches"]
    xyz = np.asarray([r["world"] for r in rows], np.float64)
    uv = np.asarray([r["reference_pixel"] for r in rows], np.float64)
    trials = []
    for lens in [22, 28, 32, 36, 42, 50, 60]:
        focal = lens / 36 * 1280
        k = np.array([[focal, 0, 640], [0, focal, 360], [0, 0, 1]], np.float64)
        ok, rvec, tvec, inliers = cv2.solvePnPRansac(
            xyz,
            uv,
            k,
            None,
            iterationsCount=6000,
            reprojectionError=4,
            confidence=0.999,
            flags=cv2.SOLVEPNP_EPNP,
        )
        if not ok or inliers is None or len(inliers) < 12:
            continue
        ix = inliers[:, 0]
        flags = (
            cv2.CALIB_USE_INTRINSIC_GUESS
            | cv2.CALIB_FIX_PRINCIPAL_POINT
            | cv2.CALIB_FIX_ASPECT_RATIO
            | cv2.CALIB_ZERO_TANGENT_DIST
            | cv2.CALIB_FIX_K1
            | cv2.CALIB_FIX_K2
            | cv2.CALIB_FIX_K3
        )
        rms, calibrated, _dist, rotations, translations = cv2.calibrateCamera(
            [xyz[ix].astype(np.float32)],
            [uv[ix].astype(np.float32)],
            (1280, 720),
            k,
            None,
            flags=flags,
        )
        rvec, tvec = rotations[0], translations[0]
        projected = cv2.projectPoints(xyz, rvec, tvec, calibrated, None)[0][:, 0]
        error = np.linalg.norm(projected - uv, axis=1)
        ix = np.where(error < 4)[0]
        rcw = cv2.Rodrigues(rvec)[0]
        extrinsic = np.eye(4)
        extrinsic[:3, :3] = rcw
        extrinsic[:3, 3] = tvec[:, 0]
        c2w = np.linalg.inv(extrinsic) @ np.diag([1, -1, -1, 1])
        mm = float(calibrated[0, 0] / 1280 * 36)
        location = c2w[:3, 3]
        if not (
            15 < mm < 90
            and -25 < location[0] < 25
            and -100 < location[1] < 15
            and -2 < location[2] < 20
        ):
            continue
        trials.append(
            (
                len(ix),
                -float(np.median(error[ix])),
                {
                    "camera_to_world_blender": c2w.tolist(),
                    "lens_mm": mm,
                    "inliers": len(ix),
                    "total_world_matches": len(rows),
                    "median_inlier_error_pixels": float(np.median(error[ix])),
                    "rms_pixels": float(rms),
                    "frame_size": [1280, 720],
                    "estimated_from_reference": True,
                    "recovered_original_camera_data": False,
                },
                projected,
                error,
            )
        )
    if not trials:
        raise RuntimeError(
            "No plausible camera pose; inspect matches or improve seed view"
        )
    _n, _score, report, projected, error = max(
        trials, key=lambda item: (item[0], item[1])
    )
    overlay = reference.copy()
    for target, point, e in zip(uv, projected, error):
        if e > 4:
            continue
        cv2.circle(overlay, tuple(np.rint(target).astype(int)), 3, (0, 255, 0), 1)
        cv2.circle(overlay, tuple(np.rint(point).astype(int)), 1, (0, 0, 255), 1)
    cv2.imwrite(str(args.output_dir / "reprojection.jpg"), overlay)
    (args.output_dir / "estimated-camera.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
