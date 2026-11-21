"""Read-only delta audit: v4 versus eight sleeve bones and one fixed corrective.

Blender --background --disable-autoexec --python-exit-code 1 --python this.py --
  --source rejected-v4.blend --current repaired.blend
  --repair-report sleeve-integration.json --output new-delta-report.json

--baseline-self-check permits source == current without a repair report. It tests
the capture implementation only and never certifies a repair or collision fix.
No render, save, preference change, physics Build, or registry update occurs.
"""

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import traceback

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_ikhor_wedding as native

SOURCE_SHA = "283acdf2f1063fae32b0ed49caed07952706ff4d7b9ed1675490fa7ad021a0c1"
ALLOWED_BONES = frozenset(
    f"Bone_Sleeve{number:02d}_{side}{suffix}"
    for number in (1, 2)
    for side in ("L", "R")
    for suffix in ("", "錘")
)
ANNOTATIONS = {"ikhor_sleeve_repair", "ikhor_sleeve_repair_report"}
FRAMES = range(4139, 4442)
REFERENCE_FRAME = 4290
TARGET_MESH = "Ikhor | mesh | Ikhor_mesh"
CORRECTIVE_NAME = "Sleeve repair | L wrist flex clearance"
CORRECTIVE_PATH = 'key_blocks[' + json.dumps(CORRECTIVE_NAME) + '].value'
CORRECTIVE_KEYS = [(4210, 0), (4218, 1), (4225, 1), (4233, 0)]
PMX_SHA = "ebba744cee847c16cfe5be037e7464d4f701c8edb2f5033e7de5730bd6654a52"
CORRECTIVE_ENABLED = False
SOURCE_VERTEX_SCOPE = None
CURVE_PATTERN = re.compile(
    r'^pose\.bones\[("(?:[^"\\]|\\.)*")\]\.'
    r'(location|rotation_quaternion|rotation_euler|rotation_axis_angle|scale)$'
)
RUNTIME = {
    "rna_type", "id_data", "original", "evaluated_id", "is_evaluated",
    "users", "is_updated", "is_updated_data", "is_updated_transform",
    "is_runtime_data", "library_weak_reference", "override_library",
    "preview", "asset_data", "animation_data", "depsgraph",
}
OBJECT_SKIP = {"pose", "data", "bound_box", "users_collection", "users_scene"}
MESH_SKIP = {
    "vertices", "edges", "loops", "polygons", "uv_layers", "attributes",
    "color_attributes", "vertex_colors", "shape_keys", "materials",
    "loop_triangles", "loop_triangle_polygons", "corner_normals", "vertex_normals",
    "polygon_normals", "skin_vertices", "uv_layer_clone", "uv_layer_stencil",
}
POSE_TRANSFORMS = {
    "location", "rotation_quaternion", "rotation_euler", "rotation_axis_angle",
    "scale", "matrix", "matrix_basis", "matrix_channel",
}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def identifier(value):
    if value is None:
        return None
    if isinstance(value, bpy.types.ID):
        return {"id_type": value.bl_rna.identifier, "name": value.name,
                "library": bpy.path.abspath(value.library.filepath) if value.library else None}
    if isinstance(value, bpy.types.Node):
        return {"node": value.name}
    if isinstance(value, bpy.types.NodeSocket):
        return {"node": value.node.name, "socket": value.identifier}
    if isinstance(value, (bpy.types.Bone, bpy.types.PoseBone)):
        return {"bone": value.name}
    if isinstance(value, bpy.types.ActionGroup):
        return {"group": value.name}
    if isinstance(value, bpy.types.BoneCollection):
        return {"bone_collection": value.name}
    if isinstance(value, bpy.types.ShapeKey):
        return {"shape_key": value.name}
    return None


def plain(value):
    reference = identifier(value)
    if reference is not None:
        return reference
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if hasattr(value, "to_dict"):
        return {str(k): plain(v) for k, v in value.to_dict().items()}
    if hasattr(value, "to_list"):
        return plain(value.to_list())
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, set):
        return sorted(plain(v) for v in value)
    try:
        return [plain(v) for v in value]
    except TypeError as error:
        raise TypeError(f"Unsupported value in strict capture: {type(value).__name__}") from error


def rna(value, *, skip=(), root=False, ancestors=None):
    """Writable RNA plus owned collections; ID/target pointers stay references.

    Computed read-only scalars are excluded; explicit mesh hashes and evaluated
    frame matrices cover geometry and pose. Owned read-only collections such as
    modifiers, constraints, ramps, and driver variables are still inspected.
    """
    if value is None:
        return None
    if not root:
        reference = identifier(value)
        if reference is not None:
            return reference
    if not hasattr(value, "bl_rna"):
        return plain(value)
    ancestors = set() if ancestors is None else ancestors
    pointer = value.as_pointer() if hasattr(value, "as_pointer") else id(value)
    marker = (value.bl_rna.identifier, pointer)
    if marker in ancestors:
        return {"cycle_type": marker[0], "name": getattr(value, "name", None)}
    ancestors = ancestors | {marker}
    excluded = RUNTIME | set(skip)
    result = {"rna_type": value.bl_rna.identifier}
    for prop in value.bl_rna.properties:
        name = prop.identifier
        if name in excluded:
            continue
        if prop.type not in {"COLLECTION", "POINTER"} and prop.is_readonly:
            continue
        item = getattr(value, name)
        if prop.type == "COLLECTION":
            membership = (
                isinstance(value, bpy.types.Bone) and name == "collections"
                or isinstance(value, bpy.types.BoneCollection) and name in {"bones", "children"}
            )
            result[name] = [rna(v, root=not membership and not isinstance(v, bpy.types.ID), ancestors=ancestors) for v in item]
        elif prop.type == "POINTER":
            result[name] = rna(item, ancestors=ancestors)
        else:
            result[name] = plain(item)
    if hasattr(value, "keys") and callable(value.keys):
        custom = {}
        try:
            custom_names = list(value.keys())
        except TypeError:
            # Several RNA-owned structs expose bpy_struct.keys() but explicitly
            # do not support IDProperties. Their declared RNA was captured above.
            if isinstance(value, bpy.types.ID):
                raise
            custom_names = []
        for name in custom_names:
            if name == "_RNA_UI" or isinstance(value, bpy.types.Scene) and name in ANNOTATIONS:
                continue
            custom[name] = plain(value[name])
        result["custom_properties"] = custom
    return result


def curves(action):
    result, seen = [], set()
    for curve in getattr(action, "fcurves", ()):
        if curve.as_pointer() not in seen:
            seen.add(curve.as_pointer())
            result.append(curve)
    for layer in getattr(action, "layers", ()):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                for curve in bag.fcurves:
                    if curve.as_pointer() not in seen:
                        seen.add(curve.as_pointer())
                        result.append(curve)
    return result


def sleeve_bone(path):
    match = CURVE_PATTERN.fullmatch(path)
    if not match:
        return None
    bone = json.loads(match.group(1))
    return bone if bone in ALLOWED_BONES else None


def foreach_hash(collection, prop, kind, width=1):
    buffer = array(kind, [0]) * (len(collection) * width)
    collection.foreach_get(prop, buffer)
    return hashlib.sha256(buffer.tobytes()).hexdigest()


def curve_record(curve):
    record = rna(curve, root=True, skip={"keyframe_points", "sampled_points", "group", "driver"})
    record["group"] = rna(curve.group, root=True, skip={"channels"}) if curve.group else None
    record["key_count"] = len(curve.keyframe_points)
    record["sample_count"] = len(curve.sampled_points)
    record["key_data"] = {}
    for name, width in (("co", 2), ("handle_left", 2), ("handle_right", 2),
                        ("amplitude", 1), ("back", 1), ("period", 1)):
        record["key_data"][name] = foreach_hash(curve.keyframe_points, name, "f", width)
    for name in ("interpolation", "handle_left_type", "handle_right_type", "easing", "type"):
        record["key_data"][name] = foreach_hash(curve.keyframe_points, name, "i")
    record["samples"] = foreach_hash(curve.sampled_points, "co", "f", 2)
    if hasattr(curve, "driver"):
        record["driver"] = rna(curve.driver, root=True)
    return record


_ACTION_CACHE = {}


def action_record(action, filter_sleeves=False, filter_corrective=False):
    if action is None:
        return None
    cache_key = (action.as_pointer(), filter_sleeves, filter_corrective)
    if cache_key in _ACTION_CACHE:
        return _ACTION_CACHE[cache_key]
    records, sleeves, correctives = {}, {}, {}
    for curve in curves(action):
        key = f"{curve.data_path}|{curve.array_index}"
        if key in records or key in sleeves or key in correctives:
            raise ValueError("Duplicate Action data_path/index: " + key)
        target = (correctives if filter_corrective and curve.data_path == CORRECTIVE_PATH and curve.array_index == 0
                  else sleeves if filter_sleeves and sleeve_bone(curve.data_path) else records)
        target[key] = digest(curve_record(curve))
    result = {"curves": records, "sleeve_curves": sleeves, "corrective_curves": correctives,
              "settings": rna(action, root=True, skip={"name", "fcurves", "layers", "slots", "groups",
                                                         "frame_range", "frame_start", "frame_end"}),
              "slots": [{"target_id_type": s.target_id_type, "identifier": s.identifier} for s in action.slots]}
    result["layers"] = [
        {"settings": rna(layer, root=True, skip={"strips"}),
         "strips": [rna(strip, root=True, skip={"channelbags"}) for strip in layer.strips]}
        for layer in action.layers
    ]
    # Only the replaced Ikhor Action may have a new name. Unused Actions are not
    # inventoried: appending may legitimately drop an old zero-user Action.
    if not filter_sleeves and not filter_corrective:
        result["name"] = action.name
    _ACTION_CACHE[cache_key] = result
    return result


def animation(owner, filter_sleeves=False, filter_corrective=False):
    data = getattr(owner, "animation_data", None)
    if data is None:
        return None
    drivers = {f"{c.data_path}|{c.array_index}": digest(curve_record(c)) for c in data.drivers}
    nla = []
    for track in data.nla_tracks:
        strips = []
        for strip in track.strips:
            strips.append({"settings": rna(strip, root=True, skip={"action", "fcurves", "strips"}),
                           "action": action_record(strip.action),
                           "curves": [curve_record(c) for c in strip.fcurves]})
        nla.append({"settings": rna(track, root=True, skip={"strips"}), "strips": strips})
    action = action_record(data.action, filter_sleeves, filter_corrective)
    if action and filter_corrective:
        action = dict(action, corrective_curves={})
    return {"settings": rna(data, root=True, skip={"action", "action_slot", "nla_tracks", "drivers"}),
            "action": action, "drivers": drivers, "nla": nla}


def target_mesh():
    mesh = bpy.data.objects.get(TARGET_MESH)
    if not mesh or mesh.type != "MESH" or mesh.get("performer_id") != "ikhor":
        raise ValueError("Missing exact original Ikhor target mesh")
    if len(mesh.data.vertices) != 29959 or not mesh.data.shape_keys:
        raise ValueError("Unexpected original Ikhor topology/shape-key owner")
    return mesh


def source_vertex_scope():
    """Reconstruct all allowed indices from the pinned SOURCE, never the report."""
    obj = target_mesh()
    groups = {g.index: g.name for g in obj.vertex_groups}
    left_groups = {"Bone_Sleeve01_L", "Bone_Sleeve02_L"}
    if not left_groups <= set(groups.values()):
        raise ValueError("Missing source left sleeve weight groups")
    left_positive, left_threshold, all_sleeve = [], [], []
    micro = []
    for v in obj.data.vertices:
        left = sum(g.weight for g in v.groups if groups[g.group] in left_groups)
        if left > 0:
            left_positive.append(v.index)
        if left > 0.001:
            left_threshold.append(v.index)
        if 0 < left <= 0.001:
            micro.append({"vertex": v.index, "sum_weight": left})
        if any(g.weight > 0 and groups[g.group] in ALLOWED_BONES for g in v.groups):
            all_sleeve.append(v.index)
    if len(left_positive) != 573 or left_positive != left_threshold:
        raise ValueError("Pinned left sleeve must independently rebuild exactly the same 573 vertices at >0 and >0.001")
    return {"mesh": obj.name, "vertex_count": len(obj.data.vertices),
            "base_topology_sha256": foreach_hash(obj.data.loops, "vertex_index", "i"),
            "left_groups": sorted(left_groups), "left_positive": left_positive,
            "left_sum_gt_0_001": left_threshold, "micro_weight_vertices": micro,
            "all_eight_sleeve_positive": all_sleeve,
            "all_eight_sleeve_positive_count": len(all_sleeve),
            "left_indices_sha256": digest(left_positive), "all_sleeve_indices_sha256": digest(all_sleeve)}


def geometry_record(obj):
    record = native.geometry(obj)
    if CORRECTIVE_ENABLED and obj.name == TARGET_MESH:
        record["shapes"].pop(CORRECTIVE_NAME, None)
        record["shape_action"] = animation(obj.data.shape_keys, filter_corrective=True)
    return record


def node_tree(tree):
    if tree is None:
        return None
    nodes = {}
    for node in tree.nodes:
        nodes[node.name] = {
            "settings": rna(node, root=True, skip={"inputs", "outputs", "internal_links"}),
            "inputs": [rna(s, root=True, skip={"node", "links"}) for s in node.inputs],
            "outputs": [rna(s, root=True, skip={"node", "links"}) for s in node.outputs],
            "internal_links": [(l.from_socket.identifier, l.to_socket.identifier) for l in node.internal_links],
        }
    return {"settings": rna(tree, root=True, skip={"nodes", "links", "interface"}),
            "interface": rna(tree.interface, root=True) if tree.interface else None,
            "nodes": nodes,
            "links": sorted((l.from_node.name, l.from_socket.identifier,
                             l.to_node.name, l.to_socket.identifier, l.is_muted) for l in tree.links),
            "animation": animation(tree)}


def attributes(mesh):
    result = {}
    for attribute in mesh.attributes:
        values = {}
        if attribute.data:
            for prop in attribute.data[0].bl_rna.properties:
                if prop.identifier == "rna_type" or prop.type not in {"BOOLEAN", "INT", "FLOAT", "ENUM"}:
                    continue
                width = prop.array_length if prop.is_array else 1
                values[prop.identifier] = foreach_hash(attribute.data, prop.identifier,
                                                       "f" if prop.type == "FLOAT" else "i", width)
        result[attribute.name] = {"settings": rna(attribute, root=True, skip={"data"}),
                                  "count": len(attribute.data), "data": values}
    return result


def fixed_frame():
    for scene in bpy.data.scenes:
        scene.frame_set(REFERENCE_FRAME)
    bpy.context.view_layer.update()


def ikhor_arm():
    matches = [o for o in bpy.context.scene.objects if o.type == "ARMATURE" and o.get("performer_id") == "ikhor"]
    if len(matches) != 1:
        raise ValueError("Expected exactly one active Ikhor armature")
    arm = matches[0]
    if not ALLOWED_BONES <= set(arm.pose.bones.keys()):
        raise ValueError("The fixed eight sleeve bone names are not all present")
    return arm


def capture_static():
    fixed_frame()
    arm = ikhor_arm()
    user_map = bpy.data.user_map()
    # A save may purge source zero-user remnants. Only node groups/images with
    # no fake user AND no reverse ID reference can qualify, independently of
    # the producer report. Retained blocks remain byte/settings strict.
    removable_orphans = {"nodes": {}, "images": {}}
    for category, blocks in (("nodes", bpy.data.node_groups), ("images", bpy.data.images)):
        for block in blocks:
            referrers = sorted((identifier(i) for i in user_map.get(block, set())),
                               key=lambda i: (i["id_type"], i["name"]))
            if block.users == 0 and not block.use_fake_user and not referrers:
                removable_orphans[category][block.name] = {
                    "users": 0, "fake_user": False, "reverse_id_references": [],
                    "reason": "Unreferenced source datablock may be purged by Save As; no output graph can reach it.",
                }
    result = {"objects": {}, "meshes": {}, "armatures": {}, "materials": {}, "nodes": {},
              "lights": {}, "cameras": {}, "curves": {}, "worlds": {}, "scenes": {},
              "collections": {}, "images": {}, "sounds": {}, "other_data": {}}
    for obj in bpy.data.objects:
        is_target = obj == arm
        record = {"settings": rna(obj, root=True, skip=OBJECT_SKIP),
                  "data": identifier(obj.data), "animation": animation(obj, is_target)}
        if obj.type == "ARMATURE":
            record["pose"] = {b.name: rna(b, root=True, skip=POSE_TRANSFORMS if is_target and b.name in ALLOWED_BONES else ())
                              for b in obj.pose.bones}
        result["objects"][obj.name] = digest(record)
    print("IKHOR_SLEEVE_DELTA_STATIC_OBJECTS", len(result["objects"]), flush=True)
    for mesh in bpy.data.meshes:
        owners = [o for o in bpy.data.objects if o.type == "MESH" and o.data == mesh]
        filter_corrective = CORRECTIVE_ENABLED and any(o.name == TARGET_MESH for o in owners)
        record = {"settings": rna(mesh, root=True, skip=MESH_SKIP), "attributes": attributes(mesh),
                  "geometry_by_owner": {o.name: geometry_record(o) for o in owners},
                  "edges": foreach_hash(mesh.edges, "vertices", "i", 2),
                  "polygon_ranges": {n: foreach_hash(mesh.polygons, n, "i") for n in ("loop_start", "loop_total", "use_smooth")},
                  "uv_settings": [rna(layer, root=True, skip={"data", "uv", "vertex_selection", "edge_selection", "pin"}) for layer in mesh.uv_layers],
                  "materials": [identifier(m) for m in mesh.materials], "animation": animation(mesh)}
        if mesh.shape_keys:
            retained_keys = [k for k in mesh.shape_keys.key_blocks if not (filter_corrective and k.name == CORRECTIVE_NAME)]
            record["key_settings"] = rna(mesh.shape_keys, root=True, skip={"key_blocks"})
            record["key_blocks"] = [rna(k, root=True, skip={"data"}) for k in retained_keys]
            record["key_coordinates"] = {k.name: foreach_hash(k.data, "co", "f", 3) for k in retained_keys}
            record["key_animation"] = animation(mesh.shape_keys, filter_corrective=filter_corrective)
        result["meshes"][mesh.name] = digest(record)
    print("IKHOR_SLEEVE_DELTA_STATIC_MESHES", len(result["meshes"]), flush=True)
    for group_name in ("armatures", "lights", "cameras", "curves", "worlds", "scenes", "collections"):
        for item in getattr(bpy.data, group_name):
            skip = {"node_tree", "compositing_node_group"}
            if group_name == "scenes":
                skip |= {"frame_current", "frame_subframe", "frame_current_final"}
            record = {"settings": rna(item, root=True, skip=skip), "animation": animation(item)}
            if group_name == "scenes":
                record["root_collection"] = rna(item.collection, root=True)
            if hasattr(item, "node_tree") and item.node_tree:
                record["nodes"] = node_tree(item.node_tree)
            if group_name == "scenes" and item.compositing_node_group:
                record["compositor"] = node_tree(item.compositing_node_group)
            result[group_name][item.name] = digest(record)
    for material in bpy.data.materials:
        result["materials"][material.name] = digest({"settings": rna(material, root=True, skip={"node_tree"}),
                                                    "nodes": node_tree(material.node_tree), "animation": animation(material)})
    print("IKHOR_SLEEVE_DELTA_STATIC_MATERIALS", len(result["materials"]), flush=True)
    for tree in bpy.data.node_groups:
        result["nodes"][tree.name] = digest(node_tree(tree))
    for image in bpy.data.images:
        result["images"][image.name] = digest({
            "payload": native.image_record(image),
            "settings": rna(image, root=True, skip={"filepath", "filepath_raw", "pixels", "packed_file", "packed_files"}),
            "animation": animation(image),
        })
    for sound in bpy.data.sounds:
        packed = sound.packed_file
        path = str(Path(bpy.path.abspath(sound.filepath)).resolve())
        result["sounds"][sound.name] = digest({"settings": rna(sound, root=True, skip={"filepath", "packed_file"}),
                                              "path": path, "packed": bool(packed),
                                              "sha256": hashlib.sha256(bytes(packed.data)).hexdigest() if packed else native.sha(path)})
    for group_name in ("textures", "metaballs", "lattices", "speakers", "volumes"):
        result["other_data"][group_name] = {i.name: digest(rna(i, root=True)) for i in getattr(bpy.data, group_name)}
    result["sound_strips"] = native.sound_capture()
    result["scene_contract"] = native.scene_contract()
    filtered_action = action_record(arm.animation_data.action, True)
    # These are compared separately: filtering only eight transform curves must
    # never hide a geometry/constraint/material/object edit.
    target_animation = animation(arm, True)
    target_animation["action"] = dict(filtered_action, sleeve_curves={})
    result["target_animation_without_sleeves"] = target_animation
    record = {"settings": rna(arm, root=True, skip=OBJECT_SKIP), "data": identifier(arm.data),
              "animation": target_animation,
              "pose": {b.name: rna(b, root=True, skip=POSE_TRANSFORMS if b.name in ALLOWED_BONES else ()) for b in arm.pose.bones}}
    result["objects"][arm.name] = digest(record)
    return result, filtered_action, arm.name, removable_orphans


def evaluated_non_sleeve():
    obj = target_mesh()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        if len(mesh.vertices) != SOURCE_VERTEX_SCOPE["vertex_count"]:
            raise ValueError("Evaluated body vertex correspondence changed after disabling only outline")
        if foreach_hash(mesh.loops, "vertex_index", "i") != SOURCE_VERTEX_SCOPE["base_topology_sha256"]:
            raise ValueError("Evaluated body topology no longer proves original vertex correspondence")
        coords = array("f", [0]) * (3 * len(mesh.vertices))
        mesh.vertices.foreach_get("co", coords)
        excluded = set(SOURCE_VERTEX_SCOPE["all_eight_sleeve_positive"])
        selected = array("f", (coords[3 * i + axis] for i in range(len(mesh.vertices))
                               if i not in excluded for axis in range(3)))
        return {"vertex_count": len(mesh.vertices), "compared_vertex_count": len(selected) // 3,
                "sha256": hashlib.sha256(selected.tobytes()).hexdigest(),
                "finite": all(math.isfinite(v) for v in selected)}
    finally:
        evaluated.to_mesh_clear()


def frame_state():
    arm = ikhor_arm()
    matrices, morphs = array("d"), array("d")
    labels, morph_labels = [], []
    for obj in sorted(bpy.context.scene.objects, key=lambda o: o.name):
        labels.append("object:" + obj.name)
        matrices.extend(v for row in obj.matrix_world for v in row)
        if obj.type == "ARMATURE":
            for bone in sorted(obj.pose.bones, key=lambda b: b.name):
                if obj == arm and bone.name in ALLOWED_BONES:
                    continue
                labels.append(obj.name + ":bone:" + bone.name)
                matrices.extend(v for row in bone.matrix for v in row)
        if obj.type == "MESH" and obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:
                if CORRECTIVE_ENABLED and obj.name == TARGET_MESH and key.name == CORRECTIVE_NAME:
                    continue
                morph_labels.append(obj.name + ":" + key.name)
                morphs.append(key.value)
    corrective = target_mesh().data.shape_keys.key_blocks.get(CORRECTIVE_NAME)
    value = corrective.value if CORRECTIVE_ENABLED and corrective else None
    if value is not None and not math.isfinite(value):
        raise ValueError("Non-finite corrective value")
    return labels, matrices, morph_labels, morphs, evaluated_non_sleeve(), value


def capture_frames():
    scene, result = bpy.context.scene, {}
    outlines = [m for m in target_mesh().modifiers if m.name == "mmd_edge_preview" and m.type == "SOLIDIFY"]
    if len(outlines) != 1:
        raise ValueError("Expected exactly the original mmd_edge_preview Solidify")
    states = [(m, m.show_viewport, m.show_render) for m in outlines]
    try:
        for modifier, _, _ in states:
            modifier.show_viewport = modifier.show_render = False
        for frame in FRAMES:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            result[frame] = frame_state()
            if (frame - FRAMES.start) % 50 == 0:
                print("IKHOR_SLEEVE_DELTA_FRAME", frame, flush=True)
    finally:
        for modifier, viewport, render in states:
            modifier.show_viewport, modifier.show_render = viewport, render
        bpy.context.view_layer.update()
    return result


def compare_frames(source, current, check, report):
    records, geometry_records, corrective_values = [], [], []
    for frame in FRAMES:
        a, b = source[frame], current[frame]
        same_labels = a[0] == b[0] and a[2] == b[2]
        matrices_equal, morphs_equal = a[1] == b[1], a[3] == b[3]
        finite = all(math.isfinite(v) for v in b[1]) and all(math.isfinite(v) for v in b[3])
        matrix_error = max((abs(x - y) for x, y in zip(a[1], b[1])), default=0) if same_labels and finite else None
        morph_error = max((abs(x - y) for x, y in zip(a[3], b[3])), default=0) if same_labels and finite else None
        item = {"frame": frame, "same_identities": same_labels, "matrix_max_error": matrix_error,
                "morph_max_error": morph_error, "passed": same_labels and matrices_equal and morphs_equal and finite,
                "matrix_sha256": hashlib.sha256(b[1].tobytes()).hexdigest(),
                "morph_sha256": hashlib.sha256(b[3].tobytes()).hexdigest()}
        records.append(item)
        geometry_records.append({"frame": frame, "source": a[4], "current": b[4],
                                 "passed": a[4] == b[4] and a[4]["finite"] and b[4]["finite"]})
        if CORRECTIVE_ENABLED:
            corrective_values.append({"frame": frame, "value": b[5]})
    report["non_sleeve_303_frames"] = records
    check("303 frames: strict non-sleeve matrices and all Morphs", all(r["passed"] for r in records),
          {"frames": [FRAMES.start, FRAMES.stop - 1], "count": len(records), "tolerance": 0.0,
           "failed_frames": [r for r in records if not r["passed"]][:20]})
    report["non_sleeve_303_evaluated_body_frames"] = geometry_records
    check("303 frames: exact evaluated body positions outside source eight-bone weight support",
          all(r["passed"] for r in geometry_records),
          {"count": len(geometry_records), "tolerance": 0.0,
           "failed_frames": [r["frame"] for r in geometry_records if not r["passed"]],
           "audit_only_modifier_change": "Both copies temporarily disable original mmd_edge_preview Solidify; restore flags, never save.",
           "outline_settings_compared_separately": True})
    if CORRECTIVE_ENABLED:
        report["corrective_303_values"] = corrective_values
        bounded = all(r["value"] is not None and 0 <= r["value"] <= 1 for r in corrective_values)
        outside = all(r["value"] == 0 for r in corrective_values if r["frame"] <= 4210 or r["frame"] >= 4233)
        plateau = all(r["value"] == 1 for r in corrective_values if 4218 <= r["frame"] <= 4225)
        up = [r["value"] for r in corrective_values if 4210 <= r["frame"] <= 4218]
        down = [r["value"] for r in corrective_values if 4225 <= r["frame"] <= 4233]
        monotone = bounded and all(a <= b for a, b in zip(up, up[1:])) and all(a >= b for a, b in zip(down, down[1:]))
        check("fixed corrective stays bounded with monotone entry/exit and zero outside 4210-4233",
              bounded and outside and plateau and monotone)


def verify_corrective(data, proof, check, report):
    """An exact fixed-shape exception, not a producer-controlled whitelist."""
    obj = target_mesh()
    keys, basis = obj.data.shape_keys, obj.data.shape_keys.reference_key
    check("corrective data independently bound to original v4 and original PMX",
          data.get("baseline_blend_sha256") == SOURCE_SHA
          and data.get("source_pmx_sha256") == PMX_SHA and data.get("vertex_count") == 29959
          and data.get("mesh_object") == TARGET_MESH)
    check("corrective actor provenance equals integration's SHA-bound repair actor",
          data.get("actor_source_sha256") == (proof.get("actor_candidate_sha256") or proof.get("actor_sha256"))
          and Path(data.get("actor_source", "")).resolve() == Path(proof.get("actor_candidate") or proof.get("actor") or "").resolve())
    prototype = Path(data.get("prototype_report", ""))
    check("fixed unsaved prototype evidence bytes unchanged",
          prototype.is_file() and data.get("prototype_report_sha256") == native.sha(prototype))
    items = data.get("shapes", [])
    check("exactly one fixed left corrective, never a report-expanded shape whitelist",
          len(items) == 1 and items[0].get("name") == CORRECTIVE_NAME and items[0].get("side") == "L")
    if len(items) != 1 or items[0].get("name") != CORRECTIVE_NAME or items[0].get("side") != "L":
        raise ValueError("Refusing an expanded corrective definition")
    item = items[0]
    key = keys.key_blocks.get(CORRECTIVE_NAME)
    if key is None:
        raise ValueError("Missing the single approved corrective")
    allowed = set(SOURCE_VERTEX_SCOPE["left_positive"])
    indices = [d["index"] for d in item["deltas"]]
    valid_indices = len(indices) == len(set(indices)) and set(indices) <= allowed
    check("corrective indices are inside independently rebuilt 573 source vertices", valid_indices,
          {"submitted_count": len(indices), "source_count": len(allowed),
           "outside": sorted(set(indices) - allowed), "source_indices_sha256": digest(sorted(allowed))})
    if not valid_indices:
        raise ValueError("Out-of-scope corrective vertex")
    expected, original, actual = (array("f", [0]) * (3 * len(basis.data)) for _ in range(3))
    basis.data.foreach_get("co", original)
    check("corrective data Basis fingerprint equals actual unchanged Basis",
          data.get("basis_position_sha256") == hashlib.sha256(original.tobytes()).hexdigest())
    expected[:] = original
    maximum_submitted = 0
    for entry in item["deltas"]:
        delta = entry["delta"]
        if len(delta) != 3 or not all(math.isfinite(v) for v in delta):
            raise ValueError("Invalid corrective vector")
        maximum_submitted = max(maximum_submitted, math.sqrt(sum(v * v for v in delta)))
        for axis, value in enumerate(delta):
            expected[3 * entry["index"] + axis] += value
    key.data.foreach_get("co", actual)
    changed, outside, maximum_actual = [], [], 0
    for i in range(len(basis.data)):
        delta = [actual[3 * i + a] - original[3 * i + a] for a in range(3)]
        if any(delta):
            changed.append(i)
            if i not in allowed:
                outside.append(i)
            maximum_actual = max(maximum_actual, math.sqrt(sum(v * v for v in delta)))
    report["corrective_static"] = {
        "name": key.name, "settings": rna(key, root=True, skip={"data"}),
        "changed_vertex_count": len(changed), "changed_vertices": changed,
        "outside_source_573": outside, "maximum_rest_delta_m": maximum_actual,
        "submitted_maximum_rest_delta_m": maximum_submitted,
        "actual_coordinates_sha256": hashlib.sha256(actual.tobytes()).hexdigest(),
        "expected_coordinates_sha256": hashlib.sha256(expected.tobytes()).hexdigest(),
    }
    check("new corrective coordinates exactly equal SHA-bound vectors on 573 source vertices",
          actual == expected and bool(changed) and not outside and maximum_submitted <= 0.03)
    check("new corrective uses unmodified Basis with unrestricted original vertex weights",
          key.relative_key == basis and key.vertex_group == "" and not key.mute
          and key.slider_min == 0 and key.slider_max == 1 and keys.use_relative)
    current_curves = [c for c in curves(keys.animation_data.action)
                      if c.data_path == CORRECTIVE_PATH and c.array_index == 0]
    if len(current_curves) != 1:
        raise ValueError("Expected exactly one new fixed shape.value curve")
    curve = current_curves[0]
    expected_keys = item.get("keys", [])
    check("corrective exact fixed four-key window", [(k.get("frame"), k.get("value")) for k in expected_keys] == CORRECTIVE_KEYS)
    matches = len(curve.keyframe_points) == len(expected_keys) == 4
    for point, wanted in zip(curve.keyframe_points, expected_keys):
        matches = matches and list(point.co) == list(array("f", [wanted["frame"], wanted["value"]]))
        matches = matches and all(getattr(point, name) == wanted[name]
                                  for name in ("interpolation", "handle_left_type", "handle_right_type"))
        matches = matches and all(list(getattr(point, name)) == list(array("f", wanted[name]))
                                  for name in ("handle_left", "handle_right"))
    check("corrective curve and handles exactly match SHA-bound smooth definition",
          matches and curve.extrapolation == "CONSTANT" and not curve.mute and not curve.modifiers,
          {"data_path": curve.data_path, "record_sha256": digest(curve_record(curve))})


def main():
    global CORRECTIVE_ENABLED, SOURCE_VERTEX_SCOPE
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "current", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--repair-report", type=Path)
    parser.add_argument("--baseline-self-check", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.output.exists():
        raise FileExistsError(args.output)
    if not args.baseline_self_check and args.repair_report is None:
        parser.error("--repair-report is required for a candidate audit")
    report = {"source": str(args.source), "current": str(args.current), "checks": [], "errors": [],
              "allowed_bones": sorted(ALLOWED_BONES), "baseline_self_check": args.baseline_self_check,
              "read_only": True, "rendered": False, "project_saved": False, "preferences_changed": False,
              "geometry_collision_certified": False, "user_art_approval": False}

    def check(name, passed, details=None):
        report["checks"].append({"name": name, "passed": bool(passed), "details": details})

    try:
        report["source_sha256"], report["project_sha256"] = native.sha(args.source), native.sha(args.current)
        report["audit_script_sha256"] = native.sha(__file__)
        check("pinned rejected v4 SHA256", report["source_sha256"] == SOURCE_SHA)
        if report["source_sha256"] != SOURCE_SHA:
            raise ValueError("Refusing an unpinned source")
        baseline_path = args.source.parent / "master-verification.json"
        baseline = read(baseline_path)
        check("v4 original 1049-check technical report is SHA-bound",
              baseline.get("passed") is True and len(baseline.get("checks", [])) == 1049
              and all(c.get("passed") is True for c in baseline["checks"])
              and baseline.get("project_sha256") == SOURCE_SHA,
              {"path": str(baseline_path), "sha256": native.sha(baseline_path)})
        proof, actor_actions, corrective_data = {}, None, None
        if args.baseline_self_check:
            check("self-check uses exact same file", report["project_sha256"] == SOURCE_SHA)
        else:
            proof = read(args.repair_report)
            report["repair_report"] = str(args.repair_report)
            report["repair_report_sha256"] = native.sha(args.repair_report)
            check("repair evidence source bound to v4", (proof.get("source_v4_sha256") or proof.get("source_sha256")) == SOURCE_SHA)
            check("repair evidence bound to actual final SHA", proof.get("project_sha256") == report["project_sha256"])
            check("repair evidence identifies actual final path", Path(proof.get("project", "")).resolve() == args.current.resolve())
            check("candidate differs from rejected v4", report["project_sha256"] != SOURCE_SHA)
            if "allowed_bones" in proof:
                check("evidence cannot widen fixed eight-bone whitelist", set(proof["allowed_bones"]) == ALLOWED_BONES)
            actor = Path(proof.get("actor_candidate") or proof.get("actor") or "")
            actor_sha = proof.get("actor_candidate_sha256") or proof.get("actor_sha256")
            check("repair actor source is SHA-bound", actor.is_file() and actor_sha == native.sha(actor),
                  {"actor": str(actor), "sha256": actor_sha})
            if proof.get("repair_report_sha256"):
                nested = Path(proof["repair_report"])
                check("producer's solver evidence bytes unchanged", nested.is_file() and native.sha(nested) == proof["repair_report_sha256"])
            if proof.get("corrective_data"):
                corrective_path = Path(proof["corrective_data"])
                report["corrective_data"] = str(corrective_path)
                report["corrective_data_sha256"] = native.sha(corrective_path)
                check("corrective definition bytes bound by final integration report",
                      proof.get("corrective_data_sha256") == report["corrective_data_sha256"])
                corrective_data = read(corrective_path)
                CORRECTIVE_ENABLED = True
            if actor.is_file():
                native.reopen(actor)
                _ACTION_CACHE.clear()
                source_action_name = proof.get("source_action") or proof.get("action") or proof.get("applied_action")
                actor_action = bpy.data.actions.get(source_action_name)
                actor_actions = {source_action_name: action_record(actor_action, True)} if actor_action else {}
        native.reopen(args.source)
        _ACTION_CACHE.clear()
        SOURCE_VERTEX_SCOPE = source_vertex_scope()
        report["independently_rebuilt_source_vertex_scope"] = SOURCE_VERTEX_SCOPE
        check("source v4 has no added corrective shape", CORRECTIVE_NAME not in target_mesh().data.shape_keys.key_blocks)
        report["allowed_corrective_shapes"] = [CORRECTIVE_NAME] if CORRECTIVE_ENABLED else []
        report["audit_only_outline_disable_for_vertex_correspondence"] = True
        source, old_action, arm_name, source_orphans = capture_static()
        print("IKHOR_SLEEVE_DELTA_SOURCE_STATIC", flush=True)
        source_frames = capture_frames()
        native.reopen(args.current)
        _ACTION_CACHE.clear()
        current, new_action, current_arm, _ = capture_static()
        print("IKHOR_SLEEVE_DELTA_CURRENT_STATIC", flush=True)
        check("same Ikhor armature", current_arm == arm_name)
        report["permitted_unreferenced_source_datablock_removals"] = {}
        for category in source:
            equal = source[category] == current.get(category)
            details = None
            if not equal and isinstance(source[category], dict) and isinstance(current.get(category), dict):
                a, b = source[category], current[category]
                missing, added = sorted(a.keys() - b.keys()), sorted(b.keys() - a.keys())
                changed = sorted(n for n in a.keys() & b.keys() if a[n] != b[n])
                permitted = {n: dict(source_orphans[category][n], source_capture_sha256=a[n])
                             for n in missing if n in source_orphans.get(category, {})}
                forbidden_missing = [n for n in missing if n not in permitted]
                equal = not forbidden_missing and not added and not changed
                details = {"missing": missing, "added": added, "changed": changed,
                           "forbidden_missing": forbidden_missing, "permitted_source_orphan_removals": permitted}
                if permitted:
                    report["permitted_unreferenced_source_datablock_removals"][category] = permitted
            check("unchanged " + category, equal, details)
        report["source_static_sha256"], report["current_static_sha256"] = digest(source), digest(current)
        report["retained_action_curves"] = {
            "source_count": len(old_action["curves"]), "current_count": len(new_action["curves"]),
            "changed": sorted(k for k in old_action["curves"].keys() | new_action["curves"].keys()
                              if old_action["curves"].get(k) != new_action["curves"].get(k))[:50],
            "source_settings": old_action["settings"], "current_settings": new_action["settings"],
            "source_slots": old_action["slots"], "current_slots": new_action["slots"],
        }
        changed = sorted(k for k in old_action["sleeve_curves"].keys() | new_action["sleeve_curves"].keys()
                         if old_action["sleeve_curves"].get(k) != new_action["sleeve_curves"].get(k))
        report["changed_allowed_sleeve_curves"] = changed
        report["changed_allowed_bones"] = sorted({sleeve_bone(k.rsplit("|", 1)[0]) for k in changed})
        if not args.baseline_self_check:
            check("at least one allowed sleeve transform curve changed", bool(changed))
            name = ikhor_arm().animation_data.action.name
            check("producer names current active repair Action", (proof.get("action") or proof.get("applied_action")) == name, name)
            source_action = proof.get("source_action") or proof.get("action") or proof.get("applied_action")
            check("current full Action equals SHA-bound repair actor Action",
                  bool(actor_actions) and actor_actions.get(source_action) == new_action,
                  {"actor_action": source_action, "current_action": name})
        annotations = {s.name: {k: plain(s[k]) for k in ANNOTATIONS if k in s} for s in bpy.data.scenes}
        check("only allowed scene annotations are strings", all(isinstance(v, str) and len(v) <= 4096 for a in annotations.values() for v in a.values()), annotations)
        if CORRECTIVE_ENABLED:
            verify_corrective(corrective_data, proof, check, report)
        compare_frames(source_frames, capture_frames(), check, report)
        check("source file bytes unchanged", native.sha(args.source) == report["source_sha256"])
        check("current file bytes unchanged", native.sha(args.current) == report["project_sha256"])
        if args.repair_report:
            check("repair report bytes unchanged", native.sha(args.repair_report) == report["repair_report_sha256"])
        if CORRECTIVE_ENABLED:
            check("corrective definition bytes unchanged", native.sha(report["corrective_data"]) == report["corrective_data_sha256"])
    except Exception as error:
        report["errors"].append({"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
    report["failed_checks"] = [c for c in report["checks"] if not c["passed"]]
    report["passed"] = bool(report["checks"]) and not report["failed_checks"] and not report["errors"]
    report["delta_verified"] = report["passed"] and not args.baseline_self_check
    report["limits"] = [
        "Exact data/curve and 303-frame non-sleeve audit only; sleeve/skin intersection needs separate geometric and continuous image evidence.",
        "The eight fixed sibling sleeve bones may deform only their original weight support; Basis, UV, weights and all original shapes stay strict. One named left corrective is permitted only on 573 independently rebuilt source sleeve vertices with SHA-bound vectors and a fixed four-key window.",
        "Only Ikhor's active Action name and two bounded scene annotation properties are permitted metadata exceptions; orphan Action counts are ignored.",
        "Source node groups/images may disappear only when independently zero-user, without fake user or reverse ID references; retained data and all reachable graphs remain strict.",
        "The target ShapeKey Action may acquire a copied name only when the one fixed corrective is declared; all original shape curves, handles, Action settings/layers/slots and original Morph values remain exact.",
        "The original 1049-check report certifies its pinned v4 technical state, not an absence of sleeve penetration or final artistic acceptance.",
        "No full-song physical or artistic validation is implied.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print("IKHOR_SLEEVE_DELTA_VERIFIED", json.dumps({"passed": report["passed"], "delta_verified": report["delta_verified"],
          "checks": len(report["checks"]), "failed": report["failed_checks"], "errors": report["errors"], "output": str(args.output)}, ensure_ascii=True), flush=True)
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
