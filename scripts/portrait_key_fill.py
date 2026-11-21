"""Reversible portrait key/fill and single-palette experiment for Clean v2.

API: ``apply(scene, settings=None)``; ``set_gain(scene, 0)`` physically restores
every intercepted input link. This module neither opens nor saves a blend,
renders, edits lights, nor changes preferences. The caller owns diagnostics.

The existing key-facing Diffuse signal is retained as a *combined illumination
and geometric-occlusion approximation*, with optional fixed recalibration. It
is not visibility or a game shadow map. The existing repaired Aksiniya face SDF
and Ikhor's posed soft face form remain available upstream of that response.
Ikhor alone has an optional analytic head-space curved-normal proxy, disabled
by default. It uses both posed head axes, not the nose/mouth mesh normals, and
is neither SDF nor geometric shadow. Its optional directional face fill also
defaults off and lifts only the key-dark form using the actual fill direction.
New fill acts before response; neither fill nor the proxy bypasses the old AO.
All new colors are linear multipliers of the retained MMD Color, not albedo or
display-sRGB swatches. No output-color floor or extra emission closure is added.
"""

import copy
import hashlib
import json
import math
from pathlib import Path

import bpy

PREFIX = "Portrait relight | keyfill | "
STATE = "portrait_keyfill_state"
SOURCE_SHA256 = "0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4"

# Exact saved material names, original MMD material identities, and roles.
# The overlay face has no original SDF and is deliberately not selected.
TARGETS = {
    "aksiniya": {
        "颜": ("颜", "face"),
        "首": ("首", "skin"),
        "手": ("手", "skin"),
        **{
            name: (name, "cloth")
            for name in (
                "帽",
                "帽+",
                "披肩",
                "披肩+",
                "腿",
                "腿+",
                "衣",
                "衣+",
                "裙",
                "裙+",
            )
        },
    },
    "ikhor": {
        "颜.001": ("颜", "face"),
        "首.001": ("首", "skin"),
        "手.001": ("手", "skin"),
        "带子": ("带子", "white_outer"),
        "衣.001": ("衣", "white_outer"),
        "衣2": ("衣2", "white_outer"),
        "衣领": ("衣领", "white_outer"),
        "裙.001": ("裙", "white_outer"),
    },
}

DEFAULT_SETTINGS = {
    "id": "portrait-keyfill-v1",
    "gain": 1.0,
    "verify_source_hash": True,
    "actors": {
        "aksiniya": {
            "face": {
                "response_range": [0.055, 0.34],
                "fill_strength": 0.0,
                "palette": [
                    [0.18, [0.76, 0.50, 0.63, 1]],
                    [0.57, [0.97, 0.88, 0.92, 1]],
                    [0.83, [1.06, 1.015, 1.025, 1]],
                ],
            },
            "skin": {
                "response_range": [0.055, 0.34],
                "form_range": [-0.08, 0.65],
                "fill_range": [-0.12, 0.75],
                "fill_strength": 0.12,
                "palette": [
                    [0.14, [0.74, 0.47, 0.62, 1]],
                    [0.52, [0.99, 0.88, 0.94, 1]],
                    [0.79, [1.08, 1.025, 1.04, 1]],
                ],
            },
            "cloth": {
                "response_range": [0.055, 0.34],
                "form_range": [-0.08, 0.65],
                "fill_range": [-0.12, 0.75],
                "fill_strength": 0.18,
                "palette": [
                    [0.16, [0.34, 0.40, 0.65, 1]],
                    [0.52, [1.02, 1.08, 1.27, 1]],
                    [0.84, [1.46, 1.47, 1.60, 1]],
                ],
            },
        },
        "ikhor": {
            "face": {
                "response_range": [0.055, 0.34],
                "fill_strength": 0.0,
                "directional_fill": {
                    "enabled": False,
                    "strength": 0.20,
                    "range": [-0.10, 0.80],
                    "tint": [1.0, 1.0, 1.0, 1.0],
                },
                "analytic_form": {
                    "enabled": False,
                    "gain": 1.0,
                    "half_width": 0.0823,
                    "center_offset": 0.002857,
                    "curvature": 1.2,
                    "up_bias": 0.03,
                    "range": [0.18, 0.72],
                    "floor": 0.45,
                },
                "palette": [
                    [0.18, [0.79, 0.58, 0.73, 1]],
                    [0.54, [0.98, 0.90, 1.00, 1]],
                    [0.79, [1.045, 1.01, 1.055, 1]],
                ],
            },
            "skin": {
                "response_range": [0.055, 0.34],
                "form_range": [-0.08, 0.65],
                "fill_range": [-0.12, 0.75],
                "fill_strength": 0.10,
                "palette": [
                    [0.14, [0.79, 0.55, 0.70, 1]],
                    [0.50, [1.00, 0.92, 1.00, 1]],
                    [0.77, [1.045, 1.015, 1.055, 1]],
                ],
            },
            "white_outer": {
                "response_range": [0.055, 0.34],
                "form_range": [-0.08, 0.65],
                "fill_range": [-0.12, 0.75],
                "fill_strength": 0.09,
                "palette": [
                    [0.15, [0.68, 0.66, 0.78, 1]],
                    [0.50, [0.94, 0.96, 1.015, 1]],
                    [0.80, [1.02, 1.025, 1.035, 1]],
                ],
            },
        },
    },
}


def _plain(value):
    if value is None or isinstance(value, (bool, str, int, float)):
        return value
    return [_plain(item) for item in value]


def _merge(base, changes):
    result = copy.deepcopy(base)
    for key, value in changes.items():
        if key not in result:
            raise ValueError("Unknown portrait keyfill setting: " + str(key))
        if isinstance(result[key], dict):
            if not isinstance(value, dict):
                raise TypeError("Expected settings object: " + key)
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _number(value, label, low=0.0, high=1.0):
    number = float(value)
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError("Invalid " + label + ": " + str(value))
    return number


def _validate(settings):
    _number(settings["gain"], "gain")
    for actor, roles in settings["actors"].items():
        for role, spec in roles.items():
            _number(spec["fill_strength"], actor + " " + role + " fill")
            if role == "face" and spec["fill_strength"] != 0:
                raise ValueError(
                    "Face fill_strength must be zero; use the separate Ikhor form option"
                )
            if "analytic_form" in spec:
                if (actor, role) != ("ikhor", "face"):
                    raise ValueError(
                        "Analytic face form is restricted to Ikhor main face"
                    )
                proxy = spec["analytic_form"]
                if not isinstance(proxy["enabled"], bool):
                    raise TypeError("analytic_form.enabled must be boolean")
                _number(proxy["gain"], "analytic form gain")
                _number(proxy["half_width"], "analytic half width", 0.01, 0.5)
                _number(proxy["center_offset"], "analytic center offset", -0.2, 0.2)
                _number(proxy["curvature"], "analytic curvature", 0, 3)
                _number(proxy["up_bias"], "analytic up bias", -0.5, 0.5)
                _number(proxy["floor"], "analytic pre-response form floor")
                if len(proxy["range"]) != 2 or proxy["range"][0] >= proxy["range"][1]:
                    raise ValueError("Invalid analytic NoL interval")
                for value in proxy["range"]:
                    _number(value, "analytic NoL bound", -1, 1)
            if "directional_fill" in spec:
                fill = spec["directional_fill"]
                if (actor, role) != ("ikhor", "face"):
                    raise ValueError(
                        "Directional face fill is restricted to Ikhor proxy"
                    )
                if not isinstance(fill["enabled"], bool):
                    raise TypeError("directional_fill.enabled must be boolean")
                _number(fill["strength"], "directional face fill strength", 0, 0.8)
                if len(fill["range"]) != 2 or fill["range"][0] >= fill["range"][1]:
                    raise ValueError("Invalid directional face fill NoL interval")
                for value in fill["range"]:
                    _number(value, "face fill NoL bound", -1, 1)
                if len(fill["tint"]) != 4 or fill["tint"][3] != 1:
                    raise ValueError("Face fill tint must preserve alpha one")
                for value in fill["tint"][:3]:
                    _number(value, "face fill linear tint", 0, 2)
                if fill["enabled"] and not (
                    spec["analytic_form"]["enabled"] and spec["analytic_form"]["gain"]
                ):
                    raise ValueError(
                        "Enable Ikhor analytic form before its directional fill"
                    )
            for key in ("response_range", "form_range", "fill_range"):
                if key not in spec:
                    continue
                values = spec[key]
                if len(values) != 2:
                    raise ValueError("Expected two values: " + key)
                for value in values:
                    _number(value, key, -1, 16)
                if values[0] >= values[1]:
                    raise ValueError("Expected increasing range: " + key)
            if len(spec["palette"]) < 2:
                raise ValueError("Palette requires at least two points")
            previous = -1
            for position, rgba in spec["palette"]:
                _number(position, "palette position")
                if position <= previous or len(rgba) != 4:
                    raise ValueError("Invalid palette order or RGBA")
                previous = position
                for value in rgba:
                    _number(value, "palette multiplier", 0, 4)
                if rgba[3] != 1:
                    raise ValueError("Palette alpha must remain one")


def _sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _required(tree, name, kind=None):
    node = tree.nodes.get(name)
    if not node or kind and node.bl_idname != kind:
        raise ValueError("Missing pinned node contract: " + name)
    return node


def _source(socket):
    if len(socket.links) != 1:
        raise ValueError("Expected one original input link: " + socket.node.name)
    return socket.links[0].from_socket


def _descriptor(socket):
    sockets = socket.node.outputs if socket.is_output else socket.node.inputs
    return {
        "node": socket.node.name,
        "index": list(sockets).index(socket),
        "identifier": socket.identifier,
    }


def _resolve(tree, record, output):
    node = _required(tree, record["node"])
    sockets = node.outputs if output else node.inputs
    socket = sockets[record["index"]]
    if socket.identifier != record["identifier"]:
        raise ValueError("Stored portrait socket contract changed")
    return socket


def _new(tree, kind, label):
    name = PREFIX + label
    if len(name.encode("utf-8")) > 63:
        raise ValueError("Portrait node name exceeds Blender limit: " + name)
    if tree.nodes.get(name):
        raise ValueError("Refusing to stack portrait keyfill: " + name)
    node = tree.nodes.new(kind)
    node.name = node.label = name
    return node


def _plug(tree, value, target):
    if hasattr(value, "is_output"):
        tree.links.new(value, target)
    else:
        target.default_value = value


def _math(tree, operation, first, second, label):
    node = _new(tree, "ShaderNodeMath", label)
    node.operation = operation
    _plug(tree, first, node.inputs[0])
    _plug(tree, second, node.inputs[1])
    return node.outputs[0]


def _vector(tree, operation, first, second, label):
    node = _new(tree, "ShaderNodeVectorMath", label)
    node.operation = operation
    _plug(tree, first, node.inputs[0])
    if second is not None:
        _plug(tree, second, node.inputs[3] if operation == "SCALE" else node.inputs[1])
    return node.outputs["Value"] if operation == "DOT_PRODUCT" else node.outputs[0]


def _smooth(tree, value, limits, label):
    node = _new(tree, "ShaderNodeMapRange", label)
    node.clamp, node.interpolation_type = True, "SMOOTHSTEP"
    _plug(tree, value, node.inputs["Value"])
    node.inputs["From Min"].default_value = limits[0]
    node.inputs["From Max"].default_value = limits[1]
    return node.outputs["Result"]


def _position(tree, obj, label):
    node = _new(tree, "ShaderNodeCombineXYZ", label)
    for index, socket in enumerate(node.inputs):
        driver = socket.driver_add("default_value").driver
        variable = driver.variables.new()
        variable.name, variable.type = "p", "TRANSFORMS"
        target = variable.targets[0]
        target.id, target.transform_space = obj, "WORLD_SPACE"
        target.transform_type = "LOC_" + "XYZ"[index]
        driver.type, driver.expression = "SCRIPTED", "p"
    return node.outputs[0]


def _mix(tree, first, second, factor, label):
    node = _new(tree, "ShaderNodeMixRGB", label)
    node.blend_type, node.use_clamp = "MIX", False
    for value, socket in zip((factor, first, second), node.inputs):
        _plug(tree, value, socket)
    return node.outputs[0]


def _analytic_face_form(scene, tree, geometry, original, settings, fill_settings):
    """Original smooth proxy, using the full posed basis; no mesh Normal input."""
    points = {
        label: _position(
            tree, scene.objects["Quality | ikhor | head " + label], "face " + label
        )
        for label in ("origin", "forward", "up")
    }
    forward_delta = _vector(
        tree, "SUBTRACT", points["forward"], points["origin"], "face forward delta"
    )
    forward = _vector(tree, "NORMALIZE", forward_delta, None, "face forward axis")
    up_delta = _vector(
        tree, "SUBTRACT", points["up"], points["origin"], "face up delta"
    )
    right_raw = _vector(tree, "CROSS_PRODUCT", forward, up_delta, "face right cross")
    right = _vector(tree, "NORMALIZE", right_raw, None, "face right axis")
    up_raw = _vector(tree, "CROSS_PRODUCT", right, forward, "face up cross")
    up = _vector(tree, "NORMALIZE", up_raw, None, "face up axis")
    relative = _vector(
        tree,
        "SUBTRACT",
        geometry.outputs["Position"],
        points["origin"],
        "face head offset",
    )
    horizontal = _vector(tree, "DOT_PRODUCT", relative, right, "face local horizontal")
    centered = _math(
        tree,
        "SUBTRACT",
        horizontal,
        settings["center_offset"],
        "face center correction",
    )
    fraction = _math(
        tree, "DIVIDE", centered, settings["half_width"], "face half width ratio"
    )
    lower = _math(tree, "MAXIMUM", fraction, -1, "face lower width clamp")
    bounded = _math(tree, "MINIMUM", lower, 1, "face bounded width")
    curved = _math(tree, "MULTIPLY", bounded, settings["curvature"], "face curvature")
    side = _vector(tree, "SCALE", right, curved, "face lateral normal")
    tilt = _vector(tree, "SCALE", up, settings["up_bias"], "face up normal")
    horizontal_normal = _vector(tree, "ADD", forward, side, "face curved normal")
    tilted_normal = _vector(tree, "ADD", horizontal_normal, tilt, "face tilted normal")
    normal = _vector(tree, "NORMALIZE", tilted_normal, None, "face proxy normal")
    key_position = _position(
        tree, scene.objects["Reference duet | ikhor | key"], "face actual key position"
    )
    key_delta = _vector(
        tree,
        "SUBTRACT",
        key_position,
        geometry.outputs["Position"],
        "face surface to key",
    )
    key_direction = _vector(tree, "NORMALIZE", key_delta, None, "face key direction")
    no_l = _vector(tree, "DOT_PRODUCT", normal, key_direction, "face proxy NoL")
    band = _smooth(tree, no_l, settings["range"], "face proxy band")
    scale = _math(tree, "MULTIPLY", band, 1 - settings["floor"], "face proxy lit form")
    proxy = _math(tree, "ADD", settings["floor"], scale, "face proxy soft form")
    base_proxy = proxy
    fill_record = None
    if fill_settings["enabled"] and fill_settings["strength"]:
        fill_object = scene.objects["Reference duet | ikhor | fill"]
        fill_position = _position(tree, fill_object, "face fill position")
        fill_delta = _vector(
            tree,
            "SUBTRACT",
            fill_position,
            geometry.outputs["Position"],
            "face to fill",
        )
        fill_direction = _vector(
            tree, "NORMALIZE", fill_delta, None, "face fill direction"
        )
        fill_nol = _vector(tree, "DOT_PRODUCT", normal, fill_direction, "face fill NoL")
        fill_band = _smooth(tree, fill_nol, fill_settings["range"], "face fill band")
        fill_weight = _math(
            tree, "MULTIPLY", fill_band, fill_settings["strength"], "face fill weight"
        )
        dark = _math(tree, "SUBTRACT", 1, base_proxy, "face key dark permission")
        amount = _math(tree, "MULTIPLY", fill_weight, dark, "face fill dark amount")
        proxy = _math(tree, "ADD", base_proxy, amount, "face with directional fill")
        fill_record = {
            "settings": copy.deepcopy(fill_settings),
            "light_object": fill_object.name,
            "base_form": _descriptor(base_proxy),
            "filled_form": _descriptor(proxy),
            "amount": _descriptor(amount),
            "NoL": _descriptor(fill_nol),
            "semantics": "directional fill lifts only key-dark proxy form before original combined response and AO",
            "final_color_floor_added": False,
        }
    control = _new(tree, "ShaderNodeValue", "face proxy gain")
    gain = settings["gain"] if settings["enabled"] else 0.0
    control.outputs[0].default_value = gain
    difference = _math(tree, "SUBTRACT", proxy, original, "face proxy form delta")
    weighted = _math(
        tree, "MULTIPLY", difference, control.outputs[0], "face proxy enabled delta"
    )
    selected = _math(tree, "ADD", original, weighted, "face selected form")
    record = {
        "settings": copy.deepcopy(settings),
        "original_form": _descriptor(original),
        "proxy_form": _descriptor(proxy),
        "base_proxy_form": _descriptor(base_proxy),
        "directional_fill": fill_record,
        "selected_form": _descriptor(selected),
        "gain_node": control.name,
        "normal": _descriptor(normal),
        "NoL": _descriptor(no_l),
        "semantics": "original head-space analytic curved-normal proxy, not SDF or geometric shadow",
        "original_face_form_retained": True,
        "mesh_normal_consumed": False,
        "floor_applies_before_combined_response_and_existing_AO": True,
    }
    return selected if gain else original, record


def _ramp(tree, factor, points):
    node = _new(tree, "ShaderNodeValToRGB", "single portrait palette")
    node.color_ramp.interpolation = "EASE"
    while len(node.color_ramp.elements) < len(points):
        node.color_ramp.elements.new(0.5)
    for element, (position, color) in zip(node.color_ramp.elements, points):
        element.position, element.color = position, color
    tree.links.new(factor, node.inputs[0])
    return node.outputs[0]


def _protected_material(material):
    """Protected existing nodes; palette-intercept link is checked separately."""
    tree = material.node_tree
    return {
        node.name: {
            "type": node.bl_idname,
            "inputs": [
                _plain(getattr(socket, "default_value", None)) for socket in node.inputs
            ],
            "outputs": [
                _plain(getattr(socket, "default_value", None))
                for socket in node.outputs
            ],
            "links": [
                (
                    list(node.inputs).index(link.to_socket),
                    link.from_node.name,
                    list(link.from_node.outputs).index(link.from_socket),
                )
                for socket in node.inputs
                for link in socket.links
            ],
        }
        for node in tree.nodes
        if not node.name.startswith(PREFIX)
    }


def _axes_report(scene, actor):
    points = {
        name: scene.objects["Quality | " + actor + " | head " + name]
        for name in ("origin", "forward", "up")
    }
    origin = points["origin"].matrix_world.translation
    forward = (points["forward"].matrix_world.translation - origin).normalized()
    up_raw = (points["up"].matrix_world.translation - origin).normalized()
    right = forward.cross(up_raw).normalized()
    up = right.cross(forward).normalized()
    if min(forward.length, up.length, right.length) < 0.99:
        raise ValueError("Degenerate posed head basis: " + actor)
    key = scene.objects["Reference duet | " + actor + " | key"]
    fill = scene.objects["Reference duet | " + actor + " | fill"]
    direction = (key.matrix_world.translation - origin).normalized()
    return {
        "head_origin": list(origin),
        "head_forward": list(forward),
        "head_up": list(up),
        "head_right": list(right),
        "key_direction": list(direction),
        "key_in_head_basis": [
            direction.dot(right),
            direction.dot(forward),
            direction.dot(up),
        ],
        "fill_world_position": list(fill.matrix_world.translation),
        "key_diffuse_factor": key.data.diffuse_factor,
        "fill_diffuse_factor": fill.data.diffuse_factor,
        "face_form": "unchanged original full upstream form; no world-fixed face patch",
    }


def _contract(scene, actor, name, source_name, role):
    material = bpy.data.materials.get(name)
    if not material or not material.node_tree:
        raise ValueError("Missing exact portrait material: " + name)
    if (
        material.get("performer_id") != actor
        or material.get("source_mmd_material_name") != source_name
    ):
        raise ValueError("Portrait material identity mismatch: " + name)
    actual_role = material.get(
        "character_layer_role" if actor == "aksiniya" else "ikhor_material_role"
    )
    if actual_role != ("cloth" if role == "white_outer" else role):
        raise ValueError("Portrait material role mismatch: " + name)
    users = [
        obj
        for obj in scene.objects
        if obj.type == "MESH" and material in obj.data.materials[:]
    ]
    if not users or any(obj.get("performer_id") != actor for obj in users):
        raise ValueError("Portrait material has non-actor or missing users: " + name)
    tree = material.node_tree
    if STATE in material or any(node.name.startswith(PREFIX) for node in tree.nodes):
        raise ValueError("Refusing repeated portrait keyfill application: " + name)
    _required(tree, "mmd_shader", "ShaderNodeGroup")
    original = "Reference transfer | " if actor == "aksiniya" else "Ikhor character | "
    target_node = _required(
        tree,
        original
        + ("shading bypass" if actor == "aksiniya" else "source times single palette"),
    )
    target = target_node.inputs[2]
    current = _source(target)
    expected = (
        (
            "Clean Aksiniya | palette | cloth palette selected"
            if role == "cloth"
            else "Reference transfer | designed two color palette"
        )
        if actor == "aksiniya"
        else "Clean Ikhor | independent palette and response switches"
    )
    if current.node.name != expected:
        raise ValueError(
            "Unexpected active palette consumer: " + name + ": " + current.node.name
        )
    combined = _required(
        tree,
        original
        + (
            "form times directional response"
            if actor == "aksiniya"
            else "form times actual response"
        ),
        "ShaderNodeMath",
    )
    response = _required(
        tree,
        original
        + (
            "key facing response"
            if actor == "aksiniya"
            else "calibrated combined light response"
        ),
        "ShaderNodeMapRange",
    )
    if _source(combined.inputs[1]).node != response or combined.operation != "MULTIPLY":
        raise ValueError("Original form/response product changed: " + name)
    for label, expected_value in (("From Min", 0.055), ("From Max", 0.34)):
        if (
            response.inputs[label].is_linked
            or abs(response.inputs[label].default_value - expected_value) > 1e-5
        ):
            raise ValueError("Original response calibration changed: " + name)
    raw = _source(response.inputs["Value"])
    if raw.node.name != original + (
        "distance compensated illumination"
        if actor == "aksiniya"
        else "distance compensated response"
    ):
        raise ValueError("Unexpected calibrated combined response source: " + name)
    geometry = _required(
        tree,
        original + ("surface geometry" if actor == "aksiniya" else "geometry"),
        "ShaderNodeNewGeometry",
    )
    if role == "face":
        form = _source(combined.inputs[0])
        if form.node.name != original + "soft face form before occlusion":
            raise ValueError("Missing preserved face form: " + name)
        if actor == "aksiniya":
            _required(
                tree, "Clean Aksiniya | response_ramp | same dynamic SDF threshold"
            )
            _required(tree, "Face ink | Mouth crease")
    else:
        no_l = _required(
            tree,
            original
            + ("geometric form NoL" if actor == "aksiniya" else "form normal dot key"),
        )
        form = no_l.outputs["Value"]
    permission = None
    if role == "white_outer":
        permission_node = _required(
            tree, "Clean Ikhor | palette permission", "ShaderNodeMath"
        )
        permission = _source(permission_node.inputs[1])
        if not permission.node.name.startswith("Clean Ikhor | "):
            raise ValueError("White permission no longer uses original protected mask")
    return material, target, current, raw, form, geometry, permission


def apply(scene, settings=None):
    """Install on the pinned opened source; return a JSON-serializable report.

    Settings recursively override DEFAULT_SETTINGS. ``response_range`` defaults
    to the old calibration until GPU component probes justify another fixed
    interval. New fill uses the current *physical fill object's position* as an
    artistic direction, without modifying that light's zero diffuse factor.
    """
    settings = _merge(DEFAULT_SETTINGS, settings or {})
    _validate(settings)
    source = Path(bpy.data.filepath)
    if not source.is_file():
        raise ValueError("Open the pinned Clean v2 before applying portrait keyfill")
    if settings["verify_source_hash"] and _sha(source) != SOURCE_SHA256:
        raise ValueError("Portrait keyfill accepts only the pinned Clean v2 SHA")
    # Preflight every material before editing any: fail closed on drift.
    contracts = []
    for actor, materials in TARGETS.items():
        for name, (source_name, role) in materials.items():
            contracts.append(
                (actor, role, _contract(scene, actor, name, source_name, role))
            )
    axes = {actor: _axes_report(scene, actor) for actor in TARGETS}
    proxy_settings = settings["actors"]["ikhor"]["face"]["analytic_form"]
    if proxy_settings["enabled"] and proxy_settings["gain"]:
        axes["ikhor"]["face_form"] = (
            "analytic curved-normal proxy from complete posed head basis; "
            "original soft form retained for independent bypass"
        )
    before = {
        contract[0].name: _protected_material(contract[0])
        for _, _, contract in contracts
    }
    report = {
        "id": settings["id"],
        "settings": settings,
        "source_sha256": SOURCE_SHA256,
        "head_axes_at_frame": {"frame": scene.frame_current, "actors": axes},
        "materials": [],
        "response_semantics": "fixed calibrated combined illumination/occlusion approximation; not visibility",
        "face_floor_added": False,
        "face_output_brightness_floor_added": False,
        "new_ao_or_closure": False,
        "light_settings_changed": False,
        "art_status": "pending GPU same-frame comparison",
    }
    for actor, role, contract in contracts:
        material, target, old, raw, form, geometry, permission = contract
        tree, spec = material.node_tree, settings["actors"][actor][role]
        proxy_record = None
        if actor == "ikhor" and role == "face":
            form, proxy_record = _analytic_face_form(
                scene,
                tree,
                geometry,
                form,
                spec["analytic_form"],
                spec["directional_fill"],
            )
        if role != "face":
            form = _smooth(tree, form, spec["form_range"], "key form")
            fill = scene.objects["Reference duet | " + actor + " | fill"]
            fill_position = _position(tree, fill, "fill world position")
            delta = _vector(
                tree,
                "SUBTRACT",
                fill_position,
                geometry.outputs["Position"],
                "surface to fill",
            )
            direction = _vector(tree, "NORMALIZE", delta, None, "fill direction")
            no_fill = _vector(
                tree,
                "DOT_PRODUCT",
                geometry.outputs["Normal"],
                direction,
                "normal dot fill",
            )
            fill_form = _smooth(tree, no_fill, spec["fill_range"], "fill form")
            weighted = _math(
                tree, "MULTIPLY", fill_form, spec["fill_strength"], "fill amount"
            )
            unlit = _math(tree, "SUBTRACT", 1, form, "remaining key dark")
            increment = _math(tree, "MULTIPLY", weighted, unlit, "fill only dark form")
            form = _math(tree, "ADD", form, increment, "key plus bounded fill")
        response = _smooth(tree, raw, spec["response_range"], "combined response")
        factor = _math(tree, "MULTIPLY", form, response, "form times occlusion")
        if proxy_record is not None:
            proxy_record["form_target"] = _descriptor(factor.node.inputs[0])
        palette = _ramp(tree, factor, spec["palette"])
        if proxy_record is not None and proxy_record["directional_fill"] is not None:
            fill_record = proxy_record["directional_fill"]
            fill_amount = _resolve(tree, fill_record["amount"], True)
            tint_amount = _math(
                tree, "MULTIPLY", fill_amount, response, "face fill tint permission"
            )
            tint_amount = _math(
                tree,
                "MULTIPLY",
                tint_amount,
                tree.nodes[proxy_record["gain_node"]].outputs[0],
                "face fill proxy gate",
            )
            tint = _mix(
                tree,
                (1, 1, 1, 1),
                spec["directional_fill"]["tint"],
                tint_amount,
                "face fill restrained tint",
            )
            tinted = _new(tree, "ShaderNodeMixRGB", "face palette times fill tint")
            tinted.blend_type, tinted.use_clamp = "MULTIPLY", False
            tinted.inputs[0].default_value = 1
            tree.links.new(palette, tinted.inputs[1])
            tree.links.new(tint, tinted.inputs[2])
            palette = tinted.outputs[0]
        if permission is not None:
            palette = _mix(tree, old, palette, permission, "white permission mix")
        control = _new(tree, "ShaderNodeValue", "gain")
        control.outputs[0].default_value = settings["gain"]
        final = _mix(tree, old, palette, control.outputs[0], "palette bypass")
        state = {
            "target": _descriptor(target),
            "original": _descriptor(old),
            "modified": _descriptor(final),
            "gain_node": control.name,
            "requested_gain": settings["gain"],
            "actor": actor,
            "role": role,
        }
        if proxy_record is not None:
            state["analytic_form"] = proxy_record
        material[STATE] = json.dumps(state, ensure_ascii=False)
        tree.links.new(final if settings["gain"] else old, target)
        item = {
            "material": material.name,
            "actor": actor,
            "role": role,
            **state,
            "response_source": _descriptor(raw),
            "face_form_preserved": role == "face"
            and (
                proxy_record is None
                or not spec["analytic_form"]["enabled"]
                or not spec["analytic_form"]["gain"]
            ),
            "white_permission": _descriptor(permission)
            if permission is not None
            else None,
        }
        report["materials"].append(item)
        # All previous default values and all other original input links survive.
        after = _protected_material(material)
        original_before = before[material.name]
        index = list(target.node.inputs).index(target)
        for snapshot in (after, original_before):
            snapshot[target.node.name]["links"] = [
                link for link in snapshot[target.node.name]["links"] if link[0] != index
            ]
        if after != original_before:
            raise AssertionError("Unlicensed original-node mutation: " + material.name)
    json.dumps(report, ensure_ascii=False, allow_nan=False)
    return report


def set_gain(scene, gain):
    """Set all installed keyfill controls. Zero physically restores old links."""
    gain = _number(gain, "gain")
    changed = []
    for actor, materials in TARGETS.items():
        for name in materials:
            material = bpy.data.materials.get(name)
            if not material or STATE not in material:
                continue
            state = json.loads(material[STATE])
            if state["actor"] != actor:
                raise ValueError("Stored portrait actor mismatch")
            tree = material.node_tree
            target = _resolve(tree, state["target"], False)
            selected = _resolve(tree, state["modified" if gain else "original"], True)
            tree.nodes[state["gain_node"]].outputs[0].default_value = gain
            tree.links.new(selected, target)
            changed.append(name)
    return changed


def set_face_proxy_gain(scene, gain):
    """Independently select Ikhor's installed proxy; zero restores old form link.

    The global set_gain remains the bypass for the whole relight palette. Both
    selectors act before the original combined light response and existing AO.
    """
    gain = _number(gain, "analytic face proxy gain")
    material = bpy.data.materials.get("颜.001")
    if not material or STATE not in material:
        raise ValueError("Install portrait keyfill before switching the face proxy")
    state = json.loads(material[STATE])
    proxy = state.get("analytic_form")
    if state["actor"] != "ikhor" or not proxy:
        raise ValueError("The installed material has no Ikhor analytic face option")
    tree = material.node_tree
    original = _resolve(tree, proxy["original_form"], True)
    selected = _resolve(tree, proxy["selected_form"], True)
    target = _resolve(tree, proxy["form_target"], False)
    tree.nodes[proxy["gain_node"]].outputs[0].default_value = gain
    tree.links.new(selected if gain else original, target)
    return {
        "material": material.name,
        "gain": gain,
        "original_form_directly_connected": gain == 0,
    }
