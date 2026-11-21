"""Measure full-frame EEVEE variants without changing animation or source file."""

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
    scene.eevee.shadow_pool_size = "1024"
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 100
    scene.render.use_sequencer = False
    lights = []
    for obj in scene.objects:
        if obj.type == "LIGHT":
            lights.append(
                {
                    "name": obj.name,
                    "power": obj.data.energy,
                    "shadow": obj.data.use_shadow,
                    "resolution_limit": obj.data.shadow_maximum_resolution,
                }
            )
    records = []
    for variant in [
        "fixed-pool",
        "coarser-wide-shadows",
        "24-samples",
        "no-compositor",
    ]:
        if variant == "coarser-wide-shadows":
            for obj in scene.objects:
                if (
                    obj.type == "LIGHT"
                    and obj.data.type == "AREA"
                    and obj.data.size >= 10
                ):
                    obj.data.shadow_maximum_resolution = max(
                        obj.data.shadow_maximum_resolution, 0.02
                    )
        if variant == "24-samples":
            scene.eevee.taa_render_samples = 24
        if variant == "no-compositor":
            scene.render.use_compositing = False
        timings = []
        for frame in range(601, 605):
            scene.frame_set(frame)
            scene.render.filepath = str(args.output_dir / f"{variant}-{frame}.png")
            started = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            timings.append(time.perf_counter() - started)
        records.append({"variant": variant, "timings": timings})
        (args.output_dir / "benchmark.json").write_text(
            json.dumps({"lights": lights, "variants": records}, indent=2),
            encoding="utf-8",
        )
        print("ENGINE_BENCHMARK", json.dumps(records[-1]), flush=True)


if __name__ == "__main__":
    main()
