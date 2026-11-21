"""Restore visible cast/contact shadows and bounded actor self-shadow response."""

import argparse
import json
import sys
from math import radians
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import aim, math_node
from stage_night_art_lab import mix
from verify_duet_integration import snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.preset.read_text(encoding="utf-8"))
    source = bpy.data.filepath
    scene = bpy.context.scene
    assert scene.get(
        "wedding_revision"
    ) == "hesperides-blue-gold-wedding-v1" and not scene.get("grounded_shadow_revision")
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    checks = {}
    for number in (1, 2100, 4140, 4200, 4250, 4290, 4439, 8400, 11899):
        scene.frame_set(number)
        checks[number] = snapshot(scene)
    key = scene.objects["Stage art | grounded backlight"]
    key.location = config["key"]["location"]
    aim(key, config["key"]["target"])
    key.data.energy = config["key"]["watts"]
    key.data.spot_size = radians(config["key"]["angle_degrees"])
    key.data.spot_blend = config["key"]["blend"]
    key.data.shadow_soft_size = config["key"]["radius"]
    key.data.color = (1, 0.90, 0.78)
    key.data.volume_factor = 0
    key.data.use_shadow = True
    assert key.light_linking.blocker_collection
    changed = []
    floors = []
    for material in bpy.data.materials:
        if not material.node_tree:
            continue
        tree = material.node_tree
        response = tree.nodes.get("Quality | bounded real illumination")
        if material.get("performer_id") and response:
            name = material.get("source_mmd_material_name", material.name).split(".")[0]
            face = name in {"颜", "颜+", "面1", "面2"}
            skin = name == "肌"
            hair = any(word in name for word in ("发", "鬓", "呆毛"))
            category = (
                "face_floor"
                if face
                else "skin_body_floor"
                if skin
                else "hair_floor"
                if hair
                else "body_floor"
            )
            for socket in response.inputs:
                if socket.type != "VALUE":
                    continue
                if socket.name == "From Min":
                    socket.default_value = config["physical_response"]["low"]
                if socket.name == "From Max":
                    socket.default_value = config["physical_response"]["high"]
                if socket.name == "To Min":
                    socket.default_value = config["physical_response"][category]
            changed.append(
                {
                    "material": material.name,
                    "category": category,
                    "floor": config["physical_response"][category],
                }
            )
        shader = tree.nodes.get("Focused light | responsive stage surface")
        if not shader:
            continue
        geometry = tree.nodes.new("ShaderNodeNewGeometry")
        pos = tree.nodes.new("ShaderNodeSeparateXYZ")
        normal = tree.nodes.new("ShaderNodeSeparateXYZ")
        tree.links.new(geometry.outputs["Position"], pos.inputs[0])
        tree.links.new(geometry.outputs["Normal"], normal.inputs[0])
        height = math_node(
            tree, "Grounding | floor height", "ABSOLUTE", pos.outputs["Z"]
        )
        near = math_node(
            tree,
            "Grounding | near floor",
            "LESS_THAN",
            height,
            config["floor_contact"]["height_limit"],
        )
        up = math_node(
            tree,
            "Grounding | upward floor",
            "GREATER_THAN",
            normal.outputs["Z"],
            config["floor_contact"]["minimum_normal_z"],
        )
        region = math_node(tree, "Grounding | floor region", "MULTIPLY", near, up)
        ao = tree.nodes.new("ShaderNodeAmbientOcclusion")
        ao.name = "Grounding | physical contact"
        ao.samples = 16
        ao.inputs["Distance"].default_value = config["floor_contact"]["distance"]
        weighted = math_node(
            tree,
            "Grounding | contact amount",
            "MULTIPLY",
            region,
            config["floor_contact"]["strength"],
        )
        loss = math_node(
            tree, "Grounding | occlusion loss", "SUBTRACT", 1, ao.outputs["AO"]
        )
        strength = math_node(
            tree, "Grounding | contact loss", "MULTIPLY", weighted, loss
        )
        factor = math_node(tree, "Grounding | contact factor", "SUBTRACT", 1, strength)
        original = shader.inputs["Base Color"].links[0].from_socket
        tree.links.new(
            mix(tree, "MULTIPLY", original, factor), shader.inputs["Base Color"]
        )
        floors.append(material.name)
    assert changed and floors
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
        render(number, f"grounded-{number}.png")
    key.data.use_shadow = False
    render(4250, "control-key-shadow-off-4250.png")
    key.data.use_shadow = True
    for name in floors:
        bpy.data.materials[name].node_tree.nodes["Grounding | contact amount"].inputs[
            1
        ].default_value = 0
    render(4250, "control-contact-off-4250.png")
    for name in floors:
        bpy.data.materials[name].node_tree.nodes["Grounding | contact amount"].inputs[
            1
        ].default_value = config["floor_contact"]["strength"]
    for number, expected in checks.items():
        scene.frame_set(number)
        assert snapshot(scene) == expected, number
    scene.frame_set(4140)
    scene.render.resolution_percentage = 100
    scene["grounded_shadow_revision"] = config["id"]
    bpy.ops.file.pack_all()
    target = args.output_dir / "Franken_Duet_Grounded_Wedding.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    report = {
        "source": source,
        "project": str(target),
        "settings": config,
        "pose_camera_lens_unchanged_frames": list(checks),
        "actor_response": changed,
        "floor_contact_materials": floors,
        "key_blockers": [o.name for o in key.light_linking.blocker_collection.objects],
        "all_file_outputs_saved_muted": True,
    }
    (args.output_dir / "grounding-preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("GROUNDED_SHADOW_STUDY_READY", flush=True)


if __name__ == "__main__":
    main()
