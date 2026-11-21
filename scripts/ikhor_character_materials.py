"""Rebuild Ikhor's own NPR/material contract without touching motion or physics.

apply_ikhor_materials(scene, arm, spec) requires the root integrator's Ikhor
key/rim and posed head-axis helpers. It never saves, renders, changes lights,
preferences, geometry, PMX edge settings or bone data. Original MMD Color/Alpha
and all sphere/texture inputs remain the upstream sources. The missing edited
y1 face image has an explicit, reported same-character original-diffuse fallback.

No SDF is fabricated. Face form uses a posed head-forward normal, with a soft
form range *before* the calibrated key-facing combined light/occlusion response.
That diffuse probe is not an isolated visibility pass. All color masks below
are selected artistic HSV permissions, never inferred game Lightmap channels.
"""

import hashlib
from pathlib import Path

import bpy
from integrate_light_space import transform_variable, world_vector

PREFIX = "Ikhor character | "
AOVS = {
    "ReferenceDuetActor": "VALUE",
    "StageArtRim": "COLOR",
    "BoldWeddingEmission": "COLOR",
}


def _node(tree, kind, label):
    result = tree.nodes.new(kind)
    result.name, result.label = PREFIX + label, label
    return result


def _plug(tree, value, socket):
    if hasattr(value, "is_output"):
        tree.links.new(value, socket)
    else:
        socket.default_value = value


def _scalar(tree, operation, first, second=None, label=""):
    result = _node(tree, "ShaderNodeMath", label or operation)
    result.operation = operation
    _plug(tree, first, result.inputs[0])
    if second is not None:
        _plug(tree, second, result.inputs[1])
    return result.outputs[0]


def _vector(tree, operation, first, second=None, label=""):
    result = _node(tree, "ShaderNodeVectorMath", label or operation)
    result.operation = operation
    _plug(tree, first, result.inputs[0])
    if second is not None:
        _plug(
            tree, second, result.inputs[3] if operation == "SCALE" else result.inputs[1]
        )
    return result.outputs["Value"] if operation == "DOT_PRODUCT" else result.outputs[0]


def _value(tree, value, label):
    result = _node(tree, "ShaderNodeValue", label)
    result.outputs[0].default_value = value
    return result.outputs[0]


def _mix(tree, first, second, factor=1, blend="MULTIPLY", label=""):
    result = _node(tree, "ShaderNodeMixRGB", label or blend)
    result.blend_type, result.use_clamp = blend, False
    for value, socket in zip((factor, first, second), result.inputs):
        _plug(tree, value, socket)
    return result.outputs[0]


def _range(tree, value, low, high, label):
    result = _node(tree, "ShaderNodeMapRange", label)
    result.clamp, result.interpolation_type = True, "SMOOTHSTEP"
    _plug(tree, value, result.inputs["Value"])
    result.inputs["From Min"].default_value = low
    result.inputs["From Max"].default_value = high
    return result.outputs[0]


def _position(tree, obj, label):
    result = _node(tree, "ShaderNodeCombineXYZ", label)
    for index, socket in enumerate(result.inputs):
        driver = socket.driver_add("default_value").driver
        driver.type = "SCRIPTED"
        transform_variable(driver, "position", obj, index)
        driver.expression = "position"
    return result.outputs[0]


def _world(tree, first, second, label):
    result = world_vector(tree, first, second, PREFIX + label)
    result.node.name = PREFIX + label + " normalized"
    result.node.label = label + " normalized"
    return result


def _hsv(tree, base, settings, label):
    split = _node(tree, "ShaderNodeSeparateColor", label + " source HSV")
    split.mode = "HSV"
    tree.links.new(base.outputs["Color"], split.inputs[0])
    h0, h1, h2, h3 = settings["hue"]
    enter = _range(tree, split.outputs[0], h0, h1, label + " hue enters")
    leave = _scalar(
        tree,
        "SUBTRACT",
        1,
        _range(tree, split.outputs[0], h2, h3, label + " hue exits"),
    )
    hue = _scalar(tree, "MULTIPLY", enter, leave, label + " selected hue")
    saturation = _range(
        tree, split.outputs[1], *settings["saturation"], label + " selected saturation"
    )
    value = _range(
        tree, split.outputs[2], *settings["value"], label + " selected value"
    )
    mask = _scalar(
        tree,
        "MULTIPLY",
        hue,
        _scalar(tree, "MULTIPLY", saturation, value),
        label + " art permission",
    )
    if "uv_box" in settings:
        if not base.inputs["Vector"].is_linked:
            raise ValueError("UV window needs the original linked MMD base UV")
        xyz = _node(tree, "ShaderNodeSeparateXYZ", label + " original UV")
        tree.links.new(base.inputs["Vector"].links[0].from_socket, xyz.inputs[0])
        u0, u1, v0, v1 = settings["uv_box"]
        for axis, low, high in ((0, u0, u1), (1, v0, v1)):
            window = _scalar(
                tree,
                "MULTIPLY",
                _scalar(tree, "GREATER_THAN", xyz.outputs[axis], low),
                _scalar(tree, "LESS_THAN", xyz.outputs[axis], high),
            )
            mask = _scalar(tree, "MULTIPLY", mask, window, label + f" UV window {axis}")
    return mask


def _lighting(tree, geometry, role, helpers, spec):
    settings = spec["lighting_response"]
    key_position = _position(tree, helpers["key"], "actual key position")
    delta = _vector(
        tree,
        "SUBTRACT",
        key_position,
        geometry.outputs["Position"],
        "surface to actual key",
    )
    direction = _vector(tree, "NORMALIZE", delta, label="key facing normal")
    probe = _node(tree, "ShaderNodeBsdfDiffuse", "key facing diffuse probe")
    probe.inputs["Color"].default_value = (1, 1, 1, 1)
    tree.links.new(direction, probe.inputs["Normal"])
    rgb = _node(tree, "ShaderNodeShaderToRGB", "combined actual illumination")
    tree.links.new(probe.outputs[0], rgb.inputs[0])
    gray = _node(tree, "ShaderNodeRGBToBW", "illumination luminance")
    tree.links.new(rgb.outputs[0], gray.inputs[0])
    origin = _position(tree, helpers["origin"], "posed head position")
    reference = _vector(tree, "SUBTRACT", key_position, origin)
    distance2 = _vector(tree, "DOT_PRODUCT", delta, delta)
    reference2 = _vector(tree, "DOT_PRODUCT", reference, reference)
    compensation = _scalar(
        tree, "DIVIDE", distance2, _scalar(tree, "MAXIMUM", reference2, 0.0001)
    )
    normalized = _scalar(
        tree, "MULTIPLY", gray.outputs[0], compensation, "distance compensated response"
    )
    response = _range(
        tree,
        normalized,
        settings["low"],
        settings["high"],
        "calibrated combined light response",
    )
    normal = geometry.outputs["Normal"]
    if role == "face":
        normal = _world(
            tree,
            helpers["forward"],
            helpers["origin"],
            "posed face form normal",
        )
    no_l = _vector(tree, "DOT_PRODUCT", normal, direction, "form normal dot key")
    form = _range(
        tree, no_l, settings["form_low"], settings["form_high"], "geometric form"
    )
    if role == "face":
        floor = settings["face_form_floor"]
        form = _scalar(
            tree,
            "ADD",
            floor,
            _scalar(tree, "MULTIPLY", form, 1 - floor),
            "soft face form before occlusion",
        )
    factor = _scalar(tree, "MULTIPLY", form, response, "form times actual response")
    lighting_switch = _value(tree, 1, "enable single lighting palette")
    factor = _scalar(
        tree,
        "ADD",
        1,
        _scalar(
            tree, "MULTIPLY", lighting_switch, _scalar(tree, "SUBTRACT", factor, 1)
        ),
        "lighting bypass",
    )
    palette = _node(tree, "ShaderNodeValToRGB", "single material palette")
    palette.color_ramp.interpolation = "EASE"
    for item, position, color in zip(
        palette.color_ramp.elements, (0.24, 0.80), spec["palettes"][role]
    ):
        item.position, item.color = position, color
    tree.links.new(factor, palette.inputs[0])
    return palette.outputs[0], response, direction


def _hair(tree, geometry, helpers, direction, response, spec):
    settings = spec["hair"]
    normal = geometry.outputs["Normal"]
    up = _world(tree, helpers["up"], helpers["origin"], "posed hair up")
    projection = _vector(
        tree, "SCALE", normal, _vector(tree, "DOT_PRODUCT", normal, up)
    )
    tangent = _vector(tree, "NORMALIZE", _vector(tree, "SUBTRACT", up, projection))
    half = _vector(
        tree, "NORMALIZE", _vector(tree, "ADD", geometry.outputs["Incoming"], direction)
    )
    th = _vector(tree, "DOT_PRODUCT", tangent, half)
    q = _scalar(
        tree,
        "MAXIMUM",
        _scalar(tree, "SUBTRACT", 1, _scalar(tree, "MULTIPLY", th, th)),
        0,
    )
    band = _scalar(tree, "POWER", q, settings["exponent"], "directional hair band")
    gate = _scalar(
        tree,
        "ADD",
        settings["shadow_retention"],
        _scalar(tree, "MULTIPLY", response, 1 - settings["shadow_retention"]),
    )
    amount = _scalar(
        tree,
        "MULTIPLY",
        band,
        _scalar(
            tree,
            "MULTIPLY",
            gate,
            _value(tree, settings["strength"], "hair band strength"),
        ),
        "single gated hair highlight",
    )
    return _vector(
        tree, "SCALE", tuple(settings["color"]), amount, "hair highlight RGB"
    )


def _rim(tree, geometry, helpers, role, spec):
    settings = spec["rim"]
    direction = _world(tree, helpers["rim"], helpers["origin"], "actual rim direction")
    facing = _vector(
        tree, "DOT_PRODUCT", geometry.outputs["Normal"], geometry.outputs["Incoming"]
    )
    edge = _scalar(
        tree,
        "MAXIMUM",
        _scalar(tree, "SUBTRACT", 1, _scalar(tree, "ABSOLUTE", facing)),
        0,
    )
    edge = _scalar(tree, "POWER", edge, settings["power"])
    lit = _scalar(
        tree,
        "MAXIMUM",
        _vector(tree, "DOT_PRODUCT", geometry.outputs["Normal"], direction),
        0,
    )
    strength = (
        settings["hair_strength"]
        if role == "hair"
        else settings["skin_strength"]
        if role in {"face", "skin"}
        else settings["body_strength"]
    )
    amount = _scalar(
        tree,
        "MULTIPLY",
        edge,
        _scalar(tree, "MULTIPLY", lit, _value(tree, strength, "rim strength")),
        "narrow lit-side rim",
    )
    return _vector(tree, "SCALE", tuple(settings["color"]), amount, "rim RGB")


def _physical(tree, color, role, base, material_name, spec):
    settings = spec["physical"][role]
    if not settings["mix"]:
        return None, 0, None
    item = _node(tree, "ShaderNodeBsdfPrincipled", "material-specific physical closure")
    tree.links.new(color, item.inputs["Base Color"])
    item.inputs["Roughness"].default_value = settings["roughness"]
    item.inputs["Metallic"].default_value = settings.get("metallic", 0)
    item.inputs["Specular IOR Level"].default_value = settings.get("specular", 0.3)
    item.inputs["Sheen Weight"].default_value = settings.get("sheen", 0)
    item.inputs["Sheen Roughness"].default_value = 0.60
    item.inputs["Coat Weight"].default_value = settings.get("coat", 0)
    mix = _value(tree, settings["mix"], "physical closure mix")
    mask_report = None
    if material_name in spec["gold_partition"]["materials"]:
        mask = _hsv(
            tree, base, spec["gold_partition"]["mask"], "gold material partition"
        )
        metal = spec["gold_partition"]
        _plug(
            tree,
            _scalar(tree, "MULTIPLY", mask, metal["metallic"]),
            item.inputs["Metallic"],
        )
        rough = _scalar(
            tree,
            "ADD",
            settings["roughness"],
            _scalar(tree, "MULTIPLY", mask, metal["roughness"] - settings["roughness"]),
        )
        tree.links.new(rough, item.inputs["Roughness"])
        mix = _scalar(
            tree,
            "ADD",
            mix,
            _scalar(tree, "MULTIPLY", mask, metal["mix"] - settings["mix"]),
            "gold versus cloth closure mix",
        )
        mask_report = (
            "base-texture HSV artistic gold partition; not recovered metallic data"
        )
    return item.outputs[0], mix, mask_report


def _fallback(material, spec):
    base = material.node_tree.nodes.get("mmd_base_tex")
    if not base:
        raise ValueError("Ikhor face must retain the original MMD base texture node")
    if base.image and all(base.image.size):
        return None
    settings = spec["face_fallback"]
    path = Path(settings["path"])
    if not path.is_file():
        raise FileNotFoundError(path)
    before = base.image.filepath if base.image else None
    image = bpy.data.images.load(str(path), check_existing=True)
    if image.colorspace_settings.name != "sRGB":
        raise ValueError("Expected supplied Ikhor original Face Diffuse in sRGB")
    base.image = image
    return {
        "missing_original": before,
        "replacement": str(path),
        "image": image.name,
        "semantics": "same-character supplied original diffuse fallback; not restored edited y1.png",
        "UV_check": settings["uv_evidence"],
    }


def apply_ikhor_materials(scene, arm, spec):
    """Return real mappings/limits; install Ikhor-only shader nodes in memory."""
    pmx = Path(spec["source_pmx"])
    if hashlib.sha256(pmx.read_bytes()).hexdigest() != spec["source_pmx_sha256"]:
        raise ValueError("Unexpected Ikhor source PMX SHA256")
    if arm.type != "ARMATURE":
        raise TypeError("An explicit Ikhor armature is required")
    helpers = {key: scene.objects[name] for key, name in spec["helpers"].items()}
    materials = {}
    for obj in scene.objects:
        if obj.type == "MESH" and any(
            m.type == "ARMATURE" and m.object == arm for m in obj.modifiers
        ):
            for material in obj.data.materials:
                if material:
                    materials[material.name] = material
    report = {
        "id": spec["id"],
        "source_pmx": str(pmx),
        "materials": [],
        "skipped": [],
        "face_fallback": None,
        "SDF": "not present; posed head-normal form and actual key-facing combined response approximation",
        "limits": spec["limits"],
        "saved": False,
        "rendered": False,
        "physics_changed": False,
    }
    for material in materials.values():
        name = material.get("source_mmd_material_name", material.name)
        role = spec["material_roles"].get(name)
        if role is None:
            report["skipped"].append(
                {
                    "material": material.name,
                    "reason": "not one of the 26 audited source materials",
                }
            )
            continue
        tree = material.node_tree
        source = tree.nodes.get("mmd_shader") if tree else None
        if (
            not source
            or not source.outputs.get("Color")
            or not source.outputs.get("Alpha")
        ):
            raise ValueError(
                "Ikhor material needs actual MMDShaderDev Color/Alpha: " + material.name
            )
        if any(n.name.startswith(PREFIX) for n in tree.nodes):
            raise ValueError(
                "Refusing to stack Ikhor shader migration: " + material.name
            )
        if role == "face":
            report["face_fallback"] = _fallback(material, spec)
        base = tree.nodes.get("mmd_base_tex")
        original = source.outputs["Color"]
        geometry = _node(tree, "ShaderNodeNewGeometry", "geometry")
        feature = role in {"ink", "eye_white", "iris", "eye_layer", "mouth", "hidden"}
        hair_rgb, rim_rgb, motif_rgb = (0, 0, 0), (0, 0, 0), (0, 0, 0)
        if feature:
            shaded = _mix(
                tree,
                original,
                (spec["feature_gain"].get(role, 1),) * 3 + (1,),
                label="preserved feature color",
            )
        else:
            palette, response, direction = _lighting(
                tree, geometry, role, helpers, spec
            )
            shaded = _mix(tree, original, palette, label="source times single palette")
            ao = _node(tree, "ShaderNodeAmbientOcclusion", "single short contact AO")
            ao.samples = 16
            ao.inputs["Distance"].default_value = spec["ao"][
                "face_distance" if role == "face" else "distance"
            ]
            amount = spec["ao"]["face_strength" if role == "face" else "strength"]
            contact = _scalar(
                tree,
                "SUBTRACT",
                1,
                _scalar(
                    tree,
                    "MULTIPLY",
                    _value(tree, amount, "contact AO strength"),
                    _scalar(tree, "SUBTRACT", 1, ao.outputs["AO"]),
                ),
                "single bounded contact factor",
            )
            shaded = _mix(tree, shaded, contact, label="one contact application")
            if role == "hair":
                hair_rgb = _hair(tree, geometry, helpers, direction, response, spec)
                shaded = _vector(
                    tree, "ADD", shaded, hair_rgb, "one hair highlight application"
                )
            rim_rgb = _rim(tree, geometry, helpers, role, spec)
            shaded = _vector(
                tree, "ADD", shaded, rim_rgb, "unclamped narrow rim application"
            )
            for key, settings in spec["local_emission"].items():
                if name not in settings["materials"]:
                    continue
                mask = _hsv(tree, base, settings["mask"], key)
                amount = _scalar(
                    tree,
                    "MULTIPLY",
                    mask,
                    _value(tree, settings["strength"], key + " HDR strength"),
                )
                rgb = _vector(
                    tree, "SCALE", tuple(settings["color"]), amount, key + " HDR RGB"
                )
                motif_rgb = (
                    rgb
                    if isinstance(motif_rgb, tuple)
                    else _vector(tree, "ADD", motif_rgb, rgb)
                )
                shaded = _vector(
                    tree, "ADD", shaded, rgb, key + " unclamped HDR application"
                )
        emission = _node(tree, "ShaderNodeEmission", "controlled NPR surface")
        _plug(tree, shaded, emission.inputs["Color"])
        closure = emission.outputs[0]
        physical, physical_mix, gold_report = _physical(
            tree, original, role, base, name, spec
        )
        if physical:
            mixed = _node(
                tree, "ShaderNodeMixShader", "toon and material physical closure"
            )
            _plug(tree, physical_mix, mixed.inputs[0])
            tree.links.new(closure, mixed.inputs[1])
            tree.links.new(physical, mixed.inputs[2])
            closure = mixed.outputs[0]
        transparent = _node(
            tree, "ShaderNodeBsdfTransparent", "original animated PMX transparency"
        )
        alpha = _node(tree, "ShaderNodeMixShader", "preserve original MMD Alpha")
        tree.links.new(source.outputs["Alpha"], alpha.inputs[0])
        tree.links.new(transparent.outputs[0], alpha.inputs[1])
        tree.links.new(closure, alpha.inputs[2])
        output = next(
            n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
        )
        previous = [
            (link.from_node.name, link.from_socket.name)
            for link in output.inputs["Surface"].links
        ]
        tree.links.new(alpha.outputs[0], output.inputs["Surface"])
        halo = _vector(tree, "ADD", hair_rgb, rim_rgb, "hair and rim AOV source")
        emissive = _vector(tree, "ADD", motif_rgb, rim_rgb, "selective HDR AOV source")
        for aov_name, color_signal in (
            ("StageArtRim", halo),
            ("BoldWeddingEmission", emissive),
        ):
            aov = _node(tree, "ShaderNodeOutputAOV", aov_name)
            aov.aov_name = aov_name
            tree.links.new(
                _vector(
                    tree,
                    "SCALE",
                    color_signal,
                    source.outputs["Alpha"],
                    aov_name + " respects Alpha",
                ),
                aov.inputs["Color"],
            )
        actor = _node(tree, "ShaderNodeOutputAOV", "Alpha respecting actor coverage")
        actor.aov_name = "ReferenceDuetActor"
        tree.links.new(source.outputs["Alpha"], actor.inputs["Value"])
        material["performer_id"], material["ikhor_material_role"] = "ikhor", role
        material["ikhor_character_revision"] = spec["id"]
        report["materials"].append(
            {
                "material": material.name,
                "source_name": name,
                "role": role,
                "base_image": base.image.name if base and base.image else None,
                "source_color": source.name + ".Color",
                "source_alpha": source.name + ".Alpha",
                "old_surface": previous,
                "gold_partition": gold_report,
                "sphere_inputs_retained": True,
                "PMX_edge_unchanged": True,
            }
        )
    if len(report["materials"]) != len(spec["material_roles"]):
        raise ValueError(
            "Expected all 26 mapped Ikhor materials, got "
            + str(len(report["materials"]))
        )
    for layer in scene.view_layers:
        for name, kind in AOVS.items():
            aov = layer.aovs.get(name)
            if aov and aov.type != kind:
                raise ValueError("Unexpected existing AOV type: " + name)
            if not aov:
                aov = layer.aovs.add()
                aov.name, aov.type = name, kind
        layer.update_render_passes()
    scene["ikhor_character_revision"] = spec["id"]
    return report
