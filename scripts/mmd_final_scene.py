"""Art direct the physics-baked Aksiniya project with pastel stage and NPR materials.

Model-specific material routing is intentional. General workflow is documented
separately; do not silently reuse Chinese slot names for an unrelated model.
"""

from __future__ import annotations
import argparse
import bpy
import json
import math
import sys
import time
from pathlib import Path
from mathutils import Vector


def node(tree, kind, **props):
    n = tree.nodes.new(kind)
    for k, v in props.items():
        setattr(n, k, v)
    return n


def solid(name, color, roughness=0.55, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def cube(name, location, scale, mat, bevel=0.035):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new("Soft architectural edges", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        o.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return o


def curve(name, coords, mat, radius=0.018):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = 3
    s = data.splines.new("POLY")
    s.points.add(len(coords) - 1)
    for point, co in zip(s.points, coords):
        point.co = (*co, 1)
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def toon_material(mat):
    old = mat.node_tree.nodes.get("mmd_base_tex")
    image = old.image if old else None
    if not image:
        return
    name = mat.name
    skin = name in {"颜", "首", "手"}
    eye = name in {"目", "白目"}
    hair = name.rstrip("+") in {"鬓", "前鬓", "呆毛"}
    tree = mat.node_tree
    link = tree.links.new
    shader = tree.nodes.get("mmd_shader")
    if not shader:
        return
    # Preserve MMD's sphere-add layers, sidedness, alpha and UV interpretation.
    # Converting individual texture nodes is not equivalent for this PMX.
    out = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL")
    rgb = node(tree, "ShaderNodeShaderToRGB")
    rgb.label = "MMD result to controlled NPR color"
    link(shader.outputs[0], rgb.inputs[0])
    hue = node(tree, "ShaderNodeHueSaturation")
    hue.inputs["Saturation"].default_value = 1.03
    hue.inputs["Value"].default_value = 1.05 if skin else (1.12 if eye else 1.04)
    link(rgb.outputs["Color"], hue.inputs["Color"])
    add = node(tree, "ShaderNodeVectorMath", operation="ADD")
    add.inputs[1].default_value = (0.45, 0.45, 0.45)
    link(hue.outputs[0], add.inputs[0])
    compress = node(tree, "ShaderNodeVectorMath", operation="DIVIDE")
    link(hue.outputs[0], compress.inputs[0])
    link(add.outputs[0], compress.inputs[1])
    emission = node(tree, "ShaderNodeEmission")
    link(compress.outputs[0], emission.inputs[0])
    transparent = node(tree, "ShaderNodeBsdfTransparent")
    mix = node(tree, "ShaderNodeMixShader")
    link(rgb.outputs["Alpha"], mix.inputs[0])
    link(transparent.outputs[0], mix.inputs[1])
    link(emission.outputs[0], mix.inputs[2])
    link(mix.outputs[0], out.inputs[0])
    mat["production_shader"] = "MMD-preserving Shader-to-RGB pastel v2"


def create_stage():
    ivory = solid("Stage | warm porcelain", (0.75, 0.66, 0.55))
    rose = solid("Stage | rose velvet", (0.38, 0.105, 0.15), 0.82)
    cream = solid("Stage | butter cream", (0.85, 0.75, 0.57), 0.7)
    gold = solid("Stage | champagne gold", (0.53, 0.32, 0.105), 0.29, 0.65)
    lilac = solid("Stage | dusty lilac", (0.31, 0.24, 0.37))
    floor = bpy.data.materials.new("Stage | cream and rose checkerboard")
    t = floor.node_tree
    bs = next(n for n in t.nodes if n.type == "BSDF_PRINCIPLED")
    coords = node(t, "ShaderNodeTexCoord")
    checker = node(t, "ShaderNodeTexChecker")
    checker.inputs[1].default_value = (0.67, 0.58, 0.55, 1)
    checker.inputs[2].default_value = (0.92, 0.85, 0.73, 1)
    checker.inputs[3].default_value = 2
    t.links.new(coords.outputs["Object"], checker.inputs[0])
    t.links.new(checker.outputs[0], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.47
    cube("Rose Salon | tiled dance floor", (0, 0, -0.065), (60, 60, 0.10), floor, 0.015)
    cube("Rose Salon | backdrop", (0, 4.8, 2.2), (24, 0.25, 5.0), rose)
    cube("Rose Salon | cornice", (0, 4.52, 3.65), (24, 0.24, 0.16), cream)
    cube("Rose Salon | gold cornice", (0, 4.36, 3.47), (24, 0.055, 0.035), gold, 0.006)
    for x in [-9, -6, -3, 0, 3, 6, 9]:
        cube("Panel | recessed lilac", (x, 4.61, 1.75), (2.65, 0.10, 2.95), lilac)
        for dx in [-1.32, 1.32]:
            cube(
                "Panel | ivory pilaster",
                (x + dx, 4.30, 1.66),
                (0.13, 0.38, 3.25),
                cream,
            )
        for z in [0.23, 3.1]:
            cube(
                "Panel | champagne rail", (x, 4.26, z), (2.68, 0.07, 0.045), gold, 0.01
            )
        coords = [(x - 1.02, 4.25, 0.52), (x - 1.02, 4.25, 2.25)]
        coords += [
            (x + 1.02 * math.cos(a), 4.25, 2.25 + 1.02 * math.sin(a))
            for a in [math.pi - i * math.pi / 48 for i in range(49)]
        ]
        coords += [(x + 1.02, 4.25, 0.52)]
        curve("Panel | arched gold molding", coords, gold, 0.016)
        # Rose curtains are modeled pleats with smooth silhouettes.
        for side in [-1, 1]:
            for k in range(5):
                bx = x + side * (0.82 + 0.065 * k)
                bpy.ops.mesh.primitive_uv_sphere_add(
                    segments=12, ring_count=8, location=(bx, 4.15, 1.77)
                )
                o = bpy.context.object
                o.name = "Curtain | soft pleat"
                o.scale = (0.085, 0.09, 1.34)
                o.data.materials.append(rose)
                for p in o.data.polygons:
                    p.use_smooth = True
        curve(
            "Panel | heart ornament",
            [
                (
                    x + 0.16 * math.sin(a) ** 3,
                    4.08,
                    2.76
                    + 0.014
                    * (
                        13 * math.cos(a)
                        - 5 * math.cos(2 * a)
                        - 2 * math.cos(3 * a)
                        - math.cos(4 * a)
                    ),
                )
                for a in [i * math.tau / 64 for i in range(65)]
            ],
            gold,
            0.012,
        )
    # Broad side wings keep every moderate orbit within the finished set.
    for sign in [-1, 1]:
        cube("Salon | side wing", (sign * 10, 0, 2.1), (0.2, 12, 4.8), rose)
    return {
        "palette": "rose / ivory / lilac / champagne",
        "geometry": "original procedural salon, no external stage assets",
    }


def point_at(obj, target):
    obj.rotation_euler = (
        (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    )


def retime_actions(source_start, scale):
    import numpy as np

    curves = 0
    for action in bpy.data.actions:
        for layer in action.layers:
            for strip in layer.strips:
                if not hasattr(strip, "channelbags"):
                    continue
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        count = len(fc.keyframe_points)
                        if not count:
                            continue
                        for attr in ("co", "handle_left", "handle_right"):
                            values = np.empty(count * 2, dtype=np.float32)
                            fc.keyframe_points.foreach_get(attr, values)
                            values[0::2] = (values[0::2] - source_start) * scale + 1
                            fc.keyframe_points.foreach_set(attr, values)
                        fc.update()
                        curves += 1
    return curves


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--camera-vmd", type=Path, required=True)
    p.add_argument("--frame", type=int, default=1944)
    p.add_argument("--start", type=int, default=1)
    p.add_argument("--end", type=int, default=6368)
    p.add_argument("--sample-only", action="store_true")
    p.add_argument("--output-fps", type=int, default=30)
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    root = arm.parent
    physics_exported = bool(
        arm.animation_data and "baked native" in arm.animation_data.action.name
    )
    if physics_exported:
        # The native simulation has been visually baked into pose channels.
        # Remove runtime physics and thousands of helper constraints so the
        # production file reopens without an external cache or live simulation.
        from bl_ext.blender_org.mmd_tools.core.model import Model

        rig = Model(root)
        groups = [
            rig.rigidGroupObject(),
            rig.jointGroupObject(),
            rig.temporaryGroupObject(),
        ]
        garbage = set()
        for group in groups:
            if group:
                garbage.update(group.children_recursive)
                garbage.add(group)
        for b in arm.pose.bones:
            c = b.constraints.get("mmd_tools_rigid_track")
            if c:
                b.constraints.remove(c)
        if scene.rigidbody_world:
            bpy.ops.rigidbody.world_remove()
        bpy.data.batch_remove(ids=garbage)
        root.mmd_root.is_built = False
        root["production_physics_baked"] = True
    for o in list(scene.objects):
        if o.type == "LIGHT" or o.name.startswith("Draft_Floor"):
            bpy.data.objects.remove(o, do_unlink=True)
    meshes = [
        o
        for o in scene.objects
        if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
    ]
    for mesh in meshes:
        for material in mesh.data.materials:
            if material:
                toon_material(material)
    stage = create_stage()
    for name, loc, power, size, color in [
        ("Key softbox", (-3, -4, 6), 200, 5, (1, 0.86, 0.82)),
        ("Fill softbox", (4, -2, 4), 140, 4, (0.85, 0.88, 1)),
        ("Stage softbox", (0, 3, 5), 350, 4, (1, 0.82, 0.74)),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power
        data.size = size
        data.color = color
        o = bpy.data.objects.new(name, data)
        scene.collection.objects.link(o)
        o.location = loc
        point_at(o, (0, 0, 1))
    scene.world.color = (0.4, 0.35, 0.4)
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.65, 0.55, 0.60, 1)
    bg.inputs[1].default_value = 0.65
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 48
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1920
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.render.fps_base = 1
    # Load author camera as a timing/FOV reference, then build a separately
    # corrected portrait camera. The original author data stays in the project.
    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.camera_add()
    source_camera = bpy.context.object
    source_camera.name = "Waterfall_Mina_Source_Camera"
    bpy.ops.mmd_tools.import_vmd(
        filepath=str(args.camera_vmd),
        scale=0.08,
        create_new_action=True,
        update_scene_settings=False,
        log_level="ERROR",
    )
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "Final | single portrait director"
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = 32
    cam.data.lens = 60
    focus = bpy.data.objects.new("Final | face focus", None)
    scene.collection.objects.link(focus)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = focus
    cam.data.dof.aperture_fstop = 2.0
    cam.data.dof.aperture_blades = 8
    scene.camera = cam
    head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
    start = time.time()
    for f in range(args.start, args.end + 1, 1):
        scene.frame_set(f)
        h = arm.matrix_world @ head.matrix.translation
        # Keep a bright, face-readable portrait rather than directly cropping
        # the original duo shot. Source focal changes retain shot rhythm.
        source_lens = source_camera.data.lens
        span = max(1.05, min(1.60, 1.35 - (source_lens - 40) * 0.008))
        yaw = 0.11 * math.sin(f / 220) + 0.035 * math.sin(f / 57)
        target = h + Vector((0, 0, -span * 0.28))
        distance = span * cam.data.lens / cam.data.sensor_height
        cam.location = target + Vector(
            (math.sin(yaw) * distance, -math.cos(yaw) * distance, 0.08)
        )
        point_at(cam, target)
        focus.location = h + Vector((0, -0.025, 0.07))
        for prop in ["location", "rotation_euler"]:
            cam.keyframe_insert(data_path=prop, frame=f)
        focus.keyframe_insert(data_path="location", frame=f)
        if f % 600 == 0:
            print("DIRECTOR_FRAME", f, round(time.time() - start, 1), flush=True)
    scene.frame_start = args.start
    scene.frame_end = args.end
    sample = args.frame
    retimed_curves = 0
    if args.output_fps != 30:
        factor = args.output_fps / 30
        retimed_curves = retime_actions(args.start, factor)
        scene.render.fps = args.output_fps
        scene.frame_start = 1
        scene.frame_end = round((args.end - args.start) * factor)
        sample = round((args.frame - args.start) * factor + 1)
        if scene.sequence_editor:
            for strip in scene.sequence_editor.strips:
                if strip.type == "SOUND":
                    strip.frame_start = 1 - round((args.start - 1) * factor)
    scene.frame_set(sample)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str(args.output_dir / "look-sample.png")
    # Textures packed for reuse. Physics cache remains alongside its source
    # project until the dedicated bake-export step makes a portable action.
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_dir / "production.blend"))
    if args.sample_only:
        scene.render.resolution_percentage = 50
    bpy.ops.render.render(write_still=True)
    report = {
        "stage": stage,
        "source_frames": [args.start, args.end],
        "output_frames": [scene.frame_start, scene.frame_end],
        "resolution": [1080, 1920],
        "fps": args.output_fps,
        "materials": "per-slot texture-preserving NPR",
        "physics_baked_to_action": physics_exported,
        "retimed_curves": retimed_curves,
        "camera_reference": str(args.camera_vmd),
        "sample_frame": sample,
    }
    (args.output_dir / "production-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("PRODUCTION_SCENE_OK", args.output_dir, flush=True)


if __name__ == "__main__":
    main()
