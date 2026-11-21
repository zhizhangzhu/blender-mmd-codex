"""Fade the MMD inverted-hull outline together with the eye-occluding hair."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fix_goo_eye_ray_and_shadow import vector
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, ROOT, math, node, remap
from render_portrait_light_controls import mute_file_outputs
from revise_goo_projected_eye_shadow import world_center

register_addons()
old = ROOT / "production-v7/Franken_Duet_Goo_Eye_Hair_Stage.blend"
production = ROOT / "production-v8"
production.mkdir(parents=True, exist_ok=True)
assert not (production/'Franken_Duet_Goo_Eye_Hair_Stage.blend').exists()
bpy.ops.wm.open_mainfile(filepath=str(old), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
report = []
hair = [
    m
    for m in bpy.data.materials
    if m.node_tree and m.node_tree.nodes.get(PREFIX + "eye region bang peek")
]
for original in hair:
    mat = bpy.data.materials.get("mmd_edge." + original.name)
    if not mat:
        continue
    tree = mat.node_tree
    actor = original["performer_id"]
    geo = node(tree, "ShaderNodeNewGeometry", "outline camera ray geometry")
    masks = []
    for side in ("L", "R"):
        center = world_center(
            tree,
            scene.objects[PREFIX + actor + " eye " + side],
            side + " outline eye world",
        )
        delta = vector(
            tree,
            "SUBTRACT",
            geo.outputs["Position"],
            center,
            side + " outline eye delta",
        )
        depth = vector(
            tree,
            "DOT_PRODUCT",
            delta,
            geo.outputs["Incoming"],
            side + " outline ray depth",
        )
        parallel = node(tree, "ShaderNodeVectorMath", side + " outline parallel ray")
        parallel.operation = "SCALE"
        tree.links.new(geo.outputs["Incoming"], parallel.inputs[0])
        tree.links.new(depth, parallel.inputs[3])
        perpendicular = vector(
            tree,
            "SUBTRACT",
            delta,
            parallel.outputs[0],
            side + " outline perpendicular",
        )
        distance = vector(
            tree, "LENGTH", perpendicular, None, side + " outline eye distance"
        )
        circle = remap(
            tree, distance, 0.021, 0.043, 1, 0, side + " soft outline eye window"
        )
        front = math(
            tree, "GREATER_THAN", depth, -0.002, side + " outline front permission"
        )
        masks.append(math(tree, "MULTIPLY", circle, front, side + " outline eye mask"))
    alpha = math(
        tree,
        "MULTIPLY",
        math(tree, "MAXIMUM", *masks, "outline two eye union"),
        0.97,
        "local eye outline fade",
    )
    output = next(
        n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
    )
    old_shader = output.inputs["Surface"].links[0].from_socket
    clear = node(tree, "ShaderNodeBsdfTransparent", "outline eye transparency")
    mix = node(tree, "ShaderNodeMixShader", "outline eye fade")
    tree.links.new(alpha, mix.inputs[0])
    tree.links.new(old_shader, mix.inputs[1])
    tree.links.new(clear.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], output.inputs["Surface"])
    mat.surface_render_method = "BLENDED"
    mat.use_transparency_overlap = False
    report.append({"material": mat.name, "actor": actor, "local_outline_fade": 0.97})
assert {r['material'] for r in report}=={'mmd_edge.前鬓','mmd_edge.呆毛','mmd_edge.鬓','mmd_edge.鬓.001'},report
project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
prep = json.loads((old.parent / "preparation.json").read_text(encoding="utf-8"))
prep.update(
    source=str(old),
    source_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
    project=str(project),
    project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
    outline_eye_peek=report,
)
(production / "preparation.json").write_text(
    json.dumps(prep, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("OUTLINE_EYE_PEEK_SAVED", json.dumps(report, ensure_ascii=False), flush=True)
