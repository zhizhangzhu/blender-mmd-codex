"""Correct eye peek in camera space and establish a directional head-light response."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import (
    ACTORS,
    PREFIX,
    ROOT,
    color,
    link,
    math,
    node,
    remap,
)
from render_portrait_light_controls import mute_file_outputs

OLD = ROOT / "production-v4/Franken_Duet_Goo_Eye_Hair_Stage.blend"
SHA = "5d2c861870e210bb27777cdd5842bd4ebc189712dc22dc69eb1edd87364e6c37"


def camera_point(tree, value, label):
    n = node(tree, "ShaderNodeVectorTransform", label)
    n.vector_type = "POINT"
    n.convert_from, n.convert_to = "WORLD", "CAMERA"
    link(tree, value, n.inputs[0])
    s = node(tree, "ShaderNodeSeparateXYZ", label + " XYZ")
    tree.links.new(n.outputs[0], s.inputs[0])
    return s.outputs


def world_center(tree, helper, label):
    n = node(tree, "ShaderNodeCombineXYZ", label)
    for i, axis in enumerate("XYZ"):
        driver = n.inputs[i].driver_add("default_value").driver
        driver.type = "AVERAGE"
        var = driver.variables.new()
        var.name = "eye_location"
        var.type = "TRANSFORMS"
        target = var.targets[0]
        target.id = helper
        target.transform_type = "LOC_" + axis
        target.transform_space = "WORLD_SPACE"
    return n.outputs[0]


def projected_peek(scene, mat, actor):
    tree = mat.node_tree
    geometry = node(tree, "ShaderNodeNewGeometry", "projected peek surface")
    pixel = camera_point(tree, geometry.outputs["Position"], "surface in camera")
    safe_z = math(tree, "MINIMUM", pixel[2], -0.0001, "safe surface camera Z")
    windows = []
    for side in ("L", "R"):
        helper = scene.objects[PREFIX + actor + " eye " + side]
        eye = camera_point(
            tree,
            world_center(tree, helper, side + " tracked eye center"),
            side + " eye in camera",
        )
        scale = math(tree, "DIVIDE", eye[2], safe_z, side + " perspective depth ratio")
        dx = math(
            tree,
            "SUBTRACT",
            math(tree, "MULTIPLY", pixel[0], scale, side + " projected surface X"),
            eye[0],
            side + " projected eye delta X",
        )
        dy = math(
            tree,
            "SUBTRACT",
            math(tree, "MULTIPLY", pixel[1], scale, side + " projected surface Y"),
            eye[1],
            side + " projected eye delta Y",
        )
        x = math(tree, "DIVIDE", dx, 0.030, side + " projected eye radius X")
        y = math(tree, "DIVIDE", dy, 0.024, side + " projected eye radius Y")
        r2 = math(
            tree,
            "ADD",
            math(tree, "MULTIPLY", x, x, side + " projected X2"),
            math(tree, "MULTIPLY", y, y, side + " projected Y2"),
            side + " projected ellipse",
        )
        oval = remap(tree, r2, 0.65, 1.65, 1, 0, side + " projected soft feather")
        depth = math(tree, "SUBTRACT", pixel[2], eye[2], side + " hair closer than eye")
        front = math(tree, "GREATER_THAN", depth, 0.0005, side + " front hair only")
        close = math(tree, "LESS_THAN", depth, 0.20, side + " local hair depth only")
        windows.append(
            math(
                tree,
                "MULTIPLY",
                oval,
                math(tree, "MULTIPLY", front, close, side + " valid front depth"),
                side + " actual projected eye window",
            )
        )
    amount = math(
        tree,
        "MULTIPLY",
        math(tree, "MAXIMUM", *windows, "projected two eye union"),
        0.72,
        "projected bang transparency",
    )
    tree.links.new(amount, tree.nodes[PREFIX + "eye region bang peek"].inputs[0])
    tree.links.new(
        amount, tree.nodes[PREFIX + "eye peek mask diagnostic"].inputs["Value"]
    )


def head_key(scene, actor):
    helpers = [scene.objects[PREFIX + actor + " eye " + side] for side in ("L", "R")]
    center = (
        helpers[0].matrix_world.translation + helpers[1].matrix_world.translation
    ) * 0.5
    data = bpy.data.lights.new(PREFIX + actor + " directional head key", "AREA")
    data.shape = "DISK"
    data.size = 0.30
    data.energy = 175
    data.color = (1.0, 0.95, 0.88)
    data.diffuse_factor = 1
    data.specular_factor = 0.45
    data.volume_factor = 0
    data.use_shadow = True
    data.shadow_maximum_resolution = 0.003
    group = "EyeHair head key | " + actor
    data.light_groups.use_default = False
    data.light_groups.groups.add().name = group
    obj = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(obj)
    obj.location = center + Vector((-0.48, -0.80, 1.12))
    obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj, group


def main():
    assert hashlib.sha256(OLD.read_bytes()).hexdigest() == SHA
    production = ROOT / "production-v5"
    production.mkdir(parents=True, exist_ok=False)
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(OLD), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    groups = {}
    changes = {
        "hair": [],
        "faces": [],
        "lights": [],
        "peek_method": "camera-projected eye center, perspective-correct ellipse and front-depth test",
        "peek_max_transparency": 0.72,
    }
    for actor in ACTORS:
        lamp, group = head_key(scene, actor)
        groups[actor] = group
        changes["lights"].append(
            {
                "name": lamp.name,
                "position": list(lamp.location),
                "watts": 175,
                "size": 0.30,
                "group": group,
            }
        )
    for mat in bpy.data.materials:
        actor = mat.get("performer_id")
        if actor not in ACTORS or not mat.node_tree:
            continue
        tree = mat.node_tree
        is_hair = tree.nodes.get(PREFIX + "eye region bang peek") is not None
        is_face = mat.name in ("颜", "颜.001")
        if is_hair or is_face:
            info = next(
                n
                for n in tree.nodes
                if n.bl_idname == "ShaderNodeShaderInfo" and n.use_own_light_groups
            )
            info.light_groups.groups.clear()
            info.light_groups.groups.add().name = groups[actor]
            info.light_groups.use_default = False
            form = remap(
                tree,
                info.outputs["Half-lambert factor"],
                0.25,
                0.90,
                0,
                1,
                "directional head form",
            )
            if is_hair:
                projected_peek(scene, mat, actor)
                target = (
                    tree.nodes["Reference transfer | form times directional response"]
                    if actor == "aksiniya"
                    else tree.nodes["Ikhor character | form times actual response"]
                )
                old = target.inputs[0].links[0].from_socket
                mixed = math(
                    tree,
                    "ADD",
                    math(tree, "MULTIPLY", old, 0.25, "authored hair form retained"),
                    math(tree, "MULTIPLY", form, 0.75, "directional hair form weight"),
                    "directional and authored hair form",
                )
                tree.links.new(mixed, target.inputs[0])
                response = tree.nodes[PREFIX + "hair shadow response"]
                response.inputs["To Min"].default_value = 0.32
                changes["hair"].append(
                    {
                        "material": mat.name,
                        "native_form_weight": 0.75,
                        "shadow_min": 0.32,
                        "peek_transparency": 0.72,
                    }
                )
            if is_face:
                target = tree.nodes["Portrait relight | keyfill | form times occlusion"]
                old = target.inputs[0].links[0].from_socket
                mixed = math(
                    tree,
                    "ADD",
                    math(tree, "MULTIPLY", old, 0.75, "SDF face form retained"),
                    math(tree, "MULTIPLY", form, 0.25, "native face form weight"),
                    "SDF and directional face form",
                )
                tree.links.new(mixed, target.inputs[0])
                response = tree.nodes["Goo portrait | separate cast shadow response"]
                response.inputs["To Min"].default_value = (
                    0.59 if actor == "aksiniya" else 0.64
                )
                surface = (
                    tree.nodes.get("Look v3 | NPR surface")
                    or tree.nodes["Ikhor character | controlled NPR surface"]
                )
                old_color = surface.inputs["Color"].links[0].from_socket
                lit = color(
                    tree,
                    "MULTIPLY",
                    old_color,
                    (1.16, 1.16, 1.16, 1),
                    1,
                    "controlled luminous skin",
                )
                visibility = tree.nodes[
                    PREFIX + "external and self visibility"
                ].outputs[0]
                shadow = math(
                    tree, "SUBTRACT", 1, visibility, "warm face shadow permission"
                )
                tinted = color(
                    tree,
                    "MULTIPLY",
                    lit,
                    (1.0, 0.88, 0.83, 1),
                    math(tree, "MULTIPLY", shadow, 0.55, "warm shadow tint amount"),
                    "bright skin with warm shadow",
                )
                tree.links.new(tinted, surface.inputs["Color"])
                changes["faces"].append(
                    {
                        "material": mat.name,
                        "skin_gain": 1.16,
                        "shadow_min": response.inputs["To Min"].default_value,
                        "SDF_retained": True,
                    }
                )
    import goo_engine_light_groups

    goo_engine_light_groups.sync_light_groups()
    bpy.context.view_layer.update()
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 24
    scene.frame_set(4290)
    project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    prep = json.loads((OLD.parent / "preparation.json").read_text(encoding="utf-8"))
    prep.update(
        source=str(OLD),
        source_sha256=SHA,
        project=str(project),
        project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
        revision=changes,
    )
    for row in prep["hair"]:
        row.update(peek_opacity_reduction=0.72, shadow_min=0.32)
    (production / "preparation.json").write_text(
        json.dumps(prep, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("PROJECTED_EYE_SHADOW_SAVED", project, flush=True)


if __name__ == "__main__":
    main()
