"""Compare both baked skeletons and authored camera across the time transform."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy


def snapshot(scene):
    return {
        "actors": {
            arm["performer_id"]: {
                bone.name: [v for row in bone.matrix for v in row]
                for bone in arm.pose.bones
            }
            for arm in scene.objects
            if arm.type == "ARMATURE" and arm.get("performer_id")
        },
        "camera_matrix": [v for row in scene.camera.matrix_world for v in row],
        "lens": scene.camera.data.lens,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-blend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.output.exists():
        raise FileExistsError(args.output)
    frames = [1, 2100, 4200, 8400, 11899]
    source = {}
    for frame in frames:
        original = 450 + (frame - 1) / 2
        bpy.context.scene.frame_set(math.floor(original), subframe=original % 1)
        source[frame] = snapshot(bpy.context.scene)
    bpy.ops.wm.open_mainfile(filepath=str(args.final_blend))
    scene = bpy.context.scene
    errors = []
    for frame in frames:
        scene.frame_set(frame)
        final = snapshot(scene)
        actor_error = {}
        for actor, bones in source[frame]["actors"].items():
            actor_error[actor] = max(
                abs(value - final["actors"][actor][name][index])
                for name, matrix in bones.items()
                for index, value in enumerate(matrix)
            )
        errors.append(
            {
                "frame": frame,
                "bone_matrix_error": actor_error,
                "camera_matrix_error": max(
                    abs(a - b)
                    for a, b in zip(
                        source[frame]["camera_matrix"], final["camera_matrix"]
                    )
                ),
                "lens_error": abs(source[frame]["lens"] - final["lens"]),
            }
        )
    images = [im for im in bpy.data.images if im.source == "FILE"]
    maximum = max(max(item["bone_matrix_error"].values()) for item in errors)
    camera_error = max(item["camera_matrix_error"] for item in errors)
    report = {
        "samples": errors,
        "maximum_pose_error": maximum,
        "maximum_camera_error": camera_error,
        "all_file_images_packed": all(im.packed_file for im in images),
        "file_image_count": len(images),
        "runtime_physics_present": scene.rigidbody_world is not None,
        "frame_range": [scene.frame_start, scene.frame_end],
        "fps": scene.render.fps,
        "characters": sorted(source[frames[0]]["actors"]),
        "passed": maximum < 0.002
        and camera_error < 0.002
        and scene.rigidbody_world is None,
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DUET_INTEGRATION_VERIFIED", json.dumps(report), flush=True)
    assert report["passed"]


if __name__ == "__main__":
    main()
