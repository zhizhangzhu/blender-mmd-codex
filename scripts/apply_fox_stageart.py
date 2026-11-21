"""Develop the reviewed fox study into a shadowed, spatially coherent stage.

Run on the v1 fox master only, in an independent process and new output folder.
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import area, math_node
from stage_night_art_lab import mix, pool, spot
from verify_duet_integration import snapshot


def wall_palette(scene, config):
    changed = []
    for mat in bpy.data.materials:
        if not mat.get("stage_id") or not mat.node_tree:
            continue
        tree = mat.node_tree
        for emission in [n for n in tree.nodes if n.type == "EMISSION"]:
            wrapper = emission.inputs["Color"].links[0].from_node
            assert wrapper.type == "MIX_RGB" and wrapper.blend_type == "MULTIPLY"
            position = tree.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
            illumination = config["ambient_tint"]
            for spec in config["pools"]:
                illumination = mix(
                    tree, "ADD", illumination, pool(tree, position, spec)
                )
            tree.links.new(illumination, wrapper.inputs[2])
        changed.append(mat.name)
    return changed


def physical_ground(scene, config):
    changed = []
    copies = {}
    for name in config["ground_materials"]:
        source_mat = bpy.data.materials.get(name)
        assert source_mat and source_mat.node_tree, name
        mat = source_mat.copy()
        mat.name = "Stage art | ground only | " + name
        tree = mat.node_tree
        original = tree.nodes.get("Reference | ordinary PBR control")
        assert original, name
        new = tree.nodes.new("ShaderNodeBsdfPrincipled")
        new.name = "Stage art | physical ground"
        for destination in new.inputs:
            source = original.inputs.get(destination.name)
            if source is None:
                continue
            if source.is_linked:
                tree.links.new(source.links[0].from_socket, destination)
            elif hasattr(source, "default_value"):
                destination.default_value = source.default_value
        albedo = original.inputs["Base Color"].links[0].from_socket
        cap = tree.nodes.get("Reference | masked additive MatCap")
        if cap:
            albedo = cap.inputs[1].links[0].from_socket
        tree.links.new(
            mix(tree, "MULTIPLY", albedo, config["ground_color_gain"]),
            new.inputs["Base Color"],
        )
        # Use the authored roughness but prevent an accidental mirror floor.
        rough = (
            original.inputs["Roughness"].links[0].from_socket
            if original.inputs["Roughness"].is_linked
            else original.inputs["Roughness"].default_value
        )
        rough = math_node(
            tree,
            "Stage art | ground roughness floor",
            "MAXIMUM",
            rough,
            config["ground_roughness_min"],
        )
        tree.links.new(rough, new.inputs["Roughness"])
        output = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL")
        tree.links.new(new.outputs[0], output.inputs["Surface"])
        copies[source_mat] = mat
    bounds = config["ground_polygon_selection"]
    for obj in scene.objects:
        if obj.type != "MESH" or obj.get("performer_id") or obj.hide_render:
            continue
        if not any(m in copies for m in obj.data.materials):
            continue
        normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
        selected = []
        for polygon in obj.data.polygons:
            material = obj.data.materials[polygon.material_index]
            if material not in copies:
                continue
            normal = (normal_matrix @ polygon.normal).normalized()
            center = obj.matrix_world @ polygon.center
            if (
                normal.z >= bounds["minimum_world_normal_z"]
                and bounds["minimum_world_center_z"]
                <= center.z
                <= bounds["maximum_world_center_z"]
            ):
                selected.append((polygon.index, material))
        if not selected:
            continue
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        indices = {}
        for index, material in selected:
            if material not in indices:
                indices[material] = len(obj.data.materials)
                obj.data.materials.append(copies[material])
            obj.data.polygons[index].material_index = indices[material]
        changed.append(
            {
                "object": obj.name,
                "polygons": len(selected),
                "materials": [m.name for m in indices],
            }
        )
    assert changed, "No actual horizontal ground polygons selected"
    return changed


def rim_aov(scene, config):
    name = "StageArtRim"
    layer = scene.view_layers[0]
    aov = layer.aovs.add()
    aov.name, aov.type = name, "COLOR"
    materials = {
        m
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id")
        for m in o.data.materials
        if m and m.node_tree
    }
    changed = []
    for mat in materials:
        tree = mat.node_tree
        out = tree.nodes.new("ShaderNodeOutputAOV")
        out.aov_name = name
        out.inputs["Color"].default_value = (0, 0, 0, 1)
        gain = tree.nodes.get("Cinema | rim gain")
        narrow = tree.nodes.get("Cinema | narrow rim")
        source_name = mat.get("source_mmd_material_name", mat.name).split(".")[0]
        if source_name in {"面1", "面2"} or any(
            k in source_name
            for k in ("目", "眉", "睫", "口", "舌", "颜", "肌", "二重", "脸")
        ):
            if gain:
                gain.inputs[1].default_value = 0
            continue
        if not gain or not narrow:
            continue
        is_hair = any(k in mat.name for k in ("发", "鬓", "呆毛"))
        gain.inputs[1].default_value = config["rim"][
            "hair_gain" if is_hair else "body_gain"
        ]
        narrow.inputs[1].default_value = config["rim"]["narrow_power"]
        tint = next(
            l.to_node for l in gain.outputs[0].links if l.to_node.type == "MIX_RGB"
        )
        tint.inputs[1].default_value = config["rim"]["color"]
        tree.links.new(tint.outputs[0], out.inputs["Color"])
        changed.append(mat.name)
    layer.update_render_passes()
    return changed


def air_volume(scene, spec):
    bpy.ops.mesh.primitive_cube_add(size=2, location=spec["center"])
    obj = bpy.context.object
    obj.name = "Stage art | rear air only"
    obj.scale = spec["scale"]
    mat = bpy.data.materials.new(obj.name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    generated = tree.nodes.new("ShaderNodeTexCoord").outputs["Generated"]
    separate = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(generated, separate.inputs[0])
    distances = [
        math_node(
            tree,
            "Stage art | volume edge",
            "ABSOLUTE",
            math_node(
                tree,
                "Stage art | volume center",
                "SUBTRACT",
                math_node(tree, "Stage art | volume scale", "MULTIPLY", s, 2),
                1,
            ),
        )
        for s in separate.outputs
    ]
    maximum = math_node(
        tree,
        "Stage art | box distance",
        "MAXIMUM",
        math_node(tree, "Stage art | box XY", "MAXIMUM", distances[0], distances[1]),
        distances[2],
    )
    fade = math_node(
        tree,
        "Stage art | smooth density",
        "SUBTRACT",
        1,
        math_node(tree, "Stage art | edge fade", "POWER", maximum, 4),
    )
    fade.node.use_clamp = True
    density = math_node(
        tree, "Stage art | bounded density", "MULTIPLY", fade, spec["density"]
    )
    scatter = tree.nodes.new("ShaderNodeVolumeScatter")
    scatter.inputs["Color"].default_value = spec["color"]
    scatter.inputs["Anisotropy"].default_value = spec["anisotropy"]
    tree.links.new(density, scatter.inputs["Density"])
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(scatter.outputs[0], output.inputs["Volume"])
    obj.data.materials.append(mat)
    obj.display_type = "WIRE"
    return obj


def compositing(scene, config):
    tree = scene.compositing_node_group
    render = next(n for n in tree.nodes if n.type == "R_LAYERS")
    output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    previous = output.inputs["Image"].links[0].from_socket
    existing = next(n for n in tree.nodes if n.type == "GLARE")
    existing.inputs["Threshold"].default_value = config["bloom"]["stage_threshold"]
    existing.inputs["Strength"].default_value = config["bloom"]["stage_strength"]
    glow = tree.nodes.new("CompositorNodeGlare")
    glow.name = "Stage art | protected rim halation"
    for socket, value in [
        ("Type", "Fog Glow"),
        ("Quality", "High"),
        ("Threshold", config["bloom"]["rim_threshold"]),
        ("Strength", config["bloom"]["rim_strength"]),
        ("Size", config["bloom"]["rim_size"]),
    ]:
        glow.inputs[socket].default_value = value
    tree.links.new(render.outputs["StageArtRim"], glow.inputs["Image"])
    result = mix(tree, "ADD", previous, glow.outputs["Glare"])
    result.node.name = "Stage art | add rim after skin protection"
    tree.links.new(result, output.inputs["Image"])
    if config["transition"]["enabled"]:
        for frame, amount in zip(
            config["transition"]["frames"], config["transition"]["rim_glow_strength"]
        ):
            glow.inputs["Strength"].default_value = amount
            glow.inputs["Strength"].keyframe_insert("default_value", frame=frame)
    return glow


def render(scene, folder, label, frame):
    scene.frame_set(frame)
    scene.render.filepath = str(folder / (label + ".png"))
    bpy.ops.render.render(write_still=True)


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.preset.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    assert scene.get(
        "fox_cinema_revision"
    ) == "hesperides-fox-cinema-v1" and not scene.get("stageart_revision")
    source = bpy.data.filepath
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    checks = {}
    for frame in (1, 2100, 4200, 8400, 11899):
        scene.frame_set(frame)
        checks[frame] = snapshot(scene)
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = 67
    scene.eevee.taa_render_samples = 48
    render(scene, args.output_dir, "01-before-wide", 4250)
    walls = wall_palette(scene, config)
    ground = physical_ground(scene, config)
    rims = rim_aov(scene, config)
    sky = next(n for n in scene.world.node_tree.nodes if n.type == "VALTORGB")
    sky.color_ramp.elements[0].color = config["sky_dark"]
    sky.color_ramp.elements[-1].color = config["sky_cloud"]
    for light in [o for o in scene.objects if o.type == "LIGHT" and not o.hide_render]:
        light.data.volume_factor = 0
        if light.name == "Cinema | rear floor projector":
            light.hide_render = True
        elif light.name.endswith(" | rim"):
            light.data.energy = 120
            light.data.color = (1, 0.78, 0.58)
    projector = spot(scene, "Stage art | grounded backlight", config["projector"])
    blockers = bpy.data.collections.new("Stage art | dancer shadow blockers")
    scene.collection.children.link(blockers)
    for obj in list(scene.objects):
        if obj.type == "MESH" and obj.get("performer_id") and not obj.hide_render:
            blockers.objects.link(obj)
    projector.light_linking.blocker_collection = blockers
    projector.data.shadow_soft_size = config["projector"]["source_radius"]
    projector.data.volume_factor = 0.6
    rose = area(
        "Stage art | rose side bounce",
        location=config["rose_area"]["location"],
        target=config["rose_area"]["target"],
        energy=config["rose_area"]["watts"],
        color=config["rose_area"]["color"],
        size=config["rose_area"]["size"],
    )
    rose.data.volume_factor = 0.4
    moon = bpy.data.objects.get("Cinema | cold backlight")
    moon.data.volume_factor = 1
    # No static performer silhouettes in the indirect cache.
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
    volume = air_volume(scene, config["air"])
    bpy.context.view_layer.update()
    compositing(scene, config)
    camera = scene.camera
    for frame in range(4139, 4441):
        scene.frame_set(frame)
        distance = camera.data.dof.focus_distance
        camera.data.dof.aperture_fstop = min(
            config["optics"]["wide_fstop_max"],
            max(
                config["optics"]["minimum_fstop"],
                config["optics"]["minimum_fstop"] + (distance - 3) * 0.4,
            ),
        )
        camera.data.keyframe_insert(
            "dof.aperture_fstop", frame=frame, group="Stage art | shot aperture"
        )
        if scene.render.motion_blur_shutter > 0.001:
            scene.render.motion_blur_shutter = config["optics"]["shutter_frames"]
            scene.keyframe_insert(
                "render.motion_blur_shutter",
                frame=frame,
                group="Cinema | cut protection",
            )
    scene.eevee.motion_blur_max = config["optics"]["blur_max_pixels"]
    render(scene, args.output_dir, "02-stage-wide", 4250)
    render(scene, args.output_dir, "03-stage-close", 4290)
    # Same-frame counterfactuals distinguish actual effects from settings alone.
    projector.data.use_shadow = False
    render(scene, args.output_dir, "control-no-projector-shadow", 4250)
    projector.data.use_shadow = True
    volume.hide_render = True
    render(scene, args.output_dir, "control-no-rear-air", 4250)
    volume.hide_render = False
    add = scene.compositing_node_group.nodes[
        "Stage art | add rim after skin protection"
    ]
    add.mute = True
    render(scene, args.output_dir, "control-no-rim-glow", 4290)
    add.mute = False
    render(scene, args.output_dir, "transition-peak", 4262)
    for frame, expected in checks.items():
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        assert snapshot(scene) == expected, frame
    scene.frame_set(4140)
    scene.render.resolution_percentage = 100
    scene.frame_start, scene.frame_end = 4140, 4439
    scene["stageart_revision"] = config["id"]
    project = args.output_dir / "Franken_Duet_StageArt_v2.blend"
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "source": source,
        "project": str(project),
        "config": config,
        "wall_materials": walls,
        "physical_ground_materials": ground,
        "rim_aov_materials": rims,
        "unchanged_rig_camera_lens_frames": list(checks),
        "native_cinema": "controls and project saved; independent video verification still required",
        "notes": [
            "No author source recovered",
            "NPR wall pools and rims have no physical occlusion",
            "Only stage ground switched to physical shading; actor face/ink retained",
            "Auxiliary RGBA scenes not calibrated for these effects",
        ],
    }
    (args.output_dir / "stageart-study.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("FOX_STAGE_ART_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
