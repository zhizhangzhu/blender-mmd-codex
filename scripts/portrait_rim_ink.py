"""Reversible narrow warm rims and existing inverse-hull ink for Clean v2.

API: apply(scene, settings=None), set_module_enabled(scene, "rim"/"ink", 0..1),
set_gain(scene, 0..1), remove(scene). Zero physically restores intercepted
input links AND defaults; remove also deletes this module's nodes and state.
Only the exact actor material slots below are accepted. No save, render,
preferences, lights, compositor, geometry, modifiers, weights or Actions change.

The new RGB replaces the audited *additive HDR rim source*, including every
existing beauty/AOV consumer. Aksiniya's separate SCREEN rim is attenuated at
its own scalar control; SCREEN Fac is never treated as HDR radiance. Motifs,
MMD Color/Alpha/sphere, physical closures and facial features remain intact.
HDR gain, grazing power (width), side direction and tint are separate controls.
Camera-space directions are frozen into WORLD directions when apply is called,
so this is an art light with a fixed direction, not a light following the camera.

Reused short-distance AO suppresses contact rims; it is NOT directional shadow
visibility, depth rim, a game shadow map or a guarantee against leakage. Normal
depth testing still hides occluded geometry. Hand/body and actor intersections
require actual image review. No new lighting probe or second AO is introduced.
"""

import copy
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

PREFIX = "Portrait relight | rimink | "
STATE = "portrait_rim_ink_state"
SOURCE = Path(
    "D:/codex/output/MMD-Clean-Game-Characters-v1/production-v2/"
    "Franken_Duet_Clean_Game.blend"
)
SOURCE_SHA256 = "0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4"
ACTOR_OBJECTS = {
    "aksiniya": "阿克西妮娅2_mesh",
    "ikhor": "Ikhor | mesh | Ikhor_mesh",
}
ARCS = ("Bold wedding | blue vow arc", "Bold wedding | gold vow arc")

# Exact saved names -> source PMX name, saved role, new rim settings group.
RIM_TARGETS = {
    "aksiniya": {
        **{name: (name, "hair", "hair") for name in ("前鬓", "呆毛", "鬓")},
        "毛领": ("毛领", "fur", "fur"),
        **{name: (name, "cloth", "body") for name in ("帽", "披肩", "腿", "衣", "裙")},
        **{name: (name, "trim", "body") for name in ("前装饰", "后装饰", "头饰")},
    },
    "ikhor": {
        "鬓.001": ("鬓", "hair", "hair"),
        "带子": ("带子", "cloth", "body"),
        "衣.001": ("衣", "cloth", "body"),
        "衣2": ("衣2", "cloth", "body"),
        "衣领": ("衣领", "cloth", "body"),
        "裙.001": ("裙", "cloth", "body"),
    },
}
INK_TARGETS = {
    "aksiniya": {
        **{"mmd_edge." + name: "hair" for name in ("前鬓", "呆毛", "鬓")},
        "mmd_edge.毛领": "fur",
        **{
            "mmd_edge." + name: "cloth"
            for name in ("衣", "裙", "腿", "披肩", "头饰", "前装饰", "后装饰")
        },
        "mmd_edge.颜": "face",
        "mmd_edge.首": "skin",
        "mmd_edge.手": "skin",
    },
    "ikhor": {
        "mmd_edge.鬓.001": "hair",
        **{
            "mmd_edge." + name: "cloth"
            for name in (
                "带子",
                "衣.001",
                "衣2",
                "衣领",
                "衣饰",
                "裙.001",
                "裤",
                "靴",
                "靴底",
                "靴饰",
            )
        },
        "mmd_edge.颜.001": "face",
        "mmd_edge.首.001": "skin",
        "mmd_edge.手.001": "skin",
    },
}


def _rim_defaults(power, gain):
    return {
        "power": power,
        "hdr_gain": gain,
        "left_color": [1.0, 0.74, 0.66],
        "right_color": [1.0, 0.84, 0.76],
        "left_gain": 1.0,
        "right_gain": 0.22,
    }


DEFAULT_SETTINGS = {
    "id": "portrait-rim-ink-v1",
    "verify_source_hash": True,
    "rim": {
        "enabled": 1.0,
        "reference_screen_gain": 0.0,
        # Camera-local +X right, +Y up, +Z toward viewer. Negative Z is rear.
        "left_direction_camera": [-1.0, 0.38, -0.40],
        "right_direction_camera": [1.0, 0.25, -0.55],
        "direction_gate": [0.10, 0.72],
        # Optional independent silhouette permission in abs(N dot View).
        # None preserves the original v1 power-only shape exactly.
        "view_edge_range": None,
        "contact_ao_range": [0.35, 0.90],
        "headroom_luminance_range": [0.70, 1.60],
        "highlight_retention": 0.45,
        "actors": {
            "aksiniya": {
                "hair": _rim_defaults(10.0, 2.1),
                "body": _rim_defaults(12.0, 1.7),
                "fur": _rim_defaults(13.0, 1.45),
            },
            "ikhor": {
                "hair": _rim_defaults(10.0, 1.9),
                "body": _rim_defaults(12.0, 1.6),
            },
        },
        # Exact whitelisted names only; any group key above may be overridden.
        "material_overrides": {},
    },
    "ink": {
        "enabled": 1.0,
        "actors": {
            "aksiniya": {
                "hair": {"color": [0.008, 0.011, 0.022], "strength": 1.0},
                "fur": {"color": [0.014, 0.017, 0.027], "strength": 1.0},
                "cloth": {"color": [0.007, 0.009, 0.018], "strength": 0.40},
                "face": {"color": [0.012, 0.010, 0.018], "strength": 0.0},
                "skin": {"color": [0.012, 0.010, 0.018], "strength": 0.0},
            },
            "ikhor": {
                "hair": {"color": [0.006, 0.008, 0.015], "strength": 0.70},
                "cloth": {"color": [0.006, 0.008, 0.016], "strength": 0.40},
                "face": {"color": [0.012, 0.010, 0.018], "strength": 0.0},
                "skin": {"color": [0.012, 0.010, 0.018], "strength": 0.0},
            },
        },
        "material_overrides": {},
    },
}


def _plain(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return [_plain(item) for item in value]


def _number(value, label, low=0.0, high=1.0):
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Invalid finite " + label)
    return value


def _color(value, label):
    if len(value) != 3:
        raise ValueError("Expected three linear RGB components: " + label)
    return [_number(v, label) for v in value]


def _merge(base, changes):
    result = copy.deepcopy(base)
    for key, value in changes.items():
        if key not in result:
            raise ValueError("Unknown portrait rim/ink setting: " + str(key))
        if key == "material_overrides":
            if not isinstance(value, dict):
                raise TypeError("material_overrides must be an object")
            result[key] = copy.deepcopy(value)
        elif isinstance(result[key], dict):
            if not isinstance(value, dict):
                raise TypeError("Expected settings object: " + key)
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _validate(settings):
    rim = settings["rim"]
    for module in ("rim", "ink"):
        _number(settings[module]["enabled"], module + " enabled")
        allowed = set().union(
            *(
                set(d)
                for d in (RIM_TARGETS if module == "rim" else INK_TARGETS).values()
            )
        )
        extra = set(settings[module]["material_overrides"]) - allowed
        if extra:
            raise ValueError("Unlicensed material override: " + repr(sorted(extra)))
    _number(rim["reference_screen_gain"], "SCREEN relative attenuation")
    _number(rim["highlight_retention"], "highlight retention")
    if rim["view_edge_range"] is not None:
        lo, hi = rim["view_edge_range"]
        _number(lo, "view-edge full cosine")
        _number(hi, "view-edge zero cosine")
        if not lo < hi:
            raise ValueError("Expected increasing view-edge cosine range")
    for key in ("direction_gate", "contact_ao_range", "headroom_luminance_range"):
        lo, hi = rim[key]
        _number(lo, key, -1.0 if key == "direction_gate" else 0.0, 8.0)
        _number(hi, key, 0.0, 8.0)
        if not lo < hi:
            raise ValueError("Expected increasing range: " + key)
    for key in ("left_direction_camera", "right_direction_camera"):
        direction = rim[key]
        if len(direction) != 3 or not all(math.isfinite(float(x)) for x in direction):
            raise ValueError("Invalid camera-space rim direction")
        if Vector(direction).length < 0.001:
            raise ValueError("Zero rim direction")
    for actor, targets in RIM_TARGETS.items():
        for name, (_, _, group) in targets.items():
            spec = _merge(
                rim["actors"][actor][group], rim["material_overrides"].get(name, {})
            )
            _number(spec["power"], "grazing power", 2.0, 48.0)
            _number(spec["hdr_gain"], "linear HDR gain", 0.0, 8.0)
            for side in ("left", "right"):
                _color(spec[side + "_color"], "linear " + side + " rim tint")
                _number(spec[side + "_gain"], side + " gain", 0.0, 2.0)
    for actor, targets in INK_TARGETS.items():
        for name, group in targets.items():
            spec = _merge(
                settings["ink"]["actors"][actor][group],
                settings["ink"]["material_overrides"].get(name, {}),
            )
            _color(spec["color"], "linear ink RGB")
            _number(spec["strength"], "ink color replacement fraction")


def _required(tree, name, kind=None):
    node = tree.nodes.get(name)
    if not node or kind and node.bl_idname != kind:
        raise ValueError("Missing audited portrait rim/ink node: " + name)
    return node


def _source(socket):
    if socket.is_linked:
        if len(socket.links) != 1:
            raise ValueError("Expected single-link material input")
        return socket.links[0].from_socket
    return _plain(socket.default_value)


def _descriptor(socket, output=True):
    return {
        "node": socket.node.name,
        "index": list(socket.node.outputs if output else socket.node.inputs).index(
            socket
        ),
        "identifier": socket.identifier,
    }


def _node(tree, kind, module, label):
    name = PREFIX + label
    if len(name.encode("utf-8")) > 62:
        raise ValueError("Node label exceeds Blender's stable name limit: " + name)
    if tree.nodes.get(name):
        raise ValueError("Refusing repeated portrait rim/ink node: " + name)
    node = tree.nodes.new(kind)
    node.name = node.label = name
    node["portrait_rim_ink_module"] = module
    return node


def _plug(tree, value, socket):
    if hasattr(value, "is_output"):
        tree.links.new(value, socket)
    else:
        socket.default_value = value


def _math(tree, op, first, second, label):
    node = _node(tree, "ShaderNodeMath", "rim", label)
    node.operation, node.use_clamp = op, False
    _plug(tree, first, node.inputs[0])
    if second is not None:
        _plug(tree, second, node.inputs[1])
    return node.outputs[0]


def _vector(tree, op, first, second, label):
    node = _node(tree, "ShaderNodeVectorMath", "rim", label)
    node.operation = op
    _plug(tree, first, node.inputs[0])
    if second is not None:
        _plug(tree, second, node.inputs[3] if op == "SCALE" else node.inputs[1])
    return node.outputs["Value"] if op == "DOT_PRODUCT" else node.outputs[0]


def _range(tree, value, limits, label):
    node = _node(tree, "ShaderNodeMapRange", "rim", label)
    node.clamp, node.interpolation_type = True, "SMOOTHSTEP"
    _plug(tree, value, node.inputs["Value"])
    node.inputs["From Min"].default_value = limits[0]
    node.inputs["From Max"].default_value = limits[1]
    return node.outputs["Result"]


def _wrap(tree, target, replacement, module, controls, records, label, fraction=1.0):
    old = _source(target)
    original = {"default": _plain(target.default_value)}
    if hasattr(old, "is_output"):
        original["source"] = _descriptor(old)
    if module not in controls:
        control = _node(tree, "ShaderNodeValue", module, module + " enabled")
        control.outputs[0].default_value = 1.0
        controls[module] = control
    fac = controls[module].outputs[0]
    if fraction != 1:
        node = _node(tree, "ShaderNodeMath", module, label + " local strength")
        node.operation = "MULTIPLY"
        _plug(tree, fac, node.inputs[0])
        node.inputs[1].default_value = fraction
        fac = node.outputs[0]
    if target.type == "VALUE":
        delta = _math(tree, "SUBTRACT", replacement, old, label + " delta")
        delta = _math(tree, "MULTIPLY", delta, fac, label + " gated")
        selected = _math(tree, "ADD", old, delta, label + " selected")
    elif target.type in {"RGBA", "VECTOR"}:
        node = _node(tree, "ShaderNodeMixRGB", module, label + " selected")
        node.blend_type, node.use_clamp = "MIX", False
        _plug(tree, fac, node.inputs[0])
        _plug(tree, old, node.inputs[1])
        _plug(tree, replacement, node.inputs[2])
        selected = node.outputs[0]
    else:
        raise ValueError("Unsupported material interception socket: " + target.type)
    tree.links.new(selected, target)
    records.append(
        {
            "module": module,
            "target": _descriptor(target, False),
            "original": original,
            "final": _descriptor(selected),
            "control": controls[module].name,
            "label": label,
        }
    )


def _actor_contract(scene):
    actors = {}
    for actor, name in ACTOR_OBJECTS.items():
        meshes = [
            o
            for o in scene.objects
            if o.type == "MESH" and o.get("performer_id") == actor and not o.hide_render
        ]
        if len(meshes) != 1 or meshes[0].name != name:
            raise ValueError("Unexpected visible portrait actor mesh: " + actor)
        actors[actor] = meshes[0]
    for name in ARCS:
        obj = scene.objects.get(name)
        if not obj or not obj.hide_render or not obj.hide_viewport:
            raise ValueError("Both already removed wedding arcs must remain hidden")
    return actors


def _material_contract(scene, actors, actor, name, identity=None):
    material = bpy.data.materials.get(name)
    if (
        not material
        or not material.node_tree
        or material not in actors[actor].data.materials[:]
    ):
        raise ValueError("Missing exact actor material slot: " + name)
    users = [
        o for o in scene.objects if o.type == "MESH" and material in o.data.materials[:]
    ]
    if any(o.get("performer_id") != actor for o in users):
        raise ValueError("Refusing shared actor/stage material: " + name)
    if STATE in material or any(
        n.name.startswith(PREFIX) for n in material.node_tree.nodes
    ):
        raise ValueError("Refusing repeated portrait rim/ink install: " + name)
    if identity:
        source, role, _ = identity
        role_key = (
            "character_layer_role" if actor == "aksiniya" else "ikhor_material_role"
        )
        if (
            material.get("performer_id") != actor
            or material.get("source_mmd_material_name") != source
            or material.get(role_key) != role
        ):
            raise ValueError("Portrait rim material identity mismatch: " + name)
        _required(material.node_tree, "mmd_shader", "ShaderNodeGroup")
    else:
        edge = _required(material.node_tree, "mmd_edge_preview", "ShaderNodeGroup")
        if edge.inputs["Alpha"].is_linked:
            raise ValueError("Unexpected animated outline Alpha: " + name)
    return material


def _rim_contract(material, actor):
    tree = material.node_tree
    if actor == "aksiniya":
        prefix = "Reference transfer | "
        geometry = _required(tree, prefix + "surface geometry", "ShaderNodeNewGeometry")
        screen = _required(
            tree, prefix + "controlled emissive edge", "ShaderNodeMixRGB"
        )
        if screen.blend_type != "SCREEN":
            raise ValueError("Aksiniya SCREEN branch changed")
        candidates = [
            tree.nodes.get("Bold wedding material | " + group + " HDR source")
            for group in ("aksiniya_head_rim", "aksiniya_body_rim")
        ]
        candidates = [n for n in candidates if n]
        if len(candidates) != 1:
            raise ValueError("Expected one exact additive Aksiniya rim source")
        rgb = candidates[0]
        source = _source(screen.inputs[1])
        ao = _required(
            tree, "Character layers | single contact AO", "ShaderNodeAmbientOcclusion"
        )
        screen_amount = _required(
            tree, prefix + "controlled rim amount", "ShaderNodeMath"
        )
        if screen_amount.operation != "MULTIPLY":
            raise ValueError("Aksiniya SCREEN Fac contract changed")
        permission = 1.0
    else:
        prefix = "Ikhor character | "
        geometry = _required(tree, prefix + "geometry", "ShaderNodeNewGeometry")
        rgb = _required(tree, prefix + "rim RGB", "ShaderNodeVectorMath")
        source = _source(
            _required(
                tree,
                prefix + "unclamped narrow rim application",
                "ShaderNodeVectorMath",
            ).inputs[0]
        )
        ao = _required(
            tree, prefix + "single short contact AO", "ShaderNodeAmbientOcclusion"
        )
        screen_amount = None
        # Preserve the actual original white-cloth permission and its exclusions.
        permission_node = _required(
            tree, "Clean Ikhor | rim permission", "ShaderNodeMath"
        )
        permission = _source(permission_node.inputs[1])
    if (
        rgb.bl_idname != "ShaderNodeVectorMath"
        or rgb.operation != "SCALE"
        or not rgb.outputs[0].links
    ):
        raise ValueError("Expected active additive RGB rim source: " + material.name)
    if not hasattr(source, "is_output") or "AO" not in ao.outputs:
        raise ValueError("Missing active pre-rim shaded source or original short AO")
    destinations = [link.to_socket for link in rgb.outputs[0].links]
    return (
        geometry,
        rgb,
        source,
        ao.outputs["AO"],
        permission,
        screen_amount,
        destinations,
    )


def _warm_rim(tree, geometry, shaded, ao, spec, settings, directions):
    normal = _vector(
        tree, "NORMALIZE", geometry.outputs["Normal"], None, "unit surface normal"
    )
    incoming = _vector(
        tree, "NORMALIZE", geometry.outputs["Incoming"], None, "unit view incoming"
    )
    facing = _vector(tree, "DOT_PRODUCT", normal, incoming, "view cosine")
    facing = _math(tree, "ABSOLUTE", facing, None, "absolute facing")
    grazing = _math(tree, "SUBTRACT", 1.0, facing, "grazing angle")
    grazing = _math(tree, "MAXIMUM", grazing, 0.0, "positive grazing angle")
    edge = _math(tree, "POWER", grazing, spec["power"], "width power only")
    if settings["view_edge_range"] is not None:
        outside = _range(tree, facing, settings["view_edge_range"], "view edge exits")
        permission = _math(
            tree, "SUBTRACT", 1.0, outside, "bounded view edge permission"
        )
        edge = _math(tree, "MULTIPLY", edge, permission, "power within view edge")
    contact = _range(tree, ao, settings["contact_ao_range"], "contact suppression")
    luma = _node(tree, "ShaderNodeRGBToBW", "rim", "pre rim luminance")
    _plug(tree, shaded, luma.inputs[0])
    highlight = _range(
        tree, luma.outputs[0], settings["headroom_luminance_range"], "highlight usage"
    )
    headroom = _math(
        tree,
        "MULTIPLY",
        highlight,
        1 - settings["highlight_retention"],
        "highlight reduction",
    )
    headroom = _math(tree, "SUBTRACT", 1.0, headroom, "remaining HDR headroom")
    mask = _math(tree, "MULTIPLY", edge, contact, "edge without contacts")
    mask = _math(tree, "MULTIPLY", mask, headroom, "edge with headroom")
    combined = None
    for side in ("left", "right"):
        dot = _vector(
            tree, "DOT_PRODUCT", normal, directions[side], side + " direction cosine"
        )
        gate = _range(tree, dot, settings["direction_gate"], side + " rear side gate")
        amount = _math(tree, "MULTIPLY", mask, gate, side + " narrow permission")
        amount = _math(
            tree,
            "MULTIPLY",
            amount,
            spec["hdr_gain"] * spec[side + "_gain"],
            side + " HDR gain only",
        )
        rgb = _vector(
            tree, "SCALE", spec[side + "_color"], amount, side + " warm HDR RGB"
        )
        combined = (
            rgb
            if combined is None
            else _vector(tree, "ADD", combined, rgb, "two side HDR RGB")
        )
    return combined


def _install_rim(
    material, actor, spec, settings, directions, controls, records, contract
):
    tree = material.node_tree
    geometry, rgb, source, ao, permission, screen_amount, destinations = contract
    modified = _warm_rim(tree, geometry, source, ao, spec, settings, directions)
    permission_record = (
        _descriptor(permission) if hasattr(permission, "is_output") else permission
    )
    if hasattr(permission, "is_output"):
        inverse = _math(tree, "SUBTRACT", 1.0, permission, "unlicensed original rim")
        original = _vector(
            tree, "SCALE", rgb.outputs[0], inverse, "protected original rim RGB"
        )
        permitted = _vector(
            tree, "SCALE", modified, permission, "licensed warm rim RGB"
        )
        modified = _vector(tree, "ADD", original, permitted, "licensed rim replacement")
    for i, destination in enumerate(destinations):
        _wrap(
            tree,
            destination,
            modified,
            "rim",
            controls,
            records,
            "HDR consumer " + str(i),
        )
    if actor == "aksiniya":
        old = _source(screen_amount.inputs[1])
        attenuated = _math(
            tree,
            "MULTIPLY",
            old,
            settings["reference_screen_gain"],
            "SCREEN relative attenuation",
        )
        _wrap(
            tree,
            screen_amount.inputs[1],
            attenuated,
            "rim",
            controls,
            records,
            "SCREEN Fac gate",
        )
    return {
        "old_additive_rgb": _descriptor(rgb.outputs[0]),
        "existing_consumers": [_descriptor(s, False) for s in destinations],
        "pre_rim_shaded_source": _descriptor(source),
        "contact_ao": _descriptor(ao),
        "permission": permission_record,
        "unlicensed_white_pixels": "Original rim retained; original gold/cyan mask exclusions preserved"
        if hasattr(permission, "is_output")
        else "Full audited non-face material",
        "settings": spec,
        "screen_fac_relative_gain": settings["reference_screen_gain"]
        if actor == "aksiniya"
        else None,
    }


def _restore(tree, records, module=None, value=0.0):
    for record in records:
        if module is not None and record["module"] != module:
            continue
        target = record["target"]
        socket = tree.nodes[target["node"]].inputs[target["index"]]
        for link in list(socket.links):
            tree.links.remove(link)
        socket.default_value = record["original"]["default"]
        descriptor = record["final"] if value else record["original"].get("source")
        if descriptor:
            tree.links.new(
                tree.nodes[descriptor["node"]].outputs[descriptor["index"]], socket
            )
        tree.nodes[record["control"]].outputs[0].default_value = value


def _state_materials(scene):
    return {
        m
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id") in ACTOR_OBJECTS
        for m in o.data.materials
        if m and STATE in m
    }


def set_module_enabled(scene, module, value):
    """Zero restores original links/defaults; fractional values blend RGB deltas."""
    if module not in {"rim", "ink"}:
        raise ValueError("Expected rim or ink")
    value = _number(value, "module enable")
    changed = []
    for material in sorted(_state_materials(scene), key=lambda m: m.name):
        state = json.loads(material[STATE])
        records = [r for r in state["targets"] if r["module"] == module]
        _restore(material.node_tree, records, value=value)
        state["enabled"][module] = value
        material[STATE] = json.dumps(state, ensure_ascii=False)
        changed.extend(
            {"material": material.name, "target": r["label"], "value": value}
            for r in records
        )
    return changed


def set_gain(scene, value):
    """Set both module blends together; does not change HDR radiance gain."""
    return {
        module: set_module_enabled(scene, module, value) for module in ("rim", "ink")
    }


def remove(scene):
    """Restore original sockets and remove only this module's nodes and state."""
    changed = []
    for material in sorted(_state_materials(scene), key=lambda m: m.name):
        _restore(material.node_tree, json.loads(material[STATE])["targets"])
        for node in list(material.node_tree.nodes):
            if node.name.startswith(PREFIX):
                material.node_tree.nodes.remove(node)
        del material[STATE]
        changed.append(material.name)
    return changed


def apply(scene, settings=None):
    """Install the pinned still-study module and return JSON-serializable changes.

    Recursive overrides of DEFAULT_SETTINGS are accepted. Overrides under
    material_overrides use exact saved material names from the fixed whitelists.
    Default face/skin ink strengths are zero, so their materials are untouched.
    Existing facial feature materials and all plus overlays are always excluded.
    This function performs graph checks only; the caller owns visual validation.
    """
    settings = _merge(DEFAULT_SETTINGS, settings or {})
    _validate(settings)
    source = Path(bpy.data.filepath)
    if source.resolve() != SOURCE.resolve():
        raise ValueError("Portrait rim/ink accepts only the opened pinned Clean v2")
    if settings["verify_source_hash"]:
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != SOURCE_SHA256:
            raise ValueError("Portrait rim/ink source SHA mismatch")
    actors = _actor_contract(scene)
    if not scene.camera:
        raise ValueError("No active camera for fixed world rim direction")
    camera_rotation = scene.camera.matrix_world.to_quaternion()
    directions = {
        side: list(
            (
                camera_rotation @ Vector(settings["rim"][side + "_direction_camera"])
            ).normalized()
        )
        for side in ("left", "right")
    }
    plans = []
    for actor, targets in RIM_TARGETS.items():
        for name, identity in sorted(targets.items()):
            material = _material_contract(scene, actors, actor, name, identity)
            spec = _merge(
                settings["rim"]["actors"][actor][identity[2]],
                settings["rim"]["material_overrides"].get(name, {}),
            )
            plans.append((material, actor, "rim", spec, _rim_contract(material, actor)))
    for actor, targets in INK_TARGETS.items():
        for name, group in sorted(targets.items()):
            spec = _merge(
                settings["ink"]["actors"][actor][group],
                settings["ink"]["material_overrides"].get(name, {}),
            )
            if not spec["strength"]:
                continue
            material = _material_contract(scene, actors, actor, name)
            plans.append((material, actor, "ink", spec, None))
    report = {
        "id": settings["id"],
        "source": str(source),
        "source_sha256": SOURCE_SHA256,
        "settings": settings,
        "direction_reference_camera": scene.camera.name,
        "direction_reference_frame": scene.frame_current,
        "directions_world": directions,
        "materials": [],
        "graph_only": True,
        "rendered": False,
        "saved": False,
        "geometry_actions_weights_uv_shapes_modifiers_changed": False,
        "source_Color_Alpha_sphere_and_facial_features_changed": False,
        "stage_lights_camera_exposure_compositor_changed": False,
        "limits": [
            "Directional grazing shader with contact AO, not rim shadow visibility or depth rim",
            "Short AO cannot guarantee absence of hand/body or actor-overlap light leakage",
            "Original gold/cyan pixels outside Ikhor white permission retain their original rim",
            "Aksiniya replacement follows BoldWeddingEmission; its separate SCREEN/StageArtRim term is attenuated independently",
            "No inverse-hull width or mmd_edge_scale edits; face/skin outline color defaults unchanged",
            "Static graph implementation; appearance, glare, near/far lines and motion stability require rendered review",
        ],
    }
    touched = []
    try:
        for material, actor, module, spec, contract in plans:
            controls, records, tree = {}, [], material.node_tree
            touched.append((material, records))
            item = {"material": material.name, "actor": actor, "module": module}
            if module == "rim":
                item["implementation"] = _install_rim(
                    material,
                    actor,
                    spec,
                    settings["rim"],
                    directions,
                    controls,
                    records,
                    contract,
                )
            else:
                target = tree.nodes["mmd_edge_preview"].inputs["Color"]
                alpha = float(target.default_value[3])
                _wrap(
                    tree,
                    target,
                    [*spec["color"], alpha],
                    "ink",
                    controls,
                    records,
                    "existing ink RGB",
                    spec["strength"],
                )
                item["implementation"] = {
                    "settings": spec,
                    "alpha_preserved": alpha,
                    "thickness_and_PMX_weights_changed": False,
                }
            material[STATE] = json.dumps(
                {"id": settings["id"], "targets": records, "enabled": {module: 1.0}},
                ensure_ascii=False,
            )
            item["changes"] = records
            report["materials"].append(item)
        for module in ("rim", "ink"):
            set_module_enabled(scene, module, settings[module]["enabled"])
    except Exception:
        for material, records in reversed(touched):
            _restore(material.node_tree, records)
            for node in list(material.node_tree.nodes):
                if node.name.startswith(PREFIX):
                    material.node_tree.nodes.remove(node)
            if STATE in material:
                del material[STATE]
        raise
    _actor_contract(scene)
    report["counts"] = {
        "rim_materials": sum(m["module"] == "rim" for m in report["materials"]),
        "ink_materials": sum(m["module"] == "ink" for m in report["materials"]),
        "intercepted_inputs": sum(len(m["changes"]) for m in report["materials"]),
    }
    return report
