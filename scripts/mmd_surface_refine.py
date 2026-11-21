"""Model-adapted hair sheen, masked metal and restrained cloth/stage response."""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_quality_lab import position_hash, pose_hash
from mmd_caption_render import output_file


def math(t, op, a, b=None):
    n = t.nodes.new("ShaderNodeMath")
    n.operation = op
    n.name = "Surface | " + op
    for i, v in enumerate([a, b]):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            t.links.new(v, n.inputs[i])
    return n.outputs[0]


def vec(t, op, a, b=None):
    n = t.nodes.new("ShaderNodeVectorMath")
    n.operation = op
    n.name = "Surface | " + op
    for i, v in enumerate([a, b]):
        if v is None:
            continue
        if isinstance(v, tuple):
            n.inputs[i].default_value = v
        else:
            t.links.new(v, n.inputs[i])
    return n.outputs["Value"] if op == "DOT_PRODUCT" else n.outputs[0]


def head_up_controller(scene):
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
    obj = bpy.data.objects.get("Surface | head direction controller")
    if obj is None:
        obj = bpy.data.objects.new("Surface | head direction controller", None)
        scene.collection.objects.link(obj)
    else:
        obj.animation_data_clear()
    obj["up"] = [0.0, 0.0, 1.0]
    current = scene.frame_current
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        rot = (
            arm.matrix_world.to_3x3()
            @ head.matrix.to_3x3()
            @ head.bone.matrix_local.to_3x3().inverted()
        )
        obj["up"] = list((rot @ Vector((0, 0, 1))).normalized())
        obj.keyframe_insert(data_path='["up"]', frame=frame)
    scene.frame_set(current)
    return obj


def head_axis(t, controller):
    n = t.nodes.new("ShaderNodeCombineXYZ")
    n.name = "Surface | animated head up"
    for i in range(3):
        fc = n.inputs[i].driver_add("default_value")
        var = fc.driver.variables.new()
        var.name = "axis"
        var.targets[0].id = controller
        var.targets[0].data_path = f'["up"][{i}]'
        fc.driver.expression = "axis"
    return n.outputs[0]


def mask_node(mat, maps):
    base = mat.node_tree.nodes.get("mmd_base_tex")
    if not base or not base.image or base.image.name not in maps:
        return None
    t = mat.node_tree
    image = bpy.data.images.load(maps[base.image.name], check_existing=True)
    image.colorspace_settings.name = "Non-Color"
    image.pack()
    n = t.nodes.new("ShaderNodeTexImage")
    n.name = "Surface | authored control mask"
    n.image = image
    n.interpolation = "Linear"
    if base.inputs["Vector"].is_linked:
        t.links.new(base.inputs["Vector"].links[0].from_socket, n.inputs["Vector"])
    split = t.nodes.new("ShaderNodeSeparateColor")
    split.mode = "RGB"
    split.name = "Surface | mask channels"
    t.links.new(n.outputs["Color"], split.inputs[0])
    return split


def add_color(t, surface, color, fac, tint, blend="SCREEN"):
    mix = t.nodes.new("ShaderNodeMixRGB")
    mix.name = "Surface | selective sheen"
    mix.blend_type = blend
    t.links.new(fac, mix.inputs[0])
    t.links.new(color, mix.inputs[1])
    mix.inputs[2].default_value = (*tint, 1)
    t.links.new(mix.outputs[0], surface.inputs["Color"])


def hair_sheen(mat, controller, settings, mask):
    t = mat.node_tree
    surface = t.nodes["Look v3 | NPR surface"]
    previous = surface.inputs["Color"].links[0].from_socket
    gain = t.nodes.new("ShaderNodeVectorMath")
    gain.operation = "SCALE"
    gain.name = "Surface | hair base separation"
    t.links.new(previous, gain.inputs[0])
    gain.inputs[3].default_value = settings["base_gain"]
    t.links.new(gain.outputs[0], surface.inputs["Color"])
    if mat.name.endswith("+"):
        return None
    old = t.nodes.get("Look v3 | Restrained material highlight")
    if old:
        for link in list(old.inputs[0].links):
            t.links.remove(link)
        old.inputs[0].default_value = 0
    normal = t.nodes["Look v3 | Geometry"].outputs["Normal"]
    up = head_axis(t, controller)
    dot = vec(t, "DOT_PRODUCT", normal, up)
    scale = t.nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    t.links.new(normal, scale.inputs[0])
    t.links.new(dot, scale.inputs[3])
    tangent = vec(t, "NORMALIZE", vec(t, "SUBTRACT", up, scale.outputs[0]))
    h = t.nodes["Look v3 | Normalize half"].outputs[0]
    th = vec(t, "DOT_PRODUCT", tangent, h)
    band = math(
        t,
        "POWER",
        math(t, "MAXIMUM", math(t, "SUBTRACT", 1, math(t, "MULTIPLY", th, th)), 0),
        settings["exponent"],
    )
    if mask:
        painted = math(
            t,
            "ADD",
            math(
                t, "MULTIPLY", mask.outputs["Blue"], 1 - settings["painted_mask_floor"]
            ),
            settings["painted_mask_floor"],
        )
        band = math(t, "MULTIPLY", band, painted)
    fac = math(t, "MULTIPLY", band, settings["strength"])
    add_color(t, surface, gain.outputs[0], fac, settings["color"])
    return fac


def surface_material(mat, mask, settings):
    if not mask:
        return None
    t = mat.node_tree
    category = mat["look_category"]
    gold = mask.outputs["Red"]
    if category == "cloth":
        surface = t.nodes["Look v3 | NPR surface"]
        previous = surface.inputs["Color"].links[0].from_socket
        dot = t.nodes.get("Look v3 | Specular normal")
        if dot:
            sheen = math(
                t,
                "POWER",
                math(t, "MAXIMUM", dot.outputs["Value"], 0),
                settings["cloth"]["exponent"],
            )
            sheen = math(t, "MULTIPLY", sheen, math(t, "SUBTRACT", 1, gold))
            sheen = math(t, "MULTIPLY", sheen, settings["cloth"]["sheen"])
            add_color(
                t, surface, previous, sheen, settings["cloth"]["color"], blend="ADD"
            )
    out = next(n for n in t.nodes if n.type == "OUTPUT_MATERIAL")
    previous = out.inputs["Surface"].links[0].from_socket
    bsdf = t.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Surface | masked gold response"
    t.links.new(t.nodes["mmd_shader"].outputs["Color"], bsdf.inputs["Base Color"])
    t.links.new(t.nodes["mmd_shader"].outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Metallic"].default_value = settings["metal"]["metallic"]
    t.links.new(mask.outputs["Green"], bsdf.inputs["Roughness"])
    bsdf.inputs["Coat Weight"].default_value = settings["metal"]["coat"]
    mix = t.nodes.new("ShaderNodeMixShader")
    mix.name = "Surface | gold only; retain cloth NPR"
    t.links.new(math(t, "MULTIPLY", gold, settings["metal"]["mix"]), mix.inputs[0])
    t.links.new(previous, mix.inputs[1])
    t.links.new(bsdf.outputs[0], mix.inputs[2])
    t.links.new(mix.outputs[0], out.inputs["Surface"])
    return gold


def apply(scene, settings, maps, variant, directory):
    report = {
        "variant": variant,
        "hair_materials": [],
        "masked_surface_materials": [],
        "head_direction_frames": [scene.frame_start, scene.frame_end],
    }
    use_hair = variant in {"hair", "combined"}
    use_surface = variant in {"materials", "combined"}
    controller = head_up_controller(scene) if use_hair else None
    layer = scene.view_layers[0]
    signals = {}
    for name in ["SurfaceHair", "SurfaceGold"]:
        a = layer.aovs.add()
        a.name = name
        a.type = "VALUE"
        signals[name] = []
    for mat in list(bpy.data.materials):
        category = mat.get("look_category")
        if category not in {"hair", "cloth", "trim"}:
            continue
        if mat.mmd_material.alpha <= 0.001:
            continue
        mask = mask_node(mat, maps)
        signal = None
        signal_name = None
        if use_hair and category == "hair":
            signal = hair_sheen(mat, controller, settings["hair"], mask)
            report["hair_materials"].append(mat.name)
            signal_name = "SurfaceHair"
        if use_surface and category in {"cloth", "trim"} and not mat.name.endswith("+"):
            signal = surface_material(mat, mask, settings)
            if signal is not None:
                report["masked_surface_materials"].append(mat.name)
            signal_name = "SurfaceGold"
        if signal is not None:
            out = mat.node_tree.nodes.new("ShaderNodeOutputAOV")
            out.aov_name = signal_name
            mat.node_tree.links.new(signal, out.inputs["Value"])
            signals[signal_name].append(mat.name)
        if variant == "combined":
            ramp = mat.node_tree.nodes.get("Look v3 | Soft toon bands")
            if category in {"hair", "cloth"} and ramp:
                scale = settings["light_response"]["shadow_" + category + "_scale"]
                color = ramp.color_ramp.elements[0].color
                ramp.color_ramp.elements[0].color = (*(v * scale for v in color[:3]), 1)
                mid = settings["light_response"].get("mid_" + category + "_scale", 1)
                color = ramp.color_ramp.elements[1].color
                ramp.color_ramp.elements[1].color = (*(v * mid for v in color[:3]), 1)
    if use_surface:
        scene.eevee.use_raytracing = True
    if variant in {"lighting", "combined"}:
        bpy.data.objects["Fill softbox"].data.energy = settings["stage"]["fill_power"]
        bpy.data.objects["Stage softbox"].data.energy = settings["stage"]["stage_power"]
        bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
        bg.inputs["Strength"].default_value = settings["stage"]["world_strength"]
    layer.update_render_passes()
    tree = scene.compositing_node_group
    render = next(n for n in tree.nodes if n.type == "R_LAYERS")
    for name, mats in signals.items():
        if mats:
            output_file(
                tree, directory / "diagnostics", name, render.outputs[name], False
            )
    report["signals"] = signals
    report["raytracing"] = scene.eevee.use_raytracing
    scene["surface_refinement"] = json.dumps(settings)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--preset", type=Path, required=True)
    p.add_argument("--masks", type=Path, required=True)
    p.add_argument(
        "--variants",
        nargs="+",
        default=["baseline", "hair", "materials", "lighting", "combined"],
    )
    p.add_argument("--frames", type=int, nargs="+", default=[421, 540, 601])
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    settings = json.loads(args.preset.read_text(encoding="utf-8"))
    masks = json.loads(args.masks.read_text(encoding="utf-8"))
    maps = {x["source_image"]: x["mask"] for x in masks["maps"]}
    source = bpy.data.filepath
    args.output_dir.mkdir(parents=True, exist_ok=False)
    reports = []
    for variant in args.variants:
        if variant not in {"baseline", "hair", "materials", "lighting", "combined"}:
            raise ValueError(variant)
        bpy.ops.wm.open_mainfile(filepath=source)
        s = bpy.context.scene
        for n in list(s.compositing_node_group.nodes):
            if n.bl_idname == "CompositorNodeOutputFile":
                s.compositing_node_group.nodes.remove(n)
        dest = args.output_dir / variant
        dest.mkdir()
        arm = next(o for o in s.objects if o.type == "ARMATURE")
        mesh = next(
            o
            for o in s.objects
            if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
        )
        before = position_hash(mesh)
        poses = {f: pose_hash(s, arm, f) for f in args.frames}
        r = (
            apply(s, settings, maps, variant, dest)
            if variant != "baseline"
            else {"variant": "baseline"}
        )
        assert position_hash(mesh) == before
        assert all(pose_hash(s, arm, f) == poses[f] for f in args.frames)
        r.update(
            {
                "vertex_positions_unchanged": True,
                "pose_bones_unchanged": True,
                "frames": args.frames,
                "source": source,
                "settings": settings,
            }
        )
        s.render.resolution_percentage = 50
        s.eevee.taa_render_samples = 48
        s.render.image_settings.media_type = "IMAGE"
        s.render.image_settings.file_format = "PNG"
        for frame in args.frames:
            s.frame_set(frame)
            s.render.filepath = str(dest / f"frame-{frame:04d}.png")
            bpy.ops.render.render(write_still=True)
        if variant == "combined":
            bpy.ops.wm.save_as_mainfile(filepath=str(dest / "surface-study.blend"))
        (dest / "report.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        reports.append(r)
        print("SURFACE_VARIANT_OK", variant, flush=True)
    (args.output_dir / "surface-report.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
