"""Read festivities' downloaded node library without executing embedded code."""

import json
import sys
from pathlib import Path

import bpy

out = Path(sys.argv[sys.argv.index("--") + 1])
out.mkdir(parents=True, exist_ok=False)


def value(s):
    v = getattr(s, "default_value", None)
    if isinstance(v, bpy.types.ID):
        return {"id": v.name, "type": type(v).__name__}
    return list(v) if hasattr(v, "__len__") and not isinstance(v, str) else v


groups = []
for group in bpy.data.node_groups:
    groups.append(
        {
            "name": group.name,
            "type": group.bl_idname,
            "sockets": [
                {
                    "name": s.name,
                    "direction": s.in_out,
                    "type": s.socket_type,
                    "value": value(s),
                }
                for s in group.interface.items_tree
                if s.item_type == "SOCKET"
            ],
            "nodes": [
                {
                    "name": n.name,
                    "type": n.bl_idname,
                    "group": n.node_tree.name
                    if n.type == "GROUP" and n.node_tree
                    else None,
                    "image": n.image.name
                    if n.type == "TEX_IMAGE" and n.image
                    else None,
                    "properties": {
                        k: getattr(n, k)
                        for k in [
                            "operation",
                            "attribute_name",
                            "vector_type",
                            "convert_from",
                            "convert_to",
                            "data_type",
                            "domain",
                        ]
                        if hasattr(n, k)
                    },
                    "inputs": [
                        {"name": s.name, "linked": s.is_linked, "value": value(s)}
                        for s in n.inputs
                    ],
                }
                for n in group.nodes
            ],
            "links": [
                [l.from_node.name, l.from_socket.name, l.to_node.name, l.to_socket.name]
                for l in group.links
            ],
        }
    )
report = {
    "groups": groups,
    "materials": [
        {
            "name": m.name,
            "nodes": [
                {
                    "name": n.name,
                    "type": n.bl_idname,
                    "group": n.node_tree.name
                    if n.type == "GROUP" and n.node_tree
                    else None,
                    "image": n.image.name
                    if n.type == "TEX_IMAGE" and n.image
                    else None,
                }
                for n in m.node_tree.nodes
            ],
            "links": [
                [l.from_node.name, l.from_socket.name, l.to_node.name, l.to_socket.name]
                for l in m.node_tree.links
            ],
        }
        for m in bpy.data.materials
        if m.node_tree
    ],
    "objects": [{"name": o.name, "type": o.type} for o in bpy.context.scene.objects],
}
(out / "library.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "LIBRARY_GROUPS",
    [(g["name"], [(s["name"], s["direction"]) for s in g["sockets"]]) for g in groups],
    flush=True,
)
print("MATERIALS", [m["name"] for m in report["materials"]], flush=True)
