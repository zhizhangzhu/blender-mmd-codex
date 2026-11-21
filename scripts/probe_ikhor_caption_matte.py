"""Read-only inventory of the active caption matte graph and PNG coverage.

Run inside Blender. Does not render, save a blend, alter shader links or write
into the production/cache directories. Cached PNGs are only loaded in memory.
"""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import bpy
import numpy as np


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def upstream(socket):
    records, pending, seen = [], [socket], set()
    while pending:
        current = pending.pop()
        for link in current.links:
            key = (
                link.from_node.name,
                link.from_socket.identifier,
                link.to_node.name,
                link.to_socket.identifier,
            )
            if key in seen:
                continue
            seen.add(key)
            node = link.from_node
            records.append(
                {
                    "from_node": node.name,
                    "from_type": node.bl_idname,
                    "from_socket": link.from_socket.name,
                    "to_node": link.to_node.name,
                    "to_socket": link.to_socket.name,
                    "from_node_muted": node.mute,
                    "render_scene": node.scene.name
                    if node.type == "R_LAYERS" and node.scene
                    else None,
                    "render_layer": getattr(node, "layer", None),
                }
            )
            pending.extend(node.inputs)
    return records


def bbox(mask):
    yy, xx = np.where(mask)
    return (
        [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]
        if len(xx)
        else None
    )


def coverage(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = "Non-Color"
    values = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(values)
    width, height = image.size
    channels = len(values) // (width * height)
    pixels = values.reshape(height, width, channels)
    # Blender's pixel buffer has its origin at bottom left; report top-left PNG.
    mask = pixels[::-1, :, : min(channels, 3)].max(axis=2) > 1e-5
    left, right = mask.copy(), mask.copy()
    left[:, width // 2 :] = False
    right[:, : width // 2] = False
    result = {
        "path": str(path),
        "sha256": digest(path),
        "size": [width, height],
        "nonzero_pixels": int(mask.sum()),
        "bbox_xyxy_top_left": bbox(mask),
        "left_half": {"nonzero_pixels": int(left.sum()), "bbox": bbox(left)},
        "right_half": {"nonzero_pixels": int(right.sum()), "bbox": bbox(right)},
    }
    bpy.data.images.remove(image)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--frames", default="4140,4250,4290,4439")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(args.blend), load_ui=False)
    scene = bpy.context.scene
    tree = scene.compositing_node_group
    crypto_nodes = []
    for node in tree.nodes:
        if "Cryptomatte" in node.bl_idname:
            properties = {}
            for name in [
                "source",
                "scene",
                "layer_name",
                "view_layer",
                "matte_id",
                "render_source",
            ]:
                if hasattr(node, name):
                    value = getattr(node, name)
                    properties[name] = (
                        value.name if isinstance(value, bpy.types.Scene) else str(value)
                    )
            selected_names = [v.strip() for v in properties.get("matte_id", "").split(",") if v.strip()]
            crypto_nodes.append({"name": node.name, "properties": properties,
                                 "selected_object_names_absent_from_scene": [v for v in selected_names if v not in scene.objects],
                                 "selection_check_scope": "Literal scene object names only; numeric hash tokens or escaped/comma-containing names require manual interpretation."})
    caption_nodes = []
    for node in tree.nodes:
        if "caption" in node.name.lower() and (
            "actor" in node.name.lower() or node.type == "OUTPUT_FILE"
        ):
            paths = [row for socket in node.inputs for row in upstream(socket)]
            caption_nodes.append(
                {
                    "name": node.name,
                    "type": node.bl_idname,
                    "muted": node.mute,
                    "directory": getattr(node, "directory", None),
                    "upstream_edges": paths,
                    "aov_source_sockets": sorted(
                        {
                            r["from_socket"]
                            for r in paths
                            if r["from_type"] == "CompositorNodeRLayers"
                        }
                    ),
                }
            )
    materials = defaultdict(dict)
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        actor = obj.get("performer_id")
        if actor not in {"aksiniya", "ikhor"}:
            actor = next(
                (
                    m.object.get("performer_id")
                    for m in obj.modifiers
                    if m.type == "ARMATURE"
                    and m.object
                    and m.object.get("performer_id") in {"aksiniya", "ikhor"}
                ),
                None,
            )
        if actor not in {"aksiniya", "ikhor"}:
            continue
        for material in obj.data.materials:
            if not material or not material.use_nodes:
                continue
            aovs = []
            for node in material.node_tree.nodes:
                if node.bl_idname == "ShaderNodeOutputAOV":
                    aovs.append(
                        {
                            "node": node.name,
                            "aov_name": node.aov_name,
                            "muted": node.mute,
                            "inputs": [
                                {
                                    "socket": s.name,
                                    "default": list(s.default_value)
                                    if s.type == "RGBA"
                                    else s.default_value,
                                    "links": [
                                        {
                                            "node": link.from_node.name,
                                            "socket": link.from_socket.name,
                                        }
                                        for link in s.links
                                    ],
                                }
                                for s in node.inputs
                            ],
                        }
                    )
            materials[actor][material.name] = {
                "source_name": material.get(
                    "source_mmd_material_name", material.mmd_material.name_j
                ),
                "aov_outputs": aovs,
            }
    pngs = []
    for frame in [int(v) for v in args.frames.split(",")]:
        path = args.cache_dir / "actor" / f"frame_{frame:04d}actor.png"
        pngs.append(
            {"frame": frame, **coverage(path)}
            if path.is_file()
            else {"frame": frame, "missing": str(path)}
        )
    result = {
        "project": str(args.blend),
        "project_sha256": digest(args.blend),
        "scene": scene.name,
        "view_layers": [
            {
                "name": layer.name,
                "aovs": [{"name": a.name, "data_type": a.type} for a in layer.aovs],
            }
            for layer in scene.view_layers
        ],
        "caption_nodes": caption_nodes,
        "performer_material_aovs": dict(materials),
        "actor_pngs": pngs,
        "cryptomatte_nodes": crypto_nodes,
        "saved_blend": False,
        "rendered": False,
        "cache_modified": False,
        "limits": [
            "Left/right mask halves are spatial diagnostics, not semantic character segmentation; inspect against the beauty frame.",
            "AOV graph inventory lists active scene material nodes and all linked upstream sockets; it does not evaluate opacity by rendering.",
        ],
    }
    path = args.output_dir / "caption-matte-probe.json"
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf8",
    )
    print("CAPTION_MATTE_PROBE_COMPLETE", path, flush=True)


if __name__ == "__main__":
    main()
