"""Inspect reachable emission, lighting and color transforms on the same HDR frame."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import bpy


def active_nodes(material):
    if not material.node_tree:
        return []
    outputs = [
        n
        for n in material.node_tree.nodes
        if n.type == "OUTPUT_MATERIAL" and n.is_active_output
    ]
    reached = set()

    def visit(node):
        if node in reached:
            return
        reached.add(node)
        for socket in node.inputs:
            for link in socket.links:
                visit(link.from_node)

    for node in outputs:
        visit(node)
    return list(reached)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    scene.frame_set(4200)
    materials = []
    for material in bpy.data.materials:
        if not (material.get("performer_id") or material.get("stage_id")):
            continue
        nodes = active_nodes(material)
        materials.append(
            {
                "name": material.name,
                "actor": material.get("performer_id"),
                "stage": material.get("stage_id"),
                "active_types": dict(Counter(n.type for n in nodes)),
                "emission_nodes": [
                    {"name": n.name, "strength": n.inputs["Strength"].default_value}
                    for n in nodes
                    if n.type == "EMISSION"
                ],
            }
        )
    tree = scene.compositing_node_group
    report = {
        "source": bpy.data.filepath,
        "view": {
            "transform": scene.view_settings.view_transform,
            "look": scene.view_settings.look,
            "exposure": scene.view_settings.exposure,
            "gamma": scene.view_settings.gamma,
        },
        "materials": materials,
        "lights": [
            {
                "name": o.name,
                "type": o.data.type,
                "watts": o.data.energy,
                "color": list(o.data.color),
                "size": getattr(o.data, "size", None),
                "location": list(o.location),
            }
            for o in scene.objects
            if o.type == "LIGHT"
        ],
        "compositor": [
            {
                "name": n.name,
                "type": n.bl_idname,
                "inputs": {
                    s.name: list(s.default_value)
                    if hasattr(s.default_value, "__iter__")
                    and not isinstance(s.default_value, str)
                    else s.default_value
                    for s in n.inputs
                    if hasattr(s, "default_value") and not s.is_linked
                },
            }
            for n in tree.nodes
        ]
        if tree
        else [],
    }
    (args.output_dir / "source-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(args.output_dir / "original-agx.png")
    bpy.ops.render.render(write_still=True)
    result = bpy.data.images["Render Result"]
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "16"
    result.save_render(str(args.output_dir / "original-scene-linear.exr"), scene=scene)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    variants = [
        ("agx-plus-0.7", "AgX", "AgX - Medium High Contrast", 0.7),
        ("standard-minus-0.7", "Standard", "None", -0.7),
        ("standard-zero", "Standard", "None", 0),
    ]
    for name, transform, look, exposure in variants:
        scene.view_settings.view_transform = transform
        scene.view_settings.look = look
        scene.view_settings.exposure = exposure
        result.save_render(str(args.output_dir / (name + ".png")), scene=scene)
    print("BRIGHTNESS_PROBE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
