"""Audit current light/shader/layer capabilities without saving the source blend."""

import json
import sys
from pathlib import Path

import bpy


def val(socket):
    value = getattr(socket, "default_value", None)
    if isinstance(value, bpy.types.ID):
        return value.name
    return (
        list(value)
        if hasattr(value, "__len__") and not isinstance(value, str)
        else value
    )


scene = bpy.context.scene
scene.frame_set(4200)
bpy.context.view_layer.update()
materials = []
for material in bpy.data.materials:
    if not material.node_tree or not material.get("performer_id"):
        continue
    materials.append(
        {
            "name": material.name,
            "properties": dict(material.items()),
            "nodes": [
                {
                    "name": node.name,
                    "type": node.bl_idname,
                    "group": node.node_tree.name
                    if node.type == "GROUP" and node.node_tree
                    else None,
                    "inputs": [
                        {
                            "name": socket.name,
                            "value": val(socket),
                            "links": [
                                [link.from_node.name, link.from_socket.name]
                                for link in socket.links
                            ],
                        }
                        for socket in node.inputs
                    ],
                }
                for node in material.node_tree.nodes
            ],
        }
    )
result = {
    "head_axes": [],
    "materials": materials,
    "lights": [
        {
            "name": obj.name,
            "type": obj.data.type,
            "hidden": obj.hide_render,
            "position": list(obj.matrix_world.translation),
            "energy": obj.data.energy,
            "color": list(obj.data.color),
            "shadows": obj.data.use_shadow,
        }
        for obj in scene.objects
        if obj.type == "LIGHT"
    ],
    "layers": [
        {
            "name": layer.name,
            "use_sky": getattr(layer, "use_sky", None),
            "properties": [p.identifier for p in layer.bl_rna.properties],
        }
        for layer in scene.view_layers
    ],
    "collections": [
        {
            "name": col.name,
            "objects": len(col.objects),
            "actors": sorted({obj.get("performer_id", "") for obj in col.objects}),
        }
        for col in bpy.data.collections
    ],
    "color": {
        key: getattr(scene.view_settings, key)
        for key in ["view_transform", "look", "exposure", "gamma"]
    },
    "compositor": [
        {
            "name": node.name,
            "type": node.bl_idname,
            "inputs": [
                {
                    "name": s.name,
                    "value": val(s),
                    "links": [[l.from_node.name, l.from_socket.name] for l in s.links],
                }
                for s in node.inputs
            ],
        }
        for node in scene.compositing_node_group.nodes
    ],
}
file_node = scene.compositing_node_group.nodes.new("CompositorNodeOutputFile")
result["file_output_api"] = [p.identifier for p in file_node.bl_rna.properties]
result["file_output_inputs"] = [(s.name, s.bl_idname) for s in file_node.inputs]
for attribute in [
    "file_output_items",
    "file_slots",
    "format",
    "directory",
    "file_name",
    "base_path",
]:
    if hasattr(file_node, attribute):
        value = getattr(file_node, attribute)
        result["file_output_" + attribute] = {
            "type": type(value).__name__,
            "methods": [name for name in dir(value) if not name.startswith("_")][:35],
        }
scene.compositing_node_group.nodes.remove(file_node)
from mathutils import Vector

for arm in scene.objects:
    if arm.type != "ARMATURE" or not arm.get("performer_id"):
        continue
    head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
    ctl = bpy.data.objects.get("Genshin study | head axes | " + arm["performer_id"])
    axes = {}
    for name, axis in [("up", Vector((0, 0, 1))), ("forward", Vector((0, -1, 0)))]:
        expected = (
            arm.matrix_world.to_3x3()
            @ head.matrix.to_3x3()
            @ head.bone.matrix_local.to_3x3().inverted()
            @ arm.matrix_world.to_3x3().inverted()
            @ axis
        )
        axes[name] = {
            "expected": list(expected.normalized()),
            "stored": list(ctl[name]),
        }
    result["head_axes"].append({"actor": arm["performer_id"], "axes": axes})
out = Path(sys.argv[sys.argv.index("--") + 1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
)
print("QUALITY_PROBE", len(materials), len(result["lights"]), flush=True)
