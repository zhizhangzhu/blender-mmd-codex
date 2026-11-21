"""Isolate normal design, local AO, metallic trim and real volumetric light.

These are experimental modules applied to independent copies of the validated
scene. Existing render caches, source geometry, actions and prefs are preserved.
"""

import argparse
import array
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_caption_render import output_file
from mmd_half_lambert import apply_half_lambert


def position_hash(mesh):
    values = array.array("f", [0]) * (len(mesh.data.vertices) * 3)
    mesh.data.vertices.foreach_get("co", values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def pose_hash(scene, arm, frame):
    scene.frame_set(frame)
    values = array.array(
        "f", [v for b in arm.pose.bones for row in b.matrix for v in row]
    )
    return hashlib.sha256(values.tobytes()).hexdigest()


def face_normals(mesh, settings):
    data = mesh.data
    slots = {i for i, mat in enumerate(data.materials) if mat and mat.name == "颜"}
    vertices = {
        v for p in data.polygons if p.material_index in slots for v in p.vertices
    }
    bounds = [
        [
            min(data.vertices[i].co[a] for i in vertices),
            max(data.vertices[i].co[a] for i in vertices),
        ]
        for a in range(3)
    ]
    center = Vector(
        (
            (bounds[0][0] + bounds[0][1]) / 2,
            bounds[1][1] + settings["center_behind_face"],
            (bounds[2][0] + bounds[2][1]) / 2,
        )
    )
    values = [tuple(n.vector) for n in data.corner_normals]
    count = 0
    for poly in data.polygons:
        if poly.material_index not in slots:
            continue
        for index in poly.loop_indices:
            co = data.vertices[data.loops[index].vertex_index].co
            radial = Vector(
                tuple(
                    (co[a] - center[a]) / settings["ellipsoid_radius"][a] ** 2
                    for a in range(3)
                )
            ).normalized()
            old = Vector(values[index])
            # Do not turn an intentionally back-facing loop inside out.
            if old.dot(radial) <= 0:
                continue
            values[index] = tuple(old.lerp(radial, settings["mix"]).normalized())
            count += 1
    data.normals_split_custom_set(values)
    data.update()
    return {
        "face_vertices": len(vertices),
        "modified_corner_normals": count,
        "center": list(center),
        "settings": settings,
    }


def local_ao(scene, settings, directory):
    layer = scene.view_layers[0]
    aov = layer.aovs.add()
    aov.name = "QualityAO"
    aov.type = "VALUE"
    changed = []
    for mat in bpy.data.materials:
        category = mat.get("look_category")
        strength = settings["strength"].get(category, 0)
        if not strength or mat.name.endswith("+"):
            continue
        t = mat.node_tree
        surface = t.nodes["Look v3 | NPR surface"]
        previous = surface.inputs["Color"].links[0].from_socket
        ao = t.nodes.new("ShaderNodeAmbientOcclusion")
        ao.name = "Quality | local AO"
        ao.inputs["Distance"].default_value = settings["distance"]
        ao.samples = settings["samples"]
        ao.only_local = False
        gain = t.nodes.new("ShaderNodeMath")
        gain.operation = "MULTIPLY_ADD"
        t.links.new(ao.outputs["AO"], gain.inputs[0])
        gain.inputs[1].default_value = strength
        gain.inputs[2].default_value = 1 - strength
        mix = t.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.name = "Quality | bounded local occlusion"
        mix.inputs[0].default_value = 1
        t.links.new(previous, mix.inputs[1])
        t.links.new(gain.outputs[0], mix.inputs[2])
        t.links.new(mix.outputs[0], surface.inputs["Color"])
        out = t.nodes.new("ShaderNodeOutputAOV")
        out.aov_name = "QualityAO"
        t.links.new(ao.outputs["AO"], out.inputs["Value"])
        changed.append(mat.name)
    layer.update_render_passes()
    tree = scene.compositing_node_group
    render = next(n for n in tree.nodes if n.type == "R_LAYERS")
    output_file(tree, directory, "ao", render.outputs["QualityAO"], False)
    return {"materials": changed, "settings": settings, "aov": "QualityAO"}


def metallic_trim(settings):
    changed = []
    for mat in bpy.data.materials:
        if mat.get("look_category") != "trim" or mat.name.endswith("+"):
            continue
        t = mat.node_tree
        out = next(n for n in t.nodes if n.type == "OUTPUT_MATERIAL")
        previous = out.inputs["Surface"].links[0].from_socket
        mmd = t.nodes["mmd_shader"]
        bsdf = t.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.name = "Quality | metallic accessory"
        t.links.new(mmd.outputs["Color"], bsdf.inputs["Base Color"])
        t.links.new(mmd.outputs["Alpha"], bsdf.inputs["Alpha"])
        bsdf.inputs["Metallic"].default_value = settings["metallic"]
        bsdf.inputs["Roughness"].default_value = settings["roughness"]
        bsdf.inputs["Coat Weight"].default_value = settings["coat"]
        blend = t.nodes.new("ShaderNodeMixShader")
        blend.name = "Quality | NPR and physical trim"
        blend.inputs[0].default_value = settings["mix"]
        t.links.new(previous, blend.inputs[1])
        t.links.new(bsdf.outputs[0], blend.inputs[2])
        t.links.new(blend.outputs[0], out.inputs["Surface"])
        changed.append(mat.name)
    return {"materials": changed, "settings": settings}


def volume(scene, settings):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.65, 1.55))
    fog = bpy.context.object
    fog.name = "Quality | bounded stage fog"
    fog.scale = (3.5, 3.5, 3.1)
    mat = bpy.data.materials.new("Quality | volume scattering")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    scatter = tree.nodes.new("ShaderNodeVolumeScatter")
    scatter.inputs["Color"].default_value = (*settings["color"], 1)
    scatter.inputs["Density"].default_value = settings["density"]
    scatter.inputs["Anisotropy"].default_value = settings["anisotropy"]
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(scatter.outputs[0], out.inputs["Volume"])
    fog.data.materials.append(mat)
    for i, (x, color) in enumerate([(-0.8, (1, 0.68, 0.40)), (0.8, (0.50, 0.65, 1))]):
        data = bpy.data.lights.new("Quality | beam " + str(i), "SPOT")
        data.energy = settings["spot_energy"]
        data.color = color
        data.spot_size = settings["spot_size"]
        data.spot_blend = 0.45
        obj = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(obj)
        obj.location = (x, 1.25, 2.65)
        target = Vector((-x * 0.35, -0.05, 0.65))
        obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
    scene.eevee.use_volumetric_shadows = True
    return settings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--preset", type=Path, required=True)
    p.add_argument(
        "--variants",
        nargs="+",
        default=["baseline", "normals", "ao", "metal", "combined", "volume"],
    )
    p.add_argument("--frames", nargs="+", type=int, default=[421, 540, 601])
    p.add_argument(
        "--half-lambert-preset",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "presets/quality/half-lambert-v1.json",
    )
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    settings = json.loads(args.preset.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    source = bpy.data.filepath
    reports = []
    for variant in args.variants:
        if variant not in {
            "baseline",
            "normals",
            "ao",
            "metal",
            "combined",
            "volume",
            "half_lambert",
            "half_detail",
        }:
            raise ValueError(variant)
        bpy.ops.wm.open_mainfile(filepath=source)
        scene = bpy.context.scene
        assert scene.rigidbody_world is None
        tree = scene.compositing_node_group
        # Saved source contains File Output nodes pointing to old production
        # caches. Remove them before any render; preserve the old caches.
        for n in list(tree.nodes):
            if n.bl_idname == "CompositorNodeOutputFile":
                tree.nodes.remove(n)
        directory = args.output_dir / variant
        directory.mkdir()
        arm = next(o for o in scene.objects if o.type == "ARMATURE")
        mesh = next(
            o
            for o in scene.objects
            if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
        )
        before = position_hash(mesh)
        poses = {f: pose_hash(scene, arm, f) for f in args.frames}
        report = {"variant": variant, "source_project": source, "frames": args.frames}
        if variant in {"half_lambert", "half_detail"}:
            report["half_lambert"] = apply_half_lambert(
                bpy.data.materials,
                json.loads(args.half_lambert_preset.read_text(encoding="utf-8")),
            )
        if variant in {"normals", "combined", "volume", "half_detail"}:
            report["normals"] = face_normals(mesh, settings["face_normals"])
        if variant in {"ao", "combined", "volume", "half_detail"}:
            report["ao"] = local_ao(scene, settings["ao"], directory / "diagnostics")
        if variant in {"metal", "combined", "volume"}:
            report["metal"] = metallic_trim(settings["trim_bsdf"])
        if variant == "volume":
            report["volume"] = volume(scene, settings["fog"])
        assert position_hash(mesh) == before
        assert all(pose_hash(scene, arm, f) == poses[f] for f in args.frames)
        report["vertex_positions_unchanged"] = True
        report["pose_bone_hashes_unchanged"] = True
        scene.render.resolution_percentage = 50
        scene.eevee.taa_render_samples = 48
        scene.render.image_settings.media_type = "IMAGE"
        scene.render.image_settings.file_format = "PNG"
        scene.render.use_sequencer = False
        for frame in args.frames:
            scene.frame_set(frame)
            scene.render.filepath = str(directory / f"frame-{frame:04d}.png")
            bpy.ops.render.render(write_still=True)
        if variant in {"combined", "volume", "half_lambert", "half_detail"}:
            bpy.ops.wm.save_as_mainfile(filepath=str(directory / "quality-study.blend"))
        reports.append(report)
        (directory / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("QUALITY_VARIANT_OK", variant, flush=True)
    (args.output_dir / "quality-report.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
