"""Place actual scattering lights below the hall ceiling and remove volume linking ambiguity."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-Goo-Tyndall-Rim-v1")
source = ROOT / "production-v5/Franken_Duet_Goo_Tyndall_Rim.blend"
expected = json.loads((source.parent / "preparation.json").read_text(encoding="utf-8"))
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected["project_sha256"]
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
production = ROOT / "production-v6"
production.mkdir(exist_ok=False)
scene.objects["Stage art | rear air only"].hide_render = True
air = scene.objects["Goo Tyndall | rear window air only"]
air.location, air.scale = (0, 2.6, 1.85), (4, 1.6, 1.75)
air.data.materials[0].light_groups.use_default = True
lights = []
for index, (position, target) in enumerate(
    (((-2.4, 2.6, 2.8), (0.7, 1.0, 0.15)), ((-0.8, 3.1, 3.0), (2.2, 1.4, 0.15)))
):
    lamp = scene.objects[f"Goo Tyndall v2 | window shaft {index}"]
    lamp.location = position
    rotation = (Vector(target) - lamp.location).to_track_quat("-Z", "Y")
    lamp.rotation_euler = rotation.to_euler()
    lamp.data.energy, lamp.data.volume_factor = 3000, 3
    lamp.data.diffuse_factor, lamp.data.specular_factor = 0, 0
    lamp.data.spot_size, lamp.data.spot_blend = 0.28, 0.35
    lamp.data.light_groups.use_default = True
    lamp.light_linking.receiver_collection = None
    lamp.light_linking.blocker_collection = None
    slat = scene.objects[f"Goo Tyndall v2 | shaft divider {index}"]
    slat.location = lamp.location.lerp(Vector(target), 0.32)
    slat.rotation_euler = rotation.to_euler()
    slat.scale = (0.028, 0.9, 0.03)
    lights.append(
        {
            "name": lamp.name,
            "position": list(position),
            "target": list(target),
            "diffuse": 0,
            "specular": 0,
            "volume_factor": 3,
            "actual_geometry_shadows": True,
        }
    )
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
    "final_window_shafts": lights,
    "final_volume_bounds": [[-4, 1, 0.1], [4, 4.2, 3.6]],
    "legacy_rear_air_hidden": True,
    "volume_light_group": "Default group enabled; no native receiver/blocker collection; diffuse/specular 0, volume only",
    "shaft_shadow_linking": "No exclusions: actual geometry and window slat accessories cast volume shadows. Lamps placed inside ceiling, not proof of original exterior window transmission.",
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
    print("TYNDALL_V6_STILL", frame, flush=True)
