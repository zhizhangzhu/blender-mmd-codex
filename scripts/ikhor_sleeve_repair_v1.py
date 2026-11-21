"""Diagnose and isolate Ikhor's sleeve bake without rebuilding the entire rig.

Run only in an independent background Blender process. The audit compares the
unbuilt 30fps native baseline with the fixed 60fps portable actor. Candidate
ablations alter sleeve-only channels in a new file. Local-rebake explicitly
builds only the eight sleeve bodies and local references/contacts; it never
rebuilds the full actor or renders. Diagnostics are not penetration approvals.
"""

import argparse
import hashlib
import importlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_ikhor_motion import digest, plain, repair_self_inheritance, set_frame
from verify_ikhor_wedding import action_signature

PROFILE = (
    Path(__file__).resolve().parents[1] / "presets/quality/ikhor-sleeve-repair-v1.json"
)


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def flat(matrix):
    return [value for row in matrix for value in row]


def matrix(values):
    return Matrix([values[i : i + 4] for i in range(0, 16, 4)])


def curves(action):
    if hasattr(action, "fcurves"):
        yield action.fcurves
    for layer in getattr(action, "layers", ()):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                yield bag.fcurves


def pose_record(arm, name):
    bone = arm.pose.bones[name]
    location, rotation, scale = bone.matrix_basis.decompose()
    return {
        "basis": flat(bone.matrix_basis),
        "matrix": flat(bone.matrix),
        "world_head": list(arm.matrix_world @ bone.head),
        "world_tail": list(arm.matrix_world @ bone.tail),
        "basis_translation": list(location),
        "basis_rotation_degrees": math.degrees(rotation.angle),
        "basis_scale": list(scale),
    }


def body_controls(arm):
    names = {
        "左腕",
        "左ひじ",
        "左手首",
        "右腕",
        "右ひじ",
        "右手首",
        "左手捩",
        "右手捩",
        "左腕捩",
        "右腕捩",
    }
    return [
        b.name
        for b in arm.pose.bones
        if b.mmd_bone.name_j in names
        or b.name.startswith(("Bone_ForearmTwistA01_", "Bone_SleeveMain01_"))
    ]


def sample(arm, names):
    return {name: pose_record(arm, name) for name in names}


def capture_native(spec, model):
    bpy.ops.wm.open_mainfile(filepath=spec["native"])
    scene = bpy.context.scene
    if scene.rigidbody_world:
        scene.rigidbody_world.enabled = False
    arm = bpy.data.objects[spec["armature"]]
    assert not arm.parent.mmd_root.is_built
    repairs = repair_self_inheritance(arm, model)
    controls, result = body_controls(arm), {}
    for frame in range(spec["guard_frames"][0], spec["guard_frames"][1] + 1):
        native_frame = 330 + (frame - 1) / 2
        set_frame(scene, native_frame)
        result[str(frame)] = {
            "sleeves": sample(arm, spec["sleeve_bones"]),
            "controls": sample(arm, controls),
        }
    return result, repairs


def audit(spec, output):
    assert digest(Path(spec["pmx"])) == spec["pmx_sha256"]
    assert digest(Path(spec["portable"])) == spec["portable_sha256"]
    pmx = importlib.import_module("bl_ext.blender_org.mmd_tools.core.pmx")
    model = pmx.load(spec["pmx"])
    selected = {i for i, b in enumerate(model.bones) if "Sleeve" in b.name}
    relevant = selected | {model.bones[i].parent for i in selected}
    rigid_ids = {i for i, r in enumerate(model.rigids) if r.bone in relevant}
    joint_ids = {
        i
        for i, j in enumerate(model.joints)
        if j.src_rigid in rigid_ids or j.dest_rigid in rigid_ids
    }
    rigid_ids |= {
        index
        for i in joint_ids
        for index in (model.joints[i].src_rigid, model.joints[i].dest_rigid)
    }
    raw = {
        "bones": [
            {
                "index": i,
                "parent_name": model.bones[b.parent].name if b.parent >= 0 else None,
                "record": plain(b),
            }
            for i, b in enumerate(model.bones)
            if i in relevant
        ],
        "rigids": [
            {
                "index": i,
                "bone_name": model.bones[r.bone].name if r.bone >= 0 else None,
                "record": plain(r),
            }
            for i, r in enumerate(model.rigids)
            if i in rigid_ids
        ],
        "joints": [
            {"index": i, "record": plain(j)}
            for i, j in enumerate(model.joints)
            if i in joint_ids
        ],
    }
    print("SLEEVE_AUDIT_NATIVE_BEGIN", flush=True)
    native, repairs = capture_native(spec, model)
    write(output / "native-sleeve-303.json", native)
    bpy.ops.wm.open_mainfile(filepath=spec["portable"])
    scene, arm = bpy.context.scene, bpy.data.objects[spec["armature"]]
    assert scene.rigidbody_world is None
    controls = body_controls(arm)
    set_frame(scene, spec["focus_frame"])
    before = sample(arm, spec["sleeve_bones"])
    focus_native = native[str(spec["focus_frame"])]
    deltas = {}
    for name in spec["sleeve_bones"]:
        source, current = focus_native["sleeves"][name], before[name]
        q = (
            matrix(source["basis"])
            .to_quaternion()
            .rotation_difference(matrix(current["basis"]).to_quaternion())
        )
        deltas[name] = {
            "world_head_difference": math.dist(
                source["world_head"], current["world_head"]
            ),
            "basis_translation_difference": math.dist(
                source["basis_translation"], current["basis_translation"]
            ),
            "basis_rotation_difference_degrees": math.degrees(q.angle),
        }
    control_errors = {
        name: max(
            abs(a - b)
            for a, b in zip(
                focus_native["controls"][name]["matrix"],
                pose_record(arm, name)["matrix"],
            )
        )
        for name in controls
    }
    report = {
        "id": spec["id"],
        "source_pmx_sha256": spec["pmx_sha256"],
        "native_sha256": digest(Path(spec["native"])),
        "portable_sha256": spec["portable_sha256"],
        "source_records": raw,
        "native_self_inheritance_fix_only": repairs,
        "focus_output_frame": spec["focus_frame"],
        "focus_native_blender30": 330 + (spec["focus_frame"] - 1) / 2,
        "focus_source_vmd": 329 + (spec["focus_frame"] - 1) / 2,
        "native_sleeves": focus_native["sleeves"],
        "portable_sleeves": before,
        "dynamic_deviation": deltas,
        "native_vs_portable_control_matrix_errors": control_errors,
        "portable_body_action": action_signature(arm.animation_data.action),
        "raw_hierarchy": [
            {
                "name": name,
                "parent": arm.pose.bones[name].parent.name,
                "rotation_mode": arm.pose.bones[name].rotation_mode,
            }
            for name in spec["sleeve_bones"]
        ],
        "native_capture_frames": spec["guard_frames"],
        "native_capture_count": len(native),
        "rendered": False,
        "physics_built_or_simulated": False,
        "sleeve_penetration_resolved": False,
        "visual_status": "pending",
    }
    write(output / "sleeve-diagnosis.json", report)
    print(
        "SLEEVE_AUDIT_DONE",
        json.dumps(
            {
                "report": str(output / "sleeve-diagnosis.json"),
                "focus_native_frame": report["focus_native_blender30"],
                "dynamic_deviation": deltas,
                "body_control_errors": control_errors,
            },
            ensure_ascii=True,
        ),
        flush=True,
    )


def candidate(spec, output, mode):
    reference = (
        "fitted-repair-303.json"
        if mode == "fitted_repair"
        else "local-rebake-303.json"
        if mode == "local_rebake"
        else "native-sleeve-303.json"
    )
    native = json.loads((output / reference).read_text(encoding="utf-8"))
    assert digest(Path(spec["portable"])) == spec["portable_sha256"]
    bpy.ops.wm.open_mainfile(filepath=spec["portable"])
    scene, arm = bpy.context.scene, bpy.data.objects[spec["armature"]]
    assert scene.rigidbody_world is None
    selected = (
        spec["near_bones"]
        if mode == "proximal_native"
        else spec["sleeve_bones"]
        if mode in {"native_sleeves", "local_rebake", "fitted_repair"}
        else spec["weighted_sleeve_bones"]
    )
    before = {}
    other_names = [b.name for b in arm.pose.bones if b.name not in spec["sleeve_bones"]]
    expected_other, desired = {}, {}
    for frame, values in native.items():
        set_frame(scene, int(frame))
        expected_other[frame] = {
            name: flat(arm.pose.bones[name].matrix) for name in other_names
        }
        desired[frame] = {}
        for name in selected:
            original = arm.pose.bones[name].matrix_basis.copy()
            before.setdefault(name, []).append(flat(original))
            target = matrix(values["sleeves"][name]["basis"])
            if mode == "translations_only":
                original.translation = target.translation
                target = original
            desired[frame][name] = flat(target)
    action = arm.animation_data.action.copy()
    action.name = "Ikhor | sleeve diagnostic | " + mode
    arm.animation_data.action = action
    for collection in curves(action):
        for curve in list(collection):
            for name in selected:
                prefix = arm.pose.bones[name].path_from_id()
                paths = (
                    {prefix + ".location"}
                    if mode == "translations_only"
                    else {
                        prefix + ".location",
                        prefix + ".rotation_quaternion",
                        prefix + ".rotation_euler",
                        prefix + ".rotation_axis_angle",
                    }
                )
                if curve.data_path in paths:
                    collection.remove(curve)
                    break
    for frame, values in desired.items():
        set_frame(scene, int(frame))
        for name, value in values.items():
            bone = arm.pose.bones[name]
            bone.matrix_basis = matrix(value)
            bone.keyframe_insert(
                "location", frame=int(frame), group="Ikhor sleeve diagnostic"
            )
            if mode != "translations_only":
                rotation = (
                    "rotation_quaternion"
                    if bone.rotation_mode == "QUATERNION"
                    else "rotation_axis_angle"
                    if bone.rotation_mode == "AXIS_ANGLE"
                    else "rotation_euler"
                )
                bone.keyframe_insert(
                    rotation, frame=int(frame), group="Ikhor sleeve diagnostic"
                )
    selected_paths = {arm.pose.bones[name].path_from_id() for name in selected}
    for collection in curves(action):
        for curve in collection:
            if any(
                curve.data_path.startswith(prefix + ".") for prefix in selected_paths
            ) and (
                mode != "translations_only" or curve.data_path.endswith(".location")
            ):
                for key in curve.keyframe_points:
                    key.interpolation = "LINEAR"
    maximum_other_error = 0
    for frame, bones in expected_other.items():
        set_frame(scene, int(frame))
        for name, expected in bones.items():
            maximum_other_error = max(
                maximum_other_error,
                max(
                    abs(a - b)
                    for a, b in zip(expected, flat(arm.pose.bones[name].matrix))
                ),
            )
    assert maximum_other_error < 0.00001, maximum_other_error
    scene["ikhor_sleeve_diagnostic"] = mode
    scene["sleeve_repair_visual_status"] = "unaccepted diagnostic"
    set_frame(scene, spec["focus_frame"])
    target = output / ("Ikhor_Sleeve_Diagnostic_" + mode + ".blend")
    assert not target.exists()
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    report = {
        "mode": mode,
        "project": str(target),
        "project_sha256": digest(target),
        "changed_bones": selected,
        "allowed_affected_descendants": spec["sleeve_bones"],
        "range": spec["guard_frames"],
        "other_bone_matrix_maximum_error_all_303_frames": maximum_other_error,
        "body_motion_preserved": True,
        "materials_geometry_weights_changed": False,
        "rendered": False,
        "physics_built_or_simulated": mode in {"local_rebake", "fitted_repair"},
        "candidate_overlay_phase_simulated": False,
        "physics_report": str(
            Path(spec.get("physics_dir", output)) / "local-physics-report.json"
        )
        if mode in {"local_rebake", "fitted_repair"}
        else None,
        "rig_correction_after_physics": mode == "fitted_repair",
        "sleeve_penetration_resolved": False,
        "visual_status": "pending diagnostic only",
    }
    write(output / ("diagnostic-" + mode + ".json"), report)
    print("SLEEVE_DIAGNOSTIC_READY", json.dumps(report, ensure_ascii=True), flush=True)


def local_rebake(spec, output):
    """Solve eight sleeve bodies, with forearm references and skin contact hulls."""
    from bl_ext.blender_org.mmd_tools.core.model import Model
    from bl_ext.blender_org.mmd_tools.core.rigid_body import FnRigidBody
    from bpy_extras.anim_utils import BakeOptions, bake_action_objects_iter
    from mmd_final_scene import retime_actions

    report_path = output / "local-physics-report.json"
    assert not report_path.exists() and not (output / "local-rebake-303.json").exists()
    assert digest(Path(spec["pmx"])) == spec["pmx_sha256"]
    raw = importlib.import_module("bl_ext.blender_org.mmd_tools.core.pmx").load(
        spec["pmx"]
    )
    settings = spec["local_solver"]
    bpy.ops.wm.open_mainfile(filepath=spec["native"])
    scene, arm = bpy.context.scene, bpy.data.objects[spec["armature"]]
    root = arm.parent
    assert not root.mmd_root.is_built
    world = scene.rigidbody_world
    world.enabled = False
    repair = repair_self_inheritance(arm, raw)
    model = Model(root)
    body_group = model.rigidGroupObject()
    keep = {f"{index:03d}_" for index in settings["keep_rigid_indices"]}
    originals = {
        obj for obj in scene.objects if getattr(obj, "mmd_type", "") == "RIGID_BODY"
    }
    retained = {
        obj for obj in originals if any(obj.name.startswith(prefix) for prefix in keep)
    }
    assert len(retained) == 10
    original_joints = {
        obj for obj in scene.objects if getattr(obj, "mmd_type", "") == "JOINT"
    }
    joints = {
        obj
        for obj in original_joints
        if obj.rigid_body_constraint
        and obj.rigid_body_constraint.object1 in retained
        and obj.rigid_body_constraint.object2 in retained
        and "補" not in obj.mmd_joint.name_j
    }
    assert len(joints) == 8
    # Bullet constraint references must die before the bodies they reference.
    bpy.data.batch_remove(ids=original_joints - joints)
    bpy.data.batch_remove(ids=originals - retained)
    changes = []
    for name, bone in settings["anchor_bones"].items():
        obj = bpy.data.objects[name]
        changes.append(
            {"anchor": name, "source_bone": obj.mmd_rigid.bone, "new_bone": bone}
        )
        obj.mmd_rigid.bone = bone
    joint_limits = []
    for obj in joints:
        name = obj.mmd_joint.name_j
        if "錘" in name:
            continue
        constraint = obj.rigid_body_constraint
        degrees = (
            settings["near_angle_degrees"]
            if "Sleeve01" in name
            else settings["far_angle_degrees"]
        )
        old = {
            axis: [
                getattr(constraint, "limit_ang_" + axis + "_lower"),
                getattr(constraint, "limit_ang_" + axis + "_upper"),
            ]
            for axis in "xyz"
        }
        for axis in "xyz":
            setattr(constraint, "limit_ang_" + axis + "_lower", -math.radians(degrees))
            setattr(constraint, "limit_ang_" + axis + "_upper", math.radians(degrees))
        joint_limits.append(
            {"joint": name, "source_limits_radians": old, "new_limit_degrees": degrees}
        )
    mesh = next(
        obj
        for obj in scene.objects
        if obj.type == "MESH"
        and any(mod.type == "ARMATURE" and mod.object == arm for mod in obj.modifiers)
    )
    skin_materials = {
        i
        for i, material in enumerate(mesh.data.materials)
        if material
        and material.get("source_mmd_material_name", material.name)
        == settings["skin_material"]
    }
    skin_ids = {
        index
        for polygon in mesh.data.polygons
        if polygon.material_index in skin_materials
        for index in polygon.vertices
    }
    assert skin_ids
    transform = arm.matrix_world.inverted() @ mesh.matrix_world
    by_j = {bone.mmd_bone.name_j: bone for bone in arm.pose.bones}
    contacts, hulls = [], {}
    for side, japanese in (("L", "左"), ("R", "右")):
        wrist, elbow = by_j[japanese + "手首"], by_j[japanese + "ひじ"]
        origin = wrist.bone.head_local.copy()
        axis = (origin - elbow.bone.head_local).normalized()
        arm_length = (origin - elbow.bone.head_local).length
        wrist_group = mesh.vertex_groups[wrist.name].index
        for label, bone_name, low, high in (
            ("palm", wrist.name, *settings["palm_axial_range"]),
            (
                "forearm",
                "Bone_ForearmTwistA01_" + side,
                -arm_length + settings["forearm_inset_elbow"],
                -settings["forearm_inset_wrist"],
            ),
        ):
            selected_points, indices = [], []
            for index in sorted(skin_ids):
                vertex = mesh.data.vertices[index]
                point = transform @ vertex.co
                delta = point - origin
                axial = delta.dot(axis)
                radius = (delta - axis * axial).length
                weight = next(
                    (g.weight for g in vertex.groups if g.group == wrist_group), 0
                )
                if not (
                    point.x * origin.x > 0 and low <= axial <= high and radius < 0.050
                ):
                    continue
                if label == "palm" and weight < settings["palm_min_wrist_weight"]:
                    continue
                selected_points.append(point)
                indices.append(index)
            assert len(selected_points) >= 12, (side, label, len(selected_points))
            center = sum(selected_points, Vector()) / len(selected_points)
            points = [
                (point - center) * settings["contact_shrink"]
                for point in selected_points
            ]
            half = Vector(
                tuple(max(abs(point[i]) for point in points) for i in range(3))
            )
            obj = FnRigidBody.new_rigid_body_object(bpy.context, body_group)
            obj.name = "Sleeve repair | " + side + " | " + label + " skin contact"
            obj.mmd_rigid.name_j = obj.name
            obj.mmd_rigid.bone = bone_name
            obj.mmd_rigid.shape = "BOX"
            obj.mmd_rigid.size = half
            obj.mmd_rigid.type = "0"
            obj.mmd_rigid.collision_group_number = settings["collision_group"]
            mask = [True] * 16
            mask[4] = False
            obj.mmd_rigid.collision_group_mask = mask
            obj.location = center
            obj["performer_id"] = "ikhor"
            obj.rigid_body.friction = 0.15
            hulls[obj.name] = [list(point) for point in points]
            contacts.append(
                {
                    "name": obj.name,
                    "bone": bone_name,
                    "source_vertices": indices,
                    "axial_range": [low, high],
                    "rest_center": list(center),
                    "point_count": len(points),
                    "rest_half_extents": list(half),
                    "shrink": settings["contact_shrink"],
                    "group": settings["collision_group"],
                    "ignore_sleeve_group_4": False,
                }
            )
            retained.add(obj)
    for obj in retained:
        if obj.name not in world.collection.objects:
            world.collection.objects.link(obj)
        if obj.mmd_rigid.bone in spec["weighted_sleeve_bones"]:
            obj.mmd_rigid.type = settings["weighted_sleeve_binding_mode"]
            mask = list(obj.mmd_rigid.collision_group_mask)
            mask[settings["collision_group"]] = False
            obj.mmd_rigid.collision_group_mask = mask
    for obj in joints:
        if obj.name not in world.constraints.objects:
            world.constraints.objects.link(obj)
    sim_first, sim_last = settings["simulation_source_frames"]
    export_first, export_last = settings["export_source_frames"]
    scene.frame_start, scene.frame_end = sim_first, sim_last
    set_frame(scene, sim_first)
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    started = time.perf_counter()
    assert bpy.ops.mmd_tools.build_rig() == {"FINISHED"}
    world = scene.rigidbody_world
    world.enabled = True
    world.substeps_per_frame = settings["substeps"]
    world.solver_iterations = settings["iterations"]
    world.time_scale = 1
    bodies = [obj for obj in world.collection.all_objects if obj.rigid_body]
    dynamic = [obj for obj in bodies if not obj.rigid_body.kinematic]
    kinematic_counts = dict(Counter(str(obj.rigid_body.kinematic) for obj in bodies))
    physical = [
        bone.name
        for bone in arm.pose.bones
        if bone.constraints.get("mmd_tools_rigid_track")
    ]
    binding_modes = {
        obj.mmd_rigid.bone: obj.mmd_rigid.type
        for obj in bodies
        if obj.mmd_rigid.bone in spec["sleeve_bones"]
    }
    assert (
        len(bodies) == 14
        and len(dynamic) == 8
        and set(physical) == set(spec["sleeve_bones"])
    )
    for name, points in hulls.items():
        obj = bpy.data.objects[name]
        data = bpy.data.meshes.new(name + " | convex skin vertices")
        data.from_pydata(points, [], [])
        data.update()
        obj.data = data
        obj.rigid_body.collision_shape = "CONVEX_HULL"
    for obj in bodies:
        obj.rigid_body.use_margin = True
        obj.rigid_body.collision_margin = settings["margin"]
    disabled_contacts = []
    contact_names = set(hulls)
    main_names = {
        obj.name
        for obj in bodies
        if obj.mmd_rigid.bone in spec["weighted_sleeve_bones"]
    }
    for obj in world.constraints.all_objects:
        constraint = obj.rigid_body_constraint
        if (
            not constraint
            or not constraint.disable_collisions
            or not constraint.object1
            or not constraint.object2
        ):
            continue
        pair = {constraint.object1.name, constraint.object2.name}
        if pair & contact_names and pair & main_names:
            disabled_contacts.append(sorted(pair))
    assert not disabled_contacts, disabled_contacts
    cache = world.point_cache
    cache.frame_start, cache.frame_end = sim_first, sim_last
    print(
        "LOCAL_SLEEVE_SIMULATION_START",
        len(bodies),
        len(dynamic),
        len(world.constraints.all_objects),
        flush=True,
    )
    with bpy.context.temp_override(point_cache=cache):
        assert bpy.ops.ptcache.bake(bake=True) == {"FINISHED"}
    assert cache.is_baked
    simulation_seconds = time.perf_counter() - started
    expected = {}
    for frame in [export_first, 2420, 2474, 2475, 2500, export_last]:
        set_frame(scene, frame)
        expected[frame] = {name: flat(arm.pose.bones[name].matrix) for name in physical}
    action = arm.animation_data.action.copy()
    action.name = "Ikhor | local eight sleeve physics 30fps"
    action.use_fake_user = True
    for bone in arm.pose.bones:
        bone.select = bone.name in physical
    options = BakeOptions(
        only_selected=True,
        do_pose=True,
        do_object=False,
        do_visual_keying=True,
        do_constraint_clear=False,
        do_parents_clear=False,
        do_clean=False,
        do_location=True,
        do_rotation=True,
        do_scale=False,
        do_bbone=False,
        do_custom_props=False,
    )
    iterator = bake_action_objects_iter([(arm, action)], bake_options=options)
    iterator.send(None)
    for frame in range(export_first, export_last + 1):
        iterator.send(frame)
    iterator.send(None)
    temporary = Path(spec["temp_dir"])
    temporary.mkdir(parents=True, exist_ok=True)
    checkpoint = temporary / "local-sleeve-visual-30fps.blend"
    assert not checkpoint.exists()
    bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
    for name in physical:
        bone = arm.pose.bones[name]
        bone.constraints.remove(bone.constraints["mmd_tools_rigid_track"])
    world.enabled = False
    constraint_objects = {obj for obj in bpy.data.objects if obj.rigid_body_constraint}
    body_objects = {obj for obj in bpy.data.objects if obj.rigid_body}
    bpy.data.batch_remove(ids=constraint_objects)
    bpy.ops.rigidbody.world_remove()
    bpy.data.batch_remove(ids=body_objects)
    root.mmd_root.is_built = False
    maximum_export_error = 0
    for frame, bones in expected.items():
        set_frame(scene, frame)
        for name, values in bones.items():
            maximum_export_error = max(
                maximum_export_error,
                max(
                    abs(a - b)
                    for a, b in zip(values, flat(arm.pose.bones[name].matrix))
                ),
            )
    assert maximum_export_error < 0.0001, maximum_export_error
    retime_actions(330, 2)
    scene.render.fps = 60
    baked = {}
    for frame in range(spec["guard_frames"][0], spec["guard_frames"][1] + 1):
        set_frame(scene, frame)
        baked[str(frame)] = {"sleeves": sample(arm, spec["sleeve_bones"])}
    write(output / "local-rebake-303.json", baked)
    report = {
        "id": spec["id"],
        "source_pmx_sha256": spec["pmx_sha256"],
        "native_sha256": digest(Path(spec["native"])),
        "native_self_inheritance_fix_only": repair,
        "participating_bodies": len(bodies),
        "dynamic_bodies": len(dynamic),
        "kinematic_counts": kinematic_counts,
        "physical_bones": physical,
        "sleeve_bone_binding_modes": binding_modes,
        "anchors": changes,
        "contacts": contacts,
        "contact_scope": settings["contact_scope"],
        "joint_limits": joint_limits,
        "removed_cross_side_auxiliary_joints": True,
        "contact_pairs_disabled": disabled_contacts,
        "simulation_source_frames": [sim_first, sim_last],
        "export_source_frames": [export_first, export_last],
        "preroll_source_frames": export_first - sim_first,
        "substeps": settings["substeps"],
        "iterations": settings["iterations"],
        "effective_local_solver_parameters": settings,
        "simulation_and_build_seconds": simulation_seconds,
        "maximum_simulation_vs_export_matrix_error": maximum_export_error,
        "timebase": spec["native_frame_formula"],
        "visual_checkpoint": str(checkpoint),
        "runtime_physics_removed_after_export": scene.rigidbody_world is None,
        "full_514_body_build_performed": False,
        "full_song_physics_validated": False,
        "rendered": False,
        "visual_status": "pending both cuffs, hands and chest over all 300 output frames",
    }
    write(report_path, report)
    print(
        "LOCAL_SLEEVE_PHYSICS_DONE",
        json.dumps(
            {
                "report": str(report_path),
                "bodies": len(bodies),
                "dynamic": len(dynamic),
                "export_error": maximum_export_error,
            },
            ensure_ascii=True,
        ),
        flush=True,
    )


def rest_frame_audit(spec, output):
    raw = importlib.import_module("bl_ext.blender_org.mmd_tools.core.pmx").load(
        spec["pmx"]
    )
    bpy.ops.wm.open_mainfile(filepath=spec["native"])
    scene, arm = bpy.context.scene, bpy.data.objects[spec["armature"]]
    scene.rigidbody_world.enabled = False
    repair_self_inheritance(arm, raw)
    frame = spec["local_solver"]["simulation_source_frames"][0]
    set_frame(scene, frame)
    expected, maps = {}, {}
    for obj in scene.objects:
        if (
            getattr(obj, "mmd_type", "") != "JOINT"
            or obj.mmd_joint.name_j not in spec["weighted_sleeve_bones"]
        ):
            continue
        name = obj.mmd_joint.name_j
        side = name.rsplit("_", 1)[1]
        reference = arm.pose.bones["Bone_ForearmTwistA01_" + side]
        child = arm.pose.bones[name]
        reference_map = reference.matrix @ reference.bone.matrix_local.inverted()
        child_map = child.matrix @ child.bone.matrix_local.inverted()
        maps[name] = max(
            abs(a - b) for a, b in zip(flat(reference_map), flat(child_map))
        )
        expected[name] = arm.matrix_world @ reference_map @ obj.matrix_local
    assert len(expected) == 4
    checkpoint = Path(spec["temp_dir"]) / "local-sleeve-visual-30fps.blend"
    bpy.ops.wm.open_mainfile(filepath=str(checkpoint))
    scene = bpy.context.scene
    scene.rigidbody_world.enabled = False
    records = []
    for obj in scene.objects:
        if (
            getattr(obj, "mmd_type", "") != "JOINT"
            or obj.mmd_joint.name_j not in expected
        ):
            continue
        name, constraint = obj.mmd_joint.name_j, obj.rigid_body_constraint
        wanted = expected[name]
        actual = obj.matrix_world
        records.append(
            {
                "joint": name,
                "native_child_vs_forearm_delta_map_error": maps[name],
                "translation_error": (wanted.translation - actual.translation).length,
                "rotation_error_degrees": math.degrees(
                    wanted.to_quaternion()
                    .rotation_difference(actual.to_quaternion())
                    .angle
                ),
                "maximum_matrix_error": max(
                    abs(a - b) for a, b in zip(flat(wanted), flat(actual))
                ),
                "enabled": constraint.enabled,
                "world_linked": obj.name
                in scene.rigidbody_world.constraints.all_objects,
                "anchor_parent_bone": constraint.object1.parent_bone,
                "limits": {
                    axis: {
                        "enabled": getattr(constraint, "use_limit_ang_" + axis),
                        "radians": [
                            getattr(constraint, "limit_ang_" + axis + "_lower"),
                            getattr(constraint, "limit_ang_" + axis + "_upper"),
                        ],
                    }
                    for axis in "xyz"
                },
            }
        )
    report = {
        "source_frame_at_build": frame,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": digest(checkpoint),
        "method": "Forearm native pose/rest delta times untouched original PMX joint rest matrix, compared with the actual built joint world frame.",
        "joints": records,
        "passed": len(records) == 4
        and all(
            item["native_child_vs_forearm_delta_map_error"] < 0.00001
            and item["maximum_matrix_error"] < 0.00001
            and item["enabled"]
            and item["world_linked"]
            for item in records
        ),
        "limits": "Validates initial joint coordinates and references only; does not prove later contact constraints or visual nonpenetration.",
    }
    write(output / "rest-frame-audit.json", report)
    print("LOCAL_SLEEVE_REST_FRAMES", json.dumps(report, ensure_ascii=True), flush=True)


def rig_basis(spec, native, solved, frame):
    result = {
        name: matrix(record["basis"])
        for name, record in solved[str(frame)]["sleeves"].items()
    }
    settings = spec["post_physics_rig"]
    for name in spec["weighted_sleeve_bones"]:
        if name.rsplit("_", 1)[1] not in settings["soft_limit_sides"]:
            continue
        n = matrix(native[str(frame)]["sleeves"][name]["basis"])
        _position, rotation, scale = result[name].decompose()
        base_position, base_rotation, _ = n.decompose()
        if base_rotation.dot(rotation) < 0:
            rotation.negate()
        angle = base_rotation.rotation_difference(rotation).angle
        limit = math.radians(
            settings["near_limit_degrees"]
            if "Sleeve01" in name
            else settings["far_limit_degrees"]
        )
        amount = math.tanh(angle / limit) * limit / angle if angle > 1e-9 else 1
        result[name] = Matrix.LocRotScale(
            base_position, base_rotation.slerp(rotation, amount), scale
        )
    return result


def apply_follow(spec, arm, base, side, gains):
    by_j = {bone.mmd_bone.name_j: bone for bone in arm.pose.bones}
    wrist = by_j[("左" if side == "L" else "右") + "手首"]
    elbow = by_j[("左" if side == "L" else "右") + "ひじ"]
    forearm_axis = (wrist.head - elbow.head).normalized()
    hand_axis = (wrist.tail - wrist.head).normalized()
    axis = forearm_axis.cross(hand_axis)
    angle = math.acos(max(-1, min(1, forearm_axis.dot(hand_axis))))
    axis = axis.normalized() if axis.length > 1e-8 else Vector((0, 1, 0))
    settings = spec["post_physics_rig"]
    for number, gain in zip((1, 2), gains):
        bone = arm.pose.bones[f"Bone_Sleeve0{number}_{side}"]
        location, rotation, scale = base[bone.name].decompose()
        follow_angle = max(
            -math.radians(settings["wrist_follow_max_degrees"]),
            min(math.radians(settings["wrist_follow_max_degrees"]), angle * gain),
        )
        correction = Quaternion(axis, follow_angle)
        moved = wrist.matrix.translation + correction @ (
            location - wrist.matrix.translation
        )
        displacement = moved - location
        if displacement.length > settings["wrist_pivot_max_translation"]:
            moved = (
                location
                + displacement.normalized() * settings["wrist_pivot_max_translation"]
            )
        bone.matrix = Matrix.LocRotScale(moved, correction @ rotation, scale)


def fit_window(spec, output, side, frames):
    import numpy as np
    from audit_ikhor_sleeve_geometry import (
        bone_j,
        evaluated_coords,
        mesh_topology,
        point,
        triangle_crossings,
        visible_crossings,
    )

    source = Path(
        spec.get(
            "physics_dir",
            Path(spec["output_dir"]) / spec["post_physics_rig"]["source_attempt"],
        )
    )
    native = json.loads(
        (Path(spec["output_dir"]) / "native-sleeve-303.json").read_text(
            encoding="utf-8"
        )
    )
    solved = json.loads((source / "local-rebake-303.json").read_text(encoding="utf-8"))
    assert digest(Path(spec["source_master"])) == spec["source_master_sha256"]
    bpy.ops.wm.open_mainfile(filepath=spec["source_master"])
    cameras = {}
    for frame in frames:
        set_frame(bpy.context.scene, frame)
        cameras[frame] = list(bpy.context.scene.camera.matrix_world.translation)
    bpy.ops.wm.open_mainfile(filepath=spec["portable"])
    scene, arm = bpy.context.scene, bpy.data.objects[spec["armature"]]
    for collection in curves(arm.animation_data.action):
        for curve in collection:
            if any(
                curve.data_path.startswith(arm.pose.bones[name].path_from_id() + ".")
                for name in spec["sleeve_bones"]
            ):
                curve.mute = True
    mesh = next(
        obj
        for obj in scene.objects
        if obj.type == "MESH" and len(obj.data.vertices) == 29959
    )
    _, triangles, sleeve, visible = mesh_topology(mesh)
    skin = [t for t, name in triangles if name == "手"]
    cloth = [
        t
        for t, name in triangles
        if name in {"衣", "衣2"} and sleeve[side].intersection(t)
    ]
    records = []
    for frame in frames:
        set_frame(scene, frame)
        bases = rig_basis(spec, native, solved, frame)
        for name, basis in bases.items():
            arm.pose.bones[name].matrix_basis = basis
        bpy.context.view_layer.update()
        base_world = {
            name: arm.pose.bones[name].matrix.copy()
            for name in spec["weighted_sleeve_bones"]
        }
        wrist = point(
            arm.matrix_world, bone_j(arm, ("左" if side == "L" else "右") + "手首").head
        )
        elbow = point(
            arm.matrix_world, bone_j(arm, ("左" if side == "L" else "右") + "ひじ").head
        )
        axis = (wrist - elbow) / np.linalg.norm(wrist - elbow)
        initial = evaluated_coords(mesh, bpy.context.evaluated_depsgraph_get())
        near = set(np.where(np.linalg.norm(initial - wrist, axis=1) < 0.15)[0])
        local_skin = [t for t in skin if near.intersection(t)]
        for first in spec["post_physics_rig"]["search_gains"]:
            for second in spec["post_physics_rig"]["search_gains"]:
                for name, basis in bases.items():
                    arm.pose.bones[name].matrix_basis = basis
                bpy.context.view_layer.update()
                apply_follow(spec, arm, base_world, side, (first, second))
                bpy.context.view_layer.update()
                coords = evaluated_coords(mesh, bpy.context.evaluated_depsgraph_get())
                crosses = triangle_crossings(coords, local_skin, cloth)
                visible_crossings(coords, visible, crosses, cameras[frame])
                rear = [
                    x
                    for x in crosses
                    if np.dot(np.mean(x["points"], axis=0) - wrist, axis) < 0
                ]
                vis = [x for x in crosses if x.get("camera_geometry_visible")]
                visible_rear = [x for x in rear if x.get("camera_geometry_visible")]
                records.append(
                    {
                        "frame": frame,
                        "gains": [first, second],
                        "pairs": len(crosses),
                        "rear": len(rear),
                        "visible": len(vis),
                        "visible_rear": len(visible_rear),
                    }
                )
        print("SLEEVE_RIG_FIT_FRAME", side, frame, flush=True)
    aggregate = []
    for first in spec["post_physics_rig"]["search_gains"]:
        for second in spec["post_physics_rig"]["search_gains"]:
            rows = [r for r in records if r["gains"] == [first, second]]
            score = [
                max(r["visible_rear"] for r in rows),
                sum(r["visible_rear"] for r in rows),
                sum(r["rear"] for r in rows),
                sum(r["visible"] for r in rows),
                abs(first) + abs(second),
            ]
            aggregate.append({"gains": [first, second], "score": score, "frames": rows})
    aggregate.sort(key=lambda r: r["score"])
    report = {
        "side": side,
        "frames": frames,
        "source_physics": str(source),
        "method": spec["post_physics_rig"],
        "best": aggregate[:10],
        "all_candidates": records,
        "allowed_bones": spec["sleeve_bones"],
        "main_hand_or_forearm_changed": False,
        "geometry_weights_materials_changed": False,
        "rendered": False,
        "status": "Geometric search only; visual and full303 continuous recheck remain required",
    }
    write(output / ("fit-" + side + ".json"), report)
    print(
        "SLEEVE_RIG_FIT_READY",
        json.dumps({"side": side, "best": aggregate[:3]}, ensure_ascii=True),
        flush=True,
    )


def corrective_prototype(spec, output):
    import numpy as np
    from audit_ikhor_sleeve_geometry import (
        bone_j,
        evaluated_coords,
        mesh_topology,
        point,
        triangle_crossings,
        visible_crossings,
    )
    from mathutils.bvhtree import BVHTree

    settings = spec["corrective_prototype"]
    side, frame = settings["side"], settings["reference_frame"]
    source = Path(spec.get("physics_dir", Path(spec["output_dir"]) / "local-v2"))
    actor = source / "Ikhor_Sleeve_Diagnostic_local_rebake.blend"
    bpy.ops.wm.open_mainfile(filepath=spec["source_master"])
    set_frame(bpy.context.scene, frame)
    camera = list(bpy.context.scene.camera.matrix_world.translation)
    bpy.ops.wm.open_mainfile(filepath=str(actor))
    scene, arm = bpy.context.scene, bpy.data.objects[spec["armature"]]
    set_frame(scene, frame)
    mesh = next(
        obj
        for obj in scene.objects
        if obj.type == "MESH" and len(obj.data.vertices) == 29959
    )
    modifier = next(mod for mod in mesh.modifiers if mod.type == "ARMATURE")
    assert not modifier.use_deform_preserve_volume, (
        "Prototype inverse Jacobian requires ordinary linear blend skinning"
    )
    _, triangles, sleeve, visible = mesh_topology(mesh)
    allowed = sleeve[side]
    assert len(allowed) == 573
    skin_ids = {i for tri, name in triangles if name == "手" for i in tri}
    assert not allowed.intersection(skin_ids), (
        "Skin must never be in the corrective region"
    )
    cloth = [
        tri
        for tri, name in triangles
        if name in {"衣", "衣2"} and allowed.intersection(tri)
    ]
    initial = evaluated_coords(mesh, bpy.context.evaluated_depsgraph_get())
    wrist = point(arm.matrix_world, bone_j(arm, "左手首").head)
    elbow = point(arm.matrix_world, bone_j(arm, "左ひじ").head)
    axis = (wrist - elbow) / np.linalg.norm(wrist - elbow)
    near = set(np.where(np.linalg.norm(initial - wrist, axis=1) < 0.15)[0])
    skin = [tri for tri, name in triangles if name == "手" and near.intersection(tri)]
    skin_tree = BVHTree.FromPolygons(
        [Vector(p) for p in initial], skin, all_triangles=True
    )
    adjacency = {index: set() for index in allowed}
    for edge in mesh.data.edges:
        a, b = edge.vertices
        if a in allowed:
            adjacency[a].add(b)
        if b in allowed:
            adjacency[b].add(a)
    seam_map = {}
    for index in allowed:
        vertex = mesh.data.vertices[index]
        weight_key = tuple(
            sorted(
                (mesh.vertex_groups[group.group].name, round(group.weight, 6))
                for group in vertex.groups
                if mesh.vertex_groups[group.group].name in arm.pose.bones
            )
        )
        seam_map.setdefault(
            (tuple(round(float(value), 6) for value in vertex.co), weight_key), []
        ).append(index)
    seam_groups = [indices for indices in seam_map.values() if len(indices) > 1]
    for indices in seam_groups:
        neighbors = set().union(*(adjacency[index] for index in indices)) - set(indices)
        for index in indices:
            adjacency[index] = neighbors.copy()
    identity = Matrix.Identity(3)
    mesh_to_arm = arm.matrix_world.inverted() @ mesh.matrix_world
    jacobians = {}
    for index in allowed:
        deform = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
        total = 0
        for group in mesh.data.vertices[index].groups:
            name = mesh.vertex_groups[group.group].name
            if name not in arm.pose.bones:
                continue
            bone = arm.pose.bones[name]
            deform += (
                bone.matrix @ bone.bone.matrix_local.inverted()
            ).to_3x3() * group.weight
            total += group.weight
        if total < 1:
            deform += identity * (1 - total)
        elif total > 1.000001:
            deform *= 1 / total
        jacobians[index] = (
            arm.matrix_world.to_3x3() @ deform @ mesh_to_arm.to_3x3()
        ).inverted_safe()
    key = mesh.shape_key_add(name=settings["shape_name"], from_mix=False)
    basis = mesh.data.shape_keys.key_blocks[0]
    key.value = 1
    samples = [
        (1 / 3, 1 / 3, 1 / 3),
        (0.6, 0.2, 0.2),
        (0.2, 0.6, 0.2),
        (0.2, 0.2, 0.6),
        (0.1, 0.45, 0.45),
        (0.45, 0.1, 0.45),
        (0.45, 0.45, 0.1),
    ]
    samples.extend(
        (a / 6, b / 6, (6 - a - b) / 6)
        for a in range(7)
        for b in range(7 - a)
        if max(a, b, 6 - a - b) < 6
    )

    def crossings(coords):
        values = triangle_crossings(coords, skin, cloth)
        visible_crossings(coords, visible, values, camera)
        for value in values:
            value["axis"] = float(
                np.dot(np.mean(value["points"], axis=0) - wrist, axis)
            )
        return values

    def metric(values):
        rear = [value for value in values if value["axis"] < 0]
        return {
            "pairs": len(values),
            "rear": len(rear),
            "visible": sum(
                bool(value.get("camera_geometry_visible")) for value in values
            ),
            "visible_rear": sum(
                bool(value.get("camera_geometry_visible")) for value in rear
            ),
        }

    before = metric(crossings(initial))
    variants, fixed_samples = [], {}
    for clearance in settings["clearance_candidates"]:
        delta = {index: Vector() for index in allowed}
        for index in allowed:
            key.data[index].co = basis.data[index].co
        bpy.context.view_layer.update()
        rows, best = [], None
        for iteration in range(settings["iterations"] + 1):
            coords = evaluated_coords(mesh, bpy.context.evaluated_depsgraph_get())
            values = crossings(coords)
            result = metric(values)
            displacement = np.linalg.norm(coords - initial, axis=1)
            maximum = float(displacement.max())
            score = [result["visible_rear"], result["rear"], result["visible"], maximum]
            rows.append(
                {
                    "iteration": iteration,
                    **result,
                    "maximum_world_displacement": maximum,
                }
            )
            if best is None or score < best[0]:
                best = (
                    score,
                    {index: value.copy() for index, value in delta.items()},
                    rows[-1],
                )
            if iteration == settings["iterations"]:
                break
            bad = [value for value in values if value["axis"] < 0.005]
            active = {
                index for value in bad for index in value["cloth"] if index in allowed
            }
            for _ in range(2):
                active |= {
                    neighbor
                    for index in list(active)
                    for neighbor in adjacency[index]
                    if neighbor in allowed
                }
            suggestions = {index: [] for index in active}
            for index in active:
                point_ = Vector(coords[index])
                hit, normal, _triangle, distance = skin_tree.find_nearest(point_)
                signed = (point_ - hit).dot(normal)
                if signed < clearance and distance < 0.020:
                    suggestions[index].append(normal * (clearance - signed))
            bad_triangles = {tuple(value["cloth"]) for value in bad}
            for tri in bad_triangles:
                for weights in samples:
                    point_ = sum(
                        (
                            Vector(coords[index]) * weight
                            for index, weight in zip(tri, weights)
                        ),
                        Vector(),
                    )
                    hit, normal, _triangle, distance = skin_tree.find_nearest(point_)
                    signed = (point_ - hit).dot(normal)
                    if signed >= clearance or distance >= 0.020:
                        continue
                    denom = sum(
                        weight * weight
                        for index, weight in zip(tri, weights)
                        if index in allowed
                    )
                    if denom < 1e-12:
                        if signed < -1e-6:
                            fixed_samples[tuple(tri) + tuple(weights)] = {
                                "cloth": list(tri),
                                "barycentric": list(weights),
                                "signed_nearest_skin_mm": signed * 1000,
                                "axis_offset_m": float(
                                    np.dot(np.array(point_) - wrist, axis)
                                ),
                            }
                        continue
                    for index, weight in zip(tri, weights):
                        if index in allowed:
                            suggestions.setdefault(index, []).append(
                                normal * ((clearance - signed) * weight / denom)
                            )
            proposed = {index: value.copy() for index, value in delta.items()}
            for index, vectors in suggestions.items():
                if not vectors:
                    continue
                step = sum(vectors, Vector()) / len(vectors)
                if step.length > settings["maximum_iteration_step"]:
                    step *= settings["maximum_iteration_step"] / step.length
                proposed[index] += step
            smoothed = {}
            for index in allowed:
                neighbors = adjacency[index]
                average = (
                    sum(
                        (proposed.get(other, Vector()) for other in neighbors), Vector()
                    )
                    / len(neighbors)
                    if neighbors
                    else proposed[index]
                )
                value = proposed[index].lerp(average, settings["smoothing"])
                if value.length > settings["maximum_world_displacement"]:
                    value *= settings["maximum_world_displacement"] / value.length
                smoothed[index] = value
            for indices in seam_groups:
                average = sum((smoothed[index] for index in indices), Vector()) / len(
                    indices
                )
                for index in indices:
                    smoothed[index] = average.copy()
            for index, value in smoothed.items():
                key.data[index].co = basis.data[index].co + jacobians[index] @ value
            delta = smoothed
            bpy.context.view_layer.update()
        score, best_delta, best_result = best
        variants.append(
            {
                "clearance": clearance,
                "best": best_result,
                "score": score,
                "iterations": rows,
                "rest_deltas": [
                    {"vertex": index, "delta": list(jacobians[index] @ value)}
                    for index, value in best_delta.items()
                    if value.length > 1e-8
                ],
            }
        )
    variants.sort(key=lambda value: value["score"])
    selected = variants[0]
    rest_delta = {index: Vector() for index in allowed}
    for entry in selected["rest_deltas"]:
        rest_delta[entry["vertex"]] = Vector(entry["delta"])

    def evaluate_delta(values):
        for index in allowed:
            key.data[index].co = basis.data[index].co + values[index]
        bpy.context.view_layer.update()
        coords = evaluated_coords(mesh, bpy.context.evaluated_depsgraph_get())
        found = crossings(coords)
        result = metric(found)
        maximum = float(np.linalg.norm(coords - initial, axis=1).max())
        return (
            [result["visible_rear"], result["rear"], result["visible"], maximum],
            result,
            coords,
            found,
        )

    current_score, _current_metric, current_coords, current_crosses = evaluate_delta(
        rest_delta
    )
    refinement = []
    for iteration in range(6):
        residual = [
            value
            for value in current_crosses
            if value["axis"] < 0 and value.get("camera_geometry_visible")
        ]
        if not residual:
            break
        best_refinement = None
        for crossing in residual:
            skin_points = [Vector(current_coords[index]) for index in crossing["skin"]]
            normal = (
                (skin_points[1] - skin_points[0])
                .cross(skin_points[2] - skin_points[0])
                .normalized()
            )
            middle = Vector(np.mean(crossing["points"], axis=0))
            _hit, nearest_normal, _idx, _distance = skin_tree.find_nearest(middle)
            patch = {index: 1.0 for index in crossing["cloth"] if index in allowed}
            for level, coefficient in ((1, 0.55), (2, 0.20)):
                del level
                for index in list(patch):
                    for neighbor in adjacency[index]:
                        if neighbor in allowed and neighbor not in patch:
                            patch[neighbor] = coefficient
            for direction in (normal, nearest_normal):
                for amount in (-0.004, -0.002, -0.001, 0.001, 0.002, 0.004):
                    trial = {index: value.copy() for index, value in rest_delta.items()}
                    for index, coefficient in patch.items():
                        world = jacobians[index].inverted_safe() @ trial[
                            index
                        ] + direction * (amount * coefficient)
                        if world.length > settings["maximum_world_displacement"]:
                            world *= (
                                settings["maximum_world_displacement"] / world.length
                            )
                        trial[index] = jacobians[index] @ world
                    for indices in seam_groups:
                        average = sum(
                            (trial[index] for index in indices), Vector()
                        ) / len(indices)
                        for index in indices:
                            trial[index] = average.copy()
                    score, result, coords, found = evaluate_delta(trial)
                    if score < current_score and (
                        best_refinement is None or score < best_refinement[0]
                    ):
                        best_refinement = (
                            score,
                            trial,
                            result,
                            coords,
                            found,
                            {
                                "iteration": iteration,
                                "amount": amount,
                                "normal": list(direction),
                                "cloth_triangle": crossing["cloth"],
                                "metric": result,
                            },
                        )
        if best_refinement is None:
            break
        (
            current_score,
            rest_delta,
            _current_metric,
            current_coords,
            current_crosses,
            record,
        ) = best_refinement
        refinement.append(record)
    selected = dict(selected)
    selected["rest_deltas"] = [
        {"vertex": index, "delta": list(value)}
        for index, value in rest_delta.items()
        if value.length > 1e-8
    ]
    selected["intersection_refinement"] = refinement
    evaluate_delta(rest_delta)
    final = evaluated_coords(mesh, bpy.context.evaluated_depsgraph_get())
    unchanged = np.ones(len(final), dtype=bool)
    unchanged[list(allowed)] = False
    outside_error = float(
        np.linalg.norm(final[unchanged] - initial[unchanged], axis=1).max()
    )
    assert outside_error < 0.0000001, outside_error
    final_crosses = crossings(final)
    report = {
        "actor": str(actor),
        "actor_sha256": digest(actor),
        "mesh": mesh.name,
        "frame": frame,
        "shape_name": key.name,
        "allowed_vertex_count": len(allowed),
        "allowed_vertices": sorted(allowed),
        "synchronized_uv_seam_vertex_groups": seam_groups,
        "settings": settings,
        "before": before,
        "after": metric(final_crosses),
        "residual_visible_rear": [
            value
            for value in final_crosses
            if value["axis"] < 0 and value.get("camera_geometry_visible")
        ],
        "fixed_vertex_edge_sample_limits": list(fixed_samples.values()),
        "chosen": selected,
        "variants": variants,
        "maximum_world_displacement_mm": float(
            np.linalg.norm(final - initial, axis=1).max() * 1000
        ),
        "outside_allowed_maximum_world_error": outside_error,
        "basis_uv_weights_materials_changed": False,
        "hand_bones_changed": False,
        "project_saved": False,
        "rendered": False,
        "status": "single-pose unsaved prototype; no temporal or render acceptance",
    }
    write(output / "corrective-prototype.json", report)
    print(
        "SLEEVE_CORRECTIVE_PROTOTYPE",
        json.dumps(
            {
                "before": before,
                "after": report["after"],
                "maximum_mm": report["maximum_world_displacement_mm"],
                "outside_error": outside_error,
                "report": str(output / "corrective-prototype.json"),
            },
            ensure_ascii=True,
        ),
        flush=True,
    )


def rig_samples(spec, output):
    source = Path(spec.get("physics_dir", Path(spec["output_dir"]) / "local-v2"))
    native = json.loads(
        (Path(spec["output_dir"]) / "native-sleeve-303.json").read_text(
            encoding="utf-8"
        )
    )
    solved = json.loads((source / "local-rebake-303.json").read_text(encoding="utf-8"))
    result = {
        frame: {
            "sleeves": {
                name: {"basis": flat(value)}
                for name, value in rig_basis(spec, native, solved, int(frame)).items()
            }
        }
        for frame in solved
    }
    write(output / "fitted-repair-303.json", result)
    write(
        output / "rig-correction-report.json",
        {
            "source_physics": str(source / "local-physics-report.json"),
            "source_physics_samples_sha256": digest(source / "local-rebake-303.json"),
            "settings": spec["post_physics_rig"],
            "count": len(result),
            "range": spec["guard_frames"],
            "actual_operation": "Soft native-relative angular amplitude limit on R01/R02 only; left physical basis unchanged. Wrist-follow search is diagnostic, no fitted swing is active.",
            "failed_attempts": spec["preserved_failed_attempts"],
            "visual_status": "pending all-frame audit",
        },
    )


def export_corrective(spec, output, prototype_path, actor_override=None):
    from array import array

    prototype = json.loads(prototype_path.read_text(encoding="utf-8"))
    assert prototype["after"]["visible_rear"] == 0
    assert prototype["outside_allowed_maximum_world_error"] < 1e-7
    actor = actor_override or Path(prototype["actor"])
    assert digest(Path(spec["pmx"])) == spec["pmx_sha256"]
    bpy.ops.wm.open_mainfile(filepath=str(actor))
    scene = bpy.context.scene
    mesh = bpy.data.objects[prototype["mesh"]]
    keys = mesh.data.shape_keys
    basis = keys.key_blocks[0]
    rest = array("f", [0]) * (3 * len(basis.data))
    basis.data.foreach_get("co", rest)
    baseline_basis_sha = hashlib.sha256(rest.tobytes()).hexdigest()
    shape = mesh.shape_key_add(name=prototype["shape_name"], from_mix=False)
    assert shape.name == prototype["shape_name"]
    allowed = set(prototype["allowed_vertices"])
    deltas = []
    for entry in prototype["chosen"]["rest_deltas"]:
        index = entry["vertex"]
        assert index in allowed and Vector(entry["delta"]).length <= 0.03
        shape.data[index].co = basis.data[index].co + Vector(entry["delta"])
        deltas.append({"index": index, "delta": entry["delta"]})
    source_morph_action = keys.animation_data.action
    keys.animation_data.action = source_morph_action.copy()
    keys.animation_data.action.name = source_morph_action.name + " | sleeve corrective"
    settings = prototype["settings"]
    frames, values = settings["window_frames"], settings["window_values"]
    for frame, value in zip(frames, values):
        shape.value = value
        shape.keyframe_insert("value", frame=frame, group="Sleeve repair corrective")
    path = shape.path_from_id("value")
    curve = next(
        curve
        for group in curves(keys.animation_data.action)
        for curve in group
        if curve.data_path == path
    )
    curve.extrapolation = "CONSTANT"
    curve.update()
    for i, point in enumerate(curve.keyframe_points):
        point.interpolation = "BEZIER"
        point.handle_left_type = point.handle_right_type = "FREE"
        left_interval = frames[i] - frames[i - 1] if i else frames[1] - frames[0]
        right_interval = (
            frames[i + 1] - frames[i]
            if i < len(frames) - 1
            else frames[-1] - frames[-2]
        )
        point.handle_left = (frames[i] - left_interval / 3, values[i])
        point.handle_right = (frames[i] + right_interval / 3, values[i])
    curve.update()
    serialized = [
        {
            "frame": float(point.co.x),
            "value": float(point.co.y),
            "interpolation": point.interpolation,
            "handle_left_type": point.handle_left_type,
            "handle_right_type": point.handle_right_type,
            "handle_left": list(point.handle_left),
            "handle_right": list(point.handle_right),
        }
        for point in curve.keyframe_points
    ]
    data = {
        "source_pmx_sha256": spec["pmx_sha256"],
        "baseline_blend_sha256": spec["source_master_sha256"],
        "vertex_count": len(basis.data),
        "mesh_object": mesh.name,
        "basis_position_sha256": baseline_basis_sha,
        "actor_source": str(actor),
        "actor_source_sha256": digest(actor),
        "prototype_report": str(prototype_path),
        "prototype_report_sha256": digest(prototype_path),
        "shapes": [
            {
                "name": shape.name,
                "side": "L",
                "deltas": deltas,
                "keys": serialized,
                "extrapolation": "CONSTANT",
                "allowed_region": "sum of source Bone_Sleeve01_L and Bone_Sleeve02_L weights >0.001",
                "allowed_count": 573,
                "maximum_reference_world_displacement_m": prototype[
                    "maximum_world_displacement_mm"
                ]
                / 1000,
            }
        ],
        "scope": "Single L4220 prototype cleared visible wrist-rear crossings; full303 and production-shader visual verification pending",
    }
    data_path = output / "corrective-data.json"
    write(data_path, data)
    set_frame(scene, prototype["frame"])
    final = output / "Ikhor_Sleeve_Corrective_Preview.blend"
    assert not final.exists()
    bpy.ops.wm.save_as_mainfile(filepath=str(final))
    report = {
        "project": str(final),
        "project_sha256": digest(final),
        "source_v4_sha256": spec["source_master_sha256"],
        "corrective_data": str(data_path),
        "corrective_data_sha256": digest(data_path),
        "prototype_report_sha256": digest(prototype_path),
        "source_actor_sha256": digest(actor),
        "action": next(
            obj for obj in scene.objects if obj.type == "ARMATURE"
        ).animation_data.action.name,
        "shape": shape.name,
        "allowed_count": len(allowed),
        "nonzero_delta_count": len(deltas),
        "maximum_rest_delta_mm": max(Vector(entry["delta"]).length for entry in deltas)
        * 1000,
        "keys": serialized,
        "source_basis_position_sha256": baseline_basis_sha,
        "visual_status": "preview only; no full-segment acceptance",
    }
    write(output / "corrective-export-report.json", report)
    print(
        "SLEEVE_CORRECTIVE_EXPORTED", json.dumps(report, ensure_ascii=True), flush=True
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=PROFILE)
    parser.add_argument("--physics-dir", type=Path)
    parser.add_argument("--fit-side", choices=["L", "R"])
    parser.add_argument("--frames", type=int, nargs="+")
    parser.add_argument("--prototype-report", type=Path)
    parser.add_argument("--actor-input", type=Path)
    parser.add_argument(
        "--output-dir", type=Path, help="New isolated solver attempt directory"
    )
    parser.add_argument(
        "--temp-dir", type=Path, help="New isolated checkpoint directory"
    )
    parser.add_argument(
        "--phase",
        choices=[
            "audit",
            "candidate",
            "local-rebake",
            "rest-audit",
            "fit",
            "corrective-prototype",
            "rig-samples",
            "export-corrective",
        ],
        default="audit",
    )
    parser.add_argument(
        "--mode",
        choices=[
            "native_sleeves",
            "translations_only",
            "proximal_native",
            "local_rebake",
            "fitted_repair",
        ],
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    spec = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    output = args.output_dir or Path(spec["output_dir"])
    if args.temp_dir:
        spec["temp_dir"] = str(args.temp_dir)
    if args.physics_dir:
        spec["physics_dir"] = str(args.physics_dir)
    output.mkdir(parents=True, exist_ok=True)
    if args.phase == "audit":
        audit(spec, output)
    elif args.phase == "local-rebake":
        local_rebake(spec, output)
    elif args.phase == "rest-audit":
        rest_frame_audit(spec, output)
    elif args.phase == "fit":
        assert args.fit_side and args.frames
        fit_window(spec, output, args.fit_side, args.frames)
    elif args.phase == "corrective-prototype":
        corrective_prototype(spec, output)
    elif args.phase == "rig-samples":
        rig_samples(spec, output)
    elif args.phase == "export-corrective":
        assert args.prototype_report
        export_corrective(spec, output, args.prototype_report, args.actor_input)
    else:
        assert args.mode
        candidate(spec, output, args.mode)


if __name__ == "__main__":
    main()
