"""Render bounded same-frame layer ablations without saving the production file."""

import argparse
import json
import sys
from pathlib import Path

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame", type=int, default=4290)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    assert scene.get("character_layer_revision") == "duet-character-layers-v1"
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    controls = {}
    for material in bpy.data.materials:
        if not material.get("performer_id") or not material.node_tree:
            continue
        for node in material.node_tree.nodes:
            if node.name in {
                "Character layers | enable lighting",
                "Character layers | AO strength",
                "Character layers | hair highlight strength",
            }:
                controls[material.name + "/" + node.name] = (
                    node,
                    node.outputs[0].default_value,
                )
    assert len(controls) > 30
    lights = [(o.data, o.data.use_shadow) for o in scene.objects if o.type == "LIGHT"]
    scene.frame_set(args.frame)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    cases = [
        "complete",
        "lighting-off",
        "ao-off",
        "hair-highlight-off",
        "cast-shadows-off",
    ]
    for case in cases:
        for name, (node, value) in controls.items():
            disabled = (
                (case == "lighting-off" and "enable lighting" in name)
                or (case == "ao-off" and "AO strength" in name)
                or (case == "hair-highlight-off" and "hair highlight strength" in name)
            )
            node.outputs[0].default_value = 0 if disabled else value
        for data, enabled in lights:
            data.use_shadow = False if case == "cast-shadows-off" else enabled
        scene.render.filepath = str(args.output_dir / (case + ".png"))
        bpy.ops.render.render(write_still=True)
    (args.output_dir / "controls.json").write_text(
        json.dumps(
            {
                "source": bpy.data.filepath,
                "frame": args.frame,
                "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                "cases": cases,
                "value_controls": len(controls),
                "scope": "Native same-frame ablations, full production post retained; no project saved. Lighting-off bypasses the new palette; preserved physical closures still respond to lights. Cast-off affects scene lights, not baked GI or SDF.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("CHARACTER_LAYER_CONTROLS_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
