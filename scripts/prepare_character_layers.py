"""Unify one actor color/lighting/AO/highlight contract in an independent copy."""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrate_light_space import world_vector
from mmd_hesperides_stage import aim
from verify_duet_integration import snapshot

PREFIX = "Character layers | "


def node(tree, kind, label):
    result = tree.nodes.new(kind)
    result.name = PREFIX + label
    result.label = label
    return result


def plug(tree, value, socket):
    if hasattr(value, "is_output"):
        tree.links.new(value, socket)
    else:
        socket.default_value = value


def scalar(tree, operation, a, b=None, label=""):
    result = node(tree, "ShaderNodeMath", label or operation)
    result.operation = operation
    plug(tree, a, result.inputs[0])
    if b is not None:
        plug(tree, b, result.inputs[1])
    return result.outputs[0]


def vector(tree, operation, a, b=None, label=""):
    result = node(tree, "ShaderNodeVectorMath", label or operation)
    result.operation = operation
    plug(tree, a, result.inputs[0])
    if b is not None:
        plug(tree, b, result.inputs[1])
    return result.outputs["Value"] if operation == "DOT_PRODUCT" else result.outputs[0]


def color(tree, a, b, fac=1, blend="MULTIPLY", label=""):
    result = node(tree, "ShaderNodeMixRGB", label or blend)
    result.blend_type = blend
    plug(tree, fac, result.inputs[0])
    plug(tree, a, result.inputs[1])
    plug(tree, b, result.inputs[2])
    return result.outputs[0]


def role(material):
    name = (
        material.get("source_mmd_material_name", material.name)
        .split(".")[0]
        .rstrip("+")
    )
    kind = material.get("aether_surface", material.get("look_category", "cloth"))
    if name in {"颜", "面1", "面2"}:
        return "face"
    if name == "肌" or name in {"首", "手"}:
        return "skin"
    if kind in {"ink", "iris", "eye"} or any(
        w in name for w in ("眉", "睫", "目", "齿", "口", "舌", "二重")
    ):
        return "features"
    return (
        kind
        if kind in {"skin", "hair", "cloth", "leather", "fur", "trim", "gold"}
        else "cloth"
    )


def setup_lights(scene, spec):
    stage = bpy.data.collections.new("Character layers | stage-only receivers")
    scene.collection.children.link(stage)
    for obj in scene.objects:
        if obj.type == "MESH" and not obj.get("performer_id"):
            stage.objects.link(obj)
    changed = []
    for light in scene.objects:
        if light.type != "LIGHT" or light.name.startswith("Reference duet |"):
            continue
        receivers = light.light_linking.receiver_collection
        if receivers is None:
            light.light_linking.receiver_collection = stage
            changed.append(
                {"light": light.name, "change": "stage-only receiver collection"}
            )
        elif any(o.get("performer_id") for o in receivers.objects):
            light.hide_render = True
            changed.append(
                {"light": light.name, "change": "redundant actor fill disabled"}
            )
    for actor in ("aksiniya", "aether"):
        origin = scene.objects[
            f"Quality | {actor} | head origin"
        ].matrix_world.translation.copy()
        for kind, offset in [
            ("key", (-2.8, -3.6, 3.3)),
            ("fill", (2.8, -2.0, 0.6)),
            ("rim", (1.8, 2.1, 1.8)),
        ]:
            light = scene.objects[f"Reference duet | {actor} | {kind}"]
            light.location = origin + Vector(offset)
            aim(light, origin + Vector((0, 0, -0.15)))
            light.data.energy = spec[kind + "_watts"]
            light.data.size = spec[kind + "_size"]
            light.data.color = (
                (1, 0.94, 0.88)
                if kind == "key"
                else (0.75, 0.85, 1)
                if kind == "fill"
                else (1, 0.86, 0.69)
            )
            light.data.use_shadow = True
            light.data.volume_factor = 0
            changed.append(
                {
                    "light": light.name,
                    "watts": light.data.energy,
                    "size": light.data.size,
                    "location": list(light.location),
                }
            )
    return changed


def rebuild(material, scene, spec):
    tree = material.node_tree
    source = tree.nodes.get("mmd_shader")
    surface = tree.nodes.get("Aether v2 | controlled toon surface") or tree.nodes.get(
        "Look v3 | NPR surface"
    )
    if not source or not surface:
        return None
    actor = material.get("performer_id")
    kind = role(material)
    # Keep texture-designed feature lines and the original corneal closure.
    if kind == "features":
        chroma = tree.nodes.get("Aether v2 | texture white balance")
        if chroma and material.get("aether_surface") == "iris":
            chroma.inputs["Saturation"].default_value = spec["eyes"]["iris_saturation"]
        coat = tree.nodes.get("Aether v2 | clear eye highlight")
        if coat:
            coat.inputs["Roughness"].default_value = spec["eyes"]["coat_roughness"]
        normal = tree.nodes.get("Aether v2 | convex iris optical normal")
        if normal:
            normal.inputs["Strength"].default_value = spec["eyes"]["normal_strength"]
        return {
            "material": material.name,
            "role": kind,
            "feature_design_preserved": True,
        }
    raw = source.outputs["Color"]
    chroma = node(tree, "ShaderNodeHueSaturation", "source color and chroma")
    tree.links.new(raw, chroma.inputs["Color"])
    chroma.inputs["Saturation"].default_value = (
        0.96 if kind in {"face", "skin"} else 1.02
    )
    base = chroma.outputs["Color"]
    if kind == "face":
        crease = tree.nodes.get("Aether v2 | Aether mouth crease")
        if crease:
            tree.links.new(base, crease.inputs[1])
            base = crease.outputs[0]
        face_line = tree.nodes.get("Face ink | Mouth crease")
        if face_line and face_line.type == "MIX_RGB":
            tree.links.new(base, face_line.inputs[1])
            base = face_line.outputs[0]
    geometry = node(tree, "ShaderNodeNewGeometry", "geometry")
    diffuse = node(tree, "ShaderNodeBsdfDiffuse", "native diffuse response")
    diffuse.inputs["Color"].default_value = (1, 1, 1, 1)
    if kind == "face":
        normal = world_vector(
            tree,
            scene.objects[f"Quality | {actor} | head forward"],
            scene.objects[f"Quality | {actor} | head origin"],
            PREFIX + "posed planar face normal",
        )
        tree.links.new(normal, diffuse.inputs["Normal"])
    rgb = node(tree, "ShaderNodeShaderToRGB", "actual light and occlusion")
    tree.links.new(diffuse.outputs[0], rgb.inputs[0])
    bw = node(tree, "ShaderNodeRGBToBW", "illumination value")
    tree.links.new(rgb.outputs[0], bw.inputs[0])
    response = node(tree, "ShaderNodeMapRange", "illumination calibration")
    response.clamp = True
    response.interpolation_type = "SMOOTHSTEP"
    tree.links.new(bw.outputs[0], response.inputs["Value"])
    response.inputs["From Min"].default_value = spec["illumination"]["low"]
    response.inputs["From Max"].default_value = spec["illumination"]["high"]
    factor = response.outputs[0]
    sdf = tree.nodes.get("Genshin study | SDF face factor")
    if kind == "face" and sdf:
        ramp = tree.nodes.get("Aether v2 | material light response") or tree.nodes.get(
            "Look v3 | Soft toon bands"
        )
        sdf_signal = ramp.inputs[0].links[0].from_socket
        factor = scalar(
            tree, "MINIMUM", factor, sdf_signal, "SDF and native light combined once"
        )
    enable = node(tree, "ShaderNodeValue", "enable lighting")
    enable.outputs[0].default_value = 1
    factor = scalar(
        tree,
        "ADD",
        1,
        scalar(
            tree, "MULTIPLY", enable.outputs[0], scalar(tree, "SUBTRACT", factor, 1)
        ),
        "lighting switch",
    )
    palette = node(tree, "ShaderNodeValToRGB", "single material palette")
    palette.color_ramp.interpolation = "EASE"
    palette.color_ramp.elements.new(0.52)
    key = "gold_hair" if actor == "aether" and kind == "hair" else kind
    for element, position, rgba in zip(
        palette.color_ramp.elements, [0, 0.52, 1], spec["palettes"][key]
    ):
        element.position = position
        element.color = rgba
    tree.links.new(factor, palette.inputs[0])
    shaded = color(tree, base, palette.outputs[0], label="base times one palette")
    ao = node(tree, "ShaderNodeAmbientOcclusion", "single contact AO")
    ao.samples = 16
    ao.inputs["Distance"].default_value = (
        0.018 if kind == "face" else spec["illumination"]["ao_distance"]
    )
    amount = node(tree, "ShaderNodeValue", "AO strength")
    amount.outputs[0].default_value = (
        0.045 if kind == "face" else spec["illumination"]["ao_strength"]
    )
    ao_factor = scalar(
        tree,
        "SUBTRACT",
        1,
        scalar(
            tree,
            "MULTIPLY",
            amount.outputs[0],
            scalar(tree, "SUBTRACT", 1, ao.outputs["AO"]),
        ),
        "bounded contact factor",
    )
    shaded = color(tree, shaded, ao_factor, label="one contact application")
    highlight = None
    if kind == "hair" and not material.name.split(".")[0].endswith("+"):
        normal = geometry.outputs["Normal"]
        up = world_vector(
            tree,
            scene.objects[f"Quality | {actor} | head up"],
            scene.objects[f"Quality | {actor} | head origin"],
            PREFIX + "posed hair up",
        )
        dot = vector(tree, "DOT_PRODUCT", normal, up)
        projected = node(tree, "ShaderNodeVectorMath", "head axis projection")
        projected.operation = "SCALE"
        tree.links.new(normal, projected.inputs[0])
        tree.links.new(dot, projected.inputs[3])
        tangent = vector(
            tree, "NORMALIZE", vector(tree, "SUBTRACT", up, projected.outputs[0])
        )
        key_direction = world_vector(
            tree,
            scene.objects[f"Reference duet | {actor} | key"],
            scene.objects[f"Quality | {actor} | head origin"],
            PREFIX + "actual moving key direction",
        )
        half = vector(
            tree,
            "NORMALIZE",
            vector(tree, "ADD", geometry.outputs["Incoming"], key_direction),
        )
        th = vector(tree, "DOT_PRODUCT", tangent, half)
        band = scalar(
            tree,
            "POWER",
            scalar(
                tree,
                "MAXIMUM",
                scalar(tree, "SUBTRACT", 1, scalar(tree, "MULTIPLY", th, th)),
                0,
            ),
            spec["hair"]["exponent"],
        )
        mask = tree.nodes.get("Surface | mask channels")
        if mask:
            band = scalar(
                tree,
                "MULTIPLY",
                band,
                scalar(
                    tree,
                    "ADD",
                    0.35,
                    scalar(tree, "MULTIPLY", mask.outputs["Blue"], 0.65),
                ),
            )
        gain = node(tree, "ShaderNodeValue", "hair highlight strength")
        gain.outputs[0].default_value = spec["hair"][
            "gold_strength" if actor == "aether" else "silver_strength"
        ]
        highlight = scalar(
            tree, "MULTIPLY", band, gain.outputs[0], "single hair highlight"
        )
        shaded = color(
            tree,
            shaded,
            (1, 0.96, 0.85, 1) if actor == "aether" else (0.92, 0.96, 1, 1),
            highlight,
            "SCREEN",
            "one directional hair highlight",
        )
    tree.links.new(shaded, surface.inputs["Color"])
    for n in tree.nodes:
        if n.type == "OUTPUT_AOV" and n.aov_name == "StageArtRim":
            for link in list(n.inputs["Color"].links):
                tree.links.remove(link)
            n.inputs["Color"].default_value = (0, 0, 0, 1)
            if highlight:
                tree.links.new(highlight, n.inputs["Color"])
        if n.type == "BSDF_PRINCIPLED" and ("gold" in n.name.lower()):
            n.inputs["Metallic"].default_value = spec["physical"]["gold_metallic"]
            old = (
                n.inputs["Roughness"].links[0].from_socket
                if n.inputs["Roughness"].is_linked
                else n.inputs["Roughness"].default_value
            )
            clamp = node(tree, "ShaderNodeMapRange", "metal roughness range")
            clamp.clamp = True
            plug(tree, old, clamp.inputs["Value"])
            clamp.inputs["To Min"].default_value = spec["physical"][
                "gold_roughness_min"
            ]
            clamp.inputs["To Max"].default_value = spec["physical"][
                "gold_roughness_max"
            ]
            tree.links.new(clamp.outputs[0], n.inputs["Roughness"])
    mix = tree.nodes.get("Aether v2 | toon and physical layers")
    if mix and kind in {"cloth", "leather"}:
        mix.inputs[0].default_value = spec["physical"][kind + "_mix"]
    material["character_layer_revision"] = spec["id"]
    material["character_layer_role"] = kind
    return {
        "material": material.name,
        "actor": actor,
        "role": kind,
        "surface": surface.name,
        "source": "mmd_shader.Color with retained source MMD composition",
        "sdf_combined_once": bool(kind == "face" and sdf),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--stills", type=int, nargs="*", default=[4200, 4250, 4290])
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    config = json.loads(args.profile.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    source = bpy.data.filepath
    assert scene.get("graphic_self_shadow_revision") == config["input_revision"]
    assert not scene.get("character_layer_revision")
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for n in other.compositing_node_group.nodes:
                if n.type == "OUTPUT_FILE":
                    n.mute = True
    poses = {}
    for frame in [1, 2100, 4140, 4200, 4250, 4290, 4439, 8400, 11899]:
        scene.frame_set(frame)
        poses[frame] = snapshot(scene)
    scene.frame_set(4200)
    bpy.context.view_layer.update()
    lights = setup_lights(scene, config["lighting"])
    materials = []
    for mat in list(bpy.data.materials):
        if mat.get("performer_id") and mat.node_tree:
            record = rebuild(mat, scene, config)
            if record:
                materials.append(record)
    assert len(materials) > 30
    scene["character_layer_revision"] = config["id"]
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = 67
    for frame in args.stills:
        scene.frame_set(frame)
        scene.render.filepath = str(args.output_dir / f"layers-{frame}.png")
        bpy.ops.render.render(write_still=True)
    for frame, state in poses.items():
        scene.frame_set(frame)
        assert snapshot(scene) == state, frame
    scene.frame_set(4140)
    scene.render.resolution_percentage = 100
    bpy.ops.file.pack_all()
    target = args.output_dir / "Franken_Duet_Character_Layers.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    (args.output_dir / "layer-preparation.json").write_text(
        json.dumps(
            {
                "source": source,
                "project": str(target),
                "profile": config,
                "materials": materials,
                "lights": lights,
                "pose_camera_unchanged_frames": list(poses),
                "all_file_outputs_saved_muted": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("CHARACTER_LAYERS_MASTER_READY", flush=True)


if __name__ == "__main__":
    main()
