"""Relight the selected hall and create a controlled SDR toon finish.

Keep portable dance/physics and authored camera. Emission is already present:
this changes its color-managed presentation rather than making actors lamps.
"""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import area


def math_node(tree, operation, first, second=None, label=None):
    node = tree.nodes.new("ShaderNodeMath")
    node.operation = operation
    node.label = label or operation
    for socket, value in zip(node.inputs, [first, second]):
        if value is None:
            continue
        if hasattr(value, "is_output"):
            tree.links.new(value, socket)
        else:
            socket.default_value = value
    return node.outputs[0]


def compositor(scene, settings):
    aov_name = "ClearLightActor"
    aov = scene.view_layers[0].aovs.add()
    aov.name, aov.type = aov_name, "VALUE"
    for material in bpy.data.materials:
        if material.node_tree and material.get("performer_id"):
            output = material.node_tree.nodes.new("ShaderNodeOutputAOV")
            output.aov_name = aov_name
            output.inputs["Value"].default_value = 1.0
    scene.view_layers[0].update_render_passes()
    tree = bpy.data.node_groups.new(
        "Clear light | SDR shoulder and restrained glow", "CompositorNodeTree"
    )
    scene.compositing_node_group = tree
    tree.interface.new_socket(
        name="Image", in_out="OUTPUT", socket_type="NodeSocketColor"
    )
    layers = tree.nodes.new("CompositorNodeRLayers")
    layers.scene = scene
    channels = tree.nodes.new("CompositorNodeSeparateColor")
    channels.mode = "RGB"
    tree.links.new(layers.outputs["Image"], channels.inputs[0])
    maximum = math_node(
        tree,
        "MAXIMUM",
        math_node(tree, "MAXIMUM", channels.outputs[0], channels.outputs[1]),
        channels.outputs[2],
    )
    background_max = math_node(
        tree,
        "POWER",
        math_node(tree, "MAXIMUM", maximum, 0),
        settings["background_mid_gamma"],
    )
    background_weight = math_node(tree, "SUBTRACT", 1, layers.outputs[aov_name])
    corrected_max = math_node(
        tree,
        "ADD",
        maximum,
        math_node(
            tree,
            "MULTIPLY",
            background_weight,
            math_node(tree, "SUBTRACT", background_max, maximum),
        ),
    )
    knee, headroom = settings["shoulder"]["knee"], settings["shoulder"]["headroom"]
    distance = math_node(
        tree, "MAXIMUM", math_node(tree, "SUBTRACT", corrected_max, knee), 0
    )
    exponent = math_node(tree, "DIVIDE", distance, -headroom)
    exp = math_node(tree, "POWER", 2.718281828459045, exponent)
    mapped = math_node(
        tree,
        "ADD",
        knee,
        math_node(tree, "MULTIPLY", math_node(tree, "SUBTRACT", 1, exp), headroom),
    )
    mapped = math_node(tree, "MINIMUM", corrected_max, mapped)
    scale = math_node(
        tree,
        "DIVIDE",
        mapped,
        math_node(tree, "MAXIMUM", maximum, 0.000001),
        "preserve hue; retain zero black",
    )
    combine = tree.nodes.new("CompositorNodeCombineColor")
    combine.mode = "RGB"
    for i in range(3):
        tree.links.new(
            math_node(tree, "MULTIPLY", channels.outputs[i], scale), combine.inputs[i]
        )
    tree.links.new(channels.outputs[3], combine.inputs[3])
    saturation = tree.nodes.new("CompositorNodeHueSat")
    saturation.inputs["Saturation"].default_value = settings["saturation"]
    tree.links.new(combine.outputs[0], saturation.inputs["Image"])
    glow = tree.nodes.new("CompositorNodeGlare")
    glow.inputs["Type"].default_value = "Fog Glow"
    glow.inputs["Quality"].default_value = "High"
    glow.inputs["Threshold"].default_value = settings["bloom"]["threshold"]
    glow.inputs["Strength"].default_value = settings["bloom"]["strength"]
    glow.inputs["Size"].default_value = settings["bloom"]["size"]
    tree.links.new(saturation.outputs[0], glow.inputs["Image"])
    output = tree.nodes.new("NodeGroupOutput")
    tree.links.new(glow.outputs["Image"], output.inputs[0])


def relight(scene, settings):
    disabled = []
    for obj in scene.objects:
        if obj.type == "LIGHT" and obj.data.type != "POINT":
            obj.hide_render = True
            disabled.append(obj.name)
    for spec in settings["lights"]:
        light = area(
            "Clear light | " + spec["name"],
            spec["location"],
            spec["target"],
            spec["watts"],
            spec["color"],
            spec["size"],
        )
        light.data.shadow_maximum_resolution = 0.02
        light.data.use_shadow = spec.get("shadow", True)
    world = scene.world.node_tree
    background = next(node for node in world.nodes if node.type == "BACKGROUND")
    background.inputs["Strength"].default_value = settings["world_strength"]
    sky = background.inputs["Color"].links[0].from_node
    assert sky.type == "VALTORGB"
    for item, value in zip(sky.color_ramp.elements, settings["sky_colors"]):
        item.color = value
    key_direction = Vector(settings["lights"][0]["location"]) - Vector((0, 0, 1.3))
    key_direction.normalize()
    old_directions = [
        Vector((-0.55, -0.68, 0.49)).normalized(),
        Vector((-0.35, -0.65, 0.72)).normalized(),
    ]
    for material in bpy.data.materials:
        if not material.node_tree:
            continue
        tree = material.node_tree
        if material.get("performer_id"):
            for node in tree.nodes:
                if node.type == "VECT_MATH":
                    for socket in node.inputs:
                        if socket.type == "VECTOR" and not socket.is_linked:
                            direction = Vector(socket.default_value)
                            if any(
                                (direction - old).length < 0.001
                                for old in old_directions
                            ):
                                socket.default_value = key_direction
        if material.get("stage_id"):
            tint = tree.nodes.get("Stage | winter stone palette")
            if tint:
                tint.inputs[2].default_value = (*settings["architecture_tint"], 1)
            mask = tree.nodes.get("Duet | authored MatCap mask")
            if mask:
                mask.inputs[1].default_value = settings["matcap_gain"]
            for node in tree.nodes:
                if node.type == "AMBIENT_OCCLUSION":
                    node.inputs["Distance"].default_value = 0.18
                    for link in node.outputs["AO"].links:
                        link.to_node.inputs[0].default_value = 0.10
        if material.get("performer_id") == "aether":
            kind = material.get("aether_surface")
            if kind in {"skin", "face"}:
                tree.nodes["Aether v2 | texture white balance"].inputs[
                    "Saturation"
                ].default_value = 0.88
                tree.nodes["Aether v2 | skin balance"].inputs[2].default_value = (
                    1,
                    1.01,
                    1.02,
                    1,
                )
            if kind == "hair":
                tree.nodes["Aether v2 | texture white balance"].inputs[
                    "Saturation"
                ].default_value = 0.98
    hidden = [
        (o, o.hide_render)
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id")
    ]
    for obj, _previous in hidden:
        obj.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    probes = [o for o in scene.objects if o.type == "LIGHT_PROBE"]
    for obj in probes:
        obj.select_set(True)
    volume = next(o for o in probes if o.data.type == "VOLUME")
    bpy.context.view_layer.objects.active = volume
    bpy.context.view_layer.update()
    assert bpy.ops.object.lightprobe_cache_bake(subset="SELECTED") == {"FINISHED"}
    for obj, previous in hidden:
        obj.hide_render = previous
    return disabled


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    settings = json.loads(args.preset.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    source = bpy.data.filepath
    assert scene.rigidbody_world is None and not scene.get("clear_light_revision")
    disabled = relight(scene, settings)
    compositor(scene, settings)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.eevee.shadow_pool_size = "1024"
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_sequencer = False
    scene["clear_light_revision"] = settings["id"]
    scene.frame_set(4140)
    bpy.ops.file.pack_all()
    destination = args.output_dir / "Franken_Duet_Clear_Light.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    for frame in [4200, 4420]:
        scene.frame_set(frame)
        scene.render.filepath = str(args.output_dir / f"revised-{frame}.png")
        bpy.ops.render.render(write_still=True)
    tree = scene.compositing_node_group
    output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    original_socket = output.inputs[0].links[0].from_socket
    layers = next(n for n in tree.nodes if n.type == "R_LAYERS")
    tree.links.new(layers.outputs["ClearLightActor"], output.inputs[0])
    scene.frame_set(4200)
    scene.render.filepath = str(args.output_dir / "actor-mask-4200.png")
    bpy.ops.render.render(write_still=True)
    tree.links.new(original_socket, output.inputs[0])
    (args.output_dir / "revision-report.json").write_text(
        json.dumps(
            {
                "source": source,
                "project": str(destination),
                "preset": settings,
                "disabled_old_area_lights": disabled,
                "emission": "Existing artist-controlled actor NPR emission retained; not used as architectural illumination",
                "camera_motion_changed": False,
                "physics_changed": False,
                "static_gi_rebaked_without_actors": True,
                "status": "Relit study; five-second render and dynamic verification pending",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("CLEAR_LIGHT_REVISION_SAVED", flush=True)


if __name__ == "__main__":
    main()
