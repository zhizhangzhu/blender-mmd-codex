"""Read real window mesh islands and existing hair/rim controls, without rendering."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

SOURCE = Path(
    "D:/codex/output/MMD-Goo-Tyndall-Rim-v1/production-v7/Franken_Duet_Goo_Tyndall_Rim.blend"
)
assert (
    hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    == "25565d772273d9991c5c5eedafb8283e81e4f9c81d5724b707d542ecdb652f96"
)
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
scene = bpy.context.scene
scene.frame_set(4290)
bpy.context.view_layer.update()
result = {"windows": [], "materials": {}, "glow_sources": []}
for obj in scene.objects:
    if obj.type != "MESH":
        continue
    slots = {
        i
        for i, mat in enumerate(obj.data.materials)
        if mat and mat.name.startswith("mat_89")
    }
    if not slots:
        continue
    parents = {}

    def find(index, parents=parents):
        parents.setdefault(index, index)
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for polygon in obj.data.polygons:
        if polygon.material_index not in slots:
            continue
        ids = list(polygon.vertices)
        root = find(ids[0])
        for index in ids[1:]:
            parents[find(index)] = root
    islands = {}
    for index in parents:
        islands.setdefault(find(index), []).append(
            obj.matrix_world @ obj.data.vertices[index].co
        )
    for points in islands.values():
        lo = [min(point[i] for point in points) for i in range(3)]
        hi = [max(point[i] for point in points) for i in range(3)]
        result["windows"].append(
            {
                "object": obj.name,
                "materials": [obj.data.materials[i].name for i in slots],
                "min": lo,
                "max": hi,
                "vertices": len(points),
                "hidden": obj.hide_render,
            }
        )
for name in ("前鬓", "鬓.001", "衣", "衣.001", "毛领"):
    mat = bpy.data.materials[name]
    result["materials"][name] = [
        {
            "name": node.name,
            "type": node.bl_idname,
            "inputs": [
                {
                    "i": i,
                    "name": sock.name,
                    "linked": sock.is_linked,
                    "value": list(sock.default_value)
                    if hasattr(sock.default_value, "__len__")
                    and not isinstance(sock.default_value, str)
                    else sock.default_value,
                }
                for i, sock in enumerate(node.inputs)
                if hasattr(sock, "default_value")
            ],
            "value": node.outputs[0].default_value if node.type == "VALUE" else None,
        }
        for node in mat.node_tree.nodes
        if any(
            label in node.name.lower()
            for label in (
                "width power only",
                "hair highlight",
                "hair band",
                "hdr gain only",
                "direction cosine",
            )
        )
    ]
for node in scene.compositing_node_group.nodes:
    if node.type == "GLARE":
        result["glow_sources"].append(
            {
                "name": node.name,
                "source": [
                    {"node": link.from_node.name, "socket": link.from_socket.name}
                    for link in node.inputs["Image"].links
                ],
            }
        )
folder = Path("D:/codex/temp/MMD-Goo-Window-Wrap-v1")
folder.mkdir(parents=True, exist_ok=True)
(folder / "window-and-rim-inventory.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("WINDOW_WRAP_INVENTORY", len(result["windows"]), flush=True)
