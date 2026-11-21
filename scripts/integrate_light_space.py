"""Repair fixture transforms and head axes, then connect bounded real shading.

All changes target a new independent copy. Shader color/alpha, baked animation,
camera actions and model-specific textures remain upstream of the new controls.
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from genshin_material_adapt import KEY
from verify_duet_integration import snapshot


def scalar(tree, operation, first, second):
    node = tree.nodes.new("ShaderNodeMath")
    node.name = "Quality | " + operation
    node.operation = operation
    for socket, value in zip(node.inputs, [first, second]):
        if hasattr(value, "is_output"):
            tree.links.new(value, socket)
        else:
            socket.default_value = value
    return node.outputs[0]


def multiply(tree, first, second, name):
    node = tree.nodes.new("ShaderNodeMixRGB")
    node.name = name
    node.blend_type = "MULTIPLY"
    node.inputs[0].default_value = 1
    for socket, value in zip(node.inputs[1:], [first, second]):
        if hasattr(value, "is_output"):
            tree.links.new(value, socket)
        else:
            socket.default_value = value
    return node.outputs[0]


def basis_world(obj):
    if obj.parent:
        return basis_world(obj.parent) @ obj.matrix_parent_inverse @ obj.matrix_basis
    return obj.matrix_basis.copy()


def restore_stage(scene, source):
    root = next(
        o
        for o in scene.objects
        if o.name.startswith("Duet | selected Hesperides stage | reference rebuild")
    )
    names = {
        o.name: o
        for o in scene.objects
        if o.type in {"LIGHT", "LIGHT_PROBE"} and o.parent == root
    }
    with bpy.data.libraries.load(str(source), link=False) as (available, loaded):
        selected = tuple(name for name in available.objects if name in names)
        loaded.objects = list(selected)
    report = []
    for name, original in zip(selected, loaded.objects):
        current = names[name]
        before = current.matrix_world.copy()
        restored = root.matrix_world @ basis_world(original)
        current.matrix_world = restored
        report.append(
            {
                "object": name,
                "old_position": list(before.translation),
                "new_position": list(restored.translation),
                "maximum_matrix_delta": max(
                    abs(a - b)
                    for row1, row2 in zip(before, restored)
                    for a, b in zip(row1, row2)
                ),
            }
        )
    for obj in loaded.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    return report


def transform_variable(driver, name, obj, axis):
    variable = driver.variables.new()
    variable.name = name
    variable.type = "TRANSFORMS"
    variable.targets[0].id = obj
    variable.targets[0].transform_type = "LOC_" + "XYZ"[axis]
    variable.targets[0].transform_space = "WORLD_SPACE"


def difference_driver(socket, first, second, axis):
    try:
        socket.driver_remove("default_value")
    except TypeError:
        pass
    driver = socket.driver_add("default_value").driver
    driver.type = "SCRIPTED"
    transform_variable(driver, "first", first, axis)
    transform_variable(driver, "second", second, axis)
    driver.expression = "first-second"


def world_vector(tree, first, second, label):
    vector = tree.nodes.new("ShaderNodeCombineXYZ")
    vector.name = label
    for axis, socket in enumerate(vector.inputs):
        difference_driver(socket, first, second, axis)
    normal = tree.nodes.new("ShaderNodeVectorMath")
    normal.operation = "NORMALIZE"
    tree.links.new(vector.outputs[0], normal.inputs[0])
    return normal.outputs[0]


def repair_axes(scene):
    helpers = {}
    before = []
    for arm in scene.objects[:]:
        actor = arm.get("performer_id")
        if arm.type != "ARMATURE" or not actor:
            continue
        head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
        controller = bpy.data.objects["Genshin study | head axes | " + actor]
        record = {
            "actor": actor,
            "old_up": list(controller["up"]),
            "old_forward": list(controller["forward"]),
        }
        points = {}
        inverse = (
            arm.matrix_world.to_3x3() @ head.bone.matrix_local.to_3x3()
        ).inverted()
        for label, axis in [
            ("origin", (0, 0, 0)),
            ("up", (0, 0, 1)),
            ("forward", (0, -1, 0)),
        ]:
            point = bpy.data.objects.new(
                "Quality | " + actor + " | head " + label, None
            )
            scene.collection.objects.link(point)
            point.parent = arm
            point.parent_type = "BONE"
            point.parent_bone = head.name
            point.location = inverse @ Vector(axis)
            point.empty_display_size = 0.04
            points[label] = point
        for label in ["up", "forward"]:
            for axis in range(3):
                controller.driver_remove(f'["{label}"]', axis)
                driver = controller.driver_add(f'["{label}"]', axis).driver
                driver.type = "SCRIPTED"
                transform_variable(driver, "first", points[label], axis)
                transform_variable(driver, "second", points["origin"], axis)
                driver.expression = "first-second"
        helpers[actor] = {"arm": arm, "head": head, "controller": controller, **points}
        before.append(record)
    bpy.context.view_layer.update()
    for mat in bpy.data.materials:
        actor = mat.get("performer_id")
        if actor not in helpers or not mat.node_tree:
            continue
        tree = mat.node_tree
        points = helpers[actor]
        key = bpy.data.objects["Reference duet | " + actor + " | key"]
        lighting = world_vector(
            tree, key, points["origin"], "Quality | actual key direction"
        )
        for node in list(tree.nodes):
            if node.name == "Surface | animated head up":
                for axis, socket in enumerate(node.inputs[:3]):
                    difference_driver(socket, points["up"], points["origin"], axis)
            if node.name.startswith("Quality |"):
                continue
            for socket in node.inputs:
                value = getattr(socket, "default_value", None)
                if socket.is_linked or not hasattr(value, "__len__") or len(value) != 3:
                    continue
                if max(abs(a - b) for a, b in zip(value, KEY)) < 0.00001:
                    tree.links.new(lighting, socket)
        for node in tree.nodes:
            if (
                node.type == "GROUP"
                and node.node_tree
                and node.node_tree.name.startswith(
                    "Genshin study | festivities Face Factor"
                )
            ):
                group = node.node_tree
                if group.nodes.get("Quality | actual key direction") is None:
                    incoming = world_vector(
                        group, points["origin"], key, "Quality | actual key direction"
                    )
                    group.links.new(incoming, group.nodes["Vector Math.006"].inputs[0])
                group["quality_light_vector_contract"] = "incoming"
    return helpers, before


def physical_surface(scene, settings):
    actor_meshes = [
        o
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id") and not o.hide_render
    ]
    stages = [
        o
        for o in scene.objects
        if o.type == "MESH" and not o.get("performer_id") and not o.hide_render
    ]
    used = {
        m for o in actor_meshes + stages for m in o.data.materials if m and m.node_tree
    }
    report = []
    for mat in used:
        tree = mat.node_tree
        actor = mat.get("performer_id")
        name = mat.get("source_mmd_material_name", mat.name)
        stage = bool(mat.get("stage_id"))
        if not actor and not stage:
            continue
        if actor and any(
            word in name
            for word in [
                "眉",
                "睫",
                "目",
                "齿",
                "口",
                "二重",
                "> <",
                "rigid",
                "脸红",
                "edge",
            ]
        ):
            continue
        emissions = [n for n in tree.nodes if n.type == "EMISSION"]
        if not emissions:
            continue
        face = actor and name in {"颜", "面1", "面2", "肌"}
        hair = actor and (name == "发" or "发" in name)
        key = (
            "stage_floor"
            if stage
            else "face_floor"
            if face
            else "hair_floor"
            if hair
            else "body_floor"
        )
        diffuse = tree.nodes.new("ShaderNodeBsdfDiffuse")
        diffuse.name = "Quality | white diffuse lighting probe"
        diffuse.inputs["Color"].default_value = (1, 1, 1, 1)
        rgb = tree.nodes.new("ShaderNodeShaderToRGB")
        tree.links.new(diffuse.outputs[0], rgb.inputs[0])
        bw = tree.nodes.new("ShaderNodeRGBToBW")
        tree.links.new(rgb.outputs[0], bw.inputs[0])
        response = tree.nodes.new("ShaderNodeMapRange")
        response.name = "Quality | bounded real illumination"
        response.clamp = True
        response.interpolation_type = "SMOOTHSTEP"
        tree.links.new(bw.outputs[0], response.inputs["Value"])
        for socket, value in [
            ("From Min", settings["physical_response"]["low"]),
            ("From Max", settings["physical_response"]["high"]),
            ("To Min", settings["physical_response"][key]),
            ("To Max", 1),
        ]:
            response.inputs[socket].default_value = value
        ao = tree.nodes.new("ShaderNodeAmbientOcclusion")
        ao.name = "Quality | short-range contact"
        ao.samples = 16
        contact = settings["contact"]
        category = "stage" if stage else "face" if face else "actor"
        ao.inputs["Distance"].default_value = contact[category + "_distance"]
        amount = contact[category + "_strength"]
        ao_response = scalar(
            tree, "ADD", 1 - amount, scalar(tree, "MULTIPLY", ao.outputs["AO"], amount)
        )
        factor = scalar(tree, "MULTIPLY", response.outputs[0], ao_response)
        for emission in emissions:
            socket = emission.inputs["Color"]
            original = (
                socket.links[0].from_socket
                if socket.is_linked
                else tuple(socket.default_value)
            )
            tree.links.new(
                multiply(
                    tree,
                    original,
                    factor,
                    "Quality | preserve chroma with scalar shading",
                ),
                socket,
            )
        report.append(
            {
                "material": mat.name,
                "actor": actor,
                "category": category,
                "floor": settings["physical_response"][key],
            }
        )
    return report


def stabilize_outlines(scene, helpers, settings):
    report = []
    for obj in scene.objects:
        actor = obj.get("performer_id")
        if obj.type != "MESH" or actor not in helpers or obj.hide_render:
            continue
        anchor = helpers[actor]["origin"]
        distance = (
            scene.camera.matrix_world.translation - anchor.matrix_world.translation
        ).length
        reference = distance / scene.camera.data.lens
        for modifier in obj.modifiers:
            if modifier.type != "SOLIDIFY" or "edge" not in modifier.name.lower():
                continue
            base = modifier.thickness
            driver = modifier.driver_add("thickness").driver
            driver.type = "SCRIPTED"
            dist = driver.variables.new()
            dist.name, dist.type = "distance", "LOC_DIFF"
            dist.targets[0].id = scene.camera
            dist.targets[1].id = anchor
            lens = driver.variables.new()
            lens.name = "focal"
            lens.targets[0].id_type = "CAMERA"
            lens.targets[0].id = scene.camera.data
            lens.targets[0].data_path = "lens"
            low, high = settings["minimum_scale"], settings["maximum_scale"]
            driver.expression = f"{base:.12g}*min({high},max({low},distance/max(focal,1)/{reference:.12g}))"
            report.append(
                {
                    "object": obj.name,
                    "modifier": modifier.name,
                    "base_thickness": base,
                    "reference_distance_over_lens": reference,
                }
            )
    return report


def validate_axes(scene, helpers):
    results = []
    for frame in [1, 2100, 4140, 4200, 4250, 4300, 4350, 4400, 4439, 8400, 11899]:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for actor, data in helpers.items():
            arm, head = data["arm"], data["head"]
            for label, axis in [
                ("up", Vector((0, 0, 1))),
                ("forward", Vector((0, -1, 0))),
            ]:
                expected = (
                    arm.matrix_world.to_3x3()
                    @ head.matrix.to_3x3()
                    @ head.bone.matrix_local.to_3x3().inverted()
                    @ arm.matrix_world.to_3x3().inverted()
                    @ axis
                )
                actual = Vector(data["controller"][label])
                error = (expected.normalized() - actual.normalized()).length
                results.append(
                    {
                        "frame": frame,
                        "actor": actor,
                        "axis": label,
                        "error": error,
                        "length": actual.length,
                    }
                )
                if error > 0.0001:
                    raise AssertionError(
                        f"Head axis mismatch: {actor} {label} {frame}: {error}"
                    )
    return results


def native_layers(scene):
    architecture = bpy.data.collections.new("Quality | stage geometry")
    performers = bpy.data.collections.new("Quality | performer geometry")
    scene.collection.children.link(architecture)
    scene.collection.children.link(performers)
    receiver_collections = set()
    for obj in scene.objects:
        if obj.type == "LIGHT" and obj.light_linking.receiver_collection:
            receiver_collections.add(obj.light_linking.receiver_collection)
    for obj in list(scene.objects):
        if obj.type != "MESH":
            continue
        target = performers if obj.get("performer_id") else architecture
        for collection in list(obj.users_collection):
            if collection not in receiver_collections:
                collection.objects.unlink(obj)
        target.objects.link(obj)

    def layer_collection(root, collection):
        if root.collection == collection:
            return root
        for child in root.children:
            found = layer_collection(child, collection)
            if found:
                return found
        return None

    actors = scene.copy()
    actors.name = "Quality | native actor RGBA"
    actors.use_fake_user = True
    actors.render.film_transparent = True
    actors.render.use_compositing = False
    actors.compositing_node_group = None
    background = scene.copy()
    background.name = "Quality | clean stage"
    background.use_fake_user = True
    background.render.use_compositing = False
    background.compositing_node_group = None
    layer_collection(
        actors.view_layers[0].layer_collection, architecture
    ).holdout = True
    layer_collection(
        background.view_layers[0].layer_collection, performers
    ).exclude = True
    for current in [scene, actors, background]:
        for collection in receiver_collections:
            found = layer_collection(
                current.view_layers[0].layer_collection, collection
            )
            if found:
                found.exclude = True
    return actors, background


def render_png(scene, path, frame, percentage=67):
    bpy.context.window.scene = scene
    scene.frame_set(frame)
    scene.render.resolution_percentage = percentage
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-source", type=Path, required=True)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    settings = json.loads(args.preset.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    assert not scene.get("quality_light_space_revision"), (
        "Start from the documented pre-upgrade source; do not stack the integration twice"
    )
    scene.frame_set(4200)
    bpy.context.view_layer.update()
    before = snapshot(scene)
    scene.eevee.taa_render_samples = 32
    render_png(scene, args.output_dir / "baseline-4200.png", 4200)
    fixtures = restore_stage(scene, args.stage_source)
    helpers, old_axes = repair_axes(scene)
    axes = validate_axes(scene, helpers)
    scene.frame_set(4200)
    bpy.context.view_layer.update()
    render_png(scene, args.output_dir / "fixed-space-4200.png", 4200)
    surfaces = physical_surface(scene, settings)
    outlines = stabilize_outlines(scene, helpers, settings["outline"])
    scene.eevee.taa_render_samples = settings["render"]["samples"]
    scene.eevee.shadow_ray_count = settings["render"]["shadow_rays"]
    # Updated fixture locations invalidate the old static lighting cache.
    hidden = [
        (o, o.hide_render)
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id")
    ]
    for obj, _ in hidden:
        obj.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    probe = next(
        o
        for o in scene.objects
        if o.type == "LIGHT_PROBE" and o.data.type == "VOLUME" and not o.hide_render
    )
    probe.select_set(True)
    bpy.context.view_layer.objects.active = probe
    bpy.context.view_layer.update()
    assert bpy.ops.object.lightprobe_cache_bake(subset="SELECTED") == {"FINISHED"}
    for obj, value in hidden:
        obj.hide_render = value
    render_png(scene, args.output_dir / "integrated-4200.png", 4200)
    shadow_flags = [
        (o, o.data.use_shadow)
        for o in scene.objects
        if o.type == "LIGHT" and not o.hide_render
    ]
    for obj, _ in shadow_flags:
        obj.data.use_shadow = False
    render_png(scene, args.output_dir / "control-no-cast-shadows-4200.png", 4200)
    for obj, value in shadow_flags:
        obj.data.use_shadow = value
    render_png(scene, args.output_dir / "integrated-4420.png", 4420)
    scene.frame_set(4200)
    bpy.context.view_layer.update()
    assert before == snapshot(scene), "Original animation or camera changed"
    actor_scene, stage_scene = native_layers(scene)
    actor_scene.frame_set(4200)
    render_png(actor_scene, args.output_dir / "native-actors-4200.png", 4200)
    render_png(stage_scene, args.output_dir / "native-stage-4200.png", 4200)
    bpy.context.window.scene = scene
    scene.render.resolution_percentage = 100
    scene.frame_set(4140)
    scene["quality_light_space_revision"] = settings["id"]
    bpy.ops.file.pack_all()
    project = args.output_dir / "Franken_Duet_Light_Space.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "project": str(project),
        "fixtures": fixtures,
        "old_axes": old_axes,
        "axes_validation": axes,
        "surfaces": surfaces,
        "outlines": outlines,
        "actor_scene": actor_scene.name,
        "stage_scene": stage_scene.name,
        "pose_camera_unchanged_4200": True,
        "settings": settings,
        "status": "still integration; requires visual and motion verification",
    }
    (args.output_dir / "integration-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("LIGHT_SPACE_INTEGRATED", str(project), flush=True)


if __name__ == "__main__":
    main()
