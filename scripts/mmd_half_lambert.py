"""A named Half-Lambert response followed by per-material artistic gradients."""


def apply_half_lambert(materials, settings):
    changed = []
    for mat in materials:
        category = mat.get("look_category")
        if category not in settings["palette"]:
            continue
        tree = mat.node_tree
        dot = tree.nodes.get("Look v3 | Key direction")
        ramp = tree.nodes.get("Look v3 | Soft toon bands")
        if not dot or not ramp:
            raise ValueError("Expected validated normal/light graph: " + mat.name)
        remap = tree.nodes.get("Quality | Half Lambert remap") or tree.nodes.new(
            "ShaderNodeMath"
        )
        remap.name = "Quality | Half Lambert remap"
        remap.operation = "MULTIPLY_ADD"
        remap.use_clamp = True
        remap.inputs[1].default_value = 0.5
        remap.inputs[2].default_value = 0.5
        tree.links.new(dot.outputs["Value"], remap.inputs[0])
        power = tree.nodes.get("Quality | Half Lambert exponent") or tree.nodes.new(
            "ShaderNodeMath"
        )
        power.name = "Quality | Half Lambert exponent"
        power.operation = "POWER"
        power.inputs[1].default_value = settings["exponent"]
        tree.links.new(remap.outputs[0], power.inputs[0])
        tree.links.new(power.outputs[0], ramp.inputs["Fac"])
        cr = ramp.color_ramp
        while len(cr.elements) > 2:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = settings["positions"][0]
        cr.elements[1].position = settings["positions"][-1]
        cr.elements.new(settings["positions"][1])
        cr.interpolation = settings["interpolation"]
        for elem, color in zip(cr.elements, settings["palette"][category]):
            elem.color = (*color, 1)
        mat["quality_light_response"] = (
            "pow(clamp(0.5*NdotL+0.5), exponent) -> three-region gradient"
        )
        changed.append(mat.name)
    if not changed:
        raise ValueError("No compatible NPR materials")
    return {"materials": changed, "settings": settings, "light_driver_preserved": True}
