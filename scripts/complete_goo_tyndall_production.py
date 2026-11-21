"""Explicit volume light groups for the actual Goo direct-light packing path."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-Goo-Tyndall-Rim-v1")
source = ROOT / "production-v4/Franken_Duet_Goo_Tyndall_Rim.blend"
expected = json.loads((source.parent / "preparation.json").read_text(encoding="utf-8"))
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected["project_sha256"]
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
production = ROOT / "production-v5"
production.mkdir(exist_ok=False)
air = scene.objects["Goo Tyndall | rear window air only"]
material = air.data.materials[0]
material.light_groups.use_default = False
material.light_groups.groups.add().name = "Goo Tyndall shafts only"
for index in range(2):
    data = scene.objects[f"Goo Tyndall v2 | window shaft {index}"].data
    data.diffuse_factor = 1
    data.light_groups.use_default = False
    data.light_groups.groups.add().name = "Goo Tyndall shafts only"
import goo_engine_light_groups

goo_engine_light_groups.sync_light_groups()
bpy.context.view_layer.update()
scene.frame_set(4290)
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.eevee.taa_render_samples = 24
project = production / "Franken_Duet_Goo_Tyndall_Rim.blend"
scene.render.filepath = str(production / "portrait-4290.png")
bpy.ops.wm.save_as_mainfile(filepath=str(project))
report = {
    **expected,
    "source": str(source),
    "source_sha256": expected["project_sha256"],
    "project": str(project),
    "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
    "volume_light_group": {
        "name": "Goo Tyndall shafts only",
        "default_membership": False,
        "surface_diffuse_factor": 1,
        "surface_exclusion": "Both explicit Goo groups and native receiver collection limit new lamps to rear air",
        "explicit_sync": True,
    },
}
(production / "preparation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.eevee.taa_render_samples = 24
for frame, label in ((4290, "portrait"), (4140, "opening")):
    scene.frame_set(frame)
    scene.render.filepath = str(production / f"{label}-{frame}.png")
    bpy.ops.render.render(write_still=True)
    print("TYNDALL_V5_STILL", frame, flush=True)
