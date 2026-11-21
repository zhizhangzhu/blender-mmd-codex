"""Identify real stage surfaces by rays through the delivered camera."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from study_jelly_eye_inputs import SOURCE

register_addons()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
report = {}
for frame in (4140, 4290):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    cam = scene.camera
    corners = cam.data.view_frame(scene=scene)
    xmin, xmax = min(c.x for c in corners), max(c.x for c in corners)
    ymin, ymax = min(c.y for c in corners), max(c.y for c in corners)
    z = corners[0].z
    rows = []
    for x, y in (
        (0.05, 0.15),
        (0.12, 0.3),
        (0.20, 0.15),
        (0.35, 0.12),
        (0.52, 0.12),
        (0.80, 0.12),
        (0.93, 0.25),
        (0.10, 0.48),
        (0.26, 0.75),
        (0.38, 0.8),
        (0.50, 0.93),
        (0.67, 0.80),
        (0.77, 0.67),
        (0.90, 0.8),
    ):
        direction = (
            cam.matrix_world.to_3x3()
            @ Vector((xmin + x * (xmax - xmin), ymax - y * (ymax - ymin), z))
        ).normalized()
        origin = cam.matrix_world.translation.copy()
        for attempt in range(60):
            hit, point, normal, index, obj, _ = scene.ray_cast(
                bpy.context.evaluated_depsgraph_get(), origin, direction
            )
            if not hit:
                break
            skip = (
                obj.hide_render
                or obj.name.startswith(("Goo Tyndall", "Goo window wrap"))
                or obj.get("performer_id")
            )
            if (
                not skip
                and obj.data.materials
                and not any(
                    m and m.name.startswith(("mat_103", "mat_89"))
                    for m in obj.data.materials
                )
            ):
                break
            origin = point + direction * 0.002
        if hit:
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = evaluated.to_mesh()
            mi = mesh.polygons[index].material_index
            mat = evaluated.data.materials[mi]
            rows.append(
                {
                    "xy": [x, y],
                    "object": obj.name,
                    "material": mat.name,
                    "point": list(point),
                }
            )
            evaluated.to_mesh_clear()
    report[str(frame)] = rows
report["stage_materials"] = []
for m in bpy.data.materials:
    if m.name.startswith(("mat_", "Stage art | ground")) and m.node_tree:
        report["stage_materials"].append(
            {
                "name": m.name,
                "nodes": [
                    (n.name, n.bl_idname)
                    for n in m.node_tree.nodes
                    if n.type in ("BSDF_PRINCIPLED", "EMISSION")
                ],
                "textures": [
                    (n.name, n.image.name)
                    for n in m.node_tree.nodes
                    if n.type == "TEX_IMAGE" and n.image
                ],
            }
        )
Path("D:/codex/temp/jelly-eye-study-v1/stage-surfaces.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "STAGE_SURFACE_RAYS",
    json.dumps(
        {k: v for k, v in report.items() if k != "stage_materials"}, ensure_ascii=False
    ),
    flush=True,
)
