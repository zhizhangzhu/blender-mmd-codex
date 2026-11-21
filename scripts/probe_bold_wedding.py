"""Read-only inventory for the bounded bold-wedding lighting revision."""

import argparse
import json
import sys
from pathlib import Path

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    scene = bpy.context.scene
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    report = {
        "source": bpy.data.filepath,
        "scene": scene.name,
        "lights": [],
        "special_objects": [],
        "compositor": [],
        "actors": {},
    }
    for obj in scene.objects:
        if obj.type == "LIGHT":
            receiver = obj.light_linking.receiver_collection
            report["lights"].append(
                {
                    "name": obj.name,
                    "type": obj.data.type,
                    "location": list(obj.matrix_world.translation),
                    "rotation": list(obj.rotation_euler),
                    "energy": obj.data.energy,
                    "color": list(obj.data.color),
                    "diffuse": obj.data.diffuse_factor,
                    "specular": obj.data.specular_factor,
                    "volume": obj.data.volume_factor,
                    "hidden": obj.hide_render,
                    "receivers": receiver.name if receiver else None,
                }
            )
        if obj.type == "LIGHT_PROBE" or any(
            word in obj.name for word in ["scattering", "snow", "Snow", "head origin"]
        ):
            report["special_objects"].append(
                {
                    "name": obj.name,
                    "type": obj.type,
                    "location": list(obj.matrix_world.translation),
                    "dimensions": list(obj.dimensions),
                    "hidden": obj.hide_render,
                }
            )
    for n in scene.compositing_node_group.nodes:
        report["compositor"].append(
            {
                "name": n.name,
                "type": n.type,
                "inputs": [
                    {
                        "name": i.name,
                        "source": i.links[0].from_node.name if i.is_linked else None,
                        "value": list(i.default_value)
                        if hasattr(i, "default_value")
                        and hasattr(i.default_value, "__len__")
                        else i.default_value
                        if hasattr(i, "default_value")
                        else None,
                    }
                    for i in n.inputs
                    if i.name in ["Strength", "Threshold", "Size", "Image", "beauty"]
                ],
                "outputs": [o.name for o in n.outputs],
            }
        )
    for frame in [4140, 4250, 4290, 4439]:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        report["actors"][frame] = {
            actor: list(
                scene.objects[
                    f"Quality | {actor} | head origin"
                ].matrix_world.translation
            )
            for actor in ["aksiniya", "aether"]
        }
    report["stage_materials"] = [
        {
            "name": m.name,
            "surface_nodes": [
                n.name
                for n in m.node_tree.nodes
                if n.type in ["BSDF_PRINCIPLED", "EMISSION"]
            ],
        }
        for m in bpy.data.materials
        if m.get("stage_id") and m.node_tree
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("BOLD_WEDDING_PROBE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
