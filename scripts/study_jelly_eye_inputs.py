"""Inventory the saved duet's eye geometry and shading without modifying it."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

SOURCE = Path(
    "D:/codex/output/MMD-Goo-Window-Wrap-v1/production-v3/Franken_Duet_Goo_Window_Wrap.blend"
)
SHA = "ed81e7325e7ef3f47fe80dd63b53e1e0e713f7d2b93b9dd4e6e296195a350d85"


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.scene.frame_set(4290)
    report = {
        "source": str(SOURCE),
        "source_sha256": SHA,
        "objects": [],
        "materials": {},
    }
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or not obj.data.shape_keys:
            continue
        mats = [m.name if m else "" for m in obj.data.materials]
        keys = obj.data.shape_keys.key_blocks
        blink = [
            k.name
            for k in keys
            if any(
                t in k.name.lower()
                for t in ("blink", "まばた", "ウィンク", "笑い", "闭", "眨")
            )
        ]
        eyes = [
            m
            for m in obj.data.materials
            if m
            and any(t in m.name.lower() for t in ("瞳", "目", "eye", "iris", "高光"))
        ]
        row = {
            "name": obj.name,
            "materials": mats,
            "blink_keys": blink,
            "armature": getattr(obj.find_armature(), "name", None),
            "modifiers": [(m.name, m.type) for m in obj.modifiers],
            "eye_geometry": [],
        }
        for mat in eyes:
            mi = obj.data.materials.find(mat.name)
            ids = sorted(
                {
                    v
                    for p in obj.data.polygons
                    if p.material_index == mi
                    for v in p.vertices
                }
            )
            centers = [obj.data.vertices[i].co for i in ids]
            uv = obj.data.uv_layers.active
            uvs = (
                [
                    tuple(uv.data[i].uv)
                    for p in obj.data.polygons
                    if p.material_index == mi
                    for i in p.loop_indices
                ]
                if uv
                else []
            )
            row["eye_geometry"].append(
                {
                    "material": mat.name,
                    "vertices": len(ids),
                    "min": [min(c[a] for c in centers) for a in range(3)]
                    if centers
                    else None,
                    "max": [max(c[a] for c in centers) for a in range(3)]
                    if centers
                    else None,
                    "uv_bounds": [
                        [min(u[a] for u in uvs), max(u[a] for u in uvs)]
                        for a in range(2)
                    ]
                    if uvs
                    else None,
                }
            )
            if mat.name in report["materials"]:
                continue
            nodes = []
            for n in mat.node_tree.nodes:
                nodes.append(
                    {
                        "name": n.name,
                        "type": n.bl_idname,
                        "operation": getattr(n, "operation", None),
                        "image": getattr(getattr(n, "image", None), "name", None),
                        "inputs": [
                            {
                                "name": s.name,
                                "source": s.links[0].from_node.name
                                if s.is_linked
                                else None,
                                "socket": s.links[0].from_socket.name
                                if s.is_linked
                                else None,
                                "value": s.default_value
                                if isinstance(
                                    getattr(s, "default_value", None), (float, int)
                                )
                                else None,
                            }
                            for s in n.inputs
                        ],
                    }
                )
            report["materials"][mat.name] = {
                "custom": dict(mat.items()),
                "nodes": nodes,
            }
        row["blink_samples"] = []
        for frame in range(4100, 4441):
            bpy.context.scene.frame_set(frame)
            row["blink_samples"].append(
                {"frame": frame, "values": {name: keys[name].value for name in blink}}
            )
        report["objects"].append(row)
    out = Path("D:/codex/temp/jelly-eye-study-v1/production-eye-inputs.json")
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(
        "EYE_INPUTS",
        json.dumps(
            [
                {k: v for k, v in r.items() if k not in ("blink_samples", "materials")}
                for r in report["objects"]
            ],
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
