"""Fix volume collection visibility and compress highlights with a fixed Reinhard shoulder."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-Goo-Tyndall-Rim-v1")
source = ROOT / "production-v2/Franken_Duet_Goo_Tyndall_Rim.blend"
expected = json.loads((source.parent / "preparation.json").read_text(encoding="utf-8"))
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected["project_sha256"]
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
production = ROOT / "production-v3"
assert not (production / "Franken_Duet_Goo_Tyndall_Rim.blend").exists()
production.mkdir(exist_ok=True)
air = scene.objects["Goo Tyndall | rear window air only"]
visibility_before = {
    "hide_render": air.hide_render,
    "hide_viewport": air.hide_viewport,
    "hide_get": air.hide_get(),
    "collections": [
        {"name": c.name, "hide_render": c.hide_render, "hide_viewport": c.hide_viewport}
        for c in air.users_collection
    ],
}
if air.name not in scene.collection.objects:
    scene.collection.objects.link(air)
air.hide_render = air.hide_viewport = False
air.hide_set(False)
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0
tree = scene.compositing_node_group
output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
image = output.inputs["Image"].links[0].from_socket
lum = tree.nodes.new("CompositorNodeRGBToBW")
lum.name = "Goo Tyndall | linear luminance"
tree.links.new(image, lum.inputs[0])


def math(operation, first, second, label):
    item = tree.nodes.new("ShaderNodeMath")
    item.name = item.label = "Goo Tyndall | " + label
    item.operation = operation
    for socket, value in zip(item.inputs, (first, second)):
        if hasattr(value, "is_output"):
            tree.links.new(value, socket)
        else:
            socket.default_value = value
    return item.outputs[0]


# Y' = min(Y,k) + s*max(Y-k,0)/(s+max(Y-k,0)); preserve RGB ratios.
y = lum.outputs[0]
base = math("MINIMUM", y, 0.75, "unchanged lower luminance")
excess = math(
    "MAXIMUM",
    math("SUBTRACT", y, 0.75, "above highlight knee"),
    0,
    "positive highlight excess",
)
shoulder = math(
    "DIVIDE",
    math("MULTIPLY", excess, 0.25, "Reinhard numerator"),
    math("ADD", excess, 0.25, "Reinhard denominator"),
    "fixed Reinhard highlight shoulder",
)
mapped = math("ADD", base, shoulder, "mapped luminance")
factor = math(
    "DIVIDE",
    mapped,
    math("MAXIMUM", y, 0.00001, "safe luminance denominator"),
    "preserve highlight chromaticity",
)
mix = tree.nodes.new("ShaderNodeMixRGB")
mix.name = mix.label = "Goo Tyndall | compress highlights after glow"
mix.blend_type = "MULTIPLY"
mix.inputs[0].default_value = 1
tree.links.new(image, mix.inputs[1])
tree.links.new(factor, mix.inputs[2])
tree.links.new(mix.outputs[0], output.inputs["Image"])
tree.links.new(mix.outputs[0], tree.nodes["Caption cache | beauty"].inputs["beauty"])
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
    "volume_visibility_before": visibility_before,
    "volume_linked_to_scene_root": True,
    "color_management": {
        "view_transform": "Standard",
        "look": "None",
        "exposure": 0,
        "compositor_tone_mapping": "Fixed luminance Reinhard shoulder above linear 0.75, asymptote 1; preserve RGB ratios, no frame-wise adaptation",
    },
    "beauty_cache_matches_final": True,
}
(production / "preparation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    "VOLUME_VISIBILITY_BEFORE",
    json.dumps(visibility_before, ensure_ascii=False),
    flush=True,
)
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.eevee.taa_render_samples = 24
for frame, label in ((4290, "portrait"), (4140, "opening")):
    scene.frame_set(frame)
    scene.render.filepath = str(production / f"{label}-{frame}.png")
    bpy.ops.render.render(write_still=True)
    print("TYNDALL_V3_STILL", frame, flush=True)
