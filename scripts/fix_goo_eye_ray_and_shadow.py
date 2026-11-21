"""Use world-space camera rays for eye peek and observable NPR shadow controls."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, ROOT, color, link, math, node, remap
from render_portrait_light_controls import mute_file_outputs
from revise_goo_projected_eye_shadow import world_center


def vector(tree, op, a, b, label):
    n = node(tree, "ShaderNodeVectorMath", label)
    n.operation = op
    link(tree, a, n.inputs[0])
    if b is not None:
        link(tree, b, n.inputs[1])
    return n.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH") else n.outputs[0]


def main():
    old = ROOT / "production-v5/Franken_Duet_Goo_Eye_Hair_Stage.blend"
    production = ROOT / "production-v6"
    production.mkdir(parents=True, exist_ok=False)
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(old), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    changes = []
    for mat in bpy.data.materials:
        actor = mat.get("performer_id")
        if actor not in ("aksiniya", "ikhor") or not mat.node_tree:
            continue
        tree = mat.node_tree
        is_hair = tree.nodes.get(PREFIX + "eye region bang peek") is not None
        is_face = mat.name in ("颜", "颜.001")
        if not (is_hair or is_face):
            continue
        geo = node(tree, "ShaderNodeNewGeometry", "camera ray geometry")
        if is_hair:
            masks = []
            for side in ("L", "R"):
                center = world_center(
                    tree,
                    scene.objects[PREFIX + actor + " eye " + side],
                    side + " ray eye world",
                )
                delta = vector(
                    tree,
                    "SUBTRACT",
                    geo.outputs["Position"],
                    center,
                    side + " surface minus eye",
                )
                depth = vector(
                    tree,
                    "DOT_PRODUCT",
                    delta,
                    geo.outputs["Incoming"],
                    side + " signed ray depth",
                )
                parallel = node(
                    tree, "ShaderNodeVectorMath", side + " parallel eye ray"
                )
                parallel.operation = "SCALE"
                tree.links.new(geo.outputs["Incoming"], parallel.inputs[0])
                tree.links.new(depth, parallel.inputs[3])
                perpendicular = vector(
                    tree,
                    "SUBTRACT",
                    delta,
                    parallel.outputs[0],
                    side + " perpendicular eye distance vector",
                )
                distance = vector(
                    tree, "LENGTH", perpendicular, None, side + " eye ray distance"
                )
                circle = remap(
                    tree,
                    distance,
                    0.020,
                    0.041,
                    1,
                    0,
                    side + " soft projected eye ray window",
                )
                front = math(
                    tree,
                    "GREATER_THAN",
                    depth,
                    0.0002,
                    side + " eye ray front permission",
                )
                masks.append(
                    math(tree, "MULTIPLY", circle, front, side + " eye ray mask")
                )
            alpha = math(
                tree,
                "MULTIPLY",
                math(tree, "MAXIMUM", *masks, "both eye ray masks"),
                0.76,
                "ray corrected bang transparency",
            )
            tree.links.new(alpha, tree.nodes[PREFIX + "eye region bang peek"].inputs[0])
            tree.links.new(
                alpha, tree.nodes[PREFIX + "eye peek mask diagnostic"].inputs["Value"]
            )
        ao = node(tree, "ShaderNodeAmbientOcclusion", "local hair contact occlusion")
        ao.only_local = True
        ao.samples = 16
        ao.inputs["Distance"].default_value = 0.045 if is_hair else 0.065
        info = next(
            n
            for n in tree.nodes
            if n.bl_idname == "ShaderNodeShaderInfo" and n.use_own_light_groups
        )
        if is_hair:
            shade = remap(
                tree,
                info.outputs["Half-lambert factor"],
                0.42,
                0.94,
                0.48,
                1.03,
                "visible directional hair value",
            )
            shade = math(
                tree,
                "MULTIPLY",
                shade,
                remap(tree, ao.outputs["AO"], 0, 1, 0.66, 1, "hair contact retention"),
                "hair form plus local contact",
            )
            target = (
                tree.nodes.get("Character layers | one directional hair highlight")
                if actor == "aksiniya"
                else tree.nodes.get("Ikhor character | one hair highlight application")
            )
            if target:
                socket = (
                    target.inputs[1] if target.type == "MIX_RGB" else target.inputs[0]
                )
                old_color = socket.links[0].from_socket
            else:
                emission = tree.nodes.get("Look v3 | NPR surface") or tree.nodes.get(
                    "Ikhor character | controlled NPR surface"
                )
                socket = emission.inputs["Color"]
                old_color = socket.links[0].from_socket
            shaded = color(
                tree,
                "MULTIPLY",
                old_color,
                shade,
                1,
                "hair value before drawn highlights",
            )
            tree.links.new(shaded, socket)
        if is_face:
            response = tree.nodes["Goo portrait | separate cast shadow response"]
            existing = response.inputs["Value"].links[0].from_socket
            combined = math(
                tree,
                "MINIMUM",
                existing,
                ao.outputs["AO"],
                "native face shadow and short contact",
            )
            tree.links.new(combined, response.inputs["Value"])
            surface = (
                tree.nodes.get("Look v3 | NPR surface")
                or tree.nodes["Ikhor character | controlled NPR surface"]
            )
            base = surface.inputs["Color"].links[0].from_socket
            # A small head-attached analytic nose SDF supplies authored anime form on a flat MMD face.
            coord = node(tree, "ShaderNodeTexCoord", "nose head local coordinates")
            coord.object = scene.objects[PREFIX + actor + " eye L"]
            sep = node(tree, "ShaderNodeSeparateXYZ", "nose head local XYZ")
            tree.links.new(coord.outputs["Object"], sep.inputs[0])
            eye = scene.objects[PREFIX + actor + " eye L"]["rest_eye_center"]
            x = math(
                tree,
                "DIVIDE",
                math(
                    tree,
                    "ADD",
                    sep.outputs["X"],
                    eye[0] - 0.002,
                    "nose local horizontal",
                ),
                0.006,
                "nose horizontal radius",
            )
            z = math(
                tree,
                "DIVIDE",
                math(tree, "ADD", sep.outputs["Z"], 0.028, "nose below eye"),
                0.010,
                "nose vertical radius",
            )
            r2 = math(
                tree,
                "ADD",
                math(tree, "MULTIPLY", x, x, "nose X2"),
                math(tree, "MULTIPLY", z, z, "nose Z2"),
                "nose ellipse SDF",
            )
            mask = remap(tree, r2, 0.55, 1.3, 0.25, 0, "soft warm nose form")
            tinted = color(
                tree,
                "MULTIPLY",
                base,
                (1, 0.70, 0.58, 1),
                mask,
                "subtle peach nose shade",
            )
            tree.links.new(tinted, surface.inputs["Color"])
        changes.append(
            {
                "material": mat.name,
                "ray_peek": is_hair,
                "direct_hair_value": is_hair,
                "short_local_AO": True,
                "authored_nose_SDF": is_face,
            }
        )
    project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.eevee.taa_render_samples = 24
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    prep = json.loads((old.parent / "preparation.json").read_text(encoding="utf-8"))
    prep.update(
        source=str(old),
        source_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
        project=str(project),
        project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
        ray_fix=changes,
    )
    (production / "preparation.json").write_text(
        json.dumps(prep, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("EYE_RAY_FIX_SAVED", project, flush=True)


if __name__ == "__main__":
    main()
