"""Read current shadow routing and render isolated glare/highlight/toplight controls."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

SOURCE = Path(
    "D:/codex/output/MMD-Goo-Window-Wrap-v1/production-v3/Franken_Duet_Goo_Window_Wrap.blend"
)
SHA = "ed81e7325e7ef3f47fe80dd63b53e1e0e713f7d2b93b9dd4e6e296195a350d85"
ROOT = Path("D:/codex/output/MMD-Hair-Shadow-Toplight-Study-v1")


def destinations(socket):
    pending = [link.to_node for link in socket.links]
    visited, names = set(), []
    while pending:
        item = pending.pop()
        if item.as_pointer() in visited:
            continue
        visited.add(item.as_pointer())
        names.append(item.name)
        pending.extend(link.to_node for out in item.outputs for link in out.links)
    return names


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA
    ROOT.mkdir(parents=True, exist_ok=False)
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    assert abs(scene.camera.data.lens - 61.734649658203125) < 0.0001
    report = {
        "source": str(SOURCE),
        "source_sha256": SHA,
        "frame": 4290,
        "materials": {},
        "cases": [],
        "production_modified": False,
    }
    for name in ("前鬓", "鬓.001", "颜", "颜.001", "衣", "衣.001"):
        mat = bpy.data.materials[name]
        tree = mat.node_tree
        entry = {
            "check_shadow_id": mat.check_shadow_id,
            "native_shadow_routes": [],
            "shadow_and_palette_nodes": [],
        }
        for item in tree.nodes:
            if item.bl_idname == "ShaderNodeShaderInfo":
                entry["native_shadow_routes"].append(
                    {
                        "name": item.name,
                        "groups": [group.name for group in item.light_groups.groups],
                        "uses_own_groups": item.use_own_light_groups,
                        "cast_downstream": destinations(item.outputs["Cast Shadows"]),
                        "self_linked": item.outputs["Self Shadows"].is_linked,
                    }
                )
            if any(
                word in item.name.lower()
                for word in ("shade", "shadow", "occlusion", "palette", "response")
            ) and item.type in ("MAP_RANGE", "VALTORGB", "MATH"):
                params = [
                    {
                        "index": index,
                        "name": socket.name,
                        "linked": socket.is_linked,
                        "source": socket.links[0].from_node.name
                        if socket.is_linked
                        else None,
                        "value": socket.default_value
                        if isinstance(
                            getattr(socket, "default_value", None), (float, int, bool)
                        )
                        else None,
                    }
                    for index, socket in enumerate(item.inputs)
                ]
                row = {"name": item.name, "type": item.bl_idname, "inputs": params}
                if item.type == "VALTORGB":
                    row["ramp"] = [
                        {"position": e.position, "color": list(e.color)}
                        for e in item.color_ramp.elements
                    ]
                entry["shadow_and_palette_nodes"].append(row)
        report["materials"][name] = entry
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 24
    scene.render.use_motion_blur = False
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.quality = 95
    saved = []

    def change(socket, value):
        saved.append((socket, socket.default_value))
        socket.default_value = value

    def render(label, description):
        scene.render.filepath = str(ROOT / (label + ".jpg"))
        bpy.ops.render.render(write_still=True)
        report["cases"].append(
            {"label": label, "description": description, "image": scene.render.filepath}
        )
        print("HAIR_SHADOW_CONTROL", label, flush=True)

    render("A-current", "Current delivered light/material/compositing settings")
    for tree in bpy.data.node_groups:
        for item in tree.nodes:
            if item.type == "GLARE" and item.inputs.get("Strength"):
                assert not item.inputs["Strength"].is_linked
                change(item.inputs["Strength"], 0)
    render(
        "B-no-glow",
        "Only all Glare Strength=0; hair/rim surface contributions still present",
    )
    for mat in bpy.data.materials:
        if not mat.node_tree or mat.get("performer_id") not in ("aksiniya", "ikhor"):
            continue
        tree = mat.node_tree
        for side in ("left", "right"):
            item = tree.nodes.get(
                "Portrait relight | rimink | " + side + " HDR gain only"
            )
            if item:
                change(item.inputs[1], 0)
        item = tree.nodes.get("Character layers | hair highlight strength")
        if item:
            change(item.outputs[0], 0)
        item = tree.nodes.get("Goo rim glow | retained hair highlight gain")
        if item:
            change(item.inputs[1], 0)
    render(
        "C-base-shading",
        "Glare off, added directional rims and hair band strengths zero; original base form/occlusion/AO retained",
    )
    for socket, value in reversed(saved):
        socket.default_value = value
    data = bpy.data.lights.new("Study only | gentle upper rear", "AREA")
    data.shape, data.size, data.energy = "DISK", 2.5, 180
    data.diffuse_factor, data.specular_factor, data.volume_factor = 0.25, 1, 0
    data.color = (0.95, 0.98, 1)
    data.light_groups.use_default = True
    top = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(top)
    top.location = (0, 0.9, 4.1)
    top.rotation_euler = (
        (Vector((0, 0.4, 1.3)) - top.location).to_track_quat("-Z", "Y").to_euler()
    )
    import goo_engine_light_groups

    goo_engine_light_groups.sync_light_groups()
    bpy.context.view_layer.update()
    render(
        "D-current-plus-top",
        "Current look plus one 180W soft upper-rear Area; default group only, no NPR palette/face-shadow rewiring",
    )
    report["toplight"] = {
        "position": list(top.location),
        "energy": data.energy,
        "size": data.size,
        "diffuse_factor": data.diffuse_factor,
        "specular_factor": data.specular_factor,
        "volume_factor": data.volume_factor,
        "npr_groups_changed": False,
    }
    report["source_unchanged"] = hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA
    report["limits"] = (
        "Single still, no production save or video render. Cast visibility routing is distinct from shape shading and separate Self output. Toplight is physical-light-only and does not automatically replace custom NPR inputs."
    )
    with (ROOT / "diagnosis.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
