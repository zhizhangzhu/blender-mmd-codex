"""Bake the two actors' actual animated bang occlusion to portable face-UV sequences."""

import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import ACTORS, PREFIX, ROOT
from prepare_goo_toon_face_hair_study import SIZE, save_mask
from render_portrait_light_controls import mute_file_outputs


def uv_template(obj, actor):
    mesh = obj.data
    mesh.calc_loop_triangles()
    face = "颜" if actor == "aksiniya" else "颜.001"
    mi = mesh.materials.find(face)
    triangles = [t for t in mesh.loop_triangles if t.material_index == mi]
    indices = np.zeros((SIZE, SIZE, 3), np.int32)
    weights = np.zeros((SIZE, SIZE, 3), np.float32)
    for tri in triangles:
        p = np.asarray([mesh.uv_layers.active.data[i].uv[:] for i in tri.loops]) * (
            SIZE - 1
        )
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
        region = indices[low[1] : high[1] + 1, low[0] : high[0] + 1]
        region[inside] = tri.vertices[:]
        region = weights[low[1] : high[1] + 1, low[0] : high[0] + 1]
        region[inside] = np.stack((a, b, c), axis=-1)[inside]
    eye_ids = {
        i
        for p in mesh.polygons
        if mesh.materials[p.material_index].name in ACTORS[actor]["eyes"]
        for i in p.vertices
    }
    eyez = np.mean([mesh.vertices[i].co.z for i in eye_ids])
    z = np.asarray([v.co.z for v in mesh.vertices], np.float32)
    height = np.clip(
        ((z[indices] * weights).sum(axis=2) - (eyez - 0.022)) / 0.028, 0, 1
    )
    height = height * height * (3 - 2 * height)
    valid = weights.sum(axis=2) > 0.5
    height *= valid
    casters = [
        p.vertices[:]
        for p in mesh.polygons
        if (
            mesh.materials[p.material_index].get("look_category") == "hair"
            or mesh.materials[p.material_index].get("ikhor_material_role") == "hair"
        )
        and not mesh.materials[p.material_index].name.endswith("+")
    ]
    return {
        "indices": indices,
        "weights": weights,
        "height": height,
        "casters": casters,
        "face_vertices": sorted({i for t in triangles for i in t.vertices}),
        "face": face,
    }


def shadow_pixels(scene, obj, actor, template):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    assert len(mesh.vertices) >= len(obj.data.vertices)
    coords = [obj.matrix_world @ v.co for v in mesh.vertices]
    tree = BVHTree.FromPolygons(
        coords, template["casters"], all_triangles=False, epsilon=0.00001
    )
    lamp = scene.objects[PREFIX + actor + " directional head key"]
    points = [
        lamp.matrix_world.translation + lamp.matrix_world.to_3x3() @ Vector((x, 0, 0))
        for x in (-0.10, 0, 0.10)
    ]
    shade = np.ones(len(obj.data.vertices), np.float32)
    for index in template["face_vertices"]:
        p = coords[index]
        lit = 0
        for source in points:
            ray = source - p
            distance = ray.length
            ray.normalize()
            hit, _, _, depth = tree.ray_cast(
                p + ray * 0.00025, ray, max(0, distance - 0.00025)
            )
            lit += 0 if hit is not None and depth < 0.055 else 1
        shade[index] = lit / 3
    values = (shade[template["indices"]] * template["weights"]).sum(axis=2)
    result = 1 - (1 - values) * template["height"] * 0.88
    evaluated.to_mesh_clear()
    return result


def main():
    register_addons()
    old = ROOT / "production-v11/Franken_Duet_Goo_Eye_Hair_Stage.blend"
    production = ROOT / "production-v12"
    production.mkdir(exist_ok=False)
    sequence = production / "hair-shadows"
    sequence.mkdir()
    bpy.ops.wm.open_mainfile(filepath=str(old), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    specs = {
        actor: uv_template(scene.objects[spec["mesh"]], actor)
        for actor, spec in ACTORS.items()
    }
    for actor, spec in ACTORS.items():
        trial = shadow_pixels(scene, scene.objects[spec["mesh"]], actor, specs[actor])
        reference = (
            bpy.data.materials[specs[actor]["face"]]
            .node_tree.nodes[PREFIX + "geometry derived hair shadow"]
            .image
        )
        raw = np.empty(SIZE * SIZE * 4, np.float32)
        reference.pixels.foreach_get(raw)
        difference = np.abs(trial - raw.reshape(SIZE, SIZE, 4)[:, :, 0])
        assert difference.max() < 0.009, (actor, float(difference.max()))
        print("UV_TEMPLATE_REFERENCE_MATCH", actor, float(difference.max()), flush=True)
    rows = []
    started = time.perf_counter()
    for frame in range(4140, 4440):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for actor, spec in ACTORS.items():
            pixels = shadow_pixels(
                scene, scene.objects[spec["mesh"]], actor, specs[actor]
            )
            path = sequence / f"{actor}_{frame - 4139:04d}.png"
            im = save_mask(path, pixels)
            bpy.data.images.remove(im)
            rows.append(
                {
                    "actor": actor,
                    "source_frame": frame,
                    "file": path.name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "mean_visibility": float(pixels.mean()),
                    "min_visibility": float(pixels.min()),
                }
            )
        if (frame - 4139) % 20 == 0:
            print(
                "ANIMATED_BANG_SHADOW",
                frame - 4139,
                "/300",
                round(time.perf_counter() - started, 1),
                flush=True,
            )
    for actor, template in specs.items():
        tree = bpy.data.materials[template["face"]].node_tree
        tex = tree.nodes[PREFIX + "geometry derived hair shadow"]
        im = bpy.data.images.load(
            str(sequence / f"{actor}_0001.png"), check_existing=False
        )
        im.source = "SEQUENCE"
        im.colorspace_settings.name = "Non-Color"
        tex.image = im
        tex.image_user.frame_start = 4140
        tex.image_user.frame_duration = 300
        tex.image_user.frame_offset = 0
        tex.image_user.use_auto_refresh = True
        tex.image_user.use_cyclic = False
        im.filepath = f"//hair-shadows/{actor}_0001.png"
        tree.nodes[PREFIX + "authored nose form mask"].image.pack()
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    for actor in ACTORS:
        assert len({r["sha256"] for r in rows if r["actor"] == actor}) > 20
    manifest = {
        "frames": [4140, 4439],
        "files": rows,
        "algorithm": "actual deformed hair BVH / three head-key samples / face UV raster; local distance and forehead permission",
        "distance_limit_m": 0.055,
        "maximum_coverage": 0.88,
        "size": [SIZE, SIZE],
        "elapsed_seconds": time.perf_counter() - started,
        "portable_relative_paths": True,
    }
    (production / "hair-shadow-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    prep = json.loads((old.parent / "preparation.json").read_text(encoding="utf-8"))
    prep.update(
        source=str(old),
        source_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
        project=str(project),
        project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
        animated_hair_shadows={k: v for k, v in manifest.items() if k != "files"},
    )
    (production / "preparation.json").write_text(
        json.dumps(prep, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("ANIMATED_HAIR_SHADOW_MASTER_SAVED", flush=True)


if __name__ == "__main__":
    main()
