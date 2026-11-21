"""Diagnose actual exterior-sun visibility on the saved floor only; never save."""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

register_addons()
root = Path("D:/codex/output/MMD-Goo-Wedding-v2/production-v1")
bpy.ops.wm.open_mainfile(
    filepath=str(root / "Franken_Duet_Goo_Daylight.blend"),
    load_ui=False,
    use_scripts=False,
)
s = bpy.context.scene
mute_file_outputs()
s.frame_set(4140)
for name in (
    "Stage art | ground only | mat_10.001",
    "Stage art | ground only | mat_20.010",
    "mat_20.010",
):
    t = bpy.data.materials[name].node_tree
    info = t.nodes.new("ShaderNodeShaderInfo")
    info.use_own_light_groups = True
    info.light_groups.use_default = False
    info.light_groups.groups.add().name = "Goo daylight exterior sun"
    emit = t.nodes.new("ShaderNodeEmission")
    t.links.new(info.outputs["Cast Shadows"], emit.inputs[0])
    output = next(
        n for n in t.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
    )
    t.links.new(emit.outputs[0], output.inputs["Surface"])
import goo_engine_light_groups

goo_engine_light_groups.sync_light_groups()
s.render.resolution_percentage = 67
s.eevee.taa_render_samples = 16
s.render.filepath = str(root / "external-sun-visibility-study.png")
bpy.ops.render.render(write_still=True)
