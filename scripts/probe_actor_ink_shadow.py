"""Inspect the current actor hull and the preset's actual shadow sockets."""

import json
import sys
from pathlib import Path

import bpy


def value(socket):
    v = getattr(socket, "default_value", None)
    return list(v) if hasattr(v, "__len__") and not isinstance(v, str) else v


scene = bpy.context.scene
report = {"objects": [], "materials": [], "lights": [], "groups": []}
for obj in scene.objects:
    if obj.type == "MESH" and obj.get("performer_id"):
        report["objects"].append(
            {
                "object": obj.name,
                "actor": obj.get("performer_id"),
                "modifiers": [
                    {
                        "name": m.name,
                        "type": m.type,
                        "thickness": getattr(m, "thickness", None),
                        "group": getattr(m, "vertex_group", None),
                        "nodes": getattr(getattr(m, "node_group", None), "name", None),
                    }
                    for m in obj.modifiers
                ],
            }
        )
    if obj.type == "LIGHT" and (
        obj.name.startswith("Reference duet |")
        or obj.name in {"Stage art | grounded backlight", "Softlight | warm rear edge"}
    ):
        report["lights"].append(
            {
                "name": obj.name,
                "watts": obj.data.energy,
                "size": getattr(obj.data, "size", None),
                "receivers": [
                    o.name for o in obj.light_linking.receiver_collection.objects
                ]
                if obj.light_linking.receiver_collection
                else None,
            }
        )
for mat in bpy.data.materials:
    if not mat.node_tree or not mat.get("performer_id"):
        continue
    selected = []
    for node in mat.node_tree.nodes:
        if node.type == "GROUP" or node.name.startswith("Quality |"):
            selected.append(
                {
                    "name": node.name,
                    "type": node.bl_idname,
                    "group": getattr(getattr(node, "node_tree", None), "name", None),
                    "inputs": [
                        {"name": s.name, "value": value(s), "linked": s.is_linked}
                        for s in node.inputs
                    ],
                    "outputs": [s.name for s in node.outputs],
                }
            )
    if mat.get("source_mmd_material_name", mat.name).split(".")[0] in {
        "颜",
        "面1",
        "肌",
        "发",
    }:
        report["materials"].append(
            {
                "name": mat.name,
                "actor": mat.get("performer_id"),
                "source": mat.get("source_mmd_material_name"),
                "nodes": selected,
            }
        )
for group in bpy.data.node_groups:
    if "facefactor" in group.name.lower() or "face factor" in group.name.lower():
        report["groups"].append(
            {
                "name": group.name,
                "nodes": [
                    {
                        "name": n.name,
                        "type": n.bl_idname,
                        "group": getattr(getattr(n, "node_tree", None), "name", None),
                        "inputs": [
                            {
                                "name": s.name,
                                "value": value(s),
                                "from": [
                                    l.from_node.name + "." + l.from_socket.name
                                    for l in s.links
                                ],
                            }
                            for s in n.inputs
                        ],
                    }
                    for n in group.nodes
                ],
            }
        )
Path(sys.argv[-1]).write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("ACTOR_INK_SHADOW_PROBE_READY", flush=True)
