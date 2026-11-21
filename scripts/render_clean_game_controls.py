"""Unblurred, same-pose material controls; never save the production scene."""

import argparse
import importlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_bold_wedding import mute_outputs

MODULES = {
    "ikhor": ("clean_ikhor_materials", "ikhor-clean-game-v1.json"),
    "aksiniya": ("clean_aksiniya_materials", "aksiniya-clean-game-v1.json"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", choices=MODULES, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame", type=int, default=4290)
    parser.add_argument("--quick", action="store_true", help="Repeat only palette ablation after a previously checked four-module run")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    mute_outputs()
    scene.frame_set(args.frame)
    scene.render.use_motion_blur = False
    scene.camera.data.dof.use_dof = False
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 48
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    records = []

    def render(label):
        path = args.output_dir / (label + ".png")
        scene.render.filepath = str(path)
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        records.append({"label": label, "frame": args.frame, "path": str(path)})
        print("CLEAN_GAME_CONTROL", label, flush=True)

    render("baseline")
    name, profile_name = MODULES[args.actor]
    module = importlib.import_module(name)
    profile_path = Path(__file__).resolve().parents[1] / "presets/quality" / profile_name
    profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    report = module.apply(scene, profile)
    render("all-on")
    names = ("palette", "response_ramp", "highlight_metal", "rim")
    for key in names:
        module.set_module_enabled(scene, key, 0)
    render("all-off")
    for key in names:
        module.set_module_enabled(scene, key, 1)
    for key in (("palette",) if args.quick else names):
        module.set_module_enabled(scene, key, 0)
        render("off-" + key)
        module.set_module_enabled(scene, key, 1)
    (args.output_dir / "control-records.json").write_text(
        json.dumps({"source": bpy.data.filepath, "actor": args.actor, "profile": str(profile_path),
                    "implementation": report, "records": records,
                    "source_saved": False, "scope": "Static material controls only. Same camera direction/lights/stage; DOF and motion blur disabled for inspection."},
                   ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
