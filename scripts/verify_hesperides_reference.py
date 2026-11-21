"""Reopen the independent hall study, verify switches/packing, and re-render."""

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
    scene = bpy.context.scene
    files = [im for im in bpy.data.images if im.source == "FILE"]
    unpacked = [im.name for im in files if not im.packed_file and not im.packed_files]
    toon = []
    caps = []
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        node = mat.node_tree.nodes.get("Reference | ToonBased vs ordinary PBR")
        if node:
            toon.append({"material": mat.name, "factor": node.inputs[0].default_value})
        node = mat.node_tree.nodes.get("Reference | authored MatCap intensity")
        if node:
            caps.append(
                {"material": mat.name, "strength": node.inputs[1].default_value}
            )
    grade = scene.compositing_node_group.nodes["Reference | stage-only reference grade"]
    errors = []
    if unpacked:
        errors.append("unpacked image files")
    if len(toon) != 20 or any(r["factor"] != 1 for r in toon):
        errors.append("ToonBased switches/count")
    if len(caps) != 14 or any(r["strength"] <= 0 for r in caps):
        errors.append("MatCap switches/count")
    if grade.inputs["Fac"].default_value != 1:
        errors.append("grade switch")
    if (
        scene.render.engine != "BLENDER_EEVEE"
        or not scene.eevee.use_raytracing
        or scene.eevee.ray_tracing_method != "SCREEN"
    ):
        errors.append("engine/reflection settings")
    if [scene.render.resolution_x, scene.render.resolution_y] != [1920, 1080]:
        errors.append("resolution")
    probes = [
        {"name": o.name, "type": o.data.type}
        for o in scene.objects
        if o.type == "LIGHT_PROBE"
    ]
    if {r["type"] for r in probes} != {"PLANE", "SPHERE", "VOLUME"}:
        errors.append("probe types")
    scene.frame_set(1)
    scene.render.filepath = str(args.output_dir / "reopened.png")
    if not errors:
        bpy.ops.render.render(write_still=True)
    report = {
        "project": bpy.data.filepath,
        "blender": bpy.app.version_string,
        "file_images": len(files),
        "unpacked": unpacked,
        "toon_based": toon,
        "matcaps": caps,
        "probes": probes,
        "errors": errors,
        "passed": not errors,
        "scope": "stage settings/packing/re-render only; not animation or artistic acceptance",
    }
    (args.output_dir / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if errors:
        raise RuntimeError(errors)
    print("REFERENCE_REOPEN_VERIFIED", len(files), len(toon), len(caps), flush=True)


if __name__ == "__main__":
    main()
