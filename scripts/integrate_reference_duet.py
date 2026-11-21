"""Integrate the tested hall and bounded character study; preserve animation."""

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from genshin_material_adapt import apply as character_adapt
from hesperides_reference_rebuild import stage_grade
from mmd_clear_light_revision import math_node
from mmd_hesperides_stage import area, compositor


def import_hall(scene, path):
    root = bpy.data.objects["Duet | selected Hesperides stage"]
    offset = root.location.copy()
    old = [root, *root.children_recursive]
    if any(o.get("performer_id") for o in old):
        raise RuntimeError("Actor found under stage root")
    for obj in old:
        bpy.data.objects.remove(obj, do_unlink=True)
    for obj in scene.objects:
        if obj.type == "LIGHT" or any(
            s in obj.name for s in ["exterior snow", "subtle winter air"]
        ):
            obj.hide_render = True
    with bpy.data.libraries.load(str(path), link=False) as (source, loaded):
        loaded.objects = [
            name for name in source.objects if name != "Reference | fitted camera"
        ]
        loaded.worlds = [
            name for name in source.worlds if name.startswith("Reference | cyan sky")
        ]
    objects = [o for o in loaded.objects if o and o.type != "CAMERA"]
    root = bpy.data.objects.new(
        "Duet | selected Hesperides stage | reference rebuild", None
    )
    scene.collection.objects.link(root)
    for obj in objects:
        scene.collection.objects.link(obj)
    # Appended objects have unevaluated matrix_world values until they are
    # linked and the dependency graph is updated. Parenting before this update
    # collapsed lights/probes onto the root even though their local transforms
    # were valid in the stage source file.
    bpy.context.view_layer.update()
    matrices = {obj: obj.matrix_world.copy() for obj in objects}
    for obj in objects:
        if obj.parent not in objects:
            obj.parent = root
            obj.matrix_world = matrices[obj]
    root.location = offset
    bpy.context.view_layer.update()
    scene.world = loaded.worlds[0]
    return {
        "source": str(path),
        "translation": list(offset),
        "objects": len(objects),
        "original_camera_imported": False,
    }


def actor_lights(scene):
    result = []
    for actor in ["aksiniya", "aether"]:
        collection = bpy.data.collections.new("Reference duet | receivers | " + actor)
        scene.collection.children.link(collection)
        for obj in scene.objects:
            if obj.type == "MESH" and obj.get("performer_id") == actor:
                collection.objects.link(obj)
        for label, loc, power, rgb, size in [
            ("key", (-2.5, -3.5, 4), 100, (1, 0.96, 0.94), 2.4),
            ("fill", (2.5, -1, 2.3), 25, (0.68, 0.79, 1), 3),
            ("rim", (1, 2, 3.5), 65, (0.75, 0.85, 1), 2),
        ]:
            light = area(
                "Reference duet | " + actor + " | " + label,
                loc,
                (0, 0, 1.4),
                power,
                rgb,
                size,
            )
            light.light_linking.receiver_collection = collection
            result.append(light.name)
    return result


def protected_compositor(scene, settings):
    name = "ReferenceDuetActor"
    layer = scene.view_layers[0]
    aov = layer.aovs.add()
    aov.name, aov.type = name, "VALUE"
    actor_materials = {
        m
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id")
        for m in o.data.materials
        if m and m.node_tree
    }
    for mat in actor_materials:
        out = mat.node_tree.nodes.new("ShaderNodeOutputAOV")
        out.aov_name = name
        out.inputs["Value"].default_value = 1
    layer.update_render_passes()
    compositor(scene, settings)
    stage_grade(scene, settings)
    tree = scene.compositing_node_group
    output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    background = output.inputs[0].links[0].from_socket
    layers = next(n for n in tree.nodes if n.type == "R_LAYERS")
    split = tree.nodes.new("CompositorNodeSeparateColor")
    split.mode = "RGB"
    tree.links.new(layers.outputs["Image"], split.inputs[0])
    maximum = math_node(
        tree,
        "MAXIMUM",
        math_node(tree, "MAXIMUM", split.outputs[0], split.outputs[1]),
        split.outputs[2],
    )
    distance = math_node(tree, "MAXIMUM", math_node(tree, "SUBTRACT", maximum, 0.78), 0)
    mapped = math_node(
        tree,
        "ADD",
        0.78,
        math_node(
            tree,
            "MULTIPLY",
            math_node(
                tree,
                "SUBTRACT",
                1,
                math_node(
                    tree,
                    "POWER",
                    2.718281828459045,
                    math_node(tree, "DIVIDE", distance, -0.20),
                ),
            ),
            0.20,
        ),
    )
    scale = math_node(
        tree,
        "DIVIDE",
        math_node(tree, "MINIMUM", maximum, mapped),
        math_node(tree, "MAXIMUM", maximum, 0.000001),
    )
    combine = tree.nodes.new("CompositorNodeCombineColor")
    combine.mode = "RGB"
    for i in range(3):
        tree.links.new(
            math_node(tree, "MULTIPLY", split.outputs[i], scale), combine.inputs[i]
        )
    tree.links.new(split.outputs[3], combine.inputs[3])
    mix = tree.nodes.new("ShaderNodeMixRGB")
    mix.name = "Reference duet | protect actors from stage grade"
    tree.links.new(layers.outputs[name], mix.inputs[0])
    tree.links.new(background, mix.inputs[1])
    tree.links.new(combine.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], output.inputs[0])
    return name


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--author-library", type=Path, required=True)
    parser.add_argument("--user-library", type=Path, required=True)
    parser.add_argument("--aksiniya-assets", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    source = bpy.data.filepath
    scene = bpy.context.scene
    assert scene.rigidbody_world is None and scene.get("production_duet_complete_scene")
    started = time.perf_counter()
    scene.frame_set(4200)
    settings = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "presets/stages/hesperides-ray-reference-v1.json"
        ).read_text(encoding="utf-8")
    )
    hall = import_hall(scene, args.stage)
    character = character_adapt(
        scene, args.author_library, args.user_library, args.aksiniya_assets
    )
    lights = actor_lights(scene)
    mask = protected_compositor(scene, settings)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_raytracing = True
    scene.eevee.ray_tracing_method = "SCREEN"
    scene.eevee.taa_render_samples = 32
    scene.eevee.shadow_pool_size = "1024"
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.use_sequencer = False
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    # Bake only fixed architecture; actor-linked lights cannot illuminate it.
    hidden = [
        (o, o.hide_render)
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id")
    ]
    for o, _old in hidden:
        o.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    volume = next(
        o
        for o in scene.objects
        if o.type == "LIGHT_PROBE" and o.data.type == "VOLUME" and not o.hide_render
    )
    volume.select_set(True)
    bpy.context.view_layer.objects.active = volume
    bpy.context.view_layer.update()
    if bpy.ops.object.lightprobe_cache_bake(subset="SELECTED") != {"FINISHED"}:
        raise RuntimeError("Static GI bake failed")
    for o, value in hidden:
        o.hide_render = value
    scene["reference_duet_revision"] = "hall-ref-v1-genshin-face-study-v1"
    scene.frame_set(4140)
    bpy.ops.file.pack_all()
    project = args.output_dir / "Franken_Duet_Reference_Genshin.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    for frame in [4200, 4420]:
        scene.frame_set(frame)
        scene.render.filepath = str(args.output_dir / f"preview-{frame}.png")
        bpy.ops.render.render(write_still=True)
    (args.output_dir / "integration-report.json").write_text(
        json.dumps(
            {
                "source": source,
                "project": str(project),
                "hall": hall,
                "character_adaptation": character,
                "actor_lights": lights,
                "actor_mask": mask,
                "static_gi_excludes_actors": True,
                "camera_changed": False,
                "physics_changed": False,
                "render_scope": "5 seconds planned; not full-song output",
                "seconds": time.perf_counter() - started,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("REFERENCE_DUET_INTEGRATED", flush=True)


if __name__ == "__main__":
    main()
