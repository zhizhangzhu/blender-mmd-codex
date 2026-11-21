"""Pinned author-Furina diagnostic stills, primary face SDF on/off; never save blend."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

SOURCE = Path(
    "D:/codex/temp/Goo-Face-Shadow-Study-2026-11-18/package53/author-toon.blend"
)
SOURCE_SHA = "d9696f8f165823e17fb542ce4b157351c657c79e958aefb87fe677d4e71f80fe"
CACHE = SOURCE.parent
OUTPUT = Path("D:/codex/output/Goo-Face-Shadow-Study-2026-11-18/author53-face-ab-v1")
MESH = "【芙宁娜_荒】_mesh"
MAT = "颜"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def evaluated_geometry(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", coords)
    face_polygons = [
        p for p in mesh.polygons if obj.data.materials[p.material_index].name == MAT
    ]
    ids = sorted({index for p in face_polygons for index in p.vertices})
    assert ids, "Primary face polygons missing"
    points = [obj.matrix_world @ mesh.vertices[index].co for index in ids]
    normal = sum((p.normal * p.area for p in face_polygons), Vector())
    normal = obj.matrix_world.to_3x3().inverted().transposed() @ normal
    assert normal.length > 1e-8
    forward = normal.normalized()
    result = {
        "sha256": hashlib.sha256(coords.tobytes()).hexdigest(),
        "vertices": len(mesh.vertices),
        "face_vertices": len(ids),
    }
    evaluated.to_mesh_clear()
    return result, points, forward


def light_guard(scene):
    value = [
        (
            obj.name,
            list(obj.matrix_world),
            obj.data.energy,
            list(obj.data.color),
            obj.hide_render,
        )
        for obj in scene.objects
        if obj.type == "LIGHT"
    ]
    text = json.dumps(value, default=lambda value: list(value), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def setup():
    assert bpy.app.version[:2] == (5, 3)
    assert sha(SOURCE) == SOURCE_SHA
    assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
    scene = bpy.context.scene
    assert scene.frame_current == 16064
    assert scene.rigidbody_world is None or not scene.rigidbody_world.enabled
    obj = scene.objects[MESH]
    assert not any(
        m.show_render and m.type in {"CLOTH", "SOFT_BODY", "FLUID", "DYNAMIC_PAINT"}
        for m in obj.modifiers
    )
    face = bpy.data.materials[MAT]
    group = face.node_tree.nodes["新卡渲着色器"]
    assert group.node_tree.name == "新卡渲着色器"
    sdf = group.inputs["使用SDF阴影"]
    shadow = group.inputs["受到阴影"]
    assert sdf.identifier == "Socket_29" and not sdf.is_linked and sdf.default_value
    assert (
        shadow.identifier == "Socket_2"
        and not shadow.is_linked
        and not shadow.default_value
    )
    trees = list(bpy.data.node_groups)
    for other in bpy.data.scenes:
        tree = getattr(other, "compositing_node_group", None)
        if tree and tree not in trees:
            trees.append(tree)
    for tree in trees:
        for node in tree.nodes:
            if node.type == "OUTPUT_FILE":
                node.mute = True
    bpy.context.view_layer.update()
    geometry, points, forward = evaluated_geometry(obj)
    up = Vector((0, 0, 1))
    up = up - forward * up.dot(forward)
    assert up.length > 0.1, "Unusual face orientation requires director review"
    up.normalize()
    right = up.cross(forward).normalized()
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (minimum + maximum) * 0.5
    height = max(p.dot(up) for p in points) - min(p.dot(up) for p in points)
    width = max(p.dot(right) for p in points) - min(p.dot(right) for p in points)
    assert height > 1e-5 and width > 1e-5
    span = max(height * 3.4, width * 2.3)
    target = center + up * height * 0.12
    camera = bpy.data.objects.new(
        "Study only | primary face SDF comparison",
        bpy.data.cameras.new("Study only | face comparison"),
    )
    scene.collection.objects.link(camera)
    camera.data.lens = 62
    camera.data.sensor_fit = "VERTICAL"
    camera.data.sensor_height = 32
    camera.data.dof.use_dof = False
    camera.location = target + forward * (
        span * camera.data.lens / camera.data.sensor_height
    )
    camera.rotation_euler = (
        (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    markers = [
        (m.name, m.frame, m.camera.name if m.camera else None)
        for m in scene.timeline_markers
    ]
    for marker in scene.timeline_markers:
        marker.camera = None
    original_camera = scene.camera.name if scene.camera else None
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = 850, 900
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 64
    scene.render.use_motion_blur = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.color_mode = "RGBA"
    report = {
        "source": str(SOURCE),
        "source_sha256": SOURCE_SHA,
        "runtime": {
            "version": list(bpy.app.version),
            "build": bpy.app.build_hash.decode(),
        },
        "frame": scene.frame_current,
        "model": MESH,
        "material": MAT,
        "original_camera": original_camera,
        "original_markers": markers,
        "diagnostic_camera": {
            "position": list(camera.location),
            "target": list(target),
            "forward_from_area_weighted_face_normals": list(forward),
            "up": list(up),
            "lens_mm": camera.data.lens,
            "vertical_span": span,
            "face_height": height,
            "face_width": width,
        },
        "geometry": geometry,
        "lights_sha256": light_guard(scene),
        "saved_primary_face_sdf": True,
        "primary_face_receive_shadow": False,
        "scope": "Only primary face material SDF enable changes;author normals,input textures,other materials,pose and lights retained",
        "render_settings": {
            "resolution": [850, 900],
            "samples": 64,
            "compositor": False,
            "sequencer": False,
            "motion_blur": False,
            "dof": False,
            "view_transform": scene.view_settings.view_transform,
            "exposure": scene.view_settings.exposure,
        },
        "limits": [
            "Diagnostic camera,not the video viewport or source render camera",
            "Author compositor including Glow is bypassed to isolate material",
            "Primary face receives real shadows=false is preserved;this does not validate bangs projection",
            "No animation,physics or current-Goo production changes",
            "No third-party blend/model delivered",
        ],
    }
    return scene, obj, sdf, report


def png_difference(first, second):
    arrays = []
    for path in (first, second):
        image = bpy.data.images.load(str(path), check_existing=False)
        values = np.empty(len(image.pixels), np.float32)
        image.pixels.foreach_get(values)
        arrays.append(values.reshape((-1, 4))[:, :3])
        bpy.data.images.remove(image)
    delta = np.abs(arrays[0] - arrays[1])
    return {
        "max_rgb": float(delta.max()),
        "mean_rgb": float(delta.mean()),
        "pixel_fraction_gt_0_001": float((delta.max(axis=1) > 0.001).mean()),
        "space": "Blender decoded original PNG RGB",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "render"), required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    scene, obj, control, report = setup()
    setup_path = CACHE / "face-control-setup.json"
    if args.mode == "preflight":
        assert not setup_path.exists()
        write(setup_path, report)
        print("AUTHOR53_FACE_PREFLIGHT", setup_path, flush=True)
        return
    expected = json.loads(setup_path.read_text(encoding="utf-8"))
    assert report["geometry"] == expected["geometry"]
    assert report["diagnostic_camera"] == expected["diagnostic_camera"]
    assert report["lights_sha256"] == expected["lights_sha256"]
    OUTPUT.mkdir(parents=True, exist_ok=False)
    report["stills"] = []
    for enabled, label in (
        (True, "author53-face-sdf-on"),
        (False, "author53-face-sdf-off"),
    ):
        control.default_value = enabled
        bpy.context.view_layer.update()
        assert evaluated_geometry(obj)[0] == report["geometry"]
        assert light_guard(scene) == report["lights_sha256"]
        scene.render.filepath = str(OUTPUT / (label + ".png"))
        bpy.ops.render.render(write_still=True)
        report["stills"].append(
            {
                "file": label + ".png",
                "sdf_enabled": enabled,
                "sha256": sha(OUTPUT / (label + ".png")),
            }
        )
        print("AUTHOR53_FACE_STILL", label, flush=True)
    report["sdf_render_difference"] = png_difference(
        OUTPUT / "author53-face-sdf-on.png", OUTPUT / "author53-face-sdf-off.png"
    )
    report["source_unchanged"] = sha(SOURCE) == SOURCE_SHA
    assert report["source_unchanged"]
    report["blend_saved"] = False
    report["new_video"] = False
    report["director_review"] = (
        "pending image inspection;nonzero difference is not artistic approval"
    )
    write(OUTPUT / "render-report.json", report)
    print("AUTHOR53_FACE_AB_RENDERED", OUTPUT, flush=True)


if __name__ == "__main__":
    main()
