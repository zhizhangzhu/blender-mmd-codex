"""Stage-only reconstruction of the supplied Ray preview; never run on a duet.

Reads the supplied HLSL as text. Blender nodes approximate its material controls;
the fitted camera and lighting are our estimates, not the author's project data.
"""

import argparse
import json
import math
import random
import re
import sys
import time
import warnings
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import (
    area,
    atmosphere,
    compositor,
    math_node,
    ray_settings,
    rebuild_materials,
    texture_node,
)


def constant(text, name):
    match = re.search(r"const\s+float[234]?\s+" + name + r"\s*=\s*([0-9.]+)\s*;", text)
    if not match:
        raise ValueError("Review non-scalar HLSL constant: " + name)
    return float(match[1])


def matcap(mat, folder, multiplier):
    path = folder / (mat.name + ".fx")
    if not path.is_file():
        return None
    defs, _values = ray_settings(path)
    if defs.get("ALBEDO_MATCAP_ENABLE") != "2":
        return None
    source = path.read_text(encoding="utf-8-sig")
    strength = constant(source, "albedoMatcap")
    affect = constant(source, "albedoMatcap_Affect")
    if defs.get("ALBEDO_MATCAP_MAP_AFFECT_FROM") != "1":
        raise ValueError("Unsupported MatCap mask: " + mat.name)
    tree = mat.node_tree
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    previous = bsdf.inputs["Base Color"].links[0].from_socket
    normal = (
        bsdf.inputs["Normal"].links[0].from_socket
        if bsdf.inputs["Normal"].is_linked
        else tree.nodes.new("ShaderNodeNewGeometry").outputs["Normal"]
    )
    view = tree.nodes.new("ShaderNodeVectorTransform")
    view.vector_type, view.convert_from, view.convert_to = "NORMAL", "WORLD", "CAMERA"
    tree.links.new(normal, view.inputs[0])
    scale = tree.nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    scale.inputs[3].default_value = 0.5
    tree.links.new(view.outputs[0], scale.inputs[0])
    offset = tree.nodes.new("ShaderNodeVectorMath")
    offset.operation = "ADD"
    offset.inputs[1].default_value = (0.5, 0.5, 0)
    tree.links.new(scale.outputs[0], offset.inputs[0])
    tex = texture_node(tree, folder, defs["ALBEDO_MATCAP_MAP_FILE"], True)
    tex.extension = "EXTEND"
    # DirectX uses top-origin texture V. Blender's image V is bottom-origin,
    # so the HLSL's explicit y=1-y must not be applied a second time here.
    tree.links.new(offset.outputs[0], tex.inputs["Vector"])
    mask = texture_node(tree, folder, defs["ALBEDO_MATCAP_MAP_AFFECT_FILE"], True)
    sep = tree.nodes.new("ShaderNodeSeparateColor")
    tree.links.new(mask.outputs["Color"], sep.inputs[0])
    channel = int(defs["ALBEDO_MATCAP_MAP_AFFECT_SWIZZLE"])
    if channel not in range(4):
        raise ValueError("Review RGB MatCap affect: " + mat.name)
    factor = math_node(
        tree,
        "Reference | authored MatCap intensity",
        "MULTIPLY",
        sep.outputs[channel] if channel < 3 else mask.outputs["Alpha"],
        strength * affect * multiplier,
    )
    add = tree.nodes.new("ShaderNodeMixRGB")
    add.name, add.blend_type = "Reference | masked additive MatCap", "ADD"
    add.use_clamp = True
    tree.links.new(factor, add.inputs[0])
    tree.links.new(previous, add.inputs[1])
    tree.links.new(tex.outputs["Color"], add.inputs[2])
    # Local HLSL converts diffuse to linear, but samples MatCap without
    # srgb2linear. Its untagged raw intensity must therefore remain Non-Color.
    tree.links.new(add.outputs[0], bsdf.inputs["Base Color"])
    return {
        "material": mat.name,
        "authored_strength": strength,
        "multiplier": multiplier,
        "mask_channel": channel,
        "file": tex.image.name,
    }


def world_sky(scene, settings):
    world = bpy.data.worlds.new("Reference | cyan sky environment")
    world.use_nodes = True
    scene.world = world
    tree = world.node_tree
    bg = next(n for n in tree.nodes if n.type == "BACKGROUND")
    coord = tree.nodes.new("ShaderNodeTexCoord")
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 12
    noise.inputs["Detail"].default_value = 3
    noise.inputs["Roughness"].default_value = 0.65
    tree.links.new(coord.outputs["Generated"], noise.inputs["Vector"])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.48
    ramp.color_ramp.elements[0].color = tuple(settings["sky_dark"])
    ramp.color_ramp.elements[1].position = 0.67
    ramp.color_ramp.elements[1].color = tuple(settings["sky_cloud"])
    density = tree.nodes.new("ShaderNodeMapRange")
    density.clamp = True
    density.inputs["From Min"].default_value = 0.48
    density.inputs["From Max"].default_value = 0.67
    tree.links.new(noise.outputs["Fac"], density.inputs["Value"])
    sep = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(coord.outputs["Generated"], sep.inputs[0])
    horizon = tree.nodes.new("ShaderNodeMapRange")
    horizon.clamp = True
    horizon.inputs["From Min"].default_value = 0.05
    horizon.inputs["From Max"].default_value = 0.24
    horizon.inputs["To Min"].default_value = 1
    horizon.inputs["To Max"].default_value = 0
    tree.links.new(sep.outputs["Z"], horizon.inputs["Value"])
    clouds = math_node(
        tree,
        "Reference | horizon clouds",
        "MULTIPLY",
        density.outputs[0],
        horizon.outputs[0],
    )
    ramp.color_ramp.elements[0].position = 0
    ramp.color_ramp.elements[1].position = 1
    tree.links.new(clouds, ramp.inputs[0])
    tree.links.new(ramp.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = settings["world_strength"]


def curtain_submap(mat, folder):
    """The supplied curtain multiplies a rotating blue/purple sub-texture."""
    tree = mat.node_tree
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    defs, _values = ray_settings(folder / "mat_52.fx")
    if defs["ALBEDO_SUB_ENABLE"] != "1" or defs["ALBEDO_SUB_MAP_UV_FLIP"] != "5":
        raise ValueError("Review curtain sub-map algorithm")
    uv = tree.nodes.new("ShaderNodeTexCoord")
    mapping = tree.nodes.new("ShaderNodeMapping")
    mapping.vector_type = "POINT"
    center = tree.nodes.new("ShaderNodeVectorMath")
    center.operation = "ADD"
    center.inputs[1].default_value = (-0.5, -0.5, 0)
    tree.links.new(uv.outputs["UV"], center.inputs[0])
    tree.links.new(center.outputs[0], mapping.inputs["Vector"])
    # Phase zero of the original rotation; author preview animation time unknown.
    driver = mapping.inputs["Rotation"].driver_add("default_value", 2).driver
    driver.expression = f"(frame-1)/60*{0.03 * 2 * math.pi}"
    restore = tree.nodes.new("ShaderNodeVectorMath")
    restore.operation = "ADD"
    restore.inputs[1].default_value = (0.5, 0.5, 0)
    tree.links.new(mapping.outputs[0], restore.inputs[0])
    repeat = tree.nodes.new("ShaderNodeVectorMath")
    repeat.operation = "SCALE"
    repeat.inputs[3].default_value = 2
    tree.links.new(restore.outputs[0], repeat.inputs[0])
    tex = texture_node(tree, folder, defs["ALBEDO_SUB_MAP_FILE"], True)
    tree.links.new(repeat.outputs[0], tex.inputs["Vector"])
    gain = tree.nodes.new("ShaderNodeVectorMath")
    gain.operation = "SCALE"
    gain.inputs[3].default_value = constant(
        (folder / "mat_52.fx").read_text(encoding="utf-8-sig"), "albedoSub"
    )
    tree.links.new(tex.outputs[0], gain.inputs[0])
    mul = tree.nodes.new("ShaderNodeMixRGB")
    mul.name, mul.blend_type = "Reference | authored curtain sub-map", "MULTIPLY"
    mul.inputs[0].default_value = 1
    tree.links.new(bsdf.inputs["Base Color"].links[0].from_socket, mul.inputs[1])
    tree.links.new(gain.outputs[0], mul.inputs[2])
    tree.links.new(mul.outputs[0], bsdf.inputs["Base Color"])


def tone_based(mat, folder, settings):
    """Adapt the verified nl*hardness+1-hardness response, retain real GGX.

    The diffuse uses an estimated directional environment and local AO, not
    Ray's unavailable shadow maps, Fresnel energy integration or IBL solver.
    """
    fx = folder / (mat.name + ".fx")
    if not fx.is_file() or mat.name in {"mat_89", "mat_103", "mat_115"}:
        return None
    defs, values = ray_settings(fx)
    if defs.get("CUSTOM_ENABLE") != "9":
        raise ValueError("Review non-ToonBased stage material: " + mat.name)
    hardness = values["customA"]
    if defs.get("CUSTOM_A_MAP_COLOR_FLIP") == "1":
        hardness = 1 - hardness
    tree = mat.node_tree
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    original_pbr = tree.nodes.new("ShaderNodeBsdfPrincipled")
    original_pbr.name = "Reference | ordinary PBR control"
    for src, dest in zip(bsdf.inputs, original_pbr.inputs):
        if src.is_linked:
            tree.links.new(src.links[0].from_socket, dest)
        elif hasattr(src, "default_value"):
            dest.default_value = src.default_value
    output = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL")
    color = bsdf.inputs["Base Color"].links[0].from_socket
    normal = (
        bsdf.inputs["Normal"].links[0].from_socket
        if bsdf.inputs["Normal"].is_linked
        else tree.nodes.new("ShaderNodeNewGeometry").outputs["Normal"]
    )
    metal = (
        bsdf.inputs["Metallic"].links[0].from_socket
        if bsdf.inputs["Metallic"].is_linked
        else bsdf.inputs["Metallic"].default_value
    )
    dot = tree.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = (0.35, -0.45, 0.82)
    tree.links.new(normal, dot.inputs[0])
    response = math_node(
        tree,
        "Reference | ToonBased hardness",
        "MULTIPLY_ADD",
        dot.outputs["Value"],
        hardness,
    )
    response.node.inputs[2].default_value = 1 - hardness
    response.node.use_clamp = True
    shade = tree.nodes.new("ShaderNodeMixRGB")
    shade.name = "Reference | authored ToonBased shadow color"
    tree.links.new(response, shade.inputs[0])
    shade.inputs[1].default_value = (0.85**2.2,) * 3 + (1,)
    shade.inputs[2].default_value = (1, 1, 1, 1)
    mul = tree.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1
    tree.links.new(color, mul.inputs[1])
    tree.links.new(shade.outputs[0], mul.inputs[2])
    palette = tree.nodes.new("ShaderNodeMixRGB")
    palette.blend_type = "MULTIPLY"
    palette.inputs[0].default_value = 1
    palette.inputs[2].default_value = tuple(
        settings.get("material_diffuse_tints", {}).get(
            mat.name, settings["diffuse_tint"]
        )
    )
    tree.links.new(mul.outputs[0], palette.inputs[1])
    inv = math_node(tree, "Reference | diffuse conservation", "SUBTRACT", 1, metal)
    emission = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(palette.outputs[0], emission.inputs[0])
    tree.links.new(inv, emission.inputs[1])
    spec = tree.nodes.new("ShaderNodeMixRGB")
    spec.name = "Reference | dielectric-metal F0"
    if isinstance(metal, (int, float)):
        spec.inputs[0].default_value = metal
    else:
        tree.links.new(metal, spec.inputs[0])
    spec.inputs[1].default_value = (0.04, 0.04, 0.04, 1)
    tree.links.new(color, spec.inputs[2])
    # The local custom-material G-buffer stores specular luminance, not RGB F0.
    neutral = tree.nodes.new("ShaderNodeRGBToBW")
    tree.links.new(spec.outputs[0], neutral.inputs[0])
    tree.links.new(neutral.outputs[0], bsdf.inputs["Base Color"])
    for link in list(bsdf.inputs["Metallic"].links):
        tree.links.remove(link)
    bsdf.inputs["Metallic"].default_value = 1
    alpha = (
        bsdf.inputs["Alpha"].links[0].from_socket
        if bsdf.inputs["Alpha"].is_linked
        else None
    )
    for link in list(bsdf.inputs["Alpha"].links):
        tree.links.remove(link)
    bsdf.inputs["Alpha"].default_value = 1
    add = tree.nodes.new("ShaderNodeAddShader")
    tree.links.new(emission.outputs[0], add.inputs[0])
    tree.links.new(bsdf.outputs[0], add.inputs[1])
    surface = add.outputs[0]
    if alpha:
        mix = tree.nodes.new("ShaderNodeMixShader")
        tree.links.new(alpha, mix.inputs[0])
        tree.links.new(
            tree.nodes.new("ShaderNodeBsdfTransparent").outputs[0], mix.inputs[1]
        )
        tree.links.new(surface, mix.inputs[2])
        surface = mix.outputs[0]
    choice = tree.nodes.new("ShaderNodeMixShader")
    choice.name = "Reference | ToonBased vs ordinary PBR"
    choice.inputs[0].default_value = 1
    tree.links.new(original_pbr.outputs[0], choice.inputs[1])
    tree.links.new(surface, choice.inputs[2])
    tree.links.new(choice.outputs[0], output.inputs["Surface"])
    return {
        "material": mat.name,
        "custom_enable": 9,
        "hardness": hardness,
        "shadow_color_srgb": [0.85] * 3,
        "approximation": "estimated directional diffuse plus EEVEE GGX; not full Ray shadow/IBL",
    }


def stage_grade(scene, settings):
    if not settings.get("grade_curves"):
        return None
    tree = scene.compositing_node_group
    output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    previous = output.inputs["Image"].links[0].from_socket
    node = tree.nodes.new("CompositorNodeCurveRGB")
    node.name = "Reference | stage-only reference grade"
    node.mapping.initialize()
    for curve, points in zip(node.mapping.curves[:3], settings["grade_curves"]):
        curve.points[0].location = points[0]
        curve.points[-1].location = points[-1]
        for x, y in points[1:-1]:
            curve.points.new(x, y)
        for point in curve.points:
            point.handle_type = "VECTOR"
    node.mapping.update()
    tree.links.new(previous, node.inputs["Image"])
    tree.links.new(node.outputs["Image"], output.inputs["Image"])
    return node


def motes(scene, count):
    rng = random.Random(542)
    for index, color in enumerate([(1, 0.66, 0.32, 1), (0.55, 0.78, 1, 1)]):
        bm = bmesh.new()
        for _ in range(count // 2):
            position = (
                rng.uniform(-15, 15),
                rng.uniform(-44, 43),
                rng.uniform(0.5, 30),
            )
            bmesh.ops.create_icosphere(
                bm,
                subdivisions=1,
                radius=rng.uniform(0.008, 0.027),
                matrix=Matrix.Translation(position),
            )
        mesh = bpy.data.meshes.new("Reference | dust geometry")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new("Reference | spatial light motes", mesh)
        scene.collection.objects.link(obj)
        mat = bpy.data.materials.new(
            "Reference | warm motes" if index == 0 else "Reference | cool motes"
        )
        mat.use_nodes = True
        tree = mat.node_tree
        tree.nodes.clear()
        emission = tree.nodes.new("ShaderNodeEmission")
        emission.inputs[0].default_value = color
        emission.inputs[1].default_value = 5
        output = tree.nodes.new("ShaderNodeOutputMaterial")
        tree.links.new(emission.outputs[0], output.inputs["Surface"])
        mesh.materials.append(mat)


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--camera", type=Path)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--controls", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    source = Path(bpy.data.filepath)
    scene = bpy.context.scene
    if any(obj.type == "CAMERA" for obj in scene.objects) or len(scene.objects) != 103:
        raise RuntimeError(
            "This reconstruction requires the untouched 103-object author stage"
        )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    settings = json.loads(args.preset.read_text(encoding="utf-8"))
    pose = (
        json.loads(args.camera.read_text(encoding="utf-8"))
        if args.camera
        else settings["reference_camera_estimate"]
    )
    folder = source.parent / "textures"
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = args.samples
    scene.eevee.use_raytracing = True
    scene.eevee.ray_tracing_method = "SCREEN"
    scene.eevee.shadow_ray_count = 3
    scene.eevee.shadow_pool_size = "1024"
    scene.eevee.fast_gi_quality = 0.75
    scene.eevee.fast_gi_step_count = 16
    scene.render.resolution_x, scene.render.resolution_y = (
        args.width,
        round(args.width * 9 / 16),
    )
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "16"
    scene.render.use_sequencer = False
    scene.render.use_compositing = True
    scene.view_settings.view_transform = settings["view_transform"]
    scene.view_settings.look = settings["look"]
    scene.view_settings.exposure = settings["exposure"]
    for obj in scene.objects:
        if obj.type == "MESH" and any(
            m and m.name == "mat_103" for m in obj.data.materials
        ):
            obj.hide_render = True
    material_settings = {
        "normal_strength": 1,
        "architecture_tint": [1, 1, 1, 1],
        "bench_tint": [1, 1, 1, 1],
        "local_ao_distance": settings.get("ao_distance", 0.2),
        "local_ao_strength": settings["ao_strength"],
        "roughness_minimum": 0.05,
        "fabric_roughness_minimum": 0.35,
        "window_mode": "transparent_without_glints",
    }
    materials = rebuild_materials(folder, material_settings)
    curtain_submap(bpy.data.materials["mat_52"], folder)
    caps = [
        row
        for mat in list(bpy.data.materials)
        if (row := matcap(mat, folder, settings["matcap_multiplier"]))
    ]
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        bsdf = next(
            (n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None
        )
        if bsdf:
            bsdf.inputs["Specular IOR Level"].default_value = 0.5
    tones = [
        row
        for mat in list(bpy.data.materials)
        if (row := tone_based(mat, folder, settings))
    ]
    scene.render.fps = 60
    scene.frame_set(1)
    for item in settings["lights"]:
        light = area(
            "Reference | " + item["name"],
            item["location"],
            item["target"],
            item["watts"],
            item["color"],
            item["size"],
        )
        if "height" in item:
            light.data.shape = "RECTANGLE"
            light.data.size_y = item["height"]
    world_sky(scene, settings)
    camera_data = bpy.data.cameras.new("Reference | fitted camera")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    camera.matrix_world = Matrix(pose["camera_to_world_blender"])
    camera_data.lens = pose["lens_mm"]
    camera_data.sensor_width = 36
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.clip_end = 300
    scene.camera = camera
    compositor(scene, settings)
    grade = stage_grade(scene, settings)
    start = time.perf_counter()
    atmosphere_report = atmosphere(
        scene,
        {
            "candle_watts": settings["candle_watts"],
            "probe_resolution": [6, 12, 6],
            "probe_bake_samples": 128,
            "volume_density": 0,
        },
    )
    plane = bpy.data.lightprobes.new("Reference | floor planar reflection", "PLANE")
    plane.influence_distance = 3
    obj = bpy.data.objects.new(plane.name, plane)
    scene.collection.objects.link(obj)
    obj.location = (0, -5, 0.025)
    obj.scale = (16, 43, 1)
    motes(scene, settings.get("mote_count", 0))
    bpy.context.view_layer.update()
    scene.render.filepath = str(args.output_dir / "reference-rebuild.png")
    bpy.ops.render.render(write_still=True)
    if args.controls:
        obj.hide_render = True
        scene.eevee.use_raytracing = False
        scene.render.filepath = str(args.output_dir / "control-no-raytracing.png")
        bpy.ops.render.render(write_still=True)
        obj.hide_render = False
        scene.eevee.use_raytracing = True
        switches = [
            m.node_tree.nodes.get("Reference | ToonBased vs ordinary PBR")
            for m in bpy.data.materials
            if m.node_tree
        ]
        switches = [n for n in switches if n]
        for node in switches:
            node.inputs[0].default_value = 0
        scene.render.filepath = str(args.output_dir / "control-ordinary-pbr.png")
        bpy.ops.render.render(write_still=True)
        for node in switches:
            node.inputs[0].default_value = 1
        factors = [
            m.node_tree.nodes.get("Reference | authored MatCap intensity")
            for m in bpy.data.materials
            if m.node_tree
        ]
        factors = [n for n in factors if n]
        strengths = [n.inputs[1].default_value for n in factors]
        for node in factors:
            node.inputs[1].default_value = 0
        scene.render.filepath = str(args.output_dir / "control-no-matcap.png")
        bpy.ops.render.render(write_still=True)
        for node, strength in zip(factors, strengths):
            node.inputs[1].default_value = strength
        if grade:
            grade.inputs["Fac"].default_value = 0
            scene.render.filepath = str(args.output_dir / "control-no-grade.png")
            bpy.ops.render.render(write_still=True)
            grade.inputs["Fac"].default_value = 1
    scene.render.filepath = str(args.output_dir / "reference-rebuild.png")
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(
        filepath=str(args.output_dir / "Hesperides_Reference_Rebuild.blend")
    )
    report = {
        "source": str(source),
        "stage_only": True,
        "camera_estimate": pose,
        "materials": materials,
        "matcaps": caps,
        "toon_based_materials": tones,
        "settings": settings,
        "atmosphere": atmosphere_report,
        "raytracing": True,
        "raytracing_method": "SCREEN",
        "planar_probe": True,
        "image_size": [scene.render.resolution_x, scene.render.resolution_y],
        "elapsed_seconds": time.perf_counter() - start,
        "original_author_lighting_recovered": False,
        "limitations": [
            "ToonBased diffuse and GGX approximate the original HLSL/G-buffer; not a full Ray port",
            "Procedural sky and estimated lights replace unavailable author setup",
            "Stage-only study; character integration and animation remain separate",
        ],
    }
    (args.output_dir / "rebuild-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("REFERENCE_REBUILD_COMPLETE", round(report["elapsed_seconds"], 2), flush=True)


if __name__ == "__main__":
    main()
