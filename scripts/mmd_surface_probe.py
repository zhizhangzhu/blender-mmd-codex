"""Inspect actual source maps, material regions and head space for refinement."""

import argparse
import json
import sys
from pathlib import Path
import bpy

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output-dir", type=Path, required=True)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
args.output_dir.mkdir(parents=True, exist_ok=False)
report = {"images": [], "materials": []}
for i, image in enumerate(bpy.data.images):
    if image.source != "FILE":
        continue
    item = {
        "name": image.name,
        "filepath": image.filepath,
        "size": list(image.size),
        "colorspace": image.colorspace_settings.name,
    }
    if image.packed_file:
        target = args.output_dir / f"source-{i:02d}.png"
        target.write_bytes(bytes(image.packed_file.data))
        item["extracted"] = str(target)
    report["images"].append(item)
for mat in bpy.data.materials:
    if not mat.get("look_category"):
        continue
    report["materials"].append(
        {
            "name": mat.name,
            "category": mat["look_category"],
            "images": [
                (n.name, n.image.name if n.image else None)
                for n in mat.node_tree.nodes
                if n.type == "TEX_IMAGE"
            ],
        }
    )
mesh = next(
    o
    for o in bpy.context.scene.objects
    if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
)
report["regions"] = {}
for category in ["hair", "cloth", "trim"]:
    slots = {
        i
        for i, m in enumerate(mesh.data.materials)
        if m and m.get("look_category") == category
    }
    ids = {
        v
        for poly in mesh.data.polygons
        if poly.material_index in slots
        for v in poly.vertices
    }
    report["regions"][category] = {
        "vertices": len(ids),
        "bounds": [
            [
                min(mesh.data.vertices[i].co[a] for i in ids),
                max(mesh.data.vertices[i].co[a] for i in ids),
            ]
            for a in range(3)
        ],
    }
(args.output_dir / "surface-inventory.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("SURFACE_INVENTORY", json.dumps(report, ensure_ascii=False), flush=True)
