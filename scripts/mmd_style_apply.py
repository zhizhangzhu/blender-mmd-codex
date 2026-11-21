"""Apply a versioned NPR style to the validated local tutorial scene.

Uses the scene's actual MMD Color/Alpha graph. Does not modify animation,
physics, preferences or source files. Refuses a missing/incompatible graph.
"""

import bpy


def apply_render_style(scene, recipe):
    settings = recipe["render"]
    changed = []
    for mat in bpy.data.materials:
        category = mat.get("look_category")
        if not category:
            continue
        tree = mat.node_tree
        ramp = tree.nodes.get("Look v3 | Soft toon bands")
        if ramp is None:
            raise ValueError("Expected validated NPR graph: " + mat.name)
        colors = settings["palette"][category]
        ramp.color_ramp.interpolation = settings["ramp_interpolation"]
        for elem, position, color in zip(
            ramp.color_ramp.elements, settings["ramp_positions"], colors
        ):
            elem.position = position
            elem.color = (*color, 1)
        chroma = tree.nodes["Look v3 | Per material chroma"]
        chroma.inputs["Saturation"].default_value = settings["saturation"].get(
            category, 1
        )
        chroma.inputs["Value"].default_value = settings["value"].get(category, 1)
        edge = bpy.data.materials.get("mmd_edge." + mat.name)
        if edge and edge.node_tree:
            # Existing MMD edge graph preserves model vertex/material weights.
            for n in edge.node_tree.nodes:
                if n.name == "mmd_edge_preview" and "Color" in n.inputs:
                    n.inputs["Color"].default_value = (*settings["edge_rgb"], 1)
        changed.append(mat.name)
    if not changed:
        raise ValueError("No compatible MMD materials in source scene")
    for obj in scene.objects:
        if obj.type == "MESH":
            mod = obj.modifiers.get("mmd_edge_preview")
            if mod:
                # Absolute baseline, not repeated multiplication on reruns.
                mod.thickness = 0.0336 * settings["edge_width_scale"]
    lights = []
    for name, data in settings["lights"].items():
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "LIGHT":
            raise ValueError("Missing style light: " + name)
        obj.data.color = data["color"]
        obj.data.energy = data["energy"]
        lights.append(name)
    tree = scene.compositing_node_group
    glare = next(n for n in tree.nodes if n.type == "GLARE")
    for key, value in settings["bloom"].items():
        glare.inputs[key].default_value = value
    scene.camera.data.lens = recipe["camera"]["lens_mm"]
    scene.camera.data.dof.use_dof = recipe["camera"]["dof"]
    scene.camera.data.dof.aperture_fstop = recipe["camera"]["fstop"]
    scene["style_package_id"] = recipe["id"]
    scene["style_reference_status"] = (
        "reference-inspired; not original author parameters"
    )
    return {
        "materials": changed,
        "lights": lights,
        "render_component": recipe["render_path"],
        "engine": scene.render.engine,
        "view_transform": scene.view_settings.view_transform,
        "camera_dof": scene.camera.data.dof.use_dof,
        "camera_fstop": scene.camera.data.dof.aperture_fstop,
    }
