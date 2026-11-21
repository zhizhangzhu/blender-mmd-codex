"""Compare opaque closures and isolate a silver-hair regression in fresh renders."""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, ROOT
from render_portrait_light_controls import mute_file_outputs

register_addons()
for version in (5, 10):
    bpy.ops.wm.open_mainfile(
        filepath=str(
            ROOT / f"production-v{version}/Franken_Duet_Goo_Eye_Hair_Stage.blend"
        ),
        use_scripts=False,
    )
    for name in ("前鬓", "鬓.001"):
        m = bpy.data.materials[name]
        t = m.node_tree
        output = next(
            n for n in t.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
        )
        for n in (
            output,
            t.nodes[PREFIX + "eye region bang peek"],
            t.nodes.get("Look v3 | NPR surface")
            or t.nodes.get("Ikhor character | controlled NPR surface"),
        ):
            print(
                "GRAPH",
                version,
                name,
                m.surface_render_method,
                n.name,
                [
                    (s.name, [(l.from_node.name, l.from_socket.name) for l in s.links])
                    for s in n.inputs
                ],
                flush=True,
            )
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.eevee.taa_render_samples = 16
scene.render.image_settings.file_format = "JPEG"
for variant in ("bypass-ramp", "original-mix", "blended-opaque"):
    for m in bpy.data.materials:
        if not m.node_tree or m.get("performer_id") != "aksiniya":
            continue
        t = m.node_tree
        if not t.nodes.get(PREFIX + "final hair value ramp"):
            continue
        output = next(
            n for n in t.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
        )
        if variant == "bypass-ramp":
            surf = t.nodes["Look v3 | NPR surface"]
            source = (
                t.nodes[PREFIX + "final hair value ramp"].inputs[1].links[0].from_socket
            )
            t.links.new(source, surf.inputs["Color"])
        elif variant == "original-mix":
            t.links.new(
                t.nodes[PREFIX + "eye region bang peek"].outputs[0],
                output.inputs["Surface"],
            )
            t.nodes[PREFIX + "projected bang transparency"].inputs[1].default_value = 0
        else:
            m.surface_render_method = "BLENDED"
    scene.render.filepath = f"D:/codex/temp/jelly-eye-study-v1/{variant}.jpg"
    bpy.ops.render.render(write_still=True)
    print("DIAG_RENDER", variant, flush=True)
