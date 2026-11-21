"""Replace the rejected narrow shafts with surveyed-window daylight and a stronger NPR rim."""

import hashlib
import json
import sys
from collections import deque
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs
from snapshot_goo_scene import capture

SOURCE = Path(
    "D:/codex/output/MMD-Goo-Tyndall-Rim-v1/production-v7/Franken_Duet_Goo_Tyndall_Rim.blend"
)
SHA = "25565d772273d9991c5c5eedafb8283e81e4f9c81d5724b707d542ecdb652f96"
ROOT = Path("D:/codex/output/MMD-Goo-Window-Wrap-v1")
PREFIX = "Goo window wrap | "


def node(tree, kind, label):
    item = tree.nodes.new(kind)
    item.name = item.label = PREFIX + label
    return item


def scale_socket(tree, socket, factor, label):
    source = socket.links[0].from_socket
    gain = node(tree, "ShaderNodeMath", label)
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = factor
    tree.links.new(source, gain.inputs[0])
    tree.links.new(gain.outputs[0], socket)


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA
    production = ROOT / "production-v1"
    production.mkdir(parents=True, exist_ok=False)
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    before = capture()
    changes = {
        "hidden_narrow_shafts": [],
        "materials": [],
        "window_lights": [],
        "glows": [],
    }
    for obj in scene.objects:
        if obj.name.startswith("Goo Tyndall v2 | window shaft") or obj.name.startswith(
            "Goo Tyndall v2 | shaft divider"
        ):
            obj.hide_render = obj.hide_viewport = True
            changes["hidden_narrow_shafts"].append(obj.name)
    air = scene.objects["Goo Tyndall | rear window air only"]
    air.location, air.scale = (0, 8.5, 6), (8, 7.5, 5.95)
    air.data.materials[0].node_tree.nodes[
        "Goo Tyndall | real shadowed light scattering"
    ].inputs["Density"].default_value = 0.0025
    window_sources = ((-16.25, 28.8, 10.7), (16.65, 29.1, 10.7))
    for index, (location, energy) in enumerate(zip(window_sources, (42000, 18000))):
        data = bpy.data.lights.new(PREFIX + f"large window {index}", "AREA")
        data.shape, data.size, data.size_y = "RECTANGLE", 6.1, 14
        data.energy = energy
        data.color = (0.91, 0.96, 1)
        data.diffuse_factor, data.specular_factor, data.volume_factor = 0.35, 1, 0.8
        data.light_groups.use_default = True
        obj = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (
            (Vector((0, 0.5, 1.2)) - obj.location).to_track_quat("-Z", "Y").to_euler()
        )
        changes["window_lights"].append(
            {
                "name": obj.name,
                "type": "AREA",
                "position": list(location),
                "dimensions": [6.1, 14],
                "energy": energy,
            }
        )
    source_direction = (
        Vector((-16.54, 29.6, 15.4)) - Vector((0, 0.4, 1.2))
    ).normalized()
    data = bpy.data.lights.new(PREFIX + "parallel window daylight", "SUN")
    data.energy, data.angle = 3.2, 0.035
    data.color = (0.96, 0.98, 1)
    data.diffuse_factor, data.specular_factor, data.volume_factor = 0.7, 0.7, 1.2
    data.light_groups.use_default = True
    sun = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (-source_direction).to_track_quat("-Z", "Y").to_euler()
    changes["window_lights"].append(
        {
            "name": sun.name,
            "type": "SUN",
            "source_direction": list(source_direction),
            "energy": data.energy,
            "angle": data.angle,
        }
    )
    layer = bpy.context.view_layer
    aov = layer.aovs.add()
    aov.name, aov.type = "WindowWrapRim", "COLOR"
    for material in bpy.data.materials:
        if not material.node_tree or material.get("performer_id") not in (
            "aksiniya",
            "ikhor",
        ):
            continue
        tree = material.node_tree
        width = tree.nodes.get("Portrait relight | rimink | width power only")
        if not width:
            continue
        old_width = width.inputs[1].default_value
        is_hair = material.name in ("前鬓", "呆毛", "鬓", "鬓.001")
        width.inputs[1].default_value = 1.55 if is_hair else 1.85
        edge_exit = tree.nodes.get("Portrait relight | rimink | view edge exits")
        if edge_exit:
            edge_exit.inputs["From Min"].default_value = 0.12
            edge_exit.inputs["From Max"].default_value = 0.55
        for side, multiplier, direction in (
            ("left", 1.55, source_direction),
            ("right", 1.85, Vector((0.42, 0.80, 0.42)).normalized()),
        ):
            gain = tree.nodes["Portrait relight | rimink | " + side + " HDR gain only"]
            gain.inputs[1].default_value *= multiplier
            tree.nodes[
                "Portrait relight | rimink | " + side + " direction cosine"
            ].inputs[1].default_value = direction
            tree.nodes["Portrait relight | rimink | " + side + " warm HDR RGB"].inputs[
                0
            ].default_value = (1, 1.02, 1.10)
        rim = (
            tree.nodes.get("Portrait relight | rimink | licensed rim replacement")
            or tree.nodes["Portrait relight | rimink | two side HDR RGB"]
        )
        signal = rim.outputs[0]
        hair_signal = None
        if material.name in ("前鬓", "呆毛", "鬓"):
            strength = tree.nodes["Character layers | hair highlight strength"]
            strength.outputs[0].default_value = 0.42
            highlight = tree.nodes["Character layers | one directional hair highlight"]
            highlight.blend_type = "ADD"
            highlight.use_clamp = False
            hair_signal = highlight.inputs[0].links[0].from_socket
            queue = deque([tree.nodes["Character layers | single hair highlight"]])
            seen = set()
            while queue:
                current = queue.popleft()
                if current.as_pointer() in seen:
                    continue
                seen.add(current.as_pointer())
                if (
                    current.type == "MATH"
                    and current.operation == "POWER"
                    and current.name.startswith("Character layers |")
                    and not current.inputs[1].is_linked
                ):
                    current.inputs[1].default_value *= 0.60
                    break
                queue.extend(
                    link.from_node for socket in current.inputs for link in socket.links
                )
        elif material.name == "鬓.001":
            tree.nodes["Goo rim glow | retained hair highlight gain"].inputs[
                1
            ].default_value = 4.0
            scale_socket(
                tree,
                tree.nodes["Ikhor character | directional hair band"].inputs[1],
                0.60,
                "wider existing golden hair band",
            )
            hair_signal = tree.nodes["Ikhor character | hair highlight RGB"].outputs[0]
        if hair_signal:
            add = node(
                tree, "ShaderNodeVectorMath", "rim and existing hair-band signal"
            )
            add.operation = "ADD"
            tree.links.new(signal, add.inputs[0])
            tree.links.new(hair_signal, add.inputs[1])
            signal = add.outputs[0]
        export = node(tree, "ShaderNodeOutputAOV", "actual rim and hair radiance")
        export.aov_name = "WindowWrapRim"
        tree.links.new(signal, export.inputs["Color"])
        changes["materials"].append(
            {
                "material": material.name,
                "width_power_before": old_width,
                "width_power_after": width.inputs[1].default_value,
                "hair_band_strengthened": is_hair,
                "new_aov": export.aov_name,
            }
        )
    import goo_engine_light_groups

    goo_engine_light_groups.sync_light_groups()
    layer.update_render_passes()
    bpy.context.view_layer.update()
    tree = scene.compositing_node_group
    render = next(item for item in tree.nodes if item.type == "R_LAYERS")
    assert render.outputs.get("WindowWrapRim")
    tone = tree.nodes["Goo Tyndall | compress highlights after glow"]
    previous = tone.inputs[1].links[0].from_socket
    for label, strength, threshold, size in (
        ("tight white edge bloom", 0.85, 0.18, 0.018),
        ("soft outer edge diffusion", 0.25, 0.8, 0.045),
    ):
        glow = node(tree, "CompositorNodeGlare", label)
        for key, value in (
            ("Type", "Fog Glow"),
            ("Quality", "High"),
            ("Strength", strength),
            ("Threshold", threshold),
            ("Size", size),
        ):
            glow.inputs[key].default_value = value
        tree.links.new(render.outputs["WindowWrapRim"], glow.inputs["Image"])
        add = node(tree, "ShaderNodeMixRGB", "add " + label)
        add.blend_type = "ADD"
        add.inputs[0].default_value = 1
        tree.links.new(previous, add.inputs[1])
        tree.links.new(glow.outputs["Glare"], add.inputs[2])
        previous = add.outputs[0]
        changes["glows"].append(
            {
                "label": label,
                "strength": strength,
                "threshold": threshold,
                "size": size,
                "source": "WindowWrapRim",
            }
        )
    tree.links.new(previous, tone.inputs[1])
    tree.links.new(previous, tree.nodes["Goo Tyndall | linear luminance"].inputs[0])
    after = capture()
    preserved = {
        key: before[key] == after[key]
        for key in ("actions", "images", "samples", "geometry", "fps", "engine")
    }
    assert all(preserved.values()), preserved
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 24
    scene.frame_set(4290)
    project = production / "Franken_Duet_Goo_Window_Wrap.blend"
    scene.render.filepath = str(production / "portrait-4290.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "source": str(SOURCE),
        "source_sha256": SHA,
        "project": str(project),
        "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
        "changes": changes,
        "preserved": preserved,
        "window_basis": "Surveyed glass mat_89.001 at x approx ±16.5; front side window spans y25.6-32.0, z3.5-19.0; window-sized area fills and common directional sun, no near-camera cone pair",
        "volume_bounds": [[-8, 1, 0.05], [8, 16, 11.95]],
        "volume_density": 0.0025,
        "physics_resimulated": False,
        "art_status": "pending user review",
    }
    (production / "preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    for frame, label in ((4290, "portrait"), (4140, "opening")):
        scene.frame_set(frame)
        scene.render.filepath = str(production / f"{label}-{frame}.png")
        bpy.ops.render.render(write_still=True)
        print("WINDOW_WRAP_CONTROL", frame, flush=True)


if __name__ == "__main__":
    main()
