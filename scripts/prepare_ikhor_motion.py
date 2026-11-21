"""Import Ikhor's native Hina VMD and prepare a separately audited motion candidate.

Run in an independent Blender process with --disable-autoexec. This module never
opens/builds the production duet and never renders or changes preferences.
"""

import argparse
import hashlib
import importlib
import json
import math
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

import bpy
from bpy_extras.anim_utils import BakeOptions, bake_action_objects_iter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "presets/quality/ikhor-native-motion-v1.json"


def plain(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if hasattr(value, "__dict__"):
        return {k: plain(v) for k, v in vars(value).items() if not k.startswith("_")}
    try:
        return list(value)
    except TypeError:
        return str(value)


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(value):
    return unicodedata.normalize("NFKC", value)


def audit_sources(spec):
    pmx = importlib.import_module("bl_ext.blender_org.mmd_tools.core.pmx")
    vmd = importlib.import_module("bl_ext.blender_org.mmd_tools.core.vmd")
    source = Path(spec["pmx"])
    assert digest(source) == spec["pmx_sha256"]
    model = pmx.load(str(source))
    motion = vmd.File()
    motion.load(filepath=spec["vmd"])
    bones = {norm(b.name) for b in model.bones}
    morphs = {norm(m.name) for m in model.morphs}
    material_records = []
    for material in model.materials:
        record = plain(material)
        record["texture_references"] = {}
        for name in ("texture", "sphere_texture", "toon_texture"):
            if name == "toon_texture" and material.is_shared_toon_texture:
                continue
            value = getattr(material, name)
            if (
                isinstance(value, int)
                and not isinstance(value, bool)
                and 0 <= value < len(model.textures)
            ):
                record["texture_references"][name] = model.textures[value].path
        material_records.append(record)
    report = {
        "profile": spec["id"],
        "pmx": str(source),
        "pmx_sha256": digest(source),
        "vmd": spec["vmd"],
        "vmd_sha256": digest(Path(spec["vmd"])),
        "name": model.name,
        "comment": model.comment,
        "name_e": model.name_e,
        "comment_e": model.comment_e,
        "vertices": len(model.vertices),
        "bones": len(model.bones),
        "materials": material_records,
        "textures": [t.path for t in model.textures],
        "missing_textures": [
            t.path for t in model.textures if not Path(t.path).is_file()
        ],
        "rigids": [plain(r) for r in model.rigids],
        "joints": [plain(j) for j in model.joints],
        "bone_names": [b.name for b in model.bones],
        "morph_names": [m.name for m in model.morphs],
        "selected_source_bones": [
            plain(b)
            for b in model.bones
            if b.name in {"A", "左足ＩＫ", "右足ＩＫ", "左つま先ＩＫ", "右つま先ＩＫ"}
        ],
        "motion_bone_tracks": {
            n: {
                "count": len(keys),
                "first": min(k.frame_number for k in keys),
                "last": max(k.frame_number for k in keys),
            }
            for n, keys in motion.boneAnimation.items()
        },
        "motion_morph_tracks": {
            n: {
                "count": len(keys),
                "first": min(k.frame_number for k in keys),
                "last": max(k.frame_number for k in keys),
            }
            for n, keys in motion.shapeKeyAnimation.items()
        },
        "missing_multikey_bone_tracks_nfkc": [
            n
            for n, keys in motion.boneAnimation.items()
            if len(keys) > 2 and norm(n) not in bones
        ],
        "matched_morphs_nfkc": [
            n for n in motion.shapeKeyAnimation if norm(n) in morphs
        ],
        "unmatched_morphs_nfkc": [
            n for n in motion.shapeKeyAnimation if norm(n) not in morphs
        ],
        "motion_animation_fields": {
            k: {
                "type": type(v).__name__,
                "count": len(v) if hasattr(v, "__len__") else None,
            }
            for k, v in vars(motion).items()
        },
        "motion_non_pose_fields": {
            k: plain(v)
            for k, v in vars(motion).items()
            if k
            not in {
                "boneAnimation",
                "shapeKeyAnimation",
                "cameraAnimation",
                "lampAnimation",
            }
        },
    }
    weighted = Counter()
    for vertex in model.vertices:
        weight = vertex.weight
        for i, index in enumerate(weight.bones):
            if index < 0 or index >= len(model.bones):
                continue
            factors = list(weight.weights)
            factor = (
                factors[i]
                if i < len(factors)
                else (1 - factors[0] if len(factors) == 1 and i == 1 else 1.0)
            )
            if factor > 0.00001:
                weighted[model.bones[index].name] += 1
    report["weighted_vertex_memberships"] = dict(weighted)
    return model, motion, report


def import_native(spec, output):
    _model, motion, report = audit_sources(spec)
    report["missing_used_texture_references"] = [
        {
            "material": record.get("name"),
            "references": {
                key: value
                for key, value in record["texture_references"].items()
                if value in report["missing_textures"]
            },
        }
        for record in report["materials"]
        if any(
            value in report["missing_textures"]
            for value in record["texture_references"].values()
        )
    ]
    if not (output / "source-audit.json").exists():
        write(output / "source-audit.json", report)
    print(
        "IKHOR_SOURCE_AUDIT",
        json.dumps(
            {
                "materials": [m["name"] for m in report["materials"]],
                "missing_textures": report["missing_textures"],
                "missing_used_texture_references": report[
                    "missing_used_texture_references"
                ],
                "rigid_count": len(report["rigids"]),
                "joint_count": len(report["joints"]),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    # Startup state belongs only to this independent process; production is never opened.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = 30, 1
    scene.frame_set(1)
    assert "FINISHED" in bpy.ops.mmd_tools.import_model(
        filepath=spec["pmx"],
        scale=spec["scale"],
        clean_model=False,
        remove_doubles=False,
        save_log=False,
        log_level="ERROR",
    )
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    root = arm.parent
    root.name, arm.name = "Ikhor | root", "Ikhor | armature"
    collection = bpy.data.collections.new("Ikhor | portable character")
    scene.collection.children.link(collection)
    for obj in list(scene.objects):
        if obj != root and obj not in root.children_recursive:
            continue
        obj["performer_id"] = "ikhor"
        if obj.name not in collection.objects:
            collection.objects.link(obj)
        for old_collection in list(obj.users_collection):
            physics_collections = (
                {scene.rigidbody_world.collection, scene.rigidbody_world.constraints}
                if scene.rigidbody_world
                else set()
            )
            if (
                old_collection != collection
                and old_collection not in physics_collections
            ):
                old_collection.objects.unlink(obj)
        if obj.type == "MESH" and getattr(obj, "mmd_type", "") not in {
            "RIGID_BODY",
            "JOINT",
        }:
            obj.name = "Ikhor | mesh | " + obj.name
            for material in obj.data.materials:
                if material:
                    material["performer_id"] = "ikhor"
                    material["source_mmd_material_name"] = (
                        material.mmd_material.name_j or material.name
                    )
    names = {}
    for name in motion.boneAnimation:
        names.setdefault(norm(name), []).append(name)
    aliases = []
    for bone in arm.pose.bones:
        old = bone.mmd_bone.name_j
        candidates = names.get(norm(old), [])
        if old not in motion.boneAnimation and len(candidates) == 1:
            bone.mmd_bone.name_j = candidates[0]
            aliases.append([old, candidates[0]])
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    assert "FINISHED" in bpy.ops.mmd_tools.import_vmd(
        filepath=spec["vmd"],
        scale=spec["scale"],
        bone_mapper="PMX",
        update_scene_settings=False,
        create_new_action=True,
        use_nla=False,
        save_log=False,
        log_level="ERROR",
    )
    arm.animation_data.action.name = "Ikhor | Full Hina native body 30fps"
    scene.frame_start, scene.frame_end = 1, 6368
    scene["ikhor_motion_profile"] = spec["id"]
    scene["ikhor_native_import_only"] = True
    report.update(
        {
            "scale": spec["scale"],
            "root": root.name,
            "armature": arm.name,
            "collection": collection.name,
            "meshes": [
                {
                    "name": o.name,
                    "vertices": len(o.data.vertices),
                    "materials": [m.name if m else None for m in o.data.materials],
                }
                for o in collection.objects
                if o.type == "MESH" and getattr(o, "mmd_type", "") != "RIGID_BODY"
            ],
            "bone_aliases": aliases,
            "native_action": arm.animation_data.action.name,
            "native_action_frame_range": list(arm.animation_data.action.frame_range),
            "imported_ik_constraints": [
                {
                    "bone": b.name,
                    "name_j": b.mmd_bone.name_j,
                    "constraint": c.name,
                    "mute": c.mute,
                    "influence": c.influence,
                }
                for b in arm.pose.bones
                for c in b.constraints
                if c.type == "IK"
            ],
            "rigid_objects": [
                {"name": o.name, "mode": o.mmd_rigid.type, "bone": o.mmd_rigid.bone}
                for o in collection.objects
                if getattr(o, "mmd_type", "") == "RIGID_BODY"
            ],
            "root_location_preserved": list(root.location),
            "manual_character_translation": False,
            "runtime_physics_built": root.mmd_root.is_built,
            "rendered": False,
        }
    )
    packed, missing = [], []
    for image in bpy.data.images:
        if image.source != "FILE":
            continue
        if Path(bpy.path.abspath(image.filepath)).is_file():
            image.pack()
            packed.append(image.name)
        else:
            missing.append({"name": image.name, "path": image.filepath})
    report["packed_images"] = packed
    report["known_missing_images_preserved_without_fabrication"] = missing
    path = output / "native-import-30fps.blend"
    assert not path.exists()
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    report["import_project"] = str(path)
    write(output / "import-report.json", report)
    print(
        "IKHOR_NATIVE_IMPORTED",
        json.dumps(
            {
                "root": root.name,
                "armature": arm.name,
                "meshes": report["meshes"],
                "materials": len(report["materials"]),
                "rigids": len(report["rigids"]),
                "joints": len(report["joints"]),
                "report": str(output / "import-report.json"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


def set_frame(scene, value):
    first = math.floor(value)
    scene.frame_set(first, subframe=value - first)
    bpy.context.view_layer.update()


def snapshot(arm, names):
    return {
        name: [v for row in arm.pose.bones[name].matrix for v in row] for name in names
    }


def pose_error(expected, actual):
    return max(
        (
            abs(v - actual[name][i])
            for name, values in expected.items()
            for i, v in enumerate(values)
        ),
        default=0.0,
    )


def shape_values():
    return {
        obj.name: {key.name: key.value for key in obj.data.shape_keys.key_blocks}
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and obj.data.shape_keys
        and obj.get("performer_id") == "ikhor"
    }


def repair_self_inheritance(arm, model):
    changes = []
    by_j = {b.mmd_bone.name_j: b for b in arm.pose.bones}
    for index, source in enumerate(model.bones):
        if not source.additionalTransform or source.additionalTransform[0] != index:
            continue
        if not (source.hasAdditionalRotate or source.hasAdditionalLocation):
            continue
        bone = by_j[source.name]
        removed = []
        for name in ("mmd_additional_rotation", "mmd_additional_location"):
            constraint = bone.constraints.get(name)
            if constraint:
                removed.append(
                    {
                        "name": constraint.name,
                        "type": constraint.type,
                        "subtarget": getattr(constraint, "subtarget", None),
                    }
                )
                bone.constraints.remove(constraint)
        changes.append(
            {
                "bone": bone.name,
                "source_index": index,
                "original_additional_transform": list(source.additionalTransform),
                "original_rotation_enabled": source.hasAdditionalRotate,
                "original_location_enabled": source.hasAdditionalLocation,
                "removed_generated_constraints": removed,
                "reason": "PMX additional transform references the same bone; generated shadow/dummy path formed a dependency cycle. Only this invalid inheritance is disabled; authored IK is retained.",
            }
        )
        bone.mmd_bone.has_additional_rotation = False
        bone.mmd_bone.has_additional_location = False
    bpy.context.view_layer.update()
    return changes


def prepare_bake(spec, output):
    sys.path.insert(0, str(ROOT / "scripts"))

    report_path, candidate = output / "motion-report.json", output / "candidate.blend"
    assert not report_path.exists() and not candidate.exists()
    native_import = Path(spec["output_dir"]) / "native-import-30fps.blend"
    bpy.ops.wm.open_mainfile(filepath=str(native_import))
    scene = bpy.context.scene
    arm, root = bpy.data.objects["Ikhor | armature"], bpy.data.objects["Ikhor | root"]
    assert not root.mmd_root.is_built
    assert not any(b.constraints.get("mmd_tools_rigid_track") for b in arm.pose.bones)
    # PMX import can create an unbuilt world already; it contains only this new
    # model, never a reused production cache. Disable it for native pose audit.
    if scene.rigidbody_world:
        assert not scene.rigidbody_world.point_cache.is_baked
        assert all(
            o.get("performer_id") == "ikhor"
            for o in scene.rigidbody_world.collection.objects
        )
        scene.rigidbody_world.enabled = False
    # Actor packaging must not leave native rigid proxies outside Bullet's
    # designated collections. This is distinct from ordinary scene linking.
    assert (
        scene.rigidbody_world
        and scene.rigidbody_world.collection
        and scene.rigidbody_world.constraints
    )
    native_world = scene.rigidbody_world
    relinked_bodies, relinked_joints = [], []
    for obj in scene.objects:
        if getattr(obj, "mmd_type", "") == "RIGID_BODY":
            if obj.name not in native_world.collection.objects:
                native_world.collection.objects.link(obj)
                relinked_bodies.append(obj.name)
        elif (
            getattr(obj, "mmd_type", "") == "JOINT"
            and obj.name not in native_world.constraints.objects
        ):
            native_world.constraints.objects.link(obj)
            relinked_joints.append(obj.name)
    model, _motion, source_report = audit_sources(spec)
    report = {
        "profile": spec["id"],
        "source_pmx": spec["pmx"],
        "source_pmx_sha256": spec["pmx_sha256"],
        "source_vmd": spec["vmd"],
        "source_vmd_sha256": source_report["vmd_sha256"],
        "root": root.name,
        "armature": arm.name,
        "collection": "Ikhor | portable character",
        "material_count": len(model.materials),
        "rendered": False,
        "source_fps": 30,
        "output_fps": 60,
        "manual_character_translation": False,
        "runtime_old_Aether_cache_reused": False,
    }
    report["native_import"] = str(native_import)
    report["world_collection_membership_repair"] = {
        "relinked_bodies": len(relinked_bodies),
        "relinked_joints": len(relinked_joints),
        "reason": "Preserve native Bullet membership alongside the isolated actor collection; a previous discarded candidate had zero participating bodies.",
    }
    report["self_inheritance_repairs"] = repair_self_inheritance(arm, model)
    names = [b.name for b in arm.pose.bones if not b.is_mmd_shadow_bone]
    by_j = {b.mmd_bone.name_j: b.name for b in arm.pose.bones}
    dynamic_names = sorted(
        {
            by_j[model.bones[r.bone].name]
            for r in model.rigids
            if r.mode != 0 and r.bone >= 0 and model.bones[r.bone].name in by_j
        }
    )
    assert dynamic_names, (
        "The source has no bone-bound native dynamics; no solver success can be claimed"
    )
    original_action = arm.animation_data.action
    original_action.use_fake_user = True
    original_action.name = "Ikhor | full native Hina source 30fps (preserved)"
    sim_first, sim_last = spec["physics"]["simulation_source_blender_frames"]
    export_first, export_last = spec["physics"]["export_source_blender_frames"]
    sample_frames = [
        export_first,
        export_first + 1,
        2420,
        2470,
        2500,
        export_last - 1,
        export_last,
    ]
    native_samples = {}
    for frame in sample_frames:
        set_frame(scene, frame)
        native_samples[str(frame)] = snapshot(arm, names)
    scene.render.fps, scene.render.fps_base = 30, 1
    scene.frame_start, scene.frame_end = sim_first, sim_last
    set_frame(scene, sim_first)
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    started = time.perf_counter()
    print("IKHOR_NATIVE_BUILD_START", flush=True)
    assert "FINISHED" in bpy.ops.mmd_tools.build_rig()
    build_seconds = time.perf_counter() - started
    physical = [
        b.name for b in arm.pose.bones if b.constraints.get("mmd_tools_rigid_track")
    ]
    assert physical and set(physical) <= set(names)
    world = scene.rigidbody_world
    world.enabled = True
    world_bodies = [obj for obj in world.collection.all_objects if obj.rigid_body]
    assert len(world_bodies) == len(model.rigids) and len(world_bodies) > 0, (
        len(world_bodies),
        len(model.rigids),
    )
    assert any(not obj.rigid_body.kinematic for obj in world_bodies), (
        "No participating dynamic bodies"
    )
    world.substeps_per_frame = spec["physics"]["substeps_per_frame"]
    world.solver_iterations = spec["physics"]["solver_iterations"]
    world.time_scale = spec["physics"]["time_scale"]
    cache = world.point_cache
    cache.frame_start, cache.frame_end = sim_first, sim_last
    report["native_physics"] = {
        "raw_rigids": len(model.rigids),
        "raw_joints": len(model.joints),
        "raw_mode_counts": dict(Counter(r.mode for r in model.rigids)),
        "built_rigid_bodies": len(world_bodies),
        "built_constraints_including_noncollision": len(world.constraints.all_objects),
        "participating_kinematic_counts": dict(
            Counter(str(obj.rigid_body.kinematic) for obj in world_bodies)
        ),
        "participating_enabled_counts": dict(
            Counter(
                str(getattr(obj.rigid_body, "enabled", True)) for obj in world_bodies
            )
        ),
        "gravity": list(scene.gravity),
        "physical_bones": physical,
        "weighted_physical_bones": [
            n
            for n in physical
            if source_report["weighted_vertex_memberships"].get(
                arm.pose.bones[n].mmd_bone.name_j, 0
            )
            > 0
        ],
        "simulation_source_blender_frames": [sim_first, sim_last],
        "export_source_blender_frames": [export_first, export_last],
        "preroll_source_frames": export_first - sim_first,
        "substeps": world.substeps_per_frame,
        "iterations": world.solver_iterations,
        "build_seconds": build_seconds,
        "scope": "Preceding choreography supplies local settling; not continuous simulation from VMD frame zero and not full-song physical validation.",
    }

    def progress(current_scene, *_):
        if (current_scene.frame_current - sim_first) % 30 == 0:
            print(
                "IKHOR_SIM_FRAME",
                current_scene.frame_current,
                "/",
                sim_last,
                flush=True,
            )

    bpy.app.handlers.frame_change_post.append(progress)
    started = time.perf_counter()
    print("IKHOR_NATIVE_SIM_START", sim_first, sim_last, len(physical), flush=True)
    try:
        with bpy.context.temp_override(point_cache=cache):
            result = bpy.ops.ptcache.bake(bake=True)
        assert "FINISHED" in result and cache.is_baked
    finally:
        bpy.app.handlers.frame_change_post.remove(progress)
    report["native_physics"]["simulation_seconds"] = time.perf_counter() - started
    simulated = {}
    for frame in sample_frames:
        set_frame(scene, frame)
        simulated[str(frame)] = snapshot(arm, physical)
    report["physical_deviation_from_native_samples"] = [
        {
            "frame": frame,
            "max_matrix_delta": pose_error(
                {n: native_samples[str(frame)][n] for n in physical},
                simulated[str(frame)],
            ),
        }
        for frame in sample_frames
    ]
    action = original_action.copy()
    action.name = "Ikhor | full Hina and local native physics"
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
    started = time.perf_counter()
    iterator = bake_action_objects_iter([(arm, action)], bake_options=options)
    iterator.send(None)
    for frame in range(export_first, export_last + 1):
        iterator.send(frame)
        if (frame - export_first) % 30 == 0:
            print("IKHOR_VISUAL_BAKE_FRAME", frame, flush=True)
    iterator.send(None)
    report["native_physics"]["visual_export_seconds"] = time.perf_counter() - started
    report["native_backup_action"] = original_action.name
    write(
        output / "visual-checkpoint.json",
        {
            "report": report,
            "names": names,
            "physical": physical,
            "simulated": simulated,
            "sample_frames": sample_frames,
        },
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "simulated-visual-30fps.blend"))
    print("IKHOR_VISUAL_CHECKPOINT_SAVED", flush=True)
    finish_portable(
        spec,
        output,
        arm,
        root,
        names,
        physical,
        simulated,
        sample_frames,
        report,
        original_action,
    )


def finish_portable(
    spec,
    output,
    arm,
    root,
    names,
    physical,
    simulated,
    sample_frames,
    report,
    original_action,
):
    from bl_ext.blender_org.mmd_tools.core.model import Model

    sys.path.insert(0, str(ROOT / "scripts"))
    from mmd_final_scene import retime_actions

    scene = bpy.context.scene
    candidate, report_path = output / "candidate.blend", output / "motion-report.json"
    review_first, review_last = spec["review_output_frames"]
    garbage = set()
    current_model = Model(root)
    for group in (
        current_model.rigidGroupObject(),
        current_model.jointGroupObject(),
        current_model.temporaryGroupObject(),
    ):
        if group:
            garbage.update(group.children_recursive)
            garbage.add(group)
    # Build can detach proxies from their original parenting groups. Remove all
    # simulation components as well as the named groups, preserving render mesh.
    garbage.update(
        obj
        for obj in scene.objects
        if getattr(obj, "mmd_type", "") in {"RIGID_BODY", "JOINT"}
        or obj.rigid_body is not None
        or obj.rigid_body_constraint is not None
    )
    assert arm not in garbage and root not in garbage
    for bone in arm.pose.bones:
        constraint = bone.constraints.get("mmd_tools_rigid_track")
        if constraint:
            bone.constraints.remove(constraint)
    scene.rigidbody_world.enabled = False
    # Bullet constraints must die while their referenced bodies still exist.
    # Mixed ID deletion can otherwise free a body before removeConstraintRef.
    constraint_objects = {
        obj for obj in garbage if obj.rigid_body_constraint is not None
    }
    bpy.data.batch_remove(ids=constraint_objects)
    garbage -= constraint_objects
    print("IKHOR_CONSTRAINT_OBJECTS_REMOVED", len(constraint_objects), flush=True)
    bpy.ops.rigidbody.world_remove()
    bpy.data.batch_remove(ids=garbage)
    assert not any(obj.rigid_body or obj.rigid_body_constraint for obj in scene.objects)
    root.mmd_root.is_built = False
    root["production_physics_baked"] = True
    root["ikhor_physics_validated_output_range"] = spec["physics"][
        "verified_output_frames_with_guard"
    ]
    errors = []
    for frame in sample_frames:
        set_frame(scene, frame)
        errors.append(
            {
                "frame": frame,
                "error": pose_error(simulated[str(frame)], snapshot(arm, physical)),
            }
        )
    report["simulation_vs_portable_samples"] = errors
    assert max(e["error"] for e in errors) < 0.002, errors
    output_samples = [1, 4140, 4162, 4200, 4250, 4290, 4330, 4439, 11899]
    before_retime = {}
    for frame in output_samples:
        source_frame = 330 + (frame - 1) / 2
        set_frame(scene, source_frame)
        before_retime[str(frame)] = {
            "pose": snapshot(arm, names),
            "shapes": shape_values(),
        }
    transformed_curves = retime_actions(330, 2)
    scene.render.fps = 60
    scene.frame_start, scene.frame_end = spec["output_frame_range"]
    original_action.name = "Ikhor | full native Hina source 60fps (preserved)"
    report["timebase"] = {
        "formula": "output60 = 1 + 2 * (sourceVMD - 329) = 1 + 2 * (importedBlender30 - 330)",
        "full_source_VMD_retained": True,
        "all_keys_and_both_handles_transformed": True,
        "transformed_curves": transformed_curves,
        "output_range": spec["output_frame_range"],
        "active_action_range": list(arm.animation_data.action.frame_range),
        "review_VMD_range": [329 + (review_first - 1) / 2, 329 + (review_last - 1) / 2],
        "native_solver_rate_remains_30fps": True,
    }
    retime_checks, expected = [], {}
    for frame in output_samples:
        set_frame(scene, frame)
        now, shapes = snapshot(arm, names), shape_values()
        error = pose_error(before_retime[str(frame)]["pose"], now)
        shape_error = max(
            (
                abs(value - shapes[obj][key])
                for obj, keys in before_retime[str(frame)]["shapes"].items()
                for key, value in keys.items()
            ),
            default=0,
        )
        retime_checks.append(
            {"frame": frame, "pose_error": error, "shape_error": shape_error}
        )
        expected[str(frame)] = {"pose": now, "shapes": shapes}
    assert all(
        max(r["pose_error"], r["shape_error"]) < 0.0001 for r in retime_checks
    ), retime_checks
    report["retime_checks"] = retime_checks
    previous, max_step, max_abs = None, 0.0, 0.0
    for frame in range(review_first, review_last + 1):
        set_frame(scene, frame)
        coordinates = [
            tuple(arm.matrix_world @ arm.pose.bones[name].matrix.translation)
            for name in physical
        ]
        assert all(math.isfinite(v) for point in coordinates for v in point)
        max_abs = max(max_abs, max(abs(v) for point in coordinates for v in point))
        if previous:
            max_step = max(
                max_step, max(math.dist(a, b) for a, b in zip(previous, coordinates))
            )
        previous = coordinates
    report["numeric_300_frame_motion_check"] = {
        "frames": [review_first, review_last],
        "count": review_last - review_first + 1,
        "physical_bone_count": len(physical),
        "all_coordinates_finite": True,
        "max_absolute_world_coordinate": max_abs,
        "maximum_adjacent_tip_step_world_units": max_step,
        "visual_collision_and_naturalness_approval": False,
    }
    report["ik_constraints_retained"] = [
        {
            "bone": b.name,
            "name_j": b.mmd_bone.name_j,
            "mute": c.mute,
            "influence": c.influence,
        }
        for b in arm.pose.bones
        for c in b.constraints
        if c.type == "IK"
    ]
    scene["ikhor_native_import_only"] = False
    scene["ikhor_candidate_only"] = True
    scene["ikhor_timebase"] = report["timebase"]["formula"]
    scene["ikhor_partial_physics"] = True
    set_frame(scene, review_first)
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate))
    write(output / "reopen-expected.json", expected)
    report.update(
        {
            "candidate": str(candidate),
            "candidate_sha256": digest(candidate),
            "runtime_rigidbody_world_removed": scene.rigidbody_world is None,
            "saved_preferences": False,
            "known_missing_source_texture": str(Path(spec["pmx"]).parent / "y1.png"),
            "material_repair_performed_here": False,
            "technical_candidate_prepared": True,
            "independent_reopen_pending": True,
            "limits": [
                "Physical keys are local to output 4139-4441; outside this interval their extrapolation is not full-song physics.",
                "Body and Morph full VMD tracks, including negative output frames, are retained.",
                "300 output frames were checked numerically; no GPU render, full visual collision audit or naturalness approval is implied.",
                "The source face y1.png is absent; material integration must handle this known missing asset separately.",
            ],
        }
    )
    write(report_path, report)
    print("IKHOR_PORTABLE_CANDIDATE_SAVED", str(candidate), flush=True)


def recover_baked(spec, output):
    assert (
        not (output / "candidate.blend").exists()
        and not (output / "motion-report.json").exists()
    )
    checkpoint = json.loads(
        (output / "visual-checkpoint.json").read_text(encoding="utf-8")
    )
    assert checkpoint["report"]["native_physics"]["built_rigid_bodies"] == 514
    bpy.ops.wm.open_mainfile(filepath=str(output / "simulated-visual-30fps.blend"))
    arm = bpy.data.objects[checkpoint["report"]["armature"]]
    root = bpy.data.objects[checkpoint["report"]["root"]]
    original = bpy.data.actions[checkpoint["report"]["native_backup_action"]]
    finish_portable(
        spec,
        output,
        arm,
        root,
        checkpoint["names"],
        checkpoint["physical"],
        checkpoint["simulated"],
        checkpoint["sample_frames"],
        checkpoint["report"],
        original,
    )


def verify_candidate(spec, output, append_only=False):
    report_file = output / (
        "append-verification.json" if append_only else "reopen-report.json"
    )
    assert not report_file.exists()
    production = json.loads((output / "motion-report.json").read_text(encoding="utf-8"))
    assert production["native_physics"]["built_rigid_bodies"] == 514, (
        "Reject the discarded zero-participant prototype"
    )
    if (output / "append-report.json").exists():
        append = json.loads((output / "append-report.json").read_text(encoding="utf-8"))
        production.update(
            candidate=append["candidate"],
            candidate_sha256=append["candidate_sha256"],
            collection=append["collection"],
        )
    expected = json.loads((output / "reopen-expected.json").read_text(encoding="utf-8"))
    candidate = Path(production["candidate"])
    assert digest(candidate) == production["candidate_sha256"]
    if append_only:
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        scene = bpy.context.scene
        assert scene.rigidbody_world is None
        with bpy.data.libraries.load(str(candidate), link=False) as (available, loaded):
            assert production["collection"] in available.collections
            loaded.collections = [production["collection"]]
        scene.collection.children.link(loaded.collections[0])
        scene.render.fps, scene.render.fps_base = 60, 1
        scene.frame_start, scene.frame_end = spec["output_frame_range"]
    else:
        bpy.ops.wm.open_mainfile(filepath=str(candidate))
    scene, arm = bpy.context.scene, bpy.data.objects[production["armature"]]
    records = []
    for frame, value in expected.items():
        set_frame(scene, int(frame))
        actual, shapes = snapshot(arm, value["pose"]), shape_values()
        error = pose_error(value["pose"], actual)
        shape_error = max(
            (
                abs(x - shapes[obj][name])
                for obj, keys in value["shapes"].items()
                for name, x in keys.items()
            ),
            default=0,
        )
        records.append(
            {"frame": int(frame), "pose_error": error, "shape_error": shape_error}
        )
    root = bpy.data.objects[production["root"]]
    residual = [
        {"object": o.name, "bone": b.name, "constraint": c.name}
        for o in scene.objects
        if o.type == "ARMATURE"
        for b in o.pose.bones
        for c in b.constraints
        if c.name == "mmd_tools_rigid_track"
    ]
    project_sha = digest(candidate)
    report = {
        "candidate": str(candidate),
        "project": str(candidate),
        "sha256": project_sha,
        "project_sha256": project_sha,
        "source_pmx_sha256": spec["pmx_sha256"],
        "read_only": True,
        "rendered": False,
        "appended_only_requested_collection": append_only,
        "samples": records,
        "fps": scene.render.fps,
        "frame_range": [scene.frame_start, scene.frame_end],
        "runtime_world_absent": scene.rigidbody_world is None,
        "native_rig_not_built": not root.mmd_root.is_built,
        "residual_physics_constraints": residual,
        "all_actors_are_ikhor": all(
            o.get("performer_id") == "ikhor"
            for o in scene.objects
            if o.type in {"MESH", "ARMATURE"}
        ),
        "known_missing_images": [
            image.filepath
            for image in bpy.data.images
            if image.source == "FILE" and not image.packed_file
        ],
        "physical_scope": spec["physics"]["verified_output_frames_with_guard"],
        "full_song_physics_validated": False,
        "user_art_approval": False,
        "participating_rigid_bodies": production["native_physics"][
            "built_rigid_bodies"
        ],
        "participating_dynamic_rigid_bodies": production["native_physics"][
            "participating_kinematic_counts"
        ].get("False", 0),
        "physics_simulation_source_frames": production["native_physics"][
            "simulation_source_blender_frames"
        ],
        "timebase": production["timebase"],
        "numeric_300_frame_motion_check": production["numeric_300_frame_motion_check"],
        "motion_report": str(output / "motion-report.json"),
        "portable_manifest": str(output / "append-report.json"),
    }
    collection = bpy.data.collections.get(production["collection"])
    report["collection"] = production["collection"]
    report["collection_objects"] = (
        [o.name for o in collection.all_objects] if collection else []
    )
    report["all_collection_objects_are_ikhor"] = bool(collection) and all(
        o.get("performer_id") == "ikhor" for o in collection.all_objects
    )
    materials = (
        {
            material
            for o in collection.all_objects
            if o.type == "MESH"
            for material in o.data.materials
            if material
        }
        if collection
        else set()
    )
    report["material_count"] = len(materials)
    report["all_materials_are_ikhor"] = bool(materials) and all(
        material.get("performer_id") == "ikhor" for material in materials
    )
    report["no_Camera_Light_or_default_Cube"] = bool(collection) and all(
        o.type not in {"CAMERA", "LIGHT"} and o.name != "Cube"
        for o in collection.all_objects
    )
    report["no_live_rigid_or_joint_objects"] = bool(collection) and all(
        getattr(o, "mmd_type", "") not in {"RIGID_BODY", "JOINT"}
        and o.rigid_body is None
        and o.rigid_body_constraint is None
        for o in collection.all_objects
    )
    report["passed"] = (
        len(records) == 9
        and all(max(r["pose_error"], r["shape_error"]) < 0.0001 for r in records)
        and report["runtime_world_absent"]
        and report["native_rig_not_built"]
        and not residual
        and report["all_actors_are_ikhor"]
        and report["all_collection_objects_are_ikhor"]
        and report["all_materials_are_ikhor"]
        and scene.render.fps == 60
        and report["no_Camera_Light_or_default_Cube"]
        and report["no_live_rigid_or_joint_objects"]
        and report["participating_dynamic_rigid_bodies"] > 0
    )
    write(report_file, report)
    print(
        "IKHOR_INDEPENDENT_REOPEN",
        json.dumps(
            {
                "passed": report["passed"],
                "maximum_pose_error": max(r["pose_error"] for r in records),
                "report": str(report_file),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    assert report["passed"]


def finalize_append(spec, output):
    report_file = output / "append-report.json"
    final = output / "Ikhor_Hina_Portable.blend"
    assert not report_file.exists() and not final.exists()
    production = json.loads((output / "motion-report.json").read_text(encoding="utf-8"))
    assert production["native_physics"]["built_rigid_bodies"] == 514, (
        "Reject the discarded zero-participant prototype"
    )
    bpy.ops.wm.open_mainfile(filepath=production["candidate"])
    scene = bpy.context.scene
    assert scene.rigidbody_world is None
    collection = bpy.data.collections[production["collection"]]
    collection.name = "Ikhor | character"
    collection["performer_id"] = "ikhor"
    for obj in collection.all_objects:
        obj["performer_id"] = "ikhor"
        assert (
            obj.type not in {"LIGHT", "CAMERA"}
            and obj.rigid_body is None
            and obj.rigid_body_constraint is None
        )
        if obj.type == "MESH":
            for material in obj.data.materials:
                if material:
                    material["performer_id"] = "ikhor"
    bpy.ops.wm.save_as_mainfile(filepath=str(final))
    report = {
        "candidate": str(final),
        "candidate_sha256": digest(final),
        "source_candidate": production["candidate"],
        "collection": collection.name,
        "root": production["root"],
        "armature": production["armature"],
        "objects": [
            {
                "name": o.name,
                "type": o.type,
                "parent": o.parent.name if o.parent else None,
                "performer_id": o.get("performer_id"),
            }
            for o in collection.all_objects
        ],
        "necessary_shadow_helper_bones": [
            {"name": b.name, "type": b.mmd_shadow_bone_type}
            for b in bpy.data.objects[production["armature"]].pose.bones
            if b.is_mmd_shadow_bone
        ],
        "source_native_import_untouched": True,
        "runtime_physics_removed": True,
        "rendered": False,
        "append_contract": "Append only collection Ikhor | character, retaining internal hierarchy and actions. Material integration handles known missing source face image separately.",
    }
    write(report_file, report)
    print(
        "IKHOR_APPEND_READY",
        json.dumps(
            {
                "candidate": str(final),
                "collection": collection.name,
                "objects": len(report["objects"]),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="New attempt directory; native import always remains in the profile's original output_dir",
    )
    parser.add_argument(
        "--phase",
        choices=[
            "import",
            "audit",
            "bake",
            "recover",
            "finalize",
            "verify",
            "verify-append",
        ],
        default="import",
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    spec = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    output = args.output_dir or Path(spec["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    if args.phase == "recover":
        recover_baked(spec, output)
        return
    if args.phase == "finalize":
        finalize_append(spec, output)
        return
    if args.phase == "bake":
        prepare_bake(spec, output)
        return
    if args.phase in {"verify", "verify-append"}:
        verify_candidate(spec, output, append_only=args.phase == "verify-append")
        return
    if args.phase == "audit":
        _, _, report = audit_sources(spec)
        report["supersedes_derived_texture_references_only"] = (
            "source-audit.json generic enum/bool mapping bug; raw PMX records were correct"
        )
        version = 2
        while (output / f"source-audit-v{version}.json").exists():
            version += 1
        write(output / f"source-audit-v{version}.json", report)
        print(
            "IKHOR_CORRECTED_SOURCE_AUDIT",
            str(output / f"source-audit-v{version}.json"),
            flush=True,
        )
        return
    assert not (output / "native-import-30fps.blend").exists()
    import_native(spec, output)


if __name__ == "__main__":
    main()
