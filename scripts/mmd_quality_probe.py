"""Read local NPR/AO/normal/plugin compatibility before changing a scene."""

import argparse
import importlib
import json
import sys
from pathlib import Path

import bpy

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output", type=Path, required=True)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
s = bpy.context.scene
report = {"version": bpy.app.version_string, "engine": s.render.engine}
report["eevee"] = {
    key: str(getattr(s.eevee, key))
    for key in dir(s.eevee)
    if any(term in key for term in ["raytrac", "fast_gi", "shadow", "volumetric"])
}
mesh = next(
    o
    for o in s.objects
    if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
)
face_indices = {
    i for i, mat in enumerate(mesh.data.materials) if mat and mat.name == "颜"
}
face_verts = {
    v
    for poly in mesh.data.polygons
    if poly.material_index in face_indices
    for v in poly.vertices
}
report["mesh"] = {
    "name": mesh.name,
    "vertices": len(mesh.data.vertices),
    "has_custom_normals": mesh.data.has_custom_normals,
    "custom_set_api": hasattr(mesh.data, "normals_split_custom_set"),
    "face_vertices": len(face_verts),
    "face_bounds": [
        [
            min(mesh.data.vertices[i].co[a] for i in face_verts),
            max(mesh.data.vertices[i].co[a] for i in face_verts),
        ]
        for a in range(3)
    ],
}
mat = bpy.data.materials.new("Quality API scratch")
mat.use_nodes = True
report["nodes"] = {}
for kind in [
    "ShaderNodeAmbientOcclusion",
    "ShaderNodeShaderToRGB",
    "ShaderNodeBsdfDiffuse",
    "ShaderNodeTangent",
    "ShaderNodeVolumeScatter",
]:
    node = mat.node_tree.nodes.new(kind)
    report["nodes"][kind] = {
        "inputs": [
            (i.name, str(i.default_value) if hasattr(i, "default_value") else "")
            for i in node.inputs
        ],
        "outputs": [o.name for o in node.outputs],
    }
module = importlib.import_module(
    "bl_ext.blender_org.Paperzhu_animehelper_extension.materials"
)
face = bpy.data.materials["颜"].copy()
report["paper_highlight"] = {
    "mmd_copy_accepted": module.apply_highlight_skin(face, 0.15, 0.3),
    "principled_scratch_accepted": module.apply_highlight_skin(mat, 0.15, 0.3),
}
bpy.data.materials.remove(face)
bpy.data.materials.remove(mat)
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("x", encoding="utf-8") as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print("QUALITY_PROBE_OK", json.dumps(report, ensure_ascii=False), flush=True)
