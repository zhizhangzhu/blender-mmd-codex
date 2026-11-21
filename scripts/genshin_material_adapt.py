"""Adapt downloaded shader components to the duet's actual MMD inputs.

Face Factor is derived from festivities' GPL-3.0 library. The imported node data
is kept in delivered blends with source and license, not committed to this repo.
The hair MatCap group is from the user's 三一七片的谎言 preset collection.
"""

import bpy
from mathutils import Vector

KEY = Vector((-0.45, -0.75, 0.48)).normalized()


def own_face_factor(tree, controller, path):
    """Use the model's own SDF without the avatar-template nose/eye mask."""
    forward = shader_axis(tree, controller, "forward")
    up = shader_axis(tree, controller, "up")

    def vector(op, a, b=None):
        node = tree.nodes.new("ShaderNodeVectorMath")
        node.operation = op
        for socket, value in zip(node.inputs, [a, b]):
            if value is None:
                continue
            if hasattr(value, "is_output"):
                tree.links.new(value, socket)
            else:
                socket.default_value = value
        return node.outputs["Value"] if op == "DOT_PRODUCT" else node.outputs[0]

    def scalar(op, a, b):
        node = tree.nodes.new("ShaderNodeMath")
        node.operation = op
        for socket, value in zip(node.inputs, [a, b]):
            if hasattr(value, "is_output"):
                tree.links.new(value, socket)
            else:
                socket.default_value = value
        return node.outputs[0]

    right = vector("NORMALIZE", vector("CROSS_PRODUCT", forward, up))
    projected = vector("NORMALIZE", vector("SUBTRACT", tuple(KEY), vector("SCALE", up)))
    # Remove only the component along posed head-up.
    scale = projected.node.inputs[0].links[0].from_node.inputs[1].links[0].from_node
    tree.links.new(vector("DOT_PRODUCT", up, tuple(KEY)), scale.inputs[3])
    front = vector("DOT_PRODUCT", vector("NORMALIZE", forward), projected)
    side = scalar("GREATER_THAN", vector("DOT_PRODUCT", right, projected), 0)
    uv = tree.nodes.new("ShaderNodeUVMap")
    flip = vector("ADD", vector("MULTIPLY", uv.outputs[0], (-1, 1, 1)), (1, 0, 0))
    choice = tree.nodes.new("ShaderNodeMixRGB")
    tree.links.new(side, choice.inputs[0])
    tree.links.new(uv.outputs[0], choice.inputs[1])
    tree.links.new(flip, choice.inputs[2])
    image = tree.nodes.new("ShaderNodeTexImage")
    image.name = "Genshin study | supplied model FaceLightmap"
    image.image = bpy.data.images.load(str(path), check_existing=True)
    image.image.colorspace_settings.name = "Non-Color"
    tree.links.new(choice.outputs[0], image.inputs[0])
    channels = tree.nodes.new("ShaderNodeSeparateColor")
    tree.links.new(image.outputs[0], channels.inputs[0])
    threshold = scalar("MULTIPLY", scalar("SUBTRACT", 1, front), 0.5)
    result = tree.nodes.new("ShaderNodeMapRange")
    result.name = "Genshin study | own SDF threshold"
    result.clamp = True
    result.interpolation_type = "SMOOTHSTEP"
    tree.links.new(channels.outputs[0], result.inputs["Value"])
    tree.links.new(scalar("SUBTRACT", threshold, 0.035), result.inputs["From Min"])
    tree.links.new(scalar("ADD", threshold, 0.035), result.inputs["From Max"])
    return result.outputs[0]


def head_axes(scene, arm):
    head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
    obj = bpy.data.objects.new(
        "Genshin study | head axes | " + arm["performer_id"], None
    )
    scene.collection.objects.link(obj)
    inverse = (arm.matrix_world.to_3x3() @ head.bone.matrix_local.to_3x3()).inverted()
    origin = bpy.data.objects.new(
        "Genshin study | world head origin | " + arm["performer_id"], None
    )
    scene.collection.objects.link(origin)
    origin.parent, origin.parent_type, origin.parent_bone = arm, "BONE", head.name
    for name, axis in [("forward", Vector((0, -1, 0))), ("up", Vector((0, 0, 1)))]:
        canonical = inverse @ axis
        point = bpy.data.objects.new(
            "Genshin study | world head " + name + " | " + arm["performer_id"], None
        )
        scene.collection.objects.link(point)
        point.parent, point.parent_type, point.parent_bone = arm, "BONE", head.name
        point.location = canonical
        obj[name] = list(axis)
        for row in range(3):
            driver = obj.driver_add(f'["{name}"]', row).driver
            # Transform variables have an explicit world-space contract; the
            # RNA matrix indexing used previously transposed the intended axes.
            for label, target in [("point", point), ("origin", origin)]:
                variable = driver.variables.new()
                variable.name, variable.type = label, "TRANSFORMS"
                variable.targets[0].id = target
                variable.targets[0].transform_type = "LOC_" + "XYZ"[row]
                variable.targets[0].transform_space = "WORLD_SPACE"
            driver.expression = "point-origin"
    return obj


def shader_axis(tree, controller, name):
    node = tree.nodes.new("ShaderNodeCombineXYZ")
    node.name = "Genshin study | " + name
    for index in range(3):
        driver = node.inputs[index].driver_add("default_value").driver
        var = driver.variables.new()
        var.name = "axis"
        var.targets[0].id = controller
        var.targets[0].data_path = f'["{name}"][{index}]'
        driver.expression = "axis"
    return node.outputs[0]


def face_group(template, actor, controller):
    group = template.copy()
    group.name = "Genshin study | festivities Face Factor | " + actor
    group["source"] = "https://github.com/festivities/Blender-miHoYo-Shaders"
    group["license"] = "GPL-3.0"
    group["quality_light_vector_contract"] = "incoming"
    for node in list(group.nodes):
        if node.bl_idname == "NodeUndefined":
            for socket in node.outputs:
                for link in list(socket.links):
                    link.to_socket.default_value = 1
            group.nodes.remove(node)
        elif node.type == "ATTRIBUTE" and node.attribute_name in {
            "headForward",
            "headUp",
        }:
            output = shader_axis(
                group,
                controller,
                "forward" if node.attribute_name == "headForward" else "up",
            )
            for link in list(node.outputs["Vector"].links):
                group.links.new(output, link.to_socket)
            group.nodes.remove(node)
    # The original library encodes its light direction as Euler rotation. Use
    # a declared world-space vector here; do not interpret it as Euler angles.
    normalizer = group.nodes["Vector Math.006"]
    for link in list(normalizer.inputs[0].links):
        group.links.remove(link)
    # This adapted Face Factor uses the incoming light direction. Our own
    # FaceLightmap solver uses the opposite, surface-to-key convention.
    normalizer.inputs[0].default_value = -KEY
    return group


def apply(scene, author_library, user_genshin_library, asset_root):
    with bpy.data.libraries.load(str(author_library), link=False) as (source, loaded):
        assert "Face Factor" in source.node_groups
        loaded.node_groups = ["Face Factor"]
    template = loaded.node_groups[0]
    with bpy.data.libraries.load(str(user_genshin_library), link=False) as (
        source,
        loaded,
    ):
        loaded.node_groups = ["发高光"]
    hair_group = loaded.node_groups[0]
    arms = {
        o["performer_id"]: o
        for o in scene.objects
        if o.type == "ARMATURE" and o.get("performer_id")
    }
    controllers = {actor: head_axes(scene, arm) for actor, arm in arms.items()}
    groups = {actor: face_group(template, actor, controllers[actor]) for actor in arms}
    report = {
        "face_materials": [],
        "hair_materials": [],
        "missing_maps": {
            "aether": "No original game body/hair Lightmap or WuWa HM/HN; retained existing source-adapted hair/cloth and atlas gold masks"
        },
        "sources": [
            "festivities / Blender-miHoYo-Shaders v3.4, GPL-3.0",
            "三一七片的谎言 / 发高光 (user supplied original Genshin preset)",
        ],
        "goo_cast_shadows": "Unsupported Shader Info node removed from copied Face Factor; Catch Shadows disabled; not an exact Goo implementation",
    }
    for mat in list(bpy.data.materials):
        actor = mat.get("performer_id")
        if actor not in arms or not mat.node_tree:
            continue
        tree = mat.node_tree
        name = mat.get("source_mmd_material_name", mat.name)
        if (actor == "aksiniya" and name == "颜") or (
            actor == "aether" and name in {"面1", "面2"}
        ):
            node = tree.nodes.new("ShaderNodeGroup")
            node.name = "Genshin study | SDF face factor"
            node.node_tree = groups[actor]
            node.inputs["[Loli/Boy/Girl/Male/Lady]"].default_value = (
                5 if actor == "aksiniya" else 2
            )
            node.inputs["Softness"].default_value = 0.035
            node.inputs["Catch Shadows"].default_value = 0
            ramp = (
                tree.nodes["Aether v2 | material light response"]
                if actor == "aether"
                else tree.nodes["Look v3 | Soft toon bands"]
            )
            tree.links.new(node.outputs["Soft Factor"], ramp.inputs[0])
            palette = (
                [(0.78, 0.64, 0.63, 1), (1.0, 0.98, 0.99, 1), (1.06, 1.03, 1.02, 1)]
                if actor == "aether"
                else [
                    (0.74, 0.66, 0.76, 1),
                    (0.99, 0.98, 1.01, 1),
                    (1.04, 1.02, 1.04, 1),
                ]
            )
            for index, element in enumerate(ramp.color_ramp.elements):
                element.color = palette[min(index, len(palette) - 1)]
                element.position = index / (len(ramp.color_ramp.elements) - 1)
            mat["genshin_face_sdf"] = True
            report["face_materials"].append(
                {
                    "actor": actor,
                    "material": mat.name,
                    "source": "festivities Face Factor adapted to posed head axes; Lady/Boy template selected; MMD UV must be visually checked",
                }
            )
        if actor == "aether" and name in {"面1", "面2", "肌"}:
            balance = tree.nodes.get("Aether v2 | skin balance")
            if balance:
                balance.inputs[2].default_value = (1, 1.025, 1.04, 1)
            chroma = tree.nodes.get("Aether v2 | texture white balance")
            if chroma:
                chroma.inputs["Saturation"].default_value = 0.94
        if (
            actor == "aksiniya"
            and mat.get("look_category") == "hair"
            and not name.endswith("+")
        ):
            surface = tree.nodes.get("Look v3 | NPR surface")
            if not surface:
                continue
            old = surface.inputs["Color"].links[0].from_socket
            tex = tree.nodes.new("ShaderNodeTexImage")
            tex.image = bpy.data.images.load(
                str(asset_root / "Textures/NPC_Female_Hair206_Tex_Lightmap.png"),
                check_existing=True,
            )
            tex.image.colorspace_settings.name = "Non-Color"
            base = tree.nodes.get("mmd_base_tex")
            if base and base.inputs["Vector"].is_linked:
                tree.links.new(
                    base.inputs["Vector"].links[0].from_socket, tex.inputs["Vector"]
                )
            node = tree.nodes.new("ShaderNodeGroup")
            node.node_tree = hair_group
            node.name = "Genshin study | supplied hair MatCap"
            tree.links.new(tex.outputs[0], node.inputs["高光"])
            node.inputs["高光明暗度"].default_value = 0.08
            add = tree.nodes.new("ShaderNodeMixRGB")
            add.blend_type = "ADD"
            add.inputs[0].default_value = 1
            tree.links.new(old, add.inputs[1])
            tree.links.new(node.outputs["结果"], add.inputs[2])
            tree.links.new(add.outputs[0], surface.inputs["Color"])
            report["hair_materials"].append(mat.name)
    scene.frame_set(scene.frame_current)
    return report
