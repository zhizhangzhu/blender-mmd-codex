"""Inspect Aether's actual source materials and export supplied packed textures."""

import argparse
import json
import sys
from pathlib import Path

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    materials = [
        m
        for m in bpy.data.materials
        if m.get("performer_id") == "aether"
        and m.node_tree
        and m.node_tree.nodes.get("mmd_shader")
    ]
    images = {}
    result = []
    for mat in materials:
        source = mat.node_tree.nodes.get("mmd_base_tex")
        item = {
            "name": mat.name,
            "source_name": mat.get("source_mmd_material_name"),
            "category": mat.get("look_category"),
            "source_texture": source.image.name if source and source.image else None,
            "mmd_values": {},
        }
        for name in [
            "diffuse_color",
            "ambient_color",
            "specular_color",
            "shininess",
            "alpha",
            "edge_weight",
            "edge_weight_scale",
            "enabled_toon_edge",
        ]:
            if hasattr(mat.mmd_material, name):
                value = getattr(mat.mmd_material, name)
                item["mmd_values"][name] = (
                    list(value)
                    if hasattr(value, "__len__") and not isinstance(value, str)
                    else value
                )
        item["texture_nodes"] = []
        for node in mat.node_tree.nodes:
            if node.type != "TEX_IMAGE" or not node.image:
                continue
            image = node.image
            destination = args.output_dir / Path(image.name).name
            if image.packed_file and image.name not in images:
                destination.write_bytes(image.packed_file.data)
            images[image.name] = {
                "name": image.name,
                "path": image.filepath,
                "extracted": str(destination),
                "size": list(image.size),
                "colorspace": image.colorspace_settings.name,
            }
            item["texture_nodes"].append({"node": node.name, "image": image.name})
        result.append(item)
    meshes = []
    for obj in bpy.context.scene.objects:
        if (
            obj.type != "MESH"
            or obj.get("performer_id") != "aether"
            or not any(m.type == "ARMATURE" for m in obj.modifiers)
        ):
            continue
        counts = {}
        for face in obj.data.polygons:
            name = obj.data.materials[face.material_index].name
            counts[name] = counts.get(name, 0) + 1
        meshes.append(
            {
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "material_polygons": counts,
            }
        )
    report = {"materials": result, "images": list(images.values()), "meshes": meshes}
    (args.output_dir / "audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("AETHER_AUDIT", json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
