"""Import an authored camera VMD into an existing draft and audit sample frames.

Run inside Blender with an existing .blend and -- --camera-vmd ...
--output-dir <new-directory>. Preserves the model action and original draft file.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


def main():
    import bpy
    from bpy_extras.object_utils import world_to_camera_view

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-vmd", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frames", type=int, nargs="+", default=[1884, 1944, 2004])
    parser.add_argument("--follow-range", type=int, nargs=2, metavar=("START", "END"),
                        help="Bake a separate single-performer framing offset for this preview segment")
    parser.add_argument("--min-vertical-span", type=float, default=0.0,
                        help="For the follow test, keep at least this much vertical world space visible at the head")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if not args.camera_vmd.is_file():
        raise FileNotFoundError(args.camera_vmd)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    vmd = importlib.import_module("bl_ext.blender_org.mmd_tools.core.vmd")
    source = vmd.File()
    source.load(filepath=str(args.camera_vmd))
    keys = source.cameraAnimation
    if not keys:
        raise ValueError("VMD contains no camera keyframes")
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    original_action = armature.animation_data.action
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "Mina_160cm_Camera_Import_Check"
    result = bpy.ops.mmd_tools.import_vmd(filepath=str(args.camera_vmd), scale=0.08,
                                         update_scene_settings=False, create_new_action=True,
                                         detect_camera_changes=True, log_level="ERROR", save_log=False)
    if "FINISHED" not in result or armature.animation_data.action != original_action:
        raise RuntimeError("Camera import failed or model action changed")
    scene.camera = camera
    scene.render.resolution_x = 576
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    args.output_dir.mkdir(parents=True, exist_ok=False)
    samples = []
    head = next(b for b in armature.pose.bones if b.mmd_bone.name_j == "頭")
    follow = None
    if args.follow_range:
        start, end = args.follow_range
        if start > end or any(frame < start or frame > end for frame in args.frames):
            raise ValueError("Sample frames must be within the follow range")
        rig = camera
        while rig.parent:
            rig = rig.parent
        follow = bpy.data.objects.new("Single_Performer_Framing_Offset", None)
        scene.collection.objects.link(follow)
        rig.parent = follow
        # Original rig animation remains intact. Bake only a camera-plane
        # translation so the head stays at x=.5, y=.7 in the portrait frame.
        from mathutils import Vector
        for frame in range(start, end + 1):
            scene.frame_set(frame)
            follow.location = (0, 0, 0)
            bpy.context.view_layer.update()
            evaluated = camera.evaluated_get(bpy.context.evaluated_depsgraph_get())
            matrix = evaluated.matrix_world.copy()
            local_head = matrix.inverted() @ (armature.matrix_world @ head.matrix.translation)
            corners = camera.data.view_frame(scene=scene)
            depth = -local_head.z
            guarded_depth = depth
            if camera.data.type == "PERSP" and args.min_vertical_span > 0:
                vertical_unit = max(p.y for p in corners) - min(p.y for p in corners)
                guarded_depth = max(depth, args.min_vertical_span * abs(corners[0].z) / vertical_unit)
            scale = guarded_depth / abs(corners[0].z) if camera.data.type == "PERSP" else 1.0
            xs, ys = [p.x * scale for p in corners], [p.y * scale for p in corners]
            desired_x = (min(xs) + max(xs)) * 0.5
            desired_y = min(ys) + (max(ys) - min(ys)) * 0.7
            offset = matrix.to_quaternion() @ Vector((local_head.x - desired_x, local_head.y - desired_y, guarded_depth - depth))
            follow.location = offset
            follow.keyframe_insert(data_path="location", frame=frame)
        scene.frame_start, scene.frame_end = start, end
    for frame in args.frames:
        scene.frame_set(frame)
        evaluated = camera.evaluated_get(bpy.context.evaluated_depsgraph_get())
        point = armature.matrix_world @ head.matrix.translation
        projected = world_to_camera_view(scene, camera, point)
        samples.append({"frame": frame, "camera_location": list(evaluated.matrix_world.translation),
                        "camera_lens_mm": camera.data.lens,
                        "head_projection": list(projected),
                        "head_inside_frame": 0 <= projected.x <= 1 and 0 <= projected.y <= 1 and projected.z > 0})
        scene.render.filepath = str(args.output_dir / f"camera-check-{frame:04d}.png")
        scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)
    scene.frame_set(args.frames[0])
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_dir / "camera-import-check.blend"))
    report = {"status": "camera_import_check", "source_camera": str(args.camera_vmd),
              "source_key_count": len(keys),
              "source_frame_range": [min(k.frame_number for k in keys), max(k.frame_number for k in keys)],
              "model_action_preserved": armature.animation_data.action == original_action,
              "single_follow_range": args.follow_range,
              "min_vertical_span": args.min_vertical_span,
              "samples": samples,
              "limits": ["Follow offset is only a framing test for the specified segment; full-body clipping still needs review." if follow else "Author camera has not been adapted for a single performer or portrait crop.",
                         "Existing draft shading and unbaked physics unchanged.",
                         "Head projection checks do not detect all clipping or composition problems."]}
    (args.output_dir / "camera-import-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("CAMERA_IMPORT_CHECK_OK", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
