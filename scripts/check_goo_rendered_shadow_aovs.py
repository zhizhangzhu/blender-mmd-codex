"""Verify actual shader texture sequence sampling using raw face UV/value AOVs."""

import json

import bpy
import numpy as np
from prepare_goo_eye_hair_stage import PREFIX


def pixels(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = "Non-Color"
    values = np.empty(image.size[0] * image.size[1] * 4, np.float32)
    image.pixels.foreach_get(values)
    result = values.reshape(image.size[1], image.size[0], 4).copy()
    bpy.data.images.remove(image)
    return result


def setup(scene, production):
    tree = scene.compositing_node_group
    render = next(n for n in tree.nodes if n.type == "R_LAYERS")
    directory = production / "shadow-render-probes"
    directory.mkdir(exist_ok=True)
    for actor, face in (("aksiniya", "颜"), ("ikhor", "颜.001")):
        material = bpy.data.materials[face].node_tree
        for suffix, source in (
            ("UV", material.nodes[PREFIX + "actual face shadow UV"].outputs[0]),
            (
                "Visibility",
                material.nodes[PREFIX + "geometry derived hair shadow"].outputs[
                    "Color"
                ],
            ),
        ):
            name = "HairProbe" + actor + suffix
            aov = scene.view_layers[0].aovs.add()
            aov.name = name
            aov.type = "COLOR"
            node = material.nodes.new("ShaderNodeOutputAOV")
            node.aov_name = name
            material.links.new(source, node.inputs["Color"])
    bpy.context.view_layer.update()
    output = tree.nodes.new("CompositorNodeOutputFile")
    output.directory = str(directory)
    output.file_name = "frame_####"
    output.format.media_type = "IMAGE"
    output.format.file_format = "OPEN_EXR"
    output.format.color_depth = "32"
    output.save_as_render = False
    output.file_output_items.clear()
    for actor in ("aksiniya", "ikhor"):
        for suffix in ("UV", "Visibility"):
            name = "HairProbe" + actor + suffix
            output.file_output_items.new("RGBA", name)
            tree.links.new(render.outputs[name], output.inputs[name])
    return directory


def compare(scene, production, directory):
    records = []
    for actor in ("aksiniya", "ikhor"):
        uv = pixels(
            directory / f"frame_{scene.frame_current:04d}HairProbe{actor}UV.exr"
        )[:, :, :2]
        actual = pixels(
            directory / f"frame_{scene.frame_current:04d}HairProbe{actor}Visibility.exr"
        )[:, :, 0]
        valid = (
            (uv[:, :, 0] > 0.001)
            & (uv[:, :, 0] < 0.999)
            & (uv[:, :, 1] > 0.001)
            & (uv[:, :, 1] < 0.999)
            & (actual > 0.1)
        )
        for axis in (0, 1):
            for step in (-1, 1):
                valid &= np.abs(uv - np.roll(uv, step, axis=axis)).max(axis=2) < 0.015
        if np.count_nonzero(valid) < 100:
            continue
        expected_path = (
            production
            / "hair-shadows"
            / f"{actor}_{scene.frame_current - 4139:04d}.png"
        )

        def sample(path, uv=uv, valid=valid):
            image = pixels(path)[:, :, 0]
            x = np.clip(uv[:, :, 0] * image.shape[1] - 0.5, 0, image.shape[1] - 1)
            y = np.clip(uv[:, :, 1] * image.shape[0] - 0.5, 0, image.shape[0] - 1)
            x0 = x.astype(int)
            y0 = y.astype(int)
            x1 = np.minimum(x0 + 1, image.shape[1] - 1)
            y1 = np.minimum(y0 + 1, image.shape[0] - 1)
            fx = x - x0
            fy = y - y0
            return (
                image[y0, x0] * (1 - fx) * (1 - fy)
                + image[y0, x1] * fx * (1 - fy)
                + image[y1, x0] * (1 - fx) * fy
                + image[y1, x1] * fx * fy
            )[valid]

        error = np.abs(actual[valid] - sample(expected_path))
        frozen_error = np.abs(
            actual[valid] - sample(production / "hair-shadows" / f"{actor}_0001.png")
        )
        row = {
            "actor": actor,
            "frame": scene.frame_current,
            "expected": expected_path.name,
            "pixels": int(valid.sum()),
            "mean_abs_error": float(error.mean()),
            "p99_abs_error": float(np.quantile(error, 0.99)),
            "frozen_first_frame_mean_abs_error": float(frozen_error.mean()),
        }
        assert row["mean_abs_error"] < 0.009 and row["p99_abs_error"] < 0.065, row
        records.append(row)
    path = production / "rendered-shadow-sequence-check.json"
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    path.write_text(json.dumps(previous + records, indent=2), encoding="utf-8")
    print("RENDERED_SHADOW_AOV_MATCH", records, flush=True)
