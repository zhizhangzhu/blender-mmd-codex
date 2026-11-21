"""Reopen the focused-light master and verify motion and cache isolation."""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_duet_integration import snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--softlight-profile", type=Path)
    parser.add_argument("--wedding-profile", type=Path)
    parser.add_argument("--shadow-profile", type=Path)
    parser.add_argument("--graphic-profile", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    source = bpy.data.filepath
    frames = (1, 2100, 4140, 4200, 4250, 4262, 4290, 4439, 8400, 11899)
    expected = {}
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        expected[frame] = snapshot(bpy.context.scene)
    bpy.ops.wm.open_mainfile(filepath=str(args.target))
    scene = bpy.context.scene
    for frame in frames:
        scene.frame_set(frame)
        assert snapshot(scene) == expected[frame], frame
    assert scene.get("caption_focus_revision") == "hesperides-focused-light-v3"
    assert scene.rigidbody_world is None
    assert [scene.frame_start, scene.frame_end] == [4140, 4439]
    assert scene.render.fps == 60 and scene.render.engine == "BLENDER_EEVEE"
    assert [
        scene.render.resolution_x,
        scene.render.resolution_y,
        scene.render.resolution_percentage,
    ] == [1920, 1080, 100]
    outputs = [
        n
        for s in bpy.data.scenes
        if s.compositing_node_group
        for n in s.compositing_node_group.nodes
        if n.type == "OUTPUT_FILE"
    ]
    assert outputs and all(n.mute for n in outputs)
    caches = [n for n in outputs if n.name.startswith("Caption cache | ")]
    assert len(caches) == 2
    for node in caches:
        assert node.format.file_format == "PNG" and node.format.color_depth == "16"
    actor = next(n for n in caches if n.name.endswith("actor"))
    assert actor.format.color_mode == "BW" and not actor.save_as_render
    matte = [
        n
        for n in scene.compositing_node_group.nodes
        if n.bl_idname == "CompositorNodeCryptomatteV2"
    ]
    assert len(matte) == 1
    assert all(name in matte[0].matte_id for name in ("空_mesh", "阿克西妮娅2_mesh"))
    images = [i for i in bpy.data.images if i.source == "FILE"]
    assert images and all(i.packed_file for i in images)
    lights = [
        o
        for o in scene.objects
        if o.type == "LIGHT"
        and o.name.startswith("Focused light | ")
        and not o.hide_render
    ]
    assert len(lights) == 4
    for light in lights:
        receivers = list(light.light_linking.receiver_collection.objects)
        assert receivers and all(not o.get("performer_id") for o in receivers)
    materials = [
        m
        for m in bpy.data.materials
        if m.use_nodes
        and m.node_tree.nodes.get("Focused light | responsive stage surface")
    ]
    assert len(materials) >= 15
    soft = None
    if args.softlight_profile:
        spec = json.loads(args.softlight_profile.read_text(encoding="utf-8"))
        assert scene.get("soft_top_revision") == spec["id"]
        for item in spec["areas"]:
            light = scene.objects["Softlight | " + item["name"]]
            assert light.type == "LIGHT" and not light.hide_render
            assert light.data.type == "AREA"
            assert abs(light.data.energy - item["watts"]) < 0.001
            assert abs(light.data.size - item["size"]) < 0.001
            assert (
                max(abs(a - b) for a, b in zip(light.location, item["location"]))
                < 0.0001
            )
        excluded = []
        for material in bpy.data.materials:
            if not material.use_nodes or not material.get("performer_id"):
                continue
            name = material.get("source_mmd_material_name", material.name).split(".")[0]
            gain = material.node_tree.nodes.get("Cinema | rim gain")
            if name in {"面1", "面2"} or any(
                k in name
                for k in ("目", "眉", "睫", "口", "舌", "颜", "肌", "二重", "脸")
            ):
                if gain:
                    assert gain.inputs[1].default_value == 0, material.name
                outputs = [
                    n
                    for n in material.node_tree.nodes
                    if n.type == "OUTPUT_AOV" and n.aov_name == "StageArtRim"
                ]
                assert outputs, material.name
                for node in outputs:
                    assert not node.inputs["Color"].is_linked, material.name
                    assert tuple(node.inputs["Color"].default_value)[:3] == (0, 0, 0), (
                        material.name
                    )
                excluded.append(material.name)
        assert len(excluded) >= 10
        soft = {"profile": spec, "facial_materials_excluded": excluded}
    wedding = None
    if args.wedding_profile:
        spec = json.loads(args.wedding_profile.read_text(encoding="utf-8"))
        assert scene.get("wedding_revision") == spec["id"]
        for item in spec["spots"]:
            light = scene.objects["Wedding | " + item["name"]]
            assert (
                light.type == "LIGHT"
                and light.data.type == "SPOT"
                and not light.hide_render
            )
            assert abs(light.data.energy - item["watts"]) < 0.001
            assert abs(light.data.volume_factor - item["volume_factor"]) < 0.001
        air = scene.objects["Wedding | bounded rear scattering"]
        assert not air.hide_render and air.location.y - air.scale.y > 2
        tree = scene.compositing_node_group
        result = (
            next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
            .inputs["Image"]
            .links[0]
            .from_socket
        )
        assert (
            tree.nodes["Caption cache | beauty"].inputs["beauty"].links[0].from_socket
            == result
        )
        for key, label in [("stage_glow", "stage"), ("actor_glow", "actor")]:
            node = tree.nodes["Wedding | " + label + " halo"]
            assert (
                abs(node.inputs["Strength"].default_value - spec[key]["strength"])
                < 0.0001
            )
        accents = [
            o.name for o in scene.objects if o.name.startswith("Wedding | aisle light ")
        ]
        assert len(accents) == 2 * len(spec["aisle_lights"]["ys"])
        wedding = {
            "profile": spec,
            "localized_volume_starts_y": air.location.y - air.scale.y,
            "aisle_lights": len(accents),
            "cache_matches_final_glow_output": True,
        }
    grounding = None
    if args.shadow_profile:
        spec = json.loads(args.shadow_profile.read_text(encoding="utf-8"))
        assert scene.get("grounded_shadow_revision") == spec["id"]
        key = scene.objects["Stage art | grounded backlight"]
        assert key.data.use_shadow and not key.hide_render
        assert key.data.type == "SPOT"
        assert abs(key.data.energy - spec["key"]["watts"]) < 0.001
        assert (
            max(abs(a - b) for a, b in zip(key.location, spec["key"]["location"]))
            < 0.0001
        )
        blockers = list(key.light_linking.blocker_collection.objects)
        assert len(blockers) == 2 and all(o.get("performer_id") for o in blockers)
        contact_materials = []
        for material in materials:
            nodes = material.node_tree.nodes
            ao = nodes["Grounding | physical contact"]
            assert (
                abs(
                    ao.inputs["Distance"].default_value
                    - spec["floor_contact"]["distance"]
                )
                < 0.0001
            )
            assert (
                abs(
                    nodes["Grounding | contact amount"].inputs[1].default_value
                    - spec["floor_contact"]["strength"]
                )
                < 0.0001
            )
            assert (
                abs(
                    nodes["Grounding | near floor"].inputs[1].default_value
                    - spec["floor_contact"]["height_limit"]
                )
                < 0.0001
            )
            assert (
                abs(
                    nodes["Grounding | upward floor"].inputs[1].default_value
                    - spec["floor_contact"]["minimum_normal_z"]
                )
                < 0.0001
            )
            contact_materials.append(material.name)
        responses = []
        for material in bpy.data.materials:
            if not material.node_tree or not material.get("performer_id"):
                continue
            node = material.node_tree.nodes.get("Quality | bounded real illumination")
            if node:
                sockets = {s.name: s for s in node.inputs if s.type == "VALUE"}
                response_spec = spec
                if args.graphic_profile:
                    from prepare_graphic_self_shadows import category

                    if category(material) != "features":
                        response_spec = json.loads(
                            args.graphic_profile.read_text(encoding="utf-8")
                        )
                assert (
                    abs(
                        sockets["From Max"].default_value
                        - response_spec["physical_response"]["high"]
                    )
                    < 0.0001
                ), material.name
                responses.append(material.name)
        assert responses and contact_materials
        grounding = {
            "profile": spec,
            "blockers": [o.name for o in blockers],
            "contact_materials": contact_materials,
            "bounded_actor_materials": responses,
        }
    graphic = None
    if args.graphic_profile:
        spec = json.loads(args.graphic_profile.read_text(encoding="utf-8"))
        assert scene.get("graphic_self_shadow_revision") == spec["id"]
        from prepare_graphic_self_shadows import category

        count = 0
        for mat in bpy.data.materials:
            if not mat.node_tree or not mat.get("performer_id"):
                continue
            response = mat.node_tree.nodes.get("Quality | bounded real illumination")
            if not response or category(mat) == "features":
                continue
            cat = category(mat)
            if cat == "face":
                assert (
                    mat.node_tree.nodes["Quality | white diffuse lighting probe"]
                    .inputs["Normal"]
                    .is_linked
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
            sockets = {s.name: s for s in response.inputs if s.type == "VALUE"}
            assert (
                abs(sockets["To Min"].default_value - spec["physical_response"][key])
                < 0.0001
            )
            assert (
                abs(
                    sockets["From Min"].default_value - spec["physical_response"]["low"]
                )
                < 0.0001
            )
            count += 1
        hulls = []
        for obj in scene.objects:
            if obj.type != "MESH" or "graphic_ink_source_weights" not in obj:
                continue
            group = obj.vertex_groups["mmd_edge_preview"]
            actual = [
                next((g.weight for g in v.groups if g.group == group.index), 0)
                for v in obj.data.vertices
            ]
            assert all(
                abs(a - b) < 0.000001
                for a, b in zip(actual, obj["graphic_ink_final_weights"])
            )
            assert any(
                a > b + 0.000001
                for a, b in zip(actual, obj["graphic_ink_source_weights"])
            )
            hulls.append(obj.name)
        for actor in ("aksiniya", "aether"):
            key = scene.objects[f"Reference duet | {actor} | key"]
            assert abs(key.data.size - spec["actor_key_size"]) < 0.0001
        assert len(hulls) == 2 and count >= 30
        graphic = {
            "profile": spec,
            "hulls": hulls,
            "native_response_materials": count,
            "goo_shadow_socket_remains_disabled": "Native response is used instead",
        }
    report = {
        "source": source,
        "target": str(args.target),
        "motion_samples_exactly_preserved": list(frames),
        "packed_images": len(images),
        "responsive_stage_materials": len(materials),
        "stage_lights": [
            {
                "name": o.name,
                "watts": o.data.energy,
                "color": list(o.data.color),
                "location": list(o.location),
            }
            for o in lights
        ],
        "all_file_outputs_saved_muted": True,
        "cache_png16": True,
        "matte_names": matte[0].matte_id,
        "scope": "Reopened native source; final typography is a separate compositing step",
        "softlight_verification": soft,
        "wedding_verification": wedding,
        "grounding_verification": grounding,
        "graphic_self_shadow_verification": graphic,
        "passed": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print("CAPTION_MASTER_VERIFIED", flush=True)


if __name__ == "__main__":
    main()
