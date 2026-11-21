"""Selective HDR motifs and narrow directional edges for Reference Transfer v3.

Call apply_bold_materials(scene, spec) in the main migration's independent copy.
This module never renders, saves, changes lights, or changes preferences. It
only adds to the *current* NPR Emission Color, before existing PBR/Alpha closure
mixes. The optional COLOR AOV is an artistic source signal, not an isolated
physical Emission pass; it precedes existing PBR mixture attenuation.

spec['variant'] selects pilot/boost (multipliers in the companion preset).
Each explicit group has its own strength/enable; head and body rims are separate
groups. Face/skin/feature material roles, blush and '+' overlays are excluded.
Mixed clothing atlases may also contain exposed skin: a material role does not
prove per-pixel skin exclusion. Directional body rims may reach those narrow
skin contours; core motif permissions require separate UV/mask review.
set_bold_materials_bypass(scene, True) both zeros new AOV sources and physically
reconnects the original NPR Color socket for exact original-path restoration.
"""

import hashlib
import json
import math
from pathlib import Path

import bpy

PREFIX = "Bold wedding material | "
STATE = "bold_wedding_material_state"
SAFE_ROLES = {"hair", "cloth", "trim", "gold", "leather", "fur"}


def _node(tree, kind, label):
    name = PREFIX + label
    if tree.nodes.get(name):
        raise ValueError("Refusing to duplicate " + name)
    item = tree.nodes.new(kind)
    item.name, item.label = name, label
    return item


def _plug(tree, source, target):
    if hasattr(source, "is_output"):
        tree.links.new(source, target)
    else:
        target.default_value = source


def _math(tree, op, first, second, label):
    item = _node(tree, "ShaderNodeMath", label)
    item.operation = op
    _plug(tree, first, item.inputs[0])
    if second is not None:
        _plug(tree, second, item.inputs[1])
    return item.outputs[0]


def _vector(tree, op, first, second, label):
    item = _node(tree, "ShaderNodeVectorMath", label)
    item.operation = op
    _plug(tree, first, item.inputs[0])
    _plug(tree, second, item.inputs[3] if op == "SCALE" else item.inputs[1])
    return item.outputs["Value"] if op == "DOT_PRODUCT" else item.outputs[0]


def _range(tree, value, low, high, label):
    if not low < high:
        raise ValueError("Invalid smooth range: " + label)
    item = _node(tree, "ShaderNodeMapRange", label)
    item.interpolation_type, item.clamp = "SMOOTHSTEP", True
    _plug(tree, value, item.inputs["Value"])
    item.inputs["From Min"].default_value = low
    item.inputs["From Max"].default_value = high
    return item.outputs[0]


def _number(value, label, high=None):
    value = float(value)
    if not math.isfinite(value) or value < 0 or (high is not None and value > high):
        raise ValueError("Invalid finite nonnegative " + label)
    return value


def _socket_id(socket):
    return {
        "node": socket.node.name,
        "socket": socket.name,
        "identifier": socket.identifier,
        "index": list(socket.node.outputs).index(socket),
    }


def _source(tree, options):
    item = tree.nodes.get(options["node"])
    if not item:
        raise ValueError("Missing mask source node: " + options["node"])
    output = options.get("output", "Color")
    socket = (
        item.outputs.get(output) if isinstance(output, str) else item.outputs[output]
    )
    if socket is None:
        raise ValueError("Missing mask source output: " + str(output))
    return socket


def _edge(tree, options, label):
    """Narrow view edge times the existing rim's lit-side direction."""
    geometry = tree.nodes.get("Reference transfer | surface geometry")
    rim = tree.nodes.get("Reference transfer | rim direction")
    if not geometry or not rim:
        raise ValueError("No audited geometry/rim direction for directional edge")
    facing = _vector(
        tree,
        "DOT_PRODUCT",
        geometry.outputs["Normal"],
        geometry.outputs["Incoming"],
        label + " view cosine",
    )
    facing = _math(tree, "ABSOLUTE", facing, None, label + " absolute facing")
    edge = _math(tree, "SUBTRACT", 1, facing, label + " grazing edge")
    edge = _math(tree, "MAXIMUM", edge, 0, label + " positive edge")
    edge = _math(tree, "POWER", edge, options.get("power", 5.5), label + " narrow edge")
    lit = _vector(
        tree,
        "DOT_PRODUCT",
        geometry.outputs["Normal"],
        rim.outputs[0],
        label + " existing rim side",
    )
    lit = _math(tree, "MAXIMUM", lit, 0, label + " positive rim side")
    return _math(tree, "MULTIPLY", edge, lit, label + " directional edge")


def _mask(tree, options, label):
    kind = options["type"]
    if kind == "directional_edge":
        return _edge(tree, options, label), {
            "type": kind,
            "power": options.get("power", 5.5),
            "direction": "Reference transfer | rim direction.Vector",
            "semantics": "view-angle edge times lit-side direction; not visibility/depth rim",
        }
    source = _source(tree, options)
    if kind == "channel":
        if source.type not in {"VALUE", "INT", "BOOLEAN"}:
            raise ValueError("Channel mask source must be scalar")
        low, high = options.get("range", [0.25, 0.80])
        result = _range(tree, source, low, high, label + " channel permission")
        return result, {
            "type": kind,
            "source": _socket_id(source),
            "range": [low, high],
            "semantics": "existing color-derived artistic mask; not game Lightmap/metallic data",
        }
    if kind != "hsv":
        raise ValueError("Unsupported selective mask: " + str(kind))
    if source.node.bl_idname != "ShaderNodeTexImage" or not source.node.image:
        raise ValueError("HSV permission requires the audited stable base texture node")
    split = _node(tree, "ShaderNodeSeparateColor", label + " source HSV")
    split.mode = "HSV"
    tree.links.new(source, split.inputs[0])
    h0, h1, h2, h3 = options["hue"]
    hue_low = _range(tree, split.outputs[0], h0, h1, label + " hue enters")
    hue_high = _range(tree, split.outputs[0], h2, h3, label + " hue exits")
    hue_high = _math(tree, "SUBTRACT", 1, hue_high, label + " bounded hue exit")
    hue = _math(tree, "MULTIPLY", hue_low, hue_high, label + " blue hue")
    saturation = _range(
        tree, split.outputs[1], *options["saturation"], label + " saturation permission"
    )
    value = _range(
        tree, split.outputs[2], *options["value"], label + " bright motif permission"
    )
    result = _math(tree, "MULTIPLY", hue, saturation, label + " colored motif")
    result = _math(tree, "MULTIPLY", result, value, label + " bright colored motif")
    return result, {
        "type": kind,
        "source": _socket_id(source),
        "image": source.node.image.name,
        "hue": options["hue"],
        "saturation": options["saturation"],
        "value": options["value"],
        "semantics": "stable UV color selection in shader-linear RGB; not original emission data",
    }


def _materials(scene):
    result = {}
    for obj in scene.objects:
        if obj.type == "MESH" and not obj.hide_render:
            for slot in obj.material_slots:
                if slot.material and slot.material.get("performer_id"):
                    result[slot.material.name] = slot.material
    return result


def _input_hash(expected):
    if not expected:
        return
    source = Path(bpy.data.filepath)
    if not source.is_file():
        raise ValueError("A saved audited source is required")
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest().lower() != expected.lower():
        raise ValueError("Bold material input SHA256 does not match the audited source")


def apply_bold_materials(scene, spec):
    """Install explicit material groups; return serializable changes/skips.

    All existing closure, Alpha, palette, SDF, AO and texture inputs stay intact.
    An unexpected group contract raises; use an independent working copy, as
    with the parent migration. Repeated installation skips installed materials.
    """
    required = spec.get("required_reference_transfer_revision")
    if required and scene.get("reference_transfer_revision") != required:
        raise ValueError("Expected the audited Reference Transfer scene revision")
    if spec.get("verify_source_hash", True):
        _input_hash(spec.get("source_sha256"))
    variant = spec.get("variant", "pilot")
    multiplier = _number(
        spec.get("variant_multipliers", {"pilot": 1.0})[variant], "variant multiplier"
    )
    aov_name = spec.get("aov", "BoldWeddingEmission")
    report = {
        "id": spec.get("id", "duet-bold-wedding-emission-v1"),
        "variant": variant,
        "prefix": PREFIX,
        "changed": [],
        "skipped": [],
        "aov": aov_name,
        "aov_semantics": "masked HDR art source before PBR mix; Alpha multiplied; not physical emission pass",
        "saved": False,
        "rendered": False,
        "preferences_changed": False,
    }
    materials, selection = _materials(scene), {}
    for group in spec.get("groups", []):
        if not group.get("materials") or not group.get("actor"):
            raise ValueError(
                "Every bold emission group needs explicit actor and material names"
            )
        _number(group["strength"], "group strength")
        color = tuple(group["color"])
        if len(color) != 3 or any(
            _number(x, "linear emission color") > 1 for x in color
        ):
            raise ValueError(
                "Use a finite linear RGB tint in [0,1] and separate HDR strength"
            )
        for name in group["materials"]:
            material = materials.get(name)
            if not material or material.get("performer_id") != group["actor"]:
                report["skipped"].append(
                    {
                        "material": name,
                        "group": group["id"],
                        "reason": "actor/material not present",
                    }
                )
                continue
            role = material.get("character_layer_role")
            source_name = material.get("source_mmd_material_name", name).split(".")[0]
            if (
                role not in SAFE_ROLES
                or source_name.endswith("+")
                or source_name == "脸红"
            ):
                report["skipped"].append(
                    {
                        "material": name,
                        "group": group["id"],
                        "reason": "protected skin/feature/blush/overlay role",
                    }
                )
                continue
            selection.setdefault(name, []).append(group)
    for name, groups in selection.items():
        material = materials[name]
        if STATE in material:
            report["skipped"].append(
                {"material": name, "reason": "bold material controls already installed"}
            )
            continue
        tree = material.node_tree
        surface = tree.nodes.get(
            "Aether v2 | controlled toon surface"
        ) or tree.nodes.get("Look v3 | NPR surface")
        if (
            not surface
            or surface.bl_idname != "ShaderNodeEmission"
            or len(surface.inputs["Color"].links) != 1
        ):
            raise ValueError("Unexpected current NPR Emission Color contract: " + name)
        original = surface.inputs["Color"].links[0].from_socket
        switch = _node(tree, "ShaderNodeValue", "enable selective HDR")
        switch.outputs[0].default_value = _number(
            spec.get("enabled", True), "enabled", 1
        )
        switch["requested_enable"] = float(switch.outputs[0].default_value)
        combined, effects = None, []
        for group in groups:
            label = group["id"]
            mask, mask_record = _mask(tree, group["mask"], label)
            if group.get("edge_modulation"):
                edge = _edge(tree, group["edge_modulation"], label + " shape")
                floor = _number(
                    group["edge_modulation"].get("floor", 0.5), "edge floor", 1
                )
                edge = _math(
                    tree, "MULTIPLY", edge, 1 - floor, label + " shaped edge fraction"
                )
                edge = _math(tree, "ADD", floor, edge, label + " shaped core and edge")
                mask = _math(
                    tree, "MULTIPLY", mask, edge, label + " motif with edge shape"
                )
            enabled = _node(tree, "ShaderNodeValue", label + " enable")
            enabled.outputs[0].default_value = _number(
                group.get("enabled", True), label + " enabled", 1
            )
            gain = _node(tree, "ShaderNodeValue", label + " HDR strength")
            gain.outputs[0].default_value = float(group["strength"]) * multiplier
            amount = _math(
                tree, "MULTIPLY", mask, enabled.outputs[0], label + " enabled mask"
            )
            amount = _math(
                tree, "MULTIPLY", amount, gain.outputs[0], label + " HDR amount"
            )
            rgb = _vector(
                tree, "SCALE", tuple(group["color"]), amount, label + " HDR source"
            )
            combined = (
                rgb
                if combined is None
                else _vector(tree, "ADD", combined, rgb, label + " accumulated HDR")
            )
            effects.append(
                {
                    "group": label,
                    "mask": mask_record,
                    "strength": gain.outputs[0].default_value,
                    "color_linear": group["color"],
                    "enable_node": enabled.name,
                    "strength_node": gain.name,
                    "edge_modulation": group.get("edge_modulation"),
                }
            )
        controlled = _vector(
            tree, "SCALE", combined, switch.outputs[0], "enabled HDR source"
        )
        final = _vector(
            tree, "ADD", original, controlled, "unclamped HDR plus current NPR"
        )
        tree.links.new(final, surface.inputs["Color"])
        mmd = tree.nodes.get("mmd_shader")
        aov_rgb = controlled
        if mmd and mmd.outputs.get("Alpha"):
            aov_rgb = _vector(
                tree,
                "SCALE",
                controlled,
                mmd.outputs["Alpha"],
                "Alpha respecting emission source",
            )
        output = _node(tree, "ShaderNodeOutputAOV", "selected emission AOV")
        output.aov_name = aov_name
        tree.links.new(aov_rgb, output.inputs["Color"])
        state = {
            "surface": surface.name,
            "original": _socket_id(original),
            "final": _socket_id(final),
            "switch": switch.name,
            "revision": report["id"],
        }
        material[STATE] = json.dumps(state, ensure_ascii=False)
        report["changed"].append(
            {
                "material": name,
                "actor": material["performer_id"],
                "role": material.get("character_layer_role"),
                "surface": surface.name,
                "original": state["original"],
                "final": state["final"],
                "effects": effects,
                "closure_note": "existing PBR/PMX Alpha mixes remain downstream and attenuate the added NPR contribution",
            }
        )
    if report["changed"]:
        for layer in scene.view_layers:
            aov = layer.aovs.get(aov_name)
            if aov and aov.type != "COLOR":
                raise ValueError("Existing emission AOV has incompatible type")
            if not aov:
                aov = layer.aovs.add()
                aov.name, aov.type = aov_name, "COLOR"
            layer.update_render_passes()
        scene["bold_wedding_material_revision"] = report["id"]
    report["counts"] = {
        "materials": len(report["changed"]),
        "effects": sum(len(x["effects"]) for x in report["changed"]),
        "skipped": len(report["skipped"]),
    }
    return report


def set_bold_materials_bypass(scene, bypass):
    """Zero new AOVs and directly restore original Color links when bypassed."""
    report = []
    for material in _materials(scene).values():
        if STATE not in material:
            continue
        state = json.loads(material[STATE])
        tree = material.node_tree
        switch = tree.nodes[state["switch"]]
        switch.outputs[0].default_value = 0 if bypass else switch["requested_enable"]
        source = state["original"] if bypass else state["final"]
        socket = tree.nodes[source["node"]].outputs[source["index"]]
        tree.links.new(socket, tree.nodes[state["surface"]].inputs["Color"])
        report.append(
            {
                "material": material.name,
                "bypass": bool(bypass),
                "connected": _socket_id(socket),
                "source_AOV_enable": float(switch.outputs[0].default_value),
            }
        )
    return report
