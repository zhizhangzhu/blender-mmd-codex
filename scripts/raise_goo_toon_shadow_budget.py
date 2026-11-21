"""Increase only the inherited shadow memory budget and preflight peak frames."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import ROOT
from render_portrait_light_controls import mute_file_outputs

register_addons()
old = ROOT / "production-v13/Franken_Duet_Goo_Eye_Hair_Stage.blend"
production = ROOT / "production-v16"
production.mkdir(exist_ok=False)
for name in ("hair-shadow-manifest.json", "rendered-shadow-sequence-check.json"):
    shutil.copy2(old.parent / name, production / name)
shutil.copytree(old.parent / "hair-shadows", production / "hair-shadows")
bpy.ops.wm.open_mainfile(filepath=str(old), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
before = scene.eevee.shadow_pool_size
options = [
    i.identifier for i in scene.eevee.bl_rna.properties["shadow_pool_size"].enum_items
]
print("SHADOW_POOL_OPTIONS", before, options, flush=True)
scene.eevee.shadow_pool_size = max(options, key=int)
old_scale = scene.eevee.shadow_resolution_scale
scene.eevee.shadow_resolution_scale = 0.75
precision = []
for name, minimum in (
    ("Goo window wrap | parallel window daylight", 0.008),
    ("Goo window wrap | large window 0", 0.015),
    ("Goo window wrap | large window 1", 0.015),
    ("Eye hair v1 | aksiniya directional head key", 0.003),
    ("Eye hair v1 | ikhor directional head key", 0.003),
):
    lamp = scene.objects[name].data
    previous = lamp.shadow_maximum_resolution
    lamp.shadow_maximum_resolution = max(previous, minimum)
    precision.append(
        {"light": name, "before": previous, "after": lamp.shadow_maximum_resolution}
    )
print("SHADOW_PRECISION_BOUNDS", precision, flush=True)
scene.frame_set(4290)
bpy.context.view_layer.update()
project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project), relative_remap=False)
prep = json.loads((old.parent / "preparation.json").read_text(encoding="utf-8"))
prep.update(
    source=str(old),
    source_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
    project=str(project),
    project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
    shadow_memory_revision={
        "before": before,
        "after": scene.eevee.shadow_pool_size,
        "reason": "Full150-frame render exposed8192-page overflow; pool already at build maximum, bound overly fine light shadow texels",
        "shadow_precision_bounds": precision,
        "global_resolution_scale_before": old_scale,
        "global_resolution_scale_after": scene.eevee.shadow_resolution_scale,
        "light_energy_transform_materials_animation_changed": False,
    },
)
(production / "preparation.json").write_text(
    json.dumps(prep, ensure_ascii=False, indent=2), encoding="utf-8"
)
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 16
scene.camera.data.dof.use_dof = True
scene.render.use_motion_blur = False
scene.render.image_settings.file_format = "JPEG"
for frame in (4234, 4250, 4438):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    scene.render.filepath = str(production / f"budget-preflight-{frame}.jpg")
    bpy.ops.render.render(write_still=True)
    print("SHADOW_MEMORY_PREFLIGHT", frame, flush=True)
print("SHADOW_MEMORY_MASTER_SAVED", flush=True)
