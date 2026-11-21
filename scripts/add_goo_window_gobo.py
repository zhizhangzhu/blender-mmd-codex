"""Add an off-camera physical window-pattern lighting accessory to Goo v2."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_daylight_v2 import info, multiply_input, shadow_range
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-Goo-Wedding-v2")
source = ROOT / "production-v1/Franken_Duet_Goo_Daylight.blend"
expected = json.loads((source.parent / "preparation.json").read_text(encoding="utf-8"))
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected["project_sha256"]
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
s = bpy.context.scene
mute_file_outputs()
root = ROOT / "production-v2"
root.mkdir(parents=True, exist_ok=False)
name = "Goo daylight v2 | window gobo source"
data = bpy.data.lights.new(name, "SPOT")
data.energy, data.spot_size, data.spot_blend = 10000, 1.05, 0.24
data.shadow_soft_size = 0.045
data.color = (1, 0.96, 0.88)
data.volume_factor = 0
data.specular_factor = 0.35
data.light_groups.use_default = True
data.light_groups.groups.add().name = "Goo daylight window pattern"
lamp = bpy.data.objects.new(name, data)
s.collection.objects.link(lamp)
lamp.location = (-12, -8, 12)
target = Vector((0, 6, 0))
rotation = (target - lamp.location).to_track_quat("-Z", "Y")
lamp.rotation_euler = rotation.to_euler()
lamp.light_linking.receiver_collection = bpy.data.collections[
    "Portrait day stage | stage receivers"
]
center = lamp.location.lerp(target, 0.37)
accessory = bpy.data.collections.new("Goo daylight v2 | window pattern blockers")
s.collection.children.link(accessory)
bars = []


def bar(label, local, scale):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center + rotation @ Vector(local))
    obj = bpy.context.object
    obj.name = "Goo daylight v2 | gobo " + label
    obj.rotation_euler = rotation.to_euler()
    obj.scale = scale
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    accessory.objects.link(obj)
    bars.append(obj.name)


for i, y in enumerate((-1.2, 0, 1.2)):
    bar("horizontal " + str(i), (0, y, 0), (5.8, 0.08, 0.04))
for i, x in enumerate((-1.5, 1.5)):
    bar("vertical " + str(i), (x, 0, 0), (0.07, 3.9, 0.04))
for mname in (
    "Stage art | ground only | mat_10.001",
    "Stage art | ground only | mat_20.010",
):
    tree = bpy.data.materials[mname].node_tree
    n = info(tree, "Goo daylight window pattern")
    factor = shadow_range(
        tree, n.outputs["Cast Shadows"], 0.72, 1.09, "window pattern contrast"
    )
    pbr = tree.nodes.get("Focused light | responsive stage surface") or next(
        n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"
    )
    multiply_input(
        tree, pbr.inputs["Base Color"], factor, "window pattern on physical floor"
    )
import goo_engine_light_groups

goo_engine_light_groups.sync_light_groups()
s.frame_set(4290)
s.render.filepath = str(root / "portrait-4290.png")
project = root / "Franken_Duet_Goo_Daylight.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
report = {
    **expected,
    "source": str(source),
    "source_sha256": expected["project_sha256"],
    "project": str(project),
    "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
    "window_pattern": {
        "technique": "off-camera physical gobo blocks a stage-linked Spot; geometric shadows, not the original window-frame layout",
        "source": lamp.name,
        "position": list(lamp.location),
        "energy_watts": data.energy,
        "blockers": bars,
    },
    "camera_opening_seconds": 1.5,
}
(root / "preparation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
s.frame_set(4140)
s.render.filepath = str(root / "opening-4140.png")
bpy.ops.render.render(write_still=True)
print("GOO_WINDOW_GOBO_STUDY_COMPLETE", flush=True)
