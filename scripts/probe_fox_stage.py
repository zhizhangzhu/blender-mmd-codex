"""Audit real ground surfaces, existing light linking and compositor routing."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

scene = bpy.context.scene
scene.frame_set(4250)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
hits = []
for x in (-2, 0, 2):
    for y in (-3, 0, 2, 5, 9):
        ok, point, normal, face, obj, _ = scene.ray_cast(
            depsgraph, Vector((x, y, 0.3)), Vector((0, 0, -1)), distance=10
        )
        if ok:
            material = obj.data.materials[obj.data.polygons[face].material_index]
            hits.append(
                {
                    "origin": [x, y, 0.3],
                    "point": list(point),
                    "normal": list(normal),
                    "object": obj.name,
                    "material": material.name,
                }
            )
materials = []
for mat in bpy.data.materials:
    if not mat.get("stage_id") or not mat.node_tree:
        continue
    materials.append(
        {
            "name": mat.name,
            "nodes": [
                {
                    "name": n.name,
                    "type": n.type,
                    "inputs": [
                        {
                            "name": s.name,
                            "links": [
                                [l.from_node.name, l.from_socket.name] for l in s.links
                            ],
                            "value": str(getattr(s, "default_value", None)),
                        }
                        for s in n.inputs
                    ],
                }
                for n in mat.node_tree.nodes
                if n.type
                in ("OUTPUT_MATERIAL", "MAP_RANGE", "EMISSION", "BSDF_PRINCIPLED")
            ],
        }
    )
report = {
    "ground_hits": hits,
    "stage_materials": materials,
    "lights": [
        {
            "name": o.name,
            "hidden": o.hide_render,
            "receiver": str(o.light_linking.receiver_collection),
            "volume": getattr(o.data, "volume_factor", None),
        }
        for o in scene.objects
        if o.type == "LIGHT"
    ],
    "compositor": [
        {
            "name": n.name,
            "type": n.type,
            "outputs": [s.name for s in n.outputs],
            "inputs": [
                {
                    "name": s.name,
                    "value": str(getattr(s, "default_value", None)),
                    "links": [[l.from_node.name, l.from_socket.name] for l in s.links],
                }
                for s in n.inputs
            ],
        }
        for n in scene.compositing_node_group.nodes
    ],
}
out = Path(sys.argv[sys.argv.index("--") + 1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("FOX_STAGE_PROBE_COMPLETE", flush=True)
