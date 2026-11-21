"""Isolated Goo mechanism experiments; never load or edit a production project."""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path("D:/codex/output/Goo-MME-Feature-Study-2026-11-16")
TEMP = Path("D:/codex/temp/Goo-MME-Feature-Study-2026-11-16")


def scene(width=512, height=512):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x, s.render.resolution_y = width, height
    s.render.resolution_percentage = 100
    s.eevee.taa_render_samples = 24
    s.render.use_compositing = False
    s.view_settings.view_transform = "Standard"
    s.world = bpy.data.worlds.new("Black research world")
    s.world.use_nodes = True
    s.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
    bpy.ops.object.camera_add(location=(4, -6, 5))
    cam = bpy.context.object
    cam.rotation_euler = (
        (Vector((0, 0, 0.4)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    )
    cam.data.type, cam.data.ortho_scale = "ORTHO", 5.3
    s.camera = cam
    return s


def mat(name, color=(0, 0, 0, 1), emission=True):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    shader = t.nodes.new(
        "ShaderNodeEmission" if emission else "ShaderNodeBsdfPrincipled"
    )
    shader.inputs["Color" if emission else "Base Color"].default_value = color
    if not emission:
        shader.inputs["Roughness"].default_value = 1
    t.links.new(shader.outputs[0], out.inputs["Surface"])
    return m, shader


def sun(name="Key", color=(1, 1, 1), energy=3):
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 6))
    ob = bpy.context.object
    ob.name = name
    ob.data.color, ob.data.energy, ob.data.angle = color, energy, 0.005
    return ob


def plane(m):
    bpy.ops.mesh.primitive_plane_add(size=6)
    ob = bpy.context.object
    ob.data.materials.append(m)
    return ob


def render(s, folder, label):
    raw = TEMP / "linear" / folder.name / (label + ".exr")
    raw.parent.mkdir(parents=True, exist_ok=True)
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.image_settings.color_depth = "32"
    s.render.filepath = str(raw)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(str(raw), check_existing=False)
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(
        image.size[1], image.size[0], 4
    )
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "16"
    image.save_render(str(folder / (label + ".png")), scene=s)
    bpy.data.images.remove(image)
    point = world_to_camera_view(s, s.camera, Vector((0, 0, 0)))
    x, y = int(point.x * pixels.shape[1]), int(point.y * pixels.shape[0])
    roi = pixels[max(y - 4, 0) : y + 5, max(x - 4, 0) : x + 5, :3]
    return {
        "rgb_min": float(pixels[:, :, :3].min()),
        "rgb_max": float(pixels[:, :, :3].max()),
        "nonzero_rgb_values": int(np.count_nonzero(np.abs(pixels[:, :, :3]) > 1e-7)),
        "ground_origin_mean": roi.mean(axis=(0, 1)).tolist(),
        "linear_exr": str(raw),
    }


def curvature(folder):
    results = {}
    for label, gain, forward in (
        ("curvature_raw", 1, False),
        ("curvature_gain500", 500, False),
        ("curvature_gain500_info", 500, True),
    ):
        s = scene()
        floor, _ = mat("Black depth-writing floor")
        plane(floor)
        sun()
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=48, ring_count=24, radius=1, location=(0, 0, 1)
        )
        sphere = bpy.context.object
        for p in sphere.data.polygons:
            p.use_smooth = True
        m, emit = mat(label)
        sphere.data.materials.append(m)
        t = m.node_tree
        c = t.nodes.new("ShaderNodeCurvature")
        c.inputs["Thickness"].default_value = 0.08
        c.inputs["Sample Radius"].default_value = 2
        mul = t.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = gain
        t.links.new(c.outputs["Scene Rim"], mul.inputs[0])
        result = mul.outputs[0]
        if forward:
            info = t.nodes.new("ShaderNodeShaderInfo")
            bw = t.nodes.new("ShaderNodeRGBToBW")
            t.links.new(info.outputs["Diffuse Shading"], bw.inputs[0])
            tiny = t.nodes.new("ShaderNodeMath")
            tiny.operation = "MULTIPLY"
            tiny.inputs[1].default_value = 0.000001
            t.links.new(bw.outputs[0], tiny.inputs[0])
            add = t.nodes.new("ShaderNodeMath")
            add.operation = "ADD"
            t.links.new(result, add.inputs[0])
            t.links.new(tiny.outputs[0], add.inputs[1])
            result = add.outputs[0]
        t.links.new(result, emit.inputs[0])
        results[label] = render(s, folder, label)
    return results


def shadows(folder):
    results = {}
    for label, check, join in (
        ("shadow_id_off", False, False),
        ("shadow_external", True, False),
        ("shadow_same_object", True, True),
    ):
        s = scene()
        sun()
        m, emit = mat("RG = Cast / Self")
        m.check_shadow_id = check
        ground = plane(m)
        t = m.node_tree
        info = t.nodes.new("ShaderNodeShaderInfo")
        rgb = t.nodes.new("ShaderNodeCombineXYZ")
        t.links.new(info.outputs["Cast Shadows"], rgb.inputs[0])
        t.links.new(info.outputs["Self Shadows"], rgb.inputs[1])
        t.links.new(rgb.outputs[0], emit.inputs[0])
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.3))
        cube = bpy.context.object
        black, _ = mat("Black occluder")
        cube.data.materials.append(black)
        if join:
            bpy.ops.object.select_all(action="DESELECT")
            ground.select_set(True)
            cube.select_set(True)
            bpy.context.view_layer.objects.active = ground
            bpy.ops.object.join()
        results[label] = render(s, folder, label)
        if label == "shadow_external":
            bpy.ops.wm.save_as_mainfile(filepath=str(folder / "Cast_Self_Study.blend"))
    return results


def groups(folder):
    results = {}
    for label, group, native, own in (
        ("bsdf_red", "Red", False, None),
        ("bsdf_blue", "Blue", False, None),
        ("info_red", "Red", True, None),
        ("info_blue", "Blue", True, None),
        ("info_own_blue", "Red", True, "Blue"),
    ):
        s = scene()
        for name, color in (("Red", (1, 0, 0)), ("Blue", (0, 0, 1))):
            ob = sun(name, color)
            ob.data.light_groups.use_default = False
            ob.data.light_groups.groups.add().name = name
        m, shader = mat(label, (1, 1, 1, 1), emission=native)
        m.light_groups.use_default = False
        m.light_groups.groups.add().name = group
        plane(m)
        if native:
            info = m.node_tree.nodes.new("ShaderNodeShaderInfo")
            if own:
                info.use_own_light_groups = True
                info.light_groups.use_default = False
                info.light_groups.groups.add().name = own
            m.node_tree.links.new(info.outputs["Diffuse Shading"], shader.inputs[0])
        import goo_engine_light_groups

        goo_engine_light_groups.sync_light_groups()
        results[label] = render(s, folder, label)
    return results


def ramps_sdf(folder, correct_aspect=False):
    s = scene(768, 640)
    s.camera.location = (0, 0, 5)
    s.camera.rotation_euler = (0, 0, 0)
    # Camera local -Z points down, and text lies in the XY plane.
    s.camera.data.ortho_scale = 5.4
    for index, kind in enumerate(
        ("ShaderNodeValToRGB", "ShaderNodeOKLabColorRamp", "ShaderNodeSdfPrimitive")
    ):
        y = 1.2 - index * 1.2
        m, emit = mat(kind)
        ob = plane(m)
        ob.scale = (4 / 6, 0.7 / 6, 1)
        ob.location.y = y
        t = m.node_tree
        uv = t.nodes.new("ShaderNodeTexCoord")
        if index < 2:
            separate = t.nodes.new("ShaderNodeSeparateXYZ")
            t.links.new(uv.outputs["Generated"], separate.inputs[0])
            ramp = t.nodes.new(kind)
            ramp.color_ramp.elements[0].color = (0.8, 0.02, 0.03, 1)
            ramp.color_ramp.elements[1].color = (0.02, 0.12, 0.8, 1)
            t.links.new(separate.outputs["X"], ramp.inputs[0])
            color = ramp.outputs[0]
        else:
            v = t.nodes.new("ShaderNodeVectorMath")
            v.operation = "SUBTRACT"
            v.inputs[1].default_value = (0.5, 0.5, 0)
            t.links.new(uv.outputs["Generated"], v.inputs[0])
            primitive = t.nodes.new(kind)
            primitive.mode = "HEART_2D"
            primitive.inputs["Size"].default_value = 0.7
            coord = v.outputs[0]
            if correct_aspect:
                aspect = t.nodes.new("ShaderNodeVectorMath")
                aspect.operation = "MULTIPLY"
                aspect.inputs[1].default_value = (4 / 0.7, 1, 1)
                t.links.new(coord, aspect.inputs[0])
                coord = aspect.outputs[0]
            t.links.new(coord, primitive.inputs["Vector"])
            mask = t.nodes.new("ShaderNodeMath")
            mask.operation = "LESS_THAN"
            mask.inputs[1].default_value = 0
            t.links.new(primitive.outputs["Distance"], mask.inputs[0])
            color = mask.outputs[0]
        t.links.new(color, emit.inputs[0])
        bpy.ops.object.text_add(location=(-2, y + 0.46, 0.02))
        text = bpy.context.object
        text.data.body = (
            "Blender RGB ramp",
            "Goo OKLab ramp",
            "Goo SDF: shader mask, not geometry",
        )[index]
        text.data.size = 0.15
        white, _ = mat("Label", (1, 1, 1, 1))
        text.data.materials.append(white)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "Ramp_SDF_Study.blend"))
    return {"ramp_sdf": render(s, folder, "ramp_sdf")}


def ramps_sdf_square(folder):
    return ramps_sdf(folder, correct_aspect=True)


def screen_depth(folder):
    results = {}
    cases = (
        ("screen_disabled", False, False, False, False),
        ("screen_global_only", True, False, False, False),
        ("screen_color_enabled", True, True, False, False),
        ("screen_depth_enabled", True, True, True, False),
        ("screen_shifted", True, True, False, True),
    )
    for label, ray, refraction, depth, shift in cases:
        s = scene()
        s.camera.location = (0, 0, 5)
        s.camera.rotation_euler = (0, 0, 0)
        s.camera.data.ortho_scale = 5
        s.eevee.use_raytracing = ray
        for x, c in ((-1.5, (1, 0, 0, 1)), (1.5, (0, 0, 1, 1))):
            m, _ = mat("Background", c)
            ob = plane(m)
            ob.scale.x = 0.5
            ob.location.x = x
        m, emit = mat("Camera buffer receiver")
        m.use_raytrace_refraction = refraction
        ob = plane(m)
        ob.scale = (0.25, 0.25, 1)
        ob.location.z = 0.2
        t = m.node_tree
        node = t.nodes.new("ShaderNodeScreenspaceInfo")
        if shift:
            geom = t.nodes.new("ShaderNodeNewGeometry")
            transform = t.nodes.new("ShaderNodeVectorTransform")
            transform.vector_type = "POINT"
            transform.convert_from, transform.convert_to = "WORLD", "CAMERA"
            t.links.new(geom.outputs["Position"], transform.inputs[0])
            flip = t.nodes.new("ShaderNodeVectorMath")
            flip.operation = "MULTIPLY"
            flip.inputs[1].default_value = (1, 1, -1)
            t.links.new(transform.outputs[0], flip.inputs[0])
            offset = t.nodes.new("ShaderNodeVectorMath")
            offset.operation = "ADD"
            offset.inputs[1].default_value = (0.8, 0, 0)
            t.links.new(flip.outputs[0], offset.inputs[0])
            t.links.new(offset.outputs[0], node.inputs["View Position"])
        t.links.new(
            node.outputs["Scene Depth" if depth else "Scene Color"], emit.inputs[0]
        )
        results[label] = render(s, folder, label)
        if label == "screen_color_enabled":
            bpy.ops.wm.save_as_mainfile(
                filepath=str(folder / "Screenspace_Study.blend")
            )
    return results


def set_depth(folder, linked=False):
    results = {}
    for label, depth in (("depth_unlinked", None), ("depth_moved_behind", 6.0)):
        s = scene()
        s.camera.location = (0, 0, 5)
        s.camera.rotation_euler = (0, 0, 0)
        s.camera.data.ortho_scale = 5
        red, _ = mat("Red background", (1, 0, 0, 1))
        plane(red)
        blue, emit = mat("Blue foreground", (0, 0, 1, 1))
        ob = plane(blue)
        ob.scale = (0.25, 0.25, 1)
        ob.location.z = 0.2
        t = blue.node_tree
        node = t.nodes.new("ShaderNodeSetDepth")
        t.links.new(emit.outputs[0], node.inputs["Shader"])
        if depth is not None:
            if linked:
                value = t.nodes.new("ShaderNodeValue")
                value.outputs[0].default_value = depth
                t.links.new(value.outputs[0], node.inputs["View Depth"])
            else:
                node.inputs["View Depth"].default_value = depth
        output = next(n for n in t.nodes if n.type == "OUTPUT_MATERIAL")
        t.links.new(node.outputs[0], output.inputs["Surface"])
        results[label] = render(s, folder, label)
    return results


def set_depth_linked(folder):
    return set_depth(folder, linked=True)


def signals(folder):
    results = {}
    for label, energy, occluded in (
        ("signals_power1", 1, False),
        ("signals_power4", 4, False),
        ("signals_occluded", 1, True),
    ):
        s = scene()
        sun(energy=energy)
        m, emit = mat("R=HalfLambert G=Diffuse B=Cast")
        plane(m)
        t = m.node_tree
        info = t.nodes.new("ShaderNodeShaderInfo")
        bw = t.nodes.new("ShaderNodeRGBToBW")
        t.links.new(info.outputs["Diffuse Shading"], bw.inputs[0])
        rgb = t.nodes.new("ShaderNodeCombineXYZ")
        t.links.new(info.outputs["Half-lambert factor"], rgb.inputs[0])
        t.links.new(bw.outputs[0], rgb.inputs[1])
        t.links.new(info.outputs["Cast Shadows"], rgb.inputs[2])
        t.links.new(rgb.outputs[0], emit.inputs[0])
        if occluded:
            bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.3))
            black, _ = mat("Black occluder")
            bpy.context.object.data.materials.append(black)
        results[label] = render(s, folder, label)
    return results


def light_info(folder):
    s = scene()
    light = sun(energy=1)
    m, emit = mat("Light Info uniform update")
    plane(m)
    t = m.node_tree
    info = t.nodes.new("ShaderNodeLightInfo")
    info.light_object = light
    rgb = t.nodes.new("ShaderNodeCombineXYZ")
    t.links.new(info.outputs["Light Power"], rgb.inputs[0])
    t.links.new(info.outputs["Perceptual Power"], rgb.inputs[1])
    t.links.new(rgb.outputs[0], emit.inputs[0])
    results = {}
    for frame, energy, tag in ((1, 1, False), (2, 4, False), (3, 2, True)):
        s.frame_set(frame)
        light.data.energy = energy
        if tag:
            t.update_tag()
        bpy.context.view_layer.update()
        label = "light_info_" + str(frame)
        results[label] = render(s, folder, label)
        results[label].update(light_energy=energy, manual_tree_tag=tag)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        choices=(
            "curvature",
            "shadows",
            "groups",
            "ramps_sdf",
            "ramps_sdf_square",
            "screen_depth",
            "set_depth",
            "set_depth_linked",
            "signals",
            "light_info",
        ),
        required=True,
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    folder = ROOT / args.case
    folder.mkdir(parents=True, exist_ok=False)
    results = globals()[args.case](folder)
    report = {
        "case": args.case,
        "runtime": bpy.app.binary_path,
        "build": bpy.app.build_hash.decode(),
        "results": results,
        "production_loaded": False,
        "production_modified": False,
    }
    (folder / "measurements.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("GOO_FEATURE_EXPERIMENT_COMPLETE", args.case, flush=True)


if __name__ == "__main__":
    main()
