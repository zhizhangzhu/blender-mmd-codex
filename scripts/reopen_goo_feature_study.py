"""Reopen one isolated study blend and compare its linear render; no production input."""

import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path("D:/codex/output/Goo-MME-Feature-Study-2026-11-16")
TEMP = Path("D:/codex/temp/Goo-MME-Feature-Study-2026-11-16")
source = ROOT / "screen_depth/Screenspace_Study.blend"
assert Path(bpy.data.filepath).resolve() == source.resolve()
scene = bpy.context.scene
assert not scene.render.use_compositing
scene.render.image_settings.file_format = "OPEN_EXR"
scene.render.image_settings.color_depth = "32"
scene.render.filepath = str(TEMP / "screenspace-reopen.exr")
bpy.ops.render.render(write_still=True)


def pixels(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    values = np.array(image.pixels[:], dtype=np.float32)
    bpy.data.images.remove(image)
    return values


reference = json.loads((ROOT / "screen_depth/measurements.json").read_text())
reference_path = reference["results"]["screen_color_enabled"]["linear_exr"]
delta = np.abs(pixels(scene.render.filepath) - pixels(reference_path))
report = {
    "source": str(source),
    "build": bpy.app.build_hash.decode(),
    "max_abs_linear_delta": float(delta.max()),
    "mean_abs_linear_delta": float(delta.mean()),
    "passed": bool(delta.max() < 0.001),
    "production_loaded": False,
    "saved_study_modified": False,
    "scope": "One factory-only Screenspace study reopened, rendered and compared; other study blends not reopened",
}
with (ROOT / "reopen-verification.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(report, indent=2))
assert report["passed"]
