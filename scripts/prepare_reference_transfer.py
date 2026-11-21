"""Port bounded NPR/light/material principles into a new Character Layers copy."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrate_light_space import transform_variable, world_vector
from mmd_hesperides_stage import aim
from prepare_character_layers import role
from transfer_material_response import apply_material_response
from verify_duet_integration import snapshot

PREFIX = "Reference transfer | "
FRAMES = [1, 2100, 4140, 4200, 4250, 4290, 4439, 8400, 11899]


def node(tree, kind, label):
    value = tree.nodes.new(kind)
    value.name = PREFIX + label
    value.label = label
    return value


def plug(tree, value, target):
    if hasattr(value, "is_output"):
        tree.links.new(value, target)
    else:
        target.default_value = value


def scalar(tree, operation, a, b=None, label=""):
    value = node(tree, "ShaderNodeMath", label or operation)
    value.operation = operation
    plug(tree, a, value.inputs[0])
    if b is not None:
        plug(tree, b, value.inputs[1])
    return value.outputs[0]


def vector(tree, operation, a, b=None, label=""):
    value = node(tree, "ShaderNodeVectorMath", label or operation)
    value.operation = operation
    plug(tree, a, value.inputs[0])
    if b is not None:
        plug(tree, b, value.inputs[1])
    return (
        value.outputs["Value"]
        if operation in {"DOT_PRODUCT", "DISTANCE", "LENGTH"}
        else value.outputs[0]
    )


def mix(tree, a, b, factor=1, blend="MULTIPLY", label=""):
    value = node(tree, "ShaderNodeMixRGB", label or blend)
    value.blend_type = blend
    for socket, source in zip(value.inputs, [factor, a, b]):
        plug(tree, source, socket)
    return value.outputs[0]


def enable(tree, label, value=1):
    result = node(tree, "ShaderNodeValue", label)
    result.outputs[0].default_value = value
    return result.outputs[0]


def position(tree, obj, label):
    result = node(tree, "ShaderNodeCombineXYZ", label)
    for index, socket in enumerate(result.inputs):
        driver = socket.driver_add("default_value").driver
        driver.type = "SCRIPTED"
        transform_variable(driver, "p", obj, index)
        driver.expression = "p"
    return result.outputs[0]


def remap(tree, value, low, high, label):
    result = node(tree, "ShaderNodeMapRange", label)
    result.clamp = True
    result.interpolation_type = "SMOOTHSTEP"
    tree.links.new(value, result.inputs["Value"])
    result.inputs["From Min"].default_value = low
    result.inputs["From Max"].default_value = high
    return result.outputs[0]


def character_design(scene, config):
    records = []
    for material in bpy.data.materials:
        if not material.get("character_layer_revision") or not material.node_tree:
            continue
        kind = role(material)
        if kind == "features":
            continue
        tree = material.node_tree
        assert not any(n.name.startswith(PREFIX) for n in tree.nodes)
        actor = material["performer_id"]
        geometry = node(tree, "ShaderNodeNewGeometry", "surface geometry")
        key = scene.objects[f"Reference duet | {actor} | key"]
        key_position = position(tree, key, "actual key position")
        delta = vector(
            tree,
            "SUBTRACT",
            key_position,
            geometry.outputs["Position"],
            "surface to key",
        )
        direction = vector(tree, "NORMALIZE", delta, label="key facing normal")
        probe = node(tree, "ShaderNodeBsdfDiffuse", "key facing diffuse probe")
        probe.inputs["Color"].default_value = (1, 1, 1, 1)
        tree.links.new(direction, probe.inputs["Normal"])
        rgb = node(tree, "ShaderNodeShaderToRGB", "key facing illumination")
        tree.links.new(probe.outputs[0], rgb.inputs[0])
        bw = node(tree, "ShaderNodeRGBToBW", "key facing luminance")
        tree.links.new(rgb.outputs[0], bw.inputs[0])
        origin = position(
            tree, scene.objects[f"Quality | {actor} | head origin"], "head position"
        )
        reference_delta = vector(tree, "SUBTRACT", key_position, origin)
        distance2 = vector(
            tree, "DOT_PRODUCT", delta, delta, "surface distance squared"
        )
        reference2 = vector(
            tree,
            "DOT_PRODUCT",
            reference_delta,
            reference_delta,
            "head distance squared",
        )
        compensation = scalar(
            tree, "DIVIDE", distance2, scalar(tree, "MAXIMUM", reference2, 0.0001)
        )
        normalized = scalar(
            tree,
            "MULTIPLY",
            bw.outputs[0],
            compensation,
            "distance compensated illumination",
        )
        # This is explicitly a calibrated combined response, NOT isolated visibility.
        response = remap(
            tree,
            normalized,
            config["shadow_response"]["low"],
            config["shadow_response"]["high"],
            "key facing response",
        )
        no_l = vector(
            tree,
            "DOT_PRODUCT",
            geometry.outputs["Normal"],
            direction,
            "geometric form NoL",
        )
        form = remap(
            tree,
            no_l,
            config["shadow_response"]["form_low"],
            config["shadow_response"]["form_high"],
            "form bands",
        )
        if kind == "face":
            old_min = tree.nodes.get(
                "Character layers | SDF and native light combined once"
            )
            if old_min and old_min.inputs[1].is_linked:
                sdf = old_min.inputs[1].links[0].from_socket
                floor = config["shadow_response"]["face_form_floor"]
                form = scalar(
                    tree,
                    "ADD",
                    floor,
                    scalar(tree, "MULTIPLY", sdf, 1 - floor),
                    "soft face form before occlusion",
                )
        combined = scalar(
            tree, "MULTIPLY", form, response, "form times directional response"
        )
        palette = node(tree, "ShaderNodeValToRGB", "designed two color palette")
        palette.color_ramp.interpolation = "EASE"
        palette.color_ramp.elements[0].position = 0.30
        palette.color_ramp.elements[1].position = (
            0.82 if kind in {"face", "hair"} else 0.70
        )
        category = "gold_hair" if kind == "hair" and actor == "aether" else kind
        for element, rgba in zip(
            palette.color_ramp.elements, config["palettes"][category]
        ):
            element.color = rgba
        tree.links.new(combined, palette.inputs[0])
        multiply = tree.nodes["Character layers | base times one palette"]
        original = multiply.inputs[2].links[0].from_socket
        selected = mix(
            tree,
            original,
            palette.outputs[0],
            enable(tree, "enable designed shading"),
            "MIX",
            "shading bypass",
        )
        tree.links.new(selected, multiply.inputs[2])
        material["reference_transfer_revision"] = config["id"]
        records.append(
            {
                "material": material.name,
                "actor": actor,
                "role": kind,
                "face_uses_existing_sdf": kind == "face" and bool(old_min),
            }
        )
    assert len(records) > 30
    return records


def add_rims(scene, spec):
    changed = []
    for material in bpy.data.materials:
        if not material.get("reference_transfer_revision"):
            continue
        tree, actor, kind = material.node_tree, material["performer_id"], role(material)
        surface = tree.nodes.get(
            "Aether v2 | controlled toon surface"
        ) or tree.nodes.get("Look v3 | NPR surface")
        original = surface.inputs["Color"].links[0].from_socket
        geometry = tree.nodes[PREFIX + "surface geometry"]
        facing = scalar(
            tree,
            "ABSOLUTE",
            vector(
                tree,
                "DOT_PRODUCT",
                geometry.outputs["Normal"],
                geometry.outputs["Incoming"],
            ),
        )
        edge = scalar(tree, "POWER", scalar(tree, "SUBTRACT", 1, facing), spec["power"])
        rim_direction = world_vector(
            tree,
            scene.objects[f"Reference duet | {actor} | rim"],
            scene.objects[f"Quality | {actor} | head origin"],
            PREFIX + "rim direction",
        )
        illuminated_edge = scalar(
            tree,
            "MAXIMUM",
            vector(tree, "DOT_PRODUCT", geometry.outputs["Normal"], rim_direction),
            0,
        )
        strength = (
            spec["skin_strength"]
            if kind in {"face", "skin"}
            else spec["hair_strength"]
            if kind == "hair"
            else spec["body_strength"]
        )
        amount = scalar(
            tree, "MULTIPLY", edge, scalar(tree, "MULTIPLY", illuminated_edge, strength)
        )
        amount = scalar(
            tree,
            "MULTIPLY",
            amount,
            enable(tree, "enable artistic emissive rim"),
            "controlled rim amount",
        )
        rgba = spec["gold_color"] if actor == "aether" else spec["silver_color"]
        colored = mix(
            tree, original, rgba, amount, "SCREEN", "controlled emissive edge"
        )
        tree.links.new(colored, surface.inputs["Color"])
        aov = next(
            (
                n
                for n in tree.nodes
                if n.type == "OUTPUT_AOV" and n.aov_name == "StageArtRim"
            ),
            None,
        )
        if aov:
            old = (
                aov.inputs["Color"].links[0].from_socket
                if aov.inputs["Color"].is_linked
                else (0, 0, 0, 1)
            )
            tree.links.new(
                mix(
                    tree,
                    old,
                    mix(tree, rgba, amount),
                    blend="ADD",
                    label="rim and hair halo source",
                ),
                aov.inputs["Color"],
            )
        changed.append(material.name)
    return changed


def light_design(scene, spec):
    changes = []
    for actor in ("aksiniya", "aether"):
        for label in ("key", "fill", "rim"):
            obj = scene.objects[f"Reference duet | {actor} | {label}"]
            before = {
                key: getattr(obj.data, key)
                for key in ("energy", "diffuse_factor", "specular_factor", "size")
            }
            obj.data.energy = spec[label + "_watts"]
            if label == "key":
                obj.data.size = spec["key_size"]
                target = scene.objects[
                    f"Quality | {actor} | head origin"
                ].matrix_world.translation
                obj.location = target + Vector(
                    spec.get("key_offset", [-2.8, -3.6, 3.3])
                )
                aim(obj, target - Vector((0, 0, 0.15)))
            else:
                obj.data.diffuse_factor = 0
            obj.data.use_shadow = True
            changes.append(
                {
                    "name": obj.name,
                    "before": before,
                    "energy": obj.data.energy,
                    "diffuse_factor": obj.data.diffuse_factor,
                }
            )
        key = scene.objects[f"Reference duet | {actor} | key"]
        target = scene.objects[
            f"Quality | {actor} | head origin"
        ].matrix_world.translation
        light_data = bpy.data.lights.new(
            f"Reference duet | {actor} | reflection", "AREA"
        )
        light_data.energy = spec["reflection_watts"]
        light_data.shape = "RECTANGLE"
        light_data.size = spec["reflection_width"]
        light_data.size_y = spec["reflection_height"]
        light_data.color = (0.87, 0.93, 1)
        light_data.diffuse_factor = 0
        light_data.specular_factor = 1
        light_data.volume_factor = 0
        light = bpy.data.objects.new(light_data.name, light_data)
        scene.collection.objects.link(light)
        light.location = target + Vector((1.8, -2.4, 1.0))
        aim(light, target - Vector((0, 0, 0.4)))
        light.light_linking.receiver_collection = key.light_linking.receiver_collection
        changes.append(
            {"name": light.name, "specular_only": True, "watts": light_data.energy}
        )
    return changes


def stage_zone_grade(scene, spec):
    """Spatial post control of the foreground and side planting, actor-protected."""
    from stage_night_art_lab import mix as compositor_mix

    aov_name = "TransferStageZone"
    for layer in scene.view_layers:
        if not layer.aovs.get(aov_name):
            aov = layer.aovs.add()
            aov.name, aov.type = aov_name, "VALUE"
    count = 0
    for material in bpy.data.materials:
        tree = material.node_tree
        if not tree or material.get("performer_id"):
            continue
        if not any(
            n.type == "OUTPUT_MATERIAL" and n.inputs["Surface"].is_linked
            for n in tree.nodes
        ):
            continue
        geom = node(tree, "ShaderNodeNewGeometry", "grade world position")
        xyz = node(tree, "ShaderNodeSeparateXYZ", "grade position axes")
        tree.links.new(geom.outputs["Position"], xyz.inputs[0])
        side = remap(
            tree, scalar(tree, "ABSOLUTE", xyz.outputs["X"]), 1.3, 4.8, "grade sides"
        )
        front = scalar(
            tree,
            "SUBTRACT",
            1,
            remap(tree, xyz.outputs["Y"], -4, 0.5, "grade front falloff"),
        )
        low = scalar(
            tree,
            "SUBTRACT",
            1,
            remap(tree, xyz.outputs["Z"], 1.5, 3.5, "grade height falloff"),
        )
        zone = scalar(
            tree,
            "MULTIPLY",
            scalar(tree, "MAXIMUM", side, front),
            low,
            "foreground and side zone",
        )
        out = node(tree, "ShaderNodeOutputAOV", "stage spatial grade AOV")
        out.aov_name = aov_name
        tree.links.new(zone, out.inputs["Value"])
        count += 1
    bpy.context.view_layer.update()
    tree = scene.compositing_node_group
    output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    previous = output.inputs["Image"].links[0].from_socket
    render = next(
        n for n in tree.nodes if n.type == "R_LAYERS" and n.outputs.get(aov_name)
    )
    inverse = tree.nodes.new("ShaderNodeMath")
    inverse.name, inverse.operation = (
        PREFIX + "protect actor in stage grade",
        "SUBTRACT",
    )
    inverse.inputs[0].default_value = 1
    tree.links.new(render.outputs["ReferenceDuetActor"], inverse.inputs[1])
    zone = tree.nodes.new("ShaderNodeMath")
    zone.name, zone.operation = PREFIX + "stage-only spatial grade", "MULTIPLY"
    tree.links.new(render.outputs[aov_name], zone.inputs[0])
    tree.links.new(inverse.outputs[0], zone.inputs[1])
    darkened = compositor_mix(
        tree, "MULTIPLY", previous, (spec["foreground_gain"],) * 3 + (1,)
    )
    selected = compositor_mix(tree, "MIX", previous, darkened)
    tree.links.new(zone.outputs[0], selected.node.inputs[0])
    selected.node.name = PREFIX + "foreground hierarchy with actor protection"
    tree.links.new(selected, output.inputs["Image"])
    tree.links.new(selected, tree.nodes["Caption cache | beauty"].inputs["beauty"])
    return {
        "aov": aov_name,
        "material_count": count,
        "gain": spec["foreground_gain"],
        "actor_protected": True,
    }


def stage_design(scene, spec):
    changes, materials = [], []
    powers = {
        "Softlight | front soft fill": spec["front_fill_watts"],
        "Softlight | hall ceiling bounce": spec["ceiling_watts"],
        "Focused light | cold window key": spec["window_watts"],
        "Focused light | warm altar": spec["altar_watts"],
        "Stage art | grounded backlight": spec["pool_watts"],
    }
    for name, power in powers.items():
        obj = scene.objects[name]
        changes.append({"name": name, "old_watts": obj.data.energy, "new_watts": power})
        obj.data.energy = power
    key = scene.objects["Stage art | grounded backlight"]
    key.data.spot_size, key.data.spot_blend = math.radians(58), 0.5
    key.data.shadow_soft_size = 0.14
    aim(key, (0, 1.4, 0))
    for material in bpy.data.materials:
        tree = material.node_tree
        if not tree or material.get("performer_id"):
            continue
        surface = tree.nodes.get("Focused light | responsive stage surface")
        if not surface or not surface.inputs["Base Color"].is_linked:
            continue
        geometry = node(tree, "ShaderNodeNewGeometry", "stage coordinates")
        pos = node(tree, "ShaderNodeSeparateXYZ", "stage position")
        norm = node(tree, "ShaderNodeSeparateXYZ", "stage normal")
        tree.links.new(geometry.outputs["Position"], pos.inputs[0])
        tree.links.new(geometry.outputs["Normal"], norm.inputs[0])
        side = remap(
            tree,
            scalar(tree, "ABSOLUTE", pos.outputs["X"]),
            spec["aisle_half_width"],
            spec["side_falloff_end"],
            "aisle to side falloff",
        )
        region = scalar(
            tree,
            "MULTIPLY",
            scalar(
                tree,
                "LESS_THAN",
                scalar(tree, "ABSOLUTE", pos.outputs["Z"]),
                spec["region_height"],
            ),
            scalar(tree, "GREATER_THAN", norm.outputs["Z"], 0.25),
        )
        amount = scalar(
            tree,
            "MULTIPLY",
            region,
            scalar(tree, "MULTIPLY", side, 1 - spec["side_floor_factor"]),
        )
        factor = scalar(
            tree,
            "SUBTRACT",
            1,
            scalar(tree, "MULTIPLY", amount, enable(tree, "enable stage side control")),
        )
        original = surface.inputs["Base Color"].links[0].from_socket
        tree.links.new(
            mix(tree, original, factor, label="stage side hierarchy"),
            surface.inputs["Base Color"],
        )
        materials.append(material.name)
    air = scene.objects.get("Wedding | bounded rear scattering")
    density_changes = []
    if air:
        for slot in air.material_slots:
            if slot.material and slot.material.node_tree:
                for n in slot.material.node_tree.nodes:
                    density = n.inputs.get("Density")
                    if density and not density.is_linked:
                        old = density.default_value
                        density.default_value *= spec["rear_density_multiplier"]
                        density_changes.append(
                            {"node": n.name, "old": old, "new": density.default_value}
                        )
    tree = scene.compositing_node_group
    for label, power in (
        ("actor", spec["actor_glow_strength"]),
        ("stage", spec["stage_glow_strength"]),
    ):
        halo = tree.nodes.get("Wedding | " + label + " halo")
        if halo:
            halo.inputs["Strength"].default_value = power
    final = (
        next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
        .inputs["Image"]
        .links[0]
        .from_socket
    )
    tree.links.new(final, tree.nodes["Caption cache | beauty"].inputs["beauty"])
    return {
        "lights": changes,
        "side_control_materials": materials,
        "density": density_changes,
        "caption_beauty_matches_final": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--stills", type=int, nargs="*", default=[4200, 4250, 4290])
    parser.add_argument("--preview-percentage", type=int, default=67)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    config = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    source = Path(bpy.data.filepath)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config["source_sha256"]
    scene = bpy.context.scene
    assert scene.get("character_layer_revision") == config["input_revision"]
    assert not scene.get("reference_transfer_revision")
    scene.eevee.shadow_pool_size = str(config["lighting"]["shadow_pool_mb"])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for n in other.compositing_node_group.nodes:
                if n.type == "OUTPUT_FILE":
                    n.mute = True
    poses = {}
    for number in FRAMES:
        scene.frame_set(number)
        poses[number] = snapshot(scene)
    scene.frame_set(4200)
    bpy.context.view_layer.update()
    lights = light_design(scene, config["lighting"])
    characters = character_design(scene, config)
    material_report = apply_material_response(scene, config["materials"])
    rims = add_rims(scene, config["rim"])
    stage = stage_design(scene, config["stage"])
    stage["spatial_post"] = stage_zone_grade(scene, config["stage"])
    scene["reference_transfer_revision"] = config["id"]
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = args.preview_percentage
    for number in args.stills:
        scene.frame_set(number)
        scene.render.filepath = str(args.output_dir / f"transfer-{number}.png")
        bpy.ops.render.render(write_still=True)
        print("TRANSFER_STILL_READY", number, flush=True)
    for number, expected in poses.items():
        scene.frame_set(number)
        assert snapshot(scene) == expected, number
    scene.frame_set(4140)
    scene.render.resolution_percentage = 100
    bpy.ops.file.pack_all()
    project = args.output_dir / "Franken_Duet_Reference_Transfer.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "source": str(source),
        "source_sha256": config["source_sha256"],
        "project": str(project),
        "profile": config,
        "characters": characters,
        "materials": material_report,
        "rims": rims,
        "actor_lights": lights,
        "stage": stage,
        "pose_camera_unchanged_frames": list(poses),
        "all_file_outputs_saved_muted": True,
        "limits": config["limits"],
    }
    (args.output_dir / "transfer-preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("REFERENCE_TRANSFER_READY", flush=True)


if __name__ == "__main__":
    main()
