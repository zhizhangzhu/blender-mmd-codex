"""Compare native full and cropped renders before considering local revisions."""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy
import numpy as np


def actor_rectangle(scene, padding=80):
    width, height = scene.render.resolution_x, scene.render.resolution_y
    graph = bpy.context.evaluated_depsgraph_get()
    camera = scene.camera.evaluated_get(graph)
    projection = camera.calc_matrix_camera(graph, x=width, y=height)
    projected = []
    for obj in scene.objects:
        if obj.type != "MESH" or obj.get("performer_id") != "aether":
            continue
        if not any(mod.type == "ARMATURE" for mod in obj.modifiers):
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            coords = np.ones((len(mesh.vertices), 4), dtype=np.float64)
            xyz = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
            mesh.vertices.foreach_get("co", xyz)
            coords[:, :3] = xyz.reshape(-1, 3)
            matrix = np.asarray(
                projection @ camera.matrix_world.inverted() @ evaluated.matrix_world
            )
            clip = coords @ matrix.T
            front = clip[:, 3] > 0.001
            if not front.all():
                return (0, 0, width, height)
            screen = clip[:, :2] / clip[:, 3:4] * 0.5 + 0.5
            projected.append(screen)
        finally:
            evaluated.to_mesh_clear()
    if not projected:
        raise RuntimeError("No Aether skinned mesh")
    points = np.concatenate(projected)
    # Returned coordinates use image convention: origin at top left.
    x0 = int(np.floor(points[:, 0].min() * width)) - padding
    x1 = int(np.ceil(points[:, 0].max() * width)) + padding
    y0 = int(np.floor((1 - points[:, 1].max()) * height)) - padding
    y1 = int(np.ceil((1 - points[:, 1].min()) * height)) + padding
    return (max(0, x0), max(0, y0), min(width, x1), min(height, y1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame", type=int, default=601)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    scene.frame_set(args.frame)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_sequencer = False
    rectangle = actor_rectangle(scene)
    records = []
    for cropped in [False, True, True]:
        scene.render.use_border = cropped
        scene.render.use_crop_to_border = cropped
        x0, y0, x1, y1 = rectangle
        scene.render.border_min_x = x0 / scene.render.resolution_x
        scene.render.border_max_x = x1 / scene.render.resolution_x
        scene.render.border_min_y = 1 - y1 / scene.render.resolution_y
        scene.render.border_max_y = 1 - y0 / scene.render.resolution_y
        scene.render.filepath = str(
            args.output_dir / f"{'region' if cropped else 'full'}-{len(records)}.png"
        )
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        records.append({"cropped": cropped, "seconds": time.perf_counter() - started})
    (args.output_dir / "region-probe.json").write_text(
        json.dumps(
            {
                "frame": args.frame,
                "rectangle": rectangle,
                "timings": records,
                "pixel_fraction": (x1 - x0) * (y1 - y0) / (1920 * 1080),
                "status": "Native render comparison; not approved for production compositing",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
