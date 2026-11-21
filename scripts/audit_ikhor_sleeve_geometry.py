"""Read-only geometric audit of Ikhor's wrist/cuff relationship.

Opens independent native, portable and production files; never saves a blend.
All outputs are evidence under the requested new directory. PMX seam vertices
are welded by rest position only for identifying true cloth boundary loops.
"""

import argparse
import colorsys
import hashlib
import importlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

CLOTH_NAMES = {"衣", "衣2"}


def source_digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluated_coords(mesh, depsgraph):
    evaluated = mesh.evaluated_get(depsgraph)
    emesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    assert len(emesh.vertices) == 29959
    data = np.empty(len(emesh.vertices) * 3, dtype=np.float64)
    emesh.vertices.foreach_get("co", data)
    local = data.reshape(-1, 3)
    matrix = np.array(evaluated.matrix_world)
    coords = local @ matrix[:3, :3].T + matrix[:3, 3]
    evaluated.to_mesh_clear()
    return coords


def visible_crossings(coords, triangles, crossings, camera):
    """Conservative geometric camera visibility, without shader/DOF/outline."""
    if camera is None:
        return
    tree = BVHTree.FromPolygons(
        [Vector(p) for p in coords], triangles, all_triangles=True
    )
    for crossing in crossings:
        p = np.mean(crossing["points"], axis=0)
        direction = Vector(p) - Vector(camera)
        distance = direction.length
        hit, _normal, _index, hitdistance = tree.ray_cast(
            Vector(camera), direction.normalized(), distance + 0.001
        )
        crossing["camera_geometry_visible"] = (
            hit is not None and abs(hitdistance - distance) < 0.0004
        )


def mesh_topology(mesh):
    materials = {i: source_name(m) for i, m in enumerate(mesh.data.materials)}
    mesh.data.calc_loop_triangles()
    triangles = [
        (tuple(t.vertices), materials[t.material_index])
        for t in mesh.data.loop_triangles
    ]
    sleeve = {}
    for side in ["R", "L"]:
        group_ids = {
            g.index
            for g in mesh.vertex_groups
            if g.name in [f"Bone_Sleeve01_{side}", f"Bone_Sleeve02_{side}"]
        }
        sleeve[side] = {
            v.index
            for v in mesh.data.vertices
            if sum(g.weight for g in v.groups if g.group in group_ids) > 0.001
        }
    visible = [t for t, name in triangles if name not in {"bq", "灯", "环"}]
    return materials, triangles, sleeve, visible


def plain(matrix):
    return [float(v) for row in matrix for v in row]


def source_name(mat):
    return mat.get("source_mmd_material_name", mat.mmd_material.name_j or mat.name)


def bone_j(arm, name):
    return next(b for b in arm.pose.bones if b.mmd_bone.name_j == name)


def point(matrix, p):
    return np.array(matrix @ Vector(p), dtype=float)


def component_loops(mesh, arm):
    cloth = {"衣", "衣2", "衣领", "带子", "衣饰", "裙"}
    ids, lookup, representatives = [], {}, []
    for vertex in mesh.data.vertices:
        key = tuple(round(float(v), 6) for v in vertex.co)
        if key not in lookup:
            lookup[key] = len(representatives)
            representatives.append(vertex.index)
        ids.append(lookup[key])
    counts = Counter()
    for polygon in mesh.data.polygons:
        if source_name(mesh.data.materials[polygon.material_index]) not in cloth:
            continue
        vertices = list(polygon.vertices)
        for a, b in zip(vertices, vertices[1:] + vertices[:1]):
            ca, cb = ids[a], ids[b]
            if ca != cb:
                counts[tuple(sorted((ca, cb)))] += 1
    adjacency = defaultdict(set)
    for (a, b), count in counts.items():
        if count == 1:
            adjacency[a].add(b)
            adjacency[b].add(a)
    components, seen = [], set()
    for first in adjacency:
        if first in seen:
            continue
        group, stack = set(), [first]
        while stack:
            current = stack.pop()
            if current in group:
                continue
            group.add(current)
            stack.extend(adjacency[current] - group)
        seen.update(group)
        if len(group) < 6:
            continue
        raw = [representatives[i] for i in sorted(group)]
        center = np.mean(
            [point(mesh.matrix_world, mesh.data.vertices[i].co) for i in raw], axis=0
        )
        distances = {}
        for side, japanese in [("R", "右手首"), ("L", "左手首")]:
            wrist = point(arm.matrix_world, bone_j(arm, japanese).bone.head_local)
            distances[side] = float(np.linalg.norm(center - wrist))
        if min(distances.values()) < 0.25:
            components.append(
                {
                    "id": len(components),
                    "vertices": raw,
                    "closed_degree2": all(len(adjacency[i]) == 2 for i in group),
                    "rest_center": center.tolist(),
                    "rest_wrist_distances": distances,
                }
            )
    return components


def fit_loop(raw, coords, elbow, wrist):
    points = coords[raw]
    center = points.mean(axis=0)
    _, singular, vectors = np.linalg.svd(points - center, full_matrices=False)
    normal = vectors[-1]
    segment = wrist - elbow
    denom = float(np.dot(normal, segment))
    t = float(np.dot(normal, center - elbow) / denom) if abs(denom) > 1e-9 else None
    crossing = elbow + t * segment if t is not None else None
    radius = np.linalg.norm(points - center, axis=1)
    return {
        "center": center.tolist(),
        "normal": normal.tolist(),
        "planarity_rms": float(np.sqrt(np.mean(((points - center) @ normal) ** 2))),
        "radius_min_median_max": [
            float(radius.min()),
            float(np.median(radius)),
            float(radius.max()),
        ],
        "wrist_plane_signed_distance": float(np.dot(normal, wrist - center)),
        "forearm_axis_plane_crossing_t": t,
        "forearm_axis_crossing_radius": float(np.linalg.norm(crossing - center))
        if crossing is not None
        else None,
        "wrist_axis_to_plane_normal_degrees": float(
            math.degrees(
                math.acos(np.clip(abs(denom) / (np.linalg.norm(segment) + 1e-12), 0, 1))
            )
        ),
        "singular_values": singular.tolist(),
    }


def triangle_crossings(coords, skin_triangles, cloth_triangles):
    """Exact segment/triangle intersections after BVH candidate generation."""
    sv = [Vector(p) for p in coords]
    skin_tree = BVHTree.FromPolygons(sv, skin_triangles, all_triangles=True)
    cloth_tree = BVHTree.FromPolygons(sv, cloth_triangles, all_triangles=True)
    results = []
    for si, ci in skin_tree.overlap(cloth_tree):
        a, b = skin_triangles[si], cloth_triangles[ci]
        intersections = []
        for segment, triangle in ((a, b), (b, a)):
            for j in range(3):
                start, end = sv[segment[j]], sv[segment[(j + 1) % 3]]
                direction = end - start
                length = direction.length
                if length < 1e-8:
                    continue
                hit = intersect_ray_tri(
                    sv[triangle[0]],
                    sv[triangle[1]],
                    sv[triangle[2]],
                    direction.normalized(),
                    start,
                    True,
                )
                if (
                    hit is not None
                    and 1e-6 < (hit - start).length < length - 1e-6
                    and (hit - start).dot(direction) > 0
                ):
                    intersections.append(list(hit))
        if len(intersections) >= 2:
            points = np.unique(np.round(intersections, 7), axis=0)
            if len(points) >= 2 and np.linalg.norm(points[0] - points[-1]) > 1e-5:
                results.append(
                    {"skin": list(a), "cloth": list(b), "points": points.tolist()}
                )
    return results


def wrist_sections(coords, skin_triangles, wrist, axis):
    sections = []
    for offset in [-0.06, -0.045, -0.03, -0.015, 0.0, 0.015, 0.03]:
        center = wrist + axis * offset
        hits = []
        for triangle in skin_triangles:
            points = coords[list(triangle)]
            distances = (points - center) @ axis
            if distances.min() > 0 or distances.max() < 0:
                continue
            for j in range(3):
                a, b = j, (j + 1) % 3
                if distances[a] * distances[b] < 0:
                    t = distances[a] / (distances[a] - distances[b])
                    hits.append(points[a] + t * (points[b] - points[a]))
        radial = np.linalg.norm(np.array(hits) - center, axis=1) if hits else None
        sections.append(
            {
                "axis_offset_m": offset,
                "intersection_points": len(hits),
                "radius_min_median_max_m": [
                    float(radial.min()),
                    float(np.median(radial)),
                    float(radial.max()),
                ]
                if hits
                else None,
            }
        )
    return sections


def capture(path, frame, label, existing_loops=None, output_dir=None):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    scene = bpy.context.scene
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    arms = [
        o
        for o in scene.objects
        if o.type == "ARMATURE" and o.get("performer_id") == "ikhor"
    ]
    assert len(arms) == 1
    arm = arms[0]
    native_fix = []
    # Native source contains an invalid additional rotation targeting itself.
    # For pose comparison only, remove precisely its generated self constraint.
    if label.startswith("native"):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from prepare_ikhor_motion import repair_self_inheritance

        pmx = importlib.import_module("bl_ext.blender_org.mmd_tools.core.pmx")
        native_fix = repair_self_inheritance(
            arm, pmx.load(r"D:/codex/output/MMD-Ikhor-Model-v1/source/Ikhor/Ikhor.pmx")
        )
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    mesh = next(
        o
        for o in scene.objects
        if o.type == "MESH"
        and len(o.data.vertices) == 29959
        and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)
    )
    for mod in mesh.modifiers:
        if mod.name == "mmd_edge_preview":
            mod.show_viewport = False
    bpy.context.view_layer.update()
    loops = existing_loops or component_loops(mesh, arm)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    coords = evaluated_coords(mesh, depsgraph)
    materials = {i: source_name(m) for i, m in enumerate(mesh.data.materials)}
    arms_report = {}
    geometry = {"coords": coords}
    all_material_verts = defaultdict(set)
    for poly in mesh.data.polygons:
        for index in poly.vertices:
            all_material_verts[materials[poly.material_index]].add(index)
    _, triangles, sleeve_vertices, visible_triangles = mesh_topology(mesh)
    geometry["visible_triangles"] = np.array(visible_triangles, dtype=np.int32)
    for side, japanese, elbow_name in [
        ("R", "右手首", "右ひじ"),
        ("L", "左手首", "左ひじ"),
    ]:
        wrist = point(arm.matrix_world, bone_j(arm, japanese).head)
        elbow = point(arm.matrix_world, bone_j(arm, elbow_name).head)
        axis = (wrist - elbow) / np.linalg.norm(wrist - elbow)
        near = np.where(np.linalg.norm(coords - wrist, axis=1) < 0.15)[0]
        weights = Counter()
        near_materials = Counter()
        for index in near:
            v = mesh.data.vertices[int(index)]
            for group in v.groups:
                if mesh.vertex_groups[group.group].name in arm.pose.bones:
                    weights[mesh.vertex_groups[group.group].name] += group.weight
        for name, indices in all_material_verts.items():
            near_materials[name] = len({int(i) for i in near} & indices)
        loop_results = []
        for loop in loops:
            if loop["rest_wrist_distances"][side] < 0.25:
                loop_results.append(
                    {
                        "id": loop["id"],
                        "vertex_count": len(loop["vertices"]),
                        "closed_degree2": loop["closed_degree2"],
                        **fit_loop(loop["vertices"], coords, elbow, wrist),
                        "source_vertex_weights": [
                            {
                                "vertex": index,
                                "weights": [
                                    [mesh.vertex_groups[group.group].name, group.weight]
                                    for group in mesh.data.vertices[index].groups
                                    if mesh.vertex_groups[group.group].name
                                    in arm.pose.bones
                                ],
                            }
                            for index in loop["vertices"]
                        ],
                    }
                )
        samples = []
        for name in ["衣", "衣2", "手", "环", "灯"]:
            indices = sorted(
                {int(i) for i in near} & all_material_verts.get(name, set())
            )
            if not indices:
                continue
            # Nearest vertices expose actual primary groups and original UVs.
            indices = sorted(
                indices, key=lambda i: float(np.linalg.norm(coords[i] - wrist))
            )[:12]
            for index in indices:
                v = mesh.data.vertices[index]
                samples.append(
                    {
                        "vertex": index,
                        "material": name,
                        "world": coords[index].tolist(),
                        "weights": [
                            [mesh.vertex_groups[g.group].name, g.weight]
                            for g in v.groups
                        ],
                    }
                )
        near_set = {int(i) for i in near}
        skin_tris = [
            t for t, name in triangles if name == "手" and near_set.intersection(t)
        ]
        cloth_tris = [
            t
            for t, name in triangles
            if name in {"衣", "衣2"} and sleeve_vertices[side].intersection(t)
        ]
        crossings = triangle_crossings(coords, skin_tris, cloth_tris)
        for crossing in crossings:
            center = np.mean(crossing["points"], axis=0)
            crossing["center_axis_offset_m"] = float(np.dot(center - wrist, axis))
            crossing["center_wrist_distance_m"] = float(np.linalg.norm(center - wrist))
        all_cloth_near = [
            t
            for t, name in triangles
            if name in CLOTH_NAMES and near_set.intersection(t)
        ]
        all_crossings = triangle_crossings(coords, skin_tris, all_cloth_near)
        hand_tree = BVHTree.FromPolygons(
            [Vector(p) for p in coords], skin_tris, all_triangles=True
        )
        cloth_details = {}
        for index in {v for x in all_crossings for v in x["cloth"]}:
            nearest, normal, _face, distance = hand_tree.find_nearest(
                Vector(coords[index])
            )
            signed = (
                float((Vector(coords[index]) - nearest).dot(normal))
                if nearest is not None
                else None
            )
            cloth_details[str(index)] = {
                "weights": [
                    [mesh.vertex_groups[g.group].name, g.weight]
                    for g in mesh.data.vertices[index].groups
                    if mesh.vertex_groups[g.group].name in arm.pose.bones
                ],
                "world": coords[index].tolist(),
                "nearest_skin_distance_m": float(distance)
                if distance is not None
                else None,
                "nearest_skin_normal_signed_distance_m": signed,
                "nearest_skin_world": list(nearest) if nearest is not None else None,
                "nearest_skin_normal": list(normal) if normal is not None else None,
            }
        sampled_faces = []
        for triangle in {tuple(x["cloth"]) for x in all_crossings}:
            minimum = None
            for i in range(7):
                for j in range(7 - i):
                    barycentric_weights = np.array([i, j, 6 - i - j], dtype=float) / 6
                    p = barycentric_weights @ coords[list(triangle)]
                    nearest, normal, _face, distance = hand_tree.find_nearest(Vector(p))
                    if nearest is None:
                        continue
                    signed = float((Vector(p) - nearest).dot(normal))
                    if (
                        minimum is None
                        or signed < minimum["skin_normal_signed_distance_m"]
                    ):
                        minimum = {
                            "triangle": list(triangle),
                            "barycentric": barycentric_weights.tolist(),
                            "sample_world": p.tolist(),
                            "nearest_skin_world": list(nearest),
                            "nearest_skin_normal": list(normal),
                            "skin_normal_signed_distance_m": signed,
                        }
            sampled_faces.append(minimum)
        visible_crossings(
            coords,
            visible_triangles,
            all_crossings,
            list(scene.camera.matrix_world.translation) if scene.camera else None,
        )
        for x in all_crossings:
            x["axis_offset_m"] = float(
                np.dot(np.mean(x["points"], axis=0) - wrist, axis)
            )
        cyan = []
        image = next(
            (
                im
                for im in bpy.data.images
                if "Avatar_Boy_Undefined_Purusa_Tex_Body_Diffuse" in im.name
                or "Avatar_Boy_Undefined_Purusa_Tex_Body_Diffuse" in im.filepath
            ),
            None,
        )
        if image and mesh.data.uv_layers.active:
            pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
                image.size[1], image.size[0], 4
            )
            for poly in mesh.data.polygons:
                if materials[poly.material_index] not in {
                    "衣",
                    "衣2",
                } or not sleeve_vertices[side].intersection(poly.vertices):
                    continue
                uv = (
                    np.mean(
                        [
                            mesh.data.uv_layers.active.data[i].uv[:]
                            for i in poly.loop_indices
                        ],
                        axis=0,
                    )
                    % 1
                )
                rgb = pixels[
                    min(int(uv[1] * image.size[1]), image.size[1] - 1),
                    min(int(uv[0] * image.size[0]), image.size[0] - 1),
                    :3,
                ]
                h, s, v = colorsys.rgb_to_hsv(*rgb)
                if 0.45 < h < 0.66 and s > 0.32 and v > 0.16:
                    cyan.append(
                        {
                            "polygon": poly.index,
                            "vertices": list(poly.vertices),
                            "uv": uv.tolist(),
                            "rgb_srgb": rgb.tolist(),
                            "world_center": np.mean(
                                coords[list(poly.vertices)], axis=0
                            ).tolist(),
                        }
                    )
        geometry[f"{side}_skin_triangles"] = np.array(skin_tris, dtype=np.int32)
        geometry[f"{side}_cloth_triangles"] = np.array(cloth_tris, dtype=np.int32)
        geometry[f"{side}_wrist"] = wrist
        geometry[f"{side}_elbow"] = elbow
        arms_report[side] = {
            "wrist": wrist.tolist(),
            "elbow": elbow.tolist(),
            "near_vertices": len(near),
            "materials": dict(near_materials),
            "weight_sum": dict(weights.most_common(18)),
            "boundary_loops": loop_results,
            "nearest_samples": samples,
            "skin_wrist_sections": wrist_sections(coords, skin_tris, wrist, axis),
            "cloth_skin_exact_intersections": crossings,
            "skin_triangles": len(skin_tris),
            "sleeve_triangles": len(cloth_tris),
            "all_near_cloth_triangles": len(all_cloth_near),
            "all_near_cloth_intersections": all_crossings,
            "intersection_cloth_vertex_details": cloth_details,
            "cloth_face_skin_distance_samples": sampled_faces,
            "cyan_textured_sleeve_polygons": cyan,
            "sleeve_vertex_positions": {
                str(i): coords[i].tolist() for i in sorted(sleeve_vertices[side])
            },
        }
    bones = {}
    for bone in arm.pose.bones:
        if any(
            word in bone.name.lower() for word in ["sleeve", "wrist"]
        ) or bone.mmd_bone.name_j in {"右手首", "左手首", "右ひじ", "左ひじ"}:
            bones[bone.name] = {
                "name_j": bone.mmd_bone.name_j,
                "parent": bone.parent.name if bone.parent else None,
                "matrix": plain(bone.matrix),
                "head": list(bone.head),
                "tail": list(bone.tail),
            }
    result = {
        "label": label,
        "path": str(path),
        "sha256": source_digest(path),
        "frame": frame,
        "native_self_constraint_removed_unsaved": native_fix,
        "camera_origin": list(scene.camera.matrix_world.translation)
        if scene.camera
        else None,
        "arms": arms_report,
        "bones": bones,
        "boundary_components": loops,
        "materials": [
            {
                "index": i,
                "name": m.name,
                "source_name": materials[i],
                "alpha": m.mmd_material.alpha,
                "triangles": sum(
                    len(p.vertices) - 2
                    for p in mesh.data.polygons
                    if p.material_index == i
                ),
            }
            for i, m in enumerate(mesh.data.materials)
            if not m.name.startswith("mmd_edge.")
        ],
        "modifiers": [[m.name, m.type] for m in mesh.modifiers],
        "body_images": [
            {"name": i.name, "filepath": i.filepath, "has_data": i.has_data}
            for i in bpy.data.images
            if "Body_Diffuse" in i.name or "Body_Diffuse" in i.filepath
        ],
    }
    if output_dir:
        np.savez_compressed(output_dir / f"{label}-geometry.npz", **geometry)
    return result


def scan_candidate(path, frames, output_dir, camera_reference=None):
    input_digest = source_digest(path)
    camera_digest = source_digest(camera_reference) if camera_reference else None
    reference_cameras = {}
    if camera_reference:
        bpy.ops.wm.open_mainfile(filepath=str(camera_reference), load_ui=False)
        reference_scene = bpy.context.scene
        assert reference_scene.camera, "Camera reference has no active camera."
        for frame in frames:
            reference_scene.frame_set(math.floor(frame), subframe=frame % 1)
            bpy.context.view_layer.update()
            reference_cameras[frame] = list(
                reference_scene.camera.matrix_world.translation
            )
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    scene = bpy.context.scene
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    arm = next(
        o
        for o in scene.objects
        if o.type == "ARMATURE" and o.get("performer_id") == "ikhor"
    )
    mesh = next(
        o
        for o in scene.objects
        if o.type == "MESH"
        and len(o.data.vertices) == 29959
        and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)
    )
    for modifier in mesh.modifiers:
        if modifier.name == "mmd_edge_preview":
            modifier.show_viewport = False
    _materials, triangles, sleeve, visible = mesh_topology(mesh)
    skin = [t for t, name in triangles if name == "手"]
    cloth = {
        s: [
            t
            for t, name in triangles
            if name in CLOTH_NAMES and sleeve[s].intersection(t)
        ]
        for s in ["R", "L"]
    }
    result = []
    for frame in frames:
        scene.frame_set(math.floor(frame), subframe=frame % 1)
        bpy.context.view_layer.update()
        coords = evaluated_coords(mesh, bpy.context.evaluated_depsgraph_get())
        finite_geometry = bool(np.isfinite(coords).all())
        finite_pose = all(
            bool(np.isfinite(np.array(b.matrix)).all()) for b in arm.pose.bones
        )
        assert finite_geometry and finite_pose, (
            f"Nonfinite evaluated actor geometry/pose at {frame}"
        )
        report = {
            "frame": frame,
            "arms": {},
            "finite_evaluated_actor_geometry": finite_geometry,
            "finite_actor_pose_bone_matrices": finite_pose,
            "evaluated_actor_vertices": len(coords),
        }
        camera = reference_cameras.get(frame) or (
            list(scene.camera.matrix_world.translation) if scene.camera else None
        )
        report["camera_origin"] = camera
        report["finite_camera_origin"] = (
            bool(np.isfinite(camera).all()) if camera is not None else None
        )
        assert camera is None or report["finite_camera_origin"], (
            f"Nonfinite camera at {frame}"
        )
        for side, japanese, elbow_name in [
            ("R", "右手首", "右ひじ"),
            ("L", "左手首", "左ひじ"),
        ]:
            wrist = point(arm.matrix_world, bone_j(arm, japanese).head)
            elbow = point(arm.matrix_world, bone_j(arm, elbow_name).head)
            axis = (wrist - elbow) / np.linalg.norm(wrist - elbow)
            near = set(np.where(np.linalg.norm(coords - wrist, axis=1) < 0.15)[0])
            crosses = triangle_crossings(
                coords, [t for t in skin if near.intersection(t)], cloth[side]
            )
            visible_crossings(coords, visible, crosses, camera)
            for x in crosses:
                x["axis_offset_m"] = float(
                    np.dot(np.mean(x["points"], axis=0) - wrist, axis)
                )
            rear = [x for x in crosses if x["axis_offset_m"] < 0]
            vis = [x for x in crosses if x.get("camera_geometry_visible")]
            visrear = [x for x in vis if x["axis_offset_m"] < 0]
            report["arms"][side] = {
                "pairs": len(crosses),
                "wrist_rear_pairs": len(rear),
                "camera_geometry_visible_pairs": len(vis)
                if camera is not None
                else None,
                "camera_visible_wrist_rear_pairs": len(visrear)
                if camera is not None
                else None,
                "axis_offset_min_max_m": [
                    min(x["axis_offset_m"] for x in crosses),
                    max(x["axis_offset_m"] for x in crosses),
                ]
                if crosses
                else None,
                "visible_intersections": vis,
            }
        result.append(report)
        if len(result) % 10 == 0:
            print("SLEEVE_SCAN_PROGRESS", len(result), len(frames), flush=True)
    worst = {
        side: sorted(
            result,
            key=lambda r: (
                r["arms"][side]["camera_visible_wrist_rear_pairs"] or 0,
                r["arms"][side]["camera_geometry_visible_pairs"] or 0,
                r["arms"][side]["pairs"],
            ),
            reverse=True,
        )[:15]
        for side in ["R", "L"]
    }
    output = {
        "candidate": str(path),
        "candidate_sha256": input_digest,
        "camera_reference": str(camera_reference) if camera_reference else None,
        "camera_reference_sha256": camera_digest,
        "frames": result,
        "worst_frames": {
            side: [
                {
                    "frame": r["frame"],
                    **{
                        k: v
                        for k, v in r["arms"][side].items()
                        if k != "visible_intersections"
                    },
                }
                for r in data
            ]
            for side, data in worst.items()
        },
        "limits": [
            "Geometric midpoint ray visibility excludes bq, ring and lamp and assumes remaining actor triangles opaque; it does not include outlines, hair alpha, other actor, stage, DOF or final compositing.",
            "Triangle-pair counts depend on fixed topology, not penetration depth; source design overlaps must be visually reviewed.",
            "Raw ray flags are review candidates, not a beauty failure, an opaque-wall penetration classification or a requirement to eliminate designed cuff-edge contact.",
        ],
        "saved_blend": False,
    }
    (output_dir / "sleeve-continuous-scan.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print("SLEEVE_SCAN_COMPLETE", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--baked", type=Path)
    parser.add_argument("--production", type=Path)
    parser.add_argument(
        "--candidate",
        type=Path,
        help="Independently saved new master/portable candidate; actual bound action is evaluated.",
    )
    parser.add_argument(
        "--camera-reference",
        type=Path,
        help="Optional production master with matching world/time; supplies actual animated camera to a camera-less portable.",
    )
    parser.add_argument(
        "--frames",
        default="4140:4439",
        help="Inclusive start:end, or comma-separated frames.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--frame",
        type=float,
        default=4290,
        help="Single output60 frame used by three-source comparison.",
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    if args.candidate:
        if ":" in args.frames:
            start, end = [int(v) for v in args.frames.split(":")]
            frames = list(range(start, end + 1))
        else:
            frames = [float(v) for v in args.frames.split(",")]
        scan_candidate(args.candidate, frames, args.output_dir, args.camera_reference)
        return
    if not all([args.native, args.baked, args.production]):
        parser.error(
            "Supply --candidate or all three --native/--baked/--production paths."
        )
    frame = args.frame
    source_import_frame = 330 + (frame - 1) / 2
    native = capture(
        args.native,
        source_import_frame,
        f"native-vmd-{frame:g}-equivalent",
        output_dir=args.output_dir,
    )
    baked = capture(
        args.baked,
        frame,
        f"baked-{frame:g}",
        native["boundary_components"],
        args.output_dir,
    )
    production = capture(
        args.production,
        frame,
        f"production-{frame:g}",
        native["boundary_components"],
        args.output_dir,
    )
    for cap in [native, baked, production]:
        geometry = np.load(args.output_dir / f"{cap['label']}-geometry.npz")
        for side in ["R", "L"]:
            visible_crossings(
                geometry["coords"],
                geometry["visible_triangles"],
                cap["arms"][side]["cloth_skin_exact_intersections"],
                production["camera_origin"],
            )
            visible_crossings(
                geometry["coords"],
                geometry["visible_triangles"],
                cap["arms"][side]["all_near_cloth_intersections"],
                production["camera_origin"],
            )
    report = {
        "read_only_sources": True,
        "saved_blend": False,
        "rendered": False,
        "captures": [native, baked, production],
        "limits": [
            "Position-welded boundaries identify candidate open loops, not all manifold guarantees.",
            "Forearm-axis-to-loop measurements are geometric diagnostics, not a full mesh penetration certificate.",
        ],
    }
    (args.output_dir / "sleeve-geometry-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("SLEEVE_GEOMETRY_AUDIT_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
