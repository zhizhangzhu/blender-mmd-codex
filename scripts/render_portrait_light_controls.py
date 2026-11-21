"""Render three fingerprint-bound portrait controls without saving a blend.

A: current Clean v2; B: only its two actual scattering boxes hidden;
C: B plus gain two after the current additive HDR rim calculation. The six
art-directed luminous cone volumes remain visible in B/C as a separate factor.
"""

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy

SOURCE = Path(
    "D:/codex/output/MMD-Clean-Game-Characters-v1/production-v2/"
    "Franken_Duet_Clean_Game.blend"
)
SOURCE_SHA = "0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4"
OUTPUT = Path("D:/codex/output/MMD-Portrait-Lighting-Study-2026-11-14/controls-v1")
SCATTERING = {"Wedding | bounded rear scattering", "Bold wedding | bounded beam fan air"}
AKSINIYA_MATERIALS = {
    "前装饰", "前鬓", "后装饰", "呆毛", "头饰", "帽",
    "披肩", "毛领", "腿", "衣", "裙", "鬓",
}
IKHOR_MATERIALS = {"带子", "衣.001", "衣2", "衣领", "裙.001", "鬓.001"}
PREFIX = "Portrait light control | "


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plain(value):
    if value is None or isinstance(value, (bool, str, int, float)):
        return value
    try:
        return [plain(item) for item in value]
    except TypeError:
        return getattr(value, "name_full", str(value))


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def socket_id(socket):
    collection = socket.node.outputs if socket.is_output else socket.node.inputs
    return {"node": socket.node.name, "index": list(collection).index(socket),
            "identifier": socket.identifier, "name": socket.name}


def graph(tree):
    if tree is None:
        return None
    nodes = {}
    for node in tree.nodes:
        item = {"type": node.bl_idname, "mute": node.mute,
                "inputs": [plain(getattr(s, "default_value", None)) for s in node.inputs],
                "outputs": [plain(getattr(s, "default_value", None)) for s in node.outputs]}
        for key in ("operation", "blend_type", "use_clamp", "aov_name",
                    "is_active_output", "interpolation_type", "clamp"):
            if hasattr(node, key):
                item[key] = plain(getattr(node, key))
        for key in ("node_tree", "image"):
            if hasattr(node, key):
                item[key] = plain(getattr(node, key))
        if hasattr(node, "color_ramp"):
            item["ramp"] = {"interpolation": node.color_ramp.interpolation,
                            "elements": [(e.position, list(e.color))
                                         for e in node.color_ramp.elements]}
        nodes[node.name] = item
    links = sorted((link.from_node.name, list(link.from_node.outputs).index(link.from_socket),
                    link.to_node.name, list(link.to_node.inputs).index(link.to_socket))
                   for link in tree.links)
    return {"nodes": nodes, "links": links}


def protected_state(scene):
    """Bounded preservation proof, not the repository's complete production audit."""
    lights = {}
    for obj in scene.objects:
        if obj.type == "LIGHT":
            lights[obj.name] = {
                "matrix": plain(obj.matrix_world), "hide_render": obj.hide_render,
                "settings": {key: plain(getattr(obj.data, key)) for key in (
                    "energy", "color", "diffuse_factor", "specular_factor", "volume_factor",
                    "use_shadow")},
                "receivers": plain(obj.light_linking.receiver_collection),
                "blockers": plain(obj.light_linking.blocker_collection),
            }
    camera = scene.camera
    return {
        "objects": {o.name: {"matrix": plain(o.matrix_world), "hide_render": o.hide_render,
                             "hide_viewport": o.hide_viewport}
                    for o in scene.objects},
        "lights": lights,
        "camera": {"name": camera.name, "matrix": plain(camera.matrix_world),
                   "lens": camera.data.lens, "sensor_width": camera.data.sensor_width,
                   "dof": camera.data.dof.use_dof},
        "world": graph(scene.world.node_tree),
        "materials": {m.name: graph(m.node_tree) for m in bpy.data.materials},
        "groups": {g.name: graph(g) for g in bpy.data.node_groups},
        "color_management": {key: plain(getattr(scene.view_settings, key))
                             for key in ("view_transform", "look", "exposure", "gamma")},
        "frame": scene.frame_current,
    }


def mute_file_outputs():
    records = []
    trees = {g.as_pointer(): g for g in bpy.data.node_groups}
    for scene in bpy.data.scenes:
        tree = scene.compositing_node_group
        if tree:
            trees[tree.as_pointer()] = tree
    for tree in trees.values():
        for node in tree.nodes:
            if node.type == "OUTPUT_FILE":
                records.append({"tree": tree.name, "node": node.name, "old_mute": node.mute})
                node.mute = True
    return records


def volume_inventory(scene):
    records = []
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        for material in obj.data.materials:
            if material is None or material.node_tree is None:
                continue
            for node in material.node_tree.nodes:
                if node.type != "OUTPUT_MATERIAL" or not node.is_active_output:
                    continue
                socket = node.inputs["Volume"]
                if not socket.is_linked:
                    continue
                source = socket.links[0].from_node
                chosen = obj.name in SCATTERING
                if chosen:
                    assert not obj.get("performer_id")
                    assert not node.inputs["Surface"].is_linked
                    assert source.bl_idname == "ShaderNodeVolumeScatter"
                    assert not obj.hide_render
                records.append({
                    "object": obj.name, "material": material.name,
                    "actor": obj.get("performer_id"), "hide_render_before": obj.hide_render,
                    "hide_viewport_before": obj.hide_viewport,
                    "surface_linked": node.inputs["Surface"].is_linked,
                    "volume_source": source.name, "volume_node_type": source.bl_idname,
                    "source_inputs": {s.name: plain(getattr(s, "default_value", None))
                                      for s in source.inputs},
                    "selected": chosen,
                    "reason": "Actual visible scattering-only box" if chosen else
                              "Already hidden historical air" if obj.hide_render else
                              "Independent art-directed luminous volume; keep for this ablation",
                })
    assert {r["object"] for r in records if r["selected"]} == SCATTERING
    return sorted(records, key=lambda r: r["object"])


def downstream(source):
    pending = [link.to_node for link in source.links]
    visited = set()
    signals = {"emission": [], "aovs": [], "adds": []}
    while pending:
        node = pending.pop()
        if node.as_pointer() in visited:
            continue
        visited.add(node.as_pointer())
        if node.type == "EMISSION":
            signals["emission"].append(node.name)
        if node.type == "OUTPUT_AOV":
            signals["aovs"].append(node.aov_name)
        if node.type == "VECT_MATH" and node.operation == "ADD":
            signals["adds"].append(node.name)
        pending.extend(link.to_node for output in node.outputs for link in output.links)
    return {key: sorted(set(value)) for key, value in signals.items()}


def rim_targets():
    targets = []
    found = {"aksiniya": set(), "ikhor": set()}
    for material in bpy.data.materials:
        actor = material.get("performer_id")
        tree = material.node_tree
        if not tree or actor not in found:
            continue
        if actor == "aksiniya":
            role = material.get("character_layer_role")
            if role in {"face", "skin", "features"}:
                continue
            for label in ("aksiniya_head_rim", "aksiniya_body_rim"):
                node = tree.nodes.get("Bold wedding material | " + label + " HDR amount")
                if node is None:
                    continue
                assert node.type == "MATH" and node.operation == "MULTIPLY"
                assert node.inputs[1].is_linked
                assert node.inputs[1].links[0].from_node.name.startswith("Clean Aksiniya | rim |")
                targets.append((material, node.outputs[0], role))
                found[actor].add(material.name)
        elif material.name in IKHOR_MATERIALS:
            role = material.get("ikhor_material_role")
            assert role in {"hair", "cloth"}
            node = tree.nodes.get("Clean Ikhor | rim strength reversible parameter")
            assert node and node.type == "MATH" and node.operation == "MULTIPLY_ADD"
            assert node.inputs[0].links[0].from_node.name == "Clean Ikhor | rim permission"
            targets.append((material, node.outputs[0], role))
            found[actor].add(material.name)
    assert found["aksiniya"] == AKSINIYA_MATERIALS, found
    assert found["ikhor"] == IKHOR_MATERIALS, found
    for material, source, _ in targets:
        reach = downstream(source)
        assert reach["emission"] and reach["adds"], (material.name, reach)
        assert "BoldWeddingEmission" in reach["aovs"], (material.name, reach)
        if material.get("performer_id") == "ikhor":
            assert "StageArtRim" in reach["aovs"], (material.name, reach)
    return targets


def add_rim_gains(targets):
    restore, records = [], []
    for material, source, role in targets:
        tree = material.node_tree
        destinations = [link.to_socket for link in source.links]
        record = {"material": material.name, "actor": material.get("performer_id"),
                  "role": role, "original_output": socket_id(source),
                  "original_consumers": [socket_id(s) for s in destinations],
                  "shared_downstream_consumers": downstream(source), "gain": 2.0}
        node = tree.nodes.new("ShaderNodeMath")
        node.name, node.label = PREFIX + "linear HDR rim gain", "Diagnostic gain 2 after current rim"
        node.operation, node.use_clamp = "MULTIPLY", False
        node.inputs[1].default_value = 2.0
        tree.links.new(source, node.inputs[0])
        for destination in destinations:
            tree.links.new(node.outputs[0], destination)
        restore.append((tree, node, source, destinations))
        records.append(record)
    return restore, records


def restore_gains(restore):
    for tree, node, source, destinations in restore:
        tree.nodes.remove(node)
        for destination in destinations:
            tree.links.new(source, destination)


def camera_driver_record(camera):
    """Require the existing MMD camera RNA before accepting a diagnostic camera."""
    result = []
    for owner in (camera, camera.data, camera.parent):
        if owner is None or not owner.animation_data:
            continue
        for curve in owner.animation_data.drivers:
            driver = curve.driver
            variables = {}
            for variable in driver.variables:
                if variable.type == "SINGLE_PROP":
                    target = variable.targets[0]
                    variables[variable.name] = plain(target.id.path_resolve(target.data_path))
            result.append({"owner": owner.name, "path": curve.data_path,
                           "index": curve.array_index, "expression": driver.expression,
                           "valid": driver.is_valid, "single_prop_values": variables})
            assert driver.is_valid, (owner.name, curve.data_path)
            if curve.data_path == "lens" and "angle" in variables:
                angle = variables["angle"]
                assert angle > 0
                expected = 12.0 / math.tan(angle / 2)
                assert math.isclose(camera.data.lens, expected, rel_tol=0.00001)
    assert camera.data.lens > 2, "Reject the 1mm fallback from missing MMD camera RNA"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    assert args.output_dir.resolve() == OUTPUT.resolve(), "Output is fixed to a fresh controls-v1"
    assert sha(SOURCE) == SOURCE_SHA
    preferences_path = Path(bpy.utils.user_resource("CONFIG")) / "userpref.blend"
    preferences_sha = sha(preferences_path)
    # Saved preferences register the existing MMD Tools camera RNA. Factory
    # startup alone leaves these driver data paths unavailable and is invalid.
    bpy.ops.wm.read_userpref()
    assert "bl_ext.blender_org.mmd_tools" in bpy.context.preferences.addons
    assert getattr(sys.modules.get("bl_ext.blender_org.mmd_tools"), "__addon_enabled__", False)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    report = {"schema": "portrait-light-controls-v1", "source": str(SOURCE),
              "source_sha256_before": SOURCE_SHA, "script": str(Path(__file__).resolve()),
              "script_sha256": sha(__file__), "blender": bpy.app.version_string,
              "saved_preferences_read_only": str(preferences_path),
              "saved_preferences_sha256_before": preferences_sha,
              "mmd_tools_registered_before_reopen": True,
              "records": [], "source_saved": False, "preferences_saved": False,
              "full_song": False, "new_five_seconds": False, "user_art_approval": False,
              "scope": "Three same-frame diagnostic PNGs, source compositor retained. B hides only two scattering boxes; six luminous art cones remain. C doubles existing additive rim sources, excluding face/skin and Reference SCREEN."}
    base_digest = None
    try:
        for label in ("A-current", "B-scattering-off", "C-scattering-off-rim-gain2"):
            assert sha(SOURCE) == SOURCE_SHA
            bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
            scene = bpy.context.scene
            assert scene.name == "Scene" and scene.render.engine == "BLENDER_EEVEE"
            scene.frame_set(4290)
            bpy.context.view_layer.update()
            assert scene.camera and math.isfinite(scene.camera.data.lens) and scene.camera.data.lens > 0
            assert scene.get("clean_game_refinement") == "duet-clean-game-v1"
            common = {"frame": 4290, "camera": scene.camera.name,
                      "camera_lens": scene.camera.data.lens,
                      "camera_drivers": camera_driver_record(scene.camera),
                      "original_resolution": [scene.render.resolution_x, scene.render.resolution_y,
                                              scene.render.resolution_percentage],
                      "original_samples": scene.eevee.taa_render_samples,
                      "original_dof": scene.camera.data.dof.use_dof,
                      "original_motion_blur": scene.render.use_motion_blur,
                      "original_use_compositing": scene.render.use_compositing,
                      "file_outputs_muted": mute_file_outputs()}
            scene.camera.data.dof.use_dof = False
            scene.render.use_motion_blur = False
            scene.render.resolution_x, scene.render.resolution_y = 1280, 720
            scene.render.resolution_percentage = 100
            scene.eevee.taa_render_samples = 48
            scene.render.image_settings.media_type = "IMAGE"
            scene.render.image_settings.file_format = "PNG"
            scene.render.image_settings.color_mode = "RGB"
            scene.render.image_settings.color_depth = "8"
            common["diagnostic_settings"] = {"resolution": [1280, 720, 100], "samples": 48,
                                             "dof": False, "motion_blur": False,
                                             "compositing": scene.render.use_compositing,
                                             "color_management": protected_state(scene)["color_management"]}
            inventory = volume_inventory(scene)
            initial = protected_state(scene)
            initial_digest = digest(initial)
            if base_digest is None:
                base_digest = initial_digest
            assert initial_digest == base_digest, "Fresh reopen did not reproduce the common source state"
            record = {"label": label, "common": common, "volume_inventory": inventory,
                      "common_source_state_sha256": initial_digest, "volume_changes": [],
                      "rim_changes": []}
            hidden = []
            if label != "A-current":
                for name in sorted(SCATTERING):
                    obj = scene.objects[name]
                    hidden.append((obj, obj.hide_render))
                    record["volume_changes"].append({"object": name, "hide_render_before": obj.hide_render,
                                                      "hide_render_after": True})
                    obj.hide_render = True
            restore = []
            if label.startswith("C-"):
                try:
                    targets = rim_targets()
                except (AssertionError, KeyError, ValueError) as exc:
                    record["skipped"] = "Uncertain rim path; A/B remain valid: " + repr(exc)
                    report["records"].append(record)
                    break
                restore, record["rim_changes"] = add_rim_gains(targets)
            bpy.context.view_layer.update()
            image_path = args.output_dir / (label + "-4290.png")
            assert not image_path.exists()
            scene.render.filepath = str(image_path)
            started = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            record["render_seconds"] = time.perf_counter() - started
            assert image_path.is_file() and image_path.stat().st_size > 10000
            record["image"] = str(image_path)
            record["image_sha256"] = sha(image_path)
            record["image_bytes"] = image_path.stat().st_size
            restore_gains(restore)
            for obj, before in hidden:
                obj.hide_render = before
            bpy.context.view_layer.update()
            restored = digest(protected_state(scene))
            record["restored_state_sha256"] = restored
            record["only_declared_transient_controls_changed"] = restored == initial_digest
            assert restored == initial_digest, "Protected state changed beyond reversible declared controls"
            report["records"].append(record)
            (args.output_dir / "control-report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print("PORTRAIT_CONTROL_COMPLETE", label, image_path, flush=True)
        report["three_images_complete"] = len(report["records"]) == 3 and all(
            "image" in record for record in report["records"])
    except Exception as exc:
        report["error"] = repr(exc)
        raise
    finally:
        report["source_sha256_after"] = sha(SOURCE)
        report["source_bytes_unchanged"] = report["source_sha256_after"] == SOURCE_SHA
        report["saved_preferences_sha256_after"] = sha(preferences_path)
        report["saved_preferences_bytes_unchanged"] = (
            report["saved_preferences_sha256_after"] == preferences_sha)
        (args.output_dir / "control-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    assert report["source_bytes_unchanged"]
    assert report["saved_preferences_bytes_unchanged"]
    print("PORTRAIT_CONTROLS_FINISHED", report["three_images_complete"], flush=True)


if __name__ == "__main__":
    main()
