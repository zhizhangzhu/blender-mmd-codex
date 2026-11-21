"""Refine native hull ink and connect readable geometric self-shadow to NPR."""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrate_light_space import world_vector
from verify_duet_integration import snapshot


def category(mat):
    name = mat.get("source_mmd_material_name", mat.name).split(".")[0]
    kind = mat.get("aether_surface", mat.get("look_category", ""))
    if any(w in name for w in ("眉", "睫", "目", "口", "舌", "齿", "二重")):
        return "features"
    if name in {"颜", "颜+", "面1", "面2"} or kind == "face":
        return "face"
    if name == "肌" or kind == "skin":
        return "skin"
    if any(w in name for w in ("发", "鬓", "呆毛")) or kind == "hair":
        return "hair"
    if kind in {"cloth", "leather"}:
        return "cloth"
    if kind in {"trim", "gold", "metal"}:
        return "trim"
    if kind == "fur":
        return "fur"
    return "other"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    config = json.loads(args.preset.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    source = bpy.data.filepath
    assert scene.get("grounded_shadow_revision") and not scene.get(
        "graphic_self_shadow_revision"
    )
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for n in other.compositing_node_group.nodes:
                if n.type == "OUTPUT_FILE":
                    n.mute = True
    expected = {}
    for number in (1, 2100, 4140, 4200, 4250, 4262, 4290, 4439, 8400, 11899):
        scene.frame_set(number)
        expected[number] = snapshot(scene)
    hulls = []
    for obj in scene.objects:
        if obj.type != "MESH" or not obj.get("performer_id"):
            continue
        group = obj.vertex_groups.get("mmd_edge_preview")
        if not group or not obj.modifiers.get("mmd_edge_preview"):
            continue
        baseline = [
            next((g.weight for g in v.groups if g.group == group.index), 0)
            for v in obj.data.vertices
        ]
        obj["graphic_ink_source_weights"] = baseline
        scales = {}
        for poly in obj.data.polygons:
            mat = obj.data.materials[poly.material_index]
            if not mat:
                continue
            factor = config["width_relative_to_grounded_v1"][category(mat)]
            for index in poly.vertices:
                scales[index] = min(scales.get(index, factor), factor)
        changed = 0
        clipped = 0
        for index, factor in scales.items():
            before = baseline[index]
            after = min(1, before * factor)
            group.add([index], after, "REPLACE")
            changed += after > before + 0.0000001
            clipped += before * factor > 1
        hulls.append(
            {
                "mesh": obj.name,
                "thickness": obj.modifiers["mmd_edge_preview"].thickness,
                "changed_vertices": changed,
                "clamped_vertices": clipped,
            }
        )
    assert len(hulls) == 2
    responses = []
    for mat in bpy.data.materials:
        if not mat.node_tree or not mat.get("performer_id"):
            continue
        cat = category(mat)
        if cat != "features" and mat.mmd_material.enabled_toon_edge:
            mat.mmd_material.edge_color = (
                *config["ink_color"],
                0.9 if cat == "fur" else 1,
            )
        response = mat.node_tree.nodes.get("Quality | bounded real illumination")
        if not response or cat == "features":
            continue
        if cat == "face":
            actor = mat["performer_id"]
            forward = scene.objects[f"Quality | {actor} | head forward"]
            origin = scene.objects[f"Quality | {actor} | head origin"]
            normal = world_vector(
                mat.node_tree,
                forward,
                origin,
                "Graphic shadow | posed planar face normal",
            )
            mat.node_tree.links.new(
                normal,
                mat.node_tree.nodes["Quality | white diffuse lighting probe"].inputs[
                    "Normal"
                ],
            )
        key = (
            "face_floor"
            if cat == "face"
            else "skin_body_floor"
            if cat == "skin"
            else "hair_floor"
            if cat == "hair"
            else "body_floor"
        )
        for socket in response.inputs:
            if socket.type != "VALUE":
                continue
            if socket.name == "From Min":
                socket.default_value = config["physical_response"]["low"]
            elif socket.name == "From Max":
                socket.default_value = config["physical_response"]["high"]
            elif socket.name == "To Min":
                socket.default_value = config["physical_response"][key]
        responses.append(
            {
                "material": mat.name,
                "category": cat,
                "floor": config["physical_response"][key],
            }
        )
    lights = []
    for actor in ("aksiniya", "aether"):
        key = scene.objects[f"Reference duet | {actor} | key"]
        key.data.size = config["actor_key_size"]
        lights.append(key.name)
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = 100

    def render(number, name):
        scene.frame_set(number)
        scene.render.filepath = str(args.output_dir / name)
        bpy.ops.render.render(write_still=True)

    for number in (4200, 4250, 4290):
        render(number, f"grounded-{number}.png")
    shadow_states = [
        (o.data, o.data.use_shadow) for o in scene.objects if o.type == "LIGHT"
    ]
    for data, _ in shadow_states:
        data.use_shadow = False
    render(4290, "control-self-cast-off-4290.png")
    for data, value in shadow_states:
        data.use_shadow = value
    key = scene.objects["Stage art | grounded backlight"]
    key.data.use_shadow = False
    render(4250, "control-key-shadow-off-4250.png")
    key.data.use_shadow = True
    contact = []
    for mat in bpy.data.materials:
        if mat.node_tree:
            node = mat.node_tree.nodes.get("Grounding | contact amount")
            if node:
                contact.append((node, node.inputs[1].default_value))
                node.inputs[1].default_value = 0
    render(4250, "control-contact-off-4250.png")
    for node, value in contact:
        node.inputs[1].default_value = value
    for obj in scene.objects:
        if obj.type == "MESH" and "graphic_ink_source_weights" in obj:
            group = obj.vertex_groups["mmd_edge_preview"]
            current = [
                next((g.weight for g in v.groups if g.group == group.index), 0)
                for v in obj.data.vertices
            ]
            obj["graphic_ink_final_weights"] = current
            for i, value in enumerate(obj["graphic_ink_source_weights"]):
                group.add([i], value, "REPLACE")
    render(4290, "control-previous-ink-4290.png")
    for obj in scene.objects:
        if obj.type == "MESH" and "graphic_ink_final_weights" in obj:
            group = obj.vertex_groups["mmd_edge_preview"]
            for i, value in enumerate(obj["graphic_ink_final_weights"]):
                group.add([i], value, "REPLACE")
    for number, state in expected.items():
        scene.frame_set(number)
        assert snapshot(scene) == state, number
    scene.frame_set(4140)
    scene["graphic_self_shadow_revision"] = config["id"]
    bpy.ops.file.pack_all()
    target = args.output_dir / "Franken_Duet_Grounded_Wedding.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    report = {
        "source": source,
        "target": str(target),
        "preset": config,
        "hulls": hulls,
        "responses": responses,
        "actor_keys": lights,
        "pose_camera_lens_unchanged_frames": list(expected),
        "self_cast_control": "All light shadow casting disabled; form lighting and SDF retained. Stage changes also occur; inspect actor crops.",
        "ink_control": "Previous vertex width weights restored; revised darker ink color retained",
        "passed": True,
    }
    (args.output_dir / "graphic-self-shadow-preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("GRAPHIC_SELF_SHADOW_MASTER_READY", flush=True)


if __name__ == "__main__":
    main()
