"""Add wedding shafts, luminous aisle accents and isolated highlight halos."""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_fox_stageart import air_volume
from stage_night_art_lab import mix, spot
from verify_duet_integration import snapshot


def halos(scene, config):
    tree = scene.compositing_node_group
    output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    previous = output.inputs["Image"].links[0].from_socket
    render = next(
        n for n in tree.nodes if n.type == "R_LAYERS" and n.outputs.get("StageArtRim")
    )
    actor = render.outputs["ReferenceDuetActor"]
    inverse = tree.nodes.new("ShaderNodeMath")
    inverse.operation = "SUBTRACT"
    inverse.inputs[0].default_value = 1
    tree.links.new(actor, inverse.inputs[1])
    nodes = []
    for label, spec, image in [
        (
            "stage",
            config["stage_glow"],
            mix(tree, "MULTIPLY", render.outputs["Image"], inverse.outputs[0]),
        ),
        ("actor", config["actor_glow"], render.outputs["StageArtRim"]),
    ]:
        glare = tree.nodes.new("CompositorNodeGlare")
        glare.name = "Wedding | " + label + " halo"
        for name, value in [
            ("Type", "Fog Glow"),
            ("Quality", "High"),
            ("Threshold", spec["threshold"]),
            ("Strength", spec["strength"]),
            ("Size", spec["size"]),
        ]:
            glare.inputs[name].default_value = value
        tree.links.new(image, glare.inputs["Image"])
        contribution = glare.outputs["Glare"]
        if label == "stage":
            contribution = mix(tree, "MULTIPLY", contribution, inverse.outputs[0])
        previous = mix(tree, "ADD", previous, contribution)
        previous.node.name = "Wedding | add " + label + " halo"
        nodes.append(glare)
    tree.links.new(previous, output.inputs["Image"])
    # Cache and final image must use the same new composited beauty.
    beauty = tree.nodes["Caption cache | beauty"]
    tree.links.new(previous, beauty.inputs["beauty"])
    return nodes


def aisle(scene, spec):
    material = bpy.data.materials.new("Wedding | champagne fairy lights")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = spec["color"]
    emission.inputs["Strength"].default_value = spec["strength"]
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(emission.outputs[0], output.inputs["Surface"])
    names = []
    for side in (-1, 1):
        for y in spec["ys"]:
            bpy.ops.mesh.primitive_uv_sphere_add(
                segments=12,
                ring_count=8,
                radius=spec["radius"],
                location=(side * spec["x"], y, spec["z"]),
            )
            obj = bpy.context.object
            obj.name = f"Wedding | aisle light {side} {y}"
            obj.data.materials.append(material)
            names.append(obj.name)
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.preset.read_text(encoding="utf-8"))
    scene, source = bpy.context.scene, bpy.data.filepath
    assert scene.get(
        "soft_top_revision"
    ) == "hesperides-soft-top-rim-v1" and not scene.get("wedding_revision")
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    checks = {}
    for number in (1, 2100, 4140, 4200, 4250, 4290, 4439, 8400, 11899):
        scene.frame_set(number)
        checks[number] = snapshot(scene)
    old_air = scene.objects["Stage art | rear air only"]
    old_air.hide_render = True
    for obj in scene.objects:
        if obj.type == "LIGHT":
            obj.data.volume_factor = 0
    air = air_volume(scene, config["rear_air"])
    air.name = "Wedding | bounded rear scattering"
    lights = []
    for spec in config["spots"]:
        light = spot(scene, "Wedding | " + spec["name"], spec)
        light.data.shadow_soft_size = 0.12
        light.data.volume_factor = spec.get("volume_factor", 1)
        light.data.diffuse_factor = spec.get("diffuse_factor", 1)
        light.data.specular_factor = spec.get("specular_factor", 1)
        lights.append(light)
    accents = aisle(scene, config["aisle_lights"])
    glow = halos(scene, config)
    hidden = [(o, o.hide_render) for o in scene.objects if o.get("performer_id")]
    for obj, _ in hidden:
        obj.hide_render = True
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    probe = next(
        o for o in scene.objects if o.type == "LIGHT_PROBE" and o.data.type == "VOLUME"
    )
    probe.select_set(True)
    bpy.context.view_layer.objects.active = probe
    assert bpy.ops.object.lightprobe_cache_bake(subset="SELECTED") == {"FINISHED"}
    for obj, value in hidden:
        obj.hide_render = value
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = 67

    def render(number, name):
        scene.frame_set(number)
        scene.render.filepath = str(args.output_dir / name)
        bpy.ops.render.render(write_still=True)

    for number in (4200, 4250, 4290):
        render(number, f"wedding-{number}.png")
    air.hide_render = True
    render(4250, "control-scattering-off-4250.png")
    air.hide_render = False
    for node in glow:
        node.inputs["Strength"].default_value = 0
    render(4290, "control-new-halos-off-4290.png")
    for node, key in zip(glow, ("stage_glow", "actor_glow")):
        node.inputs["Strength"].default_value = config[key]["strength"]
    for number, expected in checks.items():
        scene.frame_set(number)
        assert snapshot(scene) == expected, number
    scene.frame_set(4140)
    scene.render.resolution_percentage = 100
    scene["wedding_revision"] = config["id"]
    bpy.ops.file.pack_all()
    target = args.output_dir / "Franken_Duet_Blue_Gold_Wedding.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    report = {
        "source": source,
        "project": str(target),
        "settings": config,
        "pose_camera_lens_unchanged_frames": list(checks),
        "aisle_accents": accents,
        "beam_lights": [o.name for o in lights],
        "volume_bounds_y": [
            config["rear_air"]["center"][1] - config["rear_air"]["scale"][1],
            config["rear_air"]["center"][1] + config["rear_air"]["scale"][1],
        ],
        "caption_cache_beauty_rewired": True,
        "all_file_outputs_saved_muted": True,
        "three_point_rig": [
            {"name": o.name, "watts": o.data.energy, "position": list(o.location)}
            for o in scene.objects
            if o.type == "LIGHT" and o.name.startswith("Reference duet |")
        ],
        "volume_settings": {
            p.identifier: str(getattr(scene.eevee, p.identifier))
            for p in scene.eevee.bl_rna.properties
            if "volum" in p.identifier
        },
    }
    (args.output_dir / "wedding-preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("BLUE_GOLD_WEDDING_READY", flush=True)


if __name__ == "__main__":
    main()
