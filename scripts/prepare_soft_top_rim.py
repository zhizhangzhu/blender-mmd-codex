"""Add broad soft fill, overhead illumination and a controlled rear rim."""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import area
from verify_duet_integration import snapshot


def change_rims(scene, spec):
    changed, excluded = [], []
    materials = {
        m
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id")
        for m in o.data.materials
        if m and m.node_tree
    }
    for material in materials:
        tree = material.node_tree
        gain = tree.nodes.get("Cinema | rim gain")
        if not gain:
            continue
        name = material.get("source_mmd_material_name", material.name).split(".")[0]
        if name in {"面1", "面2"} or any(
            k in name for k in ("目", "眉", "睫", "口", "舌", "颜", "肌", "二重", "脸")
        ):
            assert gain.inputs[1].default_value == 0, material.name
            excluded.append(material.name)
            continue
        is_hair = any(k in name for k in ("发", "鬓", "呆毛"))
        gain.inputs[1].default_value = spec["hair_gain" if is_hair else "body_gain"]
        tree.nodes["Cinema | narrow rim"].inputs[1].default_value = spec["narrow_power"]
        side = tree.nodes["Cinema | lit rim side"]
        dot = side.inputs[0].links[0].from_node
        normal = dot.inputs[0].links[0].from_node
        delta = normal.inputs[0].links[0].from_node
        assert delta.type == "VECT_MATH" and delta.operation == "SUBTRACT"
        delta.inputs[0].default_value = spec["location"]
        tint = next(
            l.to_node for l in gain.outputs[0].links if l.to_node.type == "MIX_RGB"
        )
        tint.inputs[1].default_value = spec["color"]
        changed.append(material.name)
    assert changed and excluded
    return changed, excluded


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
        "caption_focus_revision"
    ) == "hesperides-focused-light-v3" and not scene.get("soft_top_revision")
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    frames = (1, 2100, 4140, 4200, 4250, 4290, 4439, 8400, 11899)
    before = {}
    for frame in frames:
        scene.frame_set(frame)
        before[frame] = snapshot(scene)
    stage = bpy.data.collections["Focused light | stage receivers"]
    actors = bpy.data.collections.new("Softlight | actor receivers")
    for obj in scene.objects:
        if obj.type == "MESH" and obj.get("performer_id") and not obj.hide_render:
            actors.objects.link(obj)
    assert len(actors.objects) == 2
    lights = []
    for spec in config["areas"]:
        light = area(
            "Softlight | " + spec["name"],
            spec["location"],
            spec["target"],
            spec["watts"],
            spec["color"],
            spec["size"],
        )
        light.data.volume_factor = 0
        if spec["receivers"] != "all":
            light.light_linking.receiver_collection = (
                stage if spec["receivers"] == "stage" else actors
            )
        lights.append(light)
    background = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    old_world = background.inputs["Strength"].default_value
    background.inputs["Strength"].default_value = config["world_strength"]
    adjusted = []
    for material in bpy.data.materials:
        if not material.use_nodes:
            continue
        shader = material.node_tree.nodes.get(
            "Focused light | responsive stage surface"
        )
        if not shader:
            continue
        albedo = shader.inputs["Base Color"].links[0].from_node
        assert albedo.type == "MIX_RGB" and albedo.blend_type == "MULTIPLY"
        albedo.inputs[2].default_value = config["stage_albedo_gain"]
        adjusted.append(material.name)
    changed, excluded = change_rims(scene, config["toon_rim"])
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
        render(number, f"soft-{number}.png")
    for light in lights[:3]:
        light.hide_render = True
    render(4250, "control-direct-soft-off-4250.png")
    for light in lights[:3]:
        light.hide_render = False
    lights[-1].hide_render = True
    gains = [
        (
            bpy.data.materials[name].node_tree.nodes["Cinema | rim gain"],
            bpy.data.materials[name]
            .node_tree.nodes["Cinema | rim gain"]
            .inputs[1]
            .default_value,
        )
        for name in changed
    ]
    for node, _ in gains:
        node.inputs[1].default_value = 0
    render(4290, "control-rim-off-4290.png")
    for node, gain in gains:
        node.inputs[1].default_value = gain
    lights[-1].hide_render = False
    for number in frames:
        scene.frame_set(number)
        assert snapshot(scene) == before[number], number
    scene.frame_set(4140)
    scene.render.resolution_percentage = 100
    scene["soft_top_revision"] = config["id"]
    bpy.ops.file.pack_all()
    target = args.output_dir / "Franken_Duet_Soft_Top_Rim.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    report = {
        "source": source,
        "project": str(target),
        "settings": config,
        "old_world_strength": old_world,
        "changed_stage_materials": adjusted,
        "toon_rim_materials": changed,
        "facial_materials_excluded": excluded,
        "pose_camera_lens_unchanged_frames": list(frames),
        "caption_cache_nodes_saved_muted": True,
        "scope": "Lighting revision; official subtitles still composited separately",
    }
    (args.output_dir / "soft-light-preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("SOFT_TOP_RIM_SCENE_READY", flush=True)


if __name__ == "__main__":
    main()
