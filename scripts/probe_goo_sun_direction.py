"""Find architectural openings from the performance floor by geometric rays."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

register_addons()
bpy.ops.wm.open_mainfile(
    filepath="D:/codex/output/MMD-Goo-Wedding-v2/production-v1/Franken_Duet_Goo_Daylight.blend",
    use_scripts=False,
    load_ui=False,
)
s = bpy.context.scene
s.frame_set(4140)
deps = bpy.context.evaluated_depsgraph_get()
out = []
for x in (-1, 1):
    for y in (-0.8, -0.65, -0.35, -0.2, 0.15, 0.3, 0.65, 0.8):
        for z in (0.42, 0.48, 0.54, 0.66, 0.72, 0.78, 1.05, 1.15):
            d = Vector((x, y, z)).normalized()
            pos = Vector((0, 0.4, 0.06))
            blocker = None
            for _ in range(100):
                hit, loc, normal, index, obj, _ = s.ray_cast(deps, pos, d, distance=150)
                if not hit:
                    break
                material = (
                    obj.data.materials[obj.data.polygons[index].material_index]
                    if obj.type == "MESH" and 0 <= index < len(obj.data.polygons)
                    else None
                )
                pure_transparent = (
                    material
                    and material.node_tree
                    and any(
                        n.type == "BSDF_TRANSPARENT" for n in material.node_tree.nodes
                    )
                    and not any(
                        n.type in ("BSDF_PRINCIPLED", "EMISSION")
                        for n in material.node_tree.nodes
                    )
                )
                material_nodes = (
                    material.node_tree.nodes if material and material.node_tree else ()
                )
                if (
                    not obj.hide_render
                    and not obj.get("performer_id")
                    and not pure_transparent
                    and obj.type == "MESH"
                    and material
                    and not any(n.type == "VOLUME_PRINCIPLED" for n in material_nodes)
                ):
                    blocker = {
                        "object": obj.name,
                        "material": material.name if material else None,
                        "location": list(loc),
                    }
                    break
                pos = loc + d * 0.01
            out.append({"direction": [x, y, z], "blocker": blocker})
Path("D:/codex/temp/MME-Deep-Study-2026-11-16/sun-directions.json").write_text(
    json.dumps(out, ensure_ascii=False), encoding="utf-8"
)
print("SUN_DIRECTIONS", [x for x in out if x["blocker"] is None], flush=True)
