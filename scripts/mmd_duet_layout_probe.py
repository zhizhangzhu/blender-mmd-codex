"""Import the assigned full duet and an authored camera for draft layout QA.

No physics build/bake or finished look is implied by this diagnostic scene.
"""

import argparse
import importlib
import json
import sys
import unicodedata
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--project", type=Path, required=True)
p.add_argument("--camera-vmd", type=Path, required=True)
p.add_argument("--output-dir", type=Path, required=True)
p.add_argument(
    "--frames",
    type=int,
    nargs="+",
    default=[1, 326, 900, 1885, 2700, 3600, 4800, 5900, 6212, 6368],
)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
project = json.loads(args.project.read_text(encoding="utf-8"))
args.output_dir.mkdir(parents=True, exist_ok=False)
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.render.fps_base = 1
vmd = importlib.import_module("bl_ext.blender_org.mmd_tools.core.vmd")
performers = []
norm = lambda x: unicodedata.normalize("NFKC", x)
for spec in project["performers"]:
    scene.frame_set(1)
    before = set(scene.objects)
    bpy.ops.mmd_tools.import_model(
        filepath=spec["model"],
        scale=project["mmd_scale"],
        clean_model=False,
        remove_doubles=False,
        save_log=False,
        log_level="ERROR",
    )
    objects = set(scene.objects) - before
    arm = next(o for o in objects if o.type == "ARMATURE")
    root = arm.parent
    root["performer_id"] = spec["id"]
    source = vmd.File()
    source.load(filepath=spec["motion"])
    names = {}
    for n in source.boneAnimation:
        names.setdefault(norm(n), []).append(n)
    aliases = []
    for b in arm.pose.bones:
        old = b.mmd_bone.name_j
        candidates = names.get(norm(old), [])
        if old not in source.boneAnimation and len(candidates) == 1:
            b.mmd_bone.name_j = candidates[0]
            aliases.append([old, candidates[0]])
    for o in objects:
        o["performer_id"] = spec["id"]
        if o.type == "MESH":
            for mat in o.data.materials:
                if mat:
                    mat["performer_id"] = spec["id"]
                    mat["source_mmd_material_name"] = (
                        mat.mmd_material.name_j or mat.name
                    )
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.mmd_tools.import_vmd(
        filepath=spec["motion"],
        scale=project["mmd_scale"],
        bone_mapper="PMX",
        update_scene_settings=False,
        create_new_action=True,
        use_nla=False,
        save_log=False,
        log_level="ERROR",
    )
    action = arm.animation_data.action
    performers.append((spec, arm, action, aliases))
    print("DUET_PERFORMER_IMPORTED", spec["id"], flush=True)
    del source
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.name = "Duet | Tottoko authored camera"
bpy.ops.mmd_tools.import_vmd(
    filepath=str(args.camera_vmd),
    scale=project["mmd_scale"],
    update_scene_settings=False,
    create_new_action=True,
    detect_camera_changes=True,
    save_log=False,
    log_level="ERROR",
)
scene.camera = camera
assert all(arm.animation_data.action == action for _, arm, action, _ in performers)
scene.frame_start = 1
scene.frame_end = 6368
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 24
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
bpy.ops.mesh.primitive_plane_add(size=200)
floor = bpy.context.object
floor.name = "Draft layout floor"
floor.location.z = -0.015
mat = bpy.data.materials.new("Draft gray floor")
mat.diffuse_color = (0.12, 0.13, 0.16, 1)
floor.data.materials.append(mat)
if not scene.world:
    scene.world = bpy.data.worlds.new("Draft world")
scene.world.use_nodes = True
scene.world.node_tree.nodes.get("Background").inputs[0].default_value = (
    0.24,
    0.25,
    0.29,
    1,
)
scene.world.node_tree.nodes.get("Background").inputs[1].default_value = 0.6
for label, location, power, size in [
    ("Key", (-3, -4, 5), 800, 5),
    ("Fill", (3, -2, 3), 350, 4),
]:
    light = bpy.data.lights.new("Draft " + label, "AREA")
    light.energy = power
    light.shape = "DISK"
    light.size = size
    o = bpy.data.objects.new(light.name, light)
    scene.collection.objects.link(o)
    o.location = location
    o.rotation_euler = (
        (Vector((0, 0, 1)) - o.location).to_track_quat("-Z", "Y").to_euler()
    )
samples = []
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
for frame in args.frames:
    scene.frame_set(frame)
    item = {"frame": frame, "heads": []}
    for spec, arm, _, _ in performers:
        head = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
        pos = arm.matrix_world @ head.matrix.translation
        uv = world_to_camera_view(scene, camera, pos)
        item["heads"].append(
            {
                "performer": spec["id"],
                "world": list(pos),
                "projection": list(uv),
                "inside": 0 <= uv.x <= 1 and 0 <= uv.y <= 1 and uv.z > 0,
            }
        )
    scene.render.filepath = str(args.output_dir / f"draft-{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
    samples.append(item)
scene.frame_set(1)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(args.output_dir / "duet-layout-draft.blend"))
report = {
    "status": "full duet import and authored camera draft; not a finished video",
    "project": project,
    "camera_source": str(args.camera_vmd),
    "camera_action_preserved_performers": True,
    "fps": 30,
    "render_resolution": [640, 360],
    "samples": samples,
    "performers": [
        {
            "id": spec["id"],
            "motion_part": spec["motion_part"],
            "action": action.name,
            "action_frame_range": list(action.frame_range),
            "bone_width_aliases": aliases,
        }
        for spec, _, action, aliases in performers
    ],
    "limits": [
        "Physics imported only, not built or baked; no dynamic hair/cloth acceptance.",
        "Original imported materials and diagnostic lights, not upgraded production shading.",
        "Landscape diagnostic assumption only; final aspect and independent portrait design remain selectable.",
        "Head visibility is recorded, not used as a requirement that every shot show both heads.",
        "Full-song audio, typography timing, camera tail and facial morph mapping need review.",
    ],
}
(args.output_dir / "layout-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("DUET_LAYOUT_PROBE_OK", args.output_dir, flush=True)
