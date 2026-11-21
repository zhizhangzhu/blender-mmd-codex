"""Pinned Blender worker for a new, bounded still candidate and its reopen.

The launcher owns authorization and the closed iteration. This worker accepts
only exact node-input, light-energy and Glare bypass controls. It never calls
historical production entry points and evaluates only frame 4290.
"""

import argparse
from array import array
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import studio_scene_contract as contract
from scripts import studio_scene_worker as bench

FRAME = 4290
ALLOWED = {"node_input", "light_energy", "glow_bypass"}
_FIELD_TABLES = {}
_PROGRESS_DIR = None
_PROGRESS_STARTED = None
_ACTION_COUNTS = {}


def progress(event, **details):
    record = {"event": event, "utc": datetime.now(timezone.utc).isoformat(), **details}
    if _PROGRESS_STARTED is not None:
        record["elapsed_seconds"] = round(time.perf_counter() - _PROGRESS_STARTED, 4)
    line = json.dumps(record, ensure_ascii=False, allow_nan=False)
    print("STUDIO_PUBLISH_PROGRESS", line, flush=True)
    if _PROGRESS_DIR is not None:
        with (_PROGRESS_DIR / "progress.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def plain(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        need(math.isfinite(value), "Nonfinite RNA value in protection record")
        return value
    if isinstance(value, bpy.types.ID):
        return {"id": value.name_full, "type": value.bl_rna.identifier,
                "library": value.library.filepath if value.library else None}
    if hasattr(value, "bl_rna"):
        # RNA substructures stringify with process-local memory addresses.
        # Their identity is stable by owner/path; editable nested settings are
        # captured explicitly by the containing record below.
        try:
            path = value.path_from_id()
        except (AttributeError, ValueError, TypeError):
            path = None
        owner = getattr(value, "id_data", None)
        return {"rna": value.bl_rna.identifier, "path": path,
                "name": getattr(value, "name", None),
                "owner": plain(owner) if isinstance(owner, bpy.types.ID) else None}
    if hasattr(value, "to_dict"):
        return {str(k): plain(v) for k, v in value.to_dict().items()}
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(plain(v) for v in value)
    try:
        return [plain(v) for v in value]
    except TypeError:
        return str(value)


def custom(owner):
    if not hasattr(owner, "keys"):
        return {}
    try:
        keys = owner.keys()
    except TypeError as exc:
        # Some Blender RNA substructures expose keys() but do not support
        # IDProperties. Geometry Nodes modifiers that do support them still
        # take the normal complete path; unrelated TypeErrors remain errors.
        if str(exc) == "bpy_struct.keys(): this type doesn't support IDProperties":
            return {}
        raise
    return {key: plain(owner[key]) for key in keys}


def rna(owner, skip=()):
    """Stored writable scalar/array/pointer settings, excluding UI/runtime RNA."""
    if owner is None:
        return None
    result = {}
    for prop in owner.bl_rna.properties:
        key = prop.identifier
        if key in skip or key == "rna_type" or prop.is_readonly or prop.type == "COLLECTION":
            continue
        result[key] = plain(getattr(owner, key))
    return result


def field_table(item):
    """Inspect each RNA item type once; retain every writable stored field.

    No Keyframe aliases or selection flags are silently discarded. In
    particular, co_ui is retained when exposed as writable RNA, alongside co
    and both handles. Read-only RNA is omitted by the same contract as rna().
    Unexpected pointer/collection fields fail explicitly rather than becoming
    an incomplete successful action fingerprint.
    """
    key = item.bl_rna.identifier
    if key not in _FIELD_TABLES:
        fields = []
        for prop in item.bl_rna.properties:
            name = prop.identifier
            if name == "rna_type" or (prop.is_readonly and name not in {"co", "handle_left", "handle_right"}):
                continue
            need(prop.type in {"FLOAT", "INT", "BOOLEAN", "ENUM", "STRING"},
                 "Unsupported writable protected " + key + "." + name + ": " + prop.type)
            is_array = bool(getattr(prop, "is_array", False))
            width = prop.array_length if is_array else 1
            need(width >= 1, "Unsupported dynamic protected array: " + key + "." + name)
            record = {"name": name, "type": prop.type, "width": width}
            if prop.type == "ENUM":
                need(not is_array and not prop.is_enum_flag,
                     "Unsupported protected enum array/flags: " + key + "." + name)
                record["enum"] = {entry.identifier: entry.value for entry in prop.enum_items}
                need(bool(record["enum"]), "Dynamic protected enum needs explicit handling: " + key + "." + name)
            fields.append(record)
        _FIELD_TABLES[key] = fields
    return key, _FIELD_TABLES[key]


def collection_record(collection):
    """Column hashes keep full keys/handles with bounded per-curve memory."""
    count = len(collection)
    if not count:
        return {"count": 0, "fields": []}
    kind, fields = field_table(collection[0])
    columns = []
    for field in fields:
        name, field_type, width = field["name"], field["type"], field["width"]
        if field_type in {"FLOAT", "INT", "BOOLEAN"}:
            code = {"FLOAT": "f", "INT": "i", "BOOLEAN": "b"}[field_type]
            values = array(code, [0]) * (count * width)
            try:
                collection.foreach_get(name, values)
            except (TypeError, RuntimeError, AttributeError):
                # Some custom RNA numeric aliases do not implement foreach.
                # Include their complete values rather than dropping them.
                values = array(code)
                for item in collection:
                    value = getattr(item, name)
                    values.extend(value if width > 1 else (value,))
            hashed = hashlib.sha256(values.tobytes()).hexdigest()
        elif field_type == "ENUM":
            codes = field["enum"]
            values = array("i")
            for item in collection:
                actual = getattr(item, name)
                need(actual in codes, "Unknown protected enum value: " + kind + "." + name)
                values.append(codes[actual])
            hashed = hashlib.sha256(values.tobytes()).hexdigest()
        else:
            hasher = hashlib.sha256()
            for item in collection:
                value = getattr(item, name).encode("utf-8")
                hasher.update(len(value).to_bytes(8, "little"))
                hasher.update(value)
            hashed = hasher.hexdigest()
        columns.append({**field, "sha256": hashed})
    return {"rna": kind, "count": count, "fields": columns}


def curve_record(curve):
    return {"settings": rna(curve), "keys": collection_record(curve.keyframe_points),
            "samples": collection_record(curve.sampled_points),
            "modifiers": [rna(m) for m in curve.modifiers]}


def actions_record():
    global _ACTION_COUNTS
    _ACTION_COUNTS = {"actions": len(bpy.data.actions), "unique_curves": 0,
                      "keys": 0, "sample_points": 0, "curve_aliases": 0}
    result = {}
    seen = {}
    next_progress = 100000

    def unique_curve(fc):
        nonlocal next_progress
        pointer = fc.as_pointer()
        if pointer in seen:
            _ACTION_COUNTS["curve_aliases"] += 1
            return {"alias_of_curve": seen[pointer]}
        seen[pointer] = len(seen)
        record = curve_record(fc)
        _ACTION_COUNTS["unique_curves"] += 1
        _ACTION_COUNTS["keys"] += len(fc.keyframe_points)
        _ACTION_COUNTS["sample_points"] += len(fc.sampled_points)
        if _ACTION_COUNTS["keys"] >= next_progress:
            progress("action_keys_hashed", **_ACTION_COUNTS)
            next_progress = _ACTION_COUNTS["keys"] + 100000
        return {"curve_index": seen[pointer], **record}

    for action in bpy.data.actions:
        layers = []
        layered_curve_count = 0
        for layer in action.layers:
            strips = []
            for strip in layer.strips:
                bags = [{"slot_handle": bag.slot_handle,
                         "curves": [unique_curve(fc) for fc in bag.fcurves],
                         "groups": [rna(g) for g in getattr(bag, "groups", ())]}
                        for bag in getattr(strip, "channelbags", ())]
                layered_curve_count += sum(len(bag["curves"]) for bag in bags)
                strips.append({"settings": rna(strip), "channelbags": bags})
            layers.append({"settings": rna(layer), "strips": strips})
        legacy = []
        # In Blender 5.2 the legacy view can expose the layered first slot.
        # Only fall back when the layered API yielded no curves; pointer
        # deduplication also guards aliases within any layers/channelbags.
        if layered_curve_count == 0:
            try:
                legacy = [unique_curve(fc) for fc in action.fcurves]
            except (AttributeError, RuntimeError):
                pass
        result[action.name] = {"settings": rna(action), "custom": custom(action),
            "slots": [{"handle": slot.handle, "settings": rna(slot),
                       "identifier": getattr(slot, "identifier", None),
                       "target_id_type": getattr(slot, "target_id_type", None)}
                      for slot in action.slots],
            "layers": layers, "legacy_curves": legacy}
    return result


def animation(owner):
    ad = getattr(owner, "animation_data", None)
    if ad is None:
        return None
    tracks = []
    for track in ad.nla_tracks:
        strips = []
        for strip in track.strips:
            strips.append({"settings": rna(strip),
                           "curves": [curve_record(fc) for fc in strip.fcurves],
                           "modifiers": [rna(m) for m in strip.modifiers]})
        tracks.append({"settings": rna(track), "strips": strips})
    drivers = []
    for fc in ad.drivers:
        drivers.append({"curve": curve_record(fc), "driver": rna(fc.driver),
            "valid": fc.driver.is_valid,
            "variables": [{"settings": rna(v), "targets": [rna(t) for t in v.targets]}
                          for v in fc.driver.variables]})
    return {"settings": rna(ad), "nla": tracks, "drivers": drivers}


def buffer_hash(collection, field, width, code="f"):
    values = array(code, [0]) * (len(collection) * width)
    collection.foreach_get(field, values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def actor_meshes(profile):
    records = {}
    for actor in profile["actors"]:
        for name in actor["objects"]:
            obj = bpy.data.objects[name]
            mesh = obj.data
            records[name] = {"data": mesh.name, "settings": rna(mesh),
                "custom": custom(mesh), "world": plain(obj.matrix_world),
                "vertices": buffer_hash(mesh.vertices, "co", 3),
                "edges": buffer_hash(mesh.edges, "vertices", 2, "i"),
                "loops": buffer_hash(mesh.loops, "vertex_index", 1, "i"),
                "polygons": [(p.loop_start, p.loop_total, p.material_index, p.use_smooth)
                             for p in mesh.polygons],
                "attributes": mesh_attributes(mesh),
                "materials": [m.name if m else None for m in mesh.materials],
                "uv": {uv.name: buffer_hash(uv.data, "uv", 2) for uv in mesh.uv_layers},
                "groups": [(g.index, g.name, g.lock_weight) for g in obj.vertex_groups],
                "weights": digest([[(g.group, g.weight) for g in v.groups] for v in mesh.vertices]),
                "shapes": None if mesh.shape_keys is None else {
                    "settings": rna(mesh.shape_keys), "animation": animation(mesh.shape_keys),
                    "blocks": [{"settings": rna(b), "coordinates": buffer_hash(b.data, "co", 3)}
                               for b in mesh.shape_keys.key_blocks]}}
    return records


def mesh_attributes(mesh):
    records = {}
    layouts = {"FLOAT": ("value", 1, "f"), "INT": ("value", 1, "i"),
        "INT8": ("value", 1, "i"), "BOOLEAN": ("value", 1, "b"),
        "FLOAT_VECTOR": ("vector", 3, "f"), "FLOAT2": ("vector", 2, "f"),
        "FLOAT_COLOR": ("color", 4, "f"), "BYTE_COLOR": ("color", 4, "f"),
        "INT32_2D": ("value", 2, "i"), "INT16_2D": ("value", 2, "i"),
        "QUATERNION": ("value", 4, "f"),
        "FLOAT4X4": ("value", 16, "f")}
    for attribute in mesh.attributes:
        layout = layouts.get(attribute.data_type)
        if layout:
            data = buffer_hash(attribute.data, *layout)
        elif attribute.data_type == "STRING":
            data = digest([plain(v.value) for v in attribute.data])
        else:
            raise ValueError("Unsupported protected mesh attribute: " + attribute.data_type)
        records[attribute.name] = {"type": attribute.data_type, "domain": attribute.domain,
                                    "length": len(attribute.data), "sha256": data}
    return records


def object_records():
    """Include stage visibility/transforms, modifier flags and rig rest data."""
    result = {}
    for obj in bpy.data.objects:
        item = {"settings": rna(obj), "custom": custom(obj),
                "world": plain(obj.matrix_world), "animation": animation(obj),
                "modifiers": [{"settings": rna(m), "custom": custom(m)} for m in obj.modifiers],
                "constraints": [rna(c) for c in obj.constraints]}
        if obj.type == "ARMATURE":
            item["armature"] = {"settings": rna(obj.data), "custom": custom(obj.data),
                "bones": {b.name: {"settings": rna(b), "custom": custom(b),
                    "rest_matrix": plain(b.matrix_local), "head": plain(b.head_local),
                    "tail": plain(b.tail_local), "parent": b.parent.name if b.parent else None}
                    for b in obj.data.bones},
                "pose": {b.name: {"settings": rna(b), "custom": custom(b),
                    "constraints": [rna(c) for c in b.constraints]} for b in obj.pose.bones}}
        result[obj.name] = item
    return result


def node_record(node, masks):
    item = {"settings": rna(node), "custom": custom(node),
            "inputs": {}, "outputs": {}}
    for field in ("inputs", "outputs"):
        for socket in getattr(node, field):
            key = socket.identifier
            value = plain(getattr(socket, "default_value", None))
            if field == "inputs" and (node.name, key) in masks:
                value = {"allowed_exact_socket": True}
            item[field][key] = {"name": socket.name, "value": value,
                                "enabled": socket.enabled}
    for key in ("color_ramp", "mapping", "texture_mapping", "color_mapping", "image_user"):
        value = getattr(node, key, None)
        if value is None:
            continue
        record = {"settings": rna(value)}
        if hasattr(value, "elements"):
            record["elements"] = [rna(e) for e in value.elements]
        if hasattr(value, "curves"):
            record["curves"] = [{"settings": rna(c), "points": [rna(p) for p in c.points]}
                                for c in value.curves]
        item[key] = record
    return item


def tree_record(tree, masks=()):
    return {"settings": rna(tree), "custom": custom(tree),
            "animation": animation(tree),
            "nodes": {n.name: node_record(n, masks) for n in tree.nodes},
            "links": sorted((l.from_node.name, l.from_socket.identifier,
                             l.to_node.name, l.to_socket.identifier) for l in tree.links),
            "interface": [rna(item) for item in tree.interface.items_tree]
                         if hasattr(tree, "interface") else []}


def image_records():
    result = {}
    for image in bpy.data.images:
        if image.type in {"RENDER_RESULT", "COMPOSITING"} or image.name in {"Render Result", "Viewer Node"}:
            continue
        packed = []
        files = list(getattr(image, "packed_files", ()))
        if files:
            for entry in files:
                packed.append({"path": getattr(entry, "filepath", None),
                    "sha256": hashlib.sha256(bytes(entry.packed_file.data)).hexdigest()})
        elif image.packed_file:
            packed.append({"sha256": hashlib.sha256(bytes(image.packed_file.data)).hexdigest()})
        # pixels is a writable RNA array: generic rna() would expand every
        # texture pixel into Python floats (many gigabytes). Payloads remain
        # protected by packed/file byte hashes or a raw generated-pixel buffer.
        record = {"settings": rna(image, {"pixels"}), "custom": custom(image),
                  "colorspace": rna(image.colorspace_settings), "packed": packed,
                  "size": plain(image.size)}
        if not packed and image.source in {"FILE", "TILED"} and image.filepath:
            need(not image.filepath.startswith("//"),
                 "Relative unpacked image requires explicit path adaptation: " + image.name)
            path = Path(bpy.path.abspath(image.filepath, library=image.library))
            record["external_sha256"] = contract.digest(path) if path.is_file() else None
        if not packed and image.source == "GENERATED":
            record["pixels"] = pixel_hash(image)
        result[image.name] = record
    return result


def pixel_hash(image):
    values = array("f", [0.0]) * len(image.pixels)
    image.pixels.foreach_get(values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def selected_masks(profile, case):
    materials, lights = {}, set()
    for override in case["overrides"]:
        sw = profile["switches"][override["switch"]]
        need(sw["kind"] in ALLOWED, "Unsupported publish control: " + sw["kind"])
        if sw["kind"] == "node_input":
            mat = bpy.data.materials[sw["material"]]
            sock = bench.find_socket(mat.node_tree.nodes[sw["node"]], sw["socket"], sw.get("socket_match") == "identifier")
            materials.setdefault(mat.node_tree.as_pointer(), set()).add((sw["node"], sock.identifier))
        elif sw["kind"] == "light_energy":
            lights.add(bpy.data.objects[sw["object"]].data.name)
    return materials, lights


def protection(profile, case, phase="protected_state"):
    material_masks, light_masks = selected_masks(profile, case)
    started = time.perf_counter()
    progress("protection_started", phase=phase)
    fingerprints = {}
    graph_counts = {}

    def graphs():
        trees, visited = {}, set()
        roots = [("material:" + m.name, m.node_tree) for m in bpy.data.materials if m.node_tree]
        roots += [("world:" + w.name, w.node_tree) for w in bpy.data.worlds if w.node_tree]
        roots += [("light:" + l.name, l.node_tree) for l in bpy.data.lights if l.node_tree]
        root_keys = {tree.as_pointer(): key for key, tree in roots}
        references = nodes = 0
        for _owner_key, root in roots:
            for tree in bench.walk_trees(root):
                references += 1
                pointer = tree.as_pointer()
                if pointer in visited:
                    continue
                visited.add(pointer)
                # Deduplicate before serialization: shared internal shader
                # groups previously incurred full RNA scans for each material.
                stable_key = root_keys.get(pointer, "node_group:" + tree.name_full)
                need(stable_key not in trees, "Protected shader tree identity collision: " + stable_key)
                trees[stable_key] = tree_record(tree, material_masks.get(pointer, ()))
                nodes += len(tree.nodes)
        graph_counts.update(unique_trees=len(visited), nodes=nodes,
                            tree_references=references, duplicate_references=references-len(visited))
        return trees

    def component(name, callback):
        component_start = time.perf_counter()
        progress("component_started", phase=phase, component=name)
        value = callback()
        fingerprints[name] = digest(value)
        counts = dict(_ACTION_COUNTS) if name == "actions" else dict(graph_counts) if name == "node_graphs" else {}
        counts["records"] = len(value)
        progress("component_complete", phase=phase, component=name,
                 seconds=round(time.perf_counter()-component_start, 4), **counts)

    # Each large component is hashed and released separately, so a complete
    # scene-sized JSON tree is never held alongside all the others.
    component("actions", actions_record)
    component("objects_rigs_modifiers", object_records)
    component("actor_meshes", lambda: actor_meshes(profile))
    component("materials", lambda: {mat.name: {
        "settings": rna(mat), "custom": custom(mat), "animation": animation(mat),
        "light_groups": rna(getattr(mat, "light_groups", None))} for mat in bpy.data.materials})
    component("node_graphs", graphs)
    component("images", image_records)
    component("lights", lambda: {light.name: {
        "settings": rna(light, {"energy"} if light.name in light_masks else ()),
        "custom": custom(light), "animation": animation(light),
        "light_groups": rna(getattr(light, "light_groups", None))} for light in bpy.data.lights})
    component("worlds", lambda: {world.name: {
        "settings": rna(world), "animation": animation(world), "custom": custom(world)}
        for world in bpy.data.worlds})
    component("scene_camera_color", lambda: {s.name: {
        "world": plain(s.world), "display": rna(s.display_settings),
        "view": rna(s.view_settings), "animation": animation(s),
        "markers": [(m.name, m.frame, m.camera.name if m.camera else None) for m in s.timeline_markers],
        "rigidbody_world": rna(s.rigidbody_world),
        "collections": [(c.name, c.hide_render, c.hide_viewport) for c in bpy.data.collections]}
        for s in bpy.data.scenes})
    component("cameras", lambda: {c.name: {"settings": rna(c), "animation": animation(c)}
                                  for c in bpy.data.cameras})
    progress("protection_complete", phase=phase,
             seconds=round(time.perf_counter()-started, 4), components=len(fingerprints))
    return fingerprints


def compositor_records():
    trees, visited = {}, set()
    roots = [("scene:" + s.name, bench.compositor(s)) for s in bpy.data.scenes
             if bench.compositor(s)]
    root_keys = {tree.as_pointer(): key for key, tree in roots}
    for _owner_key, root in roots:
        for tree in bench.walk_trees(root):
            if tree.as_pointer() in visited:
                continue
            visited.add(tree.as_pointer())
            key = root_keys.get(tree.as_pointer(), "node_group:" + tree.name_full)
            need(key not in trees, "Protected compositor tree identity collision: " + key)
            trees[key] = tree_record(tree)
    return trees


def apply_glow(selector):
    """Make precisely the declared rewires and verify the complete tree delta."""
    for sel in selector["nodes"]:
        tree = bench.compositor(bpy.data.scenes[sel["scene"]])
        before = tree_record(tree)
        node = tree.nodes[sel["node"]]
        need(all(not socket.is_linked for socket in node.outputs
                 if socket.name not in (sel["image_output"], sel["glare_output"])),
             "Unaccounted Glare output has consumers")
        image = node.inputs.get("Image")
        need(image is not None and len(image.links) == 1, "Glare needs one Image source")
        source = image.links[0].from_socket
        zero = tree.nodes.new("CompositorNodeRGB")
        zero.name = "Studio publish | zero | " + node.name
        zero.outputs[0].default_value = (0, 0, 0, 0)
        expected = copy.deepcopy(before)
        expected["nodes"][zero.name] = node_record(zero, ())
        links = set(tuple(x) for x in expected["links"])
        for out_name, replacement in ((sel["image_output"], source),
                                      (sel["glare_output"], zero.outputs[0])):
            output = node.outputs.get(out_name)
            need(output is not None, "Glare output missing")
            for link in list(output.links):
                links.remove((node.name, output.identifier, link.to_node.name, link.to_socket.identifier))
                links.add((replacement.node.name, replacement.identifier,
                           link.to_node.name, link.to_socket.identifier))
                target = link.to_socket
                tree.links.remove(link)
                tree.links.new(replacement, target)
        expected["links"] = sorted(links)
        need(tree_record(tree) == expected, "Unexpected compositor change during bypass")


def assert_same(before, after, label):
    changed = [key for key in before if before[key] != after.get(key)]
    need(not changed and before.keys() == after.keys(), label + ": " + ", ".join(changed))


def check_no_simulation():
    hazards = bench.simulation_hazards()
    need(not hazards, "Active simulation refused before evaluation: " + "; ".join(hazards))


def set_camera(scene, profile):
    camera = scene.objects.get(profile["scene"]["camera"])
    need(camera is not None and camera.type == "CAMERA", "Exact camera missing")
    markers = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    try:
        for marker, _camera in markers:
            marker.camera = None
        scene.frame_set(FRAME)
        scene.camera = camera
        bpy.context.view_layer.update()
    finally:
        for marker, original in markers:
            marker.camera = original
    need(scene.camera == camera, "Authored camera selection failed")
    record = bench.camera_record(scene)
    need(record["lens_mm"] > 2 and all(d["valid"] for owner in record["drivers"]
                                      for d in owner["drivers"]), "Camera RNA/driver invalid")
    return record


def settings(scene, output, filename):
    need(scene.render.engine == "BLENDER_EEVEE", "Pinned EEVEE source required")
    scene.frame_start = scene.frame_end = FRAME
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.use_border = False
    scene.render.use_sequencer = False
    scene.render.use_motion_blur = False
    scene.eevee.taa_render_samples = 64
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.render.filepath = str((output / filename).resolve())
    return {"width": 1920, "height": 1080, "samples": 64, "dof": "source",
            "motion_blur": False, "color_depth": "16", "format": "PNG"}


def render(scene, profile, path):
    need(not path.exists(), "Render target already exists")
    before = bench.camera_record(scene)
    markers = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    try:
        for marker, _camera in markers:
            marker.camera = None
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True, scene=scene.name)
    finally:
        for marker, camera in markers:
            marker.camera = camera
    need(bench.camera_record(scene) == before, "Camera changed during render")
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        need(list(image.size) == [1920, 1080], "Final PNG dimensions differ")
    finally:
        bpy.data.images.remove(image)
    return {"path": str(path.resolve()), "sha256": contract.digest(path)}


def pinned(record, label):
    path = Path(record["path"]).resolve(strict=True)
    need(path.is_file() and contract.digest(path).lower() == record["sha256"].lower(), label + " hash mismatch")
    return path


def validate_request(request, request_path):
    need(request.get("schema_version", 1) == 1 and request["mode"] in {"publish", "reopen"}, "Invalid publish request")
    profile_path = pinned(request["profile"], "profile")
    runtime_path = pinned(request["runtime"], "runtime")
    source = pinned(request["expected_source"], "expected source")
    pins = request.get("pins", {})
    for key, path, legacy in (("worker", Path(__file__), "worker_sha256"),
                              ("benchworker", Path(bench.__file__), "bench_worker_sha256"),
                              ("contract", Path(contract.__file__), "contract_sha256")):
        record = pins.get(key, {"path": str(path), "sha256": request.get(legacy, "")})
        need(pinned(record, key) == path.resolve(), "Unexpected pinned " + key + " path")
    profile = contract.load(profile_path)
    need(not contract.validate(profile, check_source=True), "Invalid original frozen profile")
    need((ROOT / profile["runtime"]).resolve() == runtime_path, "Runtime/profile mismatch")
    case = next((c for c in profile["cases"] if c["id"] == request["case_id"]), None)
    need(case is not None and case["frame"] == FRAME, "Only selected frame4290 is publishable")
    need(profile["render"]["dof"] == "source" and profile["render"]["motion_blur"] is False,
         "Source DOF and disabled motion blur required")
    for override in case["overrides"]:
        need(profile["switches"][override["switch"]]["kind"] in ALLOWED, "Publish scope exceeded")
    tolerance = request["reopen_tolerance"]
    for key, cap in (("max_abs", .005), ("mean_abs", .0001)):
        need(type(tolerance[key]) in (int, float) and math.isfinite(tolerance[key])
             and 0 <= tolerance[key] <= cap, "Invalid predeclared reopen tolerance")
    iteration = request.get("iteration")
    if iteration:
        directory = Path(iteration["path"])
        need(contract.digest(directory / "manifest.json") == iteration["manifest_sha256"]
             and contract.digest(directory / "lesson.json") == iteration["lesson_sha256"], "Closed iteration pin mismatch")
        lesson = contract.load(directory / "lesson.json")
        need(lesson["selection"] == case["id"], "Case differs from reviewed selection")
    if request["mode"] == "publish":
        need(profile["source"] == request["expected_source"], "Frozen source differs")
    return profile, case, contract.load(runtime_path), source


def candidate_profile(profile, case, source):
    result = copy.deepcopy(profile)
    result["source"] = source
    for override in case["overrides"]:
        sw = result["switches"][override["switch"]]
        if sw["kind"] in {"node_input", "light_energy"}:
            sw["expected"] = override["value"]
    return result


def inspect_binding(profile, scene, muted):
    inventory = bench.inventory(profile, scene, muted)
    result = contract.bind(profile, inventory)
    need(result["passed"], "Binding failed: " + "; ".join(result["errors"]))
    need(not any(m["active_undefined"] for m in inventory["materials"]), "Undefined active material node")
    return result


def compare_images(current, prior, tolerance):
    images, buffers = [], []
    try:
        for path in (current, prior):
            image = bpy.data.images.load(str(path), check_existing=False)
            images.append(image)
            need(list(image.size) == [1920, 1080], "Reopen image dimensions differ")
            buf = array("f", [0.0]) * len(image.pixels)
            image.pixels.foreach_get(buf)
            buffers.append(buf)
        need(len(buffers[0]) == len(buffers[1]) and len(buffers[0]) > 0, "Image shape differs")
        maximum, total = 0., 0.
        for a, b in zip(*buffers):
            delta = abs(a - b)
            maximum, total = max(maximum, delta), total + delta
        mean = total / len(buffers[0])
    finally:
        for image in images:
            bpy.data.images.remove(image)
    return {"passed": maximum <= tolerance["max_abs"] and mean <= tolerance["mean_abs"],
            "max_abs": maximum, "mean_abs": mean, "thresholds": tolerance,
            "space": "Blender-decoded PNG float RGBA; no perceptual/art certification"}


def execute(request, output, request_path):
    global _PROGRESS_DIR, _PROGRESS_STARTED
    _PROGRESS_DIR, _PROGRESS_STARTED = output, time.perf_counter()
    progress("operation_started", mode=request.get("mode"), case_id=request.get("case_id"))
    profile, case, runtime, source_path = validate_request(request, request_path)
    bench.prepare_runtime(runtime, profile["scene"]["registration"])
    original_source = copy.deepcopy(profile["source"])
    source = request["expected_source"]
    mode = request["mode"]
    prior = None
    if mode == "reopen":
        prior_path = pinned(request["publish_report"], "publish report")
        prior = contract.load(prior_path)
        pinned(prior["profile"], "published profile")
        need(prior.get("passed") is True and prior["candidate"] == source
             and prior["case_id"] == case["id"]
             and prior["profile"]["sha256"] == request["profile"]["sha256"]
             and prior["runtime"] == request["runtime"]
             and prior["reopen_tolerance"] == request["reopen_tolerance"], "Reopen publish contract mismatch")
        pinned(prior["image"], "saved candidate still")
        active_profile = candidate_profile(profile, case, source)
    else:
        active_profile = profile
    progress("source_open_started", source=str(source_path))
    scene, muted = bench.open_source(active_profile)
    progress("source_open_complete", objects=len(bpy.data.objects), actions=len(bpy.data.actions),
             materials=len(bpy.data.materials), images=len(bpy.data.images))
    check_no_simulation()
    camera = set_camera(scene, active_profile)
    binding = inspect_binding(active_profile, scene, muted)
    baseline = protection(profile, case, "source_baseline")
    baseline_compositor = compositor_records()
    baseline_mesh = bench.mesh_signature(profile)
    if prior:
        assert_same(prior["protection"]["after"], baseline, "Reopened protected state differs")
        need(digest(baseline_compositor) == prior["compositor_sha256"]
             and camera == prior["camera"] and baseline_mesh == prior["mesh_signature"],
             "Reopened compositor/camera/pose differs")
        protected = baseline
    else:
        progress("controls_started", overrides=len(case["overrides"]))
        for override in case["overrides"]:
            sw = profile["switches"][override["switch"]]
            if sw["kind"] == "glow_bypass":
                apply_glow(sw)
            else:
                bench.apply_switch(sw, override["value"])
        check_no_simulation()
        bpy.context.view_layer.update()
        protected = protection(profile, case, "after_controls")
        assert_same(baseline, protected, "Nonselected production data changed")
        need(camera == bench.camera_record(scene) and baseline_mesh == bench.mesh_signature(profile),
             "Camera or evaluated actor geometry changed")
        progress("controls_complete", overrides=len(case["overrides"]))
    readback = bench.check_overrides(profile, case)
    final_settings = settings(scene, output, "selected.png" if mode == "publish" else "reopened-selected.png")
    # settings() touches only the declared final render/range fields; those
    # are read back explicitly instead of repeating the entire scene scan.
    need((scene.frame_start, scene.frame_end, scene.render.resolution_x,
          scene.render.resolution_y, scene.render.resolution_percentage,
          scene.eevee.taa_render_samples, scene.render.use_motion_blur,
          scene.render.image_settings.file_format, scene.render.image_settings.color_depth)
         == (FRAME, FRAME, 1920, 1080, 100, 64, False, "PNG", "16"), "Final render settings readback differs")
    comp_digest = digest(compositor_records())
    render_path = output / ("selected.png" if mode == "publish" else "reopened-selected.png")
    progress("render_started", path=str(render_path), settings=final_settings)
    image = render(scene, profile, render_path)
    progress("render_complete", image=image)
    assert_same(protected, protection(profile, case, "after_render"), "Protected data changed during render")
    need(digest(compositor_records()) == comp_digest and camera == bench.camera_record(scene)
         and baseline_mesh == bench.mesh_signature(profile), "Compositor/camera/mesh changed during render")
    readback = bench.check_overrides(profile, case)
    report = {"schema_version": 1, "mode": mode, "passed": False,
        "case_id": case["id"], "source": source, "original_source": original_source,
        "profile": request["profile"], "runtime": request["runtime"],
        "pins": request.get("pins"), "request_sha256": contract.digest(request_path),
        "protection": {"baseline": baseline, "after": protected}, "camera": camera,
        "mesh_signature": baseline_mesh, "color": protected["scene_camera_color"],
        "compositor_sha256": comp_digest, "switch_readback": readback, "binding": binding,
        "render": final_settings, "image": image, "reopen_tolerance": request["reopen_tolerance"],
        "muted_file_outputs": muted, "art_status": "pending", "user_art_approval": False,
        "limits": "Only4290 final still; no video/new physics/eye transparency or art approval"}
    if mode == "publish":
        candidate = (output / "Candidate.blend").resolve()
        need(not candidate.exists() and candidate != source_path
             and candidate != Path(original_source["path"]).resolve(), "New candidate path required")
        progress("save_started", candidate=str(candidate))
        bpy.ops.wm.save_as_mainfile(filepath=str(candidate), relative_remap=False, compress=True)
        progress("save_complete", candidate=str(candidate))
        need(candidate.is_file(), "Candidate save did not produce a file")
        assert_same(protected, protection(profile, case, "after_save"), "Protected data changed during save")
        need(digest(compositor_records()) == comp_digest and bench.camera_record(scene) == camera,
             "Compositor/camera changed during save")
        report["candidate"] = {"path": str(candidate), "sha256": contract.digest(candidate)}
    else:
        report["candidate"] = source
        report["publish_report"] = request["publish_report"]
        report["independent_process"] = True
        report["pixel_comparison"] = compare_images(render_path, prior["image"]["path"], request["reopen_tolerance"])
        need(report["pixel_comparison"]["passed"], "Independent reopened pixels exceed predeclared bounds")
    need(contract.digest(source_path) == source["sha256"], "Input source changed")
    need(contract.digest(original_source["path"]) == original_source["sha256"], "Frozen original changed")
    report["source_unchanged"] = report["original_source_unchanged"] = True
    report["passed"] = True
    progress("operation_complete", mode=mode, case_id=case["id"], passed=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    need(output.is_dir(), "Launcher-created output directory required")
    need(all(p.name in {"request.json", "publish-profile.json"} and p.is_file()
             for p in output.iterdir()),
         "Publish worker requires a new empty output directory")
    request = contract.load(args.request)
    mode = request.get("mode")
    need(mode in {"publish", "reopen"}, "Invalid mode")
    report = {"schema_version": 1, "mode": mode, "passed": False, "errors": []}
    try:
        report = execute(request, output, args.request)
    except Exception as exc:
        report["errors"] = [str(exc)]
        report["traceback"] = traceback.format_exc()
    bench.write(output / (mode + "-report.json"), report)
    print("STUDIO_PUBLISH_RESULT", json.dumps({"passed": report["passed"], "mode": mode,
                                              "errors": report.get("errors", [])}), flush=True)
    if not report["passed"]:
        raise RuntimeError("Pinned candidate operation rejected; see report")


if __name__ == "__main__":
    main()
