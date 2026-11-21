"""Render three controlled motion probes on an unsaved independent scene copy."""

import argparse
import json
import math
import subprocess
import sys
import warnings
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import aim
from review_video_color import encoder_arguments


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--temp-dir", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=24)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--neutral", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    args.temp_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    # Diagnostic renders must never write to a production EXR sequence inherited
    # from the opened master, even though the blend itself is not saved.
    if scene.compositing_node_group:
        for node in scene.compositing_node_group.nodes:
            if node.bl_idname == "CompositorNodeOutputFile":
                node.mute = True
    scene.frame_set(4200)
    bpy.context.view_layer.update()
    if args.neutral:
        for obj in scene.objects:
            if obj.type in {"MESH", "VOLUME", "LIGHT_PROBE"} and not obj.get(
                "performer_id"
            ):
                obj.hide_render = True
            if obj.type == "LIGHT" and not obj.name.startswith("Reference duet |"):
                obj.hide_render = True
        scene.world = bpy.data.worlds.new("Quality | neutral diagnostic world")
        scene.world.use_nodes = True
        world_tree = scene.world.node_tree
        background = world_tree.nodes.new("ShaderNodeBackground")
        output = world_tree.nodes.new("ShaderNodeOutputWorld")
        world_tree.links.new(background.outputs[0], output.inputs["Surface"])
        background.inputs["Color"].default_value = (0.025, 0.025, 0.025, 1)
        background.inputs["Strength"].default_value = 0.1
        scene.render.use_compositing = False
    scene.render.use_motion_blur = False
    actor_data = {}
    for arm in scene.objects:
        if arm.type != "ARMATURE" or not arm.get("performer_id"):
            continue
        poses = {bone.name: bone.matrix_basis.copy() for bone in arm.pose.bones}
        if arm.animation_data:
            arm.animation_data.action = None
        for bone in arm.pose.bones:
            bone.matrix_basis = poses[bone.name]
        head = next(bone for bone in arm.pose.bones if bone.mmd_bone.name_j == "頭")
        actor = arm["performer_id"]
        actor_data[actor] = {
            "arm": arm,
            "head": head,
            "head_matrix": head.matrix.copy(),
            "controller": bpy.data.objects["Genshin study | head axes | " + actor],
            "origin": bpy.data.objects["Quality | " + actor + " | head origin"],
            "key": bpy.data.objects["Reference duet | " + actor + " | key"],
        }
    bpy.context.view_layer.update()
    target = sum(
        (data["origin"].matrix_world.translation for data in actor_data.values()),
        Vector(),
    ) / len(actor_data)
    target -= Vector((0, 0, 0.11))
    camera = scene.camera.copy()
    camera.data = scene.camera.data.copy()
    camera.parent = None
    camera.matrix_parent_inverse.identity()
    camera.constraints.clear()
    camera.scale = (1, 1, 1)
    camera.animation_data_clear()
    camera.data.animation_data_clear()
    camera.name = "Quality | controlled diagnostic camera"
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 55
    camera.data.shift_x = camera.data.shift_y = 0
    camera.data.sensor_width = 36
    camera.data.sensor_fit = "HORIZONTAL"
    camera.data.dof.use_dof = False
    span = (
        max(data["origin"].matrix_world.translation.x for data in actor_data.values())
        - min(data["origin"].matrix_world.translation.x for data in actor_data.values())
        + 0.65
    )
    distance = max(3.7, span * 55 / 36 * 1.1)
    base_offset = Vector((0, -distance, 0.12))
    light_matrices = {
        actor: data["key"].matrix_world.copy() for actor, data in actor_data.items()
    }
    width, height = args.width, args.width * 9 // 16
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = args.samples
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.color_mode = "RGB"
    records = []
    for case in ["head-turn", "key-orbit", "camera-orbit"]:
        frames = args.temp_dir / case
        frames.mkdir()
        for index in range(args.frames):
            # Smooth monotonic sweep; every output frame is separately rendered.
            phase = index / (args.frames - 1)
            angle = math.radians(
                (-1 + 2 * phase)
                * (35 if case == "head-turn" else 90 if case == "key-orbit" else 15)
            )
            for actor, data in actor_data.items():
                data["head"].matrix = data["head_matrix"]
                data["key"].matrix_world = light_matrices[actor]
            camera.location = target + base_offset
            if case == "head-turn":
                for data in actor_data.values():
                    world = data["arm"].matrix_world @ data["head_matrix"]
                    pivot = world.translation
                    world = (
                        Matrix.Translation(pivot)
                        @ Matrix.Rotation(angle, 4, "Z")
                        @ Matrix.Translation(-pivot)
                        @ world
                    )
                    data["head"].matrix = data["arm"].matrix_world.inverted() @ world
            elif case == "key-orbit":
                for actor, data in actor_data.items():
                    data["key"].matrix_world = (
                        Matrix.Translation(target)
                        @ Matrix.Rotation(angle, 4, "Z")
                        @ Matrix.Translation(-target)
                        @ light_matrices[actor]
                    )
                    aim(data["key"], target)
            else:
                camera.location = target + Matrix.Rotation(angle, 3, "Z") @ base_offset
            aim(camera, target)
            bpy.context.view_layer.update()
            entry = {
                "case": case,
                "frame": index,
                "angle_degrees": math.degrees(angle),
                "actors": {},
            }
            for actor, data in actor_data.items():
                axes = {}
                for name, axis in [
                    ("up", Vector((0, 0, 1))),
                    ("forward", Vector((0, -1, 0))),
                ]:
                    arm, head = data["arm"], data["head"]
                    expected = (
                        arm.matrix_world.to_3x3()
                        @ head.matrix.to_3x3()
                        @ head.bone.matrix_local.to_3x3().inverted()
                        @ arm.matrix_world.to_3x3().inverted()
                        @ axis
                    )
                    actual = Vector(data["controller"][name]).normalized()
                    error = (actual - expected.normalized()).length
                    assert error < 0.0001, (case, actor, name, error)
                    axes[name] = {"vector": list(actual), "error": error}
                up = Vector(axes["up"]["vector"])
                forward = Vector(axes["forward"]["vector"])
                right = forward.cross(up).normalized()
                center = (
                    data["origin"].matrix_world.translation - up * 0.09 + forward * 0.07
                )
                corners = [
                    world_to_camera_view(scene, camera, center + right * x + up * y)
                    for x in [-0.15, 0.15]
                    for y in [-0.17, 0.17]
                ]
                box = [
                    min(p.x for p in corners) * width,
                    (1 - max(p.y for p in corners)) * height,
                    max(p.x for p in corners) * width,
                    (1 - min(p.y for p in corners)) * height,
                ]
                assert (
                    box[0] > 0 and box[1] > 0 and box[2] < width and box[3] < height
                ), (
                    case,
                    actor,
                    box,
                )
                entry["actors"][actor] = {
                    "axes": axes,
                    "face_roi": box,
                    "head_origin": list(data["origin"].matrix_world.translation),
                }
            scene.render.filepath = str(frames / f"frame-{index:04d}.png")
            bpy.ops.render.render(write_still=True)
            records.append(entry)
            if (index + 1) % 6 == 0:
                print(
                    "DIAGNOSTIC_PROGRESS", case, index + 1, "/", args.frames, flush=True
                )
        subprocess.run(
            [
                str(args.ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-framerate",
                "24",
                "-i",
                str(frames / "frame-%04d.png"),
                "-frames:v",
                str(args.frames),
                "-an",
                "-c:v",
                "libx264",
                "-crf",
                "16",
                *encoder_arguments(),
                str(args.output_dir / f"{case}.mp4"),
            ],
            check=True,
        )
    concat = args.output_dir / "diagnostic-concat.txt"
    concat.write_text(
        "\n".join(
            "file '" + str(args.output_dir / (case + ".mp4")).replace("\\", "/") + "'"
            for case in ["head-turn", "key-orbit", "camera-orbit"]
        ),
        encoding="utf-8",
    )
    command = [
        str(args.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-c",
        "copy",
        str(args.output_dir / "Shader_Stability_3_Cases.mp4"),
    ]
    subprocess.run(command, check=True)
    (args.output_dir / "diagnostic-records.json").write_text(
        json.dumps(
            {
                "frames_per_case": args.frames,
                "fps": 24,
                "resolution": [width, height],
                "neutral": args.neutral,
                "lighting_revision": scene.get("character_layer_revision"),
                "source_pose": 4200,
                "rendered_records": records,
                "temporary_frames": str(args.temp_dir),
                "scope": "Controlled shader probes only; not replacement choreography or camera; no production file saved",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("SHADER_DIAGNOSTICS_COMPLETE", str(args.output_dir), flush=True)


if __name__ == "__main__":
    main()
