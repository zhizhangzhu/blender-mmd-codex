"""Create a fingerprint-bound, independently saved bold wedding-lighting revision."""

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage_night_art_lab import mix, spot
from verify_duet_integration import snapshot

PREFIX = "Bold wedding | "
FRAMES = [1, 2100, 4140, 4200, 4250, 4290, 4439, 8400, 11899]


def mute_outputs():
    for scene in bpy.data.scenes:
        if scene.compositing_node_group:
            for node in scene.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True


def add_aov(scene, name):
    for layer in scene.view_layers:
        if not layer.aovs.get(name):
            aov = layer.aovs.add()
            aov.name, aov.type = name, "COLOR"
        layer.update_render_passes()


def fx_material(name, color, strength):
    material = bpy.data.materials.new(PREFIX + name)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.name = PREFIX + "visible effect source"
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(emission.outputs[0], output.inputs["Surface"])
    scaled = tree.nodes.new("ShaderNodeVectorMath")
    scaled.operation = "SCALE"
    scaled.inputs[0].default_value = color[:3]
    scaled.inputs[3].default_value = strength
    aov = tree.nodes.new("ShaderNodeOutputAOV")
    aov.aov_name = "BoldWeddingFX"
    tree.links.new(scaled.outputs[0], aov.inputs["Color"])
    material["bold_wedding_fx"] = True
    return material


def effect_collection(scene):
    collection = bpy.data.collections.new(PREFIX + "light installations")
    scene.collection.children.link(collection)
    return collection


def link_effect(obj, collection):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)
    obj["bold_wedding_fx"] = True


def arcs(scene, collection, spec):
    names = []
    for side, label in [(-1, "blue"), (1, "gold")]:
        material = fx_material(label + " vow arc", spec[label], spec["strength"])
        curve = bpy.data.curves.new(PREFIX + label + " vow curve", "CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 2
        curve.bevel_depth = spec["thickness"]
        curve.bevel_resolution = 3
        spline = curve.splines.new("POLY")
        spline.points.add(160)
        # Open at the bottom: paired wedding-light arches rather than opaque scenery.
        for index, point in enumerate(spline.points):
            theta = math.radians(-20 + 220 * index / 160)
            point.co = (
                side * spec["offset_x"] + spec["radius_x"] * math.cos(theta),
                spec["y"] + side * 0.06,
                spec["z"] + spec["radius_z"] * math.sin(theta),
                1,
            )
        obj = bpy.data.objects.new(PREFIX + label + " vow arc", curve)
        collection.objects.link(obj)
        curve.materials.append(material)
        obj["bold_wedding_fx"] = True
        names.append(obj.name)
    return names


def particles(scene, collection, spec, arc_spec):
    rng = random.Random(spec["seed"])
    materials = [
        fx_material("floating " + color, arc_spec[color], spec["strength"])
        for color in ("blue", "gold")
    ]
    names = []
    for index in range(spec["count"]):
        x, y, z = rng.uniform(-3.0, 3.0), rng.uniform(2.8, 7.5), rng.uniform(0.2, 4.0)
        radius = rng.uniform(*spec["radius_range"])
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1, radius=radius, location=(x, y, z)
        )
        obj = bpy.context.object
        obj.name = PREFIX + f"floating vow {index:02d}"
        obj.data.materials.append(materials[index % 2])
        link_effect(obj, collection)
        phase = rng.uniform(0, 2 * math.pi)
        # Deterministic, slow motion driven by time; no simulation or random per-frame state.
        obj.driver_add(
            "location", 0
        ).driver.expression = f"{x:.9f}+0.08*sin(frame/60*0.65+{phase:.9f})"
        obj.driver_add(
            "location", 2
        ).driver.expression = f"{z:.9f}+0.12*sin(frame/60*0.48+{phase:.9f})"
        names.append(obj.name)
    return names


def beam_fans(scene, collection, spec):
    # A bounded scattering slab beginning behind the actors: never a world fog wash.
    material = bpy.data.materials.new(PREFIX + "rear beam scattering")
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    scatter = tree.nodes.new("ShaderNodeVolumeScatter")
    scatter.inputs["Color"].default_value = (0.82, 0.90, 1.0, 1.0)
    scatter.inputs["Density"].default_value = spec["density"]
    scatter.inputs["Anisotropy"].default_value = spec["anisotropy"]
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(scatter.outputs[0], output.inputs["Volume"])
    bpy.ops.mesh.primitive_cube_add(size=2, location=spec["center"])
    air = bpy.context.object
    air.name = PREFIX + "bounded beam fan air"
    air.scale = spec["scale"]
    air.data.materials.append(material)
    link_effect(air, collection)
    source_receivers = scene.objects[
        "Wedding | blue vow shaft"
    ].light_linking.receiver_collection
    assert source_receivers is not None
    source_members = list(source_receivers.all_objects)
    source_names = {obj.name for obj in source_members}
    receivers = bpy.data.collections.new(PREFIX + "beam receivers")
    # Keep the existing stage receiver collection unchanged. The new volume is
    # already visible through the scene's effect collection; this independent
    # collection only controls the six new lamps' illumination recipients.
    direct_members = list(source_receivers.objects)
    for obj in source_members:
        receivers.objects.link(obj)
        if obj in direct_members:
            source_index = direct_members.index(obj)
            receivers.collection_objects[
                len(receivers.objects) - 1
            ].light_linking.link_state = source_receivers.collection_objects[
                source_index
            ].light_linking.link_state
    receivers.objects.link(air)
    air_link = receivers.collection_objects[len(receivers.objects) - 1].light_linking
    air_link.link_state = "INCLUDE"
    assert air.name in collection.objects and air.name in receivers.objects
    assert air_link.link_state == "INCLUDE"
    assert {obj.name for obj in source_receivers.all_objects} == source_names
    lights = []
    for side, color in [(-1, "blue"), (1, "gold")]:
        for index in range(spec["count_per_side"]):
            point = (side * (2.15 + index * 0.16), 3.0 + index * 0.32, 0.18)
            target = Vector((side * (-0.9 + index * 0.9), 5.9 + index * 0.25, 5.2))
            lamp = spot(
                scene,
                PREFIX + f"{color} beam {index}",
                {
                    "location": point,
                    "target": target,
                    "watts": spec["watts"],
                    "color": spec[color],
                    "angle_degrees": spec["angle_degrees"],
                    "blend": 0.36,
                },
            )
            lamp.data.diffuse_factor = 0.10
            lamp.data.specular_factor = 0.25
            lamp.data.volume_factor = spec["volume_factor"]
            lamp.data.shadow_soft_size = 0.04
            lamp.data.use_shadow = True
            lamp.light_linking.receiver_collection = receivers
            lamp["bold_wedding_fx"] = True
            # Small periodic tilt gives motion without rapid flashes or light crossings on faces.
            base = lamp.rotation_euler.y
            phase = index * 0.8 + (0 if side < 0 else 1.4)
            sweep = spec["sweep_metres"] / (target - Vector(point)).length
            period = spec["sweep_period_seconds"]
            lamp.driver_add(
                "rotation_euler", 1
            ).driver.expression = f"{base:.9f}+{sweep:.9f}*sin(frame/60*{2 * math.pi / period:.9f}+{phase:.9f})"
            lights.append(lamp.name)
    return {
        "air": air.name,
        "lights": lights,
        "receiver_collection": receivers.name,
        "copied_stage_receiver_collection": source_receivers.name,
        "copied_stage_receiver_count": len(source_members),
        "air_effect_collection": collection.name,
        "air_link_state": air_link.link_state,
        "source_receiver_members_unchanged": True,
        "bounds_y": [
            spec["center"][1] - spec["scale"][1],
            spec["center"][1] + spec["scale"][1],
        ],
    }


def light_layers(scene, spec):
    changes = []
    for name, config in spec["stage_lights"].items():
        obj = scene.objects[name]
        old = {"energy": obj.data.energy, "color": list(obj.data.color)}
        obj.data.energy = config["energy"]
        if "color" in config:
            obj.data.color = config["color"]
        changes.append(
            {
                "name": name,
                "before": old,
                "after": {"energy": obj.data.energy, "color": list(obj.data.color)},
            }
        )
    for actor in ("aksiniya", "aether"):
        rim = scene.objects[f"Reference duet | {actor} | rim"]
        old = {"energy": rim.data.energy, "color": list(rim.data.color)}
        rim.data.energy = spec["actor_specular_rim"]["energy"]
        rim.data.color = spec["actor_specular_rim"][
            "gold" if actor == "aether" else "blue"
        ]
        assert rim.data.diffuse_factor == 0
        changes.append(
            {
                "name": rim.name,
                "before": old,
                "after": {"energy": rim.data.energy, "color": list(rim.data.color)},
            }
        )
    tree = scene.compositing_node_group
    hierarchy = tree.nodes[
        "Reference transfer | foreground hierarchy with actor protection"
    ]
    dim = hierarchy.inputs[2].links[0].from_node
    assert dim.type == "MIX_RGB" and dim.blend_type == "MULTIPLY"
    dim.inputs[2].default_value = (spec["foreground_gain"],) * 3 + (1,)
    # Keep the old broad halo restrained; new accessory/effect sources get separate selective halos.
    tree.nodes["Wedding | stage halo"].inputs["Strength"].default_value = 0.14
    tree.nodes["Wedding | actor halo"].inputs["Strength"].default_value = 0.34
    return changes


def selective_glow(scene, spec):
    bpy.context.view_layer.update()
    tree = scene.compositing_node_group
    output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    previous = output.inputs["Image"].links[0].from_socket
    render = next(
        n
        for n in tree.nodes
        if n.type == "R_LAYERS" and n.outputs.get("BoldWeddingEmission")
    )
    records = []
    for label, aov in [("actor", "BoldWeddingEmission"), ("fx", "BoldWeddingFX")]:
        settings = spec[label + "_glow"]
        glare = tree.nodes.new("CompositorNodeGlare")
        glare.name = PREFIX + label + " selective halo"
        for name, value in [
            ("Type", "Fog Glow"),
            ("Quality", "High"),
            ("Threshold", settings["threshold"]),
            ("Strength", settings["strength"]),
            ("Size", settings["size"]),
        ]:
            glare.inputs[name].default_value = value
        tree.links.new(render.outputs[aov], glare.inputs["Image"])
        contribution = glare.outputs["Glare"]
        if label == "fx":
            # Background light may bloom into silhouettes; protect most actor coverage for facial clarity.
            protection = tree.nodes.new("ShaderNodeMath")
            protection.name, protection.operation = (
                PREFIX + "actor halo protection",
                "MULTIPLY_ADD",
            )
            tree.links.new(render.outputs["ReferenceDuetActor"], protection.inputs[0])
            protection.inputs[1].default_value = -0.80
            protection.inputs[2].default_value = 1
            contribution = mix(tree, "MULTIPLY", contribution, protection.outputs[0])
        previous = mix(tree, "ADD", previous, contribution)
        previous.node.name = PREFIX + "add " + label + " selective halo"
        records.append({"node": glare.name, "aov": aov, "settings": settings})
    tree.links.new(previous, output.inputs["Image"])
    tree.links.new(previous, tree.nodes["Caption cache | beauty"].inputs["beauty"])
    return records


def bake_stage(scene):
    hidden = [(o, o.hide_render) for o in scene.objects if o.get("performer_id")]
    for obj, _ in hidden:
        obj.hide_render = True
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    probes = [
        o
        for o in scene.objects
        if o.type == "LIGHT_PROBE" and o.data.type == "VOLUME" and not o.hide_render
    ]
    assert len(probes) == 1
    probe = probes[0]
    probe.select_set(True)
    bpy.context.view_layer.objects.active = probe
    result = bpy.ops.object.lightprobe_cache_bake(subset="SELECTED")
    assert result == {"FINISHED"}
    for obj, previous in hidden:
        obj.hide_render = previous
    bpy.context.view_layer.update()
    return probe.name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--stills", type=int, nargs="*", default=[4250, 4290])
    parser.add_argument("--preview-percentage", type=int, default=67)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    spec = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    source = Path(bpy.data.filepath)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == spec["source_sha256"]
    scene = bpy.context.scene
    assert scene.get("reference_transfer_revision") == spec["input_revision"]
    assert not scene.get("bold_wedding_revision")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    mute_outputs()
    before = {}
    for frame in FRAMES:
        scene.frame_set(frame)
        before[frame] = snapshot(scene)
    scene.frame_set(4200)
    bpy.context.view_layer.update()
    from bold_wedding_materials import apply_bold_materials

    material_spec = json.loads(
        Path(spec["material_profile"]).read_text(encoding="utf-8-sig")
    )
    material_spec["variant"] = spec["material_variant"]
    material_report = apply_bold_materials(scene, material_spec)
    add_aov(scene, "BoldWeddingFX")
    collection = effect_collection(scene)
    lights = light_layers(scene, spec)
    arch_names = arcs(scene, collection, spec["vow_arcs"])
    spark_names = particles(scene, collection, spec["sparkles"], spec["vow_arcs"])
    beams = beam_fans(scene, collection, spec["beam_fans"])
    glows = selective_glow(scene, spec)
    baked = bake_stage(scene) if spec["bake_stage_bounce"] else None
    scene["bold_wedding_revision"] = spec["id"]
    scene["bold_wedding_lighting_changes"] = json.dumps(lights, ensure_ascii=False)
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = args.preview_percentage
    for number in args.stills:
        scene.frame_set(number)
        scene.render.filepath = str(args.output_dir / f"bold-wedding-{number}.png")
        bpy.ops.render.render(write_still=True)
        print("BOLD_WEDDING_STILL", number, flush=True)
    for frame, expected in before.items():
        scene.frame_set(frame)
        assert snapshot(scene) == expected, frame
    scene.frame_set(4140)
    scene.render.resolution_percentage = 100
    bpy.ops.file.pack_all()
    project = args.output_dir / "Franken_Duet_Bold_Wedding.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "source": str(source),
        "source_sha256": spec["source_sha256"],
        "project": str(project),
        "profile": spec,
        "material_report": material_report,
        "lights": lights,
        "arches": arch_names,
        "sparkles": spark_names,
        "beam_fans": beams,
        "selective_glow": glows,
        "rebaked_stage_probe": baked,
        "pose_camera_unchanged_frames": list(before),
        "all_file_outputs_saved_muted": True,
        "new_physics": False,
        "full_song_rendered": False,
    }
    (args.output_dir / "bold-wedding-preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("BOLD_WEDDING_READY", project, flush=True)


if __name__ == "__main__":
    main()
