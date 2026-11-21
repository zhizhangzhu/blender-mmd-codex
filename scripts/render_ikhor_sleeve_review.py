"""Render both wrists continuously from a saved, portable repair candidate.

Diagnostic only: the source is never saved, stage/post/DOF/blur are disabled.
The production skin, cuff and hand geometry, motion and character lights remain.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import aim
from prepare_bold_wedding import mute_outputs


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start", type=int, default=4140)
    parser.add_argument("--end", type=int, default=4439)
    parser.add_argument("--size", type=int, default=480)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    assert args.start <= args.end
    source = Path(bpy.data.filepath)
    source_sha = sha(source)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    arm = next(
        obj
        for obj in scene.objects
        if obj.type == "ARMATURE" and obj.get("performer_id") == "ikhor"
    )
    assert scene.rigidbody_world is None, "Review requires a portable baked candidate"
    mute_outputs()
    source_camera = scene.camera
    camera = source_camera.copy()
    camera.data = source_camera.data.copy()
    camera.parent = None
    camera.constraints.clear()
    camera.animation_data_clear()
    camera.data.animation_data_clear()
    scene.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.52
    camera.data.dof.use_dof = False
    scene.camera = camera
    for obj in scene.objects:
        if (
            obj.type in {"MESH", "LIGHT_PROBE", "CURVE", "FONT"}
            and obj.get("performer_id") != "ikhor"
        ):
            obj.hide_render = True
        if obj.type == "LIGHT" and not obj.name.startswith("Reference duet | ikhor |"):
            obj.hide_render = True
    scene.render.use_compositing = False
    scene.render.use_motion_blur = False
    scene.render.resolution_x = scene.render.resolution_y = args.size
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 16
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    bones = {
        label: next(b for b in arm.pose.bones if b.mmd_bone.name_j == name)
        for label, name in [("right", "右手首"), ("left", "左手首")]
    }
    for side in bones:
        (args.output_dir / side).mkdir()
    records = []
    for frame in range(args.start, args.end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        view_source = source_camera.matrix_world.translation.copy()
        for side, bone in bones.items():
            target = arm.matrix_world @ bone.matrix.translation + Vector((0, 0, 0.025))
            camera.location = target + (view_source - target).normalized() * 3
            aim(camera, target)
            path = args.output_dir / side / f"{frame:06d}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
        records.append(frame)
        (args.output_dir / "progress.json").write_text(
            json.dumps(
                {"source_sha256": source_sha, "last_frame": frame, "complete": False}
            ),
            encoding="utf-8",
        )
        print("IKHOR_WRISTS_REVIEWED", frame, flush=True)
    assert sha(source) == source_sha, "The saved source must remain unchanged"
    report = {
        "source": str(source),
        "source_sha256": source_sha,
        "frames": records,
        "frames_per_wrist": len(records),
        "size": [args.size, args.size],
        "samples": 16,
        "motion_blur": False,
        "dof": False,
        "source_modified": False,
        "geometry_passed": None,
        "scope": "Continuous diagnostic views only; requires geometry and visual review, not automatic collision clearance.",
    }
    (args.output_dir / "wrist-review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "progress.json").write_text(
        json.dumps(
            {"source_sha256": source_sha, "last_frame": args.end, "complete": True}
        ),
        encoding="utf-8",
    )
    print("IKHOR_CONTINUOUS_WRIST_REVIEW_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
