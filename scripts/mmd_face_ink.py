"""Selective facial strokes; source texture/UV/alpha and expression stay intact.

The mouth ROI and image identity are Aksiniya-specific art controls. This is
not automatic landmark detection or a universal nose/mouth outline filter.
"""

import bpy


def node(tree, kind, name):
    key = "Face ink | " + name
    result = tree.nodes.get(key) or tree.nodes.new(kind)
    result.name = key
    return result


def math(tree, op, name, a, b):
    result = node(tree, "ShaderNodeMath", name)
    result.operation = op
    for i, value in enumerate((a, b)):
        if isinstance(value, (int, float)):
            result.inputs[i].default_value = value
        else:
            tree.links.new(value, result.inputs[i])
    return result.outputs[0]


def mix_surface(mat, name, factor, color, multiply=False):
    tree = mat.node_tree
    surface = tree.nodes.get("Look v3 | NPR surface")
    if not surface:
        raise ValueError("Expected NPR surface: " + mat.name)
    old = tree.nodes.get("Face ink | " + name)
    original = (
        old.inputs[1].links[0].from_socket
        if old
        else surface.inputs["Color"].links[0].from_socket
    )
    result = node(tree, "ShaderNodeMixRGB", name)
    result.blend_type = "MULTIPLY" if multiply else "MIX"
    if isinstance(factor, (int, float)):
        result.inputs[0].default_value = factor
    else:
        tree.links.new(factor, result.inputs[0])
    tree.links.new(original, result.inputs[1])
    result.inputs[2].default_value = (*color, 1)
    tree.links.new(result.outputs[0], surface.inputs["Color"])


def apply_face_features(settings):
    report = {"ink_materials": [], "mouth": None}
    for name in settings["ink_materials"]:
        mat = bpy.data.materials.get(name)
        if not mat or mat.get("look_category") != "ink":
            raise ValueError("Missing dedicated brow/lash material: " + name)
        gain = settings["ink_gain"]
        mix_surface(mat, "Brow and lash contrast", 1, [gain] * 3, True)
        report["ink_materials"].append(name)
    spec = settings["mouth_crease"]
    mat = bpy.data.materials.get(spec["material"])
    if not mat:
        raise ValueError("Missing mouth crease surface")
    tree = mat.node_tree
    source = tree.nodes.get("mmd_base_tex")
    if not source or not source.image or source.image.name != spec["source_image"]:
        raise ValueError("Mouth UV controls require the reviewed Aksiniya face atlas")
    split = node(tree, "ShaderNodeSeparateColor", "Source channels")
    split.mode = "RGB"
    tree.links.new(source.outputs["Color"], split.inputs[0])
    red = math(tree, "SUBTRACT", "Red crease", split.outputs[0], split.outputs[1])
    remap = node(tree, "ShaderNodeMapRange", "Crease contrast")
    remap.clamp = True
    tree.links.new(red, remap.inputs["Value"])
    remap.inputs["From Min"].default_value = spec["red_difference_linear"][0]
    remap.inputs["From Max"].default_value = spec["red_difference_linear"][1]
    uv = node(tree, "ShaderNodeTexCoord", "Face UV")
    axis = node(tree, "ShaderNodeSeparateXYZ", "UV components")
    if source.inputs["Vector"].is_linked:
        tree.links.new(source.inputs["Vector"].links[0].from_socket, axis.inputs[0])
    else:
        tree.links.new(uv.outputs["UV"], axis.inputs[0])
    mask = remap.outputs[0]
    u0, v0, u1, v1 = spec["uv_bounds"]
    for label, value, op, bound in [
        ("U min", axis.outputs[0], "GREATER_THAN", u0),
        ("U max", axis.outputs[0], "LESS_THAN", u1),
        ("V min", axis.outputs[1], "GREATER_THAN", v0),
        ("V max", axis.outputs[1], "LESS_THAN", v1),
    ]:
        test = math(tree, op, label, value, bound)
        mask = math(tree, "MULTIPLY", label + " gate", mask, test)
    mask = math(tree, "MULTIPLY", "Crease strength", mask, spec["strength"])
    mix_surface(mat, "Mouth crease", mask, spec["color_linear"])
    report["mouth"] = {**spec, "source_texture_preserved": True}
    report["nose"] = "Existing geometry silhouette only; no invented frontal stroke"
    return report
