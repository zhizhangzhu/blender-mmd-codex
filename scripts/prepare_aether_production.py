"""Save the revised Aether scene as a fresh, explicitly recorded production file."""

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
    source = bpy.data.filepath
    assert scene.rigidbody_world is None
    assert scene.camera.name != "Aether | QA portrait camera"
    scene.frame_start, scene.frame_end = 1, 11899
    scene.frame_set(1)
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.fps, scene.render.fps_base = 60, 1
    scene.eevee.taa_render_samples = 32
    scene.eevee.shadow_pool_size = "1024"
    scene.render.use_border = False
    scene.render.use_crop_to_border = False
    scene.render.use_sequencer = False
    scene.render.use_compositing = True
    adjusted = []
    for obj in scene.objects:
        if obj.type == "LIGHT" and obj.data.type == "AREA" and obj.data.size >= 10:
            # Broad 10-15 m window/bounce lights need no submillimetre shadow texels.
            obj.data.shadow_maximum_resolution = max(
                obj.data.shadow_maximum_resolution, 0.02
            )
            adjusted.append(obj.name)
    for obj in list(scene.objects):
        if obj.name.startswith("Aether | QA portrait camera"):
            bpy.data.objects.remove(obj, do_unlink=True)
    scene["aether_look_revision"] = "aether-hall-surface-v1"
    bpy.ops.file.pack_all()
    destination = args.output_dir / "Franken_Duet_Aether_Revised.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    report = {
        "source": source,
        "project": str(destination),
        "frames": [1, 11899],
        "resolution": [1920, 1080],
        "fps": 60,
        "samples": 32,
        "shadow_pool_mb": 1024,
        "wide_light_shadow_resolution_limit_m": 0.02,
        "adjusted_wide_lights": adjusted,
        "camera": scene.camera.name,
        "camera_motion_or_lens_changed": False,
        "physics_changed": False,
        "status": "Revised project saved; full render and decode acceptance pending",
    }
    (args.output_dir / "production-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("AETHER_PRODUCTION_PREPARED", flush=True)


if __name__ == "__main__":
    main()
