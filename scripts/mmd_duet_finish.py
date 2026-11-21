"""Build the full-song duet from portable physics and the selected existing hall.

Preserves authored camera animation; stage-study cameras are never imported.
"""

import argparse
import copy
import json
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_final_scene import retime_actions
from mmd_half_lambert import apply_half_lambert
from mmd_hesperides_stage import compositor
from mmd_look_upgrade import upgrade
from mmd_outlines import apply_outlines
from mmd_surface_refine import hair_sheen
from mmd_tutorial_lab import toon_edges

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def head_controller(scene, arm):
    """Read posed bone matrices directly; no extra full-song baking needed."""
    head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
    canonical = head.bone.matrix_local.to_3x3().inverted() @ Vector((0, 0, 1))
    rotation = arm.matrix_world.to_quaternion().to_matrix()
    obj = bpy.data.objects.new("Duet | head axis | " + arm.get("performer_id"), None)
    scene.collection.objects.link(obj)
    obj["up"] = [0.0, 0.0, 1.0]
    for row in range(3):
        curve = obj.driver_add('["up"]', row)
        terms = []
        for middle in range(3):
            for column in range(3):
                coefficient = rotation[row][middle] * canonical[column]
                if abs(coefficient) < 1e-7:
                    continue
                name = f"m{middle}{column}"
                variable = curve.driver.variables.new()
                variable.name = name
                variable.targets[0].id = arm
                variable.targets[
                    0
                ].data_path = f"pose.bones[{json.dumps(head.name, ensure_ascii=False)}].matrix[{middle}][{column}]"
                terms.append(f"{coefficient:.10f}*{name}")
        curve.driver.expression = "+".join(terms) or "0"
    return obj


def actor_look(scene):
    categories = {}
    for mat in list(bpy.data.materials):
        actor = mat.get("performer_id")
        if not actor or not mat.node_tree or not mat.node_tree.nodes.get("mmd_shader"):
            continue
        override = None
        name = mat.get("source_mmd_material_name", mat.name).rstrip("+")
        if actor == "aether":
            clean = name.removesuffix(".001")
            override = next(
                (
                    category
                    for category, names in {
                        "skin": {"面1", "面2", "肌", "口舌"},
                        "hair": {"发"},
                        "eye": {"目", "目白", "目星", "齿"},
                        "ink": {"眉", "睫", "二重", "> <"},
                        "trim": {"发饰", "耳饰"},
                    }.items()
                    if clean in names
                ),
                "cloth",
            )
        categories[mat.name] = upgrade(mat, override)
    materials = [m for m in bpy.data.materials if m.get("look_category")]
    response = load_json(ROOT / "presets/quality/half-lambert-v1.json")
    apply_half_lambert(materials, response)
    for mat in materials:
        if mat.get("performer_id") == "aether" and mat["look_category"] == "hair":
            ramp = mat.node_tree.nodes["Look v3 | Soft toon bands"].color_ramp
            for element, color in zip(
                ramp.elements,
                [(0.58, 0.48, 0.40, 1), (0.94, 0.87, 0.70, 1), (1.05, 1.02, 0.91, 1)],
            ):
                element.color = color
    for arm in [
        o for o in scene.objects if o.type == "ARMATURE" and o.get("performer_id")
    ]:
        actor = arm.get("performer_id")
        actor_materials = [m for m in materials if m.get("performer_id") == actor]
        controller = head_controller(scene, arm)
        for mat in actor_materials:
            if mat.get("look_category") == "hair":
                settings = load_json(
                    ROOT / "presets/quality/surface-refinement-v1.json"
                )["hair"]
                if actor == "aether":
                    settings.update(strength=0.16, color=[1.0, 0.95, 0.80])
                hair_sheen(mat, controller, settings, None)
        toon_edges(actor_materials, arm.parent)
    ink = load_json(ROOT / "presets/quality/outlines-v2-face-black.json")
    for mat in materials:
        if mat.get("performer_id") == "aether" and mat.get(
            "source_mmd_material_name"
        ) in {"面1", "面2"}:
            ink["material_overrides"][mat.name] = copy.deepcopy(
                ink["material_overrides"]["颜"]
            )
    outlines = apply_outlines(scene, ink)
    # Aether's atlas has different UVs; only darken his dedicated brow/lash layers.
    from mmd_face_ink import mix_surface

    for mat in materials:
        if mat.get("performer_id") == "aether" and mat.get("look_category") == "ink":
            mix_surface(mat, "Duet brow and lash contrast", 1, [0.5] * 3, True)
    return {"categories": categories, "outlines": outlines}


def import_stage(scene, path):
    with bpy.data.libraries.load(str(path), link=False) as (source, loaded):
        loaded.objects = [n for n in source.objects if "scene-study camera" not in n]
        loaded.worlds = [n for n in source.worlds if n.startswith("Hall | cold sky")]
    objects = [o for o in loaded.objects if o and o.type != "CAMERA"]
    for obj in objects:
        scene.collection.objects.link(obj)
    scene.world = loaded.worlds[0]
    bpy.context.view_layer.update()
    # Ignore transparent helper planes when measuring the walkable surface.
    vertices, triangles = [], []
    for obj in objects:
        if obj.type != "MESH" or obj.hide_render or not obj.data.polygons:
            continue
        if any(
            m and m.name.startswith(("mat_103", "mat_89", "Hall |"))
            for m in obj.data.materials
        ):
            continue
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        obj.data.calc_loop_triangles()
        triangles.extend(
            tuple(offset + index for index in p.vertices)
            for p in obj.data.loop_triangles
        )
    bvh = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
    position, normal, _index, _distance = bvh.ray_cast(
        Vector((0, -15, 8)), Vector((0, 0, -1)), 20
    )
    if position is None or normal.z < 0.9:
        raise RuntimeError(
            "No verified horizontal aisle floor: " + str((position, normal))
        )
    root = bpy.data.objects.new("Duet | selected Hesperides stage", None)
    scene.collection.objects.link(root)
    for obj in objects:
        if obj.parent not in objects:
            matrix = obj.matrix_world.copy()
            obj.parent = root
            obj.matrix_world = matrix
    root.location = (0, 15, -position.z - 0.005)
    return {
        "source": str(path),
        "objects": len(objects),
        "floor_point": list(position),
        "floor_normal": list(normal),
        "translation": list(root.location),
    }


def snow(scene):
    """Sparse exterior flakes, never a curtain across the performers' faces."""
    rng = random.Random(542)
    vertices, faces = [], []
    for _ in range(750):
        x, y, z = rng.uniform(-23, 23), rng.uniform(57, 70), rng.uniform(-4, 38)
        radius = rng.uniform(0.035, 0.09)
        start = len(vertices)
        vertices.extend(
            [
                (x - radius, y, z),
                (x + radius, y, z),
                (x, y, z + 2 * radius),
                (x, y + radius, z + radius),
            ]
        )
        faces.extend(
            [
                tuple(start + i for i in f)
                for f in [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
            ]
        )
    mesh = bpy.data.meshes.new("Duet | exterior snow")
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new(mesh.name, mesh)
    scene.collection.objects.link(obj)
    mat = bpy.data.materials.new("Duet | snow glints")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs[0].default_value = (0.65, 0.78, 1.0, 1)
    emission.inputs[1].default_value = 1.5
    mat.node_tree.links.new(
        emission.outputs[0],
        next(n for n in nodes if n.type == "OUTPUT_MATERIAL").inputs[0],
    )
    mesh.materials.append(mat)
    # Cyclic translation keeps enough flakes outside the windows throughout.
    obj.location.z = 0
    obj.keyframe_insert(data_path="location", frame=1)
    obj.location.z = -15
    obj.keyframe_insert(data_path="location", frame=1801)
    for curve in obj.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
        curve.modifiers.new("CYCLES")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--qa-frames",
        type=int,
        nargs="+",
        default=[1, 600, 2100, 4200, 6300, 8400, 10500, 11899],
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    assert scene.rigidbody_world is None
    assert (
        len(
            [o for o in scene.objects if o.type == "ARMATURE" and o.get("performer_id")]
        )
        == 2
    )
    start = time.time()
    source = bpy.data.filepath
    camera = scene.camera
    for obj in list(scene.objects):
        if obj.name.startswith("Draft "):
            bpy.data.objects.remove(obj, do_unlink=True)
    print("DUET_RETIME_START", flush=True)
    retimed = retime_actions(450, 2)
    scene.render.fps = 60
    scene.frame_start, scene.frame_end = 1, 11899
    scene.frame_set(1)
    print("DUET_RETIME_DONE", retimed, flush=True)
    look = actor_look(scene)
    print("DUET_LOOK_DONE", flush=True)
    stage = import_stage(scene, args.stage)
    scene.camera = camera
    scene.camera.data.clip_end = 300
    snow(scene)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 48
    scene.eevee.use_raytracing = True
    scene.eevee.shadow_ray_count = 2
    scene.eevee.fast_gi_quality = 0.5
    scene.eevee.fast_gi_step_count = 8
    scene.eevee.volumetric_samples = 32
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.use_sequencer = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0
    compositor(
        scene, load_json(ROOT / "presets/stages/hesperides-winter-wedding-v1.json")
    )
    project = load_json(ROOT / "presets/projects/franken-duet-full-v1.json")
    if scene.sequence_editor:
        scene.sequence_editor_clear()
    editor = scene.sequence_editor_create()
    editor.strips.new_sound(
        "Original vocal FLAC", project["audio"]["bgm"], channel=1, frame_start=1
    )
    scene["production_duet_complete_scene"] = True
    scene["production_camera"] = (
        "Tottoko 173 cm authored VMD; motion preserved; full artistic correction deferred by user"
    )
    scene["production_physics"] = (
        "Both native rigs visually baked with preroll; runtime rigidbody removed"
    )
    scene["production_timebase"] = (
        "output frame 1 = baked frame 450 = VMD frame 329; 30 to 60 fps with handles"
    )
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    bpy.ops.file.pack_all()
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(
        filepath=str(args.output_dir / "Franken_Duet_Full.blend")
    )
    report = {
        "source": source,
        "stage": stage,
        "look": look,
        "retimed_curves": retimed,
        "fps": 60,
        "frames": 11899,
        "resolution": [1920, 1080],
        "bgm": project["audio"]["bgm"],
        "camera_changed": False,
        "timebase_source_baked_first": 450,
        "qa_frames": args.qa_frames,
    }
    (args.output_dir / "scene-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    scene.render.resolution_percentage = 50
    scene.eevee.taa_render_samples = 32
    for frame in args.qa_frames:
        scene.frame_set(frame)
        scene.render.filepath = str(args.output_dir / f"qa-{frame:05d}.png")
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print("DUET_QA_FRAME", frame, round(time.time() - t, 3), flush=True)
    print("DUET_SCENE_READY", time.time() - start, flush=True)


if __name__ == "__main__":
    main()
