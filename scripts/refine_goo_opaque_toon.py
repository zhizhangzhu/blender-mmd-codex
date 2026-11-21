"""Repair legacy ramp insertion and refine the face-shadow footprint."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, ROOT, color, node, remap
from prepare_goo_toon_face_hair_study import face_masks
from render_portrait_light_controls import mute_file_outputs

register_addons()
old = ROOT / "production-v9/Franken_Duet_Goo_Eye_Hair_Stage.blend"
production = ROOT / "production-v10"
production.mkdir(parents=True, exist_ok=False)
directory = production / "shadow-study"
directory.mkdir()
bpy.ops.wm.open_mainfile(filepath=str(old), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
for mat in bpy.data.materials:
    if not mat.node_tree:
        continue
    tree = mat.node_tree
    inserted = tree.nodes.get(PREFIX + "opaque hair ramp before highlight")
    if inserted:
        original = inserted.inputs[1].links[0].from_socket
        for edge in list(inserted.outputs[0].links):
            tree.links.new(original, edge.to_socket)
        surface = tree.nodes.get("Look v3 | NPR surface") or tree.nodes.get(
            "Ikhor character | controlled NPR surface"
        )
        old_color = surface.inputs["Color"].links[0].from_socket
        luminance = node(tree, "ShaderNodeRGBToBW", "hair highlight protection")
        tree.links.new(old_color, luminance.inputs[0])
        amount = remap(
            tree, luminance.outputs[0], 0.65, 1.6, 1, 0, "preserve HDR hair highlights"
        )
        result = color(
            tree,
            "MULTIPLY",
            old_color,
            tree.nodes[PREFIX + "authored cool warm hair ramp"].outputs[0],
            amount,
            "final hair value ramp",
        )
        tree.links.new(result, surface.inputs["Color"])
stats = []
for actor, objname, face in (
    ("aksiniya", "阿克西妮娅2_mesh", "颜"),
    ("ikhor", "Ikhor | mesh | Ikhor_mesh", "颜.001"),
):
    shadow, nose, row = face_masks(scene, scene.objects[objname], actor, directory)
    tree = bpy.data.materials[face].node_tree
    tree.nodes[PREFIX + "geometry derived hair shadow"].image = shadow
    tree.nodes[PREFIX + "authored nose form mask"].image = nose
    tree.nodes[PREFIX + "warm nose authored form"].inputs[2].default_value = (
        1,
        0.74,
        0.60,
        1,
    )
    stats.append({"actor": actor, **row})
project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
prep = json.loads((old.parent / "preparation.json").read_text(encoding="utf-8"))
prep.update(
    source=str(old),
    source_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
    project=str(project),
    project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
    refined_shadow_stats=stats,
)
(production / "preparation.json").write_text(
    json.dumps(prep, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("OPAQUE_TOON_REFINED", flush=True)
