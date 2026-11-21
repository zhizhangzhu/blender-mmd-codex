"""Build responsive stage lighting and native matte/beauty caches for captions."""

import argparse
import json
import sys
import warnings
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import area, math_node
from stage_night_art_lab import mix, spot
from verify_duet_integration import snapshot


def stage_pbr(scene, config):
    materials = {
        m
        for o in scene.objects
        if o.type == "MESH" and not o.get("performer_id") and not o.hide_render
        for m in o.data.materials
        if m and m.node_tree and m.get("stage_id")
    }
    report = []
    for material in materials:
        tree = material.node_tree
        original = tree.nodes.get("Reference | ordinary PBR control")
        if original is None:
            report.append(
                {
                    "material": material.name,
                    "action": "existing physical/special surface retained",
                }
            )
            continue
        shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
        shader.name = "Focused light | responsive stage surface"
        for target in shader.inputs:
            source = original.inputs.get(target.name)
            if source is None:
                continue
            if source.is_linked:
                tree.links.new(source.links[0].from_socket, target)
            elif hasattr(source, "default_value"):
                target.default_value = source.default_value
        albedo = original.inputs["Base Color"].links[0].from_socket
        matcap = tree.nodes.get("Reference | masked additive MatCap")
        if matcap:
            albedo = matcap.inputs[1].links[0].from_socket
        tree.links.new(
            mix(tree, "MULTIPLY", albedo, config["stage_albedo_gain"]),
            shader.inputs["Base Color"],
        )
        roughness = (
            original.inputs["Roughness"].links[0].from_socket
            if original.inputs["Roughness"].is_linked
            else original.inputs["Roughness"].default_value
        )
        tree.links.new(
            math_node(
                tree,
                "Focused light | roughness floor",
                "MAXIMUM",
                roughness,
                config["stage_roughness_min"],
            ),
            shader.inputs["Roughness"],
        )
        output = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL")
        tree.links.new(shader.outputs[0], output.inputs["Surface"])
        report.append(
            {
                "material": material.name,
                "action": "real stage illumination; no self-lit NPR diffuse or additive MatCap in albedo",
            }
        )
    return report


def cache_output(tree, name, directory, socket, color):
    node = tree.nodes.new("CompositorNodeOutputFile")
    node.name = "Caption cache | " + name
    node.directory = str(directory)
    node.file_name = "frame_####"
    node.format.media_type = "IMAGE"
    node.format.file_format = "PNG"
    node.format.color_mode = "RGB" if color else "BW"
    node.format.color_depth = "16"
    node.save_as_render = color
    item = node.file_output_items.new("RGBA" if color else "FLOAT", name)
    item.save_as_render = color
    tree.links.new(socket, node.inputs[name])
    node.mute = True
    return node


def setup_cache(scene, directory):
    layer = scene.view_layers[0]
    layer.use_pass_cryptomatte_object = True
    layer.pass_cryptomatte_depth = 6
    layer.update_render_passes()
    tree = scene.compositing_node_group
    output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    crypto = tree.nodes.new("CompositorNodeCryptomatteV2")
    crypto.name = "Caption | both performers native object coverage"
    crypto.source = "RENDER"
    crypto.scene = scene
    crypto.layer_name = layer.name + ".CryptoObject"
    meshes = [
        o
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id") and not o.hide_render
    ]
    assert len(meshes) == 2
    crypto.matte_id = ",".join(o.name for o in meshes)
    cache_output(
        tree,
        "beauty",
        directory / "beauty",
        output.inputs["Image"].links[0].from_socket,
        True,
    )
    cache_output(tree, "actor", directory / "actor", crypto.outputs["Matte"], False)
    return [o.name for o in meshes]


def still(scene, output, frame):
    scene.frame_set(frame)
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--probe-cache", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    args.probe_cache.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.preset.read_text(encoding="utf-8"))
    source = bpy.data.filepath
    scene = bpy.context.scene
    assert scene.get("stageart_revision") == "hesperides-stageart-v2" and not scene.get(
        "caption_focus_revision"
    )
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    before = {}
    for frame in (1, 2100, 4200, 4250, 8400, 11899):
        scene.frame_set(frame)
        before[frame] = snapshot(scene)
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = 67
    scene.eevee.taa_render_samples = 48
    still(scene, args.output_dir / "before-4250.png", 4250)
    changed = stage_pbr(scene, config)
    stage_receivers = bpy.data.collections.new("Focused light | stage receivers")
    scene.collection.children.link(stage_receivers)
    for obj in list(scene.objects):
        if (
            obj.type == "MESH"
            and not obj.get("performer_id")
            and not obj.hide_render
            and any(m and m.get("stage_id") for m in obj.data.materials)
        ):
            stage_receivers.objects.link(obj)
    # Existing actor lights preserve their key direction and facial response.
    for obj in scene.objects:
        if obj.type == "LIGHT" and not obj.name.startswith("Reference duet |"):
            obj.hide_render = True
    backlight = scene.objects["Stage art | grounded backlight"]
    backlight.hide_render = False
    backlight.data.energy = config["ground_backlight_watts"]
    backlight.data.shadow_soft_size = config["ground_backlight_radius"]
    backlight.data.color = (0.70, 0.81, 1)
    backlight.data.volume_factor = 0
    cold = area(
        "Focused light | cold window key",
        config["cold_window"]["location"],
        config["cold_window"]["target"],
        config["cold_window"]["watts"],
        config["cold_window"]["color"],
        config["cold_window"]["size"],
    )
    warm = spot(scene, "Focused light | warm altar", config["warm_altar"])
    lights = [cold, warm]
    for spec in config["practicals"]:
        data = bpy.data.lights.new("Focused light | " + spec["name"], "POINT")
        data.energy, data.color, data.shadow_soft_size = (
            spec["watts"],
            spec["color"],
            spec["radius"],
        )
        obj = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(obj)
        obj.location = spec["location"]
        lights.append(obj)
    for obj in lights:
        obj.light_linking.receiver_collection = stage_receivers
        obj.data.volume_factor = 0.15 if obj == cold else 0
    next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND").inputs[
        "Strength"
    ].default_value = config["world_strength"]
    air = scene.objects["Stage art | rear air only"].data.materials[0]
    air.node_tree.nodes["Stage art | bounded density"].inputs[1].default_value = config[
        "volume_density"
    ]
    bpy.context.view_layer.update()
    # Receiver membership is needed for light linking, not a second render path.
    scene.view_layers[0].layer_collection.children[stage_receivers.name].exclude = True
    hidden = [(o, o.hide_render) for o in scene.objects if o.get("performer_id")]
    for obj, _ in hidden:
        obj.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    probe = next(
        o for o in scene.objects if o.type == "LIGHT_PROBE" and o.data.type == "VOLUME"
    )
    probe.select_set(True)
    bpy.context.view_layer.objects.active = probe
    assert bpy.ops.object.lightprobe_cache_bake(subset="SELECTED") == {"FINISHED"}
    for obj, value in hidden:
        obj.hide_render = value
    objects = setup_cache(scene, args.probe_cache)
    nodes = [
        n
        for n in scene.compositing_node_group.nodes
        if n.name.startswith("Caption cache | ")
    ]
    for node in nodes:
        node.mute = False
    for frame in (4200, 4250, 4290):
        still(scene, args.output_dir / f"focused-{frame}.png", frame)
    for node in nodes:
        node.mute = True
    for frame, expected in before.items():
        scene.frame_set(frame)
        assert snapshot(scene) == expected, frame
    projections = []
    for frame in range(4140, 4440):
        scene.frame_set(frame)
        row = {"frame": frame, "heads": {}}
        for arm in scene.objects:
            if arm.type == "ARMATURE" and arm.get("performer_id"):
                head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
                point = world_to_camera_view(
                    scene,
                    scene.camera,
                    arm.matrix_world @ head.matrix.translation + Vector((0, 0, 0.055)),
                )
                row["heads"][arm["performer_id"]] = list(point)
        projections.append(row)
    scene.frame_set(4140)
    scene.render.resolution_percentage = 100
    scene.frame_start, scene.frame_end = 4140, 4439
    scene["caption_focus_revision"] = config["id"]
    bpy.ops.file.pack_all()
    project = args.output_dir / "Franken_Duet_Focused_Caption_Source.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    (args.output_dir / "focus-caption-preparation.json").write_text(
        json.dumps(
            {
                "source": source,
                "project": str(project),
                "settings": config,
                "stage_materials": changed,
                "objects_in_native_matte": objects,
                "pose_camera_lens_unchanged_frames": list(before),
                "projected_head_positions": projections,
                "caption_cache_nodes_saved_muted": True,
                "caption_scope": "Raster official typography composited separately, not yet present in this blend's beauty",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("FOCUSED_CAPTION_SCENE_READY", flush=True)


if __name__ == "__main__":
    main()
