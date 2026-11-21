"""Pinned duet face-SDF adaptation; isolated stills, no motion or physics edits."""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_goo_face_hair_shadows import uv_template
from finalize_goo_character_lookdev import (
    animation,
    camera_record,
    digest,
    evaluated,
    fingerprint,
    glare_off,
    plain,
    protected_materials,
    restore_camera,
    rig_state,
    sha,
)
from goo_runtime import register_addons
from inspect_blender53_toon_package import tree_record
from prepare_goo_eye_hair_stage import ACTORS
from refine_goo_character_lookdev import hero_camera, render
from render_blender53_author_face_controls import png_difference
from render_portrait_light_controls import mute_file_outputs

SOURCE = Path(
    "D:/codex/output/Goo-Character-Lookdev-2026-11-18/final-v1/Franken_Character_Lookdev_Still.blend"
)
SOURCE_SHA = "66a030e52f93f373f009cd4308ad6b6bc6504387346ce4ca4adc43851357928a"
CACHE = Path("D:/codex/temp/Goo-Duet-SDF-2026-11-19")
ROOT = Path("D:/codex/output/Goo-Duet-SDF-2026-11-19")
FACE = {"aksiniya": "颜", "ikhor": "颜.001"}
PREFIX = "Duet SDF 19 | "


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def face_graph_signatures():
    result = {}
    for actor in ACTORS:
        tree = bpy.data.materials[FACE[actor]].node_tree
        value = {
            "nodes": [
                {
                    "name": n.name,
                    "kind": n.bl_idname,
                    "mute": n.mute,
                    "operation": getattr(n, "operation", None),
                    "blend_type": getattr(n, "blend_type", None),
                    "image": getattr(n, "image", None).name
                    if getattr(n, "image", None)
                    else None,
                    "inputs": [
                        (s.identifier, plain(getattr(s, "default_value", None)))
                        for s in n.inputs
                    ],
                }
                for n in tree.nodes
            ],
            "links": [
                (
                    l.from_node.name,
                    l.from_socket.identifier,
                    l.to_node.name,
                    l.to_socket.identifier,
                )
                for l in tree.links
            ],
        }
        result[actor] = digest(value)
    return result


def head_driver_evidence(scene):
    records = {}
    for frame in (4140, 4218, 4290, 4370, 4438):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for actor in ACTORS:
            tree = bpy.data.materials[FACE[actor]].node_tree
            curves = [
                fc for fc in tree.animation_data.drivers if PREFIX in fc.data_path
            ]
            errors = []
            for fc in curves:
                assert fc.is_valid and fc.driver.expression == "position"
                target = fc.driver.variables[0].targets[0]
                assert (
                    target.transform_space == "WORLD_SPACE"
                    and target.transform_type.startswith("LOC_")
                )
                axis = "XYZ".index(target.transform_type[-1])
                actual = tree.path_resolve(fc.data_path)
                errors.append(
                    abs(float(actual) - target.id.matrix_world.translation[axis])
                )
            root = scene.objects[PREFIX + actor + " full head basis"]
            eyes = scene.objects[f"Eye hair v1 | {actor} eye L"]
            expected = eyes.matrix_world.to_3x3().normalized()
            actual = root.matrix_world.to_3x3().normalized()
            axis_error = max(
                abs(actual[i][j] - expected[i][j]) for i in range(3) for j in range(3)
            )
            records[f"{actor}/{frame}"] = {
                "drivers": len(curves),
                "world_position_error": max(errors),
                "head_rotation_error": axis_error,
            }
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    assert max(r["world_position_error"] for r in records.values()) < 1e-5, records
    assert max(r["head_rotation_error"] for r in records.values()) < 1e-5, records
    return records


def new(tree, kind, label):
    item = tree.nodes.new(kind)
    item.name = item.label = PREFIX + label
    return item


def put(tree, value, socket):
    if hasattr(value, "is_output"):
        tree.links.new(value, socket)
    else:
        socket.default_value = value


def scalar(tree, operation, a, b, label):
    item = new(tree, "ShaderNodeMath", label)
    item.operation = operation
    put(tree, a, item.inputs[0])
    put(tree, b, item.inputs[1])
    return item.outputs[0]


def vector(tree, operation, a, b, label):
    item = new(tree, "ShaderNodeVectorMath", label)
    item.operation = operation
    put(tree, a, item.inputs[0])
    put(tree, b, item.inputs[1])
    return item.outputs["Value" if operation == "DOT_PRODUCT" else "Vector"]


def color(tree, a, b, factor, label, operation="MIX"):
    item = new(tree, "ShaderNodeMixRGB", label)
    item.blend_type = operation
    for value, socket in zip((factor, a, b), item.inputs):
        put(tree, value, socket)
    return item.outputs[0]


def remap(tree, value, low, high, a, b, label):
    item = new(tree, "ShaderNodeMapRange", label)
    item.interpolation_type = "SMOOTHSTEP"
    item.clamp = True
    for key, source in (
        ("Value", value),
        ("From Min", low),
        ("From Max", high),
        ("To Min", a),
        ("To Max", b),
    ):
        put(tree, source, item.inputs[key])
    return item.outputs[0]


def world_position(tree, obj, label):
    item = new(tree, "ShaderNodeCombineXYZ", label)
    for axis, socket in zip("XYZ", item.inputs):
        fc = socket.driver_add("default_value")
        variable = fc.driver.variables.new()
        variable.name = "position"
        variable.type = "TRANSFORMS"
        target = variable.targets[0]
        target.id = obj
        target.transform_type = "LOC_" + axis
        target.transform_space = "WORLD_SPACE"
        fc.driver.expression = "position"
    return item.outputs[0]


def source_contract(scene):
    value = {
        "fingerprint": fingerprint(scene),
        "rig": rig_state(scene),
        "protected": protected_materials(),
        "camera": camera_record(scene),
    }
    return json.loads(json.dumps(value, ensure_ascii=False))


def compare_contract(scene, baseline):
    current = source_contract(scene)
    checks = {
        key: current["fingerprint"][key] == baseline["fingerprint"][key]
        for key in (
            "actions",
            "geometry",
            "samples",
            "fps",
            "mesh_uv_weights_shapes",
            "color",
        )
    }
    # New helper empties and shader nodes are allowed; all original objects and
    # protected original texture/alpha nodes must keep their original contracts.
    checks["original_rig_actions_slots_constraints"] = all(
        current["rig"][section].get(name) == value
        for section in baseline["rig"]
        for name, value in baseline["rig"][section].items()
    )
    checks["original_textures_alpha"] = all(
        current["protected"][name]["settings"] == item["settings"]
        and all(
            current["protected"][name]["nodes"].get(n) == value
            for n, value in item["nodes"].items()
        )
        for name, item in baseline["protected"].items()
    )
    checks["original_camera_dof_markers_range"] = (
        current["camera"] == baseline["camera"]
    )
    return checks


def open_source():
    assert sha(SOURCE) == SOURCE_SHA
    register_addons()
    assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    mute_file_outputs()
    scene = bpy.context.scene
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    assert abs(scene.camera.data.lens - 61.73465) < 0.01
    return scene


def audit():
    CACHE.mkdir(parents=True, exist_ok=True)
    destination = CACHE / "current-face-audit.json"
    assert not destination.exists(), "Preserve original audit"
    scene = open_source()
    report = {
        "source": str(SOURCE),
        "sha256": SOURCE_SHA,
        "runtime": [bpy.app.version_string, bpy.app.build_hash.decode()],
        "fingerprint": fingerprint(scene),
        "camera": [scene.camera.name, scene.camera.data.lens],
        "actors": {},
        "groups": {},
    }
    for actor, spec in ACTORS.items():
        obj = scene.objects[spec["mesh"]]
        arm = obj.find_armature()
        mat = bpy.data.materials[FACE[actor]]
        mesh = obj.data
        mesh.calc_loop_triangles()
        triangles = [
            t for t in mesh.loop_triangles if mesh.materials[t.material_index] == mat
        ]
        ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        evaluated_mesh = ev.to_mesh()
        points = np.array(
            [tuple(obj.matrix_world @ v.co) for v in evaluated_mesh.vertices]
        )
        np.savez_compressed(
            CACHE / f"{actor}-face-geometry.npz",
            rest=np.array([v.co[:] for v in mesh.vertices]),
            evaluated=points[: len(mesh.vertices)],
            tri=np.array([t.vertices[:] for t in triangles], dtype=np.int32),
            uv=np.array(
                [
                    [mesh.uv_layers.active.data[i].uv[:] for i in t.loops]
                    for t in triangles
                ]
            ),
        )
        ev.to_mesh_clear()
        eyes = [
            scene.objects[f"Eye hair v1 | {actor} eye {side}"] for side in ("L", "R")
        ]
        rot = eyes[0].matrix_world.to_3x3().normalized()
        center = (
            eyes[0].matrix_world.translation + eyes[1].matrix_world.translation
        ) * 0.5
        axes = {
            name: rot @ Vector(value)
            for name, value in {
                "right": (1, 0, 0),
                "front": (0, -1, 0),
                "up": (0, 0, 1),
            }.items()
        }
        lamp = scene.objects[f"Eye hair v1 | {actor} directional head key"]
        direction = (lamp.matrix_world.translation - center).normalized()
        record = {
            "face": mat.name,
            "tree": tree_record(mat.node_tree),
            "tree_animation": animation(mat.node_tree),
            "armature": arm.name,
            "head_matrix_world": plain(arm.matrix_world @ arm.pose.bones["頭"].matrix),
            "eyes": [
                {
                    "name": eye.name,
                    "matrix": plain(eye.matrix_world),
                    "parent": plain(eye.parent),
                    "parent_type": eye.parent_type,
                    "parent_bone": eye.parent_bone,
                }
                for eye in eyes
            ],
            "basis": {name: list(value) for name, value in axes.items()},
            "center": list(center),
            "key": {
                "name": lamp.name,
                "location": list(lamp.matrix_world.translation),
                "direction": list(direction),
                "head_dot": {
                    name: value.dot(direction) for name, value in axes.items()
                },
                "energy": lamp.data.energy,
                "type": lamp.data.type,
            },
        }
        report["actors"][actor] = record
        pending = [
            n.node_tree
            for n in mat.node_tree.nodes
            if n.type == "GROUP" and n.node_tree
        ]
        while pending:
            tree = pending.pop()
            if tree.name in report["groups"]:
                continue
            report["groups"][tree.name] = tree_record(tree)
            pending.extend(
                n.node_tree for n in tree.nodes if n.type == "GROUP" and n.node_tree
            )
    report["evaluated_geometry"] = {
        key: {
            "shape": list(value.shape),
            "sum": float(value.sum()),
        }
        for key, value in evaluated(scene).items()
    }
    report["source_unchanged"] = sha(SOURCE) == SOURCE_SHA
    assert report["source_unchanged"]
    write(destination, report)
    print("DUET_SDF_CURRENT_AUDIT_COMPLETE", flush=True)


def head_basis(scene, actor, tree):
    eyes = [scene.objects[f"Eye hair v1 | {actor} eye {s}"] for s in ("L", "R")]
    center = (eyes[0].matrix_world.translation + eyes[1].matrix_world.translation) * 0.5
    root = bpy.data.objects.new(PREFIX + actor + " full head basis", None)
    scene.collection.objects.link(root)
    root.parent = eyes[0]
    root.hide_render = True
    root.empty_display_size = 0.015
    bpy.context.view_layer.update()
    root.matrix_world = (
        Matrix.Translation(center) @ eyes[0].matrix_world.to_3x3().normalized().to_4x4()
    )
    origin = world_position(tree, root, "head center world")
    axes = {}
    for name, co in (("front", (0, -1, 0)), ("right", (1, 0, 0)), ("up", (0, 0, 1))):
        endpoint = bpy.data.objects.new(PREFIX + actor + " axis " + name, None)
        scene.collection.objects.link(endpoint)
        endpoint.parent = root
        endpoint.location = co
        endpoint.hide_render = True
        endpoint.empty_display_size = 0.01
        point = world_position(tree, endpoint, name + " endpoint world")
        axes[name] = vector(
            tree,
            "NORMALIZE",
            vector(tree, "SUBTRACT", point, origin, name + " world delta"),
            (0, 0, 0),
            name + " unit axis",
        )
    key = scene.objects[f"Eye hair v1 | {actor} directional head key"]
    light = world_position(tree, key, "same actual head key world")
    direction = vector(
        tree,
        "NORMALIZE",
        vector(tree, "SUBTRACT", light, origin, "head towards actual key"),
        (0, 0, 0),
        "unit towards light",
    )
    f = vector(
        tree, "DOT_PRODUCT", axes["front"], direction, "full head forward dot key"
    )
    r = vector(tree, "DOT_PRODUCT", axes["right"], direction, "full head right dot key")
    h2 = scalar(
        tree,
        "ADD",
        scalar(tree, "MULTIPLY", f, f, "front square"),
        scalar(tree, "MULTIPLY", r, r, "right square"),
        "horizontal length squared",
    )
    length = scalar(tree, "SQRT", h2, 0, "horizontal length")
    safe = scalar(tree, "MAXIMUM", length, 0.0001, "safe horizontal denominator")
    fh = scalar(tree, "DIVIDE", f, safe, "head plane forward cosine")
    valid = scalar(tree, "GREATER_THAN", length, 0.03, "azimuth valid")
    # A near-vertical key has no defined horizontal azimuth: fade to front-lit.
    fh = scalar(
        tree,
        "ADD",
        1,
        scalar(
            tree,
            "MULTIPLY",
            scalar(tree, "SUBTRACT", fh, 1, "front cosine offset"),
            valid,
            "valid azimuth cosine",
        ),
        "vertical light front fallback",
    )
    threshold = scalar(
        tree,
        "SUBTRACT",
        0.5,
        scalar(tree, "MULTIPLY", fh, 0.5, "half front cosine"),
        "author style angular threshold",
    )
    negative_right = scalar(tree, "LESS_THAN", r, 0, "light on subject left")
    return threshold, negative_right


def own_ikhor_threshold(scene, out):
    """Original angular threshold atlas rasterized onto this character's own UV.

    R/G are subject-right/left light conventions; the final atlas is a threshold
    representation, not a recovered game map or a geometric distance field.
    """
    actor = "ikhor"
    obj = scene.objects[ACTORS[actor]["mesh"]]
    template = uv_template(obj, actor)
    ids, weights = template["indices"], template["weights"]
    valid = weights.sum(axis=2) > 0.5
    coords = np.array([v.co[:] for v in obj.data.vertices], np.float32)
    p = (coords[ids] * weights[..., None]).sum(axis=2)
    eyes = [
        scene.objects[f"Eye hair v1 | {actor} eye {s}"]["rest_eye_center"]
        for s in ("L", "R")
    ]
    eye = (np.asarray(eyes[0]) + np.asarray(eyes[1])) * 0.5
    used = coords[template["face_vertices"]]
    width = float(np.quantile(np.abs(used[:, 0] - eye[0]), 0.96))
    x = (p[..., 0] - eye[0]) / width
    z = p[..., 2] - eye[2]
    rgba = np.ones((*valid.shape, 4), np.float32)
    for channel, side in enumerate((1, -1)):
        # Broad cheek division plus a compact tapered nose lobe, all designed in
        # Ikhor's own rest-space dimensions; no Furina/Aksiniya pixels are read.
        cheek = np.clip(0.58 + 0.40 * x * side, 0.02, 0.98)
        nose_z = z + 0.0255
        nose_halfwidth = 0.0046 * np.clip(1 - nose_z / 0.020, 0.42, 1.35)
        nx = (p[..., 0] - eye[0] + side * 0.0025) / nose_halfwidth
        nz = nose_z / 0.0105
        nose = np.clip(0.075 + 0.22 * (nx * nx + nz * nz), 0.02, 1)
        value = np.minimum(cheek, nose)
        rgba[..., channel] = np.where(valid, value, 1)
    rgba[..., 2] = valid.astype(np.float32)
    image = bpy.data.images.new(
        PREFIX + "Ikhor original angular SDF atlas",
        width=valid.shape[1],
        height=valid.shape[0],
        alpha=True,
        float_buffer=True,
        is_data=True,
    )
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(out / "ikhor-original-face-threshold.exr")
    image.file_format = "OPEN_EXR"
    image.save()
    check = bpy.data.images.load(image.filepath_raw, check_existing=False)
    values = np.empty(rgba.size, np.float32)
    check.pixels.foreach_get(values)
    error = float(np.max(np.abs(values.reshape(rgba.shape) - rgba)))
    bpy.data.images.remove(check)
    assert error < 0.001, error
    image.pack()
    return image, {
        "size": list(valid.shape),
        "valid_texels": int(valid.sum()),
        "eye_rest": eye.tolist(),
        "face_halfwidth": width,
        "numeric_roundtrip_max": error,
        "channels": {
            "R": "key on subject right",
            "G": "key on subject left",
            "B": "own face UV validity",
        },
        "origin": "Original geometric-artistic angular threshold,own Ikhor rest mesh/UV only;not author-game data",
    }


def apply_faces(scene, out):
    own_image, atlas_report = own_ikhor_threshold(scene, out)
    records = {}
    for actor in ACTORS:
        tree = bpy.data.materials[FACE[actor]].node_tree
        assert not any(n.name.startswith(PREFIX) for n in tree.nodes)
        threshold, side = head_basis(scene, actor, tree)
        uv = new(tree, "ShaderNodeTexCoord", "face UV")
        image = new(tree, "ShaderNodeTexImage", "own character face threshold")
        image.interpolation = "Linear"
        image.extension = "EXTEND"
        if actor == "aksiniya":
            image.image = tree.nodes[
                "Genshin study | supplied model FaceLightmap"
            ].image
            mirrored = vector(
                tree,
                "ADD",
                vector(
                    tree, "MULTIPLY", uv.outputs["UV"], (-1, 1, 1), "mirror own UV X"
                ),
                (1, 0, 0),
                "mirror own UV around half",
            )
            selected = color(
                tree, uv.outputs["UV"], mirrored, side, "select own mirrored UV"
            )
            tree.links.new(selected, image.inputs["Vector"])
            split = new(tree, "ShaderNodeSeparateColor", "own threshold channels")
            tree.links.new(image.outputs["Color"], split.inputs[0])
            data = split.outputs["Red"]
        else:
            image.image = own_image
            tree.links.new(uv.outputs["UV"], image.inputs["Vector"])
            split = new(tree, "ShaderNodeSeparateColor", "own threshold channels")
            tree.links.new(image.outputs["Color"], split.inputs[0])
            data = scalar(
                tree,
                "ADD",
                split.outputs["Red"],
                scalar(
                    tree,
                    "MULTIPLY",
                    scalar(
                        tree,
                        "SUBTRACT",
                        split.outputs["Green"],
                        split.outputs["Red"],
                        "left minus right threshold",
                    ),
                    side,
                    "select lit side threshold delta",
                ),
                "own two side threshold",
            )
        low = scalar(tree, "SUBTRACT", threshold, 0.025, "SDF soft lower")
        high = scalar(tree, "ADD", threshold, 0.025, "SDF soft upper")
        sdf = remap(tree, data, low, high, 0, 1, "author style smooth SDF response")
        enabled = new(tree, "ShaderNodeValue", "SDF enabled")
        enabled.outputs[0].default_value = 1
        sdf = scalar(
            tree,
            "ADD",
            1,
            scalar(
                tree,
                "MULTIPLY",
                scalar(tree, "SUBTRACT", sdf, 1, "SDF offset from lit"),
                enabled.outputs[0],
                "SDF enable weight",
            ),
            "SDF lit factor",
        )
        hair = tree.nodes["Eye hair v1 | geometry derived hair shadow"].outputs["Color"]
        # One shadow palette after min: neither SDF nor genuine hair occlusion is
        # multiplied into an already shaded face a second time.
        combined = scalar(
            tree, "MINIMUM", sdf, hair, "SDF and independent 4290 bangs visibility"
        )
        dark = (0.74, 0.40, 0.39, 1) if actor == "aksiniya" else (0.68, 0.34, 0.30, 1)
        lit = (1.015, 1.005, 1.0, 1) if actor == "aksiniya" else (0.94, 0.92, 0.92, 1)
        palette = color(
            tree,
            dark,
            lit,
            combined,
            "one warm skin palette",
        )
        base = (
            tree.nodes["Face ink | Mouth crease"].outputs[0]
            if actor == "aksiniya"
            else tree.nodes["mmd_shader"].outputs["Color"]
        )
        fresh = color(
            tree, base, palette, 1, "retained MMD color times SDF palette", "MULTIPLY"
        )
        surface = tree.nodes[
            "Look v3 | NPR surface"
            if actor == "aksiniya"
            else "Ikhor character | controlled NPR surface"
        ]
        old = surface.inputs["Color"].links[0].from_socket
        switch = new(tree, "ShaderNodeValue", "new face pipeline enabled")
        switch.outputs[0].default_value = 1
        final = color(
            tree,
            old,
            fresh,
            switch.outputs[0],
            "original or new reversible face pipeline",
        )
        tree.links.new(final, surface.inputs["Color"])
        records[actor] = {
            "image": image.image.name,
            "colorspace": image.image.colorspace_settings.name,
            "key": f"Eye hair v1 | {actor} directional head key",
            "threshold": "0.5-0.5*head-plane-cosine",
            "soft_halfwidth": 0.025,
            "old_face_pipeline": [old.node.name, old.name],
            "new_sdf_enable": enabled.name,
            "original_alpha_and_surface_closures_retained": True,
            "newly_authored_map": actor == "ikhor",
            "skin_palette_scene_linear": {"shadow": dark, "lit": lit},
        }
    bpy.context.view_layer.update()
    return {"actors": records, "ikhor_atlas": atlas_report}


def prepare(iteration, preview):
    out = ROOT / iteration
    out.mkdir(parents=True, exist_ok=False)
    scene = open_source()
    baseline = source_contract(scene)
    coordinates = evaluated(scene)
    implementation = apply_faces(scene, out)
    driver_evidence = head_driver_evidence(scene)
    restore_camera(scene, baseline["camera"])
    checks = compare_contract(scene, baseline)
    after = evaluated(scene)
    differences = {
        key: float(np.max(np.abs(value - after[key])))
        for key, value in coordinates.items()
    }
    checks["five_pose_evaluated_coordinates"] = max(differences.values()) < 1e-7
    checks["source_unchanged"] = sha(SOURCE) == SOURCE_SHA
    new_drivers = [
        fc
        for actor in ACTORS
        for fc in bpy.data.materials[FACE[actor]].node_tree.animation_data.drivers
        if PREFIX in fc.data_path
    ]
    checks["new_transform_drivers_valid"] = bool(new_drivers) and all(
        fc.is_valid for fc in new_drivers
    )
    report = {
        "source": str(SOURCE),
        "source_sha256": SOURCE_SHA,
        "iteration": iteration,
        "preview": preview,
        "implementation": implementation,
        "checks": checks,
        "five_pose_coordinate_max_abs": differences,
        "new_valid_transform_driver_count": len(new_drivers),
        "five_pose_full_head_driver_evidence": driver_evidence,
        "baseline_camera": baseline["camera"],
        "renders": [],
        "scope": "Only4290 static,new character-specific face pipeline;no video,no physics,no eye see-through;author53 shader not appended",
    }
    write(out / "implementation.json", report)
    assert all(checks.values()), checks
    original_camera = scene.camera
    original_dof = original_camera.data.dof.use_dof
    scene.render.use_motion_blur = False
    original_camera.data.dof.use_dof = False
    size = (1280, 720) if preview else (1920, 1080)
    near = (640, 676) if preview else (850, 900)
    samples = 32 if preview else 64
    marker_cameras = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    for marker, _camera in marker_cameras:
        marker.camera = None
    for enabled in (True, False):
        tag = "sdf-on" if enabled else "sdf-off"
        for actor in ACTORS:
            bpy.data.materials[FACE[actor]].node_tree.nodes[
                PREFIX + "SDF enabled"
            ].outputs[0].default_value = int(enabled)
        for actor in ACTORS:
            cam = hero_camera(scene, actor)
            label = f"{tag}-{actor}-4290"
            render(scene, out, label, cam, near, samples)
            report["renders"].append(label + ".png")
        label = f"{tag}-duet-4290"
        render(scene, out, label, original_camera, size, samples)
        report["renders"].append(label + ".png")
    for actor in ACTORS:
        bpy.data.materials[FACE[actor]].node_tree.nodes[PREFIX + "SDF enabled"].outputs[
            0
        ].default_value = 1
    if not preview:
        with glare_off(scene) as controls:
            render(
                scene, out, "sdf-on-duet-glare-off-4290", original_camera, size, samples
            )
        report["glare_off_controls"] = controls
        report["renders"].append("sdf-on-duet-glare-off-4290.png")
    for marker, camera in marker_cameras:
        marker.camera = camera
    report["sdf_on_off_differences"] = {
        actor: png_difference(
            out / f"sdf-on-{actor}-4290.png", out / f"sdf-off-{actor}-4290.png"
        )
        for actor in (*ACTORS, "duet")
    }
    assert all(
        row["max_rgb"] > 0.01 for row in report["sdf_on_off_differences"].values()
    ), report["sdf_on_off_differences"]
    scene.camera = original_camera
    original_camera.data.dof.use_dof = original_dof
    restore_camera(scene, baseline["camera"])
    scene.render.resolution_x, scene.render.resolution_y = (1920, 1080)
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 64
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "16"
    scene.render.filepath = str(out / "sdf-on-duet-4290.png")
    report["checks_after_renders"] = compare_contract(scene, baseline)
    assert all(report["checks_after_renders"].values()), report["checks_after_renders"]
    project = out / "Franken_Duet_SDF_Still.blend"
    report["saved_face_graph_signatures"] = face_graph_signatures()
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report["project"] = str(project)
    report["project_sha256"] = sha(project)
    report["source_unchanged_after_render"] = sha(SOURCE) == SOURCE_SHA
    assert report["source_unchanged_after_render"]
    report["director_review"] = "pending actual image inspection"
    write(out / "implementation.json", report)
    print("DUET_SDF_STILLS_PREPARED", flush=True)


def repair_preview(iteration):
    out = ROOT / iteration
    report = json.loads((out / "implementation.json").read_text(encoding="utf-8"))
    project = Path(report["project"])
    assert report["preview"] and sha(project) == report["project_sha256"]
    assert "repaired_closeups" not in report
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(project), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    for marker in scene.timeline_markers:
        if marker.camera:
            marker.camera = None
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    report["rejected_closeups"] = {
        f"sdf-{state}-{actor}-4290.png": "Original camera marker overrode diagnostic camera during rendering;not a closeup"
        for state in ("on", "off")
        for actor in ACTORS
    }
    report["repaired_closeups"] = []
    for enabled in (True, False):
        tag = "sdf-on" if enabled else "sdf-off"
        for actor in ACTORS:
            bpy.data.materials[FACE[actor]].node_tree.nodes[
                PREFIX + "SDF enabled"
            ].outputs[0].default_value = int(enabled)
        for actor in ACTORS:
            cam = hero_camera(scene, actor)
            label = f"corrected-{tag}-{actor}-4290"
            assert not (out / (label + ".png")).exists()
            render(scene, out, label, cam, (640, 676), 32)
            report["repaired_closeups"].append(
                {
                    "file": label + ".png",
                    "camera": cam.name,
                    "matrix_world": plain(cam.matrix_world),
                }
            )
    report["corrected_sdf_differences"] = {
        actor: png_difference(
            out / f"corrected-sdf-on-{actor}-4290.png",
            out / f"corrected-sdf-off-{actor}-4290.png",
        )
        for actor in ACTORS
    }
    assert sha(project) == report["project_sha256"] and sha(SOURCE) == SOURCE_SHA
    write(out / "implementation.json", report)
    print("DUET_SDF_PREVIEW_CAMERAS_REPAIRED", flush=True)


def reopen(iteration):
    out = ROOT / iteration
    report = json.loads((out / "implementation.json").read_text(encoding="utf-8"))
    assert not report["preview"], "Final independent validation uses final resolution"
    result_path = out / "reopen-verification.json"
    assert not result_path.exists(), "Preserve prior independent result"
    project = Path(report["project"])
    assert sha(project) == report["project_sha256"]
    scene = open_source()
    baseline = source_contract(scene)
    coordinates = evaluated(scene)
    bpy.ops.wm.open_mainfile(filepath=str(project), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    checks = compare_contract(scene, baseline)
    after = evaluated(scene)
    differences = {
        key: float(np.max(np.abs(value - after[key])))
        for key, value in coordinates.items()
    }
    checks["five_pose_evaluated_coordinates"] = max(differences.values()) < 1e-7
    checks["1080p_64_samples"] = (
        scene.render.resolution_x,
        scene.render.resolution_y,
        scene.render.resolution_percentage,
        scene.eevee.taa_render_samples,
    ) == (1920, 1080, 100, 64)
    checks["SDF_and_pipeline_saved_enabled"] = all(
        abs(
            bpy.data.materials[FACE[actor]]
            .node_tree.nodes[PREFIX + label]
            .outputs[0]
            .default_value
            - 1
        )
        < 1e-7
        for actor in ACTORS
        for label in ("SDF enabled", "new face pipeline enabled")
    )
    checks["original_source_unchanged"] = sha(SOURCE) == SOURCE_SHA
    driver_evidence = head_driver_evidence(scene)
    checks["full_head_drivers"] = bool(driver_evidence)
    # The two face trees and newly-authored atlas must survive native saving.
    signature = face_graph_signatures()
    checks["saved_face_graphs"] = signature == report["saved_face_graph_signatures"]
    result = {
        "project_sha256": sha(project),
        "independent_process": True,
        "checks": checks,
        "five_pose_coordinate_max_abs": differences,
        "five_pose_full_head_driver_evidence": driver_evidence,
        "passed": False,
        "new_video": False,
        "new_physics": False,
    }
    write(result_path, result)
    assert all(checks.values()), checks
    scene.camera.data.dof.use_dof = False
    render(scene, out, "reopened-sdf-on-duet-4290", scene.camera, (1920, 1080), 64)
    difference = png_difference(
        out / "sdf-on-duet-4290.png", out / "reopened-sdf-on-duet-4290.png"
    )
    result["reopened_pixels"] = difference
    # Prior same-runtime same-scene repeated render evidence: max~0.00318,
    # mean~0.0000321. Keep a small bounded allowance,report actual values,and stop
    # if the new graph produces a material mismatch; this is not art acceptance.
    checks["bounded_render_variance"] = (
        difference["max_rgb"] < 0.005 and difference["mean_rgb"] < 0.0001
    )
    checks["saved_project_unchanged_after_render"] = (
        sha(project) == report["project_sha256"]
    )
    result["passed"] = all(checks.values())
    write(result_path, result)
    assert result["passed"], result
    print("DUET_SDF_INDEPENDENT_REOPEN_PASSED", flush=True)


def source_dof_beauty(iteration):
    """Add formal source-DOF images; retain earlier diagnostic artifacts intact."""
    out = ROOT / iteration
    old = json.loads((out / "implementation.json").read_text(encoding="utf-8"))
    assert not old["preview"] and sha(Path(old["project"])) == old["project_sha256"]
    destination = out / "beauty-finalization.json"
    assert not destination.exists()
    scene = open_source()
    baseline = source_contract(scene)
    coordinates = evaluated(scene)
    bpy.ops.wm.open_mainfile(filepath=old["project"], load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    checks = compare_contract(scene, baseline)
    assert all(checks.values()), checks
    assert camera_record(scene)["dof"] == baseline["camera"]["dof"]
    renders = []
    for enabled in (True, False):
        for actor in ACTORS:
            bpy.data.materials[FACE[actor]].node_tree.nodes[
                PREFIX + "SDF enabled"
            ].outputs[0].default_value = int(enabled)
        label = f"beauty-sdf-{'on' if enabled else 'off'}-duet-4290"
        assert not (out / (label + ".png")).exists()
        render(scene, out, label, scene.camera, (1920, 1080), 64)
        renders.append(
            {
                "file": label + ".png",
                "camera": camera_record(scene),
                "sha256": sha(out / (label + ".png")),
            }
        )
    for actor in ACTORS:
        bpy.data.materials[FACE[actor]].node_tree.nodes[PREFIX + "SDF enabled"].outputs[
            0
        ].default_value = 1
    after = evaluated(scene)
    differences = {
        key: float(np.max(np.abs(value - after[key])))
        for key, value in coordinates.items()
    }
    checks = compare_contract(scene, baseline)
    checks["five_pose_evaluated_coordinates"] = max(differences.values()) < 1e-7
    driver_evidence = head_driver_evidence(scene)
    checks["30_valid_head_drivers"] = all(
        row["drivers"] == 15 for row in driver_evidence.values()
    )
    checks["prior_snapshot_unchanged"] = (
        sha(Path(old["project"])) == old["project_sha256"]
    )
    checks["original_source_unchanged"] = sha(SOURCE) == SOURCE_SHA
    assert all(checks.values()), checks
    project = out / "Franken_Duet_SDF_SourceDOF_Still.blend"
    assert not project.exists()
    scene.render.filepath = str(out / "beauty-sdf-on-duet-4290.png")
    record = {
        "status": "formal-source-dof-stills-prepared-awaiting-reopen-and-review",
        "prior_diagnostic_snapshot": {
            "project": old["project"],
            "sha256": old["project_sha256"],
            "report": "implementation.json",
            "reopen": "reopen-verification.json",
        },
        "diagnostic_render_dof": False,
        "formal_render_dof": baseline["camera"]["dof"],
        "source": str(SOURCE),
        "source_sha256": SOURCE_SHA,
        "checks": checks,
        "five_pose_coordinate_max_abs": differences,
        "five_pose_full_head_driver_evidence": driver_evidence,
        "renders": renders,
        "saved_face_graph_signatures": face_graph_signatures(),
        "sdf_on_off_difference": png_difference(
            out / "beauty-sdf-on-duet-4290.png", out / "beauty-sdf-off-duet-4290.png"
        ),
        "project": str(project),
        "saved_render_filepath": scene.render.filepath,
        "saved_camera": camera_record(scene),
    }
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    record["project_sha256"] = sha(project)
    write(destination, record)
    print("DUET_SDF_SOURCE_DOF_BEAUTY_PREPARED", flush=True)


def beauty_reopen(iteration):
    out = ROOT / iteration
    report = json.loads((out / "beauty-finalization.json").read_text(encoding="utf-8"))
    project = Path(report["project"])
    assert sha(project) == report["project_sha256"]
    result_path = out / "beauty-reopen-verification.json"
    assert not result_path.exists()
    scene = open_source()
    baseline = source_contract(scene)
    coordinates = evaluated(scene)
    bpy.ops.wm.open_mainfile(filepath=str(project), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    checks = compare_contract(scene, baseline)
    after = evaluated(scene)
    differences = {
        key: float(np.max(np.abs(value - after[key])))
        for key, value in coordinates.items()
    }
    checks["five_pose_evaluated_coordinates"] = max(differences.values()) < 1e-7
    drivers = head_driver_evidence(scene)
    checks["head_driver_contract"] = all(
        row["drivers"] == 15 for row in drivers.values()
    )
    checks["face_graphs"] = (
        face_graph_signatures() == report["saved_face_graph_signatures"]
    )
    checks["default_filepath_formal_beauty"] = (
        scene.render.filepath == report["saved_render_filepath"]
    )
    checks["formal_camera_full_dof"] = camera_record(scene) == report["saved_camera"]
    checks["SDF_and_pipeline_on"] = all(
        abs(
            bpy.data.materials[FACE[a]]
            .node_tree.nodes[PREFIX + n]
            .outputs[0]
            .default_value
            - 1
        )
        < 1e-7
        for a in ACTORS
        for n in ("SDF enabled", "new face pipeline enabled")
    )
    checks["1080p_64samples"] = (
        scene.render.resolution_x,
        scene.render.resolution_y,
        scene.render.resolution_percentage,
        scene.eevee.taa_render_samples,
    ) == (1920, 1080, 100, 64)
    record = {
        "independent_process": True,
        "project_sha256": sha(project),
        "checks": checks,
        "camera_before_actual_render": camera_record(scene),
        "five_pose_coordinate_max_abs": differences,
        "head_driver_evidence": drivers,
        "passed": False,
    }
    write(result_path, record)
    assert all(checks.values()), checks
    render(
        scene, out, "reopened-beauty-sdf-on-duet-4290", scene.camera, (1920, 1080), 64
    )
    diff = png_difference(
        out / "beauty-sdf-on-duet-4290.png",
        out / "reopened-beauty-sdf-on-duet-4290.png",
    )
    record["reopened_pixels"] = diff
    checks["bounded_render_variance"] = (
        diff["max_rgb"] < 0.005 and diff["mean_rgb"] < 0.0001
    )
    checks["formal_project_unchanged_after_render"] = (
        sha(project) == report["project_sha256"]
    )
    checks["source_unchanged"] = sha(SOURCE) == SOURCE_SHA
    record["passed"] = all(checks.values())
    write(result_path, record)
    assert record["passed"], record
    print("DUET_SDF_SOURCE_DOF_REOPEN_PASSED", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=(
            "audit",
            "prepare",
            "reopen",
            "repair-preview",
            "source-dof-beauty",
            "beauty-reopen",
        ),
        required=True,
    )
    parser.add_argument("--iteration", default="trial-v1")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.mode == "audit":
        audit()
    elif args.mode == "prepare":
        assert (
            args.iteration.startswith(("trial-", "final-"))
            and "/" not in args.iteration
            and "\\" not in args.iteration
        )
        prepare(args.iteration, args.preview)
    elif args.mode == "reopen":
        reopen(args.iteration)
    elif args.mode == "repair-preview":
        repair_preview(args.iteration)
    elif args.mode == "source-dof-beauty":
        source_dof_beauty(args.iteration)
    elif args.mode == "beauty-reopen":
        beauty_reopen(args.iteration)


if __name__ == "__main__":
    main()
