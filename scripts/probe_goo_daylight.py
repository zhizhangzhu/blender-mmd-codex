"""Read-only light, material and sky inventory for the next Goo study."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

register_addons()
bpy.ops.wm.open_mainfile(
    filepath="D:/codex/output/MMD-Goo-Wedding-v1/production-v1/Franken_Duet_Goo_Wedding.blend",
    load_ui=False,
    use_scripts=False,
)
s = bpy.context.scene
s.frame_set(4290)
deps = bpy.context.evaluated_depsgraph_get()
out = {
    "lights": [],
    "materials": {},
    "rays": [],
    "camera": list(s.camera.matrix_world.translation),
}
for o in s.objects:
    if o.type == "LIGHT" and not o.hide_render:
        out["lights"].append(
            {
                "name": o.name,
                "position": list(o.matrix_world.translation),
                "energy": o.data.energy,
                "type": o.data.type,
                "size": getattr(o.data, "size", 0),
                "group": [x.name for x in o.data.light_groups.groups],
            }
        )
for m in bpy.data.materials:
    if m.node_tree and (
        m.get("performer_id")
        or m.name.startswith("Stage art | ground only")
        or m.name == "mat_20.010"
    ):
        out["materials"][m.name] = {
            "actor": m.get("performer_id"),
            "role": m.get("character_layer_role", m.get("ikhor_material_role")),
            "nodes": [
                {
                    "name": n.name,
                    "type": n.bl_idname,
                    "inputs": {
                        i.name: list(i.default_value)
                        if hasattr(i.default_value, "__len__")
                        else i.default_value
                        for i in n.inputs
                        if hasattr(i, "default_value") and not i.is_linked
                    },
                }
                for n in m.node_tree.nodes
                if any(
                    k in n.name.lower()
                    for k in (
                        "hair",
                        "highlight",
                        "rimink",
                        "single portrait palette",
                        "daylight response",
                    )
                )
            ],
        }
for start in ((0, 0.4, 0.02), (0, 0.4, 1.5), (-0.8, 0.4, 0.02)):
    pos = Vector(start)
    direction = (Vector((-50, 10, 30)) - pos).normalized()
    hits = []
    for _ in range(12):
        hit, loc, normal, index, obj, _ = s.ray_cast(deps, pos, direction, distance=100)
        if not hit:
            break
        mat = (
            obj.data.materials[obj.data.polygons[index].material_index].name
            if obj.type == "MESH" and index < len(obj.data.polygons)
            else None
        )
        hits.append({"object": obj.name, "location": list(loc), "material": mat})
        pos = loc + direction * 0.005
    out["rays"].append({"start": start, "hits": hits})
Path("D:/codex/temp/MME-Deep-Study-2026-11-16/goo-scene-inventory.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("GOO_DAYLIGHT_PROBE_COMPLETE", flush=True)
