"""Reopen and verify bounded eye geometry, preserved motion and saved shader routes."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import ACTORS, PREFIX, PRIVATE, ROOT
from render_portrait_light_controls import mute_file_outputs
from snapshot_goo_scene import capture


def coordinates(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", result)
    evaluated.to_mesh_clear()
    return result.reshape((-1, 3))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iteration", default="production-v4")
    parser.add_argument("--render-controls", action="store_true")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    production = ROOT / args.iteration
    prep = json.loads((production / "preparation.json").read_text(encoding="utf-8"))
    project = Path(prep["project"])
    assert hashlib.sha256(project.read_bytes()).hexdigest() == prep["project_sha256"]
    register_addons()
    assert not hasattr(bpy.types.Scene, "jelly_eye")
    bpy.ops.wm.open_mainfile(filepath=str(project), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    expected = json.loads((PRIVATE / "new-snapshot.json").read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(capture()))
    checks = {
        k: actual[k] == expected[k]
        for k in ("actions", "geometry", "images", "samples", "fps")
    }
    checks["images"] = all(row in actual["images"] for row in expected["images"])
    report = {
        "project": str(project),
        "project_sha256": prep["project_sha256"],
        "checks": checks,
        "geometry_samples": [],
        "jelly_addon_registered": hasattr(bpy.types.Scene, "jelly_eye"),
        "scope": [4140, 4441],
    }
    for actor, spec in ACTORS.items():
        obj = bpy.data.objects[spec["mesh"]]
        mods = [
            m for m in obj.modifiers if m.type == "NODES" and m.name.startswith("JE_")
        ]
        arm_index = next(i for i, m in enumerate(obj.modifiers) if m.type == "ARMATURE")
        checks[actor + "_two_eye_modifiers_before_armature"] = len(mods) == 2 and all(
            obj.modifiers.find(m.name) < arm_index for m in mods
        )
        allowed = sorted(
            {
                v
                for p in obj.data.polygons
                if obj.data.materials[p.material_index].name in spec["eyes"]
                for v in p.vertices
            }
        )
        outside = np.ones(len(obj.data.vertices), dtype=bool)
        outside[allowed] = False
        shell = [(m, m.show_viewport) for m in obj.modifiers if m.type == "SOLIDIFY"]
        for m, _ in shell:
            m.show_viewport = False
        max_delta, max_outside, max_helper = 0.0, 0.0, 0.0
        for frame in (4140, 4156, 4160, 4164, 4170, 4200, 4290, 4370, 4438, 4441):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            on = coordinates(obj)
            for m in mods:
                m.show_viewport = False
            bpy.context.view_layer.update()
            off = coordinates(obj)
            for m in mods:
                m.show_viewport = True
            bpy.context.view_layer.update()
            assert on.shape == off.shape == (len(obj.data.vertices), 3)
            delta = np.linalg.norm(on - off, axis=1)
            local = float(delta[allowed].max())
            excluded = float(delta[outside].max())
            max_delta, max_outside = max(max_delta, local), max(max_outside, excluded)
            arm = obj.find_armature()
            for helper in [
                o for o in scene.objects if o.name.startswith(PREFIX + actor + " eye ")
            ]:
                head = helper.parent_bone
                deform = (
                    arm.matrix_world
                    @ arm.pose.bones[head].matrix
                    @ arm.data.bones[head].matrix_local.inverted()
                    @ arm.matrix_world.inverted()
                    @ obj.matrix_world
                )
                expected_center = deform @ Vector(helper["rest_eye_center"])
                max_helper = max(
                    max_helper,
                    (helper.matrix_world.translation - expected_center).length,
                )
            report["geometry_samples"].append(
                {
                    "actor": actor,
                    "frame": frame,
                    "max_eye_delta_m": local,
                    "max_non_eye_delta_m": excluded,
                }
            )
        for m, value in shell:
            m.show_viewport = value
        checks[actor + "_non_eye_vertices_unchanged"] = max_outside < 1e-5
        checks[actor + "_eye_delta_bounded"] = max_delta < 0.012
        checks[actor + "_eye_peek_follows_head"] = max_helper < 1e-5
        report[actor] = {
            "max_eye_delta_m": max_delta,
            "max_non_eye_delta_m": max_outside,
            "max_helper_error_m": max_helper,
        }
    checks["aksiniya_effect_nonzero"] = report["aksiniya"]["max_eye_delta_m"] > 1e-5
    checks["hair_shadow_and_peek_materials"] = all(
        bpy.data.materials[r["material"]].check_shadow_id
        and bpy.data.materials[r["material"]].node_tree.nodes.get(
            PREFIX + "eye region bang peek"
        )
        is not None
        for r in prep["hair"]
    )
    if prep.get("eye_see_through") == "deferred":
        checks["added_eye_transparency_disabled"] = all(
            not bpy.data.materials[r["material"]]
            .node_tree.nodes[PREFIX + "eye region bang peek"]
            .inputs[0]
            .is_linked
            and bpy.data.materials[r["material"]]
            .node_tree.nodes[PREFIX + "eye region bang peek"]
            .inputs[0]
            .default_value
            == 0
            for r in prep["hair"]
        )
    if prep.get("animated_hair_shadows"):
        manifest = json.loads(
            (production / "hair-shadow-manifest.json").read_text(encoding="utf-8")
        )
        checks["six_hundred_native_shadow_files"] = len(
            manifest["files"]
        ) == 600 and all(
            hashlib.sha256(
                (production / "hair-shadows" / row["file"]).read_bytes()
            ).hexdigest()
            == row["sha256"]
            for row in manifest["files"]
        )
        checks["portable_shadow_sequence_timing"] = all(
            bpy.data.materials[name]
            .node_tree.nodes[PREFIX + "geometry derived hair shadow"]
            .image.source
            == "SEQUENCE"
            and bpy.data.materials[name]
            .node_tree.nodes[PREFIX + "geometry derived hair shadow"]
            .image.filepath.replace("\\", "/")
            .startswith("//hair-shadows/")
            and bpy.data.materials[name]
            .node_tree.nodes[PREFIX + "geometry derived hair shadow"]
            .image_user.frame_start
            == 4140
            and bpy.data.materials[name]
            .node_tree.nodes[PREFIX + "geometry derived hair shadow"]
            .image_user.frame_duration
            == 300
            for name in ("颜", "颜.001")
        )
    checks["pure_contour_aov"] = all(
        scene.compositing_node_group.nodes[n].inputs["Image"].links[0].from_socket.name
        == "ContourRim"
        for n in (
            "Goo window wrap | tight white edge bloom",
            "Goo window wrap | soft outer edge diffusion",
        )
    )
    report["passed"] = all(checks.values())
    (production / "master-verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("EYE_HAIR_STAGE_MASTER", json.dumps(report, ensure_ascii=False), flush=True)
    assert report["passed"], checks
    if not args.render_controls:
        return

    shadow_probe_directory = None
    if prep.get("animated_hair_shadows"):
        from check_goo_rendered_shadow_aovs import compare, setup

        shadow_probe_directory = setup(scene, production)

    def check_rendered_shadow_sequence():
        if shadow_probe_directory is not None:
            compare(scene, production, shadow_probe_directory)

    scene.frame_set(4290)
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.eevee.taa_render_samples = 24
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 95
    scene.render.filepath = str(production / "portrait-4290.jpg")
    bpy.ops.render.render(write_still=True)
    check_rendered_shadow_sequence()
    controls = production / "eye-controls-v3"
    controls.mkdir(exist_ok=False)
    camera_data = bpy.data.cameras.new("Eye study camera")
    camera = bpy.data.objects.new("Eye study camera", camera_data)
    scene.collection.objects.link(camera)
    for marker in scene.timeline_markers:
        marker.camera = None
    scene.camera = camera
    camera_data.lens = 72
    camera_data.dof.use_dof = False
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.eevee.taa_render_samples = 32
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 96
    tree = scene.compositing_node_group
    render = next(n for n in tree.nodes if n.type == "R_LAYERS")
    mask_file = tree.nodes.new("CompositorNodeOutputFile")
    mask_file.directory = str(controls)
    mask_file.format.media_type = "IMAGE"
    mask_file.format.file_format = "PNG"
    mask_file.format.color_depth = "16"
    mask_file.save_as_render = False
    mask_file.file_output_items.clear()
    mask_file.file_output_items.new("FLOAT", "BangPeek")
    tree.links.new(render.outputs["BangPeek"], mask_file.inputs["BangPeek"])
    for actor, frame in (("aksiniya", 4290), ("ikhor", 4290), ("aksiniya", 4160)):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        # MMD's frame handler restores the authored camera before our override.
        scene.camera = camera
        helpers = [
            scene.objects[PREFIX + actor + " eye " + side] for side in ("L", "R")
        ]
        center = (
            helpers[0].matrix_world.translation + helpers[1].matrix_world.translation
        ) * 0.5
        rotation = helpers[0].matrix_world.to_3x3()
        forward = rotation @ Vector((0, -1, 0))
        up = rotation @ Vector((0, 0, 1))
        camera.location = center + forward.normalized() * 0.40 + up.normalized() * 0.025
        camera.rotation_euler = (
            (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        bpy.context.view_layer.update()
        assert scene.camera == camera
        scene.render.filepath = str(controls / f"{actor}-{frame}-effects-on.jpg")
        mask_file.file_name = f"{actor}_{frame}_peek_"
        mask_file.mute = False
        bpy.ops.render.render(write_still=True)
        check_rendered_shadow_sequence()
        mask_file.mute = True
        print("EYE_DETAIL_CONTROL", actor, frame, flush=True)
        if frame == 4290:
            saved = []
            for mat in bpy.data.materials:
                if mat.get("performer_id") != actor or not mat.node_tree:
                    continue
                tree = mat.node_tree
                for name, index in (
                    ("HDR catchlight gain", 1),
                    ("subtle bang transparency", 1),
                    ("projected bang transparency", 1),
                    ("ray corrected bang transparency", 1),
                ):
                    item = tree.nodes.get(PREFIX + name)
                    if item:
                        saved.append(
                            (item.inputs[index], item.inputs[index].default_value)
                        )
                        item.inputs[index].default_value = 0
                gloss = tree.nodes.get(PREFIX + "wet corneal reflection")
                if gloss:
                    saved.append(
                        (
                            gloss.inputs["Color"],
                            tuple(gloss.inputs["Color"].default_value),
                        )
                    )
                    gloss.inputs["Color"].default_value = (0, 0, 0, 1)
            scene.render.filepath = str(controls / f"{actor}-{frame}-effects-off.jpg")
            bpy.ops.render.render(write_still=True)
            for socket, value in saved:
                socket.default_value = value
    print("EYE_DETAIL_CONTROLS_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
