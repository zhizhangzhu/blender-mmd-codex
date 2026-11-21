"""Apply only a separately tested sleeve Action to the rejected v4 master.

This writes a new candidate, never updates the current registry or approves art.
An independent delta verifier and continuous wrist/geometry review are required.
"""

import argparse
import hashlib
import json
import math
import sys
from array import array
from pathlib import Path

import bpy

SOURCE_SHA = "283acdf2f1063fae32b0ed49caed07952706ff4d7b9ed1675490fa7ad021a0c1"
PMX_SHA = "ebba744cee847c16cfe5be037e7464d4f701c8edb2f5033e7de5730bd6654a52"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def add_correctives(scene, path):
    """Copy explicit sleeve rest deltas, restricted independently by side."""
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["source_pmx_sha256"] == PMX_SHA
    assert data["baseline_blend_sha256"] == SOURCE_SHA
    mesh = next(
        obj
        for obj in scene.objects
        if obj.type == "MESH"
        and obj.get("performer_id") == "ikhor"
        and obj.name == "Ikhor | mesh | Ikhor_mesh"
        and obj.data.shape_keys
    )
    assert len(mesh.data.vertices) == data["vertex_count"] == 29959
    allowed_by_side = {}
    for side in ("L", "R"):
        groups = {
            group.index
            for group in mesh.vertex_groups
            if group.name in {f"Bone_Sleeve01_{side}", f"Bone_Sleeve02_{side}"}
        }
        assert len(groups) == 2
        allowed_by_side[side] = {
            vertex.index
            for vertex in mesh.data.vertices
            if any(
                group.group in groups and group.weight > 0 for group in vertex.groups
            )
        }
        assert len(allowed_by_side[side]) == 573
    keys = mesh.data.shape_keys
    active_shape_index = mesh.active_shape_key_index
    if keys.animation_data and keys.animation_data.action:
        slot_id = keys.animation_data.action_slot.identifier
        keys.animation_data.action = keys.animation_data.action.copy()
        keys.animation_data.action_slot = next(
            slot
            for slot in keys.animation_data.action.slots
            if slot.identifier == slot_id
        )
    records = []
    assert 1 <= len(data["shapes"]) <= 4
    for item in data["shapes"]:
        assert item["side"] in allowed_by_side and item["name"] not in keys.key_blocks
        allowed = allowed_by_side[item["side"]]
        assert len(item["deltas"]) <= len(allowed)
        indices = [entry["index"] for entry in item["deltas"]]
        assert len(indices) == len(set(indices)) and set(indices) <= allowed
        block = mesh.shape_key_add(name=item["name"], from_mix=False)
        block.relative_key = keys.reference_key
        coords = array("f", [0]) * (3 * len(block.data))
        keys.reference_key.data.foreach_get("co", coords)
        maximum = 0
        for entry in item["deltas"]:
            delta = entry["delta"]
            assert len(delta) == 3 and all(math.isfinite(value) for value in delta)
            length = math.sqrt(sum(value * value for value in delta))
            assert length <= 0.03, (
                "Review any corrective exceeding 3cm before integration"
            )
            maximum = max(maximum, length)
            for axis, value in enumerate(delta):
                coords[entry["index"] * 3 + axis] += value
        block.data.foreach_set("co", coords)
        assert len(item["keys"]) >= 4
        assert item["keys"][0]["value"] == item["keys"][-1]["value"] == 0
        assert all(
            a["frame"] < b["frame"] for a, b in zip(item["keys"], item["keys"][1:])
        )
        for point in item["keys"]:
            assert 4139 <= point["frame"] <= 4441 and 0 <= point["value"] <= 1
            block.value = point["value"]
            block.keyframe_insert("value", frame=point["frame"])
        curves = [
            curve
            for layer in keys.animation_data.action.layers
            for strip in layer.strips
            for bag in strip.channelbags
            for curve in bag.fcurves
            if curve.data_path == block.path_from_id("value")
        ]
        assert len(curves) == 1
        curve = curves[0]
        assert len(curve.keyframe_points) == len(item["keys"])
        for point, expected in zip(curve.keyframe_points, item["keys"]):
            assert abs(point.co.x - expected["frame"]) < 0.0001
            point.interpolation = expected["interpolation"]
            point.handle_left_type = expected["handle_left_type"]
            point.handle_right_type = expected["handle_right_type"]
            point.handle_left = expected["handle_left"]
            point.handle_right = expected["handle_right"]
        curve.extrapolation = "CONSTANT"
        block.value = 0
        records.append(
            {
                "name": block.name,
                "side": item["side"],
                "modified_vertices": len(indices),
                "maximum_rest_delta_m": maximum,
            }
        )
    mesh.active_shape_key_index = active_shape_index
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", type=Path, required=True)
    parser.add_argument("--actor-sha256", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--repair-report", type=Path, required=True)
    parser.add_argument("--corrective-data", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    source = Path(bpy.data.filepath)
    assert sha(source) == SOURCE_SHA, "This migration accepts the rejected v4 only"
    assert sha(args.actor) == args.actor_sha256
    assert args.repair_report.is_file()
    assert not bpy.context.scene.rigidbody_world, "A portable baseline is required"
    args.output_dir.mkdir(parents=True, exist_ok=False)
    arm = next(
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "ARMATURE" and obj.get("performer_id") == "ikhor"
    )
    old_action = arm.animation_data.action.name
    with bpy.data.libraries.load(str(args.actor), link=False) as (available, loaded):
        assert args.action in available.actions
        loaded.actions = [args.action]
    action = loaded.actions[0]
    arm.animation_data.action = action
    arm.animation_data.action_slot = next(
        slot for slot in action.slots if slot.target_id_type == "OBJECT"
    )
    scene = bpy.context.scene
    corrective_records = (
        add_correctives(scene, args.corrective_data) if args.corrective_data else []
    )
    scene["ikhor_sleeve_repair"] = "local-eight-sleeve-candidate-v1"
    scene["ikhor_sleeve_repair_report"] = str(args.repair_report)
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    project = args.output_dir / "Franken_Aksiniya_Ikhor_Bold_Wedding.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project), compress=True)
    report = {
        "source": str(source),
        "source_sha256": SOURCE_SHA,
        "actor": str(args.actor),
        "actor_sha256": args.actor_sha256,
        "repair_report": str(args.repair_report),
        "repair_report_sha256": sha(args.repair_report),
        "corrective_data": str(args.corrective_data) if args.corrective_data else None,
        "corrective_data_sha256": sha(args.corrective_data)
        if args.corrective_data
        else None,
        "correctives": corrective_records,
        "previous_action": old_action,
        "applied_action": action.name,
        "project": str(project),
        "project_sha256": sha(project),
        "automatic_approval": False,
        "scope": "Assign the locally repaired Ikhor Action and optionally tested sleeve corrective shapes within separate 573-vertex L/R regions; retain Basis, UV, weights, original morph curves, materials, stage, camera and the other performer.",
        "required_next": [
            "independent source/current Action and 303-frame non-sleeve delta verification",
            "continuous actual sleeve/skin geometry scan and both-wrist render review",
            "fresh 300 native final frames and completed post/audio/decoding verification",
        ],
    }
    (args.output_dir / "sleeve-integration.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("IKHOR_SLEEVE_CANDIDATE_SAVED", project, report["project_sha256"], flush=True)


if __name__ == "__main__":
    main()
