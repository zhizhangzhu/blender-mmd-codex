"""Audit anatomical chest support in source PMX and current baked motion.

This is a read-only validation in an independent Blender process. It does not
invent breast bones, alter body shape, or add a second solver to baked motion.
Every weighted bone and every native rigid/joint is recorded before deciding
whether a dedicated chest secondary-motion experiment is applicable.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def value(item):
    if isinstance(item, bpy.types.ID):
        return item.name
    if hasattr(item, "__len__") and not isinstance(item, str):
        return list(item)
    return item


def selected_properties(obj, terms):
    if obj is None:
        return {}
    result = {}
    for prop in obj.bl_rna.properties:
        name = prop.identifier
        if name == "rna_type" or not any(term in name for term in terms):
            continue
        try:
            result[name] = value(getattr(obj, name))
        except (AttributeError, TypeError, ValueError):
            pass
    return result


def pmx_paths(node, trail=()):
    if isinstance(node, dict):
        for key, item in node.items():
            yield from pmx_paths(item, (*trail, str(key)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from pmx_paths(item, (*trail, str(index)))
    elif isinstance(node, str) and node.lower().endswith(".pmx"):
        yield "/".join(trail), Path(node)


def bone_by_japanese(arm, names):
    for bone in arm.pose.bones:
        if bone.name in names or bone.mmd_bone.name_j in names:
            return bone
    return None


def weighted_meshes(arm):
    return [
        obj
        for obj in arm.users_scene[0].objects
        if obj.type == "MESH"
        and any(mod.type == "ARMATURE" and mod.object == arm for mod in obj.modifiers)
    ]


def audit_weights(arm):
    totals = {}
    inverse = arm.matrix_world.inverted()
    vertices = []
    for mesh in weighted_meshes(arm):
        material_for_vertex = {}
        for face in mesh.data.polygons:
            material = mesh.data.materials[face.material_index]
            for index in face.vertices:
                material_for_vertex.setdefault(index, set()).add(
                    material.name if material else "<none>"
                )
        for vertex in mesh.data.vertices:
            point = inverse @ mesh.matrix_world @ vertex.co
            weights = []
            for group in vertex.groups:
                if group.weight <= 0.001:
                    continue
                name = mesh.vertex_groups[group.group].name
                if name not in arm.pose.bones:
                    continue
                weights.append((name, group.weight))
                count, total = totals.get(name, (0, 0.0))
                totals[name] = (count + 1, total + group.weight)
            vertices.append(
                (
                    mesh.name,
                    vertex.index,
                    point,
                    weights,
                    material_for_vertex.get(vertex.index, set()),
                )
            )
    return totals, vertices


def chest_frame(arm):
    upper = bone_by_japanese(arm, {"上半身2", "上半身２"})
    lower = bone_by_japanese(arm, {"上半身"})
    neck = bone_by_japanese(arm, {"首"})
    left = bone_by_japanese(arm, {"左肩"})
    right = bone_by_japanese(arm, {"右肩"})
    if not all((upper, lower, neck, left, right)):
        return None
    up = (neck.bone.head_local - lower.bone.head_local).normalized()
    toe_directions = []
    for side in ("左", "右"):
        ankle = bone_by_japanese(arm, {side + "足首"})
        toe = bone_by_japanese(arm, {side + "つま先"})
        if ankle and toe:
            direction = toe.bone.head_local - ankle.bone.head_local
            direction -= up * direction.dot(up)
            if direction.length > 0.00001:
                toe_directions.append(direction.normalized())
    if not toe_directions:
        return None
    forward = sum(toe_directions, Vector()).normalized()
    across = up.cross(forward).normalized()
    forward = across.cross(up).normalized()
    origin = upper.bone.head_local.copy()
    height = (neck.bone.head_local - origin).dot(up)
    width = abs((left.bone.head_local - right.bone.head_local).dot(across))
    width = max(width, abs((left.bone.tail_local - right.bone.tail_local).dot(across)))
    left_arm = bone_by_japanese(arm, {"左腕"})
    right_arm = bone_by_japanese(arm, {"右腕"})
    if left_arm and right_arm:
        width = max(
            width,
            abs((left_arm.bone.head_local - right_arm.bone.head_local).dot(across)),
        )
    if height <= 0.01 or width <= 0.01:
        return None
    return {
        "origin": origin,
        "up": up,
        "forward": forward,
        "across": across,
        "height": height,
        "width": width,
        "upper": upper.name,
        "lower": lower.name,
        "neck": neck.name,
    }


def in_chest(point, frame, include_back=False):
    p = point - frame["origin"]
    x, z, front = p.dot(frame["across"]), p.dot(frame["up"]), p.dot(frame["forward"])
    return (
        abs(x) <= frame["width"] * 0.63
        and -frame["height"] * 0.12 <= z <= frame["height"] * 0.88
        and (include_back or front > frame["width"] * 0.025)
    )


def source_audit(arm, source_path, profile_key):
    totals, vertices = audit_weights(arm)
    frame = chest_frame(arm)
    region = []
    regional = {}
    materials = {}
    if frame:
        for mesh, index, point, weights, material_names in vertices:
            if not in_chest(point, frame):
                continue
            region.append(
                {
                    "mesh": mesh,
                    "vertex": index,
                    "point": list(point),
                    "weights": dict(weights),
                    "materials": sorted(material_names),
                }
            )
            for material in material_names:
                materials[material] = materials.get(material, 0) + 1
            for name, weight in weights:
                count, total = regional.get(name, (0, 0.0))
                regional[name] = (count + 1, total + weight)
    all_bones = []
    for bone in arm.pose.bones:
        total = totals.get(bone.name, (0, 0.0))
        local = regional.get(bone.name, (0, 0.0))
        all_bones.append(
            {
                "name": bone.name,
                "name_j": bone.mmd_bone.name_j,
                "name_e": bone.mmd_bone.name_e,
                "parent": bone.parent.name if bone.parent else None,
                "head": list(bone.bone.head_local),
                "tail": list(bone.bone.tail_local),
                "weighted_vertices": total[0],
                "total_weight": total[1],
                "chest_front_vertices": local[0],
                "chest_front_weight": local[1],
            }
        )
    native_objects = list(arm.parent.children_recursive)
    rigids = []
    for obj in native_objects:
        if obj.mmd_type != "RIGID_BODY":
            continue
        rigids.append(
            {
                "name": obj.name,
                "bone": obj.mmd_rigid.bone,
                "type": str(obj.mmd_rigid.type),
                "location": list(
                    arm.matrix_world.inverted() @ obj.matrix_world.translation
                ),
                "mmd": selected_properties(
                    obj.mmd_rigid, ("type", "bone", "size", "shape", "collision")
                ),
                "physics": selected_properties(
                    obj.rigid_body,
                    ("mass", "friction", "damping", "restitution", "margin"),
                ),
            }
        )
    joints = []
    for obj in native_objects:
        if obj.mmd_type != "JOINT":
            continue
        constraint = obj.rigid_body_constraint
        joints.append(
            {
                "name": obj.name,
                "first": constraint.object1.name
                if constraint and constraint.object1
                else None,
                "second": constraint.object2.name
                if constraint and constraint.object2
                else None,
                "settings": selected_properties(
                    constraint, ("limit_", "spring_", "disable_collisions")
                ),
            }
        )
    dynamic = {r["bone"] for r in rigids if r["type"] in {"1", "2"}}
    localized = []
    if frame:
        main_torso = {frame["upper"], frame["lower"], frame["neck"]}
        for bone in all_bones:
            if (
                bone["name"] in main_torso
                or bone["chest_front_vertices"] < 10
                or bone["chest_front_weight"] < 3
            ):
                continue
            if (
                in_chest(Vector(bone["head"]), frame, include_back=True)
                or bone["chest_front_weight"] / max(bone["total_weight"], 1e-9) >= 0.5
            ):
                localized.append(
                    {**bone, "dynamic_rigid_attached": bone["name"] in dynamic}
                )
    named_markers = [
        b
        for b in all_bones
        if any(
            term in (b["name"] + b["name_j"] + b["name_e"]).lower()
            for term in ("胸", "乳", "breast", "bust", "mune")
        )
    ]
    supported = [b for b in localized if b["dynamic_rigid_attached"]]
    if frame is None or not region:
        status = "anatomical_region_unresolved"
    elif supported:
        status = "localized_native_candidates_require_review"
    else:
        status = "not_applicable_to_existing_dedicated_binding"
    return {
        "source_pmx": str(source_path),
        "profile_key": profile_key,
        "armature": arm.name,
        "bone_count": len(all_bones),
        "weighted_bone_count": sum(b["weighted_vertices"] > 0 for b in all_bones),
        "anatomical_frame": {k: value(v) for k, v in frame.items()} if frame else None,
        "anatomical_region_definition": "rest mesh: central upper-torso front, axes derived from torso/shoulders/toes; includes material names and all weighted influences; not selected by chest-name matching",
        "chest_front_vertex_count": len(region),
        "chest_front_material_counts": materials,
        "chest_front_weight_ranking": sorted(
            [
                {"bone": name, "vertices": count, "weight": weight}
                for name, (count, weight) in regional.items()
            ],
            key=lambda item: item["weight"],
            reverse=True,
        ),
        "all_bones": all_bones,
        "all_rigids": rigids,
        "all_joints": joints,
        "named_chest_markers": named_markers,
        "localized_weighted_candidates": localized,
        "supported_native_candidates": supported,
        "applicability_status": status,
        "interpretation_limit": "Geometric region is a reproducible audit proxy, not automatic semantic segmentation. Localized clothing/accessory chains are not automatically breast bindings. No simulation is invented when a dedicated weighted chain is absent.",
    }, region


def current_motion(path, start, end):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    records = []
    for arm in [
        o for o in scene.objects if o.type == "ARMATURE" and o.get("performer_id")
    ]:
        totals, _ = audit_weights(arm)
        names = [
            b.name
            for b in arm.pose.bones
            if b.name in {"上半身", "上半身2", "首"}
            or any(
                t in (b.name + b.mmd_bone.name_j + b.mmd_bone.name_e).lower()
                for t in ("胸", "乳", "breast", "bust", "mune")
            )
        ]
        samples = {name: [] for name in names}
        for number in range(start, end + 1):
            scene.frame_set(number)
            for name in names:
                bone = arm.pose.bones[name]
                local = (
                    bone.parent.matrix.inverted() @ bone.matrix
                    if bone.parent
                    else bone.matrix.copy()
                )
                samples[name].append(
                    (
                        local.translation.copy(),
                        local.to_quaternion().normalized(),
                        bone.matrix.copy(),
                    )
                )
        changes = []
        for name, values in samples.items():
            p0, q0, m0 = values[0]
            changes.append(
                {
                    "bone": name,
                    "weighted_vertices": totals.get(name, (0, 0))[0],
                    "parent": arm.pose.bones[name].parent.name
                    if arm.pose.bones[name].parent
                    else None,
                    "max_parent_local_translation_delta": max(
                        (p - p0).length for p, q, m in values
                    ),
                    "max_parent_local_rotation_radians": max(
                        q0.rotation_difference(q).angle for p, q, m in values
                    ),
                    "max_armature_matrix_delta": max(
                        abs(m[row][col] - m0[row][col])
                        for p, q, m in values
                        for row in range(4)
                        for col in range(4)
                    ),
                    "all_finite": all(
                        math.isfinite(float(n))
                        for p, q, m in values
                        for row in m
                        for n in row
                    ),
                }
            )
        records.append(
            {
                "actor": arm["performer_id"],
                "armature": arm.name,
                "frames": [start, end],
                "samples_per_bone": end - start + 1,
                "bones": changes,
            }
        )
    return {
        "project": str(path),
        "fps": scene.render.fps,
        "actors": records,
        "source_saved": False,
        "new_solver_added": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--baked", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start", type=int, default=4140)
    parser.add_argument("--end", type=int, default=4439)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    profile = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    sources = list(
        {
            str(path): (key, path)
            for key, path in pmx_paths(profile)
            if key.startswith("performers/")
        }.values()
    )
    assert len(sources) == 2, [(key, str(path)) for key, path in sources]
    baked = current_motion(args.baked, args.start, args.end)
    write(args.output_dir / "baked-motion-validation.json", baked)
    print("BAKED_TORSO_MOTION_CHECKED", flush=True)
    audits = []
    for index, (key, source) in enumerate(sources):
        assert source.is_file(), source
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        before = set(bpy.data.objects)
        result = bpy.ops.mmd_tools.import_model(
            filepath=str(source),
            scale=0.08,
            clean_model=False,
            remove_doubles=False,
            save_log=False,
        )
        assert result == {"FINISHED"}, result
        arms = [obj for obj in set(bpy.data.objects) - before if obj.type == "ARMATURE"]
        assert len(arms) == 1
        bpy.context.view_layer.update()
        audit, region = source_audit(arms[0], source, key)
        audits.append(audit)
        write(args.output_dir / f"source-model-{index + 1}-binding.json", audit)
        write(args.output_dir / f"source-model-{index + 1}-chest-region.json", region)
        print(
            "SOURCE_PMX_AUDITED",
            index + 1,
            audit["applicability_status"],
            audit["chest_front_vertex_count"],
            flush=True,
        )
    finite = all(b["all_finite"] for a in baked["actors"] for b in a["bones"])
    report = {
        "profile": str(args.profile),
        "current_baked_motion": baked,
        "source_models": [
            {
                k: a[k]
                for k in (
                    "source_pmx",
                    "profile_key",
                    "bone_count",
                    "weighted_bone_count",
                    "chest_front_vertex_count",
                    "chest_front_weight_ranking",
                    "named_chest_markers",
                    "localized_weighted_candidates",
                    "supported_native_candidates",
                    "applicability_status",
                )
            }
            for a in audits
        ],
        "new_chest_simulation_performed": False,
        "new_chest_animation_exported": False,
        "original_animation_modified": False,
        "no_double_driver_added": True,
        "finite_motion_samples": finite,
        "status": "binding_and_baked_motion_audited",
        "scope": "Applicability validation; not a physics-quality or visual approval. Dedicated new dynamics require a genuine weighted native candidate and explicit review of material/anatomical ownership.",
    }
    write(args.output_dir / "validation-report.json", report)
    assert finite
    print("CHEST_SECONDARY_MOTION_APPLICABILITY_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
