"""Opt-in material controls for the audited Character Layers production-v2.

This module only edits the supplied scene's existing material graphs in memory.
It never saves, renders, changes preferences, or replaces a material closure.
The caller owns permission-map authorship, packing, visual review and delivery.

Example (execute inside Blender after opening the independent working copy)::

    report = apply_material_response(scene, {
        "actors": ["aksiniya", "aether"],
        "hair": {
            "materials": ["前鬓", "呆毛", "鬓", "发"],
            "permission": 1.0,
            "overrides": {
                "前鬓": {"permission": {
                    "image_path": "D:/codex/output/example/permission.png",
                    "channel": "Red"}},
            },
            "illumination_gate": {"enabled": False, "retention": 0.35},
        },
        "cloth": {
            "actors": ["aether"], "materials": ["披风"],
            "sheen_tint": [0.90, 0.95, 1.0, 1.0],
            "sheen_roughness": 0.60,
        },
    })

The example sheen settings are experiment inputs, not defaults or approved looks.
``permission`` accepts a float, {"value": float}, an image path, or the image
mapping above. Image channels: Red/Green/Blue/Alpha/Luminance. Data images use a
new Non-Color datablock and the existing mmd_base_tex Vector input. The optional
illumination source defaults to Character layers | illumination calibration,
Result; source_node/source_socket can name another explicit scalar signal.
That signal is combined illumination, never asserted to be pure visibility.

At least one actors/materials whitelist is required globally or per section.
Selections intersect. Per-actor and per-material options can be supplied through
actor_overrides and overrides. Each section installs once; repeated calls skip
installed sections. set_material_response_bypass() switches installed controls
between zero and their recorded requested values without rebuilding the graph.
"""

import math
from pathlib import Path

import bpy

PREFIX = "Transfer material | "
INPUT_REVISION = "duet-character-layers-v1"
HAIR_SIGNAL = "Character layers | single hair highlight"
HAIR_MIX = "Character layers | one directional hair highlight"
ILLUMINATION_NODE = "Character layers | illumination calibration"
CLOTH_NODE = "Aether v2 | material-specific physical response"
AUDITED_HAIR = {"aksiniya": ("前鬓", "呆毛", "鬓"), "aether": ("发",)}
AUDITED_CLOTH = {"aether": ("围巾", "披风", "身体")}


def _plain(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return list(value)


def _socket_record(socket):
    return {
        "node": socket.node.name,
        "socket": socket.name,
        "identifier": socket.identifier,
        "default": _plain(getattr(socket, "default_value", None)),
        "from": [
            {
                "node": link.from_node.name,
                "socket": link.from_socket.name,
                "identifier": link.from_socket.identifier,
            }
            for link in socket.links
        ],
    }


def _source(socket):
    return (
        socket.links[0].from_socket
        if socket.is_linked
        else _plain(socket.default_value)
    )


def _plug(tree, value, target):
    if hasattr(value, "is_output"):
        tree.links.new(value, target)
    else:
        target.default_value = value


def _node(tree, kind, label):
    name = PREFIX + label
    if tree.nodes.get(name):
        raise ValueError("Control node already exists: " + name)
    result = tree.nodes.new(kind)
    result.name = name
    result.label = label
    return result


def _scalar(tree, operation, first, second, label):
    result = _node(tree, "ShaderNodeMath", label)
    result.operation = operation
    _plug(tree, first, result.inputs[0])
    _plug(tree, second, result.inputs[1])
    return result.outputs[0]


def _unit(value, label):
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ValueError(label + " must be a finite value in [0, 1]")
    return result


def _control(tree, label, requested, bypass):
    result = _node(tree, "ShaderNodeValue", label)
    result["transfer_requested_enable"] = requested
    result.outputs[0].default_value = 0 if bypass else requested
    return result.outputs[0]


def _clamp(tree, value, label):
    result = _node(tree, "ShaderNodeClamp", label)
    _plug(tree, value, result.inputs["Value"])
    result.inputs["Min"].default_value = 0
    result.inputs["Max"].default_value = 1
    return result.outputs[0]


def _select_scalar(tree, original, target, enable, label):
    delta = _scalar(tree, "SUBTRACT", target, original, label + " delta")
    change = _scalar(tree, "MULTIPLY", enable, delta, label + " enabled delta")
    return _scalar(tree, "ADD", original, change, label + " selector")


def _scene_materials(scene):
    materials = {}
    for obj in scene.objects:
        if obj.type == "MESH":
            for slot in obj.material_slots:
                if slot.material and slot.material.get("performer_id"):
                    materials[slot.material.name] = slot.material
    return [materials[name] for name in sorted(materials)]


def _active_nodes(tree):
    outputs = [
        n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
    ]
    seen, pending = set(), list(outputs)
    while pending:
        item = pending.pop()
        if item in seen:
            continue
        seen.add(item)
        pending.extend(
            link.from_node for socket in item.inputs for link in socket.links
        )
    return seen


def _selected(material, spec, section):
    for options in (spec, section):
        if (
            "actors" in options
            and material.get("performer_id") not in options["actors"]
        ):
            return False
        if "materials" in options and material.name not in options["materials"]:
            return False
    return True


def _options(material, section):
    result = dict(section)
    for update in (
        section.get("actor_overrides", {}).get(material.get("performer_id"), {}),
        section.get("overrides", {}).get(material.name, {}),
    ):
        for key, value in update.items():
            if key == "illumination_gate":
                result[key] = {**result.get(key, {}), **value}
            else:
                result[key] = value
    return result


def _animated(socket):
    """Never freeze a touched socket's driven or keyframed default value."""
    animation = socket.id_data.animation_data
    if not animation:
        return False
    path = socket.path_from_id("default_value")
    if any(curve.data_path == path for curve in animation.drivers):
        return True
    action = animation.action
    if action:
        if any(curve.data_path == path for curve in getattr(action, "fcurves", ())):
            return True
        for layer in getattr(action, "layers", ()):
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", ()):
                    if any(curve.data_path == path for curve in bag.fcurves):
                        return True
    # NLA-controlled node defaults are uncommon here. Skip rather than flatten
    # an input when a nonempty NLA stack makes its provenance uncertain.
    return bool(animation.nla_tracks)


def _permission_spec(value):
    if isinstance(value, (int, float)):
        return {"value": _unit(value, "hair permission")}
    if isinstance(value, (str, Path)):
        value = {"image_path": str(value)}
    if not isinstance(value, dict):
        raise TypeError("hair permission must be a scalar, path or mapping")
    if "value" in value:
        if "image_path" in value:
            raise ValueError("permission must choose a value or image_path")
        return {"value": _unit(value["value"], "hair permission")}
    path = Path(bpy.path.abspath(str(value["image_path"]))).resolve()
    if not path.is_file():
        raise ValueError("permission image is missing: " + str(path))
    channel = value.get("channel", "Red")
    if channel not in {"Red", "Green", "Blue", "Alpha", "Luminance"}:
        raise ValueError("unsupported permission channel: " + str(channel))
    return {
        "image_path": str(path),
        "channel": channel,
        "uv_source_node": value.get("uv_source_node", "mmd_base_tex"),
    }


def _permission(tree, settings):
    if "value" in settings:
        item = _node(tree, "ShaderNodeValue", "hair permission mask")
        item.outputs[0].default_value = settings["value"]
        return item.outputs[0], dict(settings)
    # check_existing=False prevents changing an existing image's color space.
    image = bpy.data.images.load(settings["image_path"], check_existing=False)
    image.colorspace_settings.name = "Non-Color"
    texture = _node(tree, "ShaderNodeTexImage", "hair independent permission image")
    texture.image = image
    texture.interpolation = "Linear"
    base = tree.nodes[settings["uv_source_node"]]
    _plug(tree, _source(base.inputs["Vector"]), texture.inputs["Vector"])
    channel = settings["channel"]
    if channel == "Alpha":
        result = texture.outputs["Alpha"]
    elif channel == "Luminance":
        convert = _node(tree, "ShaderNodeRGBToBW", "hair permission luminance")
        tree.links.new(texture.outputs["Color"], convert.inputs[0])
        result = convert.outputs[0]
    else:
        separate = _node(tree, "ShaderNodeSeparateColor", "hair permission channels")
        separate.mode = "RGB"
        tree.links.new(texture.outputs["Color"], separate.inputs[0])
        result = separate.outputs[channel]
    return result, {
        **settings,
        "image": image.name,
        "colorspace": "Non-Color",
        "packed": bool(image.packed_file),
        "uv": _socket_record(base.inputs["Vector"]),
    }


def _hair(material, options, bypass):
    tree = material.node_tree
    if tree.nodes.get(PREFIX + "hair permission enable"):
        return None, "hair controls already installed"
    signal, mix = tree.nodes.get(HAIR_SIGNAL), tree.nodes.get(HAIR_MIX)
    if not signal or not mix or mix not in _active_nodes(tree):
        return None, "no active audited directional hair band"
    if mix.blend_type != "SCREEN" or not mix.inputs[0].is_linked:
        return None, "hair SCREEN factor contract differs from the audited input"
    if len(mix.inputs[0].links) != 1 or mix.inputs[0].links[0].from_node != signal:
        return None, "hair factor has already been rerouted"
    if _animated(mix.inputs[0]):
        return None, "hair factor default is animated"
    permission_settings = _permission_spec(options.get("permission", 1.0))
    if "image_path" in permission_settings:
        base = tree.nodes.get(permission_settings["uv_source_node"])
        if not base or not base.inputs.get("Vector"):
            return None, "permission image has no explicit existing UV source"
    enabled = _unit(options.get("enabled", True), "hair enabled")
    permission_enable = enabled * _unit(
        options.get("permission_enabled", True), "permission_enabled"
    )
    gate_options = options.get("illumination_gate", {})
    gate_enable = enabled * _unit(
        gate_options.get("enabled", False), "illumination gate enabled"
    )
    retention = _unit(gate_options.get("retention", 0.35), "illumination retention")
    illumination = tree.nodes.get(gate_options.get("source_node", ILLUMINATION_NODE))
    illumination_socket = (
        illumination.outputs.get(gate_options.get("source_socket", "Result"))
        if illumination
        else None
    )
    if not illumination_socket or illumination_socket.type not in {
        "VALUE",
        "INT",
        "BOOLEAN",
    }:
        return (
            None,
            "combined illumination gate requires an explicit existing scalar source",
        )
    old = signal.outputs[0]
    consumers = [mix.inputs[0]]
    for item in tree.nodes:
        if item.type == "OUTPUT_AOV" and item.aov_name == "StageArtRim":
            for socket in item.inputs:
                if any(link.from_socket == old for link in socket.links):
                    consumers.append(socket)
    originals = [_socket_record(socket) for socket in consumers]
    mask, permission_report = _permission(tree, permission_settings)
    mask = _clamp(tree, mask, "hair permission bounded")
    permission_switch = _control(
        tree, "hair permission enable", permission_enable, bypass
    )
    effective_mask = _select_scalar(
        tree, 1.0, mask, permission_switch, "hair permission"
    )
    permitted = _scalar(
        tree, "MULTIPLY", old, effective_mask, "hair permitted highlight"
    )
    illumination = _clamp(
        tree, illumination_socket, "hair combined illumination bounded"
    )
    illuminated_fraction = _scalar(
        tree, "MULTIPLY", illumination, 1 - retention, "hair illumination range"
    )
    gate = _scalar(
        tree, "ADD", retention, illuminated_fraction, "hair illumination retention"
    )
    gate_switch = _control(tree, "hair illumination gate enable", gate_enable, bypass)
    effective_gate = _select_scalar(
        tree, 1.0, gate, gate_switch, "hair illumination gate"
    )
    final = _scalar(
        tree, "MULTIPLY", permitted, effective_gate, "hair final controlled highlight"
    )
    for socket in consumers:
        tree.links.new(final, socket)
    return {
        "feature": "hair",
        "material": material.name,
        "actor": material.get("performer_id"),
        "originals": originals,
        "permission": permission_report,
        "controls": {
            "permission": permission_switch.node.name,
            "illumination": gate_switch.node.name,
        },
        "requested_enable": {
            "permission": permission_enable,
            "illumination": gate_enable,
        },
        "illumination_source": {
            "node": illumination_socket.node.name,
            "socket": illumination_socket.name,
        },
        "illumination_semantics": "combined illumination artistic gate; not pure light visibility",
        "retention": retention,
        "bypass": bypass,
        "reconnected_consumers": [_socket_record(socket) for socket in consumers],
        "preserved": [
            "existing band direction/exponent/strength/tint",
            "MMD Color and Alpha",
            "base and sphere textures",
            "existing contact AO and material palette",
        ],
    }, None


def _cloth(material, options, bypass):
    tree = material.node_tree
    if tree.nodes.get(PREFIX + "cloth sheen enable"):
        return None, "cloth controls already installed"
    # The saved source also labels the blush overlay as cloth. It is not a
    # textile; an actor whitelist alone must never apply sheen controls to it.
    source_name = material.get("source_mmd_material_name", material.name)
    if source_name.split(".")[0].rstrip("+") == "脸红":
        return None, "source blush overlay is not textile"
    role = material.get(
        "character_layer_role",
        material.get("aether_surface", material.get("look_category")),
    )
    if role != "cloth":
        return None, "material is not an audited cloth role"
    item = tree.nodes.get(CLOTH_NODE)
    if not item or item.type != "BSDF_PRINCIPLED" or item not in _active_nodes(tree):
        return None, "no active nonmetal cloth Principled branch; masked metal retained"
    metallic = item.inputs["Metallic"]
    if metallic.is_linked or metallic.default_value > 0.05:
        return None, "cloth branch metallic input is not the audited dielectric"
    targets = {}
    if "sheen_tint" in options:
        tint = tuple(float(value) for value in options["sheen_tint"])
        if len(tint) == 3:
            tint += (1.0,)
        if len(tint) != 4 or any(
            not math.isfinite(value) or value < 0 for value in tint
        ):
            raise ValueError(
                "sheen_tint must contain three or four finite nonnegative linear values"
            )
        targets["Sheen Tint"] = tint
    if "sheen_roughness" in options:
        targets["Sheen Roughness"] = _unit(
            options["sheen_roughness"], "sheen_roughness"
        )
    if not targets:
        return None, "no explicit sheen_tint or sheen_roughness requested"
    for name in targets:
        socket = item.inputs.get(name)
        if not socket or len(socket.links) > 1 or _animated(socket):
            return (
                None,
                "requested sheen input is missing, ambiguous or animated: " + name,
            )
    enable = _unit(options.get("enabled", True), "cloth enabled")
    originals = {name: _socket_record(item.inputs[name]) for name in targets}
    preserved = {
        name: _socket_record(item.inputs[name])
        for name in ("Sheen Weight", "Roughness", "Metallic", "Base Color", "Alpha")
    }
    physical_mix = tree.nodes.get("Aether v2 | toon and physical layers")
    if physical_mix:
        preserved["physical_mix"] = _socket_record(physical_mix.inputs[0])
    switch = _control(tree, "cloth sheen enable", enable, bypass)
    for name, target in targets.items():
        socket = item.inputs[name]
        original = _source(socket)
        label = "cloth " + name
        if name == "Sheen Tint":
            selector = _node(tree, "ShaderNodeMixRGB", label + " selector")
            selector.blend_type = "MIX"
            selector.use_clamp = False
            _plug(tree, switch, selector.inputs[0])
            _plug(tree, original, selector.inputs[1])
            _plug(tree, target, selector.inputs[2])
            selected = selector.outputs[0]
        else:
            selected = _select_scalar(tree, original, target, switch, label)
        tree.links.new(selected, socket)
    return {
        "feature": "cloth",
        "material": material.name,
        "actor": material.get("performer_id"),
        "node": item.name,
        "targets": {name: _plain(value) for name, value in targets.items()},
        "originals": originals,
        "preserved_inputs": preserved,
        "control": switch.node.name,
        "requested_enable": enable,
        "bypass": bypass,
        "scope": "existing dielectric cloth branch only; closure, physical mix and metal masks retained",
    }, None


def apply_material_response(scene, spec, *, bypass=False):
    """Install explicitly selected hair/sheening controls and return JSON data.

    No material changes occur when both feature sections are absent. Invalid
    parameter values raise before changing that material. Unsupported branches
    are skipped and reported. The caller must use a new copy of the input for
    a different installation; use the control values or bypass helper afterward.
    """
    if scene.get("character_layer_revision") != spec.get(
        "input_revision", INPUT_REVISION
    ):
        raise ValueError("Expected the audited Character Layers input revision")
    materials = _scene_materials(scene)
    report = {
        "id": spec.get("id", "material-response-transfer-v1"),
        "source": bpy.data.filepath,
        "prefix": PREFIX,
        "bypass": bool(bypass),
        "changed": [],
        "skipped": [],
        "metal_retained": [],
        "saved": False,
        "rendered": False,
        "preferences_changed": False,
    }
    for material in materials:
        if not material.node_tree:
            continue
        for item in _active_nodes(material.node_tree):
            if item.type == "BSDF_PRINCIPLED" and (
                "gold" in item.name.lower()
                or (
                    not item.inputs["Metallic"].is_linked
                    and item.inputs["Metallic"].default_value > 0.5
                )
            ):
                report["metal_retained"].append(
                    {
                        "material": material.name,
                        "node": item.name,
                        "metallic": _socket_record(item.inputs["Metallic"]),
                        "roughness": _socket_record(item.inputs["Roughness"]),
                    }
                )
    for feature, installer in (("hair", _hair), ("cloth", _cloth)):
        section = spec.get(feature)
        if section is None:
            continue
        if not any(
            key in options
            for options in (spec, section)
            for key in ("actors", "materials")
        ):
            report["skipped"].append(
                {
                    "feature": feature,
                    "reason": "explicit actors/materials whitelist required",
                }
            )
            continue
        selected = [
            material for material in materials if _selected(material, spec, section)
        ]
        # Report missing named inputs, rather than silently accepting a typo.
        names = {material.name for material in materials}
        for name in set(section.get("materials", ())) - names:
            report["skipped"].append(
                {
                    "feature": feature,
                    "material": name,
                    "reason": "material is absent from the supplied scene",
                }
            )
        for material in selected:
            if not material.node_tree:
                report["skipped"].append(
                    {
                        "feature": feature,
                        "material": material.name,
                        "reason": "no node tree",
                    }
                )
                continue
            change, reason = installer(
                material, _options(material, section), bool(bypass)
            )
            if change:
                report["changed"].append(change)
            else:
                report["skipped"].append(
                    {"feature": feature, "material": material.name, "reason": reason}
                )
    report["metal_retained"].sort(key=lambda item: (item["material"], item["node"]))
    report["counts"] = {
        "hair": sum(item["feature"] == "hair" for item in report["changed"]),
        "cloth": sum(item["feature"] == "cloth" for item in report["changed"]),
        "metal_retained": len(report["metal_retained"]),
        "skipped": len(report["skipped"]),
    }
    return report


def set_material_response_bypass(scene, bypass=True, *, actors=None, materials=None):
    """Toggle only this module's enable controls; return old/new values."""
    changes = []
    for material in _scene_materials(scene):
        if actors is not None and material.get("performer_id") not in actors:
            continue
        if materials is not None and material.name not in materials:
            continue
        if not material.node_tree:
            continue
        for item in material.node_tree.nodes:
            if item.name.startswith(PREFIX) and "transfer_requested_enable" in item:
                socket = item.outputs[0]
                old = float(socket.default_value)
                socket.default_value = (
                    0 if bypass else item["transfer_requested_enable"]
                )
                changes.append(
                    {
                        "material": material.name,
                        "node": item.name,
                        "old": old,
                        "new": float(socket.default_value),
                    }
                )
    return changes
