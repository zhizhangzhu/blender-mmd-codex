"""Render the user's WuWa hair example and controlled HM/HN input removals."""

import argparse
import json
import sys
import warnings
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import aim


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    source = bpy.data.filepath
    scene = bpy.context.scene
    objects = [o for o in scene.objects if o.type == "MESH"]
    bpy.context.view_layer.update()
    points = [o.matrix_world @ Vector(v) for o in objects for v in o.bound_box]
    minimum = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    maximum = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (minimum + maximum) * 0.5
    extent = max(maximum - minimum)
    camera_data = bpy.data.cameras.new("WuWa study | camera")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    camera.location = center + Vector((0, -2.2 * extent, 0.08 * extent))
    aim(camera, center)
    camera_data.lens = 50
    camera_data.clip_end = max(100, extent * 10)
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.eevee.taa_render_samples = 32
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    world = bpy.data.worlds.new("WuWa study | neutral")
    world.use_nodes = True
    scene.world = world
    next(n for n in world.node_tree.nodes if n.type == "BACKGROUND").inputs[
        "Color"
    ].default_value = (0.025, 0.03, 0.045, 1)
    groups = [
        (m, n)
        for m in bpy.data.materials
        if m.node_tree
        for n in m.node_tree.nodes
        if n.type == "GROUP"
        and n.node_tree
        and n.node_tree.name.startswith("hair高光(wuwa3.0)")
    ]
    if not groups:
        raise RuntimeError("No intended hair group found")
    inputs = []
    for mat, node in groups:
        inputs.append(
            {
                "material": mat.name,
                "inputs": {
                    name: {
                        "links": [
                            {
                                "node": l.from_node.name,
                                "image": l.from_node.image.name
                                if l.from_node.type == "TEX_IMAGE" and l.from_node.image
                                else None,
                                "socket": l.from_socket.name,
                            }
                            for l in node.inputs[name].links
                        ],
                        "default": list(node.inputs[name].default_value),
                    }
                    for name in ["HM", "HN"]
                },
            }
        )
    images = [
        {
            "name": im.name,
            "filepath": im.filepath,
            "color_space": im.colorspace_settings.name,
            "alpha_mode": im.alpha_mode,
            "packed": bool(im.packed_file),
            "size": list(im.size),
        }
        for im in bpy.data.images
        if im.source == "FILE"
    ]
    scene.render.filepath = str(args.output_dir / "native-inputs.png")
    bpy.ops.render.render(write_still=True)
    for name, neutral in [("HM", (0, 0, 0)), ("HN", (0.5, 0.5, 1))]:
        originals = []
        for _mat, node in groups:
            socket = node.inputs[name]
            originals.append(
                (
                    node,
                    socket.default_value[:],
                    [(l.from_socket, l.to_socket) for l in socket.links],
                )
            )
            for link in list(socket.links):
                node.id_data.links.remove(link)
            socket.default_value = neutral
        scene.render.filepath = str(args.output_dir / f"control-neutral-{name}.png")
        bpy.ops.render.render(write_still=True)
        for node, value, links in originals:
            node.inputs[name].default_value = value
            for src, dest in links:
                node.id_data.links.new(src, dest)
    scene.render.filepath = str(args.output_dir / "native-inputs.png")
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(
        filepath=str(args.output_dir / "WuWa_Hair_Input_Study.blend")
    )
    (args.output_dir / "hair-study.json").write_text(
        json.dumps(
            {
                "source": source,
                "group": "hair高光(wuwa3.0)",
                "credit": "三一七片的谎言; user-supplied example mesh and maps, exact character attribution not independently verified",
                "material_inputs": inputs,
                "images": images,
                "bounds": [list(minimum), list(maximum)],
                "scope": "hair preset controlled still study; not transferred to the Genshin duet",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("WUWA_HAIR_STUDY_COMPLETE", len(groups), flush=True)


if __name__ == "__main__":
    main()
