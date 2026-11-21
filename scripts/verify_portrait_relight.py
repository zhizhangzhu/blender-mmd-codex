"""Read-only CPU reopen audit of a Clean-v2 portrait-relight still project.

Blender --background --disable-autoexec --python-exit-code 1 --python this.py --
  --source Clean.blend --current Relight.blend --preparation preparation.json
  --output independent-reopen.json

No render, simulation, blend save, preference save or producer replay occurs.
All Actions and all geometry are strict: historical sleeve exceptions are never
enabled. New shader math is not certified by this structural preservation audit.
"""

import argparse
import ast
import copy
import csv
import hashlib
import inspect
import json
import math
import sys
import traceback
from array import array
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_ikhor_sleeve_repair as capture
from render_portrait_light_controls import camera_driver_record

SOURCE_SHA = "0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4"
PREFIX = "Portrait relight | "
FRAME = 4290
ACTORS = {"aksiniya": "阿克西妮娅2_mesh", "ikhor": "Ikhor | mesh | Ikhor_mesh"}
ARCS = {"Bold wedding | blue vow arc", "Bold wedding | gold vow arc"}
VOLUMES = {
    "Wedding | bounded rear scattering", "Bold wedding | bounded beam fan air",
    *(f"Bold wedding | {color} luminous volume {n}" for color in ("blue", "gold") for n in range(3)),
}
STAGE_LIGHTS = {
    "Focused light | cold window key", "Focused light | warm altar",
    "Focused light | warm vase accent", "Focused light | cool column accent",
    "Stage art | grounded backlight", "Wedding | blue vow shaft", "Wedding | gold vow shaft",
}
PALETTES = {
    "aksiniya": {"颜", "首", "手", "帽", "帽+", "披肩", "披肩+", "腿", "腿+", "衣", "衣+", "裙", "裙+", "毛领"},
    "ikhor": {"颜.001", "首.001", "手.001", "带子", "衣.001", "衣2", "衣领", "裙.001"},
}
RIMS = {
    "aksiniya": {"前鬓", "呆毛", "鬓", "毛领", "帽", "披肩", "腿", "衣", "裙", "前装饰", "后装饰", "头饰"},
    "ikhor": {"鬓.001", "带子", "衣.001", "衣2", "衣领", "裙.001"},
}
INKS = {
    "aksiniya": {"mmd_edge." + s for s in ("前鬓", "呆毛", "鬓", "毛领", "衣", "裙", "腿", "披肩", "头饰", "前装饰", "后装饰", "颜", "首", "手")},
    "ikhor": {"mmd_edge." + s for s in ("鬓.001", "带子", "衣.001", "衣2", "衣领", "衣饰", "裙.001", "裤", "靴", "靴底", "靴饰", "颜.001", "首.001", "手.001")},
}
GOLD_SOURCE_IDENTITIES = {"衣", "衣2", "衣领", "带子", "衣饰", "裙", "靴饰"}
GOLD_MODIFIED_SAVED_NAMES = {"带子", "裙.001", "衣领", "衣.001", "衣2"}
TRANSFORMS = {
    "location", "rotation_euler", "rotation_quaternion", "rotation_axis_angle", "scale",
    "delta_location", "delta_rotation_euler", "delta_rotation_quaternion", "delta_scale",
    "matrix_basis", "matrix_local", "matrix_world",
}
UI_NODE = {"inputs", "outputs", "internal_links", "location", "width", "height", "select"}
NEW_MATH_TYPES = {"ShaderNodeMath", "ShaderNodeVectorMath", "ShaderNodeCombineXYZ", "ShaderNodeMapRange",
                  "ShaderNodeValToRGB", "ShaderNodeMixRGB", "ShaderNodeValue", "ShaderNodeRGBToBW"}
CAPTURE_VERSION = "portrait-reopen-5-driven-sockets-evaluated-hidden-volumes"
CACHE_ROOT = Path("D:/codex/temp/MMD-Portrait-Relight-v1")


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest(value):
    return capture.digest(value)


def differences(a, b, path="", limit=40):
    if type(a) is not type(b):
        return [{"path": path, "source": a, "current": b}]
    if isinstance(a, dict):
        result = []
        for key in sorted(a.keys() | b.keys()):
            child = path + "/" + str(key)
            if key not in a or key not in b:
                result.append({"path": child, "kind": "added" if key not in a else "removed"})
            else:
                result.extend(differences(a[key], b[key], child, limit))
            if len(result) >= limit:
                break
        return result[:limit]
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return [{"path": path, "source_length": len(a), "current_length": len(b)}]
        result = []
        for i, (x, y) in enumerate(zip(a, b)):
            result.extend(differences(x, y, path + "/" + str(i), limit))
            if len(result) >= limit:
                break
        return result[:limit]
    return [] if a == b else [{"path": path, "source": a, "current": b}]


def complete_actions():
    """Every named Action, every curve/handle, all slots/layers/bag routing."""
    records = {}
    for action in bpy.data.actions:
        record = copy.deepcopy(capture.action_record(action, False, False))
        record["full_slots"] = [capture.rna(s, root=True) for s in action.slots]
        record["groups"] = [capture.rna(g, root=True, skip={"channels"}) for g in getattr(action, "groups", ())]
        record["routing"] = [
            [[{"settings": capture.rna(bag, root=True, skip={"fcurves", "groups"}),
               "groups": [capture.rna(g, root=True, skip={"channels"}) for g in bag.groups],
               "curves": [(c.data_path, c.array_index) for c in bag.fcurves]}
              for bag in getattr(strip, "channelbags", ())] for strip in layer.strips]
            for layer in action.layers
        ]
        records[action.name] = digest(record)
    return records


def driver_samples(tree):
    """Resolve scalar drivers independently; only safe arithmetic is evaluated."""
    records, indices = {}, {}
    curves = tree.animation_data.drivers if tree.animation_data else ()
    safe_ast = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Constant,
                ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd)
    for curve in curves:
        driver, path = curve.driver, curve.data_path
        indices.setdefault(path, set()).add(curve.array_index)
        record = {"path": path, "index": curve.array_index, "curve_sha256": digest(capture.curve_record(curve)),
                  "valid": driver.is_valid, "expression": driver.expression, "variables": {}, "verified": False}
        actual = tree.path_resolve(path)
        record["actual"] = float(actual[curve.array_index] if hasattr(actual, "__len__") else actual)
        try:
            if driver.type != "SCRIPTED" or driver.use_self:
                raise ValueError("Only scalar scripted arithmetic is recomputed")
            values = {"frame": float(bpy.context.scene.frame_current_final), "pi": math.pi, "e": math.e}
            for variable in driver.variables:
                target = variable.targets[0]
                if variable.type == "SINGLE_PROP":
                    value = float(target.id.path_resolve(target.data_path))
                elif (variable.type == "TRANSFORMS" and not target.bone_target
                      and target.transform_space == "WORLD_SPACE" and target.transform_type in {"LOC_X", "LOC_Y", "LOC_Z"}):
                    value = float(target.id.matrix_world.translation["XYZ".index(target.transform_type[-1])])
                else:
                    raise ValueError("Driver variable is outside the recomputation subset")
                values[variable.name] = value
                record["variables"][variable.name] = {"type": variable.type, "id": target.id.name,
                    "transform_type": target.transform_type, "transform_space": target.transform_space,
                    "data_path": target.data_path, "value": value}
            expression = ast.parse(driver.expression, mode="eval")
            if any(not isinstance(n, safe_ast) for n in ast.walk(expression)):
                raise ValueError("Expression outside numeric names and arithmetic")
            expected = float(eval(compile(expression, "<preserved scalar driver>", "eval"), {"__builtins__": {}}, values))
            record["expected"] = expected
            record["verified"] = bool(driver.is_valid and math.isclose(record["actual"], expected, rel_tol=1e-6, abs_tol=1e-6))
        except (AttributeError, KeyError, NameError, TypeError, ValueError, ZeroDivisionError, OverflowError, ReferenceError) as error:
            record["recompute_limit"] = str(error)
        records[path + "|" + str(curve.array_index)] = record
    return records, indices


def graph_socket(socket, indices):
    value = capture.plain(getattr(socket, "default_value", None))
    path = socket.path_from_id("default_value") if hasattr(socket, "default_value") else None
    driven = indices.get(path, set())
    if driven:
        if isinstance(value, list):
            value = ["PRESERVED_DRIVER_EVALUATED_VALUE" if i in driven else v for i, v in enumerate(value)]
        elif driven == {0}:
            value = "PRESERVED_DRIVER_EVALUATED_VALUE"
    return {"id": socket.identifier, "name": socket.name, "value": value, "driver_components": sorted(driven)}


def graph(tree):
    if tree is None:
        return None
    samples, indices = driver_samples(tree)
    return {
        "settings": capture.rna(tree, root=True, skip={"nodes", "links", "interface"}),
        "interface": capture.rna(tree.interface, root=True) if tree.interface else None,
        "nodes": {node.name: {
            "type": node.bl_idname,
            "active_output": getattr(node, "is_active_output", None),
            "settings": capture.rna(node, root=True, skip=UI_NODE),
            "inputs": [graph_socket(s, indices) for s in node.inputs],
            "outputs": [graph_socket(s, indices) for s in node.outputs],
            "internal_links": [(l.from_socket.identifier, l.to_socket.identifier) for l in node.internal_links],
        } for node in tree.nodes},
        "links": sorted((l.to_node.name, list(l.to_node.inputs).index(l.to_socket),
                         l.from_node.name, list(l.from_node.outputs).index(l.from_socket), l.is_muted) for l in tree.links),
        "animation": capture.animation(tree),
        "driver_values": samples,
    }


def source_permissions(scene):
    """Derive old destinations from SOURCE, never from producer state flags."""
    allowed = {}
    for actor in ACTORS:
        obj = scene.objects[ACTORS[actor]]
        owned = {m.name for m in obj.data.materials if m}
        for name in PALETTES[actor] | RIMS[actor] | INKS[actor]:
            if name not in owned:
                raise ValueError("Pinned actor slot missing: " + name)
            tree = bpy.data.materials[name].node_tree
            targets = allowed.setdefault(name, set())
            if name in PALETTES[actor]:
                label = "Reference transfer | shading bypass" if actor == "aksiniya" else "Ikhor character | source times single palette"
                targets.add((tree.nodes[label].name, 2))
            if name in INKS[actor]:
                node = tree.nodes["mmd_edge_preview"]
                targets.add((node.name, list(node.inputs).index(node.inputs["Color"])))
            if name in RIMS[actor]:
                if actor == "aksiniya":
                    nodes = [tree.nodes.get("Bold wedding material | " + x + " HDR source") for x in ("aksiniya_head_rim", "aksiniya_body_rim")]
                    nodes = [n for n in nodes if n]
                    if len(nodes) != 1:
                        raise ValueError("Pinned Aksiniya HDR source mismatch: " + name)
                    targets.add(("Reference transfer | controlled rim amount", 1))
                else:
                    nodes = [tree.nodes["Ikhor character | rim RGB"]]
                for link in nodes[0].outputs[0].links:
                    targets.add((link.to_node.name, list(link.to_node.inputs).index(link.to_socket)))
    gold = {}
    ikhor = scene.objects[ACTORS["ikhor"]]
    for mat in ikhor.data.materials:
        if not mat or mat.get("source_mmd_material_name") not in GOLD_SOURCE_IDENTITIES:
            continue
        if mat.get("performer_id") != "ikhor":
            raise ValueError("Gold endpoint material ownership mismatch: " + mat.name)
        tree = mat.node_tree
        endpoints = []
        for label, expected_base, expected_source_target, setting in (
            ("roughness", 0.70, 0.39, "gold_roughness"),
            ("physical mix", 0.12, 0.44, "gold_physical_mix"),
        ):
            node = tree.nodes[f"Clean Ikhor | gold {label} mask delta delta"]
            if node.operation != "SUBTRACT" or node.inputs[0].is_linked or node.inputs[1].is_linked:
                raise ValueError("Pinned gold delta contract changed: " + mat.name)
            if label == "roughness":
                endpoint = tree.nodes["Ikhor character | material-specific physical closure"].inputs["Roughness"].links[0].from_node
            else:
                endpoint = tree.nodes["Ikhor character | gold versus cloth closure mix"]
            if endpoint.operation != "ADD":
                raise ValueError("Pinned gold base path changed: " + mat.name)
            base_socket = endpoint.inputs[0]
            if base_socket.is_linked:
                if len(base_socket.links) != 1 or base_socket.links[0].from_node.bl_idname != "ShaderNodeValue":
                    raise ValueError("Pinned gold base must be constant or one Value: " + mat.name)
                base = float(base_socket.links[0].from_socket.default_value)
            else:
                base = float(base_socket.default_value)
            source_target = base + float(node.inputs[0].default_value)
            # Only the five edited cloth slots use the .70/.12 base contract.
            # The two untouched trim slots retain their own source bases and
            # receive no default-value exception in protected_graph below.
            if mat.name in GOLD_MODIFIED_SAVED_NAMES and (abs(base - expected_base) > 1e-6 or abs(source_target - expected_source_target) > 1e-6):
                raise ValueError("Pinned gold base/target values changed: " + mat.name)
            endpoints.append({"node": node.name, "input": 0, "base": base,
                              "source_target": source_target, "source_input0": node.inputs[0].default_value,
                              "preserved_input1": node.inputs[1].default_value, "setting": setting})
        gold[mat.name] = {"source_identity": mat.get("source_mmd_material_name"), "endpoints": endpoints}
    if {v["source_identity"] for v in gold.values()} != GOLD_SOURCE_IDENTITIES:
        raise ValueError("Pinned Ikhor gold material identity set changed")
    return allowed, gold


def image_record(image):
    result = capture.native.image_record(image)
    result["packed_payloads"] = [
        {"sha256": hashlib.sha256(bytes(p.packed_file.data)).hexdigest()}
        for p in image.packed_files
    ]
    if image.source == "GENERATED":
        values = array("f", [0]) * len(image.pixels)
        image.pixels.foreach_get(values)
        result["generated_pixels_sha256"] = hashlib.sha256(values.tobytes()).hexdigest()
    result["missing_unpacked_file"] = bool(
        image.source in {"FILE", "TILED", "SEQUENCE", "MOVIE"}
        and not image.packed_file and not image.packed_files
        and not Path(bpy.path.abspath(image.filepath)).is_file()
    )
    return result


def snapshot(path, derive_permissions=False):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    capture._ACTION_CACHE.clear()
    capture.native._ACTION_CACHE.clear()
    scene = bpy.context.scene
    saved_frame = scene.frame_current
    saved_visibility = {o.name: {"render": o.hide_render, "viewport": o.hide_viewport} for o in bpy.data.objects}
    # Hidden objects do not enter the depsgraph and can report identity matrices
    # after reopen. Evaluate only these named eight stage volumes temporarily;
    # their saved hidden states are checked from saved_visibility, then restored.
    for name in VOLUMES:
        bpy.data.objects[name].hide_viewport = False
    scene.frame_set(FRAME)
    bpy.context.view_layer.update()
    camera = scene.camera
    result = {"saved_frame": saved_frame, "objects": {}, "meshes": {}, "armatures": {}, "lights": {}, "cameras": {}, "worlds": {}}
    if derive_permissions:
        result["permissions"], result["gold_permissions"] = source_permissions(scene)
    result["actions"] = complete_actions()
    for obj in bpy.data.objects:
        skip = capture.OBJECT_SKIP | {"hide_render", "hide_viewport"}
        if obj.name in VOLUMES:
            skip |= {"select"}  # Hiding an object deselects it; this is UI state.
        if obj.type == "LIGHT":
            skip |= TRANSFORMS
        record = {"settings": capture.rna(obj, root=True, skip=skip),
                  "data": capture.identifier(obj.data), "animation": capture.animation(obj)}
        if obj.type == "ARMATURE":
            record["pose"] = {b.name: capture.rna(b, root=True) for b in obj.pose.bones}
        result["objects"][obj.name] = digest(record)
        if obj.type == "MESH":
            mesh = obj.data
            record = {"native": capture.native.geometry(obj), "attributes": capture.attributes(mesh),
                      "settings": capture.rna(mesh, root=True, skip=capture.MESH_SKIP),
                      "edges": capture.foreach_hash(mesh.edges, "vertices", "i", 2),
                      "polygon_ranges": {n: capture.foreach_hash(mesh.polygons, n, "i") for n in ("loop_start", "loop_total", "use_smooth")},
                      "uv_settings": [capture.rna(u, root=True, skip={"data", "uv", "vertex_selection", "edge_selection", "pin"}) for u in mesh.uv_layers],
                      "materials": [m.name if m else None for m in mesh.materials],
                      "animation": capture.animation(mesh)}
            if mesh.shape_keys:
                record["shape_settings"] = capture.rna(mesh.shape_keys, root=True, skip={"key_blocks"})
                record["shape_blocks"] = [capture.rna(k, root=True, skip={"data"}) for k in mesh.shape_keys.key_blocks]
                record["shape_animation"] = capture.animation(mesh.shape_keys)
            result["meshes"][obj.name] = digest(record)
    for arm in bpy.data.armatures:
        record = {"settings": capture.rna(arm, root=True), "animation": capture.animation(arm),
                  "rest": {b.name: {"head": list(b.head_local), "tail": list(b.tail_local),
                           "matrix": capture.plain(b.matrix_local), "parent": b.parent.name if b.parent else None}
                           for b in arm.bones}}
        result["armatures"][arm.name] = digest(record)
    for data in bpy.data.lights:
        result["lights"][data.name] = capture.rna(data, root=True)
    for data in bpy.data.cameras:
        result["cameras"][data.name] = {"settings": capture.rna(data, root=True, skip={"dof"}), "animation": capture.animation(data)}
    for world in bpy.data.worlds:
        result["worlds"][world.name] = digest({"settings": capture.rna(world, root=True, skip={"node_tree"}), "graph": graph(world.node_tree), "animation": capture.animation(world)})
    result["materials"] = {}
    result["material_owners"] = {}
    for mat in bpy.data.materials:
        settings = capture.rna(mat, root=True, skip={"node_tree"})
        settings["custom_properties"] = {k: v for k, v in settings.get("custom_properties", {}).items() if not k.startswith("portrait_")}
        result["materials"][mat.name] = {"settings": settings, "graph": graph(mat.node_tree), "animation": capture.animation(mat)}
        result["material_owners"][mat.name] = sorted(o.name for o in bpy.data.objects if o.type == "MESH" and mat in o.data.materials[:])
    result["groups"] = {g.name: graph(g) for g in bpy.data.node_groups}
    result["removable_groups"] = sorted(g.name for g in bpy.data.node_groups if not g.users and not g.use_fake_user)
    result["images"] = {i.name: image_record(i) for i in bpy.data.images if i.type not in {"RENDER_RESULT", "COMPOSITING"}}
    result["removable_images"] = sorted(i.name for i in bpy.data.images if not i.users and not i.use_fake_user)
    trees = {g.name: g for g in bpy.data.node_groups}
    trees.update({s.compositing_node_group.name: s.compositing_node_group for s in bpy.data.scenes if s.compositing_node_group})
    result["file_outputs"] = {name + "\0" + n.name: bool(n.mute) for name, tree in trees.items() for n in tree.nodes if n.type == "OUTPUT_FILE"}
    result["visibility"] = saved_visibility
    result["actor_meshes"] = {a: sorted(o.name for o in scene.objects if o.type == "MESH" and o.get("performer_id") == a and not o.hide_render) for a in ACTORS}
    result["color"] = {s.name: {"view": capture.rna(s.view_settings, root=True), "display": capture.rna(s.display_settings, root=True),
                      "sequencer": capture.rna(s.sequencer_colorspace_settings, root=True)} for s in bpy.data.scenes}
    result["render_engines"] = {s.name: s.render.engine for s in bpy.data.scenes}
    result["physics_world"] = {s.name: capture.rna(s.rigidbody_world, root=True) for s in bpy.data.scenes}
    result["camera"] = {"name": camera.name, "matrix": capture.plain(camera.matrix_world), "lens": camera.data.lens,
                        "drivers": camera_driver_record(camera), "dof": capture.rna(camera.data.dof, root=True)}
    result["compositors"] = {s.name: s.compositing_node_group.name for s in bpy.data.scenes if s.compositing_node_group}
    result["crypto"] = {s.name: s.compositing_node_group.nodes["Caption | both performers native object coverage"].matte_id for s in bpy.data.scenes if s.compositing_node_group and s.compositing_node_group.nodes.get("Caption | both performers native object coverage")}
    result["light_objects"] = {o.name: o.data.name for o in bpy.data.objects if o.type == "LIGHT"}
    result["counts"] = {"objects": len(bpy.data.objects), "mesh_objects": len(result["meshes"]), "armatures": len(result["armatures"]), "actions": len(result["actions"]), "materials": len(result["materials"]), "images": len(result["images"])}
    print("PORTRAIT_AUDIT_CAPTURE", str(path), result["counts"], flush=True)
    for name in VOLUMES:
        bpy.data.objects[name].hide_viewport = saved_visibility[name]["viewport"]
    bpy.context.view_layer.update()
    return result


def cached_snapshot(path, derive_permissions):
    functions = (snapshot, graph, graph_socket, driver_samples, complete_actions, source_permissions, image_record)
    signature = hashlib.sha256("\n".join(inspect.getsource(f) for f in functions).encode("utf-8")).hexdigest()
    binding = {"blend_sha256": sha(path), "capture_version": CAPTURE_VERSION, "capture_functions_sha256": signature,
               "strict_helper_sha256": sha(capture.__file__), "native_helper_sha256": sha(capture.native.__file__),
               "derive_source_permissions": derive_permissions,
               "rules_sha256": digest({"frame": FRAME, "volumes": sorted(VOLUMES), "actors": ACTORS,
                   "palettes": {k: sorted(v) for k, v in PALETTES.items()}, "rims": {k: sorted(v) for k, v in RIMS.items()},
                   "inks": {k: sorted(v) for k, v in INKS.items()}, "gold_five": sorted(GOLD_MODIFIED_SAVED_NAMES), "node_ui_exclusions": sorted(UI_NODE)})}
    cache = CACHE_ROOT / ("independent-source-capture.json" if derive_permissions else "independent-current-capture.json")
    if cache.is_file():
        old = json.loads(cache.read_text(encoding="utf-8"))
        if old.get("binding") == binding:
            print("PORTRAIT_AUDIT_CACHE_HIT", str(cache), flush=True)
            return old["snapshot"]
    data = {"binding": binding, "snapshot": snapshot(path, derive_permissions)}
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, allow_nan=False, default=lambda v: sorted(v) if isinstance(v, set) else v)
    temporary = cache.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(cache)
    print("PORTRAIT_AUDIT_CACHE_WRITTEN", str(cache), flush=True)
    return json.loads(text)["snapshot"]


def protected_graph(source, current, allowed_links=(), compositor=False, allow_new=False, allowed_values=()):
    """Compare every old node/input; only independently named destinations vary."""
    if source is None or current is None:
        return differences(source, current)
    problems = []
    for field in ("settings", "interface"):
        problems.extend(differences(source[field], current[field], "/" + field))
    old_names = set(source["nodes"])
    for name in sorted(old_names):
        if name not in current["nodes"]:
            problems.append({"path": "/nodes/" + name, "kind": "removed"})
            continue
        left, right = copy.deepcopy(source["nodes"][name]), copy.deepcopy(current["nodes"][name])
        if left["type"] == "CompositorNodeOutputFile":
            left["settings"].pop("mute", None)
            right["settings"].pop("mute", None)
        for target, index in allowed_values:
            if target == name:
                left["inputs"][index]["value"] = "SEPARATELY_CHECKED_GOLD_ENDPOINT"
                right["inputs"][index]["value"] = "SEPARATELY_CHECKED_GOLD_ENDPOINT"
        if compositor and left["type"] == "CompositorNodeGlare":
            for item in (left, right):
                for sock in item["inputs"]:
                    if sock["name"] == "Strength":
                        sock["value"] = "ALLOWED_ART_GLOW_STRENGTH"
        problems.extend(differences(left, right, "/nodes/" + name))
    extra = set(current["nodes"]) - old_names
    for name in sorted(extra):
        permitted_types = NEW_MATH_TYPES | ({"CompositorNodeRGBToBW"} if compositor else set())
        if not allow_new or not name.startswith(PREFIX) or current["nodes"][name]["type"] not in permitted_types:
            problems.append({"path": "/nodes/" + name, "kind": "unlicensed_added_node"})
    def retained_links(value):
        return [link for link in value["links"] if link[0] in old_names and (link[0], link[1]) not in allowed_links]
    problems.extend(differences(retained_links(source), retained_links(current), "/old_destination_links"))
    left, right = copy.deepcopy(source["animation"]), copy.deepcopy(current["animation"])
    if right and allow_new:
        right["drivers"] = {k: v for k, v in right["drivers"].items() if not k.startswith('nodes["' + PREFIX)}
        if left is None and right.get("action") is None and not right["drivers"] and not right["nla"]:
            right = None
    problems.extend(differences(left, right, "/original_animation"))
    for key, original in source["driver_values"].items():
        other = current["driver_values"].get(key)
        if other is None:
            problems.append({"path": "/driver_values/" + key, "kind": "missing_original_driver"})
        elif (original["actual"] != other["actual"]
              and (original["curve_sha256"] != other["curve_sha256"] or not original["verified"] or not other["verified"])):
            problems.append({"path": "/driver_values/" + key, "kind": "changed_evaluated_value_not_independently_verified"})
    return problems[:40]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "current", "preparation", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.output.exists():
        raise FileExistsError("Refusing to overwrite audit report: " + str(args.output))
    report = {"schema": "portrait-relight-independent-reopen-v1", "source": str(args.source), "current": str(args.current),
              "preparation": str(args.preparation), "script_sha256": sha(__file__), "frame": FRAME, "checks": [],
              "rendered": False, "saved_blend": False, "preferences_saved": False, "simulation_run": False,
              "scope": ["All named Actions including all key coordinates, handles, interpolation, modifiers, slots, groups, layers and channelbag routing; no sleeve/corrective exceptions",
                        "All mesh-object geometry, topology, UVs, attributes, weights, shape keys, material slots, modifiers, armature rest bones and posed settings at frame 4290",
                        "All original material nodes and nested node-group definitions; source-derived palette/rim/ink/fur destination link exceptions, plus separately checked Ikhor gold endpoint constants",
                        "Both actor Crypto IDs, hidden arcs/volumes, muted legacy File Outputs, image payloads/missing paths, color settings and MMD camera/driver preservation"],
              "limits": ["No exact replay or full semantic verification of newly added shader/compositor math", "New still lighting, stage grade, glow and camera DOF are art controls; DOF differences are reported separately", "No new render, dynamic simulation, collision, temporal stability, audio/video or user art approval is certified", "Object transforms and poses are sampled at frame 4290; unchanged complete Actions/constraints are compared independently"]}
    preference = Path(bpy.utils.user_resource("CONFIG")) / "userpref.blend"
    before = {"source": sha(args.source), "current": sha(args.current), "preferences": sha(preference) if preference.is_file() else None}
    def check(name, ok, detail=None):
        entry = {"name": name, "passed": bool(ok)}
        if detail is not None:
            entry["detail"] = detail
        report["checks"].append(entry)
    try:
        if before["source"] != SOURCE_SHA:
            raise ValueError("Source is not the pinned Clean-v2 SHA")
        preparation = json.loads(args.preparation.read_text(encoding="utf-8-sig"))
        check("pinned_source_and_preparation", preparation.get("source_sha256") == SOURCE_SHA)
        check("preparation_saved_project_sha", preparation.get("project_sha256") == before["current"])
        bpy.ops.wm.read_userpref()
        bpy.ops.preferences.addon_enable(module="bl_ext.blender_org.mmd_tools")
        source = cached_snapshot(args.source, True)
        current = cached_snapshot(args.current, False)
        gold_settings = preparation.get("settings", {}).get("physical_highlights", {})
        configured_gold = set(gold_settings.get("materials", []))
        check("exact_five_saved_gold_material_names", configured_gold == GOLD_MODIFIED_SAVED_NAMES and configured_gold <= set(source["gold_permissions"]), {"configured": sorted(configured_gold), "permitted_five": sorted(GOLD_MODIFIED_SAVED_NAMES), "all_source_gold_slots": sorted(source["gold_permissions"])})
        report["source_counts"], report["current_counts"] = source["counts"], current["counts"]
        for name in ("actions", "objects", "meshes", "armatures", "cameras", "worlds", "material_owners", "color", "render_engines", "physics_world", "actor_meshes", "compositors", "crypto"):
            delta = differences(source[name], current[name])
            check(name + "_strict_preservation", not delta, delta)
        check("exact_visible_actor_objects", current["actor_meshes"] == {a: [n] for a, n in ACTORS.items()})
        for scene, ids in current["crypto"].items():
            tokens = {s.strip().strip('"') for s in next(csv.reader([ids]))}
            check("both_actor_crypto_ids:" + scene, tokens == set(ACTORS.values()), sorted(tokens))
        check("crypto_node_present", bool(current["crypto"]))
        for label, names in (("removed_arcs_hidden", ARCS), ("eight_volumes_hidden", VOLUMES)):
            bad = {n: current["visibility"].get(n) for n in names if current["visibility"].get(n) != {"render": True, "viewport": True}}
            check(label, not bad, bad)
        non_art_visibility = {n: v for n, v in source["visibility"].items() if n not in VOLUMES | ARCS}
        check("other_visibility_preserved", non_art_visibility == {n: v for n, v in current["visibility"].items() if n not in VOLUMES | ARCS})
        old_outputs = set(source["file_outputs"])
        check("legacy_file_output_nodes_retained", old_outputs <= set(current["file_outputs"]))
        unmuted = [k.split("\0") for k, mute in current["file_outputs"].items() if not mute]
        check("all_file_outputs_muted", not unmuted, {"count": len(current["file_outputs"]), "unmuted": unmuted})
        camera_left = {k: v for k, v in source["camera"].items() if k != "dof"}
        camera_right = {k: v for k, v in current["camera"].items() if k != "dof"}
        check("mmd_camera_matrix_lens_drivers_at_4290", camera_left == camera_right, {"source": camera_left, "current": camera_right})
        report["dof_changes"] = differences(source["camera"]["dof"], current["camera"]["dof"])
        for name, mat in source["materials"].items():
            if name not in current["materials"]:
                check("material:" + name, False, "Original material missing")
                continue
            other = current["materials"][name]
            delta = differences(mat["settings"], other["settings"]) + differences(mat["animation"], other["animation"])
            endpoints = source["gold_permissions"].get(name, {}).get("endpoints", [])
            values = {(e["node"], e["input"]) for e in endpoints} if name in configured_gold else set()
            links = {tuple(item) for item in source["permissions"].get(name, ())}
            delta += protected_graph(mat["graph"], other["graph"], links, allow_new=name in source["permissions"], allowed_values=values)
            check("material:" + name, not delta, delta[:40])
            for endpoint in endpoints:
                target = float(gold_settings[endpoint["setting"]]) if name in configured_gold else endpoint["source_target"]
                node = other["graph"]["nodes"][endpoint["node"]]
                actual = float(node["inputs"][0]["value"])
                check("gold_endpoint:" + name + ":" + endpoint["setting"], abs(actual - (target - endpoint["base"])) < 1e-6,
                      {**endpoint, "modified_by_this_iteration": name in configured_gold, "requested_target": target, "actual_input0": actual, "actual_target": endpoint["base"] + actual})
        check("no_new_material_datablocks", set(current["materials"]) == set(source["materials"]))
        comp_names = set(source["compositors"].values())
        for name, old in source["groups"].items():
            if name not in current["groups"]:
                check("node_group:" + name, name in source["removable_groups"], "Removed zero-user group" if name in source["removable_groups"] else "Referenced source group missing")
                continue
            allowed = set()
            if name in comp_names:
                for node_name, node in old["nodes"].items():
                    if node["type"] == "NodeGroupOutput":
                        allowed.update((node_name, i) for i, s in enumerate(node["inputs"]) if s["name"] == "Image")
                    if node_name == "Caption cache | beauty":
                        allowed.update((node_name, i) for i, s in enumerate(node["inputs"]) if s["name"] == "beauty")
            delta = protected_graph(old, current["groups"][name], allowed, compositor=name in comp_names, allow_new=name in comp_names)
            check("node_group:" + name, not delta, delta)
        extra_groups = set(current["groups"]) - set(source["groups"])
        check("no_unreviewed_new_node_groups", not extra_groups, sorted(extra_groups))
        for name, old in source["images"].items():
            if name not in current["images"]:
                check("image:" + name, name in source["removable_images"], "Removed source zero-user image")
            else:
                delta = differences(old, current["images"][name])
                check("image:" + name, not delta, delta)
        missing = [n for n, i in current["images"].items() if i["missing_unpacked_file"]]
        check("no_missing_unpacked_image_files", not missing, missing)
        report["image_portability"] = {"file_images": sum(i["source"] == "FILE" for i in current["images"].values()),
                                      "packed_images": sum(i["packed"] for i in current["images"].values()), "missing_unpacked": missing}
        for name, old in source["lights"].items():
            other = current["lights"].get(name)
            if other is None:
                check("light:" + name, False, "Missing light")
                continue
            owners = {n for n, d in source["light_objects"].items() if d == name}
            fields = set()
            if owners & STAGE_LIGHTS:
                fields.add("energy")
            if any(n.startswith("Reference duet | ") and n.rsplit(" | ", 1)[-1] in {"key", "fill", "rim"} for n in owners):
                fields |= {"energy", "color", "size", "volume_factor", "specular_factor"}
            if any(n.startswith("Reference duet | ") and n.endswith(" | reflection") for n in owners):
                fields.add("specular_factor")
            delta = differences({k: v for k, v in old.items() if k not in fields}, {k: v for k, v in other.items() if k not in fields})
            check("light_protected_properties:" + name, not delta, delta)
        report["allowed_original_material_destinations"] = {n: sorted(v) for n, v in source["permissions"].items()}
        report["gold_endpoint_permissions"] = source["gold_permissions"]
        report["face_skin_ink_permission"] = "Only existing inverse-hull edge Color input may change; original Alpha, outline geometry/width/PMX weights and all separate eye/mouth feature nodes remain strict."
        report["driven_value_policy"] = "Only driver-controlled socket components are normalized. Every original driver curve/expression/variable/target remains strict; any changed evaluated scalar is independently recomputed from actual current WORLD lamp/head coordinates or ID properties and must agree within 1e-6."
        report["hidden_volume_evaluation_policy"] = "Saved hide states are captured first and checked true. Only the eight named stage volumes are temporarily viewport-enabled to evaluate their source/current matrices; they are restored without saving. Their authored transforms, geometry, drivers/modifiers remain strict; selection UI is excluded only on these eight."
        report["capture_cache_version"] = CAPTURE_VERSION
        report["old_material_nodes_compared"] = sum(len(m["graph"]["nodes"]) for m in source["materials"].values() if m["graph"])
    # Always emit a failure report, including unexpected Blender/RNA errors.
    except Exception as error:  # noqa: BLE001
        report["error"] = str(error)
        report["traceback"] = traceback.format_exc()
        check("audit_completed", False, str(error))
    after = {"source": sha(args.source), "current": sha(args.current), "preferences": sha(preference) if preference.is_file() else None}
    check("on_disk_inputs_and_preferences_unchanged", before == after, {"before": before, "after": after})
    report["passed"] = all(c["passed"] for c in report["checks"])
    report["failed_checks"] = [c["name"] for c in report["checks"] if not c["passed"]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("PORTRAIT_RELIGHT_INDEPENDENT_AUDIT", report["passed"], report["failed_checks"], flush=True)
    if not report["passed"]:
        raise RuntimeError("Portrait relight preservation audit failed; inspect " + str(args.output))


if __name__ == "__main__":
    main()
