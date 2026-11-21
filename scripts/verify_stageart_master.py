"""Reopen a stage-art master and verify motion, output isolation and ground scope."""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_duet_integration import snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    source = bpy.data.filepath
    frames = (1, 2100, 4140, 4200, 4250, 4262, 4290, 4439, 8400, 11899)
    expected = {}
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        expected[frame] = snapshot(bpy.context.scene)
    bpy.ops.wm.open_mainfile(filepath=str(args.target))
    scene = bpy.context.scene
    preserved = []
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        assert snapshot(scene) == expected[frame], frame
        preserved.append(
            {"frame": frame, "all_bones_camera_matrix_and_lens_exactly_equal": True}
        )
    assert scene.get("stageart_revision") == "hesperides-stageart-v2"
    assert scene.rigidbody_world is None
    assert [scene.frame_start, scene.frame_end] == [4140, 4439]
    assert scene.render.fps == 60 and scene.render.engine == "BLENDER_EEVEE"
    file_outputs = [
        n
        for other in bpy.data.scenes
        if other.compositing_node_group
        for n in other.compositing_node_group.nodes
        if n.type == "OUTPUT_FILE"
    ]
    assert file_outputs and all(n.mute for n in file_outputs)
    images = [i for i in bpy.data.images if i.source == "FILE"]
    assert images and all(i.packed_file for i in images)
    ground = []
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
        for polygon in obj.data.polygons:
            mat = (
                obj.data.materials[polygon.material_index]
                if obj.data.materials
                else None
            )
            if not mat or not mat.name.startswith("Stage art | ground only |"):
                continue
            center = obj.matrix_world @ polygon.center
            normal = (normal_matrix @ polygon.normal).normalized()
            assert (
                not obj.get("performer_id")
                and -0.2001 <= center.z <= 0.1201
                and normal.z >= 0.9499
            )
            ground.append(
                {
                    "object": obj.name,
                    "polygon": polygon.index,
                    "world_z": center.z,
                    "normal_z": normal.z,
                }
            )
    assert ground
    projector = scene.objects["Stage art | grounded backlight"]
    blockers = list(projector.light_linking.blocker_collection.objects)
    assert blockers and all(
        o.get("performer_id") and o.type == "MESH" for o in blockers
    )
    assert projector.data.use_shadow
    assert scene.objects["Stage art | rear air only"].hide_render is False
    assert scene.view_layers[0].aovs["StageArtRim"].type == "COLOR"
    faces = []
    for mat in bpy.data.materials:
        if mat.get("performer_id") and mat.name.split(".")[0] in {
            "颜",
            "面1",
            "面2",
            "肌",
            "眉",
            "睫",
            "口",
            "目",
            "目白",
            "白目",
        }:
            aov = next(
                n
                for n in mat.node_tree.nodes
                if n.type == "OUTPUT_AOV" and n.aov_name == "StageArtRim"
            )
            assert (
                not aov.inputs["Color"].is_linked
                and max(aov.inputs["Color"].default_value[:3]) == 0
            ), (
                mat.name,
                aov.inputs["Color"].is_linked,
                list(aov.inputs["Color"].default_value),
            )
            faces.append(mat.name)
    assert len(faces) >= 6
    optics = []
    for frame in range(4140, 4440):
        scene.frame_set(frame)
        dof = scene.camera.data.dof
        assert dof.use_dof and 3.1999 <= dof.aperture_fstop <= 5.6001
        assert (
            scene.render.use_motion_blur
            and 0 <= scene.render.motion_blur_shutter <= 0.2801
        )
        optics.append(
            {
                "frame": frame,
                "fstop": dof.aperture_fstop,
                "shutter_frames": scene.render.motion_blur_shutter,
            }
        )
    report = {
        "source": source,
        "target": str(args.target),
        "motion_samples": preserved,
        "ground_polygon_count": len(ground),
        "ground_bounds": [
            min(p["world_z"] for p in ground),
            max(p["world_z"] for p in ground),
        ],
        "all_ground_selection_constraints_passed": True,
        "packed_file_images": len(images),
        "file_output_nodes_muted": len(file_outputs),
        "performer_shadow_blockers": len(blockers),
        "face_eye_materials_excluded_from_rim_aov": faces,
        "optics_frames": 300,
        "fstop_range": [
            min(p["fstop"] for p in optics),
            max(p["fstop"] for p in optics),
        ],
        "shutter_range": [
            min(p["shutter_frames"] for p in optics),
            max(p["shutter_frames"] for p in optics),
        ],
        "passed": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("STAGEART_MASTER_REOPEN_VERIFIED", flush=True)


if __name__ == "__main__":
    main()
