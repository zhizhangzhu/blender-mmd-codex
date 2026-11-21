"""Build a new hash-bound portrait relight and render bounded stills only."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portrait_day_sky as day_sky
import portrait_day_stage as day_stage
import portrait_fur_control as fur
import portrait_key_fill as keyfill
import portrait_rim_ink as rimink
from render_portrait_light_controls import camera_driver_record, mute_file_outputs

REPO = Path(__file__).resolve().parents[1]
SOURCE = Path("D:/codex/output/MMD-Clean-Game-Characters-v1/production-v2/Franken_Duet_Clean_Game.blend")
SOURCE_SHA = "0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lamp_record(obj):
    return {"position": list(obj.matrix_world.translation), "rotation": list(obj.matrix_world.to_quaternion()),
            "energy": obj.data.energy, "color": list(obj.data.color), "size": getattr(obj.data, "size", None),
            "diffuse_factor": obj.data.diffuse_factor, "specular_factor": obj.data.specular_factor,
            "volume_factor": obj.data.volume_factor,
            "receiver_collection": getattr(obj.light_linking.receiver_collection, "name", None)}


def configure_lights(scene, spec):
    result = []
    rotation = scene.camera.matrix_world.to_quaternion()
    for actor in ("aksiniya", "ikhor"):
        origin = scene.objects[f"Quality | {actor} | head origin"].matrix_world.translation.copy()
        for role in ("key", "fill", "rim"):
            obj = scene.objects[f"Reference duet | {actor} | {role}"]
            before = lamp_record(obj)
            distance = (obj.matrix_world.translation - origin).length
            if role + "_direction_head" in spec:
                forward = (scene.objects[f"Quality | {actor} | head forward"].matrix_world.translation - origin).normalized()
                up = (scene.objects[f"Quality | {actor} | head up"].matrix_world.translation - origin).normalized()
                right = forward.cross(up).normalized()
                up = right.cross(forward).normalized()
                x, y, z = spec[role + "_direction_head"]
                direction = (right * x + forward * y + up * z).normalized()
            else:
                direction = rotation @ Vector(spec[role + "_direction_camera"]).normalized()
            point = origin + direction * distance
            orientation = (origin - point).to_track_quat("-Z", "Y")
            obj.matrix_world = Matrix.Translation(point) @ orientation.to_matrix().to_4x4()
            obj.data.energy = spec[role + "_energy"]
            obj.data.color = spec[role + "_color"]
            if hasattr(obj.data, "size"):
                obj.data.size = spec[role + "_size"]
            obj.data.volume_factor = 0
            obj.data.specular_factor = spec.get(role + "_specular_factor", obj.data.specular_factor)
            result.append({"object": obj.name, "before": before, "after": lamp_record(obj)})
        reflection = scene.objects.get(f"Reference duet | {actor} | reflection")
        if reflection and "reflection_specular_factor" in spec:
            before = lamp_record(reflection)
            reflection.data.specular_factor = spec["reflection_specular_factor"]
            result.append({"object": reflection.name, "before": before, "after": lamp_record(reflection)})
    bpy.context.view_layer.update()
    return result


def stage(scene, spec):
    changes = {"hidden_volumes": [], "lights": [], "glows": []}
    for name in spec["hidden_volumes"]:
        obj = scene.objects[name]
        assert obj.type == "MESH" and not obj.get("performer_id"), name
        assert any(m and m.use_nodes and any(n.type == "OUTPUT_MATERIAL" and n.inputs["Volume"].is_linked for n in m.node_tree.nodes) for m in obj.data.materials), name
        changes["hidden_volumes"].append({"object": name, "before": obj.hide_render, "after": True,
                                          "viewport_before": obj.hide_viewport, "viewport_after": True})
        obj.hide_render = True
        obj.hide_viewport = True
    for name, factor in spec["stage_light_multipliers"].items():
        obj = scene.objects[name]
        before = lamp_record(obj)
        obj.data.energy *= factor
        if name in spec.get("stage_light_colors", {}):
            obj.data.color = spec["stage_light_colors"][name]
        changes["lights"].append({"object": name, "before": before, "after": lamp_record(obj)})
    tree = scene.compositing_node_group
    for node in tree.nodes:
        if node.type == "GLARE" and node.inputs.get("Strength"):
            socket = node.inputs["Strength"]
            assert not socket.is_linked, node.name
            before = socket.default_value
            socket.default_value *= spec["glow_strength_multiplier"]
            changes["glows"].append({"node": node.name, "before": before, "after": socket.default_value})
    return changes


def stage_midtones(scene, settings):
    """Shot art direction in scene-linear compositing; never a physical light."""
    if not settings.get("enabled"):
        return None
    tree = scene.compositing_node_group
    output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    previous = output.inputs["Image"].links[0].from_socket
    crypto = tree.nodes["Caption | both performers native object coverage"]
    assert "Ikhor | mesh | Ikhor_mesh" in crypto.matte_id and "阿克西妮娅2_mesh" in crypto.matte_id
    bw = tree.nodes.new("CompositorNodeRGBToBW")
    bw.name = "Portrait relight | stage luminance"
    tree.links.new(previous, bw.inputs[0])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.name = "Portrait relight | stage midtones only"
    ramp.color_ramp.interpolation = "EASE"
    while len(ramp.color_ramp.elements) < len(settings["ramp"]):
        ramp.color_ramp.elements.new(0.5)
    for element, (position, value) in zip(ramp.color_ramp.elements, settings["ramp"]):
        element.position, element.color = position, (value, value, value, 1)
    tree.links.new(bw.outputs[0], ramp.inputs[0])
    inverse = tree.nodes.new("ShaderNodeMath")
    inverse.name, inverse.operation = "Portrait relight | outside both actors", "SUBTRACT"
    inverse.inputs[0].default_value = 1
    tree.links.new(crypto.outputs["Matte"], inverse.inputs[1])
    mask = tree.nodes.new("ShaderNodeMath")
    mask.name, mask.operation = "Portrait relight | protected stage midtones", "MULTIPLY"
    tree.links.new(inverse.outputs[0], mask.inputs[0])
    tree.links.new(ramp.outputs[0], mask.inputs[1])
    amount = tree.nodes.new("ShaderNodeMath")
    amount.name, amount.operation = "Portrait relight | stage holdback amount", "MULTIPLY"
    tree.links.new(mask.outputs[0], amount.inputs[0])
    amount.inputs[1].default_value = settings["amount"]
    grade = tree.nodes.new("ShaderNodeMixRGB")
    grade.name, grade.blend_type = "Portrait relight | hold back stage only", "MULTIPLY"
    tree.links.new(amount.outputs[0], grade.inputs[0])
    tree.links.new(previous, grade.inputs[1])
    grade.inputs[2].default_value = settings["tint"]
    tree.links.new(grade.outputs[0], output.inputs["Image"])
    beauty = tree.nodes["Caption cache | beauty"]
    tree.links.new(grade.outputs[0], beauty.inputs["beauty"])
    return {"settings": settings, "actor_mask": crypto.matte_id, "semantics": "scene-linear compositor stage midtone holdback with native both-actor Crypto protection; not a lamp or shadow pass"}


def environment_lights(scene, settings):
    """Broad architecture fills; actor NPR fill remains an independent signal."""
    if not settings:
        return None
    receivers = bpy.data.collections.new("Portrait v2 | architecture receivers")
    for obj in scene.objects:
        if obj.type == "MESH" and not obj.get("performer_id") and not obj.hide_render:
            receivers.objects.link(obj)
    changes = []
    for spec in settings:
        name = "Portrait v2 | " + spec["name"]
        assert name not in scene.objects
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.color = spec["energy"], spec["color"]
        data.shape, data.size = "DISK", spec["size"]
        data.diffuse_factor, data.specular_factor, data.volume_factor = 1, 0.3, 0
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = spec["location"]
        obj.rotation_euler = (Vector(spec["target"]) - obj.location).to_track_quat("-Z", "Y").to_euler()
        obj.light_linking.receiver_collection = receivers
        changes.append({"object": name, "settings": spec, "actual": lamp_record(obj)})
    return {"lights": changes, "receivers": receivers.name,
            "receiver_count": len(receivers.objects), "actor_meshes_excluded": True,
            "semantics": "actual broad area lights linked to visible non-performer meshes; no new fog"}


def physical_highlights(settings):
    """Recalibrate only existing Clean masked gold deltas, retaining masks."""
    changes = []
    for name in settings.get("materials", []):
        tree = bpy.data.materials[name].node_tree
        for label, base, target in (("roughness", 0.70, settings["gold_roughness"]),
                                    ("physical mix", 0.12, settings["gold_physical_mix"])):
            node = tree.nodes[f"Clean Ikhor | gold {label} mask delta delta"]
            assert node.operation == "SUBTRACT" and not node.inputs[0].is_linked
            before = node.inputs[0].default_value
            node.inputs[0].default_value = target - base
            changes.append({"material": name, "node": node.name, "input": 0,
                            "before": before, "after": node.inputs[0].default_value,
                            "masked_gold_endpoint": target, "white_endpoint_preserved": base})
    return changes


def actor_accent_lights(scene, settings):
    """Small actor-linked beauty fills on top of the separate daylight hall."""
    if not settings:
        return []
    rotation = scene.camera.matrix_world.to_quaternion()
    changes = []
    for actor in ("aksiniya", "ikhor"):
        origin = scene.objects[f"Quality | {actor} | head origin"].matrix_world.translation.copy()
        direction = rotation @ Vector(settings["direction_camera"]).normalized()
        point = origin + direction * settings["distance"]
        name = "Portrait daylight | " + actor + " | beauty soft fill"
        assert name not in scene.objects
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.color = settings["energy"], settings["color"]
        data.shape, data.size = "DISK", settings["size"]
        data.diffuse_factor, data.specular_factor, data.volume_factor = 0.12, 0.22, 0
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = point
        obj.rotation_euler = (origin - point).to_track_quat("-Z", "Y").to_euler()
        obj.light_linking.receiver_collection = scene.objects[f"Reference duet | {actor} | key"].light_linking.receiver_collection
        changes.append({"actor": actor, "light": name, "actual": lamp_record(obj)})
    return changes


def daylight_compositor(scene, settings):
    """Remove the specifically retained night hierarchy, not a global exposure."""
    if not settings.get("bypass_legacy_foreground_holdback"):
        return None
    tree = scene.compositing_node_group
    node = tree.nodes["Reference transfer | foreground hierarchy with actor protection"]
    before = [{"node": link.from_node.name, "socket": link.from_socket.identifier} for link in node.inputs[0].links]
    for link in list(node.inputs[0].links):
        tree.links.remove(link)
    node.inputs[0].default_value = 0
    return {"node": node.name, "old_factor_sources": before, "factor": 0,
            "semantics": "bypass only the old stage foreground dimming; actor lighting and the synchronized caption beauty path remain"}


def window_sunlight(scene, settings):
    if not settings:
        return None
    data = bpy.data.lights.new("Portrait daylight | exterior sun", "SUN")
    data.energy, data.color = settings["energy"], settings["color"]
    data.angle = settings["angle_radians"]
    data.use_shadow = True
    obj = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(obj)
    obj.location = settings["location"]
    obj.rotation_euler = (Vector(settings["target"]) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return {"name": obj.name, "settings": settings,
            "semantics": "directional exterior sun, real scene geometry casts shadows; location is illustrative, orientation controls sunlight"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--settings", type=Path, default=REPO / "presets/lighting/portrait-relight-v1.json")
    parser.add_argument("--variant", choices=("baseline", "stage", "subject", "complete"), default="complete")
    parser.add_argument("--frame", type=int, default=4290)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--samples", type=int, default=48)
    parser.add_argument("--dof", action="store_true")
    parser.add_argument("--save-project", action="store_true")
    parser.add_argument("--diagnostic", choices=("face-and-no-specular",))
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    assert not (args.diagnostic and args.save_project), "Signal diagnostics must never be saved as a production project"
    assert not args.output_dir.exists(), "Use a new output directory"
    assert args.output_dir.resolve().is_relative_to(Path("D:/codex/output").resolve())
    assert sha(SOURCE) == SOURCE_SHA
    settings = json.loads(args.settings.read_text(encoding="utf-8-sig"))
    assert settings["source_sha256"] == SOURCE_SHA
    preference = Path(bpy.utils.user_resource("CONFIG")) / "userpref.blend"
    preference_sha = sha(preference)
    bpy.ops.wm.read_userpref()
    bpy.ops.preferences.addon_enable(module="bl_ext.blender_org.mmd_tools")
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.frame_set(args.frame)
    bpy.context.view_layer.update()
    camera_drivers = camera_driver_record(scene.camera)
    assert scene.render.engine == "BLENDER_EEVEE" and scene.camera.data.lens > 2
    args.output_dir.mkdir(parents=True)
    report = {"source": str(SOURCE), "source_sha256": SOURCE_SHA, "settings_path": str(args.settings),
              "settings_sha256": sha(args.settings), "settings": settings, "variant": args.variant,
              "frame": args.frame, "camera": scene.camera.name, "camera_lens": scene.camera.data.lens,
              "camera_drivers": camera_drivers, "file_outputs_muted": mute_file_outputs(),
              "script_sha256": sha(__file__), "modules": {m.__name__: sha(m.__file__) for m in (keyfill, rimink, fur, day_sky, day_stage)}}
    if args.variant != "baseline":
        report["stage"] = stage(scene, settings)
        report["character_lights"] = configure_lights(scene, settings["character_lights"])
        report["environment_lights"] = environment_lights(scene, settings.get("environment_lights", []))
        if "day_stage" in settings:
            report["day_stage"] = day_stage.apply(scene, settings["day_stage"])
        if "day_sky" in settings:
            report["day_sky"] = day_sky.apply(scene, settings["day_sky"])
        report["actor_accent_lights"] = actor_accent_lights(scene, settings.get("actor_accent_lights", {}))
        report["window_sunlight"] = window_sunlight(scene, settings.get("window_sunlight", {}))
    if args.variant in ("subject", "complete"):
        report["key_fill"] = keyfill.apply(scene, settings["key_fill"])
    if args.variant == "complete":
        report["rim_ink"] = rimink.apply(scene, settings["rim_ink"])
        report["fur"] = fur.apply(scene, settings.get("fur", {}))
        report["physical_highlights"] = physical_highlights(settings.get("physical_highlights", {}))
    if args.variant != "baseline":
        report["stage_midtones"] = stage_midtones(scene, settings.get("stage_midtones", {}))
        report["daylight_compositor"] = daylight_compositor(scene, settings.get("daylight_compositor", {}))
    if args.diagnostic:
        changes = []
        for obj in scene.objects:
            if obj.type == "LIGHT" and obj.name.startswith("Reference duet |"):
                changes.append({"name": obj.name, "specular_before": obj.data.specular_factor})
                obj.data.specular_factor = 0
        tree = bpy.data.materials["颜.001"].node_tree
        tree.links.new(tree.nodes["Portrait relight | keyfill | face proxy soft form"].outputs[0],
                       tree.nodes["Ikhor character | controlled NPR surface"].inputs["Color"])
        socket = tree.nodes["Ikhor character | toon and material physical closure"].inputs[0]
        for link in list(socket.links):
            tree.links.remove(link)
        socket.default_value = 0
        report["diagnostic"] = {"id": args.diagnostic, "specular_disabled_lights": changes,
                                "face": "Ikhor raw analytic soft form, no physical closure; grayscale signal only"}
    scene.frame_set(args.frame)
    bpy.context.view_layer.update()
    assert all(scene.objects[name].hide_render for name in ("Bold wedding | blue vow arc", "Bold wedding | gold vow arc"))
    scene.render.resolution_x, scene.render.resolution_y = args.width, round(args.width * 9 / 16)
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = args.samples
    scene.render.use_motion_blur = False
    scene.camera.data.dof.use_dof = args.dof
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(args.output_dir / f"{args.variant}-{args.frame}.png")
    scene["portrait_relight_id"] = settings["id"]
    scene["portrait_relight_source_sha256"] = SOURCE_SHA
    scene["portrait_relight_scope"] = "still-only; original full Actions retained; no new simulation/video validation"
    report["render"] = {"resolution": [scene.render.resolution_x, scene.render.resolution_y],
                        "samples": args.samples, "dof": args.dof, "motion_blur": False,
                        "view_transform": scene.view_settings.view_transform, "look": scene.view_settings.look,
                        "exposure": scene.view_settings.exposure, "gamma": scene.view_settings.gamma}
    write(args.output_dir / "preparation.json", report)
    if args.save_project:
        project = args.output_dir / "Franken_Duet_Portrait_Relight.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(project), check_existing=False)
        report["project"] = str(project)
        report["project_sha256"] = sha(project)
    start = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    report["render_seconds"] = time.perf_counter() - start
    picture = Path(scene.render.filepath)
    assert picture.is_file()
    report["picture"] = str(picture)
    report["picture_sha256"] = sha(picture)
    report["source_unchanged"] = sha(SOURCE) == SOURCE_SHA
    report["preferences_unchanged"] = sha(preference) == preference_sha
    assert report["source_unchanged"] and report["preferences_unchanged"]
    write(args.output_dir / "preparation.json", report)
    print("PORTRAIT_RELIGHT_STILL_COMPLETE", picture, flush=True)


if __name__ == "__main__":
    main()
