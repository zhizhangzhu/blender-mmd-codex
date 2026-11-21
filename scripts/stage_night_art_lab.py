"""Test moonlight, localized warmth and thin volume on a separate duet copy."""

import argparse
import json
import math
import sys
import warnings
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import aim, area, math_node
from verify_duet_integration import snapshot


def mix(tree, op, a, b, fac=1):
    node = tree.nodes.new("ShaderNodeMixRGB")
    node.blend_type = op
    node.inputs[0].default_value = fac
    for socket, value in zip(node.inputs[1:], [a, b]):
        if hasattr(value, "is_output"):
            tree.links.new(value, socket)
        else:
            socket.default_value = value
    return node.outputs[0]


def pool(tree, position, spec):
    dist = tree.nodes.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    tree.links.new(position, dist.inputs[0])
    dist.inputs[1].default_value = spec["center"]
    radius = math_node(
        tree, "Night | pool radius", "DIVIDE", dist.outputs["Value"], spec["radius"]
    )
    squared = math_node(
        tree, "Night | pool distance squared", "MULTIPLY", radius, radius
    )
    fade = math_node(
        tree,
        "Night | soft pool",
        "EXPONENT",
        math_node(tree, "Night | negative distance", "MULTIPLY", squared, -1),
    )
    return mix(tree, "MULTIPLY", spec["tint"], fade)


def surfaces(scene, settings):
    used = {
        m
        for o in scene.objects
        if o.type == "MESH" and not o.hide_render
        for m in o.data.materials
        if m and m.node_tree
    }
    changed = []
    for mat in used:
        tree = mat.node_tree
        emissions = [n for n in tree.nodes if n.type == "EMISSION"]
        if mat.get("stage_id") and emissions:
            position = tree.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
            illumination = mix(
                tree,
                "ADD",
                settings["ambient_tint"],
                pool(tree, position, settings["moon_pool"]),
            )
            illumination = mix(
                tree, "ADD", illumination, pool(tree, position, settings["altar_pool"])
            )
        elif mat.get("performer_id"):
            illumination = settings["actor_tint"]
        else:
            continue
        for emission in emissions:
            color = (
                emission.inputs[0].links[0].from_socket
                if emission.inputs[0].is_linked
                else tuple(emission.inputs[0].default_value)
            )
            tree.links.new(
                mix(tree, "MULTIPLY", color, illumination), emission.inputs[0]
            )
        changed.append(
            {
                "material": mat.name,
                "actor": mat.get("performer_id"),
                "emissions": len(emissions),
            }
        )
    return changed


def spot(scene, name, spec):
    data = bpy.data.lights.new(name, "SPOT")
    data.energy = spec["watts"]
    data.color = spec["color"]
    data.spot_size = math.radians(spec["angle_degrees"])
    data.spot_blend = spec["blend"]
    data.shadow_soft_size = 0.6
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = spec["location"]
    aim(obj, spec["target"])
    return obj


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    settings = json.loads(args.preset.read_text(encoding="utf-8"))
    source = bpy.data.filepath
    scene = bpy.context.scene
    scene.frame_set(4200)
    before = snapshot(scene)
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.render.filepath = str(args.output_dir / "baseline-4200.png")
    bpy.ops.render.render(write_still=True)
    changed = surfaces(scene, settings)
    for obj in scene.objects:
        if obj.type != "LIGHT" or obj.hide_render:
            continue
        if obj.name.startswith("Reference duet |"):
            obj.data.energy *= (
                0.8
                if obj.name.endswith(" | key")
                else 1.6
                if obj.name.endswith(" | rim")
                else 0.4
            )
            obj.data.color = (
                (1, 0.83, 0.73) if obj.name.endswith(" | key") else (0.35, 0.55, 1)
            )
        elif obj.data.type == "AREA":
            obj.hide_render = True
    area(
        "Night | broad moon window",
        location=settings["moon_area"]["location"],
        target=settings["moon_area"]["target"],
        energy=settings["moon_area"]["watts"],
        color=settings["moon_area"]["color"],
        size=settings["moon_area"]["size"],
    )
    spot(scene, "Night | moon shaft", settings["moon_spot"])
    spot(scene, "Night | warm altar", settings["altar_spot"])
    world = scene.world.node_tree
    sky = next(n for n in world.nodes if n.type == "VALTORGB")
    sky.color_ramp.elements[0].color = settings["sky_dark"]
    sky.color_ramp.elements[-1].color = settings["sky_cloud"]
    next(n for n in world.nodes if n.type == "BACKGROUND").inputs[
        "Strength"
    ].default_value = 1
    grade = scene.compositing_node_group.nodes.get(
        "Reference | stage-only reference grade"
    )
    if grade:
        grade.inputs["Fac"].default_value = 0
    hidden = [
        (o, o.hide_render)
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id")
    ]
    for obj, _value in hidden:
        obj.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    probe = next(
        o for o in scene.objects if o.type == "LIGHT_PROBE" and o.data.type == "VOLUME"
    )
    probe.select_set(True)
    bpy.context.view_layer.objects.active = probe
    bpy.context.view_layer.update()
    assert bpy.ops.object.lightprobe_cache_bake(subset="SELECTED") == {"FINISHED"}
    for obj, value in hidden:
        obj.hide_render = value
    scene.render.filepath = str(args.output_dir / "night-no-volume-4200.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 14, 15))
    volume = bpy.context.object
    volume.name = "Night | localized cool air"
    volume.scale = (17, 43, 15)
    mat = bpy.data.materials.new(volume.name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    scatter = tree.nodes.new("ShaderNodeVolumeScatter")
    scatter.inputs["Color"].default_value = (0.55, 0.7, 1, 1)
    scatter.inputs["Density"].default_value = settings["volume_density"]
    scatter.inputs["Anisotropy"].default_value = settings["volume_anisotropy"]
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(scatter.outputs[0], output.inputs["Volume"])
    volume.data.materials.append(mat)
    scene.render.filepath = str(args.output_dir / "night-atmosphere-4200.png")
    bpy.ops.render.render(write_still=True)
    assert before == snapshot(scene), "Actor or camera changed"
    scene.frame_set(4420)
    scene.render.filepath = str(args.output_dir / "night-atmosphere-4420.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(
        filepath=str(args.output_dir / "Moonlit_Vows_Study.blend")
    )
    (args.output_dir / "study-report.json").write_text(
        json.dumps(
            {
                "source": source,
                "settings": settings,
                "changed_materials": changed,
                "actor_camera_unchanged_at_4200": True,
                "gi_rebaked_without_actors": True,
                "scope": "independent still study, not a replacement video",
                "limitations": "Spatial NPR pools have no occlusion; actual spots affect GGX and volume. Current accepted sample unchanged.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("NIGHT_ART_STUDY_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
