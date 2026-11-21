"""Compare actual Shader Info inputs across existing Goo builds in empty scenes."""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from study_goo_feature_mechanisms import mat, scene

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--build", choices=("goo52", "goo43"), required=True)
parser.add_argument("--reopen", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
EXPECTED = {"goo52": "0051aee03764", "goo43": "ba60b2412c76"}
assert bpy.app.build_hash.decode() == EXPECTED[args.build]
BASE = Path("D:/codex/output/Goo-Input-Matrix-Study-2026-11-18")
OUT = BASE / args.build
RAW = Path("D:/codex/temp/Goo-Input-Matrix-Study-2026-11-18") / args.build
RAW.mkdir(parents=True, exist_ok=True)
PANELS = ["half_lambert", "diffuse", "cast", "self", "diffuse_bsdf_combined"]
SCALES = [1.0, 0.1, 1.0, 1.0, 0.1]


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


def panel_crop(pixels, index):
    s = bpy.context.scene
    x = index - 2
    lo = world_to_camera_view(s, s.camera, Vector((x - 0.37, -0.37, 0)))
    hi = world_to_camera_view(s, s.camera, Vector((x + 0.37, 0.37, 0)))
    return pixels[
        int(lo.y * pixels.shape[0]) : int(hi.y * pixels.shape[0]),
        int(lo.x * pixels.shape[1]) : int(hi.x * pixels.shape[1]),
        :3,
    ]


if args.reopen:
    bpy.ops.wm.open_mainfile(
        filepath=str(OUT / "Normal_Down_Control.blend"),
        use_scripts=False,
        load_ui=False,
    )
    repeat = render("N-down-reopened")
    image = bpy.data.images.load(str(RAW / "N-down.exr"), check_existing=False)
    original = np.array(image.pixels[:], dtype=np.float32).reshape(repeat.shape)
    bpy.data.images.remove(image)
    difference = np.abs(original - repeat)
    result = {
        "build_hash": bpy.app.build_hash.decode(),
        "max_abs_linear_rgba_difference": float(difference.max()),
        "passed": bool(difference.max() < 1e-6),
        "production_loaded": False,
    }
    assert result["passed"], result
    (OUT / "reopen-verification.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print("INPUT_MATRIX_REOPEN_COMPLETE", json.dumps(result), flush=True)
    raise SystemExit(0)

OUT.mkdir(parents=True, exist_ok=False)
all_pixels = {}
rows = {}
for label, normal, position, move_light in (
    ("A-default", None, False, False),
    ("N-up", (0, 0, 1), False, False),
    ("N-down", (0, 0, -1), False, False),
    ("P-offset", None, True, False),
    ("L-real-move", None, False, True),
):
    s = scene(1000, 240)
    s.camera.location = (0, 0, 9)
    s.camera.rotation_euler = (0, 0, 0)
    s.camera.data.ortho_scale = 5.6
    s.eevee.taa_render_samples = 32
    bpy.ops.object.light_add(type="POINT", location=(0, -2, 4))
    lamp = bpy.context.object
    lamp.data.energy = 400
    lamp.data.shadow_soft_size = 0.025
    if move_light:
        lamp.location = (0, -0.5, 2)
    links = []
    for index, panel in enumerate(PANELS):
        x = index - 2
        material, emission = mat("Input matrix " + panel)
        material.check_shadow_id = True
        tree = material.node_tree
        info = tree.nodes.new("ShaderNodeShaderInfo")
        vector = None
        if normal is not None:
            vector = tree.nodes.new("ShaderNodeCombineXYZ")
            for socket, coordinate in zip(vector.inputs, normal):
                socket.default_value = coordinate
            tree.links.new(vector.outputs[0], info.inputs["Normal"])
        if position:
            geometry = tree.nodes.new("ShaderNodeNewGeometry")
            offset = tree.nodes.new("ShaderNodeVectorMath")
            offset.operation = "ADD"
            tree.links.new(geometry.outputs["Position"], offset.inputs[0])
            offset.inputs[1].default_value = (3, 0, 1)
            tree.links.new(offset.outputs[0], info.inputs["WorldPosition"])
        if index < 4:
            signal = info.outputs[
                [
                    "Half-lambert factor",
                    "Diffuse Shading",
                    "Cast Shadows",
                    "Self Shadows",
                ][index]
            ]
        else:
            diffuse = tree.nodes.new("ShaderNodeBsdfDiffuse")
            diffuse.inputs["Color"].default_value = (1, 1, 1, 1)
            if vector is not None:
                tree.links.new(vector.outputs[0], diffuse.inputs["Normal"])
            rgb = tree.nodes.new("ShaderNodeShaderToRGB")
            tree.links.new(diffuse.outputs[0], rgb.inputs[0])
            signal = rgb.outputs["Color"]
        scale = tree.nodes.new("ShaderNodeMixRGB")
        scale.blend_type = "MULTIPLY"
        scale.inputs[0].default_value = 1
        scale.inputs[2].default_value = (SCALES[index],) * 3 + (1,)
        tree.links.new(signal, scale.inputs[1])
        tree.links.new(scale.outputs[0], emission.inputs["Color"])
        bpy.ops.mesh.primitive_plane_add(size=0.84, location=(x, 0, 0))
        receiver = bpy.context.object
        receiver.data.materials.append(material)
        if panel in ("cast", "self"):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 0.65))
            cube = bpy.context.object
            cube.scale = (0.15, 0.10, 0.10)
            black, _ = mat("Occluder")
            cube.data.materials.append(black)
            if panel == "self":
                bpy.ops.object.select_all(action="DESELECT")
                receiver.select_set(True)
                cube.select_set(True)
                bpy.context.view_layer.objects.active = receiver
                bpy.ops.object.join()
        links.append(
            {
                "panel": panel,
                "Normal": info.inputs["Normal"].is_linked,
                "WorldPosition": info.inputs["WorldPosition"].is_linked,
            }
        )
    pixels = all_pixels[label] = render(label)
    rows[label] = {
        "links": links,
        "panel_means_scaled": {
            name: panel_crop(pixels, i).mean(axis=(0, 1)).tolist()
            for i, name in enumerate(PANELS)
        },
    }
    if label == "N-down":
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Normal_Down_Control.blend"))
    print("INPUT_MATRIX_CASE", args.build, label, flush=True)

deltas = {}
for label, pixels in all_pixels.items():
    if label == "A-default":
        continue
    deltas[label] = {}
    for i, name in enumerate(PANELS):
        difference = np.abs(
            panel_crop(pixels, i) - panel_crop(all_pixels["A-default"], i)
        )
        deltas[label][name] = {
            "max_abs_scaled": float(difference.max()),
            "mean_abs_scaled": float(difference.mean()),
        }
report = {
    "version": bpy.app.version_string,
    "build_hash": bpy.app.build_hash.decode(),
    "binary": bpy.app.binary_path,
    "cases": rows,
    "deltas_vs_default": deltas,
    "display_scales": dict(zip(PANELS, SCALES)),
    "point_light": "400W; default (0,-2,4), real move (0,-0.5,2)",
    "position_offset": [3, 0, 1],
    "normal_vectors": "linked unit up/down",
    "production_loaded": False,
    "video_created": False,
    "limits": "Five fixed planar panels, one point light, simple external/joined blockers; Diffuse BSDF route is combined shading, not pure shadow visibility. Builds have different renderers; compare input effects within each build, not absolute cross-engine pixels.",
}
(OUT / "measurements.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("GOO_INPUT_MATRIX_COMPLETE", args.build, flush=True)
