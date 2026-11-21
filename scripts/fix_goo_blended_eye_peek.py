"""Remove the failed dark eye-region result and test smooth alpha-blended bangs."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, ROOT
from render_portrait_light_controls import mute_file_outputs

register_addons()
old = ROOT / "production-v6/Franken_Duet_Goo_Eye_Hair_Stage.blend"
production = ROOT / "production-v7"
production.mkdir(parents=True, exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(old), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
changes = []
for mat in bpy.data.materials:
    tree = mat.node_tree
    if not tree or not tree.nodes.get(PREFIX + "eye region bang peek"):
        continue
    shade = tree.nodes.get(PREFIX + "hair value before drawn highlights")
    if shade:
        source = shade.inputs[1].links[0].from_socket
        for edge in list(shade.outputs[0].links):
            tree.links.new(source, edge.to_socket)
    mat.surface_render_method = "BLENDED"
    mat.use_transparency_overlap = False
    tree.nodes[PREFIX + "ray corrected bang transparency"].inputs[
        1
    ].default_value = 0.78
    changes.append(
        {
            "material": mat.name,
            "method": mat.surface_render_method,
            "overlap": mat.use_transparency_overlap,
            "removed_dark_gradient": True,
        }
    )
project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
prep = json.loads((old.parent / "preparation.json").read_text(encoding="utf-8"))
prep.update(
    source=str(old),
    source_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
    project=str(project),
    project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
    smooth_eye_alpha=changes,
)
(production / "preparation.json").write_text(
    json.dumps(prep, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("SMOOTH_EYE_ALPHA_SAVED", flush=True)
