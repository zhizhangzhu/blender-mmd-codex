"""Render the saved portrait look directly to new caption caches; no QA pass."""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-Portrait-Relight-v1")
TEMP = Path("D:/codex/temp/MMD-Portrait-Relight-v1/quick-5s-v2")
PROJECT = ROOT / "production-v1/Franken_Duet_Portrait_Relight.blend"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--temp", type=Path, default=TEMP)
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--goo", action="store_true")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    project, task_temp = args.project, args.temp
    expected = json.loads(
        (project.parent / "preparation.json").read_text(encoding="utf-8")
    )
    assert (
        hashlib.sha256(project.read_bytes()).hexdigest() == expected["project_sha256"]
    )
    cache = task_temp / "cache"
    cache.mkdir(parents=True, exist_ok=False)
    (task_temp / "render-process.json").write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "parent_pid": os.getppid(),
                "project": str(project),
                "project_sha256": expected["project_sha256"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if args.goo:
        from goo_runtime import register_addons

        register_addons()
    else:
        bpy.ops.wm.read_userpref()
        bpy.ops.preferences.addon_enable(module="bl_ext.blender_org.mmd_tools")
    bpy.ops.wm.open_mainfile(filepath=str(project), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    if str(scene.get("production_runtime", "")).startswith("Goo") and not args.goo:
        raise RuntimeError("Use the Goo runtime and --goo for this migrated project")
    assert (
        scene.rigidbody_world is None
        and scene.render.fps == 60
        and scene.render.fps_base == 1
    )
    mute_file_outputs()
    for label in ("beauty", "actor"):
        node = scene.compositing_node_group.nodes["Caption cache | " + label]
        (cache / label).mkdir()
        node.directory = str(cache / label)
        node.file_name = "frame_####"
        node.mute = False
        assert node.format.file_format == "PNG" and node.format.color_depth == "16"
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = args.samples
    scene.render.use_motion_blur = False
    scene.camera.data.dof.use_dof = True
    scene.render.use_sequencer = False
    started = time.perf_counter()
    for frame in range(4140, 4440, 2):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=False)
        if frame == 4140:
            assert (cache / "beauty/frame_4140beauty.png").is_file()
            assert (cache / "actor/frame_4140actor.png").is_file()
        (task_temp / "progress.json").write_text(
            json.dumps(
                {
                    "last_frame": frame,
                    "rendered": (frame - 4140) // 2 + 1,
                    "total": 150,
                    "elapsed_seconds": time.perf_counter() - started,
                }
            ),
            encoding="utf-8",
        )
        print("QUICK_PREVIEW_RENDER", (frame - 4140) // 2 + 1, "/150", flush=True)
    (task_temp / "render-complete.json").write_text(
        json.dumps(
            {
                "project": str(project),
                "project_sha256": expected["project_sha256"],
                "source_frames": [4140, 4438],
                "source_frame_step": 2,
                "output_frames": 150,
                "fps": 30,
                "resolution": [1920, 1080],
                "samples": args.samples,
                "dof": True,
                "motion_blur": False,
                "runtime": bpy.app.binary_path,
                "runtime_build": bpy.app.build_hash.decode(),
                "elapsed_seconds": time.perf_counter() - started,
                "post_render_validation": "skipped at user request",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
