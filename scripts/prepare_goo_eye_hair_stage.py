"""Build bounded eye animation, eye shading/peek, hair shadows and stage surfaces."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs
from snapshot_goo_scene import capture
from study_jelly_eye_inputs import SHA, SOURCE

ROOT = Path("D:/codex/output/MMD-Jelly-Eyes-v1")
PRIVATE = Path("D:/codex/temp/jelly-eye-study-v1")
PREFIX = "Eye hair v1 | "
ACTORS = {
    "aksiniya": {"mesh": "阿克西妮娅2_mesh", "eyes": ["目"], "head": "頭"},
    "ikhor": {
        "mesh": "Ikhor | mesh | Ikhor_mesh",
        "eyes": ["目.002", "目2"],
        "head": "頭",
    },
}


def node(tree, kind, label):
    item = tree.nodes.new(kind)
    item.name = item.label = PREFIX + label
    return item


def link(tree, value, socket):
    if hasattr(value, "is_output"):
        tree.links.new(value, socket)
    else:
        socket.default_value = value


def math(tree, op, a, b, label):
    item = node(tree, "ShaderNodeMath", label)
    item.operation = op
    link(tree, a, item.inputs[0])
    link(tree, b, item.inputs[1])
    return item.outputs[0]


def remap(tree, value, low, high, outlow, outhigh, label):
    item = node(tree, "ShaderNodeMapRange", label)
    item.clamp = True
    item.interpolation_type = "SMOOTHSTEP"
    for key, val in (
        ("Value", value),
        ("From Min", low),
        ("From Max", high),
        ("To Min", outlow),
        ("To Max", outhigh),
    ):
        link(tree, val, item.inputs[key])
    return item.outputs[0]


def color(tree, op, a, b, factor, label):
    item = node(tree, "ShaderNodeMixRGB", label)
    item.blend_type = op
    item.use_clamp = False
    for value, socket in zip((factor, a, b), item.inputs):
        link(tree, value, socket)
    return item.outputs[0]


def vector_scale(tree, value, amount, label):
    item = node(tree, "ShaderNodeVectorMath", label)
    item.operation = "SCALE"
    link(tree, value, item.inputs[0])
    link(tree, amount, item.inputs[3])
    return item.outputs[0]


def raw_shadow(mat, actor):
    tree = mat.node_tree
    info = next(
        (
            n
            for n in tree.nodes
            if n.bl_idname == "ShaderNodeShaderInfo" and n.use_own_light_groups
        ),
        None,
    )
    if info is None:
        info = node(tree, "ShaderNodeShaderInfo", "key shadow information")
        info.use_own_light_groups = True
        info.light_groups.use_default = False
        info.light_groups.groups.add().name = "Goo portrait key | " + actor
    # Same-object hair/face occlusion and external occlusion remain separate until this minimum.
    mat.check_shadow_id = True
    return math(
        tree,
        "MINIMUM",
        info.outputs["Cast Shadows"],
        info.outputs["Self Shadows"],
        "external and self visibility",
    )


def eye_helpers(scene, actor, spec):
    obj = bpy.data.objects[spec["mesh"]]
    arm = obj.find_armature()
    head = spec["head"]
    if head not in arm.pose.bones:
        head = next(b.name for b in arm.pose.bones if b.name.lower() in ("head", "頭"))
    ids = {
        v
        for p in obj.data.polygons
        if obj.data.materials[p.material_index].name in spec["eyes"]
        for v in p.vertices
    }
    deform = (
        arm.matrix_world
        @ arm.pose.bones[head].matrix
        @ arm.data.bones[head].matrix_local.inverted()
        @ arm.matrix_world.inverted()
        @ obj.matrix_world
    )
    helpers = []
    for sign, label in ((1, "L"), (-1, "R")):
        pts = [
            obj.data.vertices[i].co for i in ids if obj.data.vertices[i].co.x * sign > 0
        ]
        center = sum(pts, Vector()) / len(pts)
        helper = bpy.data.objects.new(PREFIX + actor + " eye " + label, None)
        scene.collection.objects.link(helper)
        helper.parent = arm
        helper.parent_type = "BONE"
        helper.parent_bone = head
        bpy.context.view_layer.update()
        helper.matrix_world = deform @ Matrix.Translation(center)
        helper["rest_eye_center"] = list(center)
        helper["actor"] = actor
        helper.empty_display_size = 0.01
        helper.hide_render = True
        helpers.append(helper)
    return helpers


def eyes(scene, report):
    layer = scene.view_layers[0]
    aov = layer.aovs.add()
    aov.name, aov.type = "EyeGlints", "COLOR"
    for actor, spec in ACTORS.items():
        for name in spec["eyes"]:
            mat = bpy.data.materials[name]
            tree = mat.node_tree
            source = tree.nodes["mmd_shader"].outputs["Color"]
            emission = tree.nodes.get("Look v3 | NPR surface") or tree.nodes.get(
                "Ikhor character | controlled NPR surface"
            )
            old = emission.inputs["Color"].links[0].from_socket
            hsv = node(tree, "ShaderNodeSeparateColor", "painted catchlight separation")
            hsv.mode = "HSV"
            tree.links.new(source, hsv.inputs[0])
            value = remap(
                tree,
                hsv.outputs[2],
                0.62,
                0.90,
                0,
                1,
                "existing bright eye details",
            )
            neutral = remap(
                tree,
                hsv.outputs[1],
                0.10,
                0.38,
                1,
                0,
                "preserve colored iris",
            )
            mask = math(
                tree, "MULTIPLY", value, neutral, "painted white catchlights only"
            )
            gain = math(tree, "MULTIPLY", mask, 2.6, "HDR catchlight gain")
            glint = vector_scale(
                tree, (0.88, 0.96, 1.0), gain, "cool white eye radiance"
            )
            final = color(tree, "ADD", old, glint, 1, "iris plus existing catchlight")
            tree.links.new(final, emission.inputs["Color"])
            # A small real reflective closure preserves the authored iris beneath it.
            alpha = (
                tree.nodes.get("Look v3 | PMX alpha")
                or tree.nodes["Ikhor character | preserve original MMD Alpha"]
            )
            old_closure = alpha.inputs[2].links[0].from_socket
            gloss = node(tree, "ShaderNodeBsdfGlossy", "wet corneal reflection")
            gloss.inputs["Color"].default_value = (0.065, 0.075, 0.085, 1)
            gloss.inputs["Roughness"].default_value = 0.055
            add = node(tree, "ShaderNodeAddShader", "NPR eye and wet reflection")
            tree.links.new(old_closure, add.inputs[0])
            tree.links.new(gloss.outputs[0], add.inputs[1])
            tree.links.new(add.outputs[0], alpha.inputs[2])
            export = node(tree, "ShaderNodeOutputAOV", "eye radiance AOV")
            export.aov_name = "EyeGlints"
            visible = vector_scale(
                tree,
                glint,
                tree.nodes["mmd_shader"].outputs["Alpha"],
                "eye glint PMX alpha",
            )
            tree.links.new(visible, export.inputs["Color"])
            report["eyes"].append(
                {
                    "actor": actor,
                    "material": name,
                    "painted_gain": 2.6,
                    "roughness": 0.055,
                }
            )


def jelly(scene, report):
    sys.path.insert(0, str(PRIVATE))
    import jelly_eye_pro as addon

    addon.register()
    for actor, spec in ACTORS.items():
        obj = bpy.data.objects[spec["mesh"]]
        settings = scene.jelly_eye
        settings.auto_detect = False
        settings.armature = obj.find_armature()
        settings.force_selected = False
        settings.eye_l = settings.eye_r = ""
        found = addon.naming.find_eye_bones(settings.armature)
        settings.eye_l = found.get("l", "")
        settings.eye_r = found.get("r", "")
        settings.blink_obj = obj
        settings.blink_mode = "SHAPE_KEY"
        settings.blink_key = ""
        settings.blink_keys.clear()
        for name, side, score in addon.naming.find_close_shapes(obj):
            key = obj.data.shape_keys.key_blocks[name]
            basis = obj.data.shape_keys.key_blocks[0]
            energy = [0.0, 0.0]
            eye_ids = {
                v
                for poly in obj.data.polygons
                if obj.data.materials[poly.material_index].name in spec["eyes"]
                for v in poly.vertices
            }
            for index in eye_ids:
                p = basis.data[index].co
                energy[0 if p.x >= 0 else 1] += (key.data[index].co - p).length_squared
            if max(energy) > 1e-10:
                if energy[0] > energy[1] * 5:
                    side = "L"
                elif energy[1] > energy[0] * 5:
                    side = "R"
            item = settings.blink_keys.add()
            item.name, item.side, item.enabled = name, side, True
        settings.eye_materials.clear()
        for name in spec["eyes"]:
            item = settings.eye_materials.add()
            item.material = bpy.data.materials[name]
            item.enabled = True
        settings.amplitude = 0.9
        settings.size = 0.14
        settings.elasticity = 1.1
        settings.damping = 0.5
        settings.move = 0.035
        settings.pupil_squeeze = 1
        settings.lateral_squeeze = 0.8
        settings.axis_mode = "Z"
        settings.bake_start, settings.bake_end = 4080, 4441
        count = addon.core.setup(bpy.context, [obj])
        assert count == (1, 2), (actor, count, dict(found))
        allowed = {
            v
            for p in obj.data.polygons
            if obj.data.materials[p.material_index].name in spec["eyes"]
            for v in p.vertices
        }
        masked = set()
        for group in obj.vertex_groups:
            if group.name.startswith("JE_Mask"):
                masked.update(
                    v.index
                    for v in obj.data.vertices
                    if any(g.group == group.index and g.weight > 0 for g in v.groups)
                )
        assert masked and masked <= allowed, (
            actor,
            "Mask escaped the audited iris/highlight materials",
        )
        row = {
            "actor": actor,
            "object": obj.name,
            "eye_bones": dict(found),
            "blink_sources": [(x.name, x.side) for x in settings.blink_keys],
            "bake_range": [4080, 4441],
            "modifiers": count[1],
            "masked_vertices": len(masked),
            "allowed_vertices": len(allowed),
            "amplitude": 0.9,
            "size": 0.14,
            "damping": 0.5,
            "move": 0.035,
        }
        obj["eye_hair_v1_jelly_settings"] = json.dumps(row, ensure_ascii=False)
        report["jelly"].append(row)
    # Native GN and baked FCurves survive without an installed add-on or its Scene UI.
    addon.unregister()


def hair(scene, report):
    for name in ("BangPeek", "HairVisibility"):
        aov = scene.view_layers[0].aovs.add()
        aov.name, aov.type = name, "VALUE"
    helpers = {actor: eye_helpers(scene, actor, spec) for actor, spec in ACTORS.items()}
    for mat in bpy.data.materials:
        actor = mat.get("performer_id")
        kind = mat.get("look_category") or mat.get("ikhor_material_role")
        if actor not in ACTORS or kind != "hair" or not mat.node_tree:
            continue
        tree = mat.node_tree
        visible = raw_shadow(mat, actor)
        shadow_export = node(
            tree, "ShaderNodeOutputAOV", "native hair visibility diagnostic"
        )
        shadow_export.aov_name = "HairVisibility"
        tree.links.new(visible, shadow_export.inputs["Value"])
        shadow = remap(tree, visible, 0, 1, 0.43, 1, "hair shadow response")
        target = (
            tree.nodes.get("Reference transfer | form times directional response")
            if actor == "aksiniya"
            else tree.nodes.get("Ikhor character | form times actual response")
        )
        assert target, (mat.name, "Missing audited form/occlusion boundary")
        tree.links.new(shadow, target.inputs[1])
        # Native visibility also gates the existing rim and the drawn hair band.
        rim_gate = tree.nodes.get("Goo daylight v2 | rim cast shadow permission")
        if rim_gate:
            tree.links.new(visible, rim_gate.inputs["Value"])
        gain = (
            tree.nodes.get("Character layers | hair highlight strength")
            if actor == "aksiniya"
            else tree.nodes.get("Goo rim glow | retained hair highlight gain")
        )
        if gain:
            for out in gain.outputs:
                destinations = [l.to_socket for l in list(out.links)]
                gated = math(
                    tree,
                    "MULTIPLY",
                    out,
                    remap(tree, visible, 0, 1, 0.18, 1, "hair glint shadow permission"),
                    "shadow gated hair band",
                )
                for destination in destinations:
                    tree.links.new(gated, destination)
        oval_masks = []
        for side, helper in zip(("L", "R"), helpers[actor]):
            coord = node(tree, "ShaderNodeTexCoord", side + " eye tracking")
            coord.object = helper
            separate = node(tree, "ShaderNodeSeparateXYZ", side + " eye space")
            tree.links.new(coord.outputs["Object"], separate.inputs[0])
            x = math(tree, "DIVIDE", separate.outputs["X"], 0.026, side + " eye width")
            z = math(tree, "DIVIDE", separate.outputs["Z"], 0.016, side + " eye height")
            r2 = math(
                tree,
                "ADD",
                math(tree, "MULTIPLY", x, x, side + " x2"),
                math(tree, "MULTIPLY", z, z, side + " z2"),
                side + " eye ellipse",
            )
            oval = remap(tree, r2, 0.52, 1.35, 1, 0, side + " eye feather")
            depth = math(
                tree, "ABSOLUTE", separate.outputs["Y"], 0, side + " eye depth"
            )
            front = remap(tree, depth, 0.035, 0.075, 1, 0, side + " exclude rear hair")
            oval_masks.append(math(tree, "MULTIPLY", oval, front, side + " eye region"))
        peek = math(
            tree,
            "MULTIPLY",
            math(tree, "MAXIMUM", *oval_masks, "two eye regions"),
            0.32,
            "subtle bang transparency",
        )
        peek_export = node(tree, "ShaderNodeOutputAOV", "eye peek mask diagnostic")
        peek_export.aov_name = "BangPeek"
        tree.links.new(peek, peek_export.inputs["Value"])
        output = next(
            n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
        )
        previous = output.inputs["Surface"].links[0].from_socket
        clear = node(tree, "ShaderNodeBsdfTransparent", "eye peek transparent layer")
        mix = node(tree, "ShaderNodeMixShader", "eye region bang peek")
        tree.links.new(peek, mix.inputs[0])
        tree.links.new(previous, mix.inputs[1])
        tree.links.new(clear.outputs[0], mix.inputs[2])
        tree.links.new(mix.outputs[0], output.inputs["Surface"])
        report["hair"].append(
            {
                "material": mat.name,
                "actor": actor,
                "shadow_min": 0.43,
                "peek_opacity_reduction": 0.32,
                "check_shadow_id": True,
            }
        )
    for name in ("颜", "颜.001"):
        mat = bpy.data.materials[name]
        actor = mat["performer_id"]
        visible = raw_shadow(mat, actor)
        response = mat.node_tree.nodes["Goo portrait | separate cast shadow response"]
        mat.node_tree.links.new(visible, response.inputs["Value"])
        response.inputs["To Min"].default_value = 0.68 if actor == "aksiniya" else 0.74
        report["face_shadows"].append(
            {
                "material": name,
                "shadow_min": response.inputs["To Min"].default_value,
                "self_and_external": True,
            }
        )


def stage(scene, report):
    for name in (
        "Stage art | ground only | mat_10.001",
        "mat_20.008",
        "mat_20.012",
        "mat_24.001",
    ):
        mat = bpy.data.materials[name]
        tree = mat.node_tree
        original = tree.nodes["Reference | ordinary PBR control"]
        image = next(
            n
            for n in tree.nodes
            if n.type == "TEX_IMAGE" and n.image and "_D.png" in n.image.name
        )
        albedo = image.outputs["Color"]
        pbr = node(tree, "ShaderNodeBsdfPrincipled", "stage reflective surface")
        link(tree, albedo, pbr.inputs["Base Color"])
        for key in ("Normal", "Metallic"):
            old = original.inputs[key]
            link(
                tree,
                old.links[0].from_socket if old.is_linked else old.default_value,
                pbr.inputs[key],
            )
        metal = name == "mat_24.001"
        pbr.inputs["Roughness"].default_value = 0.20 if metal else 0.27
        pbr.inputs["Coat Weight"].default_value = 0.25 if metal else 0.3
        pbr.inputs["Coat Roughness"].default_value = 0.12
        if metal:
            mask = (
                original.inputs["Metallic"].links[0].from_socket
                if original.inputs["Metallic"].is_linked
                else original.inputs["Metallic"].default_value
            )
            factor = math(
                tree, "MULTIPLY", mask, 0.78, "authored metal region permission"
            )
        else:
            geo = node(tree, "ShaderNodeNewGeometry", "world marble coordinates")
            wave = node(tree, "ShaderNodeTexWave", "subtle marble veins")
            wave.wave_type = "BANDS"
            wave.bands_direction = "DIAGONAL"
            wave.inputs["Scale"].default_value = 0.85
            wave.inputs["Distortion"].default_value = 7.5
            wave.inputs["Detail"].default_value = 3
            tree.links.new(geo.outputs["Position"], wave.inputs["Vector"])
            veins = remap(
                tree, wave.outputs["Fac"], 0.72, 0.96, 1, 0.64, "fine gray blue veins"
            )
            base = color(
                tree, "MULTIPLY", albedo, veins, 1, "original stone with marble grain"
            )
            tree.links.new(base, pbr.inputs["Base Color"])
            bump = node(tree, "ShaderNodeBump", "submillimeter stone relief")
            bump.inputs["Strength"].default_value = 0.11
            bump.inputs["Distance"].default_value = 0.0005
            tree.links.new(wave.outputs["Fac"], bump.inputs["Height"])
            old = original.inputs["Normal"]
            if old.is_linked:
                tree.links.new(old.links[0].from_socket, bump.inputs["Normal"])
            tree.links.new(bump.outputs["Normal"], pbr.inputs["Normal"])
            hsv = node(tree, "ShaderNodeSeparateColor", "stone versus blue textile")
            hsv.mode = "HSV"
            tree.links.new(albedo, hsv.inputs[0])
            neutral = remap(
                tree,
                hsv.outputs[1],
                0.16,
                0.40,
                1,
                0,
                "neutral stone permission",
            )
            bright = remap(
                tree,
                hsv.outputs[2],
                0.08,
                0.25,
                0,
                1,
                "stone brightness permission",
            )
            factor = math(
                tree,
                "MULTIPLY",
                math(tree, "MULTIPLY", neutral, bright, "stone region"),
                0.60,
                "marble surface mix",
            )
        output = next(
            n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
        )
        previous = output.inputs["Surface"].links[0].from_socket
        mix = node(tree, "ShaderNodeMixShader", "retained stage and material upgrade")
        link(tree, factor, mix.inputs[0])
        tree.links.new(previous, mix.inputs[1])
        tree.links.new(pbr.outputs[0], mix.inputs[2])
        tree.links.new(mix.outputs[0], output.inputs["Surface"])
        report["stage"].append(
            {
                "material": name,
                "kind": "authored-mask metal"
                if metal
                else "neutral-stone-only procedural marble",
                "old_atlas_and_mask_retained": True,
            }
        )
    candle = bpy.data.materials["mat_115.001"]
    for n in candle.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            before = n.inputs["Emission Strength"].default_value
            n.inputs["Emission Strength"].default_value = max(before, 60)
            report["stage"].append(
                {
                    "material": candle.name,
                    "kind": "existing candle emission",
                    "before": before,
                    "after": n.inputs["Emission Strength"].default_value,
                }
            )
    for obj in scene.objects:
        if (
            obj.type == "LIGHT"
            and obj.data.type == "POINT"
            and any(t in obj.name.lower() for t in ("candle", "烛"))
        ):
            obj.data.energy *= 1.18
            report["candle_lights"].append({"name": obj.name, "watts": obj.data.energy})


def glow(scene, report):
    tree = scene.compositing_node_group
    layer = scene.view_layers[0]
    aov = layer.aovs.add()
    aov.name, aov.type = "ContourRim", "COLOR"
    for material in bpy.data.materials:
        if not material.node_tree:
            continue
        shader = material.node_tree
        old_export = shader.nodes.get("Goo window wrap | actual rim and hair radiance")
        if not old_export or not old_export.inputs["Color"].is_linked:
            continue
        pure = old_export.inputs["Color"].links[0].from_socket
        if pure.node.name == "Goo window wrap | rim and existing hair-band signal":
            pure = pure.node.inputs[0].links[0].from_socket
        export = node(shader, "ShaderNodeOutputAOV", "contour only radiance")
        export.aov_name = "ContourRim"
        shader.links.new(pure, export.inputs["Color"])
    layer.update_render_passes()
    bpy.context.view_layer.update()
    render = next(n for n in tree.nodes if n.type == "R_LAYERS")
    for name, strength, size in (
        ("Goo window wrap | tight white edge bloom", 1.3, 0.022),
        ("Goo window wrap | soft outer edge diffusion", 0.58, 0.065),
    ):
        n = tree.nodes[name]
        n.inputs["Strength"].default_value = strength
        n.inputs["Size"].default_value = size
        tree.links.new(render.outputs["ContourRim"], n.inputs["Image"])
        report["glow"].append({"node": name, "strength": strength, "size": size})
    layer.update_render_passes()
    bpy.context.view_layer.update()
    tone = tree.nodes["Goo Tyndall | compress highlights after glow"]
    old = tone.inputs[1].links[0].from_socket
    glare = node(tree, "CompositorNodeGlare", "small eye glint bloom")
    for key, value in (
        ("Type", "Fog Glow"),
        ("Quality", "High"),
        ("Threshold", 0.8),
        ("Strength", 0.18),
        ("Size", 0.006),
    ):
        glare.inputs[key].default_value = value
    tree.links.new(render.outputs["EyeGlints"], glare.inputs["Image"])
    final = color(
        tree, "ADD", old, glare.outputs["Glare"], 1, "eye bloom before shoulder"
    )
    tree.links.new(final, tone.inputs[1])
    tree.links.new(final, tree.nodes["Goo Tyndall | linear luminance"].inputs[0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iteration", default="production-v4")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    assert Path(args.iteration).name == args.iteration
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA
    production = ROOT / args.iteration
    production.mkdir(parents=True, exist_ok=False)
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    before = capture()
    report = {
        "source": str(SOURCE),
        "source_sha256": SHA,
        "jelly": [],
        "eyes": [],
        "hair": [],
        "face_shadows": [],
        "stage": [],
        "glow": [],
        "candle_lights": [],
    }
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    eyes(scene, report)
    hair(scene, report)
    stage(scene, report)
    import goo_engine_light_groups

    goo_engine_light_groups.sync_light_groups()
    glow(scene, report)
    jelly(scene, report)
    after = capture()
    report["preserved"] = {
        "original_actions": all(
            after["actions"].get(k) == v for k, v in before["actions"].items()
        ),
        "original_meshes": before["geometry"] == after["geometry"],
        "images": before["images"] == after["images"],
        "bones_morphs_cameras": before["samples"] == after["samples"],
        "fps": before["fps"] == after["fps"],
    }
    assert all(report["preserved"].values()), report["preserved"]
    (PRIVATE / "source-snapshot.json").write_text(
        json.dumps(before, ensure_ascii=False), encoding="utf-8"
    )
    (PRIVATE / "new-snapshot.json").write_text(
        json.dumps(after, ensure_ascii=False), encoding="utf-8"
    )
    scene.frame_set(4290)
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 24
    scene.render.use_motion_blur = False
    scene.render.image_settings.file_format = "PNG"
    project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
    scene.render.filepath = str(production / "portrait-4290.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report.update(
        project=str(project),
        project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
        runtime=bpy.app.binary_path,
        addon_required_to_reopen=False,
        physics_resimulated=False,
        art_status="pending user review",
        jelly_verified_range=[4080, 4441],
    )
    (production / "preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 95
    for frame, label in ((4290, "portrait"), (4160, "blink"), (4140, "opening")):
        scene.frame_set(frame)
        scene.render.filepath = str(production / f"{label}-{frame}.jpg")
        bpy.ops.render.render(write_still=True)
        print("EYE_HAIR_STAGE_CONTROL", frame, flush=True)
    print("EYE_HAIR_STAGE_PREPARED", project, flush=True)


if __name__ == "__main__":
    main()
