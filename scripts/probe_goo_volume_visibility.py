"""Read actual volume toggles and view-layer visibility without rendering or saving."""

import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

register_addons()
bpy.ops.wm.open_mainfile(
    filepath="D:/codex/output/MMD-Goo-Tyndall-Rim-v1/production-v4/Franken_Duet_Goo_Tyndall_Rim.blend",
    load_ui=False,
    use_scripts=False,
)
scene = bpy.context.scene
air = scene.objects["Goo Tyndall | rear window air only"]
out = {
    "eevee": {
        p.identifier: getattr(scene.eevee, p.identifier)
        for p in scene.eevee.bl_rna.properties
        if "volum" in p.identifier
    },
    "layers": [
        {"name": v.name, "enabled": v.use, "air_visible": air.visible_get(view_layer=v)}
        for v in scene.view_layers
    ],
    "render_layers": [
        {"node": n.name, "scene": n.scene.name if n.scene else None, "layer": n.layer}
        for n in scene.compositing_node_group.nodes
        if n.type == "R_LAYERS"
    ],
    "density": air.data.materials[0]
    .node_tree.nodes["Goo Tyndall | real shadowed light scattering"]
    .inputs["Density"]
    .default_value,
}
path = Path("D:/codex/temp/MMD-Goo-Rim-Glow-v1/volume-visibility.json")
path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2), flush=True)
