"""Build original two-rig static test fixtures, not production MMD characters.

Blender-only, explicit fresh output. No third-party models or shaders are copied.
"""

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.studio_scene_contract import digest


def mesh(name, kind, location, scale, material, rig=None, bone="上半身"):
    if kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=location)
    elif kind == "plane":
        bpy.ops.mesh.primitive_plane_add(size=2, location=location)
    else:
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    if kind == "sphere":
        for face in obj.data.polygons:
            face.use_smooth = True
    if rig:
        group = obj.vertex_groups.new(name=bone)
        group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
        mod = obj.modifiers.new("BoundRig", "ARMATURE")
        mod.object = rig
    return obj


def material(name, light, dark=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    diffuse = tree.nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1)
    rgb = tree.nodes.new("ShaderNodeShaderToRGB")
    tree.links.new(diffuse.outputs[0], rgb.inputs[0])
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.26
    ramp.color_ramp.elements[0].color = dark or tuple(c * 0.38 for c in light[:3]) + (1,)
    ramp.color_ramp.elements[1].position = 0.56
    ramp.color_ramp.elements[1].color = light
    tree.links.new(rgb.outputs[0], ramp.inputs[0])
    tint = tree.nodes.new("ShaderNodeMixRGB")
    tint.name = "ClothTint"
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1
    tint.inputs[2].default_value = (1, 1, 1, 1)
    tree.links.new(ramp.outputs[0], tint.inputs[1])
    emission = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(tint.outputs[0], emission.inputs[0])
    tree.links.new(emission.outputs[0], output.inputs["Surface"])
    return mat


def rig(name):
    data = bpy.data.armatures.new(name + "Data")
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    body = data.edit_bones.new("上半身")
    body.head, body.tail = (0, 0, 0), (0, 0, 1.35)
    head = data.edit_bones.new("頭")
    head.head, head.tail, head.parent = (0, 0, 1.35), (0, 0, 2.1), body
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    return obj


def make(output, variant):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "BenchScene" + variant
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 640, 360, 100
    scene.eevee.taa_render_samples = 16
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("NeutralWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.09, 0.12, 0.18, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.3
    scene.world = world
    rig("00_UnrelatedFirstRig_" + variant)
    actors = []
    for n, x in enumerate((-0.72, 0.72)):
        prefix = ("ActorOne" if n == 0 else "ActorTwo") if variant == "A" else ("RenamedWest" if n == 0 else "RenamedEast")
        arm = rig(prefix + "Rig")
        skin = material(prefix + "Face", (0.95, 0.73, 0.65, 1), (0.57, 0.3, 0.29, 1))
        cloth = material(prefix + "Cloth", (0.87, 0.9, 0.96, 1) if n else (0.14, 0.23, 0.48, 1))
        hair = material(prefix + "Hair", (0.78, 0.56, 0.19, 1) if n else (0.55, 0.68, 0.88, 1))
        iris = material(prefix + "Iris", (0.06, 0.12, 0.22, 1))
        offset = 0.12 if variant == "B" else 0
        parts = [mesh(prefix + "Torso", "cube", (x, offset, 0.86), (0.55, 0.34, 0.9), cloth, arm),
                 mesh(prefix + "Head", "sphere", (x, offset, 1.68), (0.32, 0.29, 0.36), skin, arm, "頭"),
                 mesh(prefix + "Crown", "sphere", (x, offset + 0.02, 1.91), (0.34, 0.3, 0.19), hair, arm, "頭")]
        for sign in (-1, 1):
            parts.append(mesh(prefix + "Eye" + str(sign), "sphere", (x + sign * 0.12, offset - 0.269, 1.7), (0.046, 0.035, 0.055), iris, arm, "頭"))
        for bone in arm.pose.bones:
            bone.rotation_mode = "XYZ"
            bone.keyframe_insert(data_path="rotation_euler", frame=1)
            bone.rotation_euler.y = (0.28 if n else -0.28) if bone.name == "頭" else (0.07 if n else -0.07)
            bone.keyframe_insert(data_path="rotation_euler", frame=10)
        actors.append({"id": "left" if n == 0 else "right", "objects": [o.name for o in parts], "armature": arm.name,
                       "materials": {"face": [skin.name], "cloth": [cloth.name], "hair": [hair.name], "iris": [iris.name]}})
    floor_mat = material("StageFaceClothSimilarName_" + variant, (0.18, 0.23, 0.32, 1))
    mesh("StageGround_" + variant, "plane", (0, 0, 0.35), (3, 3, 1), floor_mat)
    for name, kind, position, energy, rotation in (("Key_" + variant, "SUN", (2, -3, 5), 2.5, (0.4, -0.5, -0.4)),
                                                   ("Fill_" + variant, "AREA", (-3, -2, 3), 100, (0, 0, 0))):
        data = bpy.data.lights.new(name, kind)
        data.energy = energy
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location, obj.rotation_euler = position, rotation
        if kind == "AREA":
            obj.rotation_euler = (Vector((0, 0, 1.3)) - obj.location).to_track_quat("-Z", "Y").to_euler()
            data.shape, data.size = "DISK", 3
    camera_data = bpy.data.cameras.new("Lens_" + variant)
    camera_data.lens = 50
    camera = bpy.data.objects.new("Camera_" + variant, camera_data)
    scene.collection.objects.link(camera)
    camera.location = (2.4, -6.5, 2.8) if variant == "A" else (-2.8, -6.7, 3.2)
    camera.rotation_euler = (Vector((0, 0, 1.3)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    alternate = camera.copy()
    alternate.data = camera_data.copy()
    alternate.name = "MarkerAlternate_" + variant
    scene.collection.objects.link(alternate)
    alternate.location.x += 1.5
    scene.timeline_markers.new("SwitchCamera", frame=10).camera = alternate
    tree = bpy.data.node_groups.new("FixtureCompositor" + variant, "CompositorNodeTree")
    scene.compositing_node_group = tree
    layers = tree.nodes.new("CompositorNodeRLayers")
    layers.scene = scene
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.name = "FixtureGlow"
    glare.inputs["Type"].default_value = "Fog Glow"
    glare.inputs["Threshold"].default_value = 0.65
    tree.links.new(layers.outputs["Image"], glare.inputs["Image"])
    combine = tree.nodes.new("ShaderNodeMixRGB")
    combine.blend_type = "ADD"
    combine.inputs[0].default_value = 0.25
    tree.links.new(glare.outputs["Image"], combine.inputs[1])
    tree.links.new(glare.outputs["Glare"], combine.inputs[2])
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    composite = tree.nodes.new("NodeGroupOutput")
    tree.links.new(combine.outputs[0], composite.inputs["Image"])
    nested = bpy.data.node_groups.new("NestedInheritedOutput" + variant, "CompositorNodeTree")
    nested.interface.new_socket(name="Image", in_out="INPUT", socket_type="NodeSocketColor")
    nested.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    group_input, group_output = nested.nodes.new("NodeGroupInput"), nested.nodes.new("NodeGroupOutput")
    nested.links.new(group_input.outputs["Image"], group_output.inputs["Image"])
    inherited = nested.nodes.new("CompositorNodeOutputFile")
    inherited.name = "MustBeMuted"
    inherited.directory = str(output / "must-not-exist")
    inherited.file_output_items.new("RGBA", "Image")
    nested.links.new(group_input.outputs["Image"], inherited.inputs[0])
    nested_node = tree.nodes.new("CompositorNodeGroup")
    nested_node.node_tree = nested
    tree.links.new(layers.outputs["Image"], nested_node.inputs["Image"])
    scene.frame_set(1)
    scene.camera = camera
    scene.render.filepath = str(output / "source-output-must-not-exist.png")
    source = output / ("fixture-" + variant + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(source), check_existing=False)
    profile = {"schema_version": 1, "id": "studio-fixture-" + variant.lower(), "source": {"path": str(source), "sha256": digest(source)},
        "runtime": "presets/runtime/native53-v1.json", "scene": {"name": scene.name, "camera": camera.name, "expected_lens_mm": 50, "registration": "none"},
        "actors": actors, "switches": {"key": {"kind": "light_energy", "object": "Key_" + variant, "expected": 2.5},
            "cloth_tint": {"kind": "node_input", "material": actors[1]["materials"]["cloth"][0], "node": "ClothTint", "socket": "Color2", "expected": [1, 1, 1, 1]},
            "glow_off": {"kind": "glow_bypass", "nodes": [{"tree": "compositor", "scene": scene.name, "node": glare.name, "image_output": "Image", "glare_output": "Glare"}]}},
        "cases": [{"id": "baseline", "frame": 1, "overrides": []}, {"id": "key_low", "frame": 1, "overrides": [{"switch": "key", "value": 0.35}]},
                  {"id": "cloth_tint", "frame": 1, "overrides": [{"switch": "cloth_tint", "value": [0.62, 0.72, 0.91, 1]}]},
                  {"id": "glow_off", "frame": 1, "overrides": [{"switch": "glow_off", "value": True}]},
                  {"id": "pose_10", "frame": 10, "overrides": []}, {"id": "baseline_repeat", "frame": 1, "overrides": []}],
        "render": {"width": 640, "height": 360, "samples": 16, "dof": "source", "motion_blur": False},
        "limits": ["Original procedural proxy fixture, not an MMD quality sample", "No physics; frame1/frame10 are independent static evaluations", "Renamed fixture variation is tool transfer evidence, not cross-project art mastery"]}
    (output / ("profile-" + variant + ".json")).write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=False)
    for variant in ("A", "B"):
        make(args.output, variant)
    print("STUDIO_FIXTURES_CREATED", str(args.output), flush=True)


if __name__ == "__main__":
    main()
