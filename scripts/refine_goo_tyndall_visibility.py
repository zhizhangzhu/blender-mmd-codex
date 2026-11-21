"""Make the requested window shafts readable with explicit art-directed light linking."""

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
source = ROOT / "production-v1/Franken_Duet_Goo_Tyndall_Rim.blend"
expected = json.loads((source.parent / "preparation.json").read_text(encoding="utf-8"))
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected["project_sha256"]
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
production = ROOT / "production-v2"
production.mkdir(exist_ok=False)
air = scene.objects["Goo Tyndall | rear window air only"]
receivers = bpy.data.collections.new("Goo Tyndall v2 | air receiver")
receivers.objects.link(air)
receivers.collection_objects[0].light_linking.link_state = "INCLUDE"
blockers = bpy.data.collections.new("Goo Tyndall v2 | window slats")
scene.collection.children.link(blockers)
lights = []
for index, (position, target) in enumerate(
    (((-3.4, 7.2, 6.5), (1.5, 2.7, 0.6)), ((-1.4, 8.0, 6.8), (3.3, 3.2, 0.6)))
):
    data = bpy.data.lights.new(f"Goo Tyndall v2 | window shaft {index}", "SPOT")
    data.energy = 4000
    data.color = (0.93, 0.97, 1)
    data.spot_size, data.spot_blend = 0.23, 0.40
    data.shadow_soft_size = 0.025
    data.diffuse_factor, data.specular_factor, data.volume_factor = 0, 0, 3.5
    data.use_shadow = True
    lamp = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(lamp)
    lamp.location = position
    rotation = (Vector(target) - lamp.location).to_track_quat("-Z", "Y")
    lamp.rotation_euler = rotation.to_euler()
    lamp.light_linking.receiver_collection = receivers
    lamp.light_linking.blocker_collection = blockers
    center = lamp.location.lerp(Vector(target), 0.32)
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    slat = bpy.context.object
    slat.name = f"Goo Tyndall v2 | shaft divider {index}"
    slat.rotation_euler = rotation.to_euler()
    slat.scale = (0.045, 0.9, 0.045)
    for collection in list(slat.users_collection):
        collection.objects.unlink(slat)
    blockers.objects.link(slat)
    blockers.collection_objects[
        len(blockers.objects) - 1
    ].light_linking.link_state = "INCLUDE"
    lights.append(
        {
            "name": lamp.name,
            "position": list(lamp.location),
            "target": list(target),
            "energy": data.energy,
            "volume_factor": data.volume_factor,
            "diffuse_factor": 0,
            "specular_factor": 0,
        }
    )
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.70
scene.render.compositor_device = "CPU"
scene.render.compositor_precision = "AUTO"
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 24
scene.frame_set(4290)
project = production / "Franken_Duet_Goo_Tyndall_Rim.blend"
scene.render.filepath = str(production / "portrait-4290.png")
bpy.ops.wm.save_as_mainfile(filepath=str(project))
report = {
    **expected,
    "source": str(source),
    "source_sha256": expected["project_sha256"],
    "project": str(project),
    "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
    "window_shafts": lights,
    "shaft_shadow_linking": "Art-directed window slats only; original architecture excluded for these volume-only lamps. Not certification of original architectural window transmission.",
    "color_management": {"view_transform": "AgX", "look": "None", "exposure": 0.7},
    "compositor_device": "CPU",
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
    print("TYNDALL_V2_STILL", frame, flush=True)
