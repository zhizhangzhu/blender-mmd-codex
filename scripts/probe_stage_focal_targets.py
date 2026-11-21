"""Locate actual rendered surfaces under image-space lighting targets."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

scene = bpy.context.scene
scene.frame_set(4250)
hidden = []
for obj in scene.objects:
    volume_only = obj.type == "MESH" and any(
        m
        and m.node_tree
        and any(
            n.type == "OUTPUT_MATERIAL"
            and n.inputs["Volume"].is_linked
            and not n.inputs["Surface"].is_linked
            for n in m.node_tree.nodes
        )
        for m in obj.data.materials
    )
    if obj.hide_render or volume_only:
        hidden.append((obj, obj.hide_get()))
        obj.hide_set(True)
bpy.context.view_layer.update()
graph = bpy.context.evaluated_depsgraph_get()
inverse = scene.camera.calc_matrix_camera(graph, x=1920, y=1080).inverted()
origin = scene.camera.matrix_world.translation
results = []
for u in (0.16, 0.32, 0.50, 0.68, 0.84):
    for v in (0.15, 0.35, 0.55, 0.75, 0.90):
        local = inverse @ Vector((u * 2 - 1, v * 2 - 1, -1, 1))
        direction = (
            scene.camera.matrix_world.to_3x3() @ (local.xyz / local.w)
        ).normalized()
        ok, point, normal, face, obj, _ = scene.ray_cast(
            graph, origin, direction, distance=300
        )
        if ok:
            results.append(
                {
                    "screen_uv_bottom_origin": [u, v],
                    "point": list(point),
                    "normal": list(normal),
                    "object": obj.name,
                    "distance": (point - origin).length,
                    "performer": obj.get("performer_id"),
                    "material": obj.data.materials[
                        obj.data.polygons[face].material_index
                    ].name,
                }
            )
for obj, was_hidden in hidden:
    obj.hide_set(was_hidden)
out = Path(sys.argv[sys.argv.index("--") + 1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("STAGE_FOCAL_SURFACES", json.dumps(results), flush=True)
