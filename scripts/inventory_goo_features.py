"""Inventory real shader RNA in an empty factory process, without loading production."""

import argparse
import json
import sys
from pathlib import Path

import bpy

p = argparse.ArgumentParser()
p.add_argument("--output", required=True)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
material = bpy.data.materials.new("Feature inventory only")
material.use_nodes = True
nodes = {}
for name in sorted(n for n in dir(bpy.types) if n.startswith("ShaderNode")):
    cls = getattr(bpy.types, name)
    if getattr(cls, "bl_rna", None) and name not in (
        "ShaderNode",
        "ShaderNodeCustomGroup",
    ):
        try:
            n = material.node_tree.nodes.new(name)
        except RuntimeError:
            continue
        nodes[name] = {
            "label": n.bl_label,
            "inputs": [{"name": x.name, "type": x.bl_idname} for x in n.inputs],
            "outputs": [{"name": x.name, "type": x.bl_idname} for x in n.outputs],
            "properties": {
                x.identifier: {
                    "type": x.type,
                    "enum": [a.identifier for a in x.enum_items]
                    if x.type == "ENUM"
                    else None,
                }
                for x in n.bl_rna.properties
                if not x.is_readonly and x.identifier not in ("rna_type",)
            },
        }
        material.node_tree.nodes.remove(n)
out = {
    "binary": bpy.app.binary_path,
    "version": bpy.app.version_string,
    "build_hash": bpy.app.build_hash.decode(),
    "node_types": nodes,
    "eevee": [x.identifier for x in bpy.context.scene.eevee.bl_rna.properties],
    "material": [x.identifier for x in material.bl_rna.properties],
    "light": [
        x.identifier
        for x in bpy.data.lights.new("Inventory only", "AREA").bl_rna.properties
    ],
}
path = Path(args.output)
path.parent.mkdir(parents=True, exist_ok=True)
with path.open("x", encoding="utf-8") as stream:
    json.dump(out, stream, ensure_ascii=False, indent=2)
print("SHADER_RNA_INVENTORY", bpy.app.version_string, len(nodes), flush=True)
