"""Inspect a supplied scene without executing embedded scripts or saving it.

Run with Blender --background --disable-autoexec INPUT.blend --python ...
and write the report to a fresh output path.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.output.exists():
        raise FileExistsError(args.output)
    objects = []
    for obj in bpy.context.scene.objects:
        corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        item = {
            "name": obj.name,
            "type": obj.type,
            "location": list(obj.location),
            "scale": list(obj.scale),
            "dimensions": list(obj.dimensions),
            "bounds": [
                [min(v[i] for v in corners) for i in range(3)],
                [max(v[i] for v in corners) for i in range(3)],
            ],
        }
        if obj.type == "MESH":
            item.update(
                {
                    "vertices": len(obj.data.vertices),
                    "polygons": len(obj.data.polygons),
                    "materials": [m.name if m else None for m in obj.data.materials],
                    "material_polygon_counts": dict(
                        Counter(p.material_index for p in obj.data.polygons)
                    ),
                    "uv_layers": [uv.name for uv in obj.data.uv_layers],
                }
            )
        objects.append(item)
    materials = []
    for mat in bpy.data.materials:
        nodes = mat.node_tree.nodes if mat.use_nodes else []
        materials.append(
            {
                "name": mat.name,
                "diffuse": list(mat.diffuse_color),
                "nodes": [
                    {
                        "name": n.name,
                        "type": n.bl_idname,
                        **(
                            {"image": n.image.name if n.image else None}
                            if n.type == "TEX_IMAGE"
                            else {}
                        ),
                    }
                    for n in nodes
                ],
                "links": [
                    (
                        l.from_node.name,
                        l.from_socket.name,
                        l.to_node.name,
                        l.to_socket.name,
                    )
                    for l in mat.node_tree.links
                ]
                if mat.use_nodes
                else [],
            }
        )
    images = [
        {
            "name": im.name,
            "path": im.filepath,
            "size": list(im.size),
            "colorspace": im.colorspace_settings.name,
            "packed": bool(im.packed_file),
        }
        for im in bpy.data.images
    ]
    report = {
        "file": bpy.data.filepath,
        "blender": bpy.app.version_string,
        "objects": objects,
        "materials": materials,
        "images": images,
        "unit_scale": bpy.context.scene.unit_settings.scale_length,
        "engine": bpy.context.scene.render.engine,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "SCENE_AUDIT",
        json.dumps(
            {
                "objects": len(objects),
                "materials": len(materials),
                "images": len(images),
                "vertices": sum(o.get("vertices", 0) for o in objects),
                "polygons": sum(o.get("polygons", 0) for o in objects),
                "report": str(args.output),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
