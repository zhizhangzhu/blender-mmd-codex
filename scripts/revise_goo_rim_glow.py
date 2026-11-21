"""Inspect or revise the pinned Goo v2 light response in a new output directory."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

SOURCE = Path(
    "D:/codex/output/MMD-Goo-Wedding-v2/production-v2/Franken_Duet_Goo_Daylight.blend"
)
SHA = "ca610cdaea99f9eca19e9067c42f5ada798a710e9f07f49b6aef8dcbb958a71f"
ROOT = Path("D:/codex/output/MMD-Goo-Rim-Glow-v1")
TEMP = Path("D:/codex/temp/MMD-Goo-Rim-Glow-v1")


def inputs(node):
    result = {}
    for socket in node.inputs:
        if hasattr(socket, "default_value"):
            value = socket.default_value
            result[socket.identifier] = {
                "linked": socket.is_linked,
                "value": list(value)
                if not isinstance(value, str) and hasattr(value, "__len__")
                else value,
            }
    return result


def inspect():
    result = {"materials": {}, "compositor": [], "lights": []}
    for m in bpy.data.materials:
        if m.node_tree and m.get("performer_id"):
            nodes = [
                {
                    "name": n.name,
                    "type": n.bl_idname,
                    "inputs": inputs(n),
                    "value": n.outputs[0].default_value if n.type == "VALUE" else None,
                }
                for n in m.node_tree.nodes
                if any(
                    k in n.name.lower()
                    for k in ("hdr gain", "highlight", "hair band", "gold", "roughness")
                )
            ]
            result["materials"][m.name] = {
                "actor": m.get("performer_id"),
                "nodes": nodes,
            }
    for tree in bpy.data.node_groups:
        for n in tree.nodes:
            if n.type == "GLARE":
                result["compositor"].append(
                    {"tree": tree.name, "name": n.name, "inputs": inputs(n)}
                )
    result["lights"] = [
        {
            "name": o.name,
            "energy": o.data.energy,
            "diffuse": o.data.diffuse_factor,
            "specular": o.data.specular_factor,
        }
        for o in bpy.context.scene.objects
        if o.type == "LIGHT"
        and ("reflection" in o.name or "rim" in o.name or "portrait" in o.name.lower())
    ]
    return result


def render_control(scene, path, frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.render.use_motion_blur = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA
    TEMP.mkdir(parents=True, exist_ok=True)
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    assert abs(scene.camera.data.lens - 61.734649658203125) < 0.0001
    mute_file_outputs()
    if args.inspect:
        (TEMP / "inventory.json").write_text(
            json.dumps(inspect(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("GOO_RIM_GLOW_INVENTORY_COMPLETE", flush=True)
        return
    from snapshot_goo_scene import capture

    production = ROOT / "production-v1"
    production.mkdir(parents=True, exist_ok=False)
    controls = ROOT / "controls"
    controls.mkdir()
    before = capture()
    changes = []
    for frame in (4140, 4290):
        render_control(scene, controls / f"before-{frame}.png", frame)
    for m in bpy.data.materials:
        if not m.node_tree or m.get("performer_id") not in ("aksiniya", "ikhor"):
            continue
        tree = m.node_tree
        for side, factor in (("left", 1.70), ("right", 1.60)):
            node = tree.nodes.get(
                "Portrait relight | rimink | " + side + " HDR gain only"
            )
            if node:
                old = node.inputs[1].default_value
                assert not node.inputs[1].is_linked
                node.inputs[1].default_value *= factor
                changes.append(
                    {
                        "material": m.name,
                        "node": node.name,
                        "before": old,
                        "after": node.inputs[1].default_value,
                    }
                )
        node = tree.nodes.get("Character layers | hair highlight strength")
        if node:
            old = node.outputs[0].default_value
            node.outputs[0].default_value *= 1.65
            changes.append(
                {
                    "material": m.name,
                    "node": node.name,
                    "before": old,
                    "after": node.outputs[0].default_value,
                }
            )
        # Scale the already selected final Ikhor hair parameter, retaining its existing bypass graph.
        node = tree.nodes.get(
            "Clean Ikhor | hair highlight strength reversible parameter"
        )
        if node:
            destinations = [link.to_socket for link in list(node.outputs[0].links)]
            gain = tree.nodes.new("ShaderNodeMath")
            gain.name = gain.label = "Goo rim glow | retained hair highlight gain"
            gain.operation = "MULTIPLY"
            gain.inputs[1].default_value = 1.65
            tree.links.new(node.outputs[0], gain.inputs[0])
            for destination in destinations:
                tree.links.new(gain.outputs[0], destination)
            changes.append(
                {
                    "material": m.name,
                    "node": gain.name,
                    "factor": 1.65,
                    "consumers": len(destinations),
                }
            )
    for actor in ("aksiniya", "ikhor"):
        for kind, factor in (("reflection", 1.5), ("rim", 1.4)):
            lamp = scene.objects[f"Reference duet | {actor} | {kind}"].data
            assert lamp.diffuse_factor == 0
            old = lamp.energy
            lamp.energy *= factor
            changes.append(
                {
                    "light": f"{actor} {kind}",
                    "before": old,
                    "after": lamp.energy,
                    "diffuse_factor": lamp.diffuse_factor,
                }
            )
    tree = scene.compositing_node_group
    glow_settings = {
        "眩光": (0.12, 1.05, 0.042),
        "Stage art | protected rim halation": (0.50, 0.05, 0.029),
        "Wedding | stage halo": (0.16, 1.05, 0.046),
        "Wedding | actor halo": (0.24, 0.08, 0.034),
        "Bold wedding | actor selective halo": (0.16, 0.75, 0.022),
        "Bold wedding | fx selective halo": (0.16, 1.10, 0.031),
    }
    for name, values in glow_settings.items():
        node = tree.nodes[name]
        old = {
            key: node.inputs[key].default_value
            for key in ("Strength", "Threshold", "Size")
        }
        for key, value in zip(("Strength", "Threshold", "Size"), values):
            assert not node.inputs[key].is_linked
            node.inputs[key].default_value = value
        changes.append(
            {
                "glare": name,
                "before": old,
                "after": dict(zip(("Strength", "Threshold", "Size"), values)),
            }
        )
    # The caption beauty cache must consume the same final glow result.
    beauty = tree.nodes["Caption cache | beauty"]
    composite = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    assert beauty.inputs[0].is_linked
    cache_source = beauty.inputs[0].links[0].from_socket
    final_sources = [
        i.links[0].from_socket
        for i in composite.inputs
        if i.is_linked and i.name == "Image"
    ]
    assert final_sources and cache_source == final_sources[0], (
        "Caption cache and final look diverged"
    )
    after = capture()
    preserved = {
        key: before[key] == after[key]
        for key in (
            "objects",
            "actions",
            "geometry",
            "images",
            "samples",
            "engine",
            "fps",
        )
    }
    assert all(preserved.values()), preserved
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 24
    scene.render.use_motion_blur = False
    scene.render.use_sequencer = False
    scene.frame_set(4290)
    scene["goo_rim_glow_revision"] = (
        "v1: stronger directional HDR rims, retained hair bands and specular lighting; selective + scene glow"
    )
    project = production / "Franken_Duet_Goo_Rim_Glow.blend"
    scene.render.filepath = str(production / "complete-4290.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "source": str(SOURCE),
        "source_sha256": SHA,
        "project": str(project),
        "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
        "changes": changes,
        "preserved": preserved,
        "beauty_cache_matches_final": True,
        "physics_resimulated": False,
        "art_status": "pending user review",
    }
    (production / "preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for frame in (4140, 4290):
        render_control(scene, controls / f"after-{frame}.png", frame)
    print("GOO_RIM_GLOW_PREPARED", project, flush=True)


if __name__ == "__main__":
    main()
