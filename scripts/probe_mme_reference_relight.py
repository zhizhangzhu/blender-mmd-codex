import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

register_addons()
bpy.ops.wm.open_mainfile(
    filepath="D:/codex/output/MMD-Citlali-Fringe-Shadow-v1/production-v3/Franken_Citlali_Fringe_Shadow_Still.blend",
    use_scripts=False,
)
for o in bpy.context.scene.objects:
    if o.type == "LIGHT" and not o.hide_render:
        print(
            "LIGHT",
            o.name,
            o.data.energy,
            "d",
            o.data.diffuse_factor,
            "shadow",
            o.data.use_shadow,
            "groups",
            [g.name for g in o.data.light_groups.groups],
            flush=True,
        )
for name in ("颜.001", "衣.001", "手.001", "鬓.001", "衣", "颜"):
    m = bpy.data.materials.get(name)
    if not m:
        continue
    print("MAT", name, dict(m.items()), flush=True)
    for n in m.node_tree.nodes:
        if (
            n.type == "EMISSION"
            or n.bl_idname == "ShaderNodeShaderInfo"
            or any(
                x in n.name
                for x in (
                    "response_ramp",
                    "palette",
                    "warm",
                    "rim",
                    "controlled luminous",
                )
            )
        ):
            print(
                "NODE",
                name,
                n.name,
                n.bl_idname,
                [
                    (s.name, str(s.default_value)[:70])
                    for s in n.inputs
                    if hasattr(s, "default_value") and not s.is_linked
                ],
                flush=True,
            )
for n in bpy.context.scene.compositing_node_group.nodes:
    if any(
        x in n.name.lower()
        for x in (
            "stage",
            "glow",
            "bloom",
            "diffusion",
            "shoulder",
            "tone",
            "glare",
            "grade",
        )
    ):
        print(
            "COMP",
            n.name,
            n.bl_idname,
            [
                (s.name, str(s.default_value))
                for s in n.inputs
                if hasattr(s, "default_value") and not s.is_linked
            ],
            flush=True,
        )
