"""Check Shader Info Normal input against explicit normal-dot-light controls."""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from study_goo_feature_mechanisms import mat, scene, sun

OUT = Path("D:/codex/output/Goo-Reference-Normal-Study-2026-11-17")
RAW = Path("D:/codex/temp/Goo-Reference-Normal-Study-2026-11-17")
OUT.mkdir(exist_ok=False)
RAW.mkdir(exist_ok=True)
arrays = {}
rows = {}


def render(label):
    s = bpy.context.scene
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.render.filepath = str(RAW / (label + ".exr"))
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(s.render.filepath, check_existing=False)
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        image.size[1], image.size[0], 4
    )
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "16"
    image.save_render(str(OUT / (label + ".png")), scene=s)
    bpy.data.images.remove(image)
    return pixels


for label, normal, analytic in (
    ("A-info-default-normal", None, False),
    ("B-info-normal-up", (0, 0, 1), False),
    ("C-info-normal-down", (0, 0, -1), False),
    ("D-math-normal-up", (0, 0, 1), True),
    ("E-math-normal-down", (0, 0, -1), True),
):
    s = scene(384, 384)
    s.camera.location = (0, -5, 1.2)
    s.camera.rotation_euler = (-s.camera.location).to_track_quat("-Z", "Y").to_euler()
    s.camera.data.ortho_scale = 2.6
    s.render.film_transparent = True
    sun(energy=1)
    material, emission = mat("Normal input basic control")
    tree = material.node_tree
    info = tree.nodes.new("ShaderNodeShaderInfo")
    signal = info.outputs["Half-lambert factor"]
    if normal is not None:
        vector = tree.nodes.new("ShaderNodeCombineXYZ")
        for socket, coordinate in zip(vector.inputs, normal):
            socket.default_value = coordinate
        if analytic:
            dot = tree.nodes.new("ShaderNodeVectorMath")
            dot.operation = "DOT_PRODUCT"
            tree.links.new(vector.outputs[0], dot.inputs[0])
            dot.inputs[1].default_value = (0, 0, 1)
            remap = tree.nodes.new("ShaderNodeMath")
            remap.operation = "MULTIPLY_ADD"
            tree.links.new(dot.outputs["Value"], remap.inputs[0])
            remap.inputs[1].default_value = 0.5
            remap.inputs[2].default_value = 0.5
            remap.use_clamp = True
            signal = remap.outputs[0]
        else:
            tree.links.new(vector.outputs[0], info.inputs["Normal"])
    tree.links.new(signal, emission.inputs["Color"])
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1)
    sphere = bpy.context.object
    sphere.data.materials.append(material)
    for p in sphere.data.polygons:
        p.use_smooth = True
    pixels = arrays[label] = render(label)
    mask = pixels[:, :, 3] > 0.999
    rows[label] = {
        "info_normal_linked": info.inputs["Normal"].is_linked,
        "analytic": analytic,
        "normal": normal,
        "interior_rgb_mean": pixels[:, :, :3][mask].mean(axis=0).tolist(),
        "interior_min": float(pixels[:, :, 0][mask].min()),
        "interior_max": float(pixels[:, :, 0][mask].max()),
    }
    if label == "B-info-normal-up":
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Info_Normal_Up.blend"))


def delta(a, b):
    return float(np.max(np.abs(arrays[a] - arrays[b])))


bpy.ops.wm.open_mainfile(
    filepath=str(OUT / "Info_Normal_Up.blend"), use_scripts=False, load_ui=False
)
arrays["B-reopened"] = render("B-reopened")
result = {
    "version": bpy.app.version_string,
    "build_hash": bpy.app.build_hash.decode(),
    "production_loaded": False,
    "video_created": False,
    "cases": rows,
    "max_abs_default_vs_up": delta("A-info-default-normal", "B-info-normal-up"),
    "max_abs_default_vs_down": delta("A-info-default-normal", "C-info-normal-down"),
    "positive_control_up_vs_down": delta("D-math-normal-up", "E-math-normal-down"),
    "independent_reopen_max_abs": delta("B-info-normal-up", "B-reopened"),
    "scope": "Half-lambert output only, one SUN, smooth sphere, linked unit Normal values; not all Shader Info outputs or all builds",
}
assert result["positive_control_up_vs_down"] > 0.99
assert result["independent_reopen_max_abs"] < 1e-6
(OUT / "measurements.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print("NORMAL_INPUT_BASIC_COMPLETE", json.dumps(result), flush=True)
