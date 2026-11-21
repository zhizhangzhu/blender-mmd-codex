"""Build an independent lighting, focus and shutter study from the repaired master.

Does not overwrite the accepted image, source choreography or camera movement.
File Output nodes are muted before any diagnostic rendering.
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import aim, area, math_node
from stage_night_art_lab import mix, spot, surfaces
from verify_duet_integration import snapshot


def heads(scene):
    result = []
    for arm in scene.objects:
        if arm.type == "ARMATURE" and arm.get("performer_id"):
            bone = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
            result.append(arm.matrix_world @ bone.matrix.translation)
    assert len(result) == 2
    return result


def directional_rims(scene, spec):
    changed = []
    mats = {
        m
        for o in scene.objects
        if o.type == "MESH" and not o.hide_render
        for m in o.data.materials
        if m and m.node_tree and m.get("performer_id")
    }
    for mat in mats:
        # Facial shading and all existing dark ink stay untouched.
        name = mat.name.split(".")[0]
        if name in {"面1", "面2"} or any(
            k in name for k in ("目", "眉", "睫", "口", "舌", "颜", "肌", "二重", "脸")
        ):
            continue
        gain = (
            spec["hair_gain"]
            if any(k in name for k in ("发", "鬓", "呆毛"))
            else spec["body_gain"]
        )
        tree = mat.node_tree
        geom = tree.nodes.new("ShaderNodeNewGeometry")
        delta = tree.nodes.new("ShaderNodeVectorMath")
        delta.operation = "SUBTRACT"
        delta.inputs[0].default_value = spec["location"]
        tree.links.new(geom.outputs["Position"], delta.inputs[1])
        norm = tree.nodes.new("ShaderNodeVectorMath")
        norm.operation = "NORMALIZE"
        tree.links.new(delta.outputs[0], norm.inputs[0])
        dot = tree.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        tree.links.new(norm.outputs[0], dot.inputs[0])
        tree.links.new(geom.outputs["Normal"], dot.inputs[1])
        facing = tree.nodes.new("ShaderNodeVectorMath")
        facing.operation = "DOT_PRODUCT"
        tree.links.new(geom.outputs["Normal"], facing.inputs[0])
        tree.links.new(geom.outputs["Incoming"], facing.inputs[1])
        absolute = math_node(
            tree, "Cinema | absolute view cosine", "ABSOLUTE", facing.outputs["Value"]
        )
        edge = math_node(tree, "Cinema | grazing rim", "SUBTRACT", 1, absolute)
        edge = math_node(tree, "Cinema | narrow rim", "POWER", edge, 3)
        positive = math_node(
            tree, "Cinema | lit rim side", "MAXIMUM", dot.outputs["Value"], 0
        )
        weight = math_node(tree, "Cinema | directional rim", "MULTIPLY", edge, positive)
        weight = math_node(tree, "Cinema | rim gain", "MULTIPLY", weight, gain)
        tint = mix(tree, "MULTIPLY", spec["color"] + [1], weight)
        for emission in [n for n in tree.nodes if n.type == "EMISSION"]:
            color = (
                emission.inputs[0].links[0].from_socket
                if emission.inputs[0].is_linked
                else tuple(emission.inputs[0].default_value)
            )
            tree.links.new(mix(tree, "ADD", color, tint), emission.inputs[0])
        changed.append(mat.name)
    return changed


def bake_optics(scene, config, start, end):
    camera = scene.camera
    data = camera.data
    data.dof.focus_object = None
    data.dof.use_dof = True
    data.dof.aperture_blades = config["camera"]["aperture_blades"]
    data.dof.aperture_ratio = config["camera"]["aperture_ratio"]
    motion = config["motion"]
    scene.render.use_motion_blur = True
    scene.render.motion_blur_position = "CENTER"
    scene.eevee.motion_blur_steps = motion["steps"]
    scene.eevee.motion_blur_max = motion["max_blur_pixels"]
    scene.eevee.motion_blur_depth_scale = motion["bleeding_bias"]
    scene.eevee.use_bokeh_jittered = False
    scene.eevee.bokeh_max_size = 48
    records = []
    previous = None
    cuts = set()
    for frame in range(start - 1, end + 2):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        inverse = camera.matrix_world.inverted()
        depths = [-(inverse @ p).z for p in heads(scene)]
        assert min(depths) > 0
        distance = sum(depths) / 2
        lens = data.lens
        # Thin-lens circle of confusion in millimetres, converted to output pixels.
        required = max(
            lens
            * lens
            * abs(z - distance)
            / (z * (distance * 1000 - lens))
            * scene.render.resolution_x
            / data.sensor_width
            / config["camera"]["maximum_face_coc_pixels"]
            for z in depths
        )
        aperture = max(config["camera"]["minimum_fstop"], required)
        assert aperture <= config["camera"]["maximum_fstop"], (
            "Pair depth exceeds this shot's focus budget"
        )
        data.dof.focus_distance = distance
        data.dof.aperture_fstop = aperture
        data.keyframe_insert(
            "dof.focus_distance", frame=frame, group="Cinema | duet focus"
        )
        data.keyframe_insert(
            "dof.aperture_fstop", frame=frame, group="Cinema | duet focus"
        )
        matrix = camera.matrix_world.copy()
        if previous:
            moved = (matrix.translation - previous[0].translation).length
            rotated = (
                matrix.to_quaternion()
                .rotation_difference(previous[0].to_quaternion())
                .angle
            )
            if (
                moved > motion["cut_translation_per_frame"]
                or rotated > motion["cut_rotation_radians_per_frame"]
                or abs(lens - previous[1]) > motion["cut_lens_mm_per_frame"]
            ):
                cuts.update((frame - 1, frame))
        previous = (matrix, lens)
        actual_coc = [
            lens
            * lens
            * abs(z - distance)
            / (aperture * z * (distance * 1000 - lens))
            * scene.render.resolution_x
            / data.sensor_width
            for z in depths
        ]
        records.append(
            {
                "frame": frame,
                "depths": depths,
                "focus_distance": distance,
                "fstop": aperture,
                "lens": lens,
                "predicted_head_coc_pixels": actual_coc,
            }
        )
    for frame in range(start - 1, end + 2):
        scene.render.motion_blur_shutter = (
            0 if frame in cuts else motion["shutter_frames"]
        )
        scene.keyframe_insert(
            "render.motion_blur_shutter", frame=frame, group="Cinema | cut protection"
        )
    return {
        "frames": records,
        "cut_protection_frames": sorted(cuts),
        "maximum_predicted_head_coc_pixels": max(
            v for r in records for v in r["predicted_head_coc_pixels"]
        ),
    }


def still(scene, folder, label, frame=4200):
    scene.frame_set(frame)
    scene.render.filepath = str(folder / (label + ".png"))
    bpy.ops.render.render(write_still=True)


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    settings = json.loads(args.preset.read_text(encoding="utf-8"))
    source = bpy.data.filepath
    scene = bpy.context.scene
    assert scene.get("quality_light_space_revision") and not scene.get(
        "fox_cinema_revision"
    )
    # Old raw/final archives must never be written by this experiment.
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for n in other.compositing_node_group.nodes:
                if n.type == "OUTPUT_FILE":
                    n.mute = True
    before = {}
    for frame in (1, 2100, 4200, 8400, 11899):
        scene.frame_set(frame)
        before[frame] = snapshot(scene)
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 67
    scene.eevee.taa_render_samples = 48
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    still(scene, args.output_dir, "01-baseline")
    materials = surfaces(scene, settings)
    for mat in bpy.data.materials:
        if mat.get("stage_id") and mat.node_tree:
            response = mat.node_tree.nodes.get("Quality | bounded real illumination")
            if response:
                response.inputs["To Min"].default_value = settings[
                    "stage_physical_response"
                ]["floor"]
                response.inputs["From Max"].default_value = settings[
                    "stage_physical_response"
                ]["high"]
    for obj in scene.objects:
        if obj.type != "LIGHT" or obj.hide_render:
            continue
        if obj.name.startswith("Reference duet |"):
            obj.data.energy *= (
                1.6
                if obj.name.endswith(" | rim")
                else 0.5
                if obj.name.endswith(" | fill")
                else 1
            )
            obj.data.color = (
                (0.45, 0.62, 1)
                if obj.name.endswith(" | rim")
                else (1, 0.88, 0.83)
                if obj.name.endswith(" | key")
                else (0.5, 0.62, 1)
            )
            if obj.name.endswith(" | rim"):
                obj.location = settings["actor_rim"]["location"]
                aim(obj, (0, 0, 1))
        elif obj.data.type == "AREA":
            obj.hide_render = True
        elif obj.data.type == "POINT":
            obj.data.energy *= 0.8
    area(
        "Cinema | cold window",
        location=settings["moon_area"]["location"],
        target=settings["moon_area"]["target"],
        energy=settings["moon_area"]["watts"],
        color=settings["moon_area"]["color"],
        size=settings["moon_area"]["size"],
    )
    spot(scene, "Cinema | cold backlight", settings["moon_spot"])
    spot(scene, "Cinema | warm aisle", settings["altar_spot"])
    spot(scene, "Cinema | rear floor projector", settings["back_projector"])
    rims = directional_rims(scene, settings["actor_rim"])
    sky = next(n for n in scene.world.node_tree.nodes if n.type == "VALTORGB")
    sky.color_ramp.elements[0].color = settings["sky_dark"]
    sky.color_ramp.elements[-1].color = settings["sky_cloud"]
    next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND").inputs[
        "Strength"
    ].default_value = 1
    grade = scene.compositing_node_group.nodes.get(
        "Reference | stage-only reference grade"
    )
    if grade:
        grade.inputs["Fac"].default_value = 0
    # Recompute static indirect light with no baked-in performer silhouettes.
    hidden = [(o, o.hide_render) for o in scene.objects if o.get("performer_id")]
    for obj, _ in hidden:
        obj.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    probe = next(
        o for o in scene.objects if o.type == "LIGHT_PROBE" and o.data.type == "VOLUME"
    )
    probe.select_set(True)
    bpy.context.view_layer.objects.active = probe
    bpy.context.view_layer.update()
    assert bpy.ops.object.lightprobe_cache_bake(subset="SELECTED") == {"FINISHED"}
    for obj, was_hidden in hidden:
        obj.hide_render = was_hidden
    scene.frame_set(4200)
    still(scene, args.output_dir, "02-lighting-only")
    optics = bake_optics(scene, settings, 4140, 4439)
    scene.render.use_motion_blur = False
    still(scene, args.output_dir, "03-lighting-focus")
    still(scene, args.output_dir, "control-motion-off-4290", 4290)
    scene.render.use_motion_blur = True
    still(scene, args.output_dir, "04-lighting-focus-motion", 4290)
    still(scene, args.output_dir, "final-4420", 4420)
    # Camera/lens tests are unsaved perturbations, with matched subject framing.
    scene.frame_set(4200)
    bpy.context.view_layer.update()
    original_camera = scene.camera
    original_world = original_camera.matrix_world.copy()
    original_data = original_camera.data
    camera = original_camera.copy()
    camera.data = original_data.copy()
    camera.parent = None
    camera.animation_data_clear()
    camera.data.animation_data_clear()
    camera.constraints.clear()
    scene.collection.objects.link(camera)
    scene.camera = camera
    center = sum(heads(scene), Vector()) / 2
    for lens in (35, 85):
        matrix = original_world.copy()
        matrix.translation = (
            center + (original_world.translation - center) * lens / original_data.lens
        )
        camera.matrix_world = matrix
        camera.data.lens = lens
        camera.data.dof.focus_distance = -(camera.matrix_world.inverted() @ center).z
        scene.render.filepath = str(
            args.output_dir / f"lens-{lens}mm-matched-framing.png"
        )
        bpy.ops.render.render(write_still=True)
    scene.camera = original_camera
    bpy.data.objects.remove(camera, do_unlink=True)
    # All camera and rig motion must still match; optical focus can change separately.
    errors = []
    for frame, expected in before.items():
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        actual = snapshot(scene)
        assert expected == actual, f"Source motion changed at {frame}"
        errors.append({"frame": frame, "rig_camera_and_lens_exactly_equal": True})
    scene.frame_set(4140)
    scene.render.resolution_percentage = 100
    scene.render.use_motion_blur = True
    scene.frame_start, scene.frame_end = 4140, 4439
    scene["fox_cinema_revision"] = settings["id"]
    scene["fox_cinema_scope"] = (
        "4140-4439 focus/shutter validated; original camera and all rigs retained. Auxiliary split scenes are not calibrated to this optical study."
    )
    bpy.ops.file.pack_all()
    project = args.output_dir / "Franken_Duet_Fox_Cinema.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "source": source,
        "project": str(project),
        "settings": settings,
        "materials": materials,
        "rim_materials": rims,
        "optics": optics,
        "source_motion_checks": errors,
        "file_outputs_muted": True,
        "scope": "native 5-second optics/lighting study; sample pending independent render verification",
        "volume": "not added: preserve contrast and avoid scattering the face light across the hall",
    }
    (args.output_dir / "cinema-study.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("FOX_CINEMA_PROJECT_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
