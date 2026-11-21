"""Compare a bounded skin-shadow calibration and save only a new review copy."""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_bold_wedding import mute_outputs
from verify_duet_integration import snapshot

SOURCE_SHA = "e0bd386d881d8fc3ddc5160ab26f728985f1426ccd0ee1385b26199d7a320ee6"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--baseline-image", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    source = Path(bpy.data.filepath)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    assert scene.get("ikhor_wedding_revision") == "franken-ikhor-bold-wedding-v1"
    mute_outputs()
    poses = {}
    for frame in (4140, 4250, 4290, 4439):
        scene.frame_set(frame)
        poses[frame] = snapshot(scene)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"

    def render(frame, name):
        scene.frame_set(frame)
        scene.render.filepath = str(args.output_dir / name)
        bpy.ops.render.render(write_still=True)
        print("IKHOR_SKIN_STILL", name, flush=True)

    if args.baseline_image:
        assert args.baseline_image.is_file()
        shutil.copyfile(args.baseline_image, args.output_dir / "native-before-4290.png")
    else:
        render(4290, "native-before-4290.png")
    spec = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    changes = []
    for material in bpy.data.materials:
        if (
            material.get("performer_id") != "ikhor"
            or material.get("ikhor_material_role") != "skin"
        ):
            continue
        ramp = material.node_tree.nodes["Ikhor character | single material palette"]
        old = list(ramp.color_ramp.elements[0].color)
        ramp.color_ramp.elements[0].color = spec["palettes"]["skin"][0]
        changes.append(
            {
                "material": material.name,
                "role": "skin",
                "old_shadow": old,
                "new_shadow": list(ramp.color_ramp.elements[0].color),
            }
        )
    assert len(changes) == 2
    for frame in (4290, 4439, 4250):
        render(frame, f"native-{frame}.png")
    for frame, expected in poses.items():
        scene.frame_set(frame)
        assert snapshot(scene) == expected
    scene.frame_set(4140)
    scene["ikhor_skin_calibration"] = "two-source-atlas-skin-shadow-colors-v1"
    target = args.output_dir / "Franken_Aksiniya_Ikhor_Bold_Wedding.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    (args.output_dir / "skin-calibration.json").write_text(
        json.dumps(
            {
                "source": str(source),
                "source_sha256": SOURCE_SHA,
                "project": str(target),
                "changes": changes,
                "changed_only_two_skin_palette_shadow_colors": True,
                "camera_dof_unchanged": True,
                "all_file_outputs_muted": True,
                "reason": "Reduce the extra pink/brown shadow tint on Hair-atlas hands/neck relative to the separately authored FaceDiffuse; preserve the real shadow/form response.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("IKHOR_SKIN_READY", target, flush=True)


if __name__ == "__main__":
    main()
