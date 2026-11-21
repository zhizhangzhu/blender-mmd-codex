"""Measure full-resolution animation cost before the full-song render."""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 100
    results = []
    for name in ["original", "balanced"]:
        if name == "balanced":
            scene.eevee.taa_render_samples = 32
            scene.eevee.use_raytracing = False
            scene.eevee.shadow_ray_count = 1
            for mat in bpy.data.materials:
                if not mat.node_tree:
                    continue
                for n in mat.node_tree.nodes:
                    if n.type == "AMBIENT_OCCLUSION":
                        for link in list(n.outputs["AO"].links):
                            link.to_node.inputs[0].default_value = 0
            for obj in scene.objects:
                if obj.name.startswith("Hall | subtle winter air"):
                    obj.hide_render = True
                if obj.type == "LIGHT" and obj.data.type == "POINT":
                    obj.data.use_shadow = False
        scene.frame_start, scene.frame_end = 601, 608
        dest = args.output_dir / name
        dest.mkdir()
        scene.render.filepath = str(dest / "frame-")
        started = time.time()
        bpy.ops.render.render(animation=True)
        results.append({"variant": name, "seconds": time.time() - started, "frames": 8})
        print("BENCHMARK", json.dumps(results[-1]), flush=True)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(args.output_dir / "balanced-candidate.blend")
    )
    (args.output_dir / "benchmark.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
