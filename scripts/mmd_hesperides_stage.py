"""Adapt Hesperides' supplied Ray texture controls to Blender and render QA.

Open the author's blend with --disable-autoexec. This reads local .fx files as
text only; it does not execute HLSL or reproduce Ray's complete rendering pipe.
"""

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector


def ray_settings(path):
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    defines = dict(re.findall(r"^#define\s+(\w+)\s+([^\r\n/]+)", text, re.MULTILINE))
    constants = dict(re.findall(r"const\s+float\s+(\w+)\s*=\s*([0-9.eE+-]+)\s*;", text))
    return {k: v.strip().strip('"') for k, v in defines.items()}, {
        k: float(v) for k, v in constants.items()
    }


def math_node(tree, name, operation, first=None, second=None):
    node = tree.nodes.new("ShaderNodeMath")
    node.name = name
    node.operation = operation
    for i, value in enumerate((first, second)):
        if value is not None:
            if isinstance(value, (int, float)):
                node.inputs[i].default_value = value
            else:
                tree.links.new(value, node.inputs[i])
    return node.outputs[0]


def texture_node(tree, folder, name, data=False):
    path = folder / name
    if not path.is_file():
        raise FileNotFoundError(path)
    image = bpy.data.images.load(str(path), check_existing=True)
    image.colorspace_settings.name = "Non-Color" if data else "sRGB"
    node = tree.nodes.new("ShaderNodeTexImage")
    node.name = "Stage | " + name
    node.image = image
    return node


def rebuild_materials(folder, settings):
    report = []
    foliage = {"mat_13", "mat_14", "mat_54", "mat_55", "mat_61"}
    for mat in bpy.data.materials:
        fx = folder / (mat.name + ".fx")
        defs, values = ray_settings(fx) if fx.is_file() else ({}, {})
        tree = mat.node_tree
        bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
        item = {
            "material": mat.name,
            "ray_file": fx.name if fx.is_file() else None,
            "normal": False,
            "smoothness": False,
            "metalness": False,
        }
        mat["stage_id"] = "hesperides_hall"
        bsdf.inputs["Roughness"].default_value = 0.65
        bsdf.inputs["Metallic"].default_value = 0
        bsdf.inputs["Specular IOR Level"].default_value = 0.35
        if mat.name not in foliage | {"mat_103", "mat_115", "mat_52", "mat_89"}:
            # Local art direction, not values attributed to the supplied Ray file.
            original = bsdf.inputs["Base Color"].links[0].from_socket
            tint = tree.nodes.new("ShaderNodeMixRGB")
            tint.name = "Stage | winter stone palette"
            tint.blend_type = "MULTIPLY"
            tint.inputs[0].default_value = 1
            tint.inputs[2].default_value = (
                settings["bench_tint"]
                if mat.name == "mat_51"
                else settings["architecture_tint"]
            )
            tree.links.new(original, tint.inputs[1])
            ao = tree.nodes.new("ShaderNodeAmbientOcclusion")
            ao.name = "Stage | shallow contact definition"
            ao.inputs["Distance"].default_value = settings["local_ao_distance"]
            contact = tree.nodes.new("ShaderNodeMixRGB")
            contact.blend_type = "MULTIPLY"
            contact.inputs[0].default_value = settings["local_ao_strength"]
            tree.links.new(tint.outputs[0], contact.inputs[1])
            tree.links.new(ao.outputs["AO"], contact.inputs[2])
            tree.links.new(contact.outputs[0], bsdf.inputs["Base Color"])
            item["art_directed_tint"] = list(tint.inputs[2].default_value)
            item["local_ao_strength"] = settings["local_ao_strength"]
        if defs.get("NORMAL_MAP_FROM") == "1":
            tex = texture_node(tree, folder, defs["NORMAL_MAP_FILE"], True)
            normal = tree.nodes.new("ShaderNodeNormalMap")
            normal.name = "Stage | authored tangent normal"
            normal.inputs["Strength"].default_value = settings["normal_strength"]
            tree.links.new(tex.outputs["Color"], normal.inputs["Color"])
            tree.links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
            item["normal"] = True
        if defs.get("SMOOTHNESS_MAP_FROM") == "1":
            tex = texture_node(tree, folder, defs["SMOOTHNESS_MAP_FILE"], True)
            sep = tree.nodes.new("ShaderNodeSeparateColor")
            tree.links.new(tex.outputs["Color"], sep.inputs[0])
            channel = int(defs.get("SMOOTHNESS_MAP_SWIZZLE", "0"))
            smooth = sep.outputs[channel] if channel < 3 else tex.outputs["Alpha"]
            if defs.get("SMOOTHNESS_MAP_TYPE", "0") != "0":
                raise ValueError(
                    "Review unsupported smoothness conversion: " + mat.name
                )
            if defs.get("SMOOTHNESS_MAP_APPLY_SCALE") == "1":
                smooth = math_node(
                    tree,
                    "Stage | smoothness multiplier",
                    "MULTIPLY",
                    smooth,
                    values.get("smoothness", 1),
                )
            rough = math_node(
                tree, "Stage | one minus smoothness", "SUBTRACT", 1, smooth
            )
            minimum = (
                settings["fabric_roughness_minimum"]
                if mat.name in foliage or mat.name == "mat_52"
                else settings["roughness_minimum"]
            )
            rough = math_node(
                tree, "Stage | roughness floor", "MAXIMUM", rough, minimum
            )
            tree.links.new(rough, bsdf.inputs["Roughness"])
            item["smoothness"] = True
        if (
            defs.get("METALNESS_MAP_FROM") == "1"
            and mat.name not in foliage
            and mat.name != "mat_52"
        ):
            tex = texture_node(tree, folder, defs["METALNESS_MAP_FILE"], True)
            sep = tree.nodes.new("ShaderNodeSeparateColor")
            tree.links.new(tex.outputs["Color"], sep.inputs[0])
            channel = int(defs.get("METALNESS_MAP_SWIZZLE", "0"))
            metal = sep.outputs[channel] if channel < 3 else tex.outputs["Alpha"]
            if defs.get("METALNESS_MAP_APPLY_SCALE") == "1":
                metal = math_node(
                    tree,
                    "Stage | authored metal multiplier",
                    "MULTIPLY",
                    metal,
                    values.get("metalness", 1),
                )
            tree.links.new(metal, bsdf.inputs["Metallic"])
            item["metalness"] = True
        if mat.name in foliage:
            mat.surface_render_method = "DITHERED"
            mat.use_backface_culling = False
            bsdf.inputs["Subsurface Weight"].default_value = 0.025
        if mat.name == "mat_52":
            bsdf.inputs["Sheen Weight"].default_value = 0.18
        if mat.name == "mat_89":
            # The package provides no window texture. A transparent closure avoids
            # alpha dithering noise; this intentionally omits glass reflections.
            output = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL")
            transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
            tree.links.new(transparent.outputs[0], output.inputs["Surface"])
            item["window_mode"] = settings["window_mode"]
        if defs.get("EMISSIVE_ENABLE") == "1":
            tex = texture_node(tree, folder, defs["EMISSIVE_MAP_FILE"])
            tree.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = values.get(
                "emissiveIntensity", 1
            )
            item["emission_strength"] = bsdf.inputs["Emission Strength"].default_value
        report.append(item)
    return report


def aim(obj, target):
    obj.rotation_euler = (
        (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    )


def area(name, location, target, energy, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.shape, data.size = energy, color, "DISK", size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def lighting(scene, settings, flat=False):
    for obj in list(scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)
        elif obj.type == "MESH" and any(
            m and m.name == "mat_103" for m in obj.data.materials
        ):
            obj.hide_render = True
    if flat:
        area(
            "Hall | flat window key",
            (-12, 8, 19),
            (0, 12, 0),
            30000,
            (0.72, 0.83, 1),
            14,
        )
        area(
            "Hall | flat window fill",
            (12, -5, 13),
            (0, 5, 0),
            22000,
            (1, 0.88, 0.75),
            12,
        )
        area(
            "Hall | flat altar glow", (0, 35, 12), (0, 22, 2), 18000, (0.75, 0.83, 1), 9
        )
        area(
            "Hall | flat front bounce",
            (0, -22, 12),
            (0, 10, 4),
            18000,
            (0.8, 0.85, 1),
            15,
        )
    else:
        for light in settings["lights"]:
            area(
                "Hall | " + light["name"],
                light["location"],
                light["target"],
                light["watts"],
                light["color"],
                light["size"],
            )
    world = bpy.data.worlds.new("Hall | cold sky")
    world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    nodes, links = world.node_tree.nodes, world.node_tree.links
    coordinates = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coordinates.outputs["Normal"], separate.inputs[0])
    mapping = nodes.new("ShaderNodeMapRange")
    mapping.inputs["From Min"].default_value = -0.3
    mapping.inputs["From Max"].default_value = 0.7
    links.new(separate.outputs["Z"], mapping.inputs["Value"])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.13, 0.29, 0.52, 1)
    ramp.color_ramp.elements[1].color = (0.025, 0.07, 0.19, 1)
    links.new(mapping.outputs["Result"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], background.inputs["Color"])
    background.inputs["Strength"].default_value = settings["world_strength"]
    scene.world = world
    view = settings["cameras"][0]
    bpy.ops.object.camera_add(location=view["location"])
    camera = bpy.context.object
    camera.name = "Hall | scene-study camera"
    camera.data.lens = view["lens"]
    camera.data.clip_end = 1000
    aim(camera, view["target"])
    scene.camera = camera
    return camera


def compositor(scene, settings):
    tree = bpy.data.node_groups.new(
        "Hall | restrained highlight bloom", "CompositorNodeTree"
    )
    scene.compositing_node_group = tree
    tree.interface.new_socket(
        name="Image", in_out="OUTPUT", socket_type="NodeSocketColor"
    )
    render = tree.nodes.new("CompositorNodeRLayers")
    render.scene = scene
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Fog Glow"
    glare.inputs["Quality"].default_value = "High"
    glare.inputs["Threshold"].default_value = settings["bloom"]["threshold"]
    glare.inputs["Strength"].default_value = settings["bloom"]["strength"]
    glare.inputs["Size"].default_value = settings["bloom"]["size"]
    tree.links.new(render.outputs["Image"], glare.inputs["Image"])
    output = tree.nodes.new("NodeGroupOutput")
    tree.links.new(glare.outputs["Image"], output.inputs["Image"])


def atmosphere(scene, settings):
    # Small lights are derived from the flame polygons, not arbitrary empty space.
    groups = defaultdict(list)
    for obj in list(scene.objects):
        if obj.type != "MESH" or obj.hide_render:
            continue
        for face in obj.data.polygons:
            if obj.data.materials[face.material_index].name != "mat_115":
                continue
            position = obj.matrix_world @ face.center
            key = tuple(round(v / 2) for v in position)
            groups[key].append(position)
    candle_positions = []
    for positions in groups.values():
        center = sum(positions, Vector()) / len(positions)
        if center.z > 12 or abs(center.x) > 20 or not -55 < center.y < 45:
            continue
        data = bpy.data.lights.new("Hall | warm candle", "POINT")
        data.energy = settings["candle_watts"]
        data.color = (1, 0.4, 0.13)
        data.shadow_soft_size = 0.22
        obj = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(obj)
        obj.location = center
        candle_positions.append(list(center))
    probe = bpy.data.lightprobes.new("Hall | baked diffuse bounce", "VOLUME")
    probe.resolution_x, probe.resolution_y, probe.resolution_z = settings[
        "probe_resolution"
    ]
    probe.bake_samples = settings["probe_bake_samples"]
    probe.surfel_density = 8
    probe.capture_world = True
    probe.capture_distance = 100
    obj = bpy.data.objects.new(probe.name, probe)
    scene.collection.objects.link(obj)
    obj.location = (0, -5, 16)
    obj.scale = (18, 45, 16)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    print("HALL_PROBE_BAKE_START", flush=True)
    result = bpy.ops.object.lightprobe_cache_bake(subset="SELECTED")
    if "FINISHED" not in result:
        raise RuntimeError("Light probe bake failed: " + str(result))
    print("HALL_PROBE_BAKE_DONE", flush=True)
    reflection = bpy.data.lightprobes.new("Hall | interior reflection", "SPHERE")
    reflection.influence_distance = 65
    reflection.clip_end = 160
    obj = bpy.data.objects.new(reflection.name, reflection)
    scene.collection.objects.link(obj)
    obj.location = (0, -10, 8)
    if settings["volume_density"] > 0:
        bpy.ops.mesh.primitive_cube_add(size=2, location=(0, -5, 15))
        volume = bpy.context.object
        volume.name = "Hall | subtle winter air"
        volume.scale = (17, 43, 15)
        mat = bpy.data.materials.new(volume.name)
        mat.use_nodes = True
        mat.node_tree.nodes.clear()
        scatter = mat.node_tree.nodes.new("ShaderNodeVolumeScatter")
        scatter.inputs["Color"].default_value = (0.68, 0.79, 1, 1)
        scatter.inputs["Density"].default_value = settings["volume_density"]
        scatter.inputs["Anisotropy"].default_value = 0.35
        output = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(scatter.outputs[0], output.inputs["Volume"])
        volume.data.materials.append(mat)
        volume.display_type = "WIRE"
    return {
        "candle_lights": candle_positions,
        "diffuse_probe_baked": True,
        "reflection_probe": reflection.name,
        "volume_density": settings["volume_density"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument(
        "--preset",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "presets/stages/hesperides-winter-wedding-v1.json",
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    source = Path(bpy.data.filepath)
    settings = json.loads(args.preset.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = args.samples
    scene.eevee.use_raytracing = True
    scene.eevee.shadow_ray_count = 3
    scene.eevee.fast_gi_quality = 0.75
    scene.eevee.fast_gi_step_count = 16
    scene.render.resolution_x = args.width
    scene.render.resolution_y = round(args.width * 9 / 16)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = settings["look"]
    scene.view_settings.exposure = settings["exposure"]
    camera = lighting(scene, settings)
    compositor(scene, settings)
    start = time.time()
    scene.render.filepath = str(args.output_dir / "baseline.png")
    bpy.ops.render.render(write_still=True)
    materials = rebuild_materials(source.parent / "textures", settings)
    scene.render.filepath = str(args.output_dir / "material-refined.png")
    bpy.ops.render.render(write_still=True)
    atmosphere_report = atmosphere(scene, settings)
    scene.render.filepath = str(args.output_dir / "lighting-refined.png")
    bpy.ops.render.render(write_still=True)
    view = settings["cameras"][1]
    camera.location = view["location"]
    camera.data.lens = view["lens"]
    aim(camera, view["target"])
    scene.render.filepath = str(args.output_dir / "aisle-refined.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(
        filepath=str(args.output_dir / "hesperides-stage-refined.blend")
    )
    report = {
        "source": str(source),
        "engine": scene.render.engine,
        "materials": materials,
        "render_seconds": time.time() - start,
        "scope": "Scene material/lighting study; not a finished duet video",
        "not_ported": ["Ray HLSL pipeline", "screen-space MatCap addition"],
        "fake_light_planes_hidden": True,
        "preset": settings,
        "atmosphere": atmosphere_report,
        "color_management": scene.view_settings.view_transform,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    }
    (args.output_dir / "stage-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "HESPERIDES_STAGE_COMPLETE",
        json.dumps({k: v for k, v in report.items() if k != "materials"}),
        flush=True,
    )


if __name__ == "__main__":
    main()
