"""Validate selected toon-lighting, outline, glow and camera tutorial concepts.

Load the v2 portable Aksiniya project. This creates an experimental study in a
new directory; it does not overwrite or certify a new production final.
"""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_look_upgrade import node, math_node


def light_vector(t, geometry, light, label):
    position = node(t, "ShaderNodeCombineXYZ", label + " position")
    for index, axis in enumerate("XYZ"):
        fc = position.inputs[index].driver_add("default_value")
        var = fc.driver.variables.new()
        var.name = "position"
        var.type = "TRANSFORMS"
        var.targets[0].id = light
        var.targets[0].transform_type = "LOC_" + axis
        var.targets[0].transform_space = "WORLD_SPACE"
        fc.driver.expression = "position"
    subtract = node(
        t, "ShaderNodeVectorMath", label + " surface direction", operation="SUBTRACT"
    )
    t.links.new(position.outputs[0], subtract.inputs[0])
    t.links.new(geometry.outputs["Position"], subtract.inputs[1])
    normalize = node(
        t, "ShaderNodeVectorMath", label + " unit direction", operation="NORMALIZE"
    )
    t.links.new(subtract.outputs[0], normalize.inputs[0])
    return normalize.outputs[0]


def light_color(t, light, label):
    rgb = node(t, "ShaderNodeRGB", label + " color")
    for index in range(3):
        fc = rgb.outputs[0].driver_add("default_value", index)
        var = fc.driver.variables.new()
        var.name = "color"
        var.targets[0].id_type = "LIGHT"
        var.targets[0].id = light.data
        var.targets[0].data_path = f"color[{index}]"
        fc.driver.expression = "color"
    return rgb.outputs[0]


def light_energy(t, light, reference):
    value = node(t, "ShaderNodeValue", "Tutorial bounded light power")
    fc = value.outputs[0].driver_add("default_value")
    var = fc.driver.variables.new()
    var.name = "energy"
    var.targets[0].id_type = "LIGHT"
    var.targets[0].id = light.data
    var.targets[0].data_path = "energy"
    fc.driver.expression = f"min(2.0,max(0.0,energy/{reference}))"
    return value.outputs[0]


def linked_key(materials, light):
    count = 0
    for mat in materials:
        t = mat.node_tree
        geo = t.nodes.get("Look v3 | Geometry")
        direction = t.nodes.get("Look v3 | Key direction")
        if not geo or not direction:
            continue
        key = light_vector(t, geo, light, "Tutorial key")
        t.links.new(key, direction.inputs[1])
        half = t.nodes.get("Look v3 | Half vector")
        if half:
            t.links.new(key, half.inputs[1])
        # The directional art light is deliberately separated from physical
        # inverse-square attenuation. Color influence remains subtle on skin.
        category = mat.get("look_category", "cloth")
        if category not in {"eye", "ink"}:
            emission = t.nodes.get("Look v3 | NPR surface")
            color = emission.inputs[0].links[0].from_socket
            tint = node(
                t,
                "ShaderNodeMixRGB",
                "Tutorial key color influence",
                blend_type="MULTIPLY",
            )
            tint.inputs[0].default_value = 0.10 if category == "skin" else 0.22
            t.links.new(color, tint.inputs[1])
            t.links.new(light_color(t, light, "Tutorial key"), tint.inputs[2])
            power_weight = 0.10 if category == "skin" else 0.25
            gain = math_node(t, "MULTIPLY", light_energy(t, light, 170), power_weight)
            gain = math_node(t, "ADD", gain, 1.0 - power_weight)
            scale = node(
                t,
                "ShaderNodeVectorMath",
                "Tutorial key power response",
                operation="SCALE",
            )
            t.links.new(tint.outputs[0], scale.inputs[0])
            t.links.new(gain, scale.inputs[3])
            t.links.new(scale.outputs[0], emission.inputs[0])
        count += 1
    return count


def selective_rim(materials, light):
    count = 0
    for mat in materials:
        category = mat.get("look_category")
        if category not in {"hair", "cloth", "fur", "trim"} or mat.name.endswith("+"):
            continue
        t = mat.node_tree
        geo = t.nodes["Look v3 | Geometry"]
        incoming = node(
            t, "ShaderNodeVectorMath", "Tutorial facing", operation="DOT_PRODUCT"
        )
        t.links.new(geo.outputs["Normal"], incoming.inputs[0])
        t.links.new(geo.outputs["Incoming"], incoming.inputs[1])
        absolute = math_node(t, "ABSOLUTE", incoming.outputs["Value"])
        edge = math_node(t, "SUBTRACT", 1.0, absolute)
        narrow = math_node(t, "POWER", edge, 3.0)
        direction = light_vector(t, geo, light, "Tutorial rim")
        dot = node(
            t, "ShaderNodeVectorMath", "Tutorial rim lit side", operation="DOT_PRODUCT"
        )
        t.links.new(geo.outputs["Normal"], dot.inputs[0])
        t.links.new(direction, dot.inputs[1])
        positive = math_node(t, "MAXIMUM", dot.outputs["Value"], 0)
        mask = math_node(t, "MULTIPLY", narrow, positive)
        mask = math_node(
            t,
            "MULTIPLY",
            mask,
            {"hair": 0.12, "cloth": 0.065, "fur": 0.04, "trim": 0.07}[category],
        )
        mask = math_node(t, "MULTIPLY", mask, light_energy(t, light, 100))
        emission = t.nodes["Look v3 | NPR surface"]
        color = emission.inputs[0].links[0].from_socket
        mix = node(t, "ShaderNodeMixRGB", "Tutorial selective rim", blend_type="ADD")
        t.links.new(mask, mix.inputs[0])
        t.links.new(color, mix.inputs[1])
        t.links.new(light_color(t, light, "Tutorial rim"), mix.inputs[2])
        t.links.new(mix.outputs[0], emission.inputs[0])
        count += 1
    return count


def toon_edges(materials, root):
    for mat in materials:
        mm = mat.mmd_material
        category = mat.get("look_category", "cloth")
        enabled = (
            category not in {"eye", "ink"}
            and not mat.name.endswith("+")
            and mm.alpha > 0.001
        )
        mm.enabled_toon_edge = enabled
        if category == "skin":
            mm.edge_color = (0.43, 0.30, 0.38, 0.55)
        elif category == "hair":
            mm.edge_color = (0.25, 0.28, 0.45, 0.72)
        else:
            mm.edge_color = (0.16, 0.18, 0.30, 0.70)
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    result = bpy.ops.mmd_tools.edge_preview_setup(action="CREATE")
    assert result == {"FINISHED"}
    modifiers = []
    for obj in root.children_recursive:
        mod = obj.modifiers.get("mmd_edge_preview") if obj.type == "MESH" else None
        if mod:
            mod.thickness *= 0.42
            modifiers.append({"object": obj.name, "thickness": mod.thickness})
    return modifiers


def selective_glow(scene, materials):
    aov_name = "TutorialGlow"
    aov = scene.view_layers[0].aovs.add()
    aov.name, aov.type = aov_name, "VALUE"
    for mat in materials:
        # EEVEE 5.2 does not expose IndexMA in Render Layers on this machine.
        # A shader AOV supplies a material mask without changing beauty color.
        output = mat.node_tree.nodes.new("ShaderNodeOutputAOV")
        output.aov_name = aov_name
        output.inputs["Value"].default_value = float(
            mat.name.rstrip("+") == "目" or mat.get("look_category") == "trim"
        )
    scene.view_layers[0].update_render_passes()
    tree = bpy.data.node_groups.new(
        "Tutorial | masked highlight bloom", "CompositorNodeTree"
    )
    scene.compositing_node_group = tree
    tree.interface.new_socket(
        name="Image", in_out="OUTPUT", socket_type="NodeSocketColor"
    )
    output = tree.nodes.new("NodeGroupOutput")
    render = tree.nodes.new("CompositorNodeRLayers")
    render.scene = scene
    extract = tree.nodes.new("ShaderNodeMixRGB")
    extract.blend_type = "MULTIPLY"
    extract.inputs[0].default_value = 1
    tree.links.new(render.outputs["Image"], extract.inputs[1])
    tree.links.new(render.outputs[aov_name], extract.inputs[2])
    glow = tree.nodes.new("CompositorNodeGlare")
    glow.inputs["Type"].default_value = "Fog Glow"
    glow.inputs["Quality"].default_value = "High"
    glow.inputs["Threshold"].default_value = 0.8
    glow.inputs["Strength"].default_value = 0.14
    glow.inputs["Size"].default_value = 0.08
    tree.links.new(extract.outputs[0], glow.inputs["Image"])
    add = tree.nodes.new("ShaderNodeMixRGB")
    add.blend_type = "ADD"
    add.inputs[0].default_value = 1
    tree.links.new(render.outputs["Image"], add.inputs[1])
    tree.links.new(glow.outputs["Glare"], add.inputs[2])
    tree.links.new(add.outputs[0], output.inputs["Image"])
    return {
        "threshold": 0.8,
        "strength": 0.14,
        "size": 0.08,
        "mask_aov": aov_name,
        "masked_categories": ["iris", "trim"],
    }


def portrait_camera(scene, arm, start=421, end=660):
    head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
    heads = {}
    hair_bounds = {}
    mesh = next(
        o
        for o in arm.parent.children_recursive
        if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
    )
    hair_materials = {
        i
        for i, m in enumerate(mesh.data.materials)
        if m and m.name.rstrip("+") in {"前鬓", "鬓", "呆毛", "头饰"}
    }
    hair_vertices = {
        v
        for p in mesh.data.polygons
        if p.material_index in hair_materials
        for v in p.vertices
    }
    assert hair_vertices
    for frame in range(start - 5, end + 6):
        scene.frame_set(frame)
        heads[frame] = (arm.matrix_world @ head.matrix.translation).copy()
        if start <= frame <= end:
            evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
            points = [
                mesh.matrix_world @ evaluated.data.vertices[i].co for i in hair_vertices
            ]
            lo = Vector(tuple(min(p[a] for p in points) for a in range(3)))
            hi = Vector(tuple(max(p[a] for p in points) for a in range(3)))
            hair_bounds[frame] = [
                Vector((x, y, z))
                for x in [lo.x, hi.x]
                for y in [lo.y, hi.y]
                for z in [lo.z, hi.z]
            ]
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "Tutorial | two portrait shots"
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = 32
    cam.data.lens = 65
    focus = bpy.data.objects.new("Tutorial | portrait focus", None)
    scene.collection.objects.link(focus)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = focus
    cam.data.dof.aperture_fstop = 4
    cam.data.dof.aperture_blades = 8
    scene.camera = cam
    checks = []
    cut = (start + end + 1) // 2
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        smooth = sum((heads[f] for f in range(frame - 5, frame + 6)), Vector()) / 11
        second = frame >= cut
        shot_start = cut if second else start
        shot_end = end if second else cut - 1
        u = (frame - shot_start) / max(1, shot_end - shot_start)
        ease = u * u * (3 - 2 * u)
        span = (0.84 - 0.02 * ease) if second else (1.08 - 0.08 * ease)
        yaw = (0.08 - 0.05 * ease) if second else (-0.12 + 0.04 * ease)
        target = smooth + Vector((0, 0, -span * (0.06 if second else 0.21)))
        distance = span * cam.data.lens / cam.data.sensor_height
        cam.location = target + Vector(
            (math.sin(yaw) * distance, -math.cos(yaw) * distance, 0.035)
        )
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        projected = [world_to_camera_view(scene, cam, v) for v in hair_bounds[frame]]
        correction = max(0.0, (max(p.y for p in projected) - 0.94) * span)
        cam.location.z += correction
        target.z += correction
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        focus.location = heads[frame] + Vector((0, -0.03, 0.07))
        for prop in ["location", "rotation_euler"]:
            cam.keyframe_insert(data_path=prop, frame=frame)
        focus.keyframe_insert(data_path="location", frame=frame)
        bpy.context.view_layer.update()
        hp = world_to_camera_view(scene, cam, heads[frame])
        projected = [world_to_camera_view(scene, cam, v) for v in hair_bounds[frame]]
        checks.append(
            {
                "frame": frame,
                "head_in_frame": 0 < hp.x < 1 and 0 < hp.y < 1 and hp.z > 0,
                "hair_in_frame": all(
                    0 < p.x < 1 and 0 < p.y < 0.985 and p.z > 0 for p in projected
                ),
            }
        )
    # Each frame was sampled after a smooth trajectory was computed. Linear
    # interpolation prevents Bezier overshoot across the hard cut at 541.
    for action in [cam.animation_data.action, focus.animation_data.action]:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        for key in fc.keyframe_points:
                            key.interpolation = "LINEAR"
    scene.frame_start, scene.frame_end = start, end
    assert all(c["head_in_frame"] and c["hair_in_frame"] for c in checks)
    return {
        "frames": [start, end],
        "cut": cut,
        "lens_mm": 65,
        "fstop": 4,
        "head_smoothing_frames": 11,
        "head_and_hair_projection_checks": len(checks),
        "hair_bounds": "deformed base hair vertices; conservative world-space bounding box",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--preview", action="store_true")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    s = bpy.context.scene
    assert s.rigidbody_world is None
    materials = [
        m
        for m in bpy.data.materials
        if m.node_tree and m.node_tree.nodes.get("Look v3 | NPR surface")
    ]
    assert len(materials) == 33
    root = next(o for o in s.objects if getattr(o, "mmd_type", None) == "ROOT")
    arm = next(o for o in s.objects if o.type == "ARMATURE")
    report = {
        "source": bpy.data.filepath,
        "experimental": True,
        "physics_changed": False,
        "stills": [],
    }
    baseline = Path(bpy.data.filepath).with_name("poster.png")
    if baseline.exists():
        shutil.copyfile(baseline, args.output_dir / "00-baseline-0421.png")

    def still(name, frame=421):
        s.frame_set(frame)
        s.render.resolution_percentage = 100
        s.render.image_settings.media_type = "IMAGE"
        s.render.image_settings.file_format = "PNG"
        s.render.filepath = str(args.output_dir / (name + ".png"))
        bpy.ops.render.render(write_still=True)
        report["stills"].append({"name": name, "frame": frame})

    key = bpy.data.objects["Key softbox"]
    key.location = (-2.8, -4.2, 4.5)
    report["light_linked_materials"] = linked_key(materials, key)
    still("01-linked-key-0421")
    key.location.x *= -1
    still("01b-key-opposite-side-0421")
    key.location.x *= -1
    key.data.energy = 0
    still("01c-key-zero-power-0421")
    key.data.energy = 170
    data = bpy.data.lights.new("Tutorial rim", "AREA")
    data.energy, data.size, data.color = 100, 3, (0.55, 0.70, 1.0)
    rim = bpy.data.objects.new("Tutorial | rim light", data)
    s.collection.objects.link(rim)
    rim.location = (2.6, 1.8, 3.2)
    rim.rotation_euler = (
        (Vector((0, 0, 1.2)) - rim.location).to_track_quat("-Z", "Y").to_euler()
    )
    report["rim_materials"] = selective_rim(materials, rim)
    still("02-selective-rim-0421")
    report["edge_modifiers"] = toon_edges(materials, root)
    still("03-thin-edges-0421")
    report["glow"] = selective_glow(s, materials)
    still("04-masked-glow-0421")
    report["camera"] = portrait_camera(s, arm)
    for frame in [421, 484, 601, 660]:
        still(f"05-portrait-{frame:04d}", frame)
    s.frame_set(421)
    s.render.filepath = str(args.output_dir / "05-portrait-0421.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_dir / "tutorial-study.blend"))
    if args.preview:
        s.render.resolution_percentage = 50
        s.eevee.taa_render_samples = 48
        s.render.image_settings.media_type = "VIDEO"
        s.render.image_settings.file_format = "FFMPEG"
        s.render.ffmpeg.format, s.render.ffmpeg.codec = "MPEG4", "H264"
        s.render.ffmpeg.constant_rate_factor = "HIGH"
        s.render.ffmpeg.audio_codec = "NONE"
        s.render.use_sequencer = False
        s.render.filepath = str(args.output_dir / "tutorial-preview-silent.mp4")
        bpy.ops.render.render(animation=True)
    (args.output_dir / "study-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("TUTORIAL_STUDY_COMPLETE", args.output_dir, flush=True)


if __name__ == "__main__":
    main()
