"""Fixed-v6, reversible character look development. Static 4290 only; no video."""

import argparse
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_goo_face_hair_shadows import uv_template
from goo_runtime import register_addons
from mathutils.bvhtree import BVHTree
from prepare_goo_eye_hair_stage import ACTORS
from prepare_goo_toon_face_hair_study import SIZE, save_mask
from render_portrait_light_controls import mute_file_outputs
from snapshot_goo_scene import capture

SOURCE = Path(
    "D:/codex/output/MMD-MME-Reference-Light-v1/production-v6/Franken_MME_Balanced_Light_Still.blend"
)
SHA = "65766b3befc9031f5c27efb25f91b1516cd2a0cd195b4ea98125bab93c07bf7a"
ROOT = Path("D:/codex/output/Goo-Character-Lookdev-2026-11-18")
PREFIX = "Lookdev 18 | "


def new(tree, kind, label):
    n = tree.nodes.new(kind)
    n.name = n.label = PREFIX + label
    return n


def put(tree, value, socket):
    if hasattr(value, "is_output"):
        tree.links.new(value, socket)
    else:
        socket.default_value = value


def scalar(tree, op, a, b, label):
    n = new(tree, "ShaderNodeMath", label)
    n.operation = op
    put(tree, a, n.inputs[0])
    put(tree, b, n.inputs[1])
    return n.outputs[0]


def vmath(tree, op, a, b, label):
    n = new(tree, "ShaderNodeVectorMath", label)
    n.operation = op
    put(tree, a, n.inputs[0])
    put(tree, b, n.inputs[1])
    return n.outputs["Value" if op == "DOT_PRODUCT" else "Vector"]


def mix(tree, a, b, fac, label, operation="MIX"):
    n = new(tree, "ShaderNodeMixRGB", label)
    n.blend_type = operation
    for v, s in zip((fac, a, b), n.inputs):
        put(tree, v, s)
    return n.outputs[0]


def ramp(tree, value, lo, hi, dark, light, label):
    n = new(tree, "ShaderNodeValToRGB", label)
    n.color_ramp.interpolation = "EASE"
    n.color_ramp.elements[0].position = lo
    n.color_ramp.elements[0].color = dark
    n.color_ramp.elements[1].position = hi
    n.color_ramp.elements[1].color = light
    tree.links.new(value, n.inputs[0])
    return n.outputs[0]


def normal_edit(scene, actor):
    obj = scene.objects[ACTORS[actor]["mesh"]]
    arm = obj.find_armature()
    face = "颜" if actor == "aksiniya" else "颜.001"
    ids = {
        v
        for p in obj.data.polygons
        if obj.data.materials[p.material_index].name == face
        for v in p.vertices
    }
    zmin = min(obj.data.vertices[i].co.z for i in ids)
    group = obj.vertex_groups.new(name=PREFIX + "face side normal permission")
    for i in ids:
        c = obj.data.vertices[i].co
        side = min(1, max(0, (abs(c.x) - 0.018) / 0.035))
        chin = min(1, max(0, (c.z - zmin) / 0.035))
        group.add([i], side * chin, "REPLACE")
    left = scene.objects[f"Eye hair v1 | {actor} eye L"]
    right = scene.objects[f"Eye hair v1 | {actor} eye R"]
    rot = left.matrix_world.to_3x3()
    center = (left.matrix_world.translation + right.matrix_world.translation) * 0.5
    front = (rot @ Vector((0, -1, 0))).normalized()
    up = (rot @ Vector((0, 0, 1))).normalized()
    target = bpy.data.objects.new(PREFIX + actor + " face radial target", None)
    scene.collection.objects.link(target)
    target.parent = arm
    target.parent_type = "BONE"
    target.parent_bone = "頭"
    target.empty_display_size = 0.015
    target.hide_render = True
    bpy.context.view_layer.update()
    target.matrix_world.translation = center - front * 0.095 - up * 0.025
    modifier = obj.modifiers.new(PREFIX + "local face normals", "NORMAL_EDIT")
    modifier.mode = "RADIAL"
    modifier.target = target
    modifier.vertex_group = group.name
    modifier.mix_factor = 0.23
    modifier.mix_limit = math.radians(32)
    modifier.no_polynors_fix = True
    return {
        "actor": actor,
        "mesh": obj.name,
        "target": target.name,
        "parent_bone": target.parent_bone,
        "affected_vertices": len(ids),
        "mix_factor": modifier.mix_factor,
        "max_angle_degrees": 32,
        "order": [m.type for m in obj.modifiers],
        "excluded": "nose center, mouth center, other materials",
    }


def reposition_keys(scene):
    records = []
    for actor in ACTORS:
        left = scene.objects[f"Eye hair v1 | {actor} eye L"]
        right_eye = scene.objects[f"Eye hair v1 | {actor} eye R"]
        rot = left.matrix_world.to_3x3()
        center = (
            left.matrix_world.translation + right_eye.matrix_world.translation
        ) * 0.5
        forward = (rot @ Vector((0, -1, 0))).normalized()
        right = (rot @ Vector((1, 0, 0))).normalized()
        up = (rot @ Vector((0, 0, 1))).normalized()
        for name in (
            f"Reference duet | {actor} | key",
            f"Eye hair v1 | {actor} directional head key",
        ):
            lamp = scene.objects[name]
            old = list(lamp.location)
            lamp.location = center - right * 0.95 + forward * 0.80 + up * 1.05
            lamp.rotation_euler = (
                (center - lamp.location).to_track_quat("-Z", "Y").to_euler()
            )
            records.append(
                {
                    "name": name,
                    "old_position": old,
                    "new_position": list(lamp.location),
                    "energy_unchanged": lamp.data.energy,
                }
            )
    import goo_engine_light_groups

    goo_engine_light_groups.sync_light_groups()
    bpy.context.view_layer.update()
    return records


def bake_bangs(scene, out):
    records = []
    for actor, spec in ACTORS.items():
        obj = scene.objects[spec["mesh"]]
        template = uv_template(obj, actor)
        ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = ev.to_mesh()
        world = [obj.matrix_world @ v.co for v in mesh.vertices]
        tree = BVHTree.FromPolygons(
            world, template["casters"], all_triangles=False, epsilon=0.000005
        )
        ids, weights = template["indices"], template["weights"]
        valid = weights.sum(axis=2) > 0.5
        xyz = (
            np.asarray([p[:] for p in world], np.float32)[ids] * weights[:, :, :, None]
        ).sum(axis=2)
        lamp = scene.objects[f"Eye hair v1 | {actor} directional head key"]
        points = [
            lamp.matrix_world.translation
            + lamp.matrix_world.to_3x3() @ Vector((x, 0, 0))
            for x in (-0.018, 0, 0.018)
        ]
        coverage = np.zeros((SIZE, SIZE), np.float32)
        for y, x in np.argwhere(valid):
            p = Vector(xyz[y, x])
            hits = 0
            for source in points:
                ray = (source - p).normalized()
                hit, _, _, distance = tree.ray_cast(p + ray * 0.0002, ray, 0.08)
                hits += int(hit is not None and distance > 0.0002)
            coverage[y, x] = hits / 3
        coverage *= template["height"]
        image = save_mask(out / f"{actor}-hair-shadow-4290.png", 1 - coverage)
        image.pack()
        material = bpy.data.materials[template["face"]]
        material.node_tree.nodes[
            "Eye hair v1 | geometry derived hair shadow"
        ].image = image
        ev.to_mesh_clear()
        records.append(
            {
                "actor": actor,
                "valid_face_texels": int(valid.sum()),
                "shadow_texels": int((coverage > 0.1).sum()),
                "light": lamp.name,
                "area_sample_span_m": 0.036,
                "max_shadow_distance_m": 0.08,
                "frame": 4290,
            }
        )
    return records


def adjust_materials(scene, revision):
    changes = []
    for m in bpy.data.materials:
        actor = m.get("performer_id")
        if actor not in ACTORS or not m.node_tree or m.name.startswith("mmd_edge"):
            continue
        t = m.node_tree
        role = (
            m.get("look_category")
            if actor == "aksiniya"
            else m.get("ikhor_material_role")
        )
        record = {"material": m.name, "actor": actor, "role": role, "edits": []}
        is_face = m.name in ("颜", "颜.001")
        if is_face:
            geo = new(t, "ShaderNodeNewGeometry", "deformed face geometry")
            light = new(t, "ShaderNodeCombineXYZ", "actual face key location")
            lamp = scene.objects[f"Eye hair v1 | {actor} directional head key"]
            for axis, socket in zip("XYZ", light.inputs):
                curve = socket.driver_add("default_value")
                variable = curve.driver.variables.new()
                variable.name = "position"
                variable.type = "TRANSFORMS"
                variable.targets[0].id = lamp
                variable.targets[0].transform_type = "LOC_" + axis
                variable.targets[0].transform_space = "WORLD_SPACE"
                curve.driver.expression = "position"
            delta = vmath(
                t,
                "SUBTRACT",
                light.outputs[0],
                geo.outputs["Position"],
                "surface to actual key",
            )
            direction = vmath(
                t, "NORMALIZE", delta, (0, 0, 0), "unit actual key direction"
            )
            nol = vmath(
                t,
                "DOT_PRODUCT",
                geo.outputs["Normal"],
                direction,
                "face mesh normal dot key",
            )
            palette = ramp(
                t,
                nol,
                0.30 if revision >= 3 else 0.16,
                0.55 if revision >= 3 else 0.44,
                (0.80, 0.57, 0.61, 1),
                (1, 0.995, 0.99, 1),
                "selective warm face form",
            )
            surface = t.nodes.get("Look v3 | NPR surface") or t.nodes.get(
                "Ikhor character | controlled NPR surface"
            )
            original = surface.inputs["Color"].links[0].from_socket
            shade = mix(
                t,
                original,
                palette,
                0.78,
                "warm form before retained final surface",
                "MULTIPLY",
            )
            switch = new(t, "ShaderNodeValue", "face form enable")
            switch.outputs[0].default_value = 1
            final = mix(
                t, original, shade, switch.outputs[0], "face form reversible output"
            )
            t.links.new(final, surface.inputs["Color"])
            luminous = t.nodes.get("Eye hair v1 | controlled luminous skin")
            if luminous:
                luminous.inputs[2].default_value = (1.09, 1.09, 1.09, 1)
            warm = t.nodes.get("Eye hair v1 | warm geometric bang shadow")
            if warm:
                warm.inputs[2].default_value = (
                    (0.91, 0.54, 0.50, 1) if actor == "ikhor" else (0.94, 0.61, 0.59, 1)
                )
            record["edits"].append(
                "head-targeted partial normals; actual-key warm face form; preserve existing SDF/UV hair shadow"
            )
        if role == "hair":
            compact = t.nodes.get("Eye hair v1 | compact opaque hair ramp")
            if compact:
                compact.color_ramp.elements[0].color = (
                    (0.63, 0.54, 0.44, 1) if actor == "ikhor" else (0.57, 0.62, 0.79, 1)
                )
                compact.color_ramp.elements[0].position = (
                    0.55 if revision >= 3 else 0.40
                )
                compact.color_ramp.elements[1].position = (
                    0.93 if revision >= 3 else 0.78
                )
                if revision >= 3:
                    compact.color_ramp.elements[1].color = (0.91, 0.91, 0.93, 1)
            width = t.nodes.get("Goo window wrap | wider existing golden hair band")
            if width:
                width.inputs[1].default_value = 1.20
            gain = t.nodes.get("Goo rim glow | retained hair highlight gain")
            if gain:
                gain.inputs[1].default_value = 2.2
            for n in t.nodes:
                if n.name == "Character layers | hair highlight strength":
                    n.outputs[0].default_value *= 0.80
            record["edits"].append(
                "separate hair masses; narrower concentrated authored highlight"
            )
        if role == "cloth":
            pal = t.nodes.get("Portrait relight | keyfill | single portrait palette")
            if pal:
                pal.color_ramp.elements[0].color = (
                    (0.57, 0.60, 0.78, 1) if actor == "ikhor" else (0.53, 0.59, 0.78, 1)
                )
            white = t.nodes.get("Eye hair v1 | MME study blue white textile ramp")
            if white:
                white.color_ramp.elements[0].color = (0.58, 0.69, 0.89, 1)
                white.color_ramp.elements[1].color = (1.08, 1.10, 1.16, 1)
            record["edits"].append(
                "colored cloth shadows and restrained neutral-white highlight"
            )
        # Keep the strong primary contour; reduce only its weaker opposite-side copy.
        if role in ("hair", "cloth", "fur", "trim"):
            secondary = t.nodes.get("Portrait relight | rimink | right HDR gain only")
            if secondary:
                secondary.inputs[1].default_value *= 0.64
                record["edits"].append(
                    "secondary-side rim gain x0.64; primary unchanged"
                )
        if role == "trim" or actor == "ikhor" and role == "cloth":
            rough = []
            for n in t.nodes:
                if (
                    n.type in ("BSDF_GLOSSY", "BSDF_PRINCIPLED")
                    and "Roughness" in n.inputs
                    and not n.inputs["Roughness"].is_linked
                    and n.outputs
                    and any(s.is_linked for s in n.outputs)
                    and any(x in n.name.lower() for x in ("metal", "gold", "physical"))
                ):
                    rough.append((n.name, n.inputs["Roughness"].default_value))
                    n.inputs["Roughness"].default_value = 0.23
            if rough:
                record["edits"].append(
                    {"masked_metal_roughness": 0.23, "previous": rough}
                )
        if record["edits"]:
            changes.append(record)
    return changes


def geometry_positions():
    result = {}
    deps = bpy.context.evaluated_depsgraph_get()
    for spec in ACTORS.values():
        obj = bpy.context.scene.objects[spec["mesh"]]
        ev = obj.evaluated_get(deps)
        mesh = ev.to_mesh()
        result[obj.name] = np.array([v.co[:] for v in mesh.vertices], dtype=np.float32)
        ev.to_mesh_clear()
    return result


def render(scene, out, label, camera=None, size=(1280, 720), samples=32):
    if camera:
        scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = samples
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "16"
    scene.render.filepath = str(out / f"{label}.png")
    bpy.ops.render.render(write_still=True)
    print("LOOKDEV_STILL", label, flush=True)


def hero_camera(scene, actor, side=0):
    left = scene.objects[f"Eye hair v1 | {actor} eye L"]
    right = scene.objects[f"Eye hair v1 | {actor} eye R"]
    rot = left.matrix_world.to_3x3()
    center = (left.matrix_world.translation + right.matrix_world.translation) * 0.5
    front = (rot @ Vector((0, -1, 0))).normalized()
    up = (rot @ Vector((0, 0, 1))).normalized()
    right_axis = (rot @ Vector((1, 0, 0))).normalized()
    name = PREFIX + actor + " diagnostic camera"
    cam = scene.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        scene.collection.objects.link(cam)
    target = center - up * 0.047
    cam.location = target + front * 0.78 + right_axis * side + up * 0.018
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 62
    cam.data.dof.use_dof = False
    return cam


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", type=int, default=1)
    parser.add_argument("--reuse-baseline", type=Path)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA
    out = ROOT / f"trial-v{args.revision}"
    out.mkdir(parents=True, exist_ok=False)
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
    scene = bpy.context.scene
    muted = mute_file_outputs()
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    baseline = capture()
    coords = geometry_positions()
    camera = scene.camera
    markers = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    # Same original authored camera/settings for both sides of the comparison.
    scene.render.use_motion_blur = False
    camera.data.dof.use_dof = False
    if args.reuse_baseline:
        for label in ("duet", "aksiniya", "ikhor"):
            shutil.copy2(
                args.reuse_baseline / f"before-{label}-4290.png",
                out / f"before-{label}-4290.png",
            )
    else:
        render(scene, out, "before-duet-4290", camera)
    for m, _ in markers:
        m.camera = None
    if not args.reuse_baseline:
        for actor in ACTORS:
            render(
                scene,
                out,
                f"before-{actor}-4290",
                hero_camera(scene, actor),
                (850, 900),
            )
    scene.camera = camera
    for m, c in markers:
        m.camera = c
    lights = reposition_keys(scene) if args.revision >= 3 else []
    normals = [normal_edit(scene, actor) for actor in ACTORS]
    shadows = bake_bangs(scene, out) if args.revision >= 3 else []
    changes = adjust_materials(scene, args.revision)
    comp = scene.compositing_node_group
    post = []
    for name, strength in (
        ("Goo window wrap | tight white edge bloom", 1.15),
        ("Goo window wrap | soft outer edge diffusion", 0.24),
        ("Eye hair v1 | MME study selective bright diffusion", 0.055),
    ):
        n = comp.nodes.get(name)
        if n and "Strength" in n.inputs:
            post.append(
                {
                    "name": name,
                    "old": n.inputs["Strength"].default_value,
                    "new": strength,
                }
            )
            n.inputs["Strength"].default_value = strength
    bpy.context.view_layer.update()
    geometry_error = {
        k: float(np.abs(v - geometry_positions()[k]).max()) for k, v in coords.items()
    }
    assert max(geometry_error.values()) < 1e-6, geometry_error
    after = capture()
    assert baseline["actions"] == after["actions"]
    assert baseline["geometry"] == after["geometry"]
    assert baseline["samples"] == after["samples"]
    scene.camera = camera
    scene.frame_set(4290)
    scene.render.resolution_x, scene.render.resolution_y = (1920, 1080)
    scene.eevee.taa_render_samples = 64
    project = out / "Franken_Character_Lookdev_Still.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "source": str(SOURCE),
        "source_sha256": SHA,
        "project": str(project),
        "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
        "frame": 4290,
        "normals": normals,
        "materials": changes,
        "lights": lights,
        "rebaked_hair_shadows": shadows,
        "post": post,
        "muted_outputs": muted,
        "preservation": {
            "all_actions_equal": True,
            "base_mesh_equal": True,
            "five_sample_bone_camera_shape_states_equal": True,
            "evaluated_geometry_max_difference": geometry_error,
        },
        "limits": [
            "4290 face hair shadow cache only",
            "no motion timing or simulation certification",
            "eye see-through deferred",
            "art pending",
        ],
    }
    (out / "implementation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    render(scene, out, "after-duet-4290", camera)
    for m, _ in markers:
        m.camera = None
    for actor in ACTORS:
        render(scene, out, f"after-{actor}-4290", hero_camera(scene, actor), (850, 900))
    print("LOOKDEV_TRIAL_COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
