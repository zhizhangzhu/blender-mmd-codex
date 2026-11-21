"""Render the saved portrait candidate in a fresh process without rebuilding it."""

import hashlib
import json
from pathlib import Path

import bpy

ROOT = Path("D:/codex/output/MMD-Portrait-Relight-v1")
PRODUCTION = ROOT / "production-v1"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    preparation = json.loads((PRODUCTION / "preparation.json").read_text(encoding="utf-8"))
    project = Path(preparation["project"])
    assert sha(project) == preparation["project_sha256"]
    picture = ROOT / "verification/reopen-1080.png"
    assert not picture.exists()
    bpy.ops.wm.read_userpref()
    bpy.ops.preferences.addon_enable(module="bl_ext.blender_org.mmd_tools")
    bpy.ops.wm.open_mainfile(filepath=str(project), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    assert abs(scene.camera.data.lens - preparation["camera_lens"]) < 1e-5
    for group in bpy.data.node_groups:
        for node in group.nodes:
            if node.type == "OUTPUT_FILE":
                assert node.mute, "Inherited File Output was not muted"
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.eevee.taa_render_samples = 64
    scene.render.filepath = str(picture)
    bpy.ops.render.render(write_still=True)
    report = {"project": str(project), "project_sha256": sha(project),
              "project_unchanged": sha(project) == preparation["project_sha256"],
              "picture": str(picture), "picture_sha256": sha(picture),
              "frame": 4290, "resolution": [1920, 1080], "samples": 64,
              "lens_mm": scene.camera.data.lens, "dof": scene.camera.data.dof.use_dof,
              "rebuilt_shader_or_scene": False}
    assert report["project_unchanged"]
    (picture.parent / "reopen-render.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("SAVED_PORTRAIT_RENDER_COMPLETE", picture, flush=True)


if __name__ == "__main__":
    main()
