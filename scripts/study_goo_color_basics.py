"""Save fixed linear patches through existing Goo display transforms, without rendering."""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

assert bpy.app.build_hash.decode() == "0051aee03764"
ROOT = Path("D:/codex/output/Goo-Blender-Official-Study-2026-11-18/color-controls")
ROOT.mkdir(parents=True, exist_ok=False)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.display_settings.display_device = "sRGB"
scene.view_settings.gamma = 1
scene.view_settings.use_curve_mapping = False
if hasattr(scene.view_settings, "use_white_balance"):
    scene.view_settings.use_white_balance = False
colors = [
    ("grey18", (0.18, 0.18, 0.18)),
    ("grey50", (0.5, 0.5, 0.5)),
    ("white1", (1, 1, 1)),
    ("white2", (2, 2, 2)),
    ("white4", (4, 4, 4)),
    ("warm", (0.8, 0.38, 0.27)),
    ("blue", (0.12, 0.35, 0.9)),
    ("blueHDR", (0.48, 1.4, 3.6)),
]
pixels = np.ones((80, len(colors) * 80, 4), dtype=np.float32)
for i, (_, rgb) in enumerate(colors):
    pixels[:, i * 80 : (i + 1) * 80, :3] = rgb
image = bpy.data.images.new(
    "Fixed scene-linear patches", width=640, height=80, float_buffer=True
)
image.colorspace_settings.name = "Linear Rec.709"
image.pixels.foreach_set(pixels.ravel())
image.update()
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "16"
cases = []
before = np.array(image.pixels[:], dtype=np.float32)
for label, transform, exposure in (
    ("Standard-0", "Standard", 0),
    ("Standard-minus1", "Standard", -1),
    ("AgX-0", "AgX", 0),
    ("AgX-minus1", "AgX", -1),
    ("Neutral-0", "Khronos PBR Neutral", 0),
):
    scene.view_settings.view_transform = transform
    scene.view_settings.look = "None"
    scene.view_settings.exposure = exposure
    image.save_render(str(ROOT / (label + ".png")), scene=scene)
    after = np.array(image.pixels[:], dtype=np.float32)
    difference = float(np.abs(after - before).max())
    assert difference == 0
    cases.append(
        {
            "id": label,
            "view_transform": transform,
            "exposure_stops": exposure,
            "look": scene.view_settings.look,
            "source_linear_max_difference": difference,
        }
    )

(ROOT / "measurements.json").write_text(
    json.dumps(
        {
            "build_hash": bpy.app.build_hash.decode(),
            "version": bpy.app.version_string,
            "display": "sRGB",
            "input_color_space": image.colorspace_settings.name,
            "patches": [{"id": name, "linear_rgb": list(rgb)} for name, rgb in colors],
            "cases": cases,
            "method": "One generated float image; Image.save_render to 16-bit PNG, no scene render, no compositor; 80px square patches",
            "production_loaded": False,
            "video_created": False,
            "limits": "Display-output control only; no character, light response, material calibration or artistic quality comparison",
        },
        indent=2,
    ),
    encoding="utf-8",
)
print("GOO_COLOR_BASIC_COMPLETE", flush=True)
sys.stdout.flush()
