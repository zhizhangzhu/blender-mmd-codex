"""Reduce Ikhor's added palette gain without changing Aksiniya or global exposure."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, color, math, node, remap
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-MME-Reference-Light-v1")
SOURCE = ROOT / "production-v3/Franken_MME_Clear_Light_Still.blend"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--revision", type=int, choices=(5, 6), default=6)
args = parser.parse_args(
    sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
)
OUT = ROOT / f"production-v{args.revision}"
GAINS = {
    5: {"skin": 0.76, "hair": 0.84, "cloth": 0.65},
    6: {"skin": 0.56, "hair": 0.66, "cloth": 0.45},
}[args.revision]
EXPECTED = "1ac199423c418220612e8b7b7e0b862b6b42c06bb0e0e40d6857cc898a486fc7"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
if OUT.exists():
    assert not list(OUT.iterdir()), "Refuse to overwrite a rendered candidate"
else:
    OUT.mkdir()
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()


def pose_hash():
    pose = {
        o.name: [list(b.matrix[i]) for b in o.pose.bones for i in range(4)]
        for o in bpy.context.scene.objects
        if o.type == "ARMATURE"
    }
    return hashlib.sha256(json.dumps(pose, sort_keys=True).encode()).hexdigest()


before_pose = pose_hash()
changed = []
for mat in bpy.data.materials:
    if mat.get("performer_id") != "ikhor" or not mat.node_tree:
        continue
    tree = mat.node_tree
    start = tree.nodes.get(PREFIX + "MME study retained surface plus key colour")
    surface = tree.nodes.get("Ikhor character | controlled NPR surface")
    if not start or not surface:
        continue
    role = mat.get("ikhor_material_role", "")
    if role == "trim":
        continue
    original = start.inputs[1].links[0].from_socket
    current = surface.inputs["Color"].links[0].from_socket
    if role in ("face", "skin") or mat.name in ("颜.001", "手.001", "首.001"):
        weight = 0.20
        core_gain = GAINS["skin"]
    elif role == "hair":
        weight = 0.50
        core_gain = GAINS["hair"]
    else:
        weight = 0.25
        core_gain = GAINS["cloth"]
    result = color(
        tree,
        "MIX",
        original,
        current,
        weight,
        "MME revision restrained Ikhor palette gain",
    )
    # Preserve the exported contour signal spatially while reducing broad lit areas.
    protected = None
    contour = tree.nodes.get(PREFIX + "contour only radiance")
    if contour and contour.inputs["Color"].is_linked:
        grey = node(tree, "ShaderNodeRGBToBW", "MME revision contour protection")
        tree.links.new(contour.inputs["Color"].links[0].from_socket, grey.inputs[0])
        protected = remap(
            tree,
            grey.outputs[0],
            0.02,
            0.5,
            0,
            1,
            "MME revision preserve lit silhouette",
        )
    for suffix in (
        "gold material partition art permission",
        "cyan_gems art permission",
    ):
        mask = tree.nodes.get("Ikhor character | " + suffix)
        if not mask:
            continue
        perm = remap(
            tree, mask.outputs[0], 0.001, 0.04, 0, 1, "MME revision preserve " + suffix
        )
        protected = (
            perm
            if protected is None
            else math(tree, "MAXIMUM", protected, perm, "MME revision protected union")
        )
    gain = (
        (core_gain, core_gain, core_gain, 1)
        if protected is None
        else remap(
            tree, protected, 0, 1, core_gain, 1, "MME revision broad surface gain"
        )
    )
    result = color(
        tree, "MULTIPLY", result, gain, 1, "MME revision reduced interior radiance"
    )
    tree.links.new(result, surface.inputs["Color"])
    changed.append(
        {
            "material": mat.name,
            "role": role,
            "new_palette_weight": weight,
            "core_radiance_gain": core_gain,
            "contour_and_trim_protected": protected is not None,
        }
    )
assert changed and pose_hash() == before_pose
project = OUT / "Franken_MME_Balanced_Light_Still.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
project_hash = hashlib.sha256(project.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(project), use_scripts=False, load_ui=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
assert pose_hash() == before_pose
scene.render.filepath = str(OUT / "balanced-double-4290.jpg")
bpy.ops.render.render(write_still=True)
print("BALANCED_DOUBLE_COMPLETE", flush=True)
for marker in scene.timeline_markers:
    marker.camera = None
cam = bpy.data.objects.new(
    "Balanced hero camera", bpy.data.cameras.new("Balanced hero camera")
)
scene.collection.objects.link(cam)
h = scene.objects["Eye hair v1 | ikhor eye L"]
rot = h.matrix_world.to_3x3()
center = (
    h.matrix_world.translation
    + scene.objects["Eye hair v1 | ikhor eye R"].matrix_world.translation
) * 0.5
up = (rot @ Vector((0, 0, 1))).normalized()
front = (rot @ Vector((0, -1, 0))).normalized()
target = center - up * 0.18
cam.location = target + front * 1.1 + up * 0.03
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.lens = 50
cam.data.dof.use_dof = False
scene.camera = cam
scene.render.resolution_x = 1000
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 32
scene.render.image_settings.file_format = "JPEG"
scene.render.filepath = str(OUT / "ikhor-balanced-hero-4290.jpg")
bpy.ops.render.render(write_still=True)
report = {
    "source": str(SOURCE),
    "source_sha256": EXPECTED,
    "project": str(project),
    "project_sha256": project_hash,
    "frame": 4290,
    "revision": args.revision,
    "core_gains_from_fixed_v3": GAINS,
    "pose_hash": before_pose,
    "independent_reopen_passed": True,
    "changed_materials": changed,
    "aksiniya_materials_modified": False,
    "lights_modified": False,
    "global_exposure_modified": False,
    "compositor_modified": False,
    "physics_changed": False,
    "video_created": False,
    "scope": "Ikhor only: restrain added palette and broad surface radiance with contour/gold/cyan protection. Lights, alpha and compositor unchanged. Static4290 only.",
}
(OUT / "preparation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("IKHOR_BALANCED_STILLS_COMPLETE", flush=True)
