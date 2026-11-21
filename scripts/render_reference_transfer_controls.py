"""Render same-frame ablations of the new reference transfer without saving."""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transfer_material_response import set_material_response_bypass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame", type=int, default=4290)
    parser.add_argument("--percentage", type=int, default=100)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    assert scene.get("reference_transfer_revision") == "duet-guanhai-transfer-v1"
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type == "OUTPUT_FILE":
                    node.mute = True
    switches = [
        (n, n.outputs[0].default_value)
        for m in bpy.data.materials
        if m.node_tree
        for n in m.node_tree.nodes
        if n.type == "VALUE" and n.name.startswith("Reference transfer | enable")
    ]
    lights = [
        (o, o.hide_render, o.data.use_shadow)
        for o in scene.objects
        if o.type == "LIGHT"
    ]
    grade = scene.compositing_node_group.nodes[
        "Reference transfer | foreground hierarchy with actor protection"
    ].inputs[0]
    grade_source = grade.links[0].from_socket
    scene.frame_set(args.frame)
    scene.render.resolution_percentage = args.percentage
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    cases = [
        "complete",
        "design-off",
        "rim-off",
        "reflection-off",
        "cast-shadows-off",
        "stage-grade-off",
    ]
    for case in cases:
        for n, value in switches:
            n.outputs[0].default_value = (
                0
                if (case == "design-off" and n.name.endswith("enable designed shading"))
                or (
                    case == "rim-off"
                    and n.name.endswith("enable artistic emissive rim")
                )
                else value
            )
        for obj, hidden, shadow in lights:
            obj.hide_render = (
                True
                if case == "reflection-off" and obj.name.endswith(" | reflection")
                else hidden
            )
            obj.data.use_shadow = False if case == "cast-shadows-off" else shadow
        if case == "stage-grade-off":
            for link in list(grade.links):
                scene.compositing_node_group.links.remove(link)
            grade.default_value = 0
        else:
            scene.compositing_node_group.links.new(grade_source, grade)
        scene.render.filepath = str(args.output_dir / (case + ".png"))
        bpy.ops.render.render(write_still=True)
        print("TRANSFER_CONTROL_READY", case, flush=True)
    # Separate material contribution from the other new controls.
    for n, value in switches:
        n.outputs[0].default_value = value
    for obj, hidden, shadow in lights:
        obj.hide_render, obj.data.use_shadow = hidden, shadow
    scene.compositing_node_group.links.new(grade_source, grade)
    set_material_response_bypass(scene, True)
    scene.render.filepath = str(args.output_dir / "material-controls-off.png")
    bpy.ops.render.render(write_still=True)
    cases.append("material-controls-off")
    (args.output_dir / "controls.json").write_text(
        json.dumps(
            {
                "source": bpy.data.filepath,
                "frame": args.frame,
                "resolution": [
                    scene.render.resolution_x * args.percentage // 100,
                    scene.render.resolution_y * args.percentage // 100,
                ],
                "cases": cases,
                "project_saved": False,
                "limits": "Ablations isolate the named new controls, not pure physical render passes; cast-off retains form/SDF/baked GI; stage grade affects background-only spatial region.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("TRANSFER_CONTROLS_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
