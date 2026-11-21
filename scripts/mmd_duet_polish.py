"""Apply the user's brighter Ray-preview hall and Guanhaizi character direction."""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_hesperides_stage import area, math_node, ray_settings, texture_node
from mmd_surface_refine import mask_node, surface_material

ROOT = Path(__file__).resolve().parents[1]


def matcap(mat, textures):
    fx = textures / (mat.name + ".fx")
    if not fx.is_file():
        return False
    defs, _values = ray_settings(fx)
    if defs.get("ALBEDO_MATCAP_ENABLE") != "2":
        return False
    tree = mat.node_tree
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    previous = bsdf.inputs["Base Color"].links[0].from_socket
    normal = (
        bsdf.inputs["Normal"].links[0].from_socket
        if bsdf.inputs["Normal"].is_linked
        else tree.nodes.new("ShaderNodeNewGeometry").outputs["Normal"]
    )
    view = tree.nodes.new("ShaderNodeVectorTransform")
    view.vector_type, view.convert_from, view.convert_to = "NORMAL", "WORLD", "CAMERA"
    tree.links.new(normal, view.inputs[0])
    scale = tree.nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    scale.inputs[3].default_value = 0.5
    tree.links.new(view.outputs[0], scale.inputs[0])
    offset = tree.nodes.new("ShaderNodeVectorMath")
    offset.operation = "ADD"
    offset.inputs[1].default_value = (0.5, 0.5, 0)
    tree.links.new(scale.outputs[0], offset.inputs[0])
    tex = texture_node(tree, textures, defs["ALBEDO_MATCAP_MAP_FILE"])
    tree.links.new(offset.outputs[0], tex.inputs["Vector"])
    mask = texture_node(tree, textures, defs["ALBEDO_MATCAP_MAP_AFFECT_FILE"], True)
    separate = tree.nodes.new("ShaderNodeSeparateColor")
    tree.links.new(mask.outputs["Color"], separate.inputs[0])
    factor = math_node(
        tree,
        "Duet | authored MatCap mask",
        "MULTIPLY",
        separate.outputs[int(defs.get("ALBEDO_MATCAP_MAP_AFFECT_SWIZZLE", 0))],
        0.65,
    )
    mix = tree.nodes.new("ShaderNodeMixRGB")
    mix.name, mix.blend_type = "Duet | authored additive MatCap adaptation", "ADD"
    tree.links.new(factor, mix.inputs[0])
    tree.links.new(previous, mix.inputs[1])
    tree.links.new(tex.outputs["Color"], mix.inputs[2])
    tree.links.new(mix.outputs[0], bsdf.inputs["Base Color"])
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--textures", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 11899
    scene.frame_set(1)
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.eevee.use_raytracing = False
    scene.eevee.shadow_ray_count = 2
    for obj in scene.objects:
        if obj.type == "LIGHT":
            if obj.data.type == "POINT":
                obj.data.use_shadow = False
            else:
                # Wide, low-angle bounced illumination avoids isolated white patches.
                obj.data.size = max(obj.data.size, 14)
                obj.data.energy *= 1.15
        if obj.name.startswith("Hall | subtle winter air"):
            obj.hide_render = True
    # Parent-free fill lights are placed in the final, translated hall coordinates.
    area(
        "Duet | left blue window fill",
        (-11, 12, 7),
        (0, 12, 3),
        7000,
        (0.48, 0.66, 1),
        13,
    )
    area(
        "Duet | right ivory window fill",
        (11, 12, 7),
        (0, 12, 3),
        6000,
        (0.8, 0.87, 1),
        13,
    )
    area("Duet | broad altar fill", (0, 42, 14), (0, 34, 4), 8500, (0.60, 0.71, 1), 15)
    world = scene.world.node_tree
    background = next(n for n in world.nodes if n.type == "BACKGROUND")
    background.inputs["Strength"].default_value = 1.05
    noise = world.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4
    noise.inputs["Detail"].default_value = 2
    coordinates = world.nodes.new("ShaderNodeTexCoord")
    world.links.new(coordinates.outputs["Normal"], noise.inputs["Vector"])
    clouds = world.nodes.new("ShaderNodeValToRGB")
    clouds.color_ramp.elements[0].position = 0.25
    clouds.color_ramp.elements[0].color = (0.018, 0.19, 0.55, 1)
    clouds.color_ramp.elements[1].position = 0.77
    clouds.color_ramp.elements[1].color = (0.28, 0.68, 0.93, 1)
    world.links.new(noise.outputs["Fac"], clouds.inputs[0])
    world.links.new(clouds.outputs[0], background.inputs["Color"])
    adapted = []
    for mat in bpy.data.materials:
        if not mat.get("stage_id") or not mat.node_tree:
            continue
        tint = mat.node_tree.nodes.get("Stage | winter stone palette")
        if tint:
            tint.inputs[2].default_value = (0.83, 0.89, 1.0, 1)
        for node in mat.node_tree.nodes:
            if node.type == "AMBIENT_OCCLUSION":
                for link in list(node.outputs["AO"].links):
                    link.to_node.inputs[0].default_value = 0.06
        if matcap(mat, args.textures):
            adapted.append(mat.name)
    # Preserve two different character palettes while sharing the Guanhaizi goal.
    style = json.loads(
        (ROOT / "presets/styles/render/guanhaizi-graphic-v1.json").read_text(
            encoding="utf-8"
        )
    )
    for mat in bpy.data.materials:
        category = mat.get("look_category")
        if not category:
            continue
        chroma = mat.node_tree.nodes.get("Look v3 | Per material chroma")
        chroma.inputs["Saturation"].default_value = style["saturation"].get(category, 1)
        ramp = mat.node_tree.nodes["Look v3 | Soft toon bands"].color_ramp
        if category == "skin":
            for element, color in zip(
                ramp.elements,
                [(0.90, 0.82, 0.98, 1), (1.01, 0.98, 1.08, 1), (1.08, 1.05, 1.13, 1)],
            ):
                element.color = color
    masks = json.loads(
        Path(
            "D:/codex/output/MMD-Surface-Refinement-v1/control-maps/mask-manifest.json"
        ).read_text(encoding="utf-8")
    )["maps"]
    masks = {item["source_image"]: item["mask"] for item in masks}
    surface = json.loads(
        (ROOT / "presets/quality/surface-refinement-v1.json").read_text(
            encoding="utf-8"
        )
    )
    for mat in list(bpy.data.materials):
        if mat.get("performer_id") == "aksiniya" and mat.get("look_category") in {
            "cloth",
            "trim",
        }:
            mask = mask_node(mat, masks)
            surface_material(mat, mask, surface)
    focus = bpy.data.objects.new("Duet | shared head focus", None)
    scene.collection.objects.link(focus)
    arms = [o for o in scene.objects if o.type == "ARMATURE" and o.get("performer_id")]
    for i, arm in enumerate(arms):
        constraint = focus.constraints.new("COPY_LOCATION")
        constraint.target = arm
        constraint.subtarget = next(
            b.name for b in arm.pose.bones if b.mmd_bone.name_j == "頭"
        )
        constraint.influence = 1 if i == 0 else 0.5
    scene.camera.data.dof.use_dof = True
    scene.camera.data.dof.focus_object = focus
    scene.camera.data.dof.aperture_fstop = 10
    # Re-bake static architectural bounce without baking the two moving people.
    hidden = [
        (o, o.hide_render)
        for o in scene.objects
        if o.type == "MESH" and o.get("performer_id")
    ]
    for obj, _previous in hidden:
        obj.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    probe = next(
        o for o in scene.objects if o.type == "LIGHT_PROBE" and o.data.type == "VOLUME"
    )
    probe.select_set(True)
    bpy.context.view_layer.objects.active = probe
    assert bpy.ops.object.lightprobe_cache_bake(subset="SELECTED") == {"FINISHED"}
    for obj, previous in hidden:
        obj.hide_render = previous
    scene["style_family"] = "guanhaizi"
    scene["style_reference_status"] = (
        "Guanhaizi-inspired character treatment, winter-wedding adaptation; not original author shaders"
    )
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(
        filepath=str(args.output_dir / "Franken_Duet_Full.blend")
    )
    scene.render.resolution_percentage = 50
    for frame in [1, 2100, 4200, 8400, 11899]:
        scene.frame_set(frame)
        scene.render.filepath = str(args.output_dir / f"qa-{frame:05d}.png")
        bpy.ops.render.render(write_still=True)
    (args.output_dir / "polish-report.json").write_text(
        json.dumps(
            {
                "stage_target": "supplied Ray preview",
                "character_target": "guanhaizi",
                "adapted_additive_matcap_materials": adapted,
                "dof_fstop": 10,
                "camera_motion_changed": False,
                "static_probe_rebaked_without_characters": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("DUET_POLISH_READY", flush=True)


if __name__ == "__main__":
    main()
