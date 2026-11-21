"""Rebuild the Aksiniya look on a portable baked scene, preserving MMD layers.

The MMDShaderDev Color/Alpha outputs retain PMX texture, sphere and transparency
semantics. Lighting is deliberately art-directed per material, in linear RGB.
This is a model-specific Blender NPR treatment, not the reference author's rig.
"""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def node(tree, kind, label, **props):
    n = tree.nodes.new(kind)
    n.label = label
    n.name = "Look v3 | " + label
    for key, value in props.items():
        setattr(n, key, value)
    return n


def math_node(t, operation, a, b=None, label=""):
    n = node(t, "ShaderNodeMath", label or operation, operation=operation)
    for index, value in enumerate([a, b]):
        if value is None:
            continue
        if isinstance(value, (float, int)):
            n.inputs[index].default_value = value
        else:
            t.links.new(value, n.inputs[index])
    return n.outputs[0]


def upgrade(mat, category_override=None):
    t = mat.node_tree
    src = t.nodes.get("mmd_shader")
    if not src or "Color" not in src.outputs:
        return None
    # Remove the previous display treatment, retain source MMD nodes and maps.
    keep = set()

    def retain(n):
        if n in keep:
            return
        keep.add(n)
        for inp in n.inputs:
            for link in inp.links:
                retain(link.from_node)

    retain(src)
    out = next(n for n in t.nodes if n.type == "OUTPUT_MATERIAL")
    keep.add(out)
    for n in list(t.nodes):
        if n not in keep:
            t.nodes.remove(n)
    name = mat.get("source_mmd_material_name", mat.name).rstrip("+")
    skin = name in {"颜", "首", "手", "口", "舌"}
    eye = name in {"目", "白目", "齿"}
    ink = name in {"眉", "睫"}
    hair = name in {"鬓", "前鬓", "呆毛"}
    trim = name in {"头饰", "前装饰", "后装饰"}
    fur = name == "毛领"
    category = (
        "skin"
        if skin
        else "eye"
        if eye
        else "ink"
        if ink
        else "hair"
        if hair
        else "trim"
        if trim
        else "fur"
        if fur
        else "cloth"
    )
    if category_override is not None:
        category = category_override
    skin = category == "skin"
    palette = {
        "skin": ((0.96, 0.96, 1.05, 1), (1.07, 1.10, 1.21, 1)),
        "eye": ((0.99, 0.99, 1, 1), (1.04, 1.04, 1.04, 1)),
        "ink": ((0.52, 0.47, 0.61, 1), (0.67, 0.63, 0.72, 1)),
        "hair": ((0.48, 0.52, 0.76, 1), (0.97, 0.99, 1.04, 1)),
        "trim": ((0.53, 0.52, 0.68, 1), (1.04, 1.00, 0.96, 1)),
        "cloth": ((0.56, 0.57, 0.78, 1), (1.00, 0.99, 1.04, 1)),
        "fur": ((0.80, 0.82, 0.94, 1), (1.02, 1.01, 1.04, 1)),
    }
    geo = node(t, "ShaderNodeNewGeometry", "Geometry")
    key = Vector((-0.35, -0.65, 0.72)).normalized()
    ndotl = node(t, "ShaderNodeVectorMath", "Key direction", operation="DOT_PRODUCT")
    t.links.new(geo.outputs["Normal"], ndotl.inputs[0])
    ndotl.inputs[1].default_value = key
    ramp = node(t, "ShaderNodeValToRGB", "Soft toon bands")
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].position = -0.0
    ramp.color_ramp.elements[0].color = palette[category][0]
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[1].color = palette[category][1]
    t.links.new(ndotl.outputs["Value"], ramp.inputs[0])
    tint = node(
        t, "ShaderNodeMixRGB", "Painted color times lighting", blend_type="MULTIPLY"
    )
    tint.inputs[0].default_value = 1
    t.links.new(src.outputs["Color"], tint.inputs[1])
    t.links.new(ramp.outputs[0], tint.inputs[2])
    hue = node(t, "ShaderNodeHueSaturation", "Per material chroma")
    hue.inputs["Saturation"].default_value = 0.80 if skin else 1.08
    hue.inputs["Value"].default_value = 1.05 if skin else 1
    t.links.new(tint.outputs[0], hue.inputs["Color"])
    color = hue.outputs[0]
    if skin:
        gamma = node(t, "ShaderNodeGamma", "Porcelain skin midtones")
        gamma.inputs[1].default_value = 0.92
        t.links.new(color, gamma.inputs[0])
        color = gamma.outputs[0]
    # Analytic half-vector highlights are stable with a moving camera. Broad
    # painted hair bands remain supplied by the model's existing sphere layers.
    highlight = {"hair": (42, 0.10), "trim": (90, 0.18), "cloth": (70, 0.025)}
    if category in highlight and not mat.name.endswith("+"):
        half = node(t, "ShaderNodeVectorMath", "Half vector", operation="ADD")
        half.inputs[1].default_value = key
        t.links.new(geo.outputs["Incoming"], half.inputs[0])
        norm = node(t, "ShaderNodeVectorMath", "Normalize half", operation="NORMALIZE")
        t.links.new(half.outputs[0], norm.inputs[0])
        dot = node(
            t, "ShaderNodeVectorMath", "Specular normal", operation="DOT_PRODUCT"
        )
        t.links.new(geo.outputs["Normal"], dot.inputs[0])
        t.links.new(norm.outputs[0], dot.inputs[1])
        positive = math_node(t, "MAXIMUM", dot.outputs["Value"], 0)
        exponent, strength = highlight[category]
        power = math_node(t, "POWER", positive, exponent)
        spec = math_node(t, "MULTIPLY", power, strength)
        add = node(
            t, "ShaderNodeMixRGB", "Restrained material highlight", blend_type="ADD"
        )
        t.links.new(spec, add.inputs[0])
        t.links.new(color, add.inputs[1])
        add.inputs[2].default_value = (0.87, 0.91, 1, 1)
        color = add.outputs[0]
    emission = node(t, "ShaderNodeEmission", "NPR surface")
    t.links.new(color, emission.inputs[0])
    transparent = node(t, "ShaderNodeBsdfTransparent", "PMX transparency")
    mix = node(t, "ShaderNodeMixShader", "PMX alpha")
    t.links.new(src.outputs["Alpha"], mix.inputs[0])
    t.links.new(transparent.outputs[0], mix.inputs[1])
    t.links.new(emission.outputs[0], mix.inputs[2])
    t.links.new(mix.outputs[0], out.inputs[0])
    mat["production_shader"] = "MMD Color/Alpha outputs; selective linear NPR v3"
    mat["look_category"] = category
    mat["look_shadow_rgba"] = palette[category][0]
    mat["look_light_rgba"] = palette[category][1]
    # Arrange the graph for subsequent manual inspection.
    for index, n in enumerate(n for n in t.nodes if n.name.startswith("Look v3 |")):
        n.location = (400 + (index % 5) * 230, -(index // 5) * 300)
    return category


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--frames", type=int, nargs="+", default=[421])
    p.add_argument("--percentage", type=int, default=100)
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    s = bpy.context.scene
    assert s.rigidbody_world is None, "Load a portable, physics-baked scene"
    assert not s.get("production_look_upgrade"), "Start from the v1 production baseline"
    assert 1 <= args.percentage <= 100
    assert all(s.frame_start <= f <= s.frame_end for f in args.frames)
    source_file = bpy.data.filepath
    args.output_dir.mkdir(parents=True, exist_ok=False)
    result = {}
    for mat in bpy.data.materials:
        if mat.node_tree:
            category = upgrade(mat)
            if category:
                result[mat.name] = category
    bg = next(n for n in s.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[1].default_value = 0.45
    for obj in s.objects:
        if obj.type == "LIGHT" and obj.name in {
            "Key softbox",
            "Fill softbox",
            "Stage softbox",
        }:
            obj.data.energy *= 0.85
    lilac = bpy.data.materials.get("Stage | dusty lilac")
    if lilac:
        bsdf = next(n for n in lilac.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (0.32, 0.21, 0.25, 1)
    s.eevee.taa_render_samples = 96
    s.render.image_settings.media_type = "IMAGE"
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGB"
    s.render.resolution_percentage = 100
    s.frame_set(args.frames[0])
    s.render.filepath = str(args.output_dir / f"look-{args.frames[0]:04d}.png")
    s["production_look_upgrade"] = "selective-linear-NPR-v3"
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_dir / "production.blend"))
    s.render.resolution_percentage = args.percentage
    for frame in args.frames:
        s.frame_set(frame)
        s.render.filepath = str(args.output_dir / f"look-{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    (args.output_dir / "look-report.json").write_text(
        json.dumps(
            {
                "materials": result,
                "frames": args.frames,
                "source": "MMDShaderDev Color/Alpha",
                "source_project": source_file,
                "render_samples": s.eevee.taa_render_samples,
                "world_strength": bg.inputs[1].default_value,
                "camera_changed": False,
                "physics_changed": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("LOOK_UPGRADE_COMPLETE", args.output_dir, flush=True)


if __name__ == "__main__":
    main()
