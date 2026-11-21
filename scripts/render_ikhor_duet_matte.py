"""Render native duet Cryptomatte and Alpha from pinned v6/v7, without saving.

The existing Cryptomatte node receives the current actor object names. Only
actor materials' Surface outputs are replaced with unlit white/transparent,
using their original animated MMD Alpha (or outline Alpha). Geometry, actions,
shape keys, camera, DOF and motion blur are retained. Every inherited File
Output is muted; the only enabled File Output is the new diagnostic Alpha.

Run separate new output directories for two disjoint worker frame ranges.
"""

import argparse
import hashlib
import json
import shutil
import struct
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view

PINNED_SOURCES = {
    "201e2632befaf0a16f17b931963626a91bbc6b8f7e58d148d5047298a530de01": "production-v6",
    "f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692": "production-v7",
}
ACTORS = {"aksiniya", "ikhor"}
CRYPTO_NAME = "Caption | both performers native object coverage"


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def performer(obj):
    if obj.get("performer_id") in ACTORS:
        return obj["performer_id"]
    for modifier in obj.modifiers:
        if (
            modifier.type == "ARMATURE"
            and modifier.object
            and modifier.object.get("performer_id") in ACTORS
        ):
            return modifier.object["performer_id"]
    return None


def mute_outputs():
    seen, muted = set(), []

    def visit(tree):
        if not tree or tree.as_pointer() in seen:
            return
        seen.add(tree.as_pointer())
        for node in tree.nodes:
            if node.type == "OUTPUT_FILE":
                node.mute = True
                muted.append({"tree": tree.name, "node": node.name})
            if node.type == "GROUP":
                visit(node.node_tree)

    for scene in bpy.data.scenes:
        visit(scene.compositing_node_group)
    return muted


def unlit_alpha(material):
    assert material.use_nodes and material.node_tree, material.name
    tree = material.node_tree
    output = next(
        node
        for node in tree.nodes
        if node.type == "OUTPUT_MATERIAL" and node.is_active_output
    )
    previous = [
        [link.from_node.name, link.from_socket.name]
        for link in output.inputs["Surface"].links
    ]
    edge = tree.nodes.get("mmd_edge_preview")
    source = tree.nodes.get("mmd_shader")
    if edge and edge.inputs.get("Alpha"):
        alpha = edge.inputs["Alpha"]
        alpha_socket = alpha.links[0].from_socket if alpha.is_linked else None
        alpha_value = float(alpha.default_value)
        origin = {"node": edge.name, "input": "Alpha"}
    elif source and source.outputs.get("Alpha"):
        alpha_socket, alpha_value = source.outputs["Alpha"], None
        origin = {"node": source.name, "output": "Alpha"}
    else:
        raise ValueError("No audited MMD or outline Alpha: " + material.name)
    transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
    transparent.name = "Duet matte | transparent"
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.name = "Duet matte | white unlit"
    emission.inputs["Color"].default_value = (1, 1, 1, 1)
    emission.inputs["Strength"].default_value = 1
    mixed = tree.nodes.new("ShaderNodeMixShader")
    mixed.name = "Duet matte | preserve animated original Alpha"
    if alpha_socket is None:
        mixed.inputs[0].default_value = alpha_value
    else:
        tree.links.new(alpha_socket, mixed.inputs[0])
    tree.links.new(transparent.outputs[0], mixed.inputs[1])
    tree.links.new(emission.outputs[0], mixed.inputs[2])
    tree.links.new(mixed.outputs[0], output.inputs["Surface"])
    for name in ("Volume", "Displacement"):
        if output.inputs.get(name):
            for link in list(output.inputs[name].links):
                tree.links.remove(link)
    return {
        "material": material.name,
        "actor": material.get("performer_id"),
        "source_material": material.get("source_mmd_material_name"),
        "alpha_source": origin,
        "alpha_constant": alpha_value,
        "previous_surface": previous,
        "backface_culling_retained": material.use_backface_culling,
        "surface_render_method_retained": material.surface_render_method,
    }


def camera_state(scene):
    camera = scene.camera
    return {
        "object": camera.name,
        "matrix_world": [float(v) for row in camera.matrix_world for v in row],
        "lens": camera.data.lens,
        "dof": camera.data.dof.use_dof,
        "fstop": camera.data.dof.aperture_fstop,
        "focus_distance": camera.data.dof.focus_distance,
        "focus_object": camera.data.dof.focus_object.name
        if camera.data.dof.focus_object
        else None,
        "motion_blur": scene.render.use_motion_blur,
        "motion_blur_shutter": scene.render.motion_blur_shutter,
        "motion_blur_position": scene.render.motion_blur_position,
    }


def png_header(path):
    with path.open("rb") as stream:
        header = stream.read(33)
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    width, height, depth, color = struct.unpack(">IIBB", header[16:26])
    assert (width, height, depth, color) == (1920, 1080, 16, 0), (
        path,
        width,
        height,
        depth,
        color,
    )
    return {"size": [width, height], "bit_depth": depth, "color_type": color}


def load_mask(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = "Non-Color"
    width, height = image.size
    values = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(values)
    result = values.reshape(height, width, -1)[::-1, :, 0].copy()
    bpy.data.images.remove(image)
    assert np.isfinite(result).all()
    return result


def coverage(mask):
    selected = mask > 0.001
    y, x = np.where(selected)
    return {
        "coverage_sum": float(mask.sum()),
        "nonzero_pixels": int(selected.sum()),
        "left_half_pixels": int(selected[:, : mask.shape[1] // 2].sum()),
        "right_half_pixels": int(selected[:, mask.shape[1] // 2 :].sum()),
        "bbox_top_left": [
            int(x.min()),
            int(y.min()),
            int(x.max()) + 1,
            int(y.max()) + 1,
        ]
        if len(x)
        else None,
    }


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def head_roi(scene, obj, mask):
    """A labelled bone proxy ROI, not a semantic facial segmentation."""
    arm = next(mod.object for mod in obj.modifiers if mod.type == "ARMATURE")
    bone = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
    projected = [
        world_to_camera_view(scene, scene.camera, arm.matrix_world @ point)
        for point in (bone.head, bone.tail)
    ]
    width, height = mask.shape[1], mask.shape[0]
    points = np.array([[p.x * width, (1 - p.y) * height] for p in projected])
    center = points.mean(axis=0)
    radius = max(8, min(80, float(np.linalg.norm(points[1] - points[0])) * 0.35))
    x0, y0 = np.maximum(np.floor(center - radius).astype(int), 0)
    x1, y1 = np.minimum(np.ceil(center + radius).astype(int), [width, height])
    if x1 <= x0 or y1 <= y0 or min(p.z for p in projected) <= 0:
        return {"kind": "head_bone_proxy", "on_screen": False}
    roi = mask[y0:y1, x0:x1]
    return {
        "kind": "head_bone_proxy",
        "on_screen": True,
        "xyxy_top_left": [int(x0), int(y0), int(x1), int(y1)],
        "mean_coverage": float(roi.mean()),
        "nonzero_pixels": int((roi > 0.001).sum()),
    }


def merge_parts(args):
    """Read/decode every primary PNG again, copy only verified native masks."""
    destination = args.output_dir / "actor"
    assert not destination.exists(), destination
    assert not (args.output_dir / "matte-verification.json").exists()
    reports = [
        json.loads((part / "matte-render-report.json").read_text(encoding="utf-8"))
        for part in args.merge_parts
    ]
    source_sha = reports[0]["source_sha256"]
    assert source_sha in PINNED_SOURCES
    records = sorted(
        [record for report in reports for record in report["records"]],
        key=lambda record: record["frame"],
    )
    assert [record["frame"] for record in records] == list(range(4140, 4440))
    for report in reports:
        assert report["complete"] and report["source_sha256"] == source_sha
        assert report["source_samples"] == report["matte_samples"] == 48
        assert report["camera_dof_motion_blur_preserved"]
        assert len(report["records"]) == len(report["frames_requested"])
    assert digest(Path(reports[0]["source"])) == source_sha
    destination.mkdir(parents=True)
    for record in records:
        path = Path(record["native_cryptomatte"]["path"])
        assert digest(path) == record["native_cryptomatte"]["sha256"]
        png_header(path)
        pixels = load_mask(path)
        assert pixels.max() > 0 and pixels.min() >= 0 and pixels.max() <= 1
        assert record["camera"]["dof"] and record["camera"]["motion_blur"]
        for actor in ACTORS:
            person = record["per_person"][actor]
            person_path = Path(person["path"])
            assert digest(person_path) == person["sha256"]
            png_header(person_path)
            person_pixels = load_mask(person_path)
            assert person_pixels.max() > 0
            assert person["nonzero_pixels"] > 0 and person["bbox_top_left"]
            assert person["head_roi"]["on_screen"]
            assert person["head_roi"]["nonzero_pixels"] > 0
        final = destination / path.name
        shutil.copyfile(path, final)
        assert digest(final) == record["native_cryptomatte"]["sha256"]
        record["native_cryptomatte"]["part_path"] = str(path)
        record["native_cryptomatte"]["path"] = str(final)
    result = {
        "passed": True,
        "complete": True,
        "source": reports[0]["source"],
        "source_sha256": source_sha,
        "source_version": PINNED_SOURCES[source_sha],
        "source_modified": False,
        "worker_reports": [
            str(part / "matte-render-report.json") for part in args.merge_parts
        ],
        "primary_actor_dir": str(destination),
        "primary_count": len(records),
        "source_frame_range": [4140, 4439],
        "fps": 60,
        "samples": 48,
        "size": [1920, 1080],
        "png_bit_depth": 16,
        "png_color_type": 0,
        "all_primary_pngs_decoded_finite_nonempty": True,
        "per_person_pngs_decoded_finite_nonempty": 600,
        "camera_dof_motion_blur_retained": True,
        "per_person_coverage": {
            actor: {
                "frames": 300,
                "minimum_nonzero_pixels": min(
                    r["per_person"][actor]["nonzero_pixels"] for r in records
                ),
                "minimum_coverage_sum": min(
                    r["per_person"][actor]["coverage_sum"] for r in records
                ),
                "minimum_head_proxy_roi_mean": min(
                    r["per_person"][actor]["head_roi"]["mean_coverage"] for r in records
                ),
            }
            for actor in sorted(ACTORS)
        },
        "visual_review": "4250/4290 previews accepted by root; final composite review remains separate",
        "roi_scope": "Per-object native Cryptomatte coverage plus projected head-bone proxy; not semantic face segmentation.",
        "records": records,
    }
    write_json(args.output_dir / "matte-verification.json", result)
    print("DUET_MATTE_MERGE_COMPLETE", len(records), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frames", type=int, nargs="+")
    parser.add_argument("--start", type=int, default=4140)
    parser.add_argument("--end", type=int, default=4439)
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--compare-cache-dir", type=Path)
    parser.add_argument("--per-person", action="store_true")
    parser.add_argument("--merge-parts", type=Path, nargs="+")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.merge_parts:
        merge_parts(args)
        return
    frames = args.frames or list(range(args.start, args.end + 1))
    assert frames and len(frames) == len(set(frames))
    assert all(4140 <= frame <= 4439 for frame in frames)
    assert 16 <= args.samples <= 128
    source = args.source or Path(bpy.data.filepath)
    assert source.is_file(), source
    source_sha = digest(source)
    assert source_sha in PINNED_SOURCES, "Requires pinned production-v6/v7"
    if args.source:
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    assert Path(bpy.data.filepath).resolve() == source.resolve()
    scene = bpy.context.scene
    assert scene.rigidbody_world is None and scene.camera
    assert (scene.render.resolution_x, scene.render.resolution_y) == (1920, 1080)
    assert scene.render.fps == 60 and scene.render.fps_base == 1
    args.output_dir.mkdir(parents=True, exist_ok=False)
    actor_dir, alpha_dir = args.output_dir / "actor", args.output_dir / "film-alpha"
    actor_dir.mkdir()
    alpha_dir.mkdir()
    muted = mute_outputs()
    actors = [
        obj
        for obj in scene.objects
        if obj.type == "MESH" and performer(obj) and not obj.hide_render
    ]
    assert {performer(obj) for obj in actors} == ACTORS
    assert len(actors) == 2, [obj.name for obj in actors]
    shared_materials = {
        material
        for obj in actors
        for material in obj.data.materials
        if material is not None
    }
    materials = [
        unlit_alpha(material)
        for material in sorted(shared_materials, key=lambda m: m.name)
    ]
    hidden = []
    for obj in scene.objects:
        if (
            obj.type
            in {
                "MESH",
                "CURVE",
                "SURFACE",
                "META",
                "FONT",
                "VOLUME",
                "POINTCLOUD",
                "GREASEPENCIL",
                "LIGHT",
                "LIGHT_PROBE",
            }
            and obj not in actors
        ):
            obj.hide_render = True
            hidden.append(obj.name)
    world = bpy.data.worlds.new("Duet matte | transparent empty world")
    world.use_nodes = True
    background = world.node_tree.nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = 0
    world_output = world.node_tree.nodes.new("ShaderNodeOutputWorld")
    world.node_tree.links.new(background.outputs[0], world_output.inputs["Surface"])
    scene.world = world
    scene.render.film_transparent = True
    scene.render.use_sequencer = False
    scene.render.resolution_percentage = 100
    source_samples = scene.eevee.taa_render_samples
    scene.eevee.taa_render_samples = args.samples
    scene.view_settings.view_transform = "Raw"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "BW"
    scene.render.image_settings.color_depth = "16"
    scene.render.use_compositing = True
    tree = scene.compositing_node_group
    crypto = tree.nodes.get(CRYPTO_NAME)
    assert crypto and crypto.bl_idname == "CompositorNodeCryptomatteV2"
    original_ids = crypto.matte_id
    crypto.matte_id = ",".join(sorted(obj.name for obj in actors))
    layer = scene.view_layers[0]
    layer.use_pass_cryptomatte_object = True
    layer.update_render_passes()
    for other in scene.view_layers:
        other.use = other == layer
    layers = tree.nodes.new("CompositorNodeRLayers")
    layers.name = "Duet matte | isolated render layers"
    layers.scene, layers.layer = scene, layer.name
    output = next(
        node
        for node in tree.nodes
        if node.type == "GROUP_OUTPUT" and node.is_active_output
    )
    tree.links.new(crypto.outputs["Matte"], output.inputs["Image"])
    alpha_output = tree.nodes.new("CompositorNodeOutputFile")
    alpha_output.name = "Duet matte | new diagnostic FilmAlpha only"
    alpha_output.directory = str(alpha_dir)
    alpha_output.file_name = "frame_####"
    alpha_output.format.media_type = "IMAGE"
    alpha_output.format.file_format = "PNG"
    alpha_output.format.color_mode = "BW"
    alpha_output.format.color_depth = "16"
    alpha_output.save_as_render = False
    item = alpha_output.file_output_items.new("FLOAT", "alpha")
    item.save_as_render = False
    tree.links.new(layers.outputs["Alpha"], alpha_output.inputs["alpha"])
    person_dir = args.output_dir / "per-person"
    if args.per_person:
        person_dir.mkdir()
        person_output = tree.nodes.new("CompositorNodeOutputFile")
        person_output.name = "Duet matte | new per-person native Crypto only"
        person_output.directory = str(person_dir)
        person_output.file_name = "frame_####"
        person_output.format.media_type = "IMAGE"
        person_output.format.file_format = "PNG"
        person_output.format.color_mode = "BW"
        person_output.format.color_depth = "16"
        person_output.save_as_render = False
        for obj in actors:
            actor = performer(obj)
            person_crypto = tree.nodes.new("CompositorNodeCryptomatteV2")
            person_crypto.source = "RENDER"
            person_crypto.scene = scene
            person_crypto.layer_name = crypto.layer_name
            person_crypto.matte_id = obj.name
            item = person_output.file_output_items.new("FLOAT", actor)
            item.save_as_render = False
            tree.links.new(person_crypto.outputs["Matte"], person_output.inputs[actor])
    report = {
        "source": str(source),
        "source_sha256": source_sha,
        "source_version": PINNED_SOURCES[source_sha],
        "saved_source_modified": False,
        "frames_requested": frames,
        "source_samples": source_samples,
        "matte_samples": args.samples,
        "actors": [
            {"name": obj.name, "performer_id": performer(obj)} for obj in actors
        ],
        "materials": materials,
        "muted_inherited_outputs": muted,
        "hidden_non_actor_objects": hidden,
        "cryptomatte": {
            "node": crypto.name,
            "old_matte_id": original_ids,
            "new_matte_id": crypto.matte_id,
            "layer": crypto.layer_name,
        },
        "camera_dof_motion_blur_preserved": True,
        "geometry_actions_shapes_preserved": True,
        "source_camera": camera_state(scene),
        "complete": False,
        "visual_review": "pending",
        "records": [],
    }
    write_json(args.output_dir / "matte-render-report.json", report)
    started = time.monotonic()
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        target = actor_dir / f"frame_{frame:04d}actor.png"
        assert not target.exists()
        scene.render.filepath = str(target)
        then = time.monotonic()
        bpy.ops.render.render(write_still=True)
        alpha_path = alpha_dir / f"frame_{frame:04d}alpha.png"
        record = {
            "frame": frame,
            "render_seconds": time.monotonic() - then,
            "camera": camera_state(scene),
            "native_cryptomatte": {
                "path": str(target),
                "sha256": digest(target),
                **png_header(target),
            },
            "film_alpha": {
                "path": str(alpha_path),
                "sha256": digest(alpha_path),
                **png_header(alpha_path),
            },
        }
        native, film = load_mask(target), load_mask(alpha_path)
        record["native_cryptomatte"].update(coverage(native))
        record["film_alpha"].update(coverage(film))
        record["film_vs_crypto"] = {
            "max_abs_error": float(np.max(np.abs(native - film))),
            "mean_abs_error": float(np.mean(np.abs(native - film))),
        }
        if args.per_person:
            record["per_person"] = {}
            for obj in actors:
                actor = performer(obj)
                person_path = person_dir / f"frame_{frame:04d}{actor}.png"
                person_pixels = load_mask(person_path)
                assert person_pixels.max() > 0
                record["per_person"][actor] = {
                    "path": str(person_path),
                    "sha256": digest(person_path),
                    **png_header(person_path),
                    **coverage(person_pixels),
                    "head_roi": head_roi(scene, obj, person_pixels),
                }
        if args.compare_cache_dir:
            old_path = args.compare_cache_dir / target.name
            if old_path.is_file():
                old = load_mask(old_path)
                record["old_cache"] = {
                    "path": str(old_path),
                    "sha256": digest(old_path),
                    **coverage(old),
                    "new_coverage_not_in_old_sum": float(
                        np.maximum(native - old, 0).sum()
                    ),
                }
        report["records"].append(record)
        write_json(args.output_dir / "matte-render-report.json", report)
        print("DUET_MATTE_FRAME_COMPLETE", frame, record["render_seconds"], flush=True)
    assert digest(source) == source_sha
    report["complete"] = True
    report["elapsed_seconds"] = time.monotonic() - started
    write_json(args.output_dir / "matte-render-report.json", report)
    print("DUET_MATTE_COMPLETE", len(frames), flush=True)


if __name__ == "__main__":
    main()
