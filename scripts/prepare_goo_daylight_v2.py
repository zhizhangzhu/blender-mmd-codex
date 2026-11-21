"""Revise only the pinned Goo v1 copy after the MME lighting study."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from portrait_key_fill import TARGETS
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-Goo-Wedding-v2")
SOURCE = Path(
    "D:/codex/output/MMD-Goo-Wedding-v1/production-v1/Franken_Duet_Goo_Wedding.blend"
)
SOURCE_SHA = "707c959284e846437f5f1abeeec7ce8f69606ad68cc14904521397d89f7039b3"
PREFIX = "Goo daylight v2 | "


def new(tree, kind, name):
    n = tree.nodes.new(kind)
    n.name = n.label = PREFIX + name
    return n


def info(tree, group):
    n = new(tree, "ShaderNodeShaderInfo", group)
    n.use_own_light_groups = True
    n.light_groups.use_default = False
    n.light_groups.groups.add().name = group
    return n


def multiply_input(tree, socket, signal, name):
    n = new(tree, "ShaderNodeMixRGB", name)
    n.blend_type = "MULTIPLY"
    n.inputs[0].default_value = 1
    if socket.is_linked:
        tree.links.new(socket.links[0].from_socket, n.inputs[1])
    else:
        n.inputs[1].default_value = socket.default_value
    tree.links.new(signal, n.inputs[2])
    tree.links.new(n.outputs[0], socket)


def shadow_range(tree, output, low, high, label):
    n = new(tree, "ShaderNodeMapRange", label)
    n.clamp = True
    n.inputs["To Min"].default_value = low
    n.inputs["To Max"].default_value = high
    tree.links.new(output, n.inputs["Value"])
    return n.outputs["Result"]


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    root = ROOT / "production-v1"
    root.mkdir(parents=True, exist_ok=False)
    addons = register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    original_camera = scene.camera
    assert abs(original_camera.data.lens - 61.734649658203125) < 0.0001
    mute_file_outputs()
    changes = {
        "source": str(SOURCE),
        "source_sha256": SOURCE_SHA,
        "addons": addons,
        "materials": [],
        "lights": [],
        "original_camera": original_camera.name,
        "physics_resimulated": False,
    }
    # Reuse the existing stage graph, sky and lights; retain alpha, matcap and GGX.
    for m in bpy.data.materials:
        tree = m.node_tree
        if not tree:
            continue
        n = tree.nodes.get("Portrait day stage | bounded daylight response")
        if n:
            n.inputs["From Min"].default_value = 0.05
            n.inputs["From Max"].default_value = 0.65
            n.inputs["To Min"].default_value = 0.62
            n.inputs["To Max"].default_value = 1.24
            changes["materials"].append(
                {
                    "name": m.name,
                    "change": "brighter stage response with retained directional contrast",
                }
            )
    for o in scene.objects:
        if o.type != "LIGHT":
            continue
        if o.name.startswith("Portrait day stage |"):
            o.data.energy *= 1.18
        if o.name.startswith("Bold wedding |") and "beam" in o.name:
            # Existing stage spot colors are retained at a daylight accent level.
            o.data.energy *= 0.35
        if o.name.endswith("| reflection") and o.name.startswith("Reference duet |"):
            o.data.energy *= 0.78
    sun = scene.objects["Portrait daylight | exterior sun"]
    sun.data.energy = 2.4
    sun.data.angle = 0.018
    sun.data.color = (1, 0.95, 0.88)
    sun.data.light_groups.groups.add().name = "Goo daylight exterior sun"
    sun.data.light_groups.use_default = True
    portal = scene.objects["Portrait v2 | window portal shadow key"]
    portal.data.energy = 650
    portal.data.size = 0.22
    portal.data.color = (1, 0.96, 0.90)
    portal.data.light_groups.groups.add().name = "Goo daylight floor shadow"
    portal.data.light_groups.use_default = True
    for obj in (sun, portal):
        changes["lights"].append(
            {
                "name": obj.name,
                "energy": obj.data.energy,
                "position": list(obj.location),
            }
        )
    # Explicit occlusion on the existing physical floor base; other lamps cannot wash it away.
    for name in (
        "Stage art | ground only | mat_10.001",
        "Stage art | ground only | mat_20.010",
    ):
        m = bpy.data.materials[name]
        tree = m.node_tree
        n = info(tree, "Goo daylight floor shadow")
        factor = shadow_range(
            tree, n.outputs["Cast Shadows"], 0.48, 1.0, "readable floor cast shadow"
        )
        pbr = tree.nodes.get("Focused light | responsive stage surface")
        if pbr is None:
            pbr = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
        multiply_input(
            tree,
            pbr.inputs["Base Color"],
            factor,
            "physical ground base with cast visibility",
        )
        changes["materials"].append(
            {
                "name": name,
                "change": "native Goo floor occlusion, retained physical surface",
            }
        )
    # Match the references' pale skin, two-tone clothes and one restrained rim side.
    for actor, mats in TARGETS.items():
        for name, (_, role) in mats.items():
            tree = bpy.data.materials[name].node_tree
            ramp = tree.nodes[
                "Portrait relight | keyfill | single portrait palette"
            ].color_ramp
            if role in ("face", "skin"):
                ramp.interpolation = "EASE"
                for e in ramp.elements:
                    c = list(e.color)
                    c[1] *= 0.988
                    c[2] *= 1.018
                    e.color = c
            elif role == "cloth":
                ramp.interpolation = "EASE"
                elems = list(ramp.elements)
                elems[0].position = 0.34
                elems[1].position = 0.58
                elems[-1].position = 0.83
            changes["materials"].append(
                {
                    "name": name,
                    "actor": actor,
                    "change": "existing single palette adjusted; source albedo and alpha retained",
                }
            )
    for m in bpy.data.materials:
        actor = m.get("performer_id")
        if actor not in ("aksiniya", "ikhor") or not m.node_tree:
            continue
        tree = m.node_tree
        gain = tree.nodes.get("Portrait relight | rimink | left HDR gain only")
        if gain is None:
            continue
        # Like PostRimLightToon's shadow exclusion: independently suppress key-occluded rims.
        n = tree.nodes.get("Goo portrait | native key light information") or info(
            tree, "Goo portrait key | " + actor
        )
        visibility = shadow_range(
            tree, n.outputs["Cast Shadows"], 0.32, 1, "rim cast shadow permission"
        )
        for side, relative, color in (
            ("left", 0.95, (1.05, 0.96, 0.91)),
            ("right", 0.34, (0.72, 0.85, 1.1)),
        ):
            g = tree.nodes["Portrait relight | rimink | " + side + " HDR gain only"]
            g.inputs[1].default_value *= relative
            gate = new(tree, "ShaderNodeMath", side + " shadow gated rim")
            gate.operation = "MULTIPLY"
            tree.links.new(g.outputs[0], gate.inputs[0])
            tree.links.new(visibility, gate.inputs[1])
            rgb = tree.nodes["Portrait relight | rimink | " + side + " warm HDR RGB"]
            rgb.inputs[0].default_value = color
            tree.links.new(gate.outputs[0], rgb.inputs[3])
        changes["materials"].append(
            {"name": m.name, "change": "key-shadow gated warm/cool asymmetric rim"}
        )
    # Restrain the existing painted hair highlight without installing a second lobe.
    for name in ("前鬓", "呆毛", "鬓"):
        tree = bpy.data.materials[name].node_tree
        value = tree.nodes.get("Character layers | hair highlight strength")
        if value:
            value.outputs[0].default_value *= 0.86
    # Keep the original camera and all its Actions. Add a short floor-readable opening shot.
    data = bpy.data.cameras.new("Goo daylight v2 | full body opening")
    cam = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(cam)
    cam.location = (0, -5.5, 2.6)
    cam.rotation_euler = (
        (Vector((0.2, 0.4, 0.52)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    )
    data.lens = 32
    data.dof.use_dof = True
    data.dof.focus_distance = (Vector((0, 0.4, 1)) - cam.location).length
    data.dof.aperture_fstop = 6.3
    marker = scene.timeline_markers.new("Goo daylight | fullbody opening", frame=4140)
    marker.camera = cam
    marker = scene.timeline_markers.new(
        "Goo daylight | original portrait camera", frame=4230
    )
    marker.camera = original_camera
    scene["goo_daylight_v2_camera"] = json.dumps(
        {
            "fullbody": [4140, 4228],
            "original": [4230, 4438],
            "original_camera": original_camera.name,
        }
    )
    import goo_engine_light_groups

    goo_engine_light_groups.sync_light_groups()
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 24
    scene.render.use_motion_blur = False
    scene.render.use_sequencer = False
    scene.render.image_settings.file_format = "PNG"
    project = root / "Franken_Duet_Goo_Daylight.blend"
    scene.frame_set(4290)
    scene.camera = original_camera
    scene.render.filepath = str(root / "portrait-4290.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    changes.update(
        project=str(project),
        project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
    )
    (root / "preparation.json").write_text(
        json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    bpy.ops.render.render(write_still=True)
    # Marker cameras are reapplied at render time, so explicitly unbind for this diagnostic.
    for marker in scene.timeline_markers:
        marker.camera = None
    scene.camera = cam
    scene.render.filepath = str(root / "fullbody-4290.png")
    bpy.ops.render.render(write_still=True)
    print("GOO_DAYLIGHT_V2_STUDIES_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
