"""Bounded Blender/Goo foundation controls in factory scenes; never load production."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from study_goo_feature_mechanisms import mat, scene

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--reopen", action="store_true")
args = parser.parse_args(
    sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
)
assert bpy.app.build_hash.decode() == "0051aee03764"
OUT = Path("D:/codex/output/Goo-MMD-Eight-Foundations-2026-11-18/controls")
RAW = Path("D:/codex/temp/Goo-MMD-Eight-Foundations-2026-11-18/linear")
RAW.mkdir(parents=True, exist_ok=True)


def save(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def render(label):
    s = bpy.context.scene
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.render.filepath = str(RAW / (label + ".exr"))
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(s.render.filepath, check_existing=False)
    pixels = np.array(image.pixels[:], dtype=np.float32)
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "16"
    image.save_render(str(OUT / (label + ".png")), scene=s)
    bpy.data.images.remove(image)
    return pixels


if args.reopen:
    bpy.ops.wm.open_mainfile(
        filepath=str(OUT / "Normal_Edit_Control.blend"),
        use_scripts=False,
        load_ui=False,
    )
    repeat = render("normal-edit-reopened")
    im = bpy.data.images.load(str(RAW / "normal-edit.exr"), check_existing=False)
    difference = float(np.abs(np.array(im.pixels[:], dtype=np.float32) - repeat).max())
    bpy.data.images.remove(im)
    assert difference < 1e-6
    save(
        OUT / "reopen-verification.json",
        {
            "max_abs_linear_rgba_difference": difference,
            "passed": True,
            "production_loaded": False,
        },
    )
    print("FOUNDATION_REOPEN_COMPLETE", difference, flush=True)
    raise SystemExit(0)

OUT.mkdir(parents=True, exist_ok=False)
images = {}
normal_results = {}
for use_modifier in (False, True):
    s = scene(900, 430)
    s.eevee.taa_render_samples = 32
    s.camera.location = (0, -7, 3.7)
    s.camera.rotation_euler = (
        (Vector((0, 0, 1)) - s.camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    s.camera.data.ortho_scale = 5
    bpy.ops.object.light_add(type="SUN")
    lamp = bpy.context.object
    lamp.data.energy = 2
    lamp.rotation_euler = (0.4, -0.45, 0)
    objects = []
    for index, x in enumerate((-1.12, 1.12)):
        material, emission = mat(
            "Half Lambert" if index == 0 else "World shading normal RGB"
        )
        t = material.node_tree
        if index == 0:
            info = t.nodes.new("ShaderNodeShaderInfo")
            t.links.new(info.outputs["Half-lambert factor"], emission.inputs["Color"])
        else:
            geometry = t.nodes.new("ShaderNodeNewGeometry")
            encode = t.nodes.new("ShaderNodeVectorMath")
            encode.operation = "MULTIPLY_ADD"
            encode.inputs[1].default_value = (0.5, 0.5, 0.5)
            encode.inputs[2].default_value = (0.5, 0.5, 0.5)
            t.links.new(geometry.outputs["Normal"], encode.inputs[0])
            t.links.new(encode.outputs["Vector"], emission.inputs["Color"])
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=48, ring_count=32, radius=0.88, location=(x, 0, 1)
        )
        ob = bpy.context.object
        ob.data.materials.append(material)
        for polygon in ob.data.polygons:
            polygon.use_smooth = True
        if use_modifier:
            bpy.ops.object.empty_add(location=ob.location + Vector((0, -4, 4)))
            target = bpy.context.object
            modifier = ob.modifiers.new("Research directional normal", "NORMAL_EDIT")
            modifier.mode = "DIRECTIONAL"
            modifier.target = target
            modifier.use_direction_parallel = True
            modifier.mix_factor = 0.65
            modifier.no_polynors_fix = True
        objects.append(ob)
    bpy.context.view_layer.update()
    shape_errors = []
    normal_means = []
    for ob in objects:
        evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        base = np.array([v.co[:] for v in ob.data.vertices])
        positions = np.array([v.co[:] for v in mesh.vertices])
        shape_errors.append(float(np.abs(base - positions).max()))
        normal_means.append(
            np.array([n.vector[:] for n in mesh.corner_normals]).mean(axis=0).tolist()
        )
        evaluated.to_mesh_clear()
    label = "normal-edit" if use_modifier else "default-normal"
    images[label] = render(label).reshape(430, 900, 4)
    normal_results[label] = {
        "evaluated_vertex_max_difference": shape_errors,
        "mean_corner_normals": normal_means,
    }
    assert max(shape_errors) == 0
    if use_modifier:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Normal_Edit_Control.blend"))

difference = np.abs(images["normal-edit"] - images["default-normal"])
normal_results["max_abs_linear_rgb_difference_left_half_lambert"] = float(
    difference[:, :450, :3].max()
)
normal_results["max_abs_linear_rgb_difference_right_normal_debug"] = float(
    difference[:, 450:, :3].max()
)
assert normal_results["max_abs_linear_rgb_difference_right_normal_debug"] > 0.01
# A negative result on Half-Lambert must be recorded rather than forced to pass.

scene()
material, _ = mat("Shared material")
group = bpy.data.node_groups.new("Shared nested group", "ShaderNodeTree")
node = material.node_tree.nodes.new("ShaderNodeGroup")
node.node_tree = group
bpy.ops.mesh.primitive_cube_add()
first = bpy.context.object
first.data.materials.append(material)
second = first.copy()
bpy.context.collection.objects.link(second)
sharing = {
    "object_copy_shares_mesh": second.data == first.data,
    "object_copy_shares_material": second.data.materials[0] == first.data.materials[0],
}
second.data = first.data.copy()
second.data.materials[0] = material.copy()
second_group_node = next(
    n for n in second.data.materials[0].node_tree.nodes if n.type == "GROUP"
)
sharing["mesh_and_material_copies_still_share_nested_group"] = (
    second_group_node.node_tree == group
)
second_group_node.node_tree = group.copy()
sharing["explicit_group_copy_is_independent"] = second_group_node.node_tree != group
assert all(sharing.values())

scene()
bpy.ops.object.armature_add(enter_editmode=True)
rig = bpy.context.object
bone_name = rig.data.edit_bones[0].name
bpy.ops.object.mode_set(mode="OBJECT")
rig.pose.bones[bone_name].rotation_mode = "XYZ"
rig.pose.bones[bone_name].rotation_euler.y = math.radians(60)
coordinates = []
for order in (("DISPLACE", "ARMATURE"), ("ARMATURE", "DISPLACE")):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    weights = ob.vertex_groups.new(name=bone_name)
    weights.add(list(range(len(ob.data.vertices))), 1, "REPLACE")
    for kind in order:
        mod = ob.modifiers.new(kind, kind)
        if kind == "ARMATURE":
            mod.object = rig
        else:
            mod.direction = "X"
            mod.strength = 0.5
            mod.mid_level = 0
    bpy.context.view_layer.update()
    evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    coordinates.append(np.array([v.co[:] for v in mesh.vertices]))
    evaluated.to_mesh_clear()
order_difference = float(np.linalg.norm(coordinates[0] - coordinates[1], axis=1).max())
assert order_difference > 0.1

save(
    OUT / "measurements.json",
    {
        "version": bpy.app.version_string,
        "build_hash": bpy.app.build_hash.decode(),
        "normal_edit": normal_results,
        "data_sharing": sharing,
        "modifier_order": {
            "orders": [["DISPLACE", "ARMATURE"], ["ARMATURE", "DISPLACE"]],
            "max_evaluated_vertex_distance": order_difference,
            "setup": "Single fully weighted cube, one bone rotated 60deg on Y, local X Displace strength0.5/no texture/midlevel0",
        },
        "production_loaded": False,
        "video_created": False,
        "limits": "Factory sphere/cube controls only; no skinning of real characters, animation, physical simulation or plugin conversion",
    },
)
print("FOUNDATION_CONTROLS_COMPLETE", json.dumps(normal_results), flush=True)
