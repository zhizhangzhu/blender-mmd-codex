"""Render aspect-specific picture and Cryptomatte sequences for typography.

Uses the existing baked tutorial study. No character segmentation by AI or
roto is needed; the matte is generated from Blender's actual object identity.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
from style_presets import load_package
from mmd_style_apply import apply_render_style


def landscape_camera(scene, start, end, settings=None):
    settings = settings or {}
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "Typography | independent landscape director"
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = 24
    cam.data.lens = settings.get("lens_mm", 50)
    focus = bpy.data.objects.new("Typography | landscape focus", None)
    scene.collection.objects.link(focus)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = focus
    cam.data.dof.aperture_fstop = 4
    cam.data.dof.aperture_blades = 8
    scene.camera = cam
    checks = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        h = arm.matrix_world @ head.matrix.translation
        u = (frame - start) / max(1, end - start)
        second = u >= 0.5
        shot = int(second)
        span = settings.get("shot_heights", [1.62, 1.25])[shot]
        # A left-third dancer shot leaves an independent graphic area on the
        # right. B is a reverse three-quarter shot, not a portrait crop.
        offset_x = settings.get("target_offsets", [0.40, -0.28])[shot]
        yaw = settings.get("yaw", [-0.16, 0.18])[shot]
        target = h + Vector((offset_x, 0, -span * (0.25 if not second else 0.18)))
        distance = span * cam.data.lens / cam.data.sensor_height
        cam.location = target + Vector(
            (math.sin(yaw) * distance, -math.cos(yaw) * distance, 0.04)
        )
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        focus.location = h + Vector((0, -0.03, 0.07))
        for prop in ["location", "rotation_euler"]:
            cam.keyframe_insert(data_path=prop, frame=frame)
        focus.keyframe_insert(data_path="location", frame=frame)
        bpy.context.view_layer.update()
        hp = world_to_camera_view(scene, cam, h)
        checks.append(0 < hp.x < 1 and 0 < hp.y < 1 and hp.z > 0)
    for action in [cam.animation_data.action, focus.animation_data.action]:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        for point in fc.keyframe_points:
                            point.interpolation = "LINEAR"
    assert all(checks)
    return {
        "independent_camera": True,
        "lens_mm": cam.data.lens,
        "sensor_height_mm": 24,
        "shot_heights": settings.get("shot_heights", [1.62, 1.25]),
        "horizontal_target_offsets": settings.get("target_offsets", [0.40, -0.28]),
        "head_checks": len(checks),
    }


def output_file(tree, directory, name, socket, color=True):
    n = tree.nodes.new("CompositorNodeOutputFile")
    n.directory = str(directory)
    n.file_name = "frame_####"
    n.format.media_type = "IMAGE"
    n.format.file_format = "PNG"
    n.format.color_mode = "RGB" if color else "BW"
    n.format.color_depth = "8"
    n.save_as_render = color
    item = n.file_output_items.new("RGBA" if color else "FLOAT", name)
    item.save_as_render = color
    tree.links.new(socket, n.inputs[name])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--cache-dir", type=Path, required=True)
    p.add_argument("--aspect", choices=["portrait", "landscape"], required=True)
    p.add_argument("--start", type=int, default=421)
    p.add_argument("--end", type=int, default=660)
    p.add_argument("--sample-only", action="store_true")
    p.add_argument("--style-package", type=Path)
    p.add_argument("--percentage", type=int, default=50)
    p.add_argument("--samples", type=int, default=48)
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--outline-preset", type=Path)
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    recipe = load_package(args.style_package) if args.style_package else None
    if recipe and recipe["aspect"] != args.aspect:
        raise ValueError("Style package aspect and render aspect disagree")
    if not 1 <= args.percentage <= 100 or args.samples < 1:
        raise ValueError("Invalid render quality")
    if (args.width is None) != (args.height is None):
        raise ValueError("Set both width and height")
    if args.width is not None:
        ratio = 9 / 16 if args.aspect == "portrait" else 16 / 9
        if (
            args.width < 2
            or args.height < 2
            or abs(args.width / args.height - ratio) > 0.001
        ):
            raise ValueError("Resolution does not match chosen aspect")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    args.cache_dir.mkdir(parents=True, exist_ok=False)
    s = bpy.context.scene
    assert s.rigidbody_world is None
    s.render.resolution_x, s.render.resolution_y = (
        (1080, 1920) if args.aspect == "portrait" else (1920, 1080)
    )
    if args.width is not None:
        s.render.resolution_x, s.render.resolution_y = args.width, args.height
    s.render.resolution_percentage = args.percentage
    s.eevee.taa_render_samples = args.samples
    report = {
        "aspect": args.aspect,
        "source_project": bpy.data.filepath,
        "frames": [args.start, args.end],
        "fps": s.render.fps,
        "sample_only": args.sample_only,
        "rendered_frame_count": 1 if args.sample_only else args.end - args.start + 1,
    }
    if args.aspect == "landscape":
        report["camera"] = landscape_camera(
            s, args.start, args.end, recipe["camera"] if recipe else None
        )
    else:
        report["camera"] = {
            "independent_camera": True,
            "source": "previous portrait study; not a landscape crop",
        }
    if recipe:
        report["style"] = apply_render_style(s, recipe)
        report["style_package"] = recipe
        (args.output_dir / "resolved-style.json").write_text(
            json.dumps(recipe, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.outline_preset:
        from mmd_outlines import apply_outlines

        report["outlines"] = apply_outlines(
            s, json.loads(args.outline_preset.read_text(encoding="utf-8"))
        )
    report["quality"] = {"percentage": args.percentage, "samples": args.samples}
    layer = s.view_layers[0]
    layer.use_pass_cryptomatte_object = True
    layer.use_pass_cryptomatte_material = True
    layer.pass_cryptomatte_depth = 6
    layer.update_render_passes()
    tree = s.compositing_node_group
    # Loaded derivative scenes may still target earlier diagnostic/production
    # caches. Each new render owns only its newly created output nodes.
    for old in list(tree.nodes):
        if old.bl_idname == "CompositorNodeOutputFile":
            tree.nodes.remove(old)
    render = next(n for n in tree.nodes if n.type == "R_LAYERS")
    render.scene = s
    original_output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    beauty = original_output.inputs["Image"].links[0].from_socket
    crypto = tree.nodes.new("CompositorNodeCryptomatteV2")
    crypto.source = "RENDER"
    crypto.scene = s
    crypto.layer_name = layer.name + ".CryptoObject"
    meshes = [
        o
        for o in s.objects
        if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
    ]
    crypto.matte_id = ",".join(o.name for o in meshes)
    output_file(tree, args.cache_dir / "beauty", "beauty", beauty, True)
    output_file(tree, args.cache_dir / "matte", "matte", crypto.outputs["Matte"], False)
    face = tree.nodes.new("CompositorNodeCryptomatteV2")
    face.source = "RENDER"
    face.scene = s
    face.layer_name = layer.name + ".CryptoMaterial"
    face_names = [
        m.name
        for m in bpy.data.materials
        if m.name in {"颜", "眉", "睫", "目", "白目", "口", "舌", "齿", "mmd_edge.颜"}
    ]
    face.matte_id = ",".join(face_names)
    output_file(tree, args.cache_dir / "face", "face", face.outputs["Matte"], False)
    report["face_materials"] = face_names
    report["cryptomatte_objects"] = [o.name for o in meshes]
    report["cache_dir"] = str(args.cache_dir)
    s.frame_start, s.frame_end = args.start, args.end
    s.frame_set(args.start)
    s.render.image_settings.media_type = "IMAGE"
    s.render.image_settings.file_format = "PNG"
    s.render.filepath = str(args.output_dir / "picture.png")
    bpy.ops.wm.save_as_mainfile(
        filepath=str(args.output_dir / "typography-source.blend")
    )
    if args.sample_only:
        bpy.ops.render.render(write_still=True)
    else:
        s.render.filepath = str(args.cache_dir / "camera" / "frame_####")
        bpy.ops.render.render(animation=True)
    (args.output_dir / "render-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("CAPTION_RENDER_OK", args.output_dir, flush=True)


if __name__ == "__main__":
    main()
