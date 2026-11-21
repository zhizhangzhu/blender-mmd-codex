"""Frame the rear shafts and keep their real shadow dividers outside the camera."""

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
source = ROOT / "production-v6/Franken_Duet_Goo_Tyndall_Rim.blend"
expected = json.loads((source.parent / "preparation.json").read_text(encoding="utf-8"))
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected["project_sha256"]
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
production = ROOT / "production-v7"
production.mkdir(exist_ok=False)
lights = []
for index, (position, target) in enumerate(
    (((-1.4, 1.8, 3.05), (0.8, 1.8, 0.15)), ((0.1, 2.3, 3.15), (2.0, 2.3, 0.15)))
):
    lamp = scene.objects[f"Goo Tyndall v2 | window shaft {index}"]
    lamp.location = position
    rotation = (Vector(target) - lamp.location).to_track_quat("-Z", "Y")
    lamp.rotation_euler = rotation.to_euler()
    lamp.data.energy, lamp.data.volume_factor = 5000, 4
    lamp.data.spot_size, lamp.data.spot_blend = 0.20, 0.42
    slat = scene.objects[f"Goo Tyndall v2 | shaft divider {index}"]
    slat.location = lamp.location.lerp(Vector(target), 0.06)
    slat.rotation_euler = rotation.to_euler()
    slat.scale = (0.004, 0.35, 0.015)
    lights.append(
        {
            "name": lamp.name,
            "position": list(position),
            "target": list(target),
            "energy": lamp.data.energy,
            "volume_factor": lamp.data.volume_factor,
            "diffuse": lamp.data.diffuse_factor,
            "specular": lamp.data.specular_factor,
            "actual_geometry_shadows": True,
            "spot_blend": lamp.data.spot_blend,
        }
    )
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
    "framing_revision": "Lights inside ceiling, shafts cross visible rear air, window slats moved to 6% of source-target distance outside camera instead of visible midair bars",
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
    print("TYNDALL_V7_STILL", frame, flush=True)
