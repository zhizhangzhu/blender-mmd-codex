"""Create a new, explicitly labeled PMX + VMD import draft in Blender.

This is an import/lighting proof, not final shading or baked physics.
Invoke using Blender --background --disable-autoexec --python-exit-code 1
--python scripts/mmd_first_scene.py -- --model ... --motion ... --output-dir ...
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
import unicodedata
from pathlib import Path


def main():
    import bpy
    from mathutils import Vector

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame", type=int, default=1884)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    for source in (args.model, args.motion, args.audio):
        if source and not source.is_file():
            raise FileNotFoundError(source)
    if args.model.suffix.lower() != ".pmx" or args.motion.suffix.lower() != ".vmd":
        raise ValueError("This workflow requires PMX and native VMD inputs")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    module = "bl_ext.blender_org.mmd_tools"
    if module not in sys.modules or not getattr(sys.modules[module], "__addon_enabled__", False):
        raise RuntimeError("Enable the current MMD Tools extension before running")
    vmd = importlib.import_module(module + ".core.vmd")
    logging.getLogger().setLevel(logging.WARNING)
    motion = vmd.File()
    motion.load(filepath=str(args.motion))
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.render.fps_base = 1
    scene.frame_set(1)
    result = bpy.ops.mmd_tools.import_model(filepath=str(args.model), scale=0.08,
                                           clean_model=False, remove_doubles=False, save_log=False, log_level="ERROR")
    if "FINISHED" not in result:
        raise RuntimeError(f"PMX import failed: {result}")
    armature = next(obj for obj in scene.objects if obj.type == "ARMATURE")
    meshes = [obj for obj in scene.objects if obj.type == "MESH" and getattr(obj, "mmd_type", "NONE") == "NONE"]
    root = armature.parent
    # Match unique width variants (e.g. full-width finger digits) without
    # changing Blender bone names or the source PMX/VMD files.
    aliases = []
    source_by_normalized = {}
    for name in motion.boneAnimation.keys():
        source_by_normalized.setdefault(unicodedata.normalize("NFKC", name), []).append(name)
    for bone in armature.pose.bones:
        name = bone.mmd_bone.name_j
        candidates = source_by_normalized.get(unicodedata.normalize("NFKC", name), [])
        if name not in motion.boneAnimation and len(candidates) == 1:
            bone.mmd_bone.name_j = candidates[0]
            aliases.append({"bone": bone.name, "original_name_j": name, "motion_name_j": candidates[0]})
    bone_names = {bone.mmd_bone.name_j for bone in armature.pose.bones}
    morph_names = {key.name for obj in meshes if obj.data.shape_keys for key in obj.data.shape_keys.key_blocks}
    animated_names = set(motion.boneAnimation.keys())
    morph_tracks = set(motion.shapeKeyAnimation.keys())
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    result = bpy.ops.mmd_tools.import_vmd(filepath=str(args.motion), scale=0.08,
                                         bone_mapper="PMX", update_scene_settings=True,
                                         create_new_action=True, use_nla=False, save_log=False, log_level="ERROR")
    if "FINISHED" not in result:
        raise RuntimeError(f"VMD import failed: {result}")
    def pose_sample(frame):
        scene.frame_set(frame)
        return {b.name: list(b.matrix.translation) for b in armature.pose.bones if b.mmd_bone.name_j in {"頭", "左手首", "右手首", "左足首", "右足首", "センター"}}
    samples = {str(frame): pose_sample(frame) for frame in (args.frame, args.frame + 15, args.frame + 30)}
    scene.frame_set(args.frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = [obj.matrix_world @ Vector(corner) for mesh in meshes
              for obj in [mesh.evaluated_get(depsgraph)] for corner in obj.bound_box]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low + high) * 0.5
    height = high.z - low.z
    def point_at(obj, target):
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add(location=center + Vector((height * 2.1, -height * 1.9, height * 0.08)))
    camera = bpy.context.object
    camera.name = "Draft_Static_Camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(height * 1.24, (high.x - low.x) * 1.4 * 4 / 3)
    point_at(camera, center)
    scene.camera = camera
    bpy.ops.mesh.primitive_plane_add(size=height * 200, location=(center.x, center.y, low.z - 0.005))
    floor = bpy.context.object
    floor.name = "Draft_Floor"
    floor_material = bpy.data.materials.new("Draft lavender floor")
    floor_material.diffuse_color = (0.21, 0.19, 0.28, 1)
    floor.data.materials.append(floor_material)
    for name, offset, energy, size in (
        ("Key", (-1.5, -2, 2.5), 60, 2.0),
        ("Fill", (1.5, -1, 1), 35, 2.0),
        ("Rim", (0.8, 1.5, 2), 90, 1.5),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy * height * height
        data.shape = "DISK"
        data.size = size * height
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = center + Vector(offset) * height
        point_at(light, center)
    scene.world = bpy.data.worlds.new("Draft World")
    scene.world.use_nodes = True
    world_nodes = scene.world.node_tree.nodes
    world_nodes.clear()
    background = world_nodes.new("ShaderNodeBackground")
    world_output = world_nodes.new("ShaderNodeOutputWorld")
    scene.world.node_tree.links.new(background.outputs[0], world_output.inputs[0])
    background.inputs[0].default_value = (0.32, 0.28, 0.4, 1)
    background.inputs[1].default_value = 0.4
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = -0.5
    if args.audio:
        editor = scene.sequence_editor_create()
        editor.strips.new_sound("Instrumental reference", str(args.audio), channel=1, frame_start=1)
    # Make the saved project open in camera view with the model selected.
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    missing_images = [image.filepath for image in bpy.data.images
                      if image.source == "FILE" and not image.packed_file
                      and not Path(bpy.path.abspath(image.filepath)).is_file()]
    report = {
        "status": "import_draft", "blender": bpy.app.version_string,
        "model": str(args.model), "motion": str(args.motion), "audio": str(args.audio) if args.audio else None,
        "scale": 0.08, "fps": scene.render.fps, "frame_range": [scene.frame_start, scene.frame_end],
        "preview_frame": args.frame, "model_meshes": len(meshes), "model_bones": len(armature.pose.bones),
        "materials": len(bpy.data.materials), "missing_image_paths": missing_images,
        "motion_bone_tracks": len(animated_names), "matched_bone_tracks": len(animated_names & bone_names),
        "unmatched_bone_tracks": sorted(animated_names - bone_names),
        "unmatched_multiframe_bone_tracks": sorted(n for n in animated_names - bone_names if len(motion.boneAnimation[n]) > 2),
        "bone_name_width_aliases": aliases,
        "motion_morph_tracks": len(morph_tracks), "unmatched_vertex_morph_tracks": sorted(morph_tracks - morph_names),
        "camera_keys_in_vmd": len(motion.cameraAnimation), "pose_samples": samples,
        "limits": ["Physics imported but not built or baked; hair and clothing motion not validated.",
                   "Static draft camera, not the reference author's camera.",
                   "Imported MMD materials and simple lighting; reference style not matched.",
                   "Foot IK warning from source readme needs motion review.",
                   "Audio is instrumental reference; synchronization has not been reviewed."]}
    with (args.output_dir / "import-report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(args.output_dir / "preview.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_dir / "first-import.blend"))
    bpy.ops.render.render(write_still=True)
    print("BLENDER_MMD_CODEX_DRAFT_OK", args.output_dir)


if __name__ == "__main__":
    main()
