"""Opaque hair, toon value ramps and geometry-derived face hair-shadow study."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fix_goo_eye_ray_and_shadow import vector
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, ROOT, color, math, node
from render_portrait_light_controls import mute_file_outputs

SIZE = 512


def save_mask(path, values):
    image = bpy.data.images.new(
        path.stem, width=SIZE, height=SIZE, alpha=True, float_buffer=False, is_data=True
    )
    rgba = np.ones((SIZE, SIZE, 4), np.float32)
    rgba[:, :, :3] = values[:, :, None]
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    return image


def raster(triangles, uvs, vertex_values, background):
    result = np.full((SIZE, SIZE), background, np.float32)
    for ids, uv in zip(triangles, uvs):
        p = np.asarray(uv) * (SIZE - 1)
        low = np.maximum(np.floor(p.min(0)).astype(int), 0)
        high = np.minimum(np.ceil(p.max(0)).astype(int), SIZE - 1)
        if np.any(high < low):
            continue
        xx, yy = np.meshgrid(
            np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1)
        )
        den = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (
            p[0, 1] - p[2, 1]
        )
        if abs(den) < 1e-8:
            continue
        a = (
            (p[1, 1] - p[2, 1]) * (xx - p[2, 0]) + (p[2, 0] - p[1, 0]) * (yy - p[2, 1])
        ) / den
        b = (
            (p[2, 1] - p[0, 1]) * (xx - p[2, 0]) + (p[0, 0] - p[2, 0]) * (yy - p[2, 1])
        ) / den
        c = 1 - a - b
        inside = (a >= -1e-5) & (b >= -1e-5) & (c >= -1e-5)
        values = (
            a * vertex_values[ids[0]]
            + b * vertex_values[ids[1]]
            + c * vertex_values[ids[2]]
        )
        region = result[low[1] : high[1] + 1, low[0] : high[0] + 1]
        region[inside] = values[inside]
    return result


def face_masks(scene, obj, actor, directory):
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    face = "颜" if actor == "aksiniya" else "颜.001"
    mi = obj.data.materials.find(face)
    triangles = [
        list(t.vertices) for t in mesh.loop_triangles if t.material_index == mi
    ]
    uvs = [
        [tuple(mesh.uv_layers.active.data[i].uv) for i in t.loops]
        for t in mesh.loop_triangles
        if t.material_index == mi
    ]
    used = sorted({i for tri in triangles for i in tri})
    casters = []
    for poly in mesh.polygons:
        mat = obj.data.materials[poly.material_index]
        if (
            mat.get("look_category") == "hair"
            or mat.get("ikhor_material_role") == "hair"
        ) and not mat.name.endswith("+"):
            casters.append(list(poly.vertices))
    coords = [obj.matrix_world @ v.co for v in mesh.vertices]
    tree = BVHTree.FromPolygons(coords, casters, all_triangles=False, epsilon=0.00001)
    lamp = scene.objects[PREFIX + actor + " directional head key"]
    points = [
        lamp.matrix_world.translation + lamp.matrix_world.to_3x3() @ Vector((x, 0, 0))
        for x in (-0.10, 0, 0.10)
    ]
    shade = np.ones(len(mesh.vertices), np.float32)
    for index in used:
        p = coords[index]
        total = 0
        for source in points:
            direction = source - p
            distance = direction.length
            direction.normalize()
            hit, _, _, hit_distance = tree.ray_cast(
                p + direction * 0.00025, direction, max(0, distance - 0.00025)
            )
            total += 0 if hit is not None and hit_distance < 0.055 else 1
        shade[index] = total / len(points)
    base = obj.data.vertices
    eye_ids = {
        i
        for p in obj.data.polygons
        if obj.data.materials[p.material_index].name in ("目", "目.002", "目2")
        for i in p.vertices
    }
    eyez = float(np.mean([base[i].co.z for i in eye_ids]))
    candidates = [
        i
        for i in used
        if i < len(base)
        and abs(base[i].co.x) < 0.012
        and eyez - 0.05 < base[i].co.z < eyez - 0.012
    ]
    tip = min(candidates, key=lambda i: base[i].co.y)
    center = base[tip].co.copy()
    center.x += 0.0015
    local = np.zeros((len(mesh.vertices), 3), np.float32)
    for i in used:
        local[i] = base[i].co
    xyz = np.stack(
        [raster(triangles, uvs, local[:, axis], 1000) for axis in range(3)], axis=2
    )
    q = xyz - np.asarray(center)
    radius = 0.0035 + 0.002 * np.clip(-q[:, :, 2] / 0.007, 0, 1)
    r2 = (q[:, :, 0] / radius) ** 2 + (q[:, :, 2] / 0.007) ** 2
    nose_pixels = np.sqrt(np.clip(1 - r2, 0, 1)) * (np.abs(q[:, :, 1]) < 0.018)
    mask_pixels = raster(triangles, uvs, shade, 1)
    height = np.clip((xyz[:, :, 2] - (eyez - 0.022)) / 0.028, 0, 1)
    height = height * height * (3 - 2 * height)
    mask_pixels = 1 - (1 - mask_pixels) * height * 0.88
    shadow_image = save_mask(directory / (actor + "_hair_shadow.png"), mask_pixels)
    nose_image = save_mask(directory / (actor + "_nose_form.png"), nose_pixels)
    evaluated.to_mesh_clear()
    return (
        shadow_image,
        nose_image,
        {
            "face_vertices": len(used),
            "partly_shadowed_vertices": int(np.count_nonzero(shade[used] < 0.99)),
            "nose_tip_local": list(center),
            "ray_samples_per_vertex": 3,
            "raster_size": SIZE,
        },
    )


def main():
    old = ROOT / "production-v5/Franken_Duet_Goo_Eye_Hair_Stage.blend"
    production = ROOT / "production-v9"
    production.mkdir(parents=True, exist_ok=True)
    assert not (production / "Franken_Duet_Goo_Eye_Hair_Stage.blend").exists()
    masks = production / "shadow-study"
    masks.mkdir(exist_ok=True)
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(old), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    report = {
        "eye_peek_deferred_by_user": True,
        "hair": [],
        "face": [],
        "shadow_scope": "Static frame4290 study; not yet an animated shadow cache",
    }
    for mat in bpy.data.materials:
        tree = mat.node_tree
        if not tree or not tree.nodes.get(PREFIX + "eye region bang peek"):
            continue
        output = next(
            n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
        )
        tree.links.new(
            tree.nodes[PREFIX + "eye region bang peek"].inputs[1].links[0].from_socket,
            output.inputs["Surface"],
        )
        mat.surface_render_method = "DITHERED"
        actor = mat["performer_id"]
        geo = node(tree, "ShaderNodeNewGeometry", "toon opaque hair geometry")
        lamp = scene.objects[PREFIX + actor + " directional head key"]
        from revise_goo_projected_eye_shadow import world_center

        direction = vector(
            tree,
            "NORMALIZE",
            vector(
                tree,
                "SUBTRACT",
                world_center(tree, lamp, "toon hair light position"),
                geo.outputs["Position"],
                "surface to toon key",
            ),
            None,
            "normalized toon head key",
        )
        nol = vector(
            tree, "DOT_PRODUCT", geo.outputs["Normal"], direction, "toon hair NoL"
        )
        half = math(
            tree,
            "MULTIPLY",
            math(tree, "ADD", nol, 1, "half lambert offset"),
            0.5,
            "half lambert range",
        )
        ramp = node(tree, "ShaderNodeValToRGB", "authored cool warm hair ramp")
        ramp.color_ramp.interpolation = "EASE"
        dark = (0.55, 0.61, 0.78, 1) if actor == "aksiniya" else (0.65, 0.49, 0.32, 1)
        ramp.color_ramp.elements[0].position = 0.50
        ramp.color_ramp.elements[0].color = dark
        ramp.color_ramp.elements[1].position = 0.74
        ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
        tree.links.new(half, ramp.inputs[0])
        target = (
            tree.nodes.get("Character layers | one directional hair highlight")
            if actor == "aksiniya"
            else tree.nodes.get("Ikhor character | one hair highlight application")
        )
        if target:
            socket = target.inputs[1] if target.type == "MIX_RGB" else target.inputs[0]
            original = socket.links[0].from_socket
            tree.links.new(
                color(
                    tree,
                    "MULTIPLY",
                    original,
                    ramp.outputs[0],
                    1,
                    "opaque hair ramp before highlight",
                ),
                socket,
            )
        report["hair"].append(
            {
                "material": mat.name,
                "dark_multiplier": dark,
                "ramp_interval": [0.50, 0.74],
            }
        )
    for actor, objname, face in (
        ("aksiniya", "阿克西妮娅2_mesh", "颜"),
        ("ikhor", "Ikhor | mesh | Ikhor_mesh", "颜.001"),
    ):
        shadow, nose, stats = face_masks(scene, scene.objects[objname], actor, masks)
        mat = bpy.data.materials[face]
        tree = mat.node_tree
        uv = node(tree, "ShaderNodeUVMap", "actual face shadow UV")
        uv.uv_map = scene.objects[objname].data.uv_layers.active.name
        sh = node(tree, "ShaderNodeTexImage", "geometry derived hair shadow")
        sh.image = shadow
        no = node(tree, "ShaderNodeTexImage", "authored nose form mask")
        no.image = nose
        tree.links.new(uv.outputs[0], sh.inputs["Vector"])
        tree.links.new(uv.outputs[0], no.inputs["Vector"])
        surface = (
            tree.nodes.get("Look v3 | NPR surface")
            or tree.nodes["Ikhor character | controlled NPR surface"]
        )
        base = surface.inputs["Color"].links[0].from_socket
        coverage = math(
            tree, "SUBTRACT", 1, sh.outputs["Color"], "hair shadow coverage"
        )
        shaded = color(
            tree,
            "MULTIPLY",
            base,
            (0.93, 0.72, 0.59, 1),
            coverage,
            "warm geometric bang shadow",
        )
        shaded = color(
            tree,
            "MULTIPLY",
            shaded,
            (1, 0.70, 0.52, 1),
            math(tree, "MULTIPLY", no.outputs["Color"], 0.60, "nose shade amount"),
            "warm nose authored form",
        )
        tree.links.new(shaded, surface.inputs["Color"])
        report["face"].append({"actor": actor, **stats})
    project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    prep = json.loads((old.parent / "preparation.json").read_text(encoding="utf-8"))
    prep.update(
        source=str(old),
        source_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
        project=str(project),
        project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
        toon_study=report,
    )
    (production / "preparation.json").write_text(
        json.dumps(prep, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("TOON_FACE_HAIR_STUDY", json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
