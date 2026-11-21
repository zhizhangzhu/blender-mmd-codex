"""Finalize the pinned v3 character still and independently reopen it.

Use the isolated Goo runtime. Each mode is a separate Blender process. No
animation rendering, physics, action edits, preferences or catalog writes.
"""

import argparse
import hashlib
import json
import sys
from array import array
from contextlib import contextmanager
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import ACTORS
from refine_goo_character_lookdev import PREFIX, ROOT, SHA, SOURCE, hero_camera, render
from render_portrait_light_controls import mute_file_outputs
from snapshot_goo_scene import capture

TRIAL = ROOT / "trial-v3/Franken_Character_Lookdev_Still.blend"
TRIAL_SHA = "fad36e618f8207d98c687232671cf0126f96189322478887a0a3d4ecff173a3f"
FRAMES = (4140, 4218, 4290, 4370, 4438)
FACE_STRENGTH = {"aksiniya": 0.52, "ikhor": 0.78}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def plain(value):
    if value is None or isinstance(value, (str, bool, float, int)):
        return value
    if isinstance(value, bpy.types.ID):
        return {"id": value.name_full, "type": value.bl_rna.identifier}
    if isinstance(value, (set, frozenset)):
        return sorted(plain(item) for item in value)
    try:
        return [plain(item) for item in value]
    except TypeError:
        if hasattr(value, "bl_rna"):
            return {
                "rna": value.bl_rna.identifier,
                "name": getattr(value, "name", getattr(value, "identifier", "")),
                "handle": getattr(value, "handle", None),
            }
        return str(value)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def rna_fields(owner):
    """Writable scalar/pointer settings; avoid runtime state and RNA collections."""
    result = {}
    for prop in owner.bl_rna.properties:
        key = prop.identifier
        if key == "rna_type" or prop.is_readonly or prop.type == "COLLECTION":
            continue
        result[key] = plain(getattr(owner, key))
    return result


def animation(owner):
    ad = owner.animation_data
    if ad is None:
        return None
    return {
        "action": ad.action.name if ad.action else None,
        "slot": getattr(ad, "action_slot_handle", None),
        "blend": ad.action_blend_type,
        "influence": ad.action_influence,
        "nla": [
            {
                "name": track.name,
                "mute": track.mute,
                "strips": [
                    {
                        "settings": rna_fields(strip),
                        "slot": getattr(strip, "action_slot_handle", None),
                    }
                    for strip in track.strips
                ],
            }
            for track in ad.nla_tracks
        ],
        "drivers": [
            {
                "path": fc.data_path,
                "index": fc.array_index,
                "type": fc.driver.type,
                "expression": fc.driver.expression,
                "mute": fc.mute,
                "variables": [
                    {
                        "name": v.name,
                        "type": v.type,
                        "targets": [rna_fields(target) for target in v.targets],
                    }
                    for v in fc.driver.variables
                ],
            }
            for fc in ad.drivers
        ],
    }


def socket(socket):
    return {
        "value": plain(getattr(socket, "default_value", None)),
        "links": sorted(
            (l.from_node.name, l.from_socket.identifier) for l in socket.links
        ),
    }


def protected_materials():
    result = {}
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        nodes = {}
        for node in mat.node_tree.nodes:
            if node.name.startswith(PREFIX):
                continue
            protected = (
                node.name.startswith("mmd_")
                or "alpha" in node.name.lower()
                or "transparency" in node.name.lower()
                or node.type in {"TEX_IMAGE", "OUTPUT_MATERIAL", "OUTPUT_AOV"}
            )
            inputs = {
                s.identifier: socket(s)
                for s in node.inputs
                if protected or "alpha" in s.name.lower()
            }
            if inputs or protected:
                record = {"type": node.bl_idname, "inputs": inputs, "mute": node.mute}
                if (
                    node.type == "TEX_IMAGE"
                    and "geometry derived hair shadow" not in node.name
                ):
                    image = node.image
                    record["image"] = (
                        None
                        if image is None
                        else {
                            "name": image.name,
                            "path": Path(
                                bpy.path.abspath(image.filepath, library=image.library)
                            )
                            .resolve()
                            .as_posix()
                            .casefold(),
                            "colorspace": image.colorspace_settings.name,
                            "alpha_mode": image.alpha_mode,
                        }
                    )
                if node.type == "GROUP":
                    record["group"] = node.node_tree.name if node.node_tree else None
                nodes[node.name] = record
        result[mat.name] = {
            "nodes": nodes,
            "settings": {
                k: plain(getattr(mat, k))
                for k in (
                    "surface_render_method",
                    "use_backface_culling",
                    "use_transparent_shadow",
                )
                if hasattr(mat, k)
            },
        }
    return result


def buffer_hash(collection, prop, width, code="f"):
    values = array(code, [0]) * (len(collection) * width)
    collection.foreach_get(prop, values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def actor_meshes(scene):
    result = {}
    for actor, spec in ACTORS.items():
        obj = scene.objects[spec["mesh"]]
        mesh = obj.data
        weights = [
            (
                v.index,
                [
                    (g.group, g.weight)
                    for g in v.groups
                    if not obj.vertex_groups[g.group].name.startswith(PREFIX)
                ],
            )
            for v in mesh.vertices
        ]
        result[actor] = {
            "materials": [m.name if m else None for m in mesh.materials],
            "groups": [
                (g.index, g.name)
                for g in obj.vertex_groups
                if not g.name.startswith(PREFIX)
            ],
            "weights": digest(weights),
            "uv": {uv.name: buffer_hash(uv.data, "uv", 2) for uv in mesh.uv_layers},
            "loops": buffer_hash(mesh.loops, "vertex_index", 1, "i"),
            "polygons": [
                (p.loop_start, p.loop_total, p.material_index) for p in mesh.polygons
            ],
            "shapes": {}
            if mesh.shape_keys is None
            else {
                block.name: buffer_hash(block.data, "co", 3)
                for block in mesh.shape_keys.key_blocks
            },
        }
    return result


def rig_state(scene):
    objects = {}
    for obj in scene.objects:
        if obj.name.startswith(PREFIX):
            continue
        objects[obj.name] = {
            "parent": plain(obj.parent),
            "parent_type": obj.parent_type,
            "parent_bone": obj.parent_bone,
            "animation": animation(obj),
            "constraints": [rna_fields(c) for c in obj.constraints],
            "bones": {
                b.name: [rna_fields(c) for c in b.constraints] for b in obj.pose.bones
            }
            if obj.type == "ARMATURE"
            else None,
        }
    owners = {}
    for name in ("shape_keys", "cameras", "lights", "materials"):
        owners[name] = {
            o.name: animation(o)
            for o in getattr(bpy.data, name)
            if not o.name.startswith(PREFIX)
        }
    return {"objects": objects, "data_animation": owners}


def existing_invalid_drivers():
    result = []
    seen = set()
    for name in (
        "objects",
        "materials",
        "node_groups",
        "cameras",
        "lights",
        "scenes",
        "worlds",
        "shape_keys",
    ):
        for owner in getattr(bpy.data, name):
            for data in (owner, getattr(owner, "node_tree", None)):
                if data is None or data.as_pointer() in seen:
                    continue
                seen.add(data.as_pointer())
                ad = data.animation_data
                for fc in ad.drivers if ad else ():
                    if PREFIX not in fc.data_path and not fc.is_valid:
                        result.append(
                            (
                                data.bl_rna.identifier,
                                data.name,
                                fc.data_path,
                                fc.array_index,
                            )
                        )
    return sorted(result)


def evaluated(scene):
    result = {}
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for actor, spec in ACTORS.items():
            obj = scene.objects[spec["mesh"]]
            ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = ev.to_mesh()
            values = np.empty(len(mesh.vertices) * 3, np.float32)
            mesh.vertices.foreach_get("co", values)
            result[f"{actor}/{frame}"] = values
            ev.to_mesh_clear()
    scene.frame_set(4290)
    return result


def fingerprint(scene):
    state = capture()
    return {
        **{
            key: digest(state[key]) for key in ("actions", "geometry", "samples", "fps")
        },
        "mesh_uv_weights_shapes": digest(actor_meshes(scene)),
        "rig_slots_constraints": digest(rig_state(scene)),
        "material_alpha_textures": digest(protected_materials()),
        "color": digest(
            {
                "display": scene.display_settings.display_device,
                "view": rna_fields(scene.view_settings),
            }
        ),
    }


def camera_record(scene):
    return {
        "name": scene.camera.name,
        "dof": {
            k: plain(getattr(scene.camera.data.dof, k))
            for k in (
                "use_dof",
                "focus_distance",
                "focus_object",
                "focus_subtarget",
                "aperture_fstop",
                "aperture_blades",
                "aperture_rotation",
                "aperture_ratio",
            )
        },
        "markers": [
            [m.name, m.frame, m.camera.name if m.camera else None]
            for m in scene.timeline_markers
        ],
        "range": [scene.frame_start, scene.frame_end],
    }


def restore_camera(scene, record):
    scene.frame_set(4290)
    scene.camera = scene.objects[record["name"]]
    for key, value in record["dof"].items():
        if key == "focus_object":
            value = scene.objects.get(value["id"]) if value else None
        setattr(scene.camera.data.dof, key, value)


def safety(scene, expected_camera):
    errors = []
    if scene.frame_current != 4290 or (scene.frame_start, scene.frame_end) != (
        4290,
        4290,
    ):
        errors.append("saved range must be the single static frame 4290")
    if scene.camera.name != expected_camera["name"]:
        errors.append("authored camera changed")
    if camera_record(scene)["dof"] != expected_camera["dof"]:
        errors.append("source camera DOF settings not restored")
    if camera_record(scene)["markers"] != expected_camera["markers"]:
        errors.append("camera marker assignments changed")
    outputs = []
    trees = {g.as_pointer(): g for g in bpy.data.node_groups}
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            trees[other.compositing_node_group.as_pointer()] = (
                other.compositing_node_group
            )
    for tree in trees.values():
        outputs.extend(
            f"{tree.name}/{n.name}"
            for n in tree.nodes
            if n.type == "OUTPUT_FILE" and not n.mute
        )
    if outputs:
        errors.append({"unmuted_file_outputs": outputs})
    peek, normals, drivers, shadows = [], [], [], []
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        for node in mat.node_tree.nodes:
            if node.name == "Eye hair v1 | eye region bang peek":
                value = node.inputs[0]
                peek.append(
                    {
                        "material": mat.name,
                        "linked": value.is_linked,
                        "factor": value.default_value,
                    }
                )
                if value.is_linked or value.default_value != 0:
                    errors.append("additional eye transparency enabled: " + mat.name)
    for actor, spec in ACTORS.items():
        obj = scene.objects[spec["mesh"]]
        mods = [m for m in obj.modifiers if m.name == PREFIX + "local face normals"]
        if len(mods) != 1 or not mods[0].show_render or not mods[0].show_viewport:
            errors.append("missing or disabled local normals: " + actor)
        else:
            mod = mods[0]
            normals.append(
                {
                    "actor": actor,
                    "mix": mod.mix_factor,
                    "target_parent": mod.target.parent_bone,
                    "vertex_group": mod.vertex_group,
                    "after_solidify": obj.modifiers.find(mod.name)
                    > max(
                        i for i, m in enumerate(obj.modifiers) if m.type == "SOLIDIFY"
                    ),
                }
            )
            if (
                mod.target.parent != obj.find_armature()
                or mod.target.parent_bone != "頭"
            ):
                errors.append(
                    "normal target does not follow the correct head: " + actor
                )
        face = bpy.data.materials["颜" if actor == "aksiniya" else "颜.001"]
        tree = face.node_tree
        key_node = tree.nodes[PREFIX + "actual face key location"]
        lamp = scene.objects[f"Eye hair v1 | {actor} directional head key"]
        bpy.context.view_layer.update()
        for index, axis in enumerate("XYZ"):
            inp = key_node.inputs[index]
            path = inp.path_from_id("default_value")
            fc = tree.animation_data.drivers.find(path)
            valid = bool(fc and fc.is_valid and fc.driver.expression == "position")
            if valid:
                target = fc.driver.variables[0].targets[0]
                valid = (
                    target.id == lamp
                    and target.transform_type == "LOC_" + axis
                    and target.transform_space == "WORLD_SPACE"
                    and abs(inp.default_value - lamp.matrix_world.translation[index])
                    < 1e-5
                )
            drivers.append(
                {
                    "actor": actor,
                    "axis": axis,
                    "valid": valid,
                    "value": inp.default_value,
                    "expected_world": lamp.matrix_world.translation[index],
                }
            )
            if not valid:
                errors.append("actual-key driver invalid: " + actor + axis)
        shadow = tree.nodes["Eye hair v1 | geometry derived hair shadow"].image
        shadows.append(
            {
                "actor": actor,
                "image": shadow.name,
                "packed": bool(shadow.packed_file),
                "size": list(shadow.size),
                "source": shadow.source,
            }
        )
        if not shadow.packed_file or shadow.source != "FILE":
            errors.append("4290 hair shadow must be a packed still: " + actor)
    if not peek:
        errors.append("expected explicit disabled eye transparency controls missing")
    return {
        "errors": errors,
        "eye_transparency": peek,
        "normals": normals,
        "actual_key_drivers": drivers,
        "hair_shadow_stills": shadows,
    }


def image_difference(a, b):
    arrays = []
    for path in (a, b):
        img = bpy.data.images.load(str(path), check_existing=False)
        pixels = np.empty(len(img.pixels), np.float32)
        img.pixels.foreach_get(pixels)
        arrays.append(pixels.reshape((-1, 4))[:, :3])
        bpy.data.images.remove(img)
    assert arrays[0].shape == arrays[1].shape
    delta = np.abs(arrays[0] - arrays[1])
    return {
        "max_rgb": float(delta.max()),
        "mean_rgb": float(delta.mean()),
        "p99_rgb": float(np.quantile(delta, 0.99)),
        "p999_rgb": float(np.quantile(delta, 0.999)),
        "pixel_fraction_gt_0_001": float((delta.max(axis=1) > 0.001).mean()),
        "pixel_fraction_gt_0_003": float((delta.max(axis=1) > 0.003).mean()),
        "pixel_fraction_gt_0_01": float((delta.max(axis=1) > 0.01).mean()),
        "changed_pixel_fraction_gt_1e_5": float((delta.max(axis=1) > 1e-5).mean()),
        "space": "Blender decoded PNG RGB, not raw HDR output",
    }


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


@contextmanager
def glare_off(scene):
    """Bypass combined Image, zero effect-only Glare; muting forwards both."""
    trees = {g.as_pointer(): g for g in bpy.data.node_groups}
    if scene.compositing_node_group:
        tree = scene.compositing_node_group
        trees[tree.as_pointer()] = tree
    old_links, created, records = [], [], []
    try:
        for tree in trees.values():
            nodes = [n for n in tree.nodes if n.type == "GLARE" and not n.mute]
            if not nodes:
                continue
            black = tree.nodes.new("CompositorNodeRGB")
            black.outputs[0].default_value = (0, 0, 0, 0)
            created.append((tree, black))
            for node in nodes:
                image_input = node.inputs["Image"]
                assert len(image_input.links) == 1, node.name
                source = image_input.links[0].from_socket
                record = {"tree": tree.name, "node": node.name, "outputs": []}
                for name, replacement in (
                    ("Image", source),
                    ("Glare", black.outputs[0]),
                ):
                    output = node.outputs.get(name)
                    if output is None:
                        continue
                    for link in list(output.links):
                        old_links.append((tree, output, link.to_socket))
                        record["outputs"].append(
                            {
                                "socket": name,
                                "to": link.to_node.name,
                                "replacement": "input Image"
                                if name == "Image"
                                else "RGBA zero",
                            }
                        )
                        tree.links.new(replacement, link.to_socket)
                records.append(record)
        assert records, "No active Glare controls found"
        yield records
    finally:
        for tree, node in created:
            tree.nodes.remove(node)
        for tree, source, target in old_links:
            tree.links.new(source, target)


def open_project(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False, load_ui=False)
    scene = bpy.context.scene
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    return scene


def preflight(out):
    """Read-only validation before the first expensive 1080p render."""
    assert sha(SOURCE) == SHA and sha(TRIAL) == TRIAL_SHA
    scene = open_project(SOURCE)
    baseline = fingerprint(scene)
    original_invalid = existing_invalid_drivers()
    original_materials = protected_materials()
    original_rig = rig_state(scene)
    source_coords = evaluated(scene)
    scene = open_project(TRIAL)
    candidate = fingerprint(scene)
    candidate_invalid = existing_invalid_drivers()
    checks = {key: baseline[key] == candidate[key] for key in baseline}
    checks["existing_invalid_driver_set_equal"] = original_invalid == candidate_invalid
    current_coords = evaluated(scene)
    deltas = {
        key: float(np.abs(values - current_coords[key]).max())
        for key, values in source_coords.items()
    }
    checks["evaluated_positions"] = max(deltas.values()) < 1e-6
    report = {
        "source_sha256": SHA,
        "trial_sha256": TRIAL_SHA,
        "checks": checks,
        "baseline": baseline,
        "candidate": candidate,
        "position_delta": deltas,
        "original_invalid_drivers": original_invalid,
        "candidate_invalid_drivers": candidate_invalid,
        "passed": all(checks.values()),
    }
    if not checks["material_alpha_textures"]:
        report["original_material_protection"] = original_materials
        report["candidate_material_protection"] = protected_materials()
    if not checks["rig_slots_constraints"]:
        report["original_rig"] = original_rig
        report["candidate_rig"] = rig_state(scene)
    write(ROOT / (out.name + "-preflight.json"), report)
    assert report["passed"], checks
    print("LOOKDEV_FINAL_PREFLIGHT_PASSED", out, flush=True)


def prepare(out):
    assert sha(SOURCE) == SHA
    assert sha(TRIAL) == TRIAL_SHA
    out.mkdir(parents=True, exist_ok=False)
    scene = open_project(SOURCE)
    source_camera = camera_record(scene)
    baseline = fingerprint(scene)
    source_coords = evaluated(scene)
    mute_file_outputs()
    scene.render.use_motion_blur = False
    render(scene, out, "before-duet-4290", scene.camera, (1920, 1080), 64)
    scene = open_project(TRIAL)
    candidate = fingerprint(scene)
    checks = {key: baseline[key] == candidate[key] for key in baseline}
    assert all(checks.values()), checks
    current_coords = evaluated(scene)
    deltas = {
        key: float(np.abs(values - current_coords[key]).max())
        for key, values in source_coords.items()
    }
    assert max(deltas.values()) < 1e-6, deltas
    for actor, strength in FACE_STRENGTH.items():
        mat = bpy.data.materials["颜" if actor == "aksiniya" else "颜.001"]
        mat.node_tree.nodes[PREFIX + "warm form before retained final surface"].inputs[
            0
        ].default_value = strength
    mute_file_outputs()
    restore_camera(scene, source_camera)
    scene.render.use_motion_blur = False
    scene.frame_start = scene.frame_end = 4290
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 64
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "16"
    scene.render.filepath = str(out / "final-duet-4290.png")
    scene["lookdev_static_scope"] = (
        "4290 only; no new physics or animation quality certification"
    )
    scene["lookdev_source_sha256"] = SHA
    protected_final = fingerprint(scene)
    assert protected_final == baseline
    guard = safety(scene, source_camera)
    assert not guard["errors"], guard
    project = out / "Franken_Character_Lookdev_Still.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "source": str(SOURCE),
        "source_sha256": SHA,
        "trial": str(TRIAL),
        "trial_sha256": TRIAL_SHA,
        "project": str(project),
        "project_sha256": sha(project),
        "runtime": {
            "version": list(bpy.app.version),
            "build": bpy.app.build_hash.decode(),
            "binary": bpy.app.binary_path,
        },
        "frame": 4290,
        "new_video": False,
        "new_physics": False,
        "authored_camera": source_camera,
        "fingerprint": protected_final,
        "preservation_checks": checks,
        "evaluated_position_max_delta": deltas,
        "saved_safety": guard,
        "face_form_mix": FACE_STRENGTH,
        "normal_edit": "partial custom normals, no vertex displacement; single-frame ablation follows",
        "art_status": "awaiting director review and user evaluation; reference quality not achieved",
        "limits": [
            "Hair UV shadow maps are packed static 4290 maps",
            "Five sampled poses and Action/Slot/constraint integrity do not certify motion quality",
            "Three views change camera position only, not head pose or expression",
            "No new video, physics simulation, eye see-through, SDF for Ikhor or stage probe bake",
        ],
        "stills": [],
        "completed": False,
    }
    write(out / "finalization.json", report)
    render(scene, out, "final-duet-4290", scene.camera, (1920, 1080), 64)
    report["stills"].extend(["before-duet-4290.png", "final-duet-4290.png"])
    with glare_off(scene) as controls:
        render(scene, out, "final-duet-no-glow-4290", scene.camera, (1920, 1080), 64)
        report["no_glow_controls"] = controls
    report["stills"].append("final-duet-no-glow-4290.png")
    markers = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    for marker, _ in markers:
        marker.camera = None
    normal_effect = {}
    for actor, spec in ACTORS.items():
        for label, offset in (
            ("front", 0),
            ("camera-minus019m", -0.19),
            ("camera-plus019m", 0.19),
        ):
            cam = hero_camera(scene, actor, offset)
            name = f"final-{actor}-{label}-4290"
            render(scene, out, name, cam, (850, 900), 48)
            report["stills"].append(name + ".png")
        cam = hero_camera(scene, actor, 0)
        mod = scene.objects[spec["mesh"]].modifiers[PREFIX + "local face normals"]
        mod.show_render = mod.show_viewport = False
        bpy.context.view_layer.update()
        name = f"control-{actor}-normal-edit-off-4290"
        render(scene, out, name, cam, (850, 900), 48)
        mod.show_render = mod.show_viewport = True
        bpy.context.view_layer.update()
        normal_effect[actor] = image_difference(
            out / f"final-{actor}-front-4290.png", out / (name + ".png")
        )
        report["stills"].append(name + ".png")
    for marker, camera in markers:
        marker.camera = camera
    restore_camera(scene, source_camera)
    report["normal_edit_rendered_effect"] = normal_effect
    report["no_glow_difference"] = image_difference(
        out / "final-duet-4290.png", out / "final-duet-no-glow-4290.png"
    )
    assert sha(project) == report["project_sha256"]
    assert all(row["max_rgb"] > 1e-5 for row in normal_effect.values()), normal_effect
    report["stills_sha256"] = {name: sha(out / name) for name in report["stills"]}
    report["completed"] = True
    write(out / "finalization.json", report)
    print("LOOKDEV_FINAL_PREPARED", project, flush=True)


def repair_controls(out):
    """Correct the invalid mute-based ablation without editing saved beauty."""
    report_path = out / "finalization.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["completed"] and "no_glow_controls" not in report
    project = Path(report["project"])
    assert sha(project) == report["project_sha256"]
    name = "final-duet-glare-off-4290"
    assert not (out / (name + ".png")).exists()
    scene = open_project(project)
    assert fingerprint(scene) == report["fingerprint"]
    guard = safety(scene, report["authored_camera"])
    assert not guard["errors"], guard
    with glare_off(scene) as controls:
        render(scene, out, name, scene.camera, (1920, 1080), 64)
        report["no_glow_controls"] = controls
    rejected = "final-duet-no-glow-4290.png"
    report["rejected_controls"] = [
        {
            "file": rejected,
            "sha256": sha(out / rejected),
            "reason": "Muting Glare forwards Image into effect-only Glare branches and adds the source again; not a valid no-glow ablation",
            "replaced_by": name + ".png",
        }
    ]
    report["stills"].remove(rejected)
    report["stills"].append(name + ".png")
    report["stills_sha256"].pop(rejected)
    report["stills_sha256"][name + ".png"] = sha(out / (name + ".png"))
    report["no_glow_difference"] = image_difference(
        out / "final-duet-4290.png", out / (name + ".png")
    )
    report["no_glow_bypassed_nodes"] = [
        row["node"] for row in report["no_glow_controls"]
    ]
    report["control_correction_preserves_project"] = (
        sha(project) == report["project_sha256"]
    )
    assert report["control_correction_preserves_project"]
    write(report_path, report)
    print("LOOKDEV_FINAL_CONTROLS_REPAIRED", project, flush=True)


def reopen(out):
    report = json.loads((out / "finalization.json").read_text(encoding="utf-8"))
    assert report["completed"]
    project = Path(report["project"])
    assert sha(project) == report["project_sha256"]
    result_path = out / "reopen-verification.json"
    if result_path.exists():
        previous = json.loads(result_path.read_text(encoding="utf-8"))
        assert previous["passed"] is False
        assert previous["project_sha256"] == report["project_sha256"]
        for attempt in range(1, 100):
            archived = out / f"reopen-verification-failed-{attempt:02d}.json"
            if not archived.exists():
                result_path.rename(archived)
                break
        else:
            raise AssertionError("Too many previous failed reopen reports")
    scene = open_project(project)
    state = fingerprint(scene)
    checks = {key: value == report["fingerprint"][key] for key, value in state.items()}
    guard = safety(scene, report["authored_camera"])
    checks["saved_guards"] = not guard["errors"]
    checks["1080p_64_samples"] = (
        scene.render.resolution_x,
        scene.render.resolution_y,
        scene.render.resolution_percentage,
        scene.eevee.taa_render_samples,
    ) == (1920, 1080, 100, 64)
    checks["face_form_mix"] = all(
        abs(
            bpy.data.materials["颜" if actor == "aksiniya" else "颜.001"]
            .node_tree.nodes[PREFIX + "warm form before retained final surface"]
            .inputs[0]
            .default_value
            - strength
        )
        < 1e-6
        for actor, strength in FACE_STRENGTH.items()
    )
    result = {
        "project": str(project),
        "project_sha256": sha(project),
        "independent_process": True,
        "checks": checks,
        "saved_safety": guard,
        "passed": False,
        "new_video": False,
    }
    write(result_path, result)
    assert all(checks.values()), checks
    render(scene, out, "reopened-final-duet-4290", scene.camera, (1920, 1080), 64)
    diff = image_difference(
        out / "final-duet-4290.png", out / "reopened-final-duet-4290.png"
    )
    result["reopened_still_difference"] = diff
    # Report actual difference; a meaningful mismatch stops delivery for review.
    checks["reopened_pixels_match"] = (
        diff["mean_rgb"] < 1e-5 and diff["max_rgb"] < 0.003
    )
    checks["project_unchanged"] = sha(project) == report["project_sha256"]
    result["passed"] = all(checks.values())
    result["reopened_still_sha256"] = sha(out / "reopened-final-duet-4290.png")
    write(result_path, result)
    assert result["passed"], result
    print("LOOKDEV_FINAL_REOPEN_PASSED", project, flush=True)


def repeat_reopen(out):
    """Measure a second independent render, retaining the strict-test failure."""
    report = json.loads((out / "finalization.json").read_text(encoding="utf-8"))
    failed = json.loads((out / "reopen-verification.json").read_text(encoding="utf-8"))
    assert failed["passed"] is False
    assert failed["checks"]["reopened_pixels_match"] is False
    assert all(
        value
        for key, value in failed["checks"].items()
        if key != "reopened_pixels_match"
    )
    project = Path(report["project"])
    assert sha(project) == report["project_sha256"] == failed["project_sha256"]
    name = "reopened-repeat-final-duet-4290"
    result_path = out / "reopen-repeat-verification.json"
    assert not result_path.exists() and not (out / (name + ".png")).exists()
    scene = open_project(project)
    checks = {
        key: value == report["fingerprint"][key]
        for key, value in fingerprint(scene).items()
    }
    guard = safety(scene, report["authored_camera"])
    checks["saved_guards"] = not guard["errors"]
    checks["1080p_64_samples"] = (
        scene.render.resolution_x,
        scene.render.resolution_y,
        scene.render.resolution_percentage,
        scene.eevee.taa_render_samples,
    ) == (1920, 1080, 100, 64)
    assert all(checks.values()), checks
    render(scene, out, name, scene.camera, (1920, 1080), 64)
    first = out / "reopened-final-duet-4290.png"
    final = out / "final-duet-4290.png"
    second = out / (name + ".png")
    result = {
        "project": str(project),
        "project_sha256": sha(project),
        "independent_process": True,
        "checks": checks,
        "saved_safety": guard,
        "lens_4290_mm": scene.camera.data.lens,
        "final_vs_first_reopen": image_difference(final, first),
        "final_vs_second_reopen": image_difference(final, second),
        "first_vs_second_reopen": image_difference(first, second),
        "second_reopened_still_sha256": sha(second),
        "pixel_acceptance": "pending director assessment of repeated render variance; strict failure retained",
        "new_video": False,
    }
    assert result["project_sha256"] == report["project_sha256"]
    write(result_path, result)
    print("LOOKDEV_FINAL_REPEAT_MEASURED", project, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("preflight", "prepare", "repair-controls", "reopen", "repeat-reopen"),
        required=True,
    )
    parser.add_argument("--iteration", default="final-v1")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    assert Path(args.iteration).name == args.iteration and args.iteration.startswith(
        "final-v"
    )
    register_addons()
    out = ROOT / args.iteration
    {
        "preflight": preflight,
        "prepare": prepare,
        "repair-controls": repair_controls,
        "reopen": reopen,
        "repeat-reopen": repeat_reopen,
    }[args.mode](out)


if __name__ == "__main__":
    main()
