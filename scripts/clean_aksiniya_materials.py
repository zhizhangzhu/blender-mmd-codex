"""Four reversible Aksiniya material modules for the pinned caption-fixed v7.

Public API: apply(scene, spec); set_module_enabled(scene, module, value).
Modules: palette, response_ramp, highlight_metal, rim. Zero physically restores
each original input link/default. No object/mesh/Action/image/light/stage/camera,
render setting, compositor, save, render or preference mutation occurs here.

The nose is a local island in the supplied FaceLightmap red channel, carried by
own SDF threshold -> .38+.62*SDF -> original key response -> palette. The repair
samples the SAME image at two adjacent mirrored-UV locations; only a small
original-UV nose permission blends that continuous field into the existing SDF.
Face sides, original threshold drivers, true combined key response, AO and mouth
crease stay in place. No final face brightness floor is introduced.
"""

import hashlib
import json
import math
from pathlib import Path

import bpy

PREFIX = "Clean Aksiniya | "
STATE = "clean_aksiniya_material_state"
MODULES = ("palette", "response_ramp", "highlight_metal", "rim")
SOURCE_SHA = "f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692"


def _number(value, label, low=0.0, high=None):
    value = float(value)
    if not math.isfinite(value) or value < low or high is not None and value > high:
        raise ValueError("Invalid " + label)
    return value


def _node(tree, kind, module, label):
    name = PREFIX + module + " | " + label
    if tree.nodes.get(name):
        raise ValueError("Refusing duplicate clean node: " + name)
    n = tree.nodes.new(kind)
    n.name = n.label = name
    n["clean_aksiniya_module"] = module
    return n


def _plug(tree, value, target):
    if hasattr(value, "is_output"):
        tree.links.new(value, target)
    else:
        target.default_value = value


def _math(tree, op, a, b, module, label):
    n = _node(tree, "ShaderNodeMath", module, label)
    n.operation = op
    _plug(tree, a, n.inputs[0])
    if b is not None:
        _plug(tree, b, n.inputs[1])
    return n.outputs[0]


def _vector(tree, op, a, b, module, label):
    n = _node(tree, "ShaderNodeVectorMath", module, label)
    n.operation = op
    _plug(tree, a, n.inputs[0])
    if b is not None:
        _plug(tree, b, n.inputs[3] if op == "SCALE" else n.inputs[1])
    return n.outputs["Value"] if op == "DOT_PRODUCT" else n.outputs[0]


def _range(tree, value, lo, hi, module, label):
    n = _node(tree, "ShaderNodeMapRange", module, label)
    n.clamp, n.interpolation_type = True, "SMOOTHSTEP"
    for source, key in ((value, "Value"), (lo, "From Min"), (hi, "From Max")):
        _plug(tree, source, n.inputs[key])
    return n.outputs["Result"]


def _descriptor(socket):
    return {"node": socket.node.name, "index": list(socket.node.outputs).index(socket),
            "identifier": socket.identifier}


def _input_value(socket):
    if socket.is_linked:
        return socket.links[0].from_socket
    value = socket.default_value
    return list(value) if hasattr(value, "__len__") and not isinstance(value, str) else value


def _original(socket):
    value = _input_value(socket)
    return {"source": _descriptor(value)} if hasattr(value, "is_output") else {"default": value}


def _wrap(tree, target, modified, module, controls, records, label):
    original = _original(target)
    old = _input_value(target)
    if module not in controls:
        enable = _node(tree, "ShaderNodeValue", module, "enable")
        enable.outputs[0].default_value = 1
        controls[module] = enable
    if target.type == "VALUE":
        delta = _math(tree, "SUBTRACT", modified, old, module, label + " delta")
        selected = _math(tree, "ADD", old,
                         _math(tree, "MULTIPLY", delta, controls[module].outputs[0], module, label + " enabled delta"),
                         module, label + " selected")
    elif target.type == "RGBA":
        mix = _node(tree, "ShaderNodeMixRGB", module, label + " selected")
        mix.blend_type = "MIX"
        _plug(tree, controls[module].outputs[0], mix.inputs[0])
        _plug(tree, old, mix.inputs[1])
        _plug(tree, modified, mix.inputs[2])
        selected = mix.outputs[0]
    else:
        raise ValueError("Unsupported clean target socket: " + target.type)
    tree.links.new(selected, target)
    records.append({"module": module, "target_node": target.node.name,
                    "target_input": list(target.node.inputs).index(target), "original": original,
                    "final": _descriptor(selected), "control": controls[module].name, "label": label})


def _materials(scene):
    return {m.name: m for o in scene.objects if o.type == "MESH"
            and o.get("performer_id") == "aksiniya" and not o.hide_render
            for m in o.data.materials if m and m.node_tree}


def _assert_exclusive(scene, material):
    other = [o.name for o in scene.objects if o.type == "MESH"
             and material in o.data.materials[:]
             and o.get("performer_id") != "aksiniya"]
    if other:
        raise ValueError("Refusing shared actor/stage material: " + material.name + " / " + repr(other))


def _palette(tree, material, config, controls, records):
    role = material.get("character_layer_role")
    if role not in config["roles"]:
        return
    old = tree.nodes.get("Reference transfer | designed two color palette")
    target = tree.nodes.get("Reference transfer | shading bypass")
    if not old or not target or not old.inputs[0].is_linked:
        raise ValueError("Missing audited palette contract: " + material.name)
    n = _node(tree, "ShaderNodeValToRGB", "palette", "separate " + role + " values")
    n.color_ramp.interpolation = "EASE"
    points = config["roles"][role]
    while len(n.color_ramp.elements) < len(points):
        n.color_ramp.elements.new(0.5)
    for e, point in zip(n.color_ramp.elements, points):
        e.position, e.color = point["position"], point["rgba"]
    tree.links.new(old.inputs[0].links[0].from_socket, n.inputs[0])
    _wrap(tree, target.inputs[2], n.outputs[0], "palette", controls, records, role + " palette")


def _nose(tree, material, config, controls, records):
    if material.get("character_layer_role") != "face" or material.name not in config["materials"]:
        return None
    sdf = tree.nodes.get("Genshin study | own SDF threshold")
    image = tree.nodes.get("Genshin study | supplied model FaceLightmap")
    uv = tree.nodes.get("mmd_tex_uv")
    active = tree.nodes.get("Reference transfer | soft face form before occlusion")
    minimum = tree.nodes.get("Character layers | SDF and native light combined once")
    if not all((sdf, image, uv, active, minimum)) or not image.image or not image.inputs[0].is_linked:
        raise ValueError("Missing actual Aksiniya SDF nose contract: " + material.name)
    crease = tree.nodes.get("Face ink | Mouth crease")
    if not crease:
        raise ValueError("Missing protected mouth crease")
    center, radius = config["nose_uv_center"], config["nose_uv_radius"]
    if len(center) != 2 or len(radius) != 2 or radius[0] <= 0 or radius[1] <= 0:
        raise ValueError("Invalid nose UV ellipse")
    if center[1] - radius[1] <= 0.345 or center[1] + radius[1] >= 0.55:
        raise ValueError("Nose permission must exclude the known mouth strip and eye region")
    split = _node(tree, "ShaderNodeSeparateXYZ", "response_ramp", "original face UV")
    tree.links.new(uv.outputs["Base UV"], split.inputs[0])
    squared = []
    for i, axis in enumerate(("X", "Y")):
        delta = _math(tree, "SUBTRACT", split.outputs[axis], center[i], "response_ramp", axis + " nose delta")
        scaled = _math(tree, "DIVIDE", delta, radius[i], "response_ramp", axis + " nose radius")
        squared.append(_math(tree, "MULTIPLY", scaled, scaled, "response_ramp", axis + " nose distance squared"))
    distance = _math(tree, "ADD", *squared, "response_ramp", "nose ellipse distance squared")
    feather = _range(tree, distance, config["nose_inner_squared"], 1.0, "response_ramp", "nose feather")
    permission = _math(tree, "SUBTRACT", 1.0, feather, "response_ramp", "local nose permission")
    amount = _math(tree, "MULTIPLY", permission, config["nose_repair_strength"], "response_ramp", "nose repair amount")
    samples = []
    mapped = image.inputs[0].links[0].from_socket
    for side, sign in (("left", -1), ("right", 1)):
        vector = _vector(tree, "ADD", mapped, (sign * config["sdf_sample_offset_u"], 0, 0),
                         "response_ramp", side + " adjacent same-SDF UV")
        tex = _node(tree, "ShaderNodeTexImage", "response_ramp", side + " same supplied SDF")
        tex.image = image.image
        tex.interpolation, tex.extension, tex.projection = image.interpolation, image.extension, image.projection
        tex.projection_blend = image.projection_blend
        tree.links.new(vector, tex.inputs[0])
        channels = _node(tree, "ShaderNodeSeparateColor", "response_ramp", side + " SDF red")
        channels.mode = "RGB"
        tree.links.new(tex.outputs["Color"], channels.inputs[0])
        samples.append(channels.outputs["Red"])
    average = _math(tree, "MULTIPLY", _math(tree, "ADD", *samples, "response_ramp", "adjacent SDF sum"),
                    0.5, "response_ramp", "continuous low-frequency nose SDF")
    remap = _node(tree, "ShaderNodeMapRange", "response_ramp", "same dynamic SDF threshold")
    remap.clamp, remap.interpolation_type = sdf.clamp, sdf.interpolation_type
    tree.links.new(average, remap.inputs["Value"])
    for name in ("From Min", "From Max", "To Min", "To Max"):
        _plug(tree, _input_value(sdf.inputs[name]), remap.inputs[name])
    delta = _math(tree, "SUBTRACT", remap.outputs["Result"], sdf.outputs["Result"], "response_ramp", "local SDF replacement delta")
    repaired = _math(tree, "ADD", sdf.outputs["Result"],
                     _math(tree, "MULTIPLY", delta, amount, "response_ramp", "only nose replacement"),
                     "response_ramp", "nose repaired with unchanged face sides")
    # Only the SDF inputs are wrapped. The .38 form scalar, key-facing response,
    # contact AO, source Color/Alpha and mouth-crease Color remain untouched.
    for n, index in ((minimum, 1), (tree.nodes.get("Reference transfer | MULTIPLY"), 0)):
        if n is None or not n.inputs[index].is_linked or n.inputs[index].links[0].from_socket != sdf.outputs["Result"]:
            raise ValueError("Unexpected source SDF consumer")
        _wrap(tree, n.inputs[index], repaired, "response_ramp", controls, records, n.name + " SDF")
    return {"material": material.name, "sdf_image": image.image.name, "raw_sdf": sdf.name,
            "nose_source": "supplied FaceLightmap red-channel nose island; base FaceDiffuse has only a light nose mark",
            "mask": {"center": center, "radius": radius}, "form_floor_unchanged": active.inputs[0].default_value,
            "key_response_unchanged": "Reference transfer | key facing response",
            "mouth_unchanged": crease.name, "outside_nose_sdf_exact": True}


def _highlight(tree, material, config, controls, records):
    if material.get("character_layer_role") == "hair":
        target = tree.nodes.get("Character layers | one directional hair highlight")
        if target and target.inputs[0].is_linked:
            old = _input_value(target.inputs[0])
            mask = tree.nodes.get("Surface | mask channels")
            permission = 1.0
            if mask:
                permission = _math(tree, "ADD", config["hair_strand_floor"],
                                   _math(tree, "MULTIPLY", mask.outputs["Blue"], 1 - config["hair_strand_floor"],
                                         "highlight_metal", "existing Blue strand modulation"),
                                   "highlight_metal", "existing strand permission")
            gain = _math(tree, "MULTIPLY", permission, config["hair_highlight_gain"], "highlight_metal", "hair band gain")
            modified = _math(tree, "MULTIPLY", old, gain, "highlight_metal", "restrained original hair highlight")
            _wrap(tree, target.inputs[0], modified, "highlight_metal", controls, records, "existing hair band")
    gold = tree.nodes.get("Surface | masked gold response")
    if gold and gold.type == "BSDF_PRINCIPLED":
        rough = _math(tree, "ADD", _math(tree, "MULTIPLY", _input_value(gold.inputs["Roughness"]),
                                       config["gold_roughness_scale"], "highlight_metal", "original gold roughness scale"),
                      config["gold_roughness_offset"], "highlight_metal", "gold roughness offset")
        clamp = _node(tree, "ShaderNodeClamp", "highlight_metal", "bounded existing gold roughness")
        _plug(tree, rough, clamp.inputs[0])
        clamp.inputs[1].default_value, clamp.inputs[2].default_value = config["gold_roughness_bounds"]
        _wrap(tree, gold.inputs["Roughness"], clamp.outputs[0], "highlight_metal", controls, records, "gold closure roughness")


def _edge(tree, material, spec, controls, records):
    name = material.name
    if name in spec["highlight_metal"]["hair_outline_materials"]:
        module, rgb = "highlight_metal", spec["highlight_metal"]["hair_line_rgb"]
    elif name in spec["palette"]["fur_outline_materials"]:
        module, rgb = "palette", spec["palette"]["fur_line_rgb"]
    else:
        return
    group = tree.nodes.get("mmd_edge_preview")
    if not group or group.inputs["Color"].is_linked:
        raise ValueError("Unexpected protected outline Color contract: " + name)
    old = list(group.inputs["Color"].default_value)
    _wrap(tree, group.inputs["Color"], (*rgb, old[3]), module, controls, records, "lower contrast line RGB only")


def _rim(tree, material, config, controls, records):
    role = material.get("character_layer_role")
    if role not in {"hair", "fur", "cloth", "trim", "gold", "leather"}:
        return
    geometry = tree.nodes.get("Reference transfer | surface geometry")
    direction = tree.nodes.get("Reference transfer | rim direction")
    target = tree.nodes.get("Reference transfer | controlled rim amount")
    if not all((geometry, direction, target)):
        raise ValueError("Missing existing directional rim contract: " + material.name)
    normalized = _vector(tree, "NORMALIZE", direction.outputs[0], None, "rim", "original rim direction normalized")
    dot = _vector(tree, "DOT_PRODUCT", geometry.outputs["Normal"], normalized, "rim", "existing rim facing")
    gate = _range(tree, dot, *config["direction_gate"], "rim", "only back-side rim permission")
    gain = config["reference_hair_gain"] if role == "hair" else config["reference_body_gain"]
    amount = _math(tree, "MULTIPLY", _input_value(target.inputs[0]),
                   _math(tree, "MULTIPLY", gate, gain, "rim", "reference rim directional gain"),
                   "rim", "restrained reference rim and its original AOV")
    _wrap(tree, target.inputs[0], amount, "rim", controls, records, "Reference rim before all consumers")
    for label, gain_key in (("aksiniya_head_rim", "bold_head_gain"), ("aksiniya_body_rim", "bold_body_gain")):
        hdr = tree.nodes.get("Bold wedding material | " + label + " HDR amount")
        if hdr:
            scaled = _math(tree, "MULTIPLY", _input_value(hdr.inputs[1]), config[gain_key], "rim", label + " reduced HDR strength")
            scaled = _math(tree, "MULTIPLY", scaled, gate, "rim", label + " directional permission")
            _wrap(tree, hdr.inputs[1], scaled, "rim", controls, records, label + " before NPR and Alpha AOV")


def apply(scene, spec):
    """Install the four material-only modules, returning serializable evidence."""
    path = Path(bpy.data.filepath)
    if spec.get("verify_source_hash", True):
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != spec.get("source_sha256", SOURCE_SHA) or digest != SOURCE_SHA:
            raise ValueError("Clean Aksiniya accepts only the pinned caption-fixed v7 source")
    for module in MODULES:
        if module not in spec:
            raise ValueError("Missing module settings: " + module)
    _number(spec["response_ramp"]["nose_repair_strength"], "nose repair strength", high=1)
    mats = _materials(scene)
    targets = [m for m in mats.values() if m.get("character_layer_role") in
               {"face", "hair", "fur", "cloth", "trim", "gold", "leather"}
               or m.name in spec["highlight_metal"]["hair_outline_materials"]
               or m.name in spec["palette"]["fur_outline_materials"]]
    for material in targets:
        _assert_exclusive(scene, material)
        if STATE in material:
            raise ValueError("Refusing repeated clean installation: " + material.name)
    report = {"id": spec["id"], "modules": list(MODULES), "materials": [], "nose_evidence": [],
              "source": str(path), "saved": False, "rendered": False,
              "stage_camera_lights_exposure_modified": False, "geometry_actions_shapes_modified": False,
              "source_images_or_mmd_ColorAlpha_sphere_modified": False,
              "new_aovs": [], "compositor_or_crypto_modified": False}
    for material in sorted(targets, key=lambda m: m.name):
        tree, controls, records = material.node_tree, {}, []
        if material.name.startswith("mmd_edge."):
            _edge(tree, material, spec, controls, records)
        else:
            _palette(tree, material, spec["palette"], controls, records)
            nose = _nose(tree, material, spec["response_ramp"], controls, records)
            if nose:
                report["nose_evidence"].append(nose)
            _highlight(tree, material, spec["highlight_metal"], controls, records)
            _rim(tree, material, spec["rim"], controls, records)
        if records:
            state = {"id": spec["id"], "targets": records,
                     "enabled": {m: float(spec[m].get("enabled", True)) for m in controls}}
            material[STATE] = json.dumps(state, ensure_ascii=False)
            report["materials"].append({"name": material.name, "role": material.get("character_layer_role"),
                                        "targets": records})
    for module in MODULES:
        set_module_enabled(scene, module, spec[module].get("enabled", True))
    report["counts"] = {"materials": len(report["materials"]),
                         "targets": sum(len(m["targets"]) for m in report["materials"]),
                         "face_materials": len(report["nose_evidence"])}
    if sorted(r["material"] for r in report["nose_evidence"]) != sorted(spec["response_ramp"]["materials"]):
        raise ValueError("Expected exactly the original SDF-bearing face material; overlay remains untouched")
    return report


def set_module_enabled(scene, module, value):
    """0 restores original socket links/defaults; 0..1 controls installed delta."""
    if module not in MODULES:
        raise ValueError("Unknown clean Aksiniya module: " + str(module))
    value = _number(value, "module value", high=1)
    changed = []
    for material in _materials(scene).values():
        if STATE not in material:
            continue
        state = json.loads(material[STATE])
        tree = material.node_tree
        for target in state["targets"]:
            if target["module"] != module:
                continue
            tree.nodes[target["control"]].outputs[0].default_value = value
            socket = tree.nodes[target["target_node"]].inputs[target["target_input"]]
            descriptor = target["final"] if value else target["original"].get("source")
            for link in list(socket.links):
                tree.links.remove(link)
            if descriptor:
                tree.links.new(tree.nodes[descriptor["node"]].outputs[descriptor["index"]], socket)
            else:
                socket.default_value = target["original"]["default"]
            changed.append({"material": material.name, "target": target["label"], "value": value})
        if module in state["enabled"]:
            state["enabled"][module] = value
            material[STATE] = json.dumps(state, ensure_ascii=False)
    return changed
