"""Independently reopen the basic experiment and compare its linear pixels."""

import json
from pathlib import Path

import bpy
import numpy as np

OUT = Path("D:/codex/output/Goo-Basics-Study-2026-11-17/light-group-controls")
RAW = Path("D:/codex/temp/Goo-Official-Basics-2026-11-17/linear")
bpy.ops.wm.open_mainfile(
    filepath=str(OUT / "Basic_Light_Groups.blend"), use_scripts=False, load_ui=False
)
s = bpy.context.scene
s.render.image_settings.file_format = "OPEN_EXR"
s.render.image_settings.color_depth = "32"
s.render.filepath = str(RAW / "reopened-C.exr")
bpy.ops.render.render(write_still=True)


def pixels(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    array = np.array(im.pixels[:], dtype=np.float32)
    bpy.data.images.remove(im)
    return array


delta = np.abs(
    pixels(RAW / "reopened-C.exr") - pixels(RAW / "C-fill-excluded-from-key-group.exr")
)
result = {
    "version": bpy.app.version_string,
    "build_hash": bpy.app.build_hash.decode(),
    "max_abs_linear_rgba_difference": float(delta.max()),
    "mean_abs_difference": float(delta.mean()),
    "passed": bool(delta.max() < 1e-6),
    "production_loaded": False,
}
assert result["passed"], result
(OUT / "reopen-verification.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8"
)
print("BASIC_REOPEN_COMPLETE", json.dumps(result), flush=True)
