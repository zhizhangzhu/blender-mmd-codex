"""Read-only native audit of a source and rebuilt character-layer master.

Run with Blender --background --disable-autoexec --python this_script --
--source original.blend --current rebuilt.blend --profile preset.json
--output new-report.json. No render, source save, or preference mutation occurs.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_character_layers import PREFIX, role
from verify_duet_integration import snapshot

FRAMES = [1, 2100, 4140, 4200, 4250, 4290, 4439, 8400, 11899]


def connection(socket):
    return [[link.from_node.name, link.from_socket.name] for link in socket.links]


def upstream(socket):
    seen = set()

    def visit(node):
        if node.name in seen:
            return
        seen.add(node.name)
        for item in node.inputs:
            for link in item.links:
                visit(link.from_node)

    for link in socket.links:
        visit(link.from_node)
    return seen


def group_signature(group, seen=None):
    """Compare the complete retained MMD composition graph, including values."""
    seen = set() if seen is None else seen
    if group.name in seen:
        return group.name
    seen.add(group.name)
    nodes = []
    for node in group.nodes:
        values = []
        for socket in node.inputs:
            value = getattr(socket, "default_value", None)
            if value is not None and not isinstance(value, (str, float, int, bool)):
                try:
                    value = list(value)
                except TypeError:
                    value = str(value)
            values.append([socket.identifier, value, connection(socket)])
        nodes.append(
            {
                "name": node.name,
                "type": node.bl_idname,
                "operation": getattr(node, "operation", None),
                "blend": getattr(node, "blend_type", None),
                "values": values,
                "image": node.image.name
                if node.type == "TEX_IMAGE" and node.image
                else None,
                "group": group_signature(node.node_tree, seen)
                if node.type == "GROUP" and node.node_tree
                else None,
            }
        )
    return hashlib.sha256(json.dumps(nodes, sort_keys=True).encode()).hexdigest()


def shader_closure(tree):
    output = next(
        (
            node
            for node in tree.nodes
            if node.type == "OUTPUT_MATERIAL" and node.is_active_output
        ),
        None,
    )
    seen, records = set(), []

    def visit(node):
        if node.name in seen:
            return
        seen.add(node.name)
        links = []
        for socket in node.inputs:
            if socket.type == "SHADER":
                links.append([socket.name, connection(socket)])
                for link in socket.links:
                    visit(link.from_node)
        record = {"name": node.name, "type": node.type, "shader_links": links}
        if node.type == "MIX_SHADER":
            record["factor_source"] = connection(node.inputs[0])
        records.append(record)

    if output:
        visit(output)
    return sorted(records, key=lambda item: item["name"])


def capture():
    scene = bpy.context.scene
    states = {}
    for frame in FRAMES:
        scene.frame_set(frame)
        states[str(frame)] = snapshot(scene)
    materials = {}
    groups = {}
    for material in bpy.data.materials:
        if not material.get("performer_id") or not material.node_tree:
            continue
        tree = material.node_tree
        source = tree.nodes.get("mmd_shader")
        emission = tree.nodes.get(
            "Aether v2 | controlled toon surface"
        ) or tree.nodes.get("Look v3 | NPR surface")
        if not source or not emission:
            continue
        if source.node_tree.name not in groups:
            groups[source.node_tree.name] = group_signature(source.node_tree)
        ramp = tree.nodes.get("Aether v2 | material light response") or tree.nodes.get(
            "Look v3 | Soft toon bands"
        )
        materials[material.name] = {
            "actor": material.get("performer_id"),
            "role": role(material),
            "group": source.node_tree.name,
            "mmd_inputs": [
                [socket.identifier, connection(socket)] for socket in source.inputs
            ],
            "alpha_links": sorted(
                [link.to_node.name, link.to_socket.name]
                for link in source.outputs["Alpha"].links
            ),
            "closure": shader_closure(tree),
            "emission_color": connection(emission.inputs["Color"]),
            "old_sdf_signal": connection(ramp.inputs[0]) if ramp else [],
            "crease_nodes": [
                node.name
                for node in tree.nodes
                if node.name
                in {"Face ink | Mouth crease", "Aether v2 | Aether mouth crease"}
            ],
            "pbr": {
                node.name: {
                    "base_color": connection(node.inputs["Base Color"]),
                    "alpha": connection(node.inputs["Alpha"]),
                }
                for node in tree.nodes
                if node.type == "BSDF_PRINCIPLED"
            },
        }
    images = {
        image.name: {
            "packed": bool(image.packed_file),
            "size": list(image.size),
            "colorspace": image.colorspace_settings.name,
        }
        for image in bpy.data.images
        if image.source == "FILE"
    }
    return {
        "filepath": bpy.data.filepath,
        "states": states,
        "materials": materials,
        "mmd_groups": groups,
        "images": images,
        "color": {
            key: getattr(scene.view_settings, key)
            for key in ("view_transform", "look", "exposure", "gamma")
        },
        "render": {
            "engine": scene.render.engine,
            "fps": scene.render.fps,
            "fps_base": scene.render.fps_base,
            "resolution": [
                scene.render.resolution_x,
                scene.render.resolution_y,
                scene.render.resolution_percentage,
            ],
            "frame_range": [scene.frame_start, scene.frame_end],
        },
        "runtime_physics": scene.rigidbody_world is not None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.output.exists():
        raise FileExistsError(args.output)
    spec = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    bpy.ops.wm.open_mainfile(filepath=str(args.source))
    source = capture()
    bpy.ops.wm.open_mainfile(filepath=str(args.current))
    current = capture()
    checks = []

    def check(name, passed, details=None):
        checks.append({"name": name, "passed": bool(passed), "details": details})

    check(
        "same_material_identities",
        set(source["materials"]) == set(current["materials"]),
        len(current["materials"]),
    )
    check(
        "retained_MMD_composition_groups",
        source["mmd_groups"] == current["mmd_groups"],
        current["mmd_groups"],
    )
    check(
        "retained_file_images",
        source["images"] == current["images"],
        len(current["images"]),
    )
    check(
        "all_file_images_packed",
        all(image["packed"] for image in current["images"].values()),
    )
    check(
        "color_management_preserved",
        source["color"] == current["color"],
        current["color"],
    )
    check(
        "render_contract_preserved",
        source["render"] == current["render"],
        current["render"],
    )
    check("no_runtime_physics", not current["runtime_physics"])
    pose_checks = []
    for frame, expected in source["states"].items():
        actual = current["states"][frame]
        pose_error = max(
            abs(value - actual["actors"][actor][bone][index])
            for actor, bones in expected["actors"].items()
            for bone, values in bones.items()
            for index, value in enumerate(values)
        )
        camera_error = max(
            abs(a - b)
            for a, b in zip(expected["camera_matrix"], actual["camera_matrix"])
        )
        lens_error = abs(expected["lens"] - actual["lens"])
        pose_checks.append(
            {
                "frame": int(frame),
                "pose_error": pose_error,
                "camera_error": camera_error,
                "lens_error": lens_error,
            }
        )
    check(
        "sampled_action_and_camera_preserved",
        all(
            max(item["pose_error"], item["camera_error"], item["lens_error"]) < 0.00001
            for item in pose_checks
        ),
        pose_checks,
    )
    records = []
    forbidden = {
        "Quality | preserve chroma with scalar shading",
        "Quality | short-range contact",
        "Aether v2 | material light response",
        "Aether v2 | local face and joint definition",
        "Look v3 | Soft toon bands",
        "Surface | hair base separation",
        "Genshin study | supplied hair MatCap",
    }
    for name, old in source["materials"].items():
        if name not in current["materials"]:
            continue
        new = current["materials"][name]
        material = bpy.data.materials[name]
        tree = material.node_tree
        surface = tree.nodes.get(
            "Aether v2 | controlled toon surface"
        ) or tree.nodes.get("Look v3 | NPR surface")
        active = upstream(surface.inputs["Color"])
        check(
            name + ": alpha consumer connections",
            old["alpha_links"] == new["alpha_links"],
            new["alpha_links"],
        )
        check(
            name + ": original PMX texture/sphere wiring",
            old["mmd_inputs"] == new["mmd_inputs"],
        )
        check(name + ": final shader closure", old["closure"] == new["closure"])
        check(name + ": PBR base color and alpha", old["pbr"] == new["pbr"])
        if new["role"] == "features":
            check(
                name + ": feature emission retained",
                old["emission_color"] == new["emission_color"],
            )
        else:
            check(
                name + ": no legacy lighting/AO/highlight chain in primary color",
                not (active & forbidden),
                sorted(active & forbidden),
            )
            for suffix, node_type in [
                ("single material palette", "VALTORGB"),
                ("single contact AO", "AMBIENT_OCCLUSION"),
            ]:
                count = sum(
                    node_name.startswith(PREFIX + suffix)
                    and tree.nodes[node_name].type == node_type
                    for node_name in active
                )
                check(name + ": exactly one " + suffix, count == 1, count)
            highlight_expected = new["role"] == "hair" and not name.split(".")[
                0
            ].endswith("+")
            highlight_count = sum(
                node_name.startswith(PREFIX + "one directional hair highlight")
                for node_name in active
            )
            check(
                name + ": directional highlight count",
                highlight_count == int(highlight_expected),
                highlight_count,
            )
            chroma = tree.nodes.get(PREFIX + "source color and chroma")
            check(
                name + ": retained MMD Color source",
                bool(chroma)
                and connection(chroma.inputs["Color"]) == [["mmd_shader", "Color"]],
            )
            response = tree.nodes.get(PREFIX + "illumination calibration")
            check(
                name + ": fixed calibration",
                bool(response)
                and abs(
                    response.inputs["From Min"].default_value
                    - spec["illumination"]["low"]
                )
                < 0.00001
                and abs(
                    response.inputs["From Max"].default_value
                    - spec["illumination"]["high"]
                )
                < 0.00001,
            )
            for crease in old["crease_nodes"]:
                check(name + ": preserved " + crease, crease in active)
            if new["role"] == "face" and tree.nodes.get(
                "Genshin study | SDF face factor"
            ):
                merged = tree.nodes.get(PREFIX + "SDF and native light combined once")
                check(
                    name + ": same SDF before single palette",
                    bool(merged)
                    and connection(merged.inputs[1]) == old["old_sdf_signal"],
                    connection(merged.inputs[1]) if merged else None,
                )
                diffuse = tree.nodes.get(PREFIX + "native diffuse response")
                check(
                    name + ": posed planar face probe",
                    diffuse.inputs["Normal"].is_linked,
                )
        records.append(
            {
                "material": name,
                "actor": new["actor"],
                "role": new["role"],
                "emission_upstream": sorted(active),
                "pbr_names": sorted(new["pbr"]),
            }
        )
    light_records = []
    for obj in bpy.context.scene.objects:
        if obj.type != "LIGHT" or obj.hide_render:
            continue
        collection = obj.light_linking.receiver_collection
        receivers = list(collection.all_objects) if collection else []
        actors = sorted(
            {item.get("performer_id") for item in receivers if item.get("performer_id")}
        )
        reference = obj.name.startswith("Reference duet |")
        if reference:
            key = obj.name.rsplit(" | ", 1)[-1]
            check(
                obj.name + ": actor-only receiver budget",
                len(actors) == 1
                and bool(receivers)
                and all(item.get("performer_id") for item in receivers),
                actors,
            )
            check(
                obj.name + ": expected energy",
                abs(obj.data.energy - spec["lighting"][key + "_watts"]) < 0.00001,
                obj.data.energy,
            )
        else:
            check(
                obj.name + ": stage-only receivers",
                collection is not None and not actors,
                actors,
            )
        light_records.append(
            {
                "name": obj.name,
                "reference_actor_light": reference,
                "energy": obj.data.energy,
                "receiver_collection": collection.name if collection else None,
                "actors": actors,
            }
        )
    file_outputs = []
    for scene in bpy.data.scenes:
        if scene.compositing_node_group:
            file_outputs.extend(
                {"scene": scene.name, "node": node.name, "muted": node.mute}
                for node in scene.compositing_node_group.nodes
                if node.type == "OUTPUT_FILE"
            )
    check(
        "inherited_File_Outputs_muted",
        all(item["muted"] for item in file_outputs),
        file_outputs,
    )
    report = {
        "source": str(args.source),
        "current": str(args.current),
        "profile": spec["id"],
        "read_only": True,
        "rendered": False,
        "saved_source": False,
        "source_summary": {
            key: value
            for key, value in source.items()
            if key not in {"states", "materials", "images"}
        },
        "current_summary": {
            key: value
            for key, value in current.items()
            if key not in {"states", "materials", "images"}
        },
        "checks": checks,
        "materials": records,
        "lights": light_records,
        "warnings": [
            "MMD Color is retained PMX composition, not certified raw game albedo.",
            "Diffuse probe is combined illumination, not an isolated shadow pass.",
            "PBR and eye/ink feature closures remain distinct from the new primary NPR palette.",
            "Pose/camera verification samples nine frames; visual checks and render decoding are separate gates.",
        ],
        "passed": all(item["passed"] for item in checks),
        "failed_checks": [item for item in checks if not item["passed"]],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "CHARACTER_MASTER_VERIFIED",
        json.dumps(
            {
                "passed": report["passed"],
                "checks": len(checks),
                "failures": report["failed_checks"],
                "report": str(args.output),
            },
            ensure_ascii=True,
        ),
        flush=True,
    )
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
