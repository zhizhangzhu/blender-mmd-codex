"""Four reversible Ikhor-only NPR refinements for an unsaved pinned v7.

API: report = apply(scene, spec). No open/save/render, image replacement, scene
mutation or rig edits are performed by apply. set_module_enabled(scene, name,
0/1) changes only the new Value-node controls for a subsequent ablation.

Standalone Blender CLI performs CPU graph assertions only and optionally
writes a new JSON report. It never renders or saves a blend.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

PREFIX = "Clean Ikhor | "
ORIGINAL = "Ikhor character | "
SOURCE_SHA256 = "f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692"
MODULES = ("palette", "response_ramp", "highlight_metal", "rim")


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def serial(value):
    if isinstance(value, (int, float, bool, str)) or value is None:
        return value
    try:
        return [serial(item) for item in value]
    except TypeError:
        return getattr(value, "name_full", str(value))


def socket_record(socket):
    return {
        "default": serial(getattr(socket, "default_value", None)),
        "links": [
            (link.from_node.name, link.from_socket.identifier) for link in socket.links
        ],
    }


def node_inputs(node):
    return [(socket.identifier, socket_record(socket)) for socket in node.inputs]


def close(actual, expected, label):
    actual, expected = serial(actual), serial(expected)
    if isinstance(actual, list):
        assert len(actual) == len(expected), label
        for a, b in zip(actual, expected):
            close(a, b, label)
    else:
        assert abs(actual - expected) < 0.00001, (label, actual, expected)


def required(tree, suffix):
    node = tree.nodes.get(ORIGINAL + suffix)
    if node is None:
        raise ValueError("Missing pinned Ikhor node: " + suffix)
    return node


def new_node(tree, kind, label):
    node = tree.nodes.new(kind)
    node.name, node.label = PREFIX + label, label
    return node


def plug(tree, value, socket):
    if hasattr(value, "is_output"):
        tree.links.new(value, socket)
    else:
        socket.default_value = value


def math(tree, operation, first, second, label):
    node = new_node(tree, "ShaderNodeMath", label)
    node.operation = operation
    plug(tree, first, node.inputs[0])
    plug(tree, second, node.inputs[1])
    return node.outputs[0]


def smooth(tree, value, low, high, label):
    node = new_node(tree, "ShaderNodeMapRange", label)
    node.clamp, node.interpolation_type = True, "SMOOTHSTEP"
    plug(tree, value, node.inputs["Value"])
    node.inputs["From Min"].default_value = low
    node.inputs["From Max"].default_value = high
    return node.outputs[0]


def mix(tree, first, second, factor, label):
    node = new_node(tree, "ShaderNodeMixRGB", label)
    node.blend_type, node.use_clamp = "MIX", False
    for value, socket in zip((factor, first, second), node.inputs):
        plug(tree, value, socket)
    return node.outputs[0]


def scalar_lerp(tree, old, target, enabled, label):
    delta = math(tree, "SUBTRACT", target, old, label + " delta")
    node = new_node(tree, "ShaderNodeMath", label + " reversible parameter")
    node.operation = "MULTIPLY_ADD"
    for value, socket in zip((enabled, delta, old), node.inputs):
        plug(tree, value, socket)
    return node.outputs[0]


def input_change(tree, socket, target, enabled, label, changes):
    old = socket.links[0].from_socket if socket.is_linked else socket.default_value
    previous = socket_record(socket)
    plug(tree, scalar_lerp(tree, old, target, enabled, label), socket)
    changes.append({"target": label, "old": previous, "new_enabled": target})


def output_change(tree, socket, target, enabled, label, changes):
    destinations = [link.to_socket for link in socket.links]
    previous = float(socket.default_value)
    replacement = scalar_lerp(tree, socket, target, enabled, label)
    for destination in destinations:
        tree.links.new(replacement, destination)
    changes.append({"target": label, "old": previous, "new_enabled": target})


def white_permission(tree, spec):
    settings = spec["white_outer"]
    base = tree.nodes.get("mmd_base_tex")
    assert base and base.image, "White permission requires the original base image"
    split = new_node(tree, "ShaderNodeSeparateColor", "white outer source HSV")
    split.mode = "HSV"
    tree.links.new(base.outputs["Color"], split.inputs[0])
    saturated = smooth(
        tree,
        split.outputs[1],
        settings["saturation_full_below"],
        settings["saturation_zero_above"],
        "white saturation exclusion",
    )
    neutral = math(tree, "SUBTRACT", 1, saturated, "low-chroma white permission")
    bright = smooth(
        tree,
        split.outputs[2],
        settings["value_zero_below"],
        settings["value_full_above"],
        "painted white value permission",
    )
    permission = math(tree, "MULTIPLY", neutral, bright, "white HSV permission")
    sources = []
    for suffix in settings["original_protection_masks"]:
        original = tree.nodes.get(ORIGINAL + suffix)
        if original:
            protected = smooth(
                tree,
                original.outputs[0],
                *settings["protection_full_range"],
                suffix + " preserved exclusion",
            )
            inverse = math(tree, "SUBTRACT", 1, protected, suffix + " inverse")
            permission = math(
                tree, "MULTIPLY", permission, inverse, suffix + " excluded from white"
            )
            sources.append(original.name)
    assert sources, "The permitted clothing must retain its gold/cyan protection"
    return permission, {
        "source_image": base.image.name,
        "source_node": base.name,
        "protected_original_masks": sources,
        "settings": settings,
    }


def ramp_copy(tree, source, colors, positions, label):
    node = new_node(tree, "ShaderNodeValToRGB", label)
    node.color_ramp.color_mode = source.color_ramp.color_mode
    node.color_ramp.interpolation = source.color_ramp.interpolation
    for item, position, color in zip(node.color_ramp.elements, positions, colors):
        item.position, item.color = position, color
    assert source.inputs[0].is_linked
    tree.links.new(source.inputs[0].links[0].from_socket, node.inputs[0])
    return node.outputs[0]


def palette_ramp(tree, role, permission, controls, spec, changes):
    source = required(tree, "single material palette")
    assert len(source.color_ramp.elements) == 2
    assert source.color_ramp.interpolation == spec["ramp"]["interpolation"]
    colors = [list(item.color) for item in source.color_ramp.elements]
    positions = [item.position for item in source.color_ramp.elements]
    close(colors, spec["baseline_palettes"][role], role + " baseline colors")
    close(positions, spec["ramp"]["baseline_positions"], role + " baseline ramp")
    destinations = [link.to_socket for link in source.outputs[0].links]
    target_colors, target_positions = (
        spec["palettes"][role],
        spec["ramp"]["positions"][role],
    )
    palette_on = math(
        tree, "MULTIPLY", controls["palette"], permission, "palette permission"
    )
    response_on = math(
        tree,
        "MULTIPLY",
        controls["response_ramp"],
        permission,
        "response ramp permission",
    )
    color_only = ramp_copy(
        tree, source, target_colors, positions, "new palette old response"
    )
    response_only = ramp_copy(
        tree, source, colors, target_positions, "old palette new response"
    )
    both = ramp_copy(
        tree, source, target_colors, target_positions, "new palette new response"
    )
    old_response = mix(
        tree, source.outputs[0], color_only, palette_on, "palette with old response"
    )
    new_response = mix(
        tree, response_only, both, palette_on, "palette with new response"
    )
    final = mix(
        tree,
        old_response,
        new_response,
        response_on,
        "independent palette and response switches",
    )
    for destination in destinations:
        tree.links.new(final, destination)
    changes.append(
        {
            "target": "palette and response ramp",
            "old_node_retained": source.name,
            "old_colors": colors,
            "new_colors": target_colors,
            "old_positions": positions,
            "new_positions": target_positions,
            "independent_four_states": True,
            "destinations": [
                socket.node.name + "." + socket.identifier for socket in destinations
            ],
        }
    )


def constant(socket):
    if not socket.is_linked:
        return float(socket.default_value)
    assert len(socket.links) == 1 and socket.links[0].from_node.type == "VALUE"
    return float(socket.links[0].from_socket.default_value)


def white_midtones(tree, permission, controls, spec, changes):
    """Raise licensed white midtones without imposing an output-color floor."""
    settings = spec["white_outer"]
    source = required(tree, "source times single palette").outputs[0]
    destinations = [link.to_socket for link in source.links]
    luminance = new_node(tree, "ShaderNodeRGBToBW", "white shaded NPR luminance")
    tree.links.new(source, luminance.inputs[0])
    used = smooth(
        tree,
        luminance.outputs[0],
        settings["headroom_full_below"],
        settings["headroom_zero_above"],
        "white existing highlight headroom used",
    )
    remaining = math(tree, "SUBTRACT", 1, used, "white remaining highlight headroom")
    enabled = math(
        tree,
        "MULTIPLY",
        controls["palette"],
        permission,
        "white midtone palette permission",
    )
    enabled = math(tree, "MULTIPLY", enabled, remaining, "white midtone available gain")
    gain = mix(
        tree,
        (1, 1, 1, 1),
        settings["midtone_gain"],
        enabled,
        "white local multiplicative midtone gain",
    )
    result = new_node(tree, "ShaderNodeMixRGB", "white shaded color times local gain")
    result.blend_type, result.use_clamp = "MULTIPLY", False
    result.inputs[0].default_value = 1
    tree.links.new(source, result.inputs[1])
    tree.links.new(gain, result.inputs[2])
    for destination in destinations:
        tree.links.new(result.outputs[0], destination)
    changes.append(
        {
            "target": "licensed white NPR midtone gain before original AO",
            "old_full_gain": [1, 1, 1, 1],
            "new_full_gain": settings["midtone_gain"],
            "headroom_luminance_range": [
                settings["headroom_full_below"],
                settings["headroom_zero_above"],
            ],
            "source": source.node.name,
            "destinations": [
                socket.node.name + "." + socket.identifier for socket in destinations
            ],
            "constant_white_floor": False,
        }
    )


def masked_parameter(tree, source, expected, target, enabled, label, changes):
    assert source.operation == "ADD"
    base = constant(source.inputs[0])
    term = source.inputs[1].links[0].from_node
    assert term.type == "MATH" and term.operation == "MULTIPLY"
    assert term.inputs[0].is_linked and not term.inputs[1].is_linked
    close(base + term.inputs[1].default_value, expected, label + " baseline")
    input_change(tree, term.inputs[1], target - base, enabled, label, changes)


def highlighter(tree, role, source_name, controls, spec, changes):
    enabled = controls["highlight_metal"]
    if role == "hair":
        band = required(tree, "directional hair band")
        strength = required(tree, "hair band strength")
        settings = spec["hair_highlight"]
        close(
            band.inputs[1].default_value, settings["baseline_exponent"], "hair exponent"
        )
        close(
            strength.outputs[0].default_value,
            settings["baseline_strength"],
            "hair strength",
        )
        input_change(
            tree,
            band.inputs[1],
            settings["exponent"],
            enabled,
            "hair exponent",
            changes,
        )
        output_change(
            tree,
            strength.outputs[0],
            settings["strength"],
            enabled,
            "hair highlight strength",
            changes,
        )
    if source_name in spec["gold_highlight"]["materials"]:
        settings = spec["gold_highlight"]
        physical = required(tree, "material-specific physical closure")
        roughness = physical.inputs["Roughness"].links[0].from_node
        masked_parameter(
            tree,
            roughness,
            settings["baseline_roughness"],
            settings["roughness"],
            enabled,
            "gold roughness mask delta",
            changes,
        )
        closure_mix = required(tree, "gold versus cloth closure mix")
        masked_parameter(
            tree,
            closure_mix,
            settings["baseline_mix"],
            settings["mix"],
            enabled,
            "gold physical mix mask delta",
            changes,
        )


def rim_change(tree, role, permission, controls, spec, changes):
    settings = spec["rim"]
    enabled = math(tree, "MULTIPLY", controls["rim"], permission, "rim permission")
    amount = required(tree, "narrow lit-side rim")
    power = amount.inputs[0].links[0].from_node
    assert power.type == "MATH" and power.operation == "POWER"
    strength = required(tree, "rim strength")
    close(power.inputs[1].default_value, settings["baseline_power"], "rim power")
    close(
        strength.outputs[0].default_value,
        settings["baseline_strength"][role],
        role + " rim",
    )
    input_change(
        tree, power.inputs[1], settings["power"], enabled, "rim edge power", changes
    )
    output_change(
        tree,
        strength.outputs[0],
        settings["strength"][role],
        enabled,
        "rim strength",
        changes,
    )


def protected_material_state(material):
    tree = material.node_tree
    records = {}
    for node in tree.nodes:
        if (
            node.name.startswith("mmd_")
            or node.type in {"OUTPUT_MATERIAL", "OUTPUT_AOV"}
            or node.name
            in {
                ORIGINAL + "preserve original MMD Alpha",
                ORIGINAL + "original animated PMX transparency",
            }
        ):
            records[node.name] = {
                "type": node.bl_idname,
                "inputs": node_inputs(node),
                "image": node.image.name
                if node.type == "TEX_IMAGE" and node.image
                else None,
                "node_tree": node.node_tree.name
                if node.type == "GROUP" and node.node_tree
                else None,
            }
    physical = tree.nodes.get(ORIGINAL + "material-specific physical closure")
    if physical:
        records["physical source preserved"] = {
            name: socket_record(physical.inputs[name])
            for name in (
                "Base Color",
                "Metallic",
                "Normal",
                "Coat Weight",
                "Sheen Weight",
            )
        }
    return {
        "performer_id": material.get("performer_id"),
        "role": material.get("ikhor_material_role"),
        "protected_nodes": records,
        "action": material.animation_data.action.name
        if material.animation_data and material.animation_data.action
        else None,
        "tree_action": tree.animation_data.action.name
        if tree.animation_data and tree.animation_data.action
        else None,
    }


def set_module_enabled(scene, module, value):
    assert module in MODULES and value in (0, 1)
    changed, seen = [], set()
    for obj in scene.objects:
        if obj.type != "MESH" or obj.get("performer_id") != "ikhor":
            continue
        for material in obj.data.materials:
            if not material or material.as_pointer() in seen:
                continue
            seen.add(material.as_pointer())
            node = material.node_tree.nodes.get(PREFIX + "enable " + module)
            if node:
                node.outputs[0].default_value = value
                changed.append(material.name)
    return changed


def apply(scene, spec):
    source = Path(bpy.data.filepath)
    assert source.is_file() and sha256(source) == SOURCE_SHA256
    assert (
        spec["source_blend_sha256"] == SOURCE_SHA256 and spec["performer_id"] == "ikhor"
    )
    assert set(spec["modules"]) == set(MODULES)
    assert all(value in (0, 1) for value in spec["modules"].values())
    actors = [
        obj
        for obj in scene.objects
        if obj.type == "MESH"
        and obj.get("performer_id") == "ikhor"
        and not obj.hide_render
    ]
    assert len(actors) == 1, [obj.name for obj in actors]
    all_materials = {
        material for obj in actors for material in obj.data.materials if material
    }
    materials = {
        material.get("source_mmd_material_name", material.name): material
        for material in all_materials
        if material.get("ikhor_material_role")
    }
    assert set(materials) == set(spec["expected_source_materials"])
    crypto = scene.compositing_node_group.nodes.get(
        "Caption | both performers native object coverage"
    )
    expected_ids = {
        obj.name
        for obj in scene.objects
        if obj.type == "MESH"
        and obj.get("performer_id") in {"ikhor", "aksiniya"}
        and not obj.hide_render
    }
    assert crypto and set(crypto.matte_id.split(",")) == expected_ids
    crypto_before = crypto.matte_id
    for material in all_materials:
        assert not any(
            node.name.startswith(PREFIX) for node in material.node_tree.nodes
        ), "Refusing to stack Clean Ikhor"
    before = {
        material.name: protected_material_state(material) for material in all_materials
    }
    other_before = {
        material.name: [
            (node.name, node_inputs(node)) for node in material.node_tree.nodes
        ]
        for material in bpy.data.materials
        if material not in all_materials and material.node_tree
    }
    report = {
        "id": spec["id"],
        "parameter_iteration": spec.get("parameter_iteration", 1),
        "source": str(source),
        "source_sha256": SOURCE_SHA256,
        "modules": dict(spec["modules"]),
        "materials": [],
        "unchanged_materials": [],
        "no_new_emission_probe_or_ao": True,
        "technical_scope": "Input and node-graph assertions only; bypass pixel equality and art remain untested.",
        "art_status": "pending",
    }
    for source_name, material in sorted(materials.items()):
        role, tree = material["ikhor_material_role"], material.node_tree
        white = role == "cloth" and source_name in spec["white_outer"]["materials"]
        palette_role = (
            "white_outer"
            if white
            else role
            if role in {"face", "skin", "hair"}
            else None
        )
        gold = source_name in spec["gold_highlight"]["materials"]
        if source_name in spec["exclude_materials"] or not (palette_role or gold):
            report["unchanged_materials"].append(material.name)
            continue
        item = {
            "material": material.name,
            "source_name": source_name,
            "role": role,
            "controls": {},
            "changes": [],
        }
        controls = {}
        for module in MODULES:
            node = new_node(tree, "ShaderNodeValue", "enable " + module)
            node.outputs[0].default_value = spec["modules"][module]
            controls[module] = node.outputs[0]
            item["controls"][module] = node.name
        permission = 1
        if white:
            permission, item["white_permission"] = white_permission(tree, spec)
        if palette_role:
            palette_ramp(
                tree, palette_role, permission, controls, spec, item["changes"]
            )
            if white:
                white_midtones(tree, permission, controls, spec, item["changes"])
            rim_change(tree, palette_role, permission, controls, spec, item["changes"])
        highlighter(tree, role, source_name, controls, spec, item["changes"])
        assert not any(
            node.bl_idname
            in {
                "ShaderNodeEmission",
                "ShaderNodeBsdfDiffuse",
                "ShaderNodeShaderToRGB",
                "ShaderNodeAmbientOcclusion",
            }
            and node.name.startswith(PREFIX)
            for node in tree.nodes
        )
        report["materials"].append(item)
    for material in all_materials:
        assert protected_material_state(material) == before[material.name], (
            material.name + " protected source changed"
        )
        if material.get("ikhor_material_role"):
            source_node = material.node_tree.nodes["mmd_shader"]
            aovs = [
                node
                for node in material.node_tree.nodes
                if node.type == "OUTPUT_AOV" and node.aov_name == "ReferenceDuetActor"
            ]
            assert (
                len(aovs) == 1
                and aovs[0].inputs["Value"].links[0].from_socket
                == source_node.outputs["Alpha"]
            )
    for material in bpy.data.materials:
        if material.name in other_before:
            assert [
                (node.name, node_inputs(node)) for node in material.node_tree.nodes
            ] == other_before[material.name], material.name
    assert crypto.matte_id == crypto_before
    assert sha256(source) == SOURCE_SHA256
    report["preserved"] = {
        "all_26_original_mmd_color_alpha_sphere_inputs": True,
        "original_feature_and_outline_materials": True,
        "physical_basecolor_and_metallic_sources": True,
        "original_alpha_respecting_aov_links": True,
        "other_materials": True,
        "cryptomatte_ids": crypto_before,
        "source_file": True,
        "actions_shapes_geometry_camera_lights_stage_exposure": "Not written by this module",
    }
    report["passed"] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output-report", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    spec = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    report = apply(bpy.context.scene, spec)
    for module in MODULES:
        changed = set_module_enabled(bpy.context.scene, module, 0)
        assert changed
    report["all_four_switches_set_to_zero_in_memory"] = True
    report["bypass_scope"] = (
        "Switch values and retained graph branches verified; no image was rendered."
    )
    if args.output_report:
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        with args.output_report.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    print("CLEAN_IKHOR_GRAPH_PASSED", len(report["materials"]), flush=True)


if __name__ == "__main__":
    main()
