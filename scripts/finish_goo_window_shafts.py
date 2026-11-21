"""Remove broad air illumination and use a bounded constant-density control for shafts."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-Goo-Tyndall-Rim-v1")
source = ROOT / "production-v3/Franken_Duet_Goo_Tyndall_Rim.blend"
expected = json.loads((source.parent / "preparation.json").read_text(encoding="utf-8"))
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected["project_sha256"]
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
production = ROOT / "production-v4"
production.mkdir(exist_ok=False)
air = scene.objects["Goo Tyndall | rear window air only"]
tree = air.data.materials[0].node_tree
scatter = tree.nodes["Goo Tyndall | real shadowed light scattering"]
for link in list(scatter.inputs["Density"].links):
    tree.links.remove(link)
scatter.inputs["Density"].default_value = 0.018
scene.objects["Goo daylight v2 | window gobo source"].data.volume_factor = 0
for index in range(2):
    lamp = scene.objects[f"Goo Tyndall v2 | window shaft {index}"]
    lamp.data.volume_factor = 5
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
    "volume_density_control": {
        "type": "constant within bounded rear mesh",
        "density": 0.018,
        "generated_edge_mask_connected": False,
        "broad_gobo_volume_factor": 0,
        "shaft_volume_factor": 5,
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
    print("TYNDALL_V4_STILL", frame, flush=True)
