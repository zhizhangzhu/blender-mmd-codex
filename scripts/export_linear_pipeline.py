"""Validate native RGBA layers, a signed interaction pass and linear archives.

Actors and stage are rendered natively, not extracted from a flattened beauty.
The interaction residual preserves coupled shadows/reflections when recombining
the independently rendered scenes. It must be regenerated if geometry changes.
"""

import argparse
import hashlib
import json
import shutil
import sys
import warnings
from pathlib import Path

import bpy
import numpy as np


def ensure_native_scenes(scene):
    def find(root, name):
        if root.collection.name == name:
            return root
        for child in root.children:
            found = find(child, name)
            if found:
                return found
        return None

    actors = bpy.data.scenes.get("Quality | native actor RGBA")
    stage = bpy.data.scenes.get("Quality | clean stage")
    if actors is None:
        actors = scene.copy()
        actors.name = "Quality | native actor RGBA"
        find(
            actors.view_layers[0].layer_collection, "Quality | stage geometry"
        ).holdout = True
    if stage is None:
        stage = scene.copy()
        stage.name = "Quality | clean stage"
        find(
            stage.view_layers[0].layer_collection, "Quality | performer geometry"
        ).exclude = True
    for current in [actors, stage]:
        current.use_fake_user = True
        current.render.use_compositing = False
        current.compositing_node_group = None
    actors.render.film_transparent = True
    return actors, stage


def read_image(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    metadata = {
        "alpha_mode": image.alpha_mode,
        "color_space": image.colorspace_settings.name,
        "size": [width, height],
        "float": image.is_float,
    }
    bpy.data.images.remove(image)
    return pixels.reshape(height, width, 4), metadata


def save_array(scene, path, pixels, depth="32", png=False):
    height, width = pixels.shape[:2]
    image = bpy.data.images.new(
        "Quality | temporary linear array",
        width=width,
        height=height,
        alpha=True,
        float_buffer=True,
    )
    image.alpha_mode = "PREMUL"
    image.colorspace_settings.name = "Linear Rec.709"
    image.pixels.foreach_set(np.asarray(pixels, dtype=np.float32).ravel())
    scene.render.image_settings.file_format = "PNG" if png else "OPEN_EXR"
    scene.render.image_settings.color_depth = "16" if png else depth
    scene.render.image_settings.color_mode = "RGBA"
    if not png:
        scene.render.image_settings.exr_codec = "ZIP"
    image.save_render(str(path), scene=scene)
    bpy.data.images.remove(image)


def native_render(scene, frame, path, percentage):
    bpy.context.window.scene = scene
    scene.frame_set(frame)
    scene.render.resolution_percentage = percentage
    scene.render.use_compositing = False
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return read_image(path)


def attach_archive(scene, directory):
    tree = scene.compositing_node_group
    layers = next(node for node in tree.nodes if node.type == "R_LAYERS")
    output = next(node for node in tree.nodes if node.type == "GROUP_OUTPUT")
    final = output.inputs[0].links[0].from_socket
    archive = tree.nodes.get("Quality | scene-linear EXR archive") or tree.nodes.new("CompositorNodeOutputFile")
    archive.file_output_items.clear()
    archive.mute = False
    archive.name = "Quality | scene-linear EXR archive"
    archive.directory = str(directory)
    archive.file_name = "duet_####"
    archive.format.file_format = "OPEN_EXR_MULTILAYER"
    archive.format.color_depth = "16"
    archive.format.exr_codec = "ZIP"
    archive.save_as_render = False
    for socket_type, name, source in [
        ("RGBA", "RawBeauty", layers.outputs["Image"]),
        ("RGBA", "FinalLinear", final),
        ("FLOAT", "ActorMask", layers.outputs["ReferenceDuetActor"]),
    ]:
        archive.file_output_items.new(socket_type, name)
        tree.links.new(source, archive.inputs[name])
    return archive


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--percentage", type=int, default=100)
    parser.add_argument("--reuse-splits-from", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with open(bpy.data.filepath, "rb") as stream:
        source_hash = hashlib.sha256()
        for block in iter(lambda: stream.read(1048576), b""):
            source_hash.update(block)
    source_record = {
        "source": bpy.data.filepath,
        "sha256": source_hash.hexdigest(),
        "percentage": args.percentage,
    }
    (args.output_dir / "split-source.json").write_text(
        json.dumps(source_record, indent=2), encoding="utf-8"
    )
    if args.reuse_splits_from:
        previous = json.loads(
            (args.reuse_splits_from / "split-source.json").read_text(encoding="utf-8")
        )
        assert (
            previous["sha256"] == source_record["sha256"]
            and previous["percentage"] == args.percentage
        )

    def capture(scene, frame, path):
        if args.reuse_splits_from:
            original = args.reuse_splits_from / path.relative_to(args.output_dir)
            if original.is_file():
                shutil.copyfile(original, path)
                return read_image(path)
        return native_render(scene, frame, path, args.percentage)

    main_scene = bpy.context.scene
    actor_scene, stage_scene = ensure_native_scenes(main_scene)
    main_compositor = main_scene.compositing_node_group
    results = []
    for frame in [4140, 4200, 4290, 4420, 4439]:
        folder = args.output_dir / f"frame-{frame}"
        folder.mkdir()
        raw, raw_meta = capture(main_scene, frame, folder / "beauty-linear.exr")
        actors, actor_meta = capture(
            actor_scene, frame, folder / "actors-premultiplied.exr"
        )
        stage, stage_meta = capture(stage_scene, frame, folder / "stage-clean.exr")
        alpha = np.clip(actors[..., 3:4], 0, 1)
        over = actors[..., :3] + stage[..., :3] * (1 - alpha)
        interaction = np.ones_like(raw)
        interaction[..., :3] = raw[..., :3] - over
        save_array(main_scene, folder / "interaction-signed.exr", interaction)
        retained, _ = read_image(folder / "interaction-signed.exr")
        reconstructed = np.ones_like(raw)
        reconstructed[..., :3] = over + retained[..., :3]
        error = np.abs(reconstructed[..., :3] - raw[..., :3])
        assert np.isfinite(reconstructed).all()
        assert error.max() < 0.00005, float(error.max())
        assert alpha.min() == 0 and alpha.max() > 0.99
        empty = alpha[..., 0] < 0.00001
        hidden_rgb = float(np.abs(actors[..., :3][empty]).max()) if empty.any() else 0
        assert hidden_rgb < 0.0001, hidden_rgb
        save_array(
            main_scene, folder / "reconstructed-standard.png", reconstructed, png=True
        )
        if frame == 4200:
            for label, color in [
                ("white", [1, 1, 1]),
                ("black", [0, 0, 0]),
                ("magenta", [1, 0.05, 0.55]),
            ]:
                review = np.ones_like(raw)
                review[..., :3] = actors[..., :3] + np.asarray(color) * (1 - alpha)
                save_array(
                    main_scene, folder / f"actors-over-{label}.png", review, png=True
                )
        results.append(
            {
                "frame": frame,
                "maximum_reconstruction_error": float(error.max()),
                "mean_reconstruction_error": float(error.mean()),
                "transparent_rgb_max": hidden_rgb,
                "partial_alpha_pixels": int(
                    np.count_nonzero((alpha > 0.001) & (alpha < 0.999))
                ),
                "interaction_min": float(interaction[..., :3].min()),
                "interaction_max": float(interaction[..., :3].max()),
                "raw_metadata": raw_meta,
                "actor_metadata": actor_meta,
                "stage_metadata": stage_meta,
            }
        )
        print("LINEAR_FRAME_VERIFIED", frame, float(error.max()), flush=True)
    # A fixed 18% patch detects accidental display transforms in EXR or double
    # display transforms on the review PNG. HDR values must survive the EXR.
    patches = np.ones((32, 128, 4), dtype=np.float32)
    for index, value in enumerate([0, 0.18, 1, 4]):
        patches[:, index * 32 : (index + 1) * 32, :3] = value
    save_array(
        main_scene, args.output_dir / "color-patches-linear.exr", patches, depth="16"
    )
    linear, metadata = read_image(args.output_dir / "color-patches-linear.exr")
    save_array(
        main_scene, args.output_dir / "color-patches-standard.png", patches, png=True
    )
    display, _ = read_image(args.output_dir / "color-patches-standard.png")
    expected = 1.055 * 0.18 ** (1 / 2.4) - 0.055
    encoded_image = bpy.data.images.load(
        str(args.output_dir / "color-patches-standard.png"), check_existing=False
    )
    encoded_image.colorspace_settings.name = "Non-Color"
    encoded_image.reload()
    encoded_pixels = np.empty(32 * 128 * 4, dtype=np.float32)
    encoded_image.pixels.foreach_get(encoded_pixels)
    encoded_value = float(encoded_pixels.reshape(32, 128, 4)[16, 48, 0])
    bpy.data.images.remove(encoded_image)
    color_check = {
        "linear_18": float(linear[16, 48, 0]),
        "linear_hdr_4": float(linear[16, 112, 0]),
        "display_18": float(display[16, 48, 0]),
        "display_18_encoded": encoded_value,
        "expected_srgb_18": expected,
        "metadata": metadata,
    }
    assert abs(color_check["linear_18"] - 0.18) < 0.0002, color_check
    assert abs(color_check["linear_hdr_4"] - 4) < 0.001, color_check
    assert abs(color_check["display_18"] - 0.18) < 0.001, color_check
    assert abs(encoded_value - expected) < 0.01, color_check
    bpy.context.window.scene = main_scene
    main_scene.compositing_node_group = main_compositor
    main_scene.render.use_compositing = True
    main_scene.render.resolution_percentage = 100
    main_scene.render.image_settings.file_format = "PNG"
    main_scene.render.image_settings.color_depth = "16"
    main_scene.frame_set(4140)
    archive = attach_archive(main_scene, args.archive_dir)
    main_scene.render.filepath = str(args.output_dir / "archive-smoke-4140.png")
    bpy.ops.render.render(write_still=True)
    args.archive_dir.mkdir(parents=True, exist_ok=True)
    files = list(args.archive_dir.glob("*.exr"))
    assert files, "Native EXR output missing"
    project = args.output_dir / "Franken_Duet_Linear_Ready.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "frames": results,
        "color_check": color_check,
        "archive_node": archive.name,
        "archive_smoke_files": [str(path) for path in files],
        "project": str(project),
        "native_layers": True,
        "reconstruction": "premultiplied actors OVER clean stage PLUS signed scene interaction; raw scene-linear before creative stage grade",
        "limits": "Interaction is coupled to geometry/lights and must be rerendered. Native split layers verified at five frames; the full sample archives RawBeauty, FinalLinear and ActorMask.",
    }
    (args.output_dir / "linear-verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("LINEAR_PIPELINE_READY", str(project), flush=True)


if __name__ == "__main__":
    main()
