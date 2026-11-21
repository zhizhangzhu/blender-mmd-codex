"""Render textured geometry or ray-cast feature positions for reference fitting."""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def setup(scene, pose=None):
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_sequencer = False
    scene.render.use_compositing = False
    scene.eevee.taa_render_samples = 16
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    world = bpy.data.worlds.new("Reference fit | neutral background")
    world.use_nodes = True
    next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs[
        "Color"
    ].default_value = (0.02, 0.25, 0.5, 1)
    scene.world = world
    for obj in scene.objects:
        if obj.type == "MESH" and any(
            m and m.name == "mat_103" for m in obj.data.materials
        ):
            obj.hide_render = True
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        tree = mat.node_tree
        output = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL")
        if mat.name == "mat_89":
            surface = tree.nodes.new("ShaderNodeBsdfTransparent").outputs[0]
        else:
            bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
            emission = tree.nodes.new("ShaderNodeEmission")
            base = bsdf.inputs["Base Color"]
            if base.is_linked:
                tree.links.new(base.links[0].from_socket, emission.inputs[0])
            else:
                emission.inputs[0].default_value = base.default_value
            surface = emission.outputs[0]
            if bsdf.inputs["Alpha"].is_linked:
                alpha = tree.nodes.new("ShaderNodeMixShader")
                tree.links.new(
                    bsdf.inputs["Alpha"].links[0].from_socket, alpha.inputs[0]
                )
                tree.links.new(
                    tree.nodes.new("ShaderNodeBsdfTransparent").outputs[0],
                    alpha.inputs[1],
                )
                tree.links.new(surface, alpha.inputs[2])
                surface = alpha.outputs[0]
        tree.links.new(surface, output.inputs["Surface"])
    camera_data = bpy.data.cameras.new("Reference fit | camera")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.sensor_width = 36
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.clip_end = 300
    camera_data.lens = 35
    camera.location = (3, -30, 6)
    camera.rotation_euler = (
        (Vector((0, 25, 9)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    if pose:
        camera.matrix_world = Matrix(pose["camera_to_world_blender"])
        camera_data.lens = pose["lens_mm"]
    bpy.context.view_layer.update()
    return camera


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--matches", type=Path)
    parser.add_argument("--pose", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    pose = json.loads(args.pose.read_text(encoding="utf-8")) if args.pose else None
    camera = setup(scene, pose)
    if not args.matches:
        scene.render.filepath = str(args.output_dir / "geometry.png")
        bpy.ops.render.render(write_still=True)
        (args.output_dir / "camera.json").write_text(
            json.dumps(
                {
                    "camera_to_world_blender": [
                        list(row) for row in camera.matrix_world
                    ],
                    "lens_mm": camera.data.lens,
                    "width": 1280,
                    "height": 720,
                    "sensor_width_mm": 36,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    else:
        rows = json.loads(args.matches.read_text(encoding="utf-8"))["matches"]
        graph = bpy.context.evaluated_depsgraph_get()
        projection = camera.calc_matrix_camera(graph, x=1280, y=720)
        inverse = projection.inverted()
        results = []
        for row in rows:
            x, y = row["seed_pixel"]
            near = inverse @ Vector(
                (2 * (x + 0.5) / 1280 - 1, 1 - 2 * (y + 0.5) / 720, -1, 1)
            )
            near /= near.w
            direction = (camera.matrix_world.to_3x3() @ near.xyz).normalized()
            origin = camera.matrix_world.translation.copy()
            # Ignore fully transparent windows and fake ray planes.
            for _attempt in range(8):
                hit, point, _normal, index, obj, _matrix = scene.ray_cast(
                    graph, origin, direction, distance=300
                )
                if not hit:
                    break
                mat = (
                    obj.data.materials[obj.data.polygons[index].material_index]
                    if index < len(obj.data.polygons)
                    else None
                )
                if mat and mat.name not in {"mat_89", "mat_103"}:
                    results.append(
                        {
                            **row,
                            "world": list(point),
                            "object": obj.name,
                            "material": mat.name,
                        }
                    )
                    break
                origin = point + direction * 0.001
        (args.output_dir / "world-matches.json").write_text(
            json.dumps({"matches": results}, indent=2), encoding="utf-8"
        )
        print("WORLD_FEATURES", len(results), flush=True)


if __name__ == "__main__":
    main()
