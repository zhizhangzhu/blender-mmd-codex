"""Still-only narrow warm hair contact-shadow study from the supplied reference."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_goo_face_hair_shadows import uv_template
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import ACTORS, PREFIX
from prepare_goo_toon_face_hair_study import SIZE, save_mask
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-Citlali-Fringe-Shadow-v1")
OUT = ROOT / "production-v2"
OUT.mkdir(parents=True, exist_ok=False)
SOURCE = Path(
    "D:/codex/output/MMD-Ikhor-Hair-Alignment-v1/production-v1/Ikhor_Hair_Aligned_Still.blend"
)
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()


def pose_hash():
    data = {
        o.name: [list(b.matrix[i]) for b in o.pose.bones for i in range(4)]
        for o in scene.objects
        if o.type == "ARMATURE"
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


before_pose = pose_hash()
stats = []
for actor, spec in ACTORS.items():
    obj = scene.objects[spec["mesh"]]
    template = uv_template(obj, actor)
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    world = [obj.matrix_world @ v.co for v in mesh.vertices]
    tree = BVHTree.FromPolygons(
        world, template["casters"], all_triangles=False, epsilon=0.000005
    )
    ids = template["indices"]
    weights = template["weights"]
    valid = weights.sum(axis=2) > 0.5
    xyz = (
        np.asarray([p[:] for p in world], np.float32)[ids] * weights[:, :, :, None]
    ).sum(axis=2)
    rot = scene.objects[PREFIX + actor + " eye L"].matrix_world.to_3x3()
    forward = (rot @ Vector((0, -1, 0))).normalized()
    up = (rot @ Vector((0, 0, 1))).normalized()
    right = (rot @ Vector((1, 0, 0))).normalized()
    directions = [
        (forward + up * 0.35 + right * (-0.06 + d)).normalized()
        for d in (-0.009, 0, 0.009)
    ]
    coverage = np.zeros((SIZE, SIZE), np.float32)
    for y, x in np.argwhere(valid):
        p = Vector(xyz[y, x])
        hits = 0
        for direction in directions:
            hit, _, _, depth = tree.ray_cast(p + direction * 0.0002, direction, 0.065)
            if hit is not None and depth > 0.0002:
                hits += 1
        coverage[y, x] = hits / 3
    # Confine the contact pass to the upper face, keeping lower cheeks luminous.
    restz = np.asarray([v.co.z for v in obj.data.vertices], np.float32)
    z = (restz[ids] * weights).sum(axis=2)
    eye_ids = {
        v
        for p in obj.data.polygons
        if obj.data.materials[p.material_index].name in spec["eyes"]
        for v in p.vertices
    }
    eyez = np.mean([obj.data.vertices[i].co.z for i in eye_ids])
    permission = np.clip((z - (eyez - 0.012)) / 0.020, 0, 1)
    permission = permission * permission * (3 - 2 * permission)
    coverage *= permission
    image = save_mask(OUT / f"{actor}_narrow_hair_visibility.png", 1 - coverage)
    image.pack()
    evaluated.to_mesh_clear()
    mat = bpy.data.materials[template["face"]].node_tree
    tex = mat.nodes[PREFIX + "geometry derived hair shadow"]
    warm = mat.nodes[PREFIX + "warm geometric bang shadow"]
    tex.image = image
    warm.inputs[2].default_value = (0.98, 0.53, 0.25, 1)
    stats.append(
        {
            "actor": actor,
            "valid_face_texels": int(valid.sum()),
            "shadowed_texels": int((coverage > 0.1).sum()),
            "resolution": SIZE,
            "shadow_direction_forward_up_right": [1, 0.35, -0.06],
        }
    )
assert pose_hash() == before_pose
project = OUT / "Franken_Citlali_Fringe_Shadow_Still.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
report = {
    "source": str(SOURCE),
    "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "project": str(project),
    "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
    "scope": "Static4290 only; narrow frontal artistic contact-shadow, not author original shader; no video",
    "reference_local_time_seconds": 8,
    "shadow_color_multiplier": [0.98, 0.53, 0.25],
    "pose_hash": before_pose,
    "poses_preserved": True,
    "actors": stats,
}
(OUT / "study.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("NARROW_SHADOW_MASTER_SAVED", flush=True)
# Independent reopen to prove packed maps, corrected hair pose and material routes persist.
bpy.ops.wm.open_mainfile(filepath=str(project), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
assert pose_hash() == before_pose
report["independent_reopen_passed"] = True
(OUT / "study.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
for marker in scene.timeline_markers:
    marker.camera = None
cam = bpy.data.objects.new(
    "Fringe study camera", bpy.data.cameras.new("Fringe study camera")
)
scene.collection.objects.link(cam)
cam.data.lens = 65
cam.data.dof.use_dof = False
scene.render.resolution_x = scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 32
scene.render.image_settings.file_format = "JPEG"
for actor in ("ikhor", "aksiniya"):
    helper = scene.objects[PREFIX + actor + " eye L"]
    rot = helper.matrix_world.to_3x3()
    center = (
        helper.matrix_world.translation
        + scene.objects[PREFIX + actor + " eye R"].matrix_world.translation
    ) * 0.5
    up = (rot @ Vector((0, 0, 1))).normalized()
    forward = (rot @ Vector((0, -1, 0))).normalized()
    cam.location = center + forward * 0.55 + up * 0.025
    cam.rotation_euler = (
        (center + up * 0.01 - cam.location).to_track_quat("-Z", "Y").to_euler()
    )
    scene.camera = cam
    scene.render.filepath = str(OUT / f"{actor}-warm-contact-4290.jpg")
    bpy.ops.render.render(write_still=True)
    print("NARROW_SHADOW_STILL", actor, flush=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
for marker in scene.timeline_markers:
    marker.camera = None
cam = bpy.data.objects.new(
    "Fringe baseline camera", bpy.data.cameras.new("Fringe baseline camera")
)
scene.collection.objects.link(cam)
cam.data.lens = 65
cam.data.dof.use_dof = False
helper = scene.objects[PREFIX + "ikhor eye L"]
rot = helper.matrix_world.to_3x3()
center = (
    helper.matrix_world.translation
    + scene.objects[PREFIX + "ikhor eye R"].matrix_world.translation
) * 0.5
up = (rot @ Vector((0, 0, 1))).normalized()
forward = (rot @ Vector((0, -1, 0))).normalized()
cam.location = center + forward * 0.55 + up * 0.025
cam.rotation_euler = (
    (center + up * 0.01 - cam.location).to_track_quat("-Z", "Y").to_euler()
)
scene.camera = cam
scene.render.resolution_x = scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 32
scene.render.image_settings.file_format = "JPEG"
scene.render.filepath = str(OUT / "ikhor-before-4290.jpg")
bpy.ops.render.render(write_still=True)
print("NARROW_SHADOW_STUDY_COMPLETE", flush=True)
