"""Rebuild Aether's own face, eyes, hair and masked outfit surfaces.

The old source node graph stays intact for PMX alpha/morph semantics. Its
generic display treatment is replaced using the actual per-material textures.
"""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import aim, area


def node(tree, kind, label, **properties):
    item = tree.nodes.new(kind)
    item.name = "Aether v2 | " + label
    item.label = label
    for name, value in properties.items():
        setattr(item, name, value)
    return item


def plug(tree, value, socket):
    if hasattr(value, "is_output"):
        tree.links.new(value, socket)
    else:
        socket.default_value = value


def scalar(tree, operation, first, second=None, label=""):
    item = node(tree, "ShaderNodeMath", label or operation, operation=operation)
    plug(tree, first, item.inputs[0])
    if second is not None:
        plug(tree, second, item.inputs[1])
    return item.outputs[0]


def vector(tree, operation, first, second=None):
    item = node(tree, "ShaderNodeVectorMath", operation, operation=operation)
    plug(tree, first, item.inputs[0])
    if second is not None:
        plug(tree, second, item.inputs[1])
    return item.outputs["Value"] if operation == "DOT_PRODUCT" else item.outputs[0]


def color(tree, first, second, factor=1, blend="MULTIPLY", label="color"):
    item = node(tree, "ShaderNodeMixRGB", label, blend_type=blend)
    plug(tree, factor, item.inputs[0])
    plug(tree, first, item.inputs[1])
    plug(tree, second, item.inputs[2])
    return item.outputs[0]


def texture(tree, path, base):
    image = bpy.data.images.load(str(path), check_existing=True)
    image.colorspace_settings.name = "Non-Color"
    image.pack()
    item = node(tree, "ShaderNodeTexImage", path.stem)
    item.image = image
    if base.inputs["Vector"].is_linked:
        tree.links.new(
            base.inputs["Vector"].links[0].from_socket, item.inputs["Vector"]
        )
    return item


def physical(tree, base_color, label, roughness, metallic=0, specular=0.3):
    bsdf = node(tree, "ShaderNodeBsdfPrincipled", label)
    plug(tree, base_color, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Specular IOR Level"].default_value = specular
    return bsdf


def rebuild(material, controls, hybrid):
    tree = material.node_tree
    source = tree.nodes.get("mmd_shader")
    base = tree.nodes.get("mmd_base_tex")
    if not source or not base or not base.image:
        return None
    name = material.get("source_mmd_material_name", material.name).removesuffix(".001")
    kind = (
        "face"
        if name in {"面1", "面2", "二重"}
        else "skin"
        if name in {"肌", "口舌"}
        else "iris"
        if name == "目"
        else "eye"
        if name in {"目白", "目星", "齿"}
        else "ink"
        if name in {"眉", "睫", "> <"}
        else "hair"
        if name == "发"
        else "leather"
        if name == "手套"
        else "gold"
        if name in {"耳饰", "发饰"}
        else "cloth"
    )
    material["aether_surface"] = kind
    geometry = node(tree, "ShaderNodeNewGeometry", "surface geometry")
    key = Vector((-0.55, -0.68, 0.49)).normalized()
    light = vector(tree, "DOT_PRODUCT", geometry.outputs["Normal"], key)
    wrapped = scalar(tree, "ADD", scalar(tree, "MULTIPLY", light, 0.82), 0.18)
    ramp = node(tree, "ShaderNodeValToRGB", "material light response")
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].position = 0.16
    ramp.color_ramp.elements[1].position = 0.86
    ramp.color_ramp.elements.new(0.52)
    palettes = {
        "face": [(0.80, 0.61, 0.54, 1), (1.18, 1.04, 0.99, 1), (1.42, 1.25, 1.14, 1)],
        "skin": [(0.70, 0.50, 0.44, 1), (1.12, 0.98, 0.92, 1), (1.38, 1.20, 1.08, 1)],
        "hair": [(0.50, 0.37, 0.22, 1), (1.00, 0.90, 0.68, 1), (1.32, 1.20, 0.88, 1)],
        "cloth": [(0.25, 0.25, 0.33, 1), (0.74, 0.75, 0.84, 1), (1.06, 1.07, 1.12, 1)],
        "leather": [
            (0.28, 0.27, 0.32, 1),
            (0.76, 0.75, 0.79, 1),
            (1.03, 1.03, 1.07, 1),
        ],
        "gold": [(0.5, 0.42, 0.35, 1), (0.95, 0.86, 0.72, 1), (1.12, 1.06, 0.94, 1)],
        "iris": [(0.83, 0.80, 0.82, 1), (0.99, 0.98, 1, 1), (1.06, 1.05, 1.06, 1)],
        "eye": [(0.82, 0.83, 0.89, 1), (1, 1, 1, 1), (1.04, 1.04, 1.04, 1)],
        "ink": [(0.20, 0.17, 0.20, 1)] * 3,
    }
    for element, rgba in zip(ramp.color_ramp.elements, palettes[kind]):
        element.color = rgba
    tree.links.new(wrapped, ramp.inputs[0])
    chroma = node(tree, "ShaderNodeHueSaturation", "texture white balance")
    tree.links.new(base.outputs["Color"], chroma.inputs["Color"])
    chroma.inputs["Saturation"].default_value = (
        1.0
        if kind in {"face", "skin"}
        else 1.08
        if kind == "hair"
        else 1.10
        if kind == "iris"
        else 0.90
    )
    original = chroma.outputs["Color"]
    if kind in {"face", "skin"}:
        original = color(tree, original, (1.03, 1.0, 0.98, 1), label="skin balance")
    shaded = color(tree, original, ramp.outputs[0], label="texture times light")
    if kind in {"face", "skin", "eye"}:
        ao = node(tree, "ShaderNodeAmbientOcclusion", "local face and joint definition")
        ao.inputs["Distance"].default_value = 0.020 if kind == "face" else 0.025
        ao.samples = 8
        shaded = color(
            tree,
            shaded,
            ao.outputs["AO"],
            0.12 if kind == "face" else 0.20,
            label="local contact tone",
        )
    if kind == "face":
        mask = texture(tree, controls / "face-crease.png", base)
        shaded = color(
            tree,
            shaded,
            (0.025, 0.008, 0.012, 1),
            mask.outputs["Color"],
            "MIX",
            "Aether mouth crease",
        )
    if kind == "hair":
        up = tree.nodes.get("Surface | animated head up")
        if up:
            normal = geometry.outputs["Normal"]
            dot = vector(tree, "DOT_PRODUCT", normal, up.outputs[0])
            scale = node(
                tree, "ShaderNodeVectorMath", "project head axis", operation="SCALE"
            )
            tree.links.new(normal, scale.inputs[0])
            tree.links.new(dot, scale.inputs[3])
            tangent = vector(
                tree,
                "NORMALIZE",
                vector(tree, "SUBTRACT", up.outputs[0], scale.outputs[0]),
            )
            half = vector(
                tree,
                "NORMALIZE",
                vector(tree, "ADD", geometry.outputs["Incoming"], key),
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
                34,
            )
            shaded = color(
                tree,
                shaded,
                (1.0, 0.98, 0.90, 1),
                scalar(tree, "MULTIPLY", band, 0.14),
                "SCREEN",
                "head aligned hair highlight",
            )
    emission = node(tree, "ShaderNodeEmission", "controlled toon surface")
    tree.links.new(shaded, emission.inputs[0])
    closure = emission.outputs[0]
    if kind in {"face", "skin", "cloth", "leather", "hair", "gold"}:
        bsdf = physical(
            tree,
            original,
            "material-specific physical response",
            0.68
            if kind in {"face", "skin"}
            else 0.38
            if kind == "leather"
            else 0.7
            if kind == "cloth"
            else 0.32,
            specular=0.22 if kind in {"face", "skin"} else 0.32,
        )
        if kind in {"face", "skin"}:
            bsdf.inputs["Subsurface Weight"].default_value = 0.035
            bsdf.inputs["Subsurface Scale"].default_value = 0.035
        if kind == "cloth":
            bsdf.inputs["Sheen Weight"].default_value = 0.15
        mix = node(tree, "ShaderNodeMixShader", "toon and physical layers")
        mix.inputs[0].default_value = (
            hybrid
            if kind in {"face", "skin"}
            else 0.18
            if kind == "cloth"
            else 0.0
            if kind == "hair"
            else 0.24
        )
        tree.links.new(closure, mix.inputs[1])
        tree.links.new(bsdf.outputs[0], mix.inputs[2])
        closure = mix.outputs[0]
    if name in {"身体", "手套", "发饰", "耳饰"}:
        control = texture(tree, controls / "body-control.png", base)
        channels = node(tree, "ShaderNodeSeparateColor", "gold controls")
        tree.links.new(control.outputs["Color"], channels.inputs[0])
        gold_color = color(
            tree, original, (1.0, 0.80, 0.48, 1), label="warm gold conductor"
        )
        metal = physical(tree, gold_color, "gold, not cloth or skin", 0.24, 0.88, 0.5)
        tree.links.new(channels.outputs["Green"], metal.inputs["Roughness"])
        metal.inputs["Coat Weight"].default_value = 0.12
        mix = node(tree, "ShaderNodeMixShader", "gold only mask")
        tree.links.new(
            scalar(tree, "MULTIPLY", channels.outputs["Red"], 0.85), mix.inputs[0]
        )
        tree.links.new(closure, mix.inputs[1])
        tree.links.new(metal.outputs[0], mix.inputs[2])
        closure = mix.outputs[0]
    if kind == "iris":
        coat = physical(tree, (0, 0, 0, 1), "clear eye highlight", 0.10, specular=0.5)
        coat.inputs["IOR"].default_value = 1.4
        eye_normal = texture(tree, controls / "iris-normal.png", base)
        optical = node(tree, "ShaderNodeNormalMap", "convex iris optical normal")
        optical.inputs["Strength"].default_value = 0.7
        tree.links.new(eye_normal.outputs["Color"], optical.inputs["Color"])
        tree.links.new(optical.outputs["Normal"], coat.inputs["Normal"])
        add = node(tree, "ShaderNodeAddShader", "iris and corneal glint")
        tree.links.new(closure, add.inputs[0])
        tree.links.new(coat.outputs[0], add.inputs[1])
        closure = add.outputs[0]
    transparent = node(tree, "ShaderNodeBsdfTransparent", "original PMX alpha")
    alpha = node(tree, "ShaderNodeMixShader", "retain animated opacity")
    tree.links.new(source.outputs["Alpha"], alpha.inputs[0])
    tree.links.new(transparent.outputs[0], alpha.inputs[1])
    tree.links.new(closure, alpha.inputs[2])
    out = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL")
    tree.links.new(alpha.outputs[0], out.inputs["Surface"])
    return {"material": material.name, "kind": kind, "source_texture": base.image.name}


def character_lights(scene):
    receivers = bpy.data.collections.new("Aether | light receivers")
    scene.collection.children.link(receivers)
    for obj in scene.objects:
        if (
            obj.type == "MESH"
            and obj.get("performer_id") == "aether"
            and any(m.type == "ARMATURE" for m in obj.modifiers)
        ):
            receivers.objects.link(obj)
    lights = []
    for name, location, target, power, rgb, size in [
        (
            "Aether | portrait key",
            (-2.5, -3.5, 4.0),
            (0, 0, 1.3),
            180,
            (1.0, 0.94, 0.96),
            2.0,
        ),
        ("Aether | cool fill", (2.5, -1.0, 2.0), (0, 0, 1.3), 35, (0.68, 0.78, 1), 3.0),
        ("Aether | rim", (1.0, 2.0, 3.5), (0, 0, 1.5), 140, (0.8, 0.87, 1), 2.0),
    ]:
        obj = area(name, location, target, power, rgb, size)
        obj.light_linking.receiver_collection = receivers
        lights.append(obj.name)
    return lights


def ink(scene):
    materials = {
        m.name: m
        for m in bpy.data.materials
        if m.get("performer_id") == "aether" and m.get("aether_surface")
    }
    for mat in materials.values():
        kind = mat["aether_surface"]
        mat.mmd_material.edge_color = (
            (0.003, 0.002, 0.005, 1)
            if kind in {"face", "skin"}
            else (0.005, 0.003, 0.007, 1)
        )
    for obj in scene.objects:
        if (
            obj.type != "MESH"
            or obj.get("performer_id") != "aether"
            or "outline_source_weights" not in obj
        ):
            continue
        vg = obj.vertex_groups.get("mmd_edge_preview")
        if not vg:
            continue
        weights = obj["outline_source_weights"]
        scales = {}
        for poly in obj.data.polygons:
            mat = obj.data.materials[poly.material_index]
            if mat.name not in materials:
                continue
            kind = mat["aether_surface"]
            factor = (
                2.1
                if kind in {"face", "hair"}
                else 1.85
                if kind in {"cloth", "leather"}
                else 1.4
            )
            for index in poly.vertices:
                scales[index] = min(scales.get(index, factor), factor)
        for index, scale in scales.items():
            vg.add([index], min(1, float(weights[index]) * scale), "REPLACE")


def study_camera(scene):
    arm = next(
        o
        for o in scene.objects
        if o.type == "ARMATURE" and o.get("performer_id") == "aether"
    )
    head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
    center = arm.matrix_world @ (head.matrix @ Vector((0, 0.1, 0)))
    bpy.ops.object.camera_add(location=center + Vector((0, -1.15, 0.03)))
    camera = bpy.context.object
    camera.name = "Aether | QA portrait camera"
    camera.data.lens = 75
    aim(camera, center)
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1000
    return camera


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--hybrid", type=float, default=0.0)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    scene.eevee.shadow_pool_size = "1024"
    scene.frame_set(4200)
    original_camera = scene.camera
    source_file = bpy.data.filepath
    study_camera(scene)
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 48
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(args.output_dir / "before-portrait.png")
    bpy.ops.render.render(write_still=True)
    report = [
        rebuild(m, args.controls, args.hybrid)
        for m in list(bpy.data.materials)
        if m.get("performer_id") == "aether"
        and m.node_tree
        and m.node_tree.nodes.get("mmd_shader")
    ]
    lights = character_lights(scene)
    ink(scene)
    scene.render.filepath = str(args.output_dir / "after-portrait.png")
    bpy.ops.render.render(write_still=True)
    scene.camera = original_camera
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.eevee.taa_render_samples = 32
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(
        filepath=str(args.output_dir / "Franken_Duet_Aether_Revised.blend")
    )
    scene.render.resolution_percentage = 50
    for frame in [4200, 8400, 11899]:
        scene.frame_set(frame)
        scene.render.filepath = str(args.output_dir / f"duet-{frame:05d}.png")
        bpy.ops.render.render(write_still=True)
    (args.output_dir / "look-report.json").write_text(
        json.dumps(
            {
                "source": source_file,
                "materials": report,
                "lights": lights,
                "skin_hybrid": args.hybrid,
                "method": "Aether-specific source textures, deeper material ramps, local AO, own skin balance, eye coat, atlas-gated gold and inverse-hull ink",
                "dropped_source_display_layers": "Old generic sphere/toon color treatment; original alpha and UV inputs preserved",
                "camera_motion_changed": False,
                "physics_changed": False,
                "scope": "New look study, not the final movie",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("AETHER_LOOK_REVISED", flush=True)


if __name__ == "__main__":
    main()
