"""Blender-only isolated scene inspection and explicitly mapped static controls.

Invoked through studio_bench. Sources are reopened for every case and never saved.
"""

import argparse
from array import array
import hashlib
import html
import json
import math
import os
from pathlib import Path
import sys
import traceback

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import studio_scene_contract as contract


def plain(value):
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value
    if hasattr(value, "to_list"):
        return value.to_list()
    if hasattr(value, "name"):
        return value.name
    try:
        return [plain(v) for v in value]
    except TypeError:
        return str(value)


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def compositor(scene):
    return getattr(scene, "compositing_node_group", None) or getattr(scene, "node_tree", None)


def walk_trees(tree, seen=None):
    seen = set() if seen is None else seen
    if tree is None or tree.as_pointer() in seen:
        return
    seen.add(tree.as_pointer())
    yield tree
    for node in tree.nodes:
        if node.type == "GROUP" and node.node_tree:
            yield from walk_trees(node.node_tree, seen)


def silence_outputs():
    records = []
    seen = set()
    for scene in bpy.data.scenes:
        scene.render.use_sequencer = False
        for tree in walk_trees(compositor(scene), seen):
            for node in tree.nodes:
                if node.type == "OUTPUT_FILE":
                    records.append({"scene": scene.name, "tree": tree.name, "node": node.name, "previous_mute": node.mute})
                    node.mute = True
    return records


def simulation_hazards():
    """Conservative refusal, not a claim to prove cache validity or GN semantics."""
    hazards = []
    for scene in bpy.data.scenes:
        world = scene.rigidbody_world
        if world and world.enabled:
            hazards.append(f"{scene.name}: active rigidbody world")
        if world:
            ad = getattr(scene, "animation_data", None)
            if ad and (ad.action or ad.nla_tracks or driver_state(scene, "rigidbody_world.enabled")):
                hazards.append(f"{scene.name}: animated rigidbody enablement")
    for obj in bpy.data.objects:
        for mod in obj.modifiers:
            reasons = []
            if mod.type in {"CLOTH", "SOFT_BODY", "FLUID", "DYNAMIC_PAINT", "PARTICLE_SYSTEM"}:
                reasons.append(mod.type)
            if mod.type == "NODES" and mod.node_group:
                for tree in walk_trees(mod.node_group):
                    if any(n.bl_idname in {"GeometryNodeSimulationInput", "GeometryNodeSimulationOutput"} for n in tree.nodes):
                        reasons.append(f"geometry simulation in {tree.name}")
            if not reasons:
                continue
            ad = getattr(obj, "animation_data", None)
            if ad and (ad.action or ad.nla_tracks or any(driver_state(obj, mod.path_from_id(flag)) for flag in ("show_render", "show_viewport"))):
                hazards.append(f"{obj.name}/{mod.name}: animated simulation enablement")
            if mod.show_render or mod.show_viewport:
                hazards.extend(f"{obj.name}/{mod.name}: {reason}" for reason in reasons)
    return sorted(set(hazards))


def prepare_runtime(runtime, registration):
    configured_version = runtime.get("version_tuple")
    if configured_version is None:
        configured_version = [int(n) for n in runtime["version"].split(".")]
    if len(configured_version) != 3 or any(type(n) is not int for n in configured_version) or tuple(bpy.app.version[:3]) != tuple(configured_version):
        raise ValueError("Unsupported runtime version; refuse before loading source")
    if bpy.app.build_hash.decode() != runtime["build_hash"]:
        raise ValueError("Runtime build differs from pinned configuration")
    for node_type in runtime.get("required_node_types", []):
        if not hasattr(bpy.types, node_type):
            raise ValueError("Required runtime node is absent: " + node_type)
    for key, env_name in (("user_config", "BLENDER_USER_CONFIG"), ("user_scripts", "BLENDER_USER_SCRIPTS")):
        if Path(os.environ.get(env_name, "")).resolve() != Path(runtime[key]).resolve():
            raise ValueError("Isolated runtime environment missing: " + env_name)
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    if registration == "mmd_tools":
        scripts = Path(runtime["user_scripts"])
        sys.path.insert(0, str(scripts / "modules"))
        sys.path.insert(0, str(scripts / "addons"))
        import addon_utils
        module = addon_utils.enable("mmd_tools", default_set=False, persistent=True)
        if not module or not Path(module.__file__).resolve().is_relative_to((scripts / "addons").resolve()):
            raise ValueError("Portable MMD camera dependency failed registration")


def open_source(profile):
    if contract.digest(profile["source"]["path"]).lower() != profile["source"]["sha256"].lower():
        raise ValueError("Source fingerprint changed before open")
    bpy.ops.wm.open_mainfile(filepath=profile["source"]["path"], load_ui=False, use_scripts=False)
    scene = bpy.data.scenes.get(profile["scene"]["name"])
    if scene is None:
        raise ValueError("Exact scene not present")
    if bpy.context.window:
        bpy.context.window.scene = scene
    muted = silence_outputs()
    return scene, muted


def driver_state(owner, path=None):
    ad = getattr(owner, "animation_data", None)
    if not ad:
        return []
    return [{"path": fc.data_path, "index": fc.array_index, "valid": fc.driver.is_valid,
             "expression": fc.driver.expression} for fc in ad.drivers if path is None or fc.data_path == path]


def property_protection(owner, path):
    ad = getattr(owner, "animation_data", None)
    return {"driven": bool(driver_state(owner, path)),
            "animated": bool(ad and (ad.action or ad.nla_tracks))}


def node_record(node):
    inputs = []
    for socket in node.inputs:
        path = socket.path_from_id("default_value") if hasattr(socket, "default_value") else None
        ad = getattr(node.id_data, "animation_data", None)
        inputs.append({"name": socket.name, "identifier": socket.identifier,
                       "value": plain(getattr(socket, "default_value", None)), "linked": socket.is_linked,
                       "driven": bool(driver_state(node.id_data, path)) if path else False,
                       "animated": bool(ad and (ad.action or ad.nla_tracks))})
    return {"name": node.name, "type": node.type, "bl_idname": node.bl_idname, "inputs": inputs,
            "mute": node.mute,
            "output_links": {s.identifier: len(s.links) for s in node.outputs},
            "outputs": [s.name for s in node.outputs]}


def camera_record(scene, evaluated=True):
    camera = scene.camera
    if not camera:
        raise ValueError("Missing scene camera")
    current = camera.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else camera
    data = current.data
    ancestors, owner = [], camera
    while owner is not None and owner not in ancestors:
        ancestors.append(owner)
        owner = owner.parent
    result = {"name": camera.name, "lens_mm": data.lens, "type": data.type,
              "sensor_width": data.sensor_width, "sensor_height": data.sensor_height,
              "shift_x": data.shift_x, "shift_y": data.shift_y,
              "matrix_world": plain(current.matrix_world),
              "evaluation": "evaluated_depsgraph" if evaluated else "stored_data_no_depsgraph_request",
              "dof": {key: plain(getattr(data.dof, key)) for key in ("use_dof", "focus_object", "focus_distance", "aperture_fstop", "aperture_blades", "aperture_rotation", "aperture_ratio")},
              "drivers": [{"owner": owner.name, "drivers": driver_state(owner)} for owner in [camera.data, *ancestors]]}
    return result


def active_undefined(tree):
    """Structural upstream traversal; mix branches are conservatively all traversed."""
    result, visited = [], set()
    def socket_up(socket):
        for link in socket.links:
            node_up(link.from_node, link.from_socket.identifier)
    def node_up(node, output):
        key = (node.id_data.as_pointer(), node.as_pointer(), output)
        if key in visited:
            return
        visited.add(key)
        if node.bl_idname == "NodeUndefined" or node.type == "UNDEFINED":
            result.append(f"{node.id_data.name}/{node.name}")
        if node.type == "GROUP" and node.node_tree:
            for group_output in node.node_tree.nodes:
                if group_output.type == "GROUP_OUTPUT" and group_output.is_active_output:
                    found = next((s for s in group_output.inputs if s.identifier == output), None)
                    if found:
                        socket_up(found)
                    else:
                        for s in group_output.inputs:
                            socket_up(s)
        for socket in node.inputs:
            socket_up(socket)
    if tree:
        for node in tree.nodes:
            if node.type == "OUTPUT_MATERIAL" and node.is_active_output:
                for socket in node.inputs:
                    socket_up(socket)
    return sorted(set(result))


def inventory(profile, scene, muted):
    objects = []
    materials = set()
    for obj in bpy.data.objects:
        mats = [s.material.name for s in obj.material_slots if s.material]
        materials.update(mats)
        objects.append({"name": obj.name, "type": obj.type, "materials": mats,
            "modifiers": [m.name for m in obj.modifiers],
            "modifier_states": {m.name: m.show_render for m in obj.modifiers},
            "armature_targets": [m.object.name for m in obj.modifiers if m.type == "ARMATURE" and m.object],
            "hide_render": obj.hide_render,
            "scene_local": obj.name in scene.objects,
            "control_protection": {"energy": property_protection(obj.data, "energy") if obj.type == "LIGHT" else {},
                "hide_render": property_protection(obj, "hide_render"),
                "modifiers": {m.name: property_protection(obj, m.path_from_id("show_render")) for m in obj.modifiers}},
            "energy": obj.data.energy if obj.type == "LIGHT" else None})
    camera = camera_record(scene, evaluated=False)
    material_records = []
    for name in sorted(materials):
        mat = bpy.data.materials[name]
        tree = mat.node_tree
        material_records.append({"name": name, "nodes": [node_record(n) for n in tree.nodes] if tree else [],
            "custom_properties": {key: plain(mat[key]) for key in ("look_category", "ikhor_material_role", "performer_id") if key in mat},
            "active_undefined": active_undefined(tree)})
    return {"schema_version": 1, "source": profile["source"],
        "runtime": {"version": bpy.app.version_string, "build": bpy.app.build_hash.decode()},
        "scene": {"name": scene.name, "camera": camera["name"], "lens_mm": camera["lens_mm"],
                  "frame": scene.frame_current, "engine": scene.render.engine},
        "camera": camera, "objects": objects, "materials": material_records,
        "lights": [{"name": o.name, "type": o.data.type, "energy": o.data.energy,
                    "color": plain(o.data.color), "location": plain(o.location), "rotation": plain(o.rotation_euler),
                    "matrix_world": plain(o.matrix_world), "size": getattr(o.data, "size", None),
                    "data_properties": {p.identifier: plain(getattr(o.data, p.identifier)) for p in o.data.bl_rna.properties if p.identifier.startswith(("use_", "light_group")) and p.type != "COLLECTION"},
                    "drivers": driver_state(o) + driver_state(o.data)} for o in bpy.data.objects if o.type == "LIGHT"],
        "compositor": [{"scene": s.name, "nodes": [node_record(n) for n in compositor(s).nodes] if compositor(s) else [],
                        "tree_users": [other.name for other in bpy.data.scenes if compositor(s) and compositor(other) == compositor(s)]} for s in bpy.data.scenes],
        "muted_file_outputs": muted, "simulation_hazards": simulation_hazards(),
        "limits": "Inventory and upstream structure only; no semantic inference, simulation, source save or art approval"}


def mesh_signature(profile):
    result = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for actor in profile["actors"]:
        for name in actor["objects"]:
            obj = bpy.data.objects[name].evaluated_get(depsgraph)
            mesh = obj.to_mesh()
            try:
                values = array("f", [0.0]) * (3 * len(mesh.vertices))
                mesh.vertices.foreach_get("co", values)
                result[name] = {"vertices": len(mesh.vertices), "coordinates_sha256": hashlib.sha256(values.tobytes()).hexdigest(),
                                "world": plain(obj.matrix_world)}
            finally:
                obj.to_mesh_clear()
    return result


def switch_readback(selector):
    kind = selector["kind"]
    if kind == "node_input":
        node = bpy.data.materials[selector["material"]].node_tree.nodes[selector["node"]]
        return plain(find_socket(node, selector["socket"], selector.get("socket_match") == "identifier").default_value)
    if kind == "light_energy":
        return bpy.data.objects[selector["object"]].data.energy
    if kind == "object_hide":
        return bpy.data.objects[selector["object"]].hide_render
    if kind == "modifier_enabled":
        return bpy.data.objects[selector["object"]].modifiers[selector["modifier"]].show_render
    if kind == "glow_bypass":
        # Rewiring is static topology; every named original Glare output must
        # have no consumers after bypass, including its effect-only branch.
        return all(not compositor(bpy.data.scenes[s["scene"]]).nodes[s["node"]].outputs[name].is_linked
                   for s in selector["nodes"] for name in (s["image_output"], s["glare_output"]))
    raise ValueError("Unknown switch")


def check_overrides(profile, case):
    result = []
    for override in case["overrides"]:
        actual = switch_readback(profile["switches"][override["switch"]])
        if not contract.equal(actual, override["value"]):
            raise ValueError("Requested switch did not survive evaluation: " + override["switch"])
        result.append({"switch": override["switch"], "requested": override["value"], "actual": actual})
    return result


def action_summary():
    return sorted((a.name, plain(a.frame_range), len(a.slots), len(a.layers)) for a in bpy.data.actions)


def find_socket(node, name, identifier_only=False):
    matches = [s for s in node.inputs if s.identifier == name or (not identifier_only and s.name == name)]
    if len(matches) != 1:
        raise ValueError("Socket absent or ambiguous: " + name)
    return matches[0]


def apply_switch(selector, value):
    kind = selector["kind"]
    if kind == "node_input":
        node = bpy.data.materials[selector["material"]].node_tree.nodes[selector["node"]]
        socket = find_socket(node, selector["socket"], selector.get("socket_match") == "identifier")
        path = socket.path_from_id("default_value")
        if socket.is_linked or driver_state(node.id_data, path):
            raise ValueError("Linked/driven controls cannot be assigned")
        socket.default_value = value
    elif kind == "light_energy":
        obj = bpy.data.objects[selector["object"]]
        if obj.data.users > 1:
            raise ValueError("Shared light data requires an explicit adaptation, not a silent multi-object change")
        obj.data.energy = value
    elif kind == "object_hide":
        bpy.data.objects[selector["object"]].hide_render = value
    elif kind == "modifier_enabled":
        bpy.data.objects[selector["object"]].modifiers[selector["modifier"]].show_render = value
    elif kind == "glow_bypass":
        if value is not True:
            raise ValueError("glow_bypass only supports explicit true")
        for selected in selector["nodes"]:
            tree = compositor(bpy.data.scenes[selected["scene"]])
            node = tree.nodes[selected["node"]]
            image = node.inputs.get("Image")
            if image is None or not image.is_linked:
                raise ValueError("Glare Image needs an actual upstream source")
            source = image.links[0].from_socket
            zero = tree.nodes.new("CompositorNodeRGB")
            zero.outputs[0].default_value = (0, 0, 0, 0)
            for output_name, replacement in ((selected["image_output"], source), (selected["glare_output"], zero.outputs[0])):
                output = node.outputs.get(output_name)
                if output is None:
                    raise ValueError("Missing explicit Glare output: " + output_name)
                for link in list(output.links):
                    destination = link.to_socket
                    tree.links.remove(link)
                    tree.links.new(replacement, destination)
    else:
        raise ValueError("Unknown switch kind")


def render_case(profile, case, output):
    scene, muted = open_source(profile)
    hazards = simulation_hazards()
    if hazards:
        raise ValueError("Active simulation refused before frame evaluation: " + "; ".join(hazards))
    # Markers can replace the active camera while setting the requested frame.
    markers = [(marker, marker.camera) for marker in scene.timeline_markers if marker.camera]
    for marker, camera in markers:
        marker.camera = None
    scene.frame_set(case["frame"])
    camera = scene.objects.get(profile["scene"]["camera"])
    if camera is None or camera.type != "CAMERA":
        raise ValueError("Exact camera not in selected scene")
    scene.camera = camera
    bpy.context.view_layer.update()
    current = inventory(profile, scene, muted)
    bound = contract.bind(profile, current)
    if not bound["passed"]:
        raise ValueError("; ".join(bound["errors"]))
    active_missing = [node for mat in current["materials"] for node in mat["active_undefined"]]
    if active_missing:
        raise ValueError("Undefined nodes upstream of material output: " + "; ".join(active_missing))
    if scene.render.engine != "BLENDER_EEVEE":
        raise ValueError("This diagnostic runner supports only pinned EEVEE scenes")
    for override in case["overrides"]:
        apply_switch(profile["switches"][override["switch"]], override["value"])
    hazards = simulation_hazards()
    if hazards:
        raise ValueError("Override activates a simulation: " + "; ".join(hazards))
    settings = profile["render"]
    scene.render.resolution_x = settings["width"]
    scene.render.resolution_y = settings["height"]
    scene.render.resolution_percentage = 100
    scene.render.use_border = False
    if hasattr(scene.render, "use_motion_blur"):
        scene.render.use_motion_blur = False
    if not hasattr(scene, "eevee") or not hasattr(scene.eevee, "taa_render_samples"):
        raise ValueError("Pinned runtime does not expose the expected EEVEE sample setting")
    scene.eevee.taa_render_samples = settings["samples"]
    if settings["dof"] != "source":
        camera.data.dof.use_dof = settings["dof"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str((output / ("case-" + case["id"] + ".png")).resolve())
    bpy.context.view_layer.update()
    before_camera, before_mesh, before_actions = camera_record(scene), mesh_signature(profile), action_summary()
    if any(not d["valid"] for owner in before_camera["drivers"] for d in owner["drivers"]):
        raise ValueError("Invalid camera or ancestor driver")
    if profile["scene"]["registration"] == "mmd_tools" and before_camera["type"] == "PERSP" and before_camera["lens_mm"] <= 2:
        raise ValueError("MMD camera has known fallback focal length")
    check_overrides(profile, case)
    bpy.ops.render.render(write_still=True, scene=scene.name)
    after_camera, after_mesh, after_actions = camera_record(scene), mesh_signature(profile), action_summary()
    switch_results = check_overrides(profile, case)
    if before_camera != after_camera or before_mesh != after_mesh or before_actions != after_actions:
        raise ValueError("Camera/pose/action summary changed during static render")
    path = Path(scene.render.filepath)
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        dimensions = list(image.size)
    finally:
        bpy.data.images.remove(image)
    if dimensions != [settings["width"], settings["height"]]:
        raise ValueError("Rendered PNG dimensions differ from requested diagnostic size")
    result = {"id": case["id"], "frame": case["frame"], "overrides": case["overrides"],
              "path": str(path), "sha256": contract.digest(path), "camera": after_camera,
              "render": settings, "engine": scene.render.engine,
              "effective_render": {"dimensions": dimensions, "samples": scene.eevee.taa_render_samples,
                  "dof": camera.data.dof.use_dof, "motion_blur": getattr(scene.render, "use_motion_blur", None)},
              "color": {"view_transform": scene.view_settings.view_transform, "look": scene.view_settings.look,
                        "exposure": scene.view_settings.exposure, "gamma": scene.view_settings.gamma},
              "mesh_signature": after_mesh, "bounded_action_summary_sha256": fingerprint(after_actions),
              "muted_file_outputs": muted, "binding": bound,
              "switch_readback": switch_results,
              "seen": False, "passed": True,
              "limits": "Static case only; action summary is bounded, source SHA protects original bytes; no temporal or art certification"}
    for marker, prior_camera in markers:
        marker.camera = prior_camera
    return result


def contact_sheet(output, profile, cases):
    cards = "".join('<figure><a href="' + html.escape(Path(c["path"]).name) + '"><img src="' + html.escape(Path(c["path"]).name) + '"></a><figcaption>' + html.escape(c["id"]) + f' / f{c["frame"]} / not reviewed</figcaption></figure>' for c in cases)
    (output / "contact.html").write_text('<!doctype html><meta charset="utf-8"><title>Static diagnostics</title><style>body{font:16px sans-serif;background:#202124;color:#eee}main{display:flex;flex-wrap:wrap}figure{width:480px;margin:12px}img{width:100%}</style><h1>' + html.escape(profile["id"]) + '</h1><p>Mapped static cases. Inspect originals; no art or motion approval inferred.</p><main>' + cards + '</main>', encoding="utf-8")


def verification_baseline(profile):
    selected = profile.get("verification")
    if not isinstance(selected, dict):
        raise ValueError("verify requires explicit verification report/hash and predeclared pixel thresholds")
    path = Path(selected["report"])
    if not path.is_absolute() or contract.digest(path) != selected["sha256"]:
        raise ValueError("Verification baseline report missing/hash mismatch")
    for key in ("max_abs", "mean_abs"):
        if type(selected.get(key)) not in (int, float) or not math.isfinite(selected[key]) or not 0 <= selected[key] <= 0.1:
            raise ValueError("Pixel limits must be finite predeclared values in [0,0.1]")
    baseline = contract.load(path)
    semantics = fingerprint({k: v for k, v in profile.items() if k != "verification"})
    if baseline.get("passed") is not True or baseline.get("source") != profile["source"] or baseline.get("profile_semantic_sha256") != semantics:
        raise ValueError("Baseline is not a passing run for this exact source and diagnostic contract")
    if baseline.get("worker_sha256") != contract.digest(__file__) or baseline.get("contract_sha256") != contract.digest(contract.__file__):
        raise ValueError("Worker/contract changed since baseline; regenerate a baseline before verification")
    if baseline.get("runtime_config_sha256") != contract.digest(ROOT / profile["runtime"]):
        raise ValueError("Runtime configuration changed since baseline")
    return baseline, selected


def compare_case(current, prior, limits):
    for key in ("id", "frame", "overrides", "camera", "mesh_signature", "bounded_action_summary_sha256", "effective_render", "color"):
        if current.get(key) != prior.get(key):
            raise ValueError("Independent rerender changed case contract: " + key)
    if contract.digest(prior["path"]) != prior["sha256"]:
        raise ValueError("Baseline image hash mismatch")
    images = [bpy.data.images.load(str(record["path"]), check_existing=False) for record in (current, prior)]
    try:
        if list(images[0].size) != list(images[1].size):
            raise ValueError("Verification image size mismatch")
        values = []
        for image in images:
            buffer = array("f", [0.0]) * len(image.pixels)
            image.pixels.foreach_get(buffer)
            values.append(buffer)
        maximum, total = 0.0, 0.0
        for a, b in zip(*values):
            difference = abs(a - b)
            maximum, total = max(maximum, difference), total + difference
        mean = total / len(values[0])
    finally:
        for image in images:
            bpy.data.images.remove(image)
    passed = maximum <= limits["max_abs"] and mean <= limits["mean_abs"]
    return {"passed": passed, "max_abs": maximum, "mean_abs": mean,
            "thresholds": {key: limits[key] for key in ("max_abs", "mean_abs")},
            "space": "Blender-decoded PNG float RGBA; not HDR light or perceptual/art similarity"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["inspect", "render", "verify"], required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    if not output.is_dir() or any(output.iterdir()):
        raise ValueError("Worker requires an empty directory created by launcher")
    report = {"passed": False, "mode": args.mode, "cases": [], "errors": []}
    try:
        profile = contract.load(args.profile)
        errors = contract.validate(profile, check_source=True)
        if errors:
            raise ValueError("; ".join(errors))
        runtime = contract.load(ROOT / profile["runtime"])
        report.update(profile_sha256=contract.digest(args.profile), worker_sha256=contract.digest(__file__),
                      contract_sha256=contract.digest(contract.__file__), runtime_config_sha256=contract.digest(ROOT / profile["runtime"]),
                      profile_semantic_sha256=fingerprint({k: v for k, v in profile.items() if k != "verification"}),
                      source=profile["source"], runtime=runtime, art_status="pending", user_art_approval=False)
        prepare_runtime(runtime, profile["scene"]["registration"])
        baseline, limits = verification_baseline(profile) if args.mode == "verify" else (None, None)
        scene, muted = open_source(profile)
        initial = inventory(profile, scene, muted)
        write(output / "inventory.json", initial)
        binding = contract.bind(profile, initial)
        report["binding"] = binding
        if args.mode == "inspect" and not binding["passed"]:
            raise ValueError("; ".join(binding["errors"]))
        if args.mode != "inspect":
            for case in profile["cases"]:
                result = render_case(profile, case, output)
                if baseline is not None:
                    prior = next((c for c in baseline["cases"] if c["id"] == result["id"]), None)
                    if prior is None:
                        raise ValueError("Verification baseline is missing case")
                    result["verification"] = compare_case(result, prior, limits)
                    if not result["verification"]["passed"]:
                        report["cases"].append(result)
                        raise ValueError("Independent pixel comparison exceeded predeclared limits")
                report["cases"].append(result)
                write(output / ("case-" + case["id"] + ".json"), result)
                print("STUDIO_CASE_COMPLETE", case["id"], flush=True)
            contact_sheet(output, profile, report["cases"])
        report["source_unchanged"] = contract.digest(profile["source"]["path"]).lower() == profile["source"]["sha256"].lower()
        if not report["source_unchanged"]:
            raise ValueError("Source changed during operation")
        report["passed"] = True
        report["limits"] = "Bounded tool execution; verify compares independently reopened source cases, not a newly saved production candidate; no video, simulation, source save or user approval"
    except Exception as exc:
        report["errors"].append(str(exc))
        report["traceback"] = traceback.format_exc()
    write(output / "report.json", report)
    print("STUDIO_WORKER_RESULT", json.dumps({"passed": report["passed"], "cases": len(report["cases"]), "errors": report["errors"]}, ensure_ascii=False), flush=True)
    if not report["passed"]:
        raise RuntimeError("Studio worker rejected operation; inspect report.json")


if __name__ == "__main__":
    main()
