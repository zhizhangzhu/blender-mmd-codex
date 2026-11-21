"""Read the current build's actual shadow budget controls."""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

register_addons()
bpy.ops.wm.open_mainfile(
    filepath="D:/codex/output/MMD-Jelly-Eyes-v1/production-v15/Franken_Duet_Goo_Eye_Hair_Stage.blend",
    use_scripts=False,
)
scene = bpy.context.scene
for prop in scene.eevee.bl_rna.properties:
    if "shadow" in prop.identifier:
        print(
            "SCENE_SHADOW",
            prop.identifier,
            str(getattr(scene.eevee, prop.identifier)),
            getattr(prop, "hard_min", ""),
            getattr(prop, "hard_max", ""),
            flush=True,
        )
for obj in scene.objects:
    if obj.type != "LIGHT" or obj.hide_render or not obj.data.use_shadow:
        continue
    data = obj.data
    print(
        "LAMP_SHADOW",
        obj.name,
        data.type,
        data.energy,
        [
            (p.identifier, str(getattr(data, p.identifier)))
            for p in data.bl_rna.properties
            if "shadow" in p.identifier
        ],
        flush=True,
    )
