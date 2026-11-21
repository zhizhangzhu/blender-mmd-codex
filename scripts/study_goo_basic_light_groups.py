"""Test the basic one-key-per-group rule in isolated spheres, not production."""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from study_goo_feature_mechanisms import mat, scene, sun

OUT = Path("D:/codex/output/Goo-Basics-Study-2026-11-17/light-group-controls")
RAW = Path("D:/codex/temp/Goo-Official-Basics-2026-11-17/linear")
OUT.mkdir(parents=True, exist_ok=False)
RAW.mkdir(exist_ok=True)
measurements = {}
raw_pixels = {}
for label, fill_on, include_fill in (
    ("A-single-key", False, False),
    ("B-two-opposite-lights", True, True),
    ("C-fill-excluded-from-key-group", True, False),
):
    s = scene(640, 360)
    s.camera.location = (0, -7, 2.4)
    s.camera.rotation_euler = (
        (Vector((0, 0, 0)) - s.camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    s.camera.data.ortho_scale = 4.7
    key = sun("Key", energy=1)
    key.data.light_groups.use_default = False
    key.data.light_groups.groups.add().name = "Key"
    fill = sun("Fill", energy=1)
    fill.rotation_euler = (math.pi, 0, 0)
    fill.hide_render = not fill_on
    fill.data.light_groups.use_default = False
    fill.data.light_groups.groups.add().name = "Fill"
    for x, toon in ((-1.05, False), (1.05, True)):
        m, emission = mat("Raw half lambert" if not toon else "Three-band palette")
        info = m.node_tree.nodes.new("ShaderNodeShaderInfo")
        info.use_own_light_groups = True
        info.light_groups.use_default = False
        info.light_groups.groups.add().name = "Key"
        if include_fill:
            info.light_groups.groups.add().name = "Fill"
        signal = info.outputs["Half-lambert factor"]
        if toon:
            ramp = m.node_tree.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.interpolation = "CONSTANT"
            ramp.color_ramp.elements[0].position = 0.35
            ramp.color_ramp.elements[0].color = (0.035, 0.05, 0.075, 1)
            ramp.color_ramp.elements[1].position = 0.65
            ramp.color_ramp.elements[1].color = (0.75, 0.65, 0.50, 1)
            ramp.color_ramp.elements.new(0.50).color = (0.22, 0.28, 0.38, 1)
            m.node_tree.links.new(signal, ramp.inputs[0])
            signal = ramp.outputs[0]
        m.node_tree.links.new(signal, emission.inputs["Color"])
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=64, ring_count=32, radius=0.85, location=(x, 0, 0)
        )
        bpy.context.object.data.materials.append(m)
        for polygon in bpy.context.object.data.polygons:
            polygon.use_smooth = True
    import goo_engine_light_groups

    goo_engine_light_groups.sync_light_groups()
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    raw = RAW / (label + ".exr")
    s.render.filepath = str(raw)
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(str(raw), check_existing=False)
    pixels = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)
    raw_pixels[label] = pixels[:, :, :3]
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "16"
    im.save_render(str(OUT / (label + ".png")), scene=s)
    bpy.data.images.remove(im)
    left = pixels[:, :320, 0]
    visible = left > 1e-5
    measurements[label] = {
        "half_lambert_min_visible": float(left[visible].min()),
        "half_lambert_max": float(left.max()),
        "half_lambert_mean_visible": float(left[visible].mean()),
        "linear_exr": str(raw),
    }
    print("BASIC_GROUP_CASE", label, flush=True)
measurements["A_vs_C_max_abs_linear_difference"] = float(
    np.max(
        np.abs(
            raw_pixels["A-single-key"] - raw_pixels["C-fill-excluded-from-key-group"]
        )
    )
)
report = {
    "version": bpy.app.version_string,
    "build_hash": bpy.app.build_hash.decode(),
    "production_loaded": False,
    "video_created": False,
    "left": "raw Half-lambert factor",
    "right": "fixed three-band palette driven only by that factor",
    "measurements": measurements,
    "limits": "Static spheres, direct light, own light groups only; not a production shadow or animation validation",
}
(OUT / "measurements.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Basic_Light_Groups.blend"))
print("BASIC_LIGHT_GROUP_STUDY_COMPLETE", flush=True)
