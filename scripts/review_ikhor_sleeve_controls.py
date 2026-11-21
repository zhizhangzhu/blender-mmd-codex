"""Render unsaved, unblurred wrist geometry controls with the production shader."""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import aim
from prepare_bold_wedding import mute_outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame", type=int, default=4290)
    parser.add_argument(
        "--variant", nargs=2, action="append", default=[], metavar=("BLEND", "ACTION")
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    assert scene.get("ikhor_wedding_revision") == "franken-ikhor-bold-wedding-v1"
    mute_outputs()
    arm = next(
        o
        for o in scene.objects
        if o.type == "ARMATURE" and o.get("performer_id") == "ikhor"
    )
    original = arm.animation_data.action
    original_slot = arm.animation_data.action_slot
    camera = scene.camera.copy()
    camera.data = scene.camera.data.copy()
    camera.parent = None
    camera.constraints.clear()
    camera.animation_data_clear()
    camera.data.animation_data_clear()
    scene.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.57
    camera.data.dof.use_dof = False
    source_camera = scene.camera
    scene.frame_set(args.frame)
    view_source = source_camera.matrix_world.translation.copy()
    scene.camera = camera
    for obj in scene.objects:
        if obj.type in {"MESH", "LIGHT_PROBE"} and obj.get("performer_id") != "ikhor":
            obj.hide_render = True
        if obj.type == "LIGHT" and not obj.name.startswith("Reference duet | ikhor |"):
            obj.hide_render = True
    scene.render.use_compositing = False
    scene.render.use_motion_blur = False
    scene.render.resolution_x = scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    records = []
    cases = [("production-physics", original, original_slot)]
    for path, name in args.variant:
        with bpy.data.libraries.load(path, link=False) as (available, loaded):
            assert name in available.actions, name
            loaded.actions = [name]
        action = loaded.actions[0]
        slot = next(s for s in action.slots if s.target_id_type == "OBJECT")
        cases.append((name.split("|")[-1].strip(), action, slot))
    for label, action, slot in cases:
        arm.animation_data.action = action
        arm.animation_data.action_slot = slot
        scene.frame_set(args.frame)
        bpy.context.view_layer.update()
        for side in ["右", "左"]:
            bone = next(b for b in arm.pose.bones if b.mmd_bone.name_j == side + "手首")
            target = arm.matrix_world @ bone.matrix.translation + Vector((0, 0, 0.025))
            camera.location = target + (view_source - target).normalized() * 3
            aim(camera, target)
            path = (
                args.output_dir
                / f"{label}-{'right' if side == '右' else 'left'}-{args.frame}.png"
            )
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            records.append(
                {
                    "label": label,
                    "action": action.name,
                    "side": side,
                    "frame": args.frame,
                    "image": str(path),
                }
            )
            print("SLEEVE_CONTROL_RENDERED", path, flush=True)
    (args.output_dir / "review-records.json").write_text(
        json.dumps(
            {
                "source": bpy.data.filepath,
                "records": records,
                "scope": "Unsaved geometry diagnosis with original production materials; no motion blur, stage or post. Not a repaired delivery.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
