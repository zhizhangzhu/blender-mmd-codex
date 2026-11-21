"""Independently reopen and audit the bounded reference transfer; never render/save.

Run in Blender: --background --disable-autoexec --python-exit-code 1
--python this_script -- --source source.blend --current new.blend
--profile preset.json --output new-report.json.
"""

import argparse
import hashlib
import json
import math
import sys
import traceback
from array import array
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_character_layer_master import capture, connection, upstream

PREFIX = "Reference transfer | "
MATERIAL_PREFIX = "Transfer material | "
SHEEN_INPUTS = {"Sheen Tint", "Sheen Roughness"}
EPSILON = 0.00001


def plain(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)


def socket_record(socket):
    return {
        "default": plain(getattr(socket, "default_value", None)),
        "links": connection(socket),
    }


def near(actual, expected):
    if isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(
            near(a, b) for a, b in zip(actual, expected)
        )
    return (
        math.isfinite(float(actual)) and abs(float(actual) - float(expected)) < EPSILON
    )


def retained_capture():
    print("REFERENCE_AUDIT_CAPTURE", bpy.data.filepath, "native snapshots", flush=True)
    result = capture()
    result["file_payloads"] = {
        image.name: hashlib.sha256(bytes(image.packed_file.data)).hexdigest()
        if image.packed_file
        else None
        for image in bpy.data.images
        if image.source == "FILE"
    }
    result["extra_materials"] = {}
    for name in result["materials"]:
        tree = bpy.data.materials[name].node_tree
        result["extra_materials"][name] = {
            "mmd_inputs": {
                s.identifier: socket_record(s) for s in tree.nodes["mmd_shader"].inputs
            },
            "pbr": {
                n.name: {s.name: socket_record(s) for s in n.inputs}
                for n in tree.nodes
                if n.type == "BSDF_PRINCIPLED"
            },
            "other_closures": {
                n.name: {s.identifier: socket_record(s) for s in n.inputs}
                for n in tree.nodes
                if n.type
                in {
                    "MIX_SHADER",
                    "ADD_SHADER",
                    "BSDF_TRANSPARENT",
                    "BSDF_GLOSSY",
                    "BSDF_GLASS",
                }
            },
            "palette_source": connection(
                tree.nodes["Character layers | base times one palette"].inputs[2]
            )
            if tree.nodes.get("Character layers | base times one palette")
            else None,
            "sdf_source": connection(
                tree.nodes[
                    "Character layers | SDF and native light combined once"
                ].inputs[1]
            )
            if tree.nodes.get("Character layers | SDF and native light combined once")
            else None,
        }
    # Action curves include interpolation and handles, beyond the nine pose samples.
    actions = {}
    for action in bpy.data.actions:
        curves = list(getattr(action, "fcurves", ()))
        for layer in getattr(action, "layers", ()):
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", ()):
                    curves.extend(bag.fcurves)
        digest = hashlib.sha256()
        for curve in curves:
            digest.update(
                json.dumps(
                    {
                        "path": curve.data_path,
                        "index": curve.array_index,
                        "extrapolation": curve.extrapolation,
                        "keys": len(curve.keyframe_points),
                        "samples": len(curve.sampled_points),
                    },
                    sort_keys=True,
                ).encode()
            )
            for prop in ("co", "handle_left", "handle_right"):
                values = array("f", [0.0]) * (2 * len(curve.keyframe_points))
                curve.keyframe_points.foreach_get(prop, values)
                digest.update(values.tobytes())
            for prop in ("interpolation", "handle_left_type", "handle_right_type"):
                values = array("i", [0]) * len(curve.keyframe_points)
                curve.keyframe_points.foreach_get(prop, values)
                digest.update(values.tobytes())
            samples = array("f", [0.0]) * (2 * len(curve.sampled_points))
            curve.sampled_points.foreach_get("co", samples)
            digest.update(samples.tobytes())
        actions[action.name] = digest.hexdigest()
        print("REFERENCE_AUDIT_ACTION", action.name, len(curves), flush=True)
    result["actions"] = actions
    print("REFERENCE_AUDIT_CAPTURE_COMPLETE", bpy.data.filepath, flush=True)
    return result


def position_driver_ok(tree, item, target):
    if not item or item.type != "COMBXYZ" or not tree.animation_data:
        return False
    drivers = {curve.data_path: curve.driver for curve in tree.animation_data.drivers}
    for axis, socket in zip("XYZ", item.inputs):
        driver = drivers.get(socket.path_from_id("default_value"))
        if (
            not driver
            or driver.type != "SCRIPTED"
            or driver.expression != "p"
            or len(driver.variables) != 1
        ):
            return False
        variable = driver.variables[0]
        endpoint = variable.targets[0]
        if not (
            variable.name == "p"
            and variable.type == "TRANSFORMS"
            and endpoint.id == target
            and endpoint.transform_type == "LOC_" + axis
            and endpoint.transform_space == "WORLD_SPACE"
        ):
            return False
    return True


def linked_from(socket, node, output=None):
    return (
        bool(node)
        and len(socket.links) == 1
        and socket.links[0].from_node == node
        and (output is None or socket.links[0].from_socket.name == output)
    )


def first_source(socket):
    return socket.links[0].from_node if len(socket.links) == 1 else None


def stage_grade_audit(scene, spec, check, report):
    """Check the spatial gain algebra and the independent actor exclusion path."""
    aov_name = "TransferStageZone"
    layer_records = []
    for layer in scene.view_layers:
        aov = layer.aovs.get(aov_name)
        passed = aov is not None and aov.type == "VALUE"
        check(layer.name + ": stage_zone_VALUE_AOV", passed)
        layer_records.append({"name": layer.name, "registered": passed})
    stage_materials = []
    for material in bpy.data.materials:
        tree = material.node_tree
        if not tree:
            continue
        aovs = [
            n for n in tree.nodes if n.type == "OUTPUT_AOV" and n.aov_name == aov_name
        ]
        if material.get("performer_id"):
            check(material.name + ": actor_has_no_stage_zone_AOV", not aovs)
            continue
        eligible = any(
            n.type == "OUTPUT_MATERIAL" and n.inputs["Surface"].is_linked
            for n in tree.nodes
        )
        if not eligible:
            continue
        check(material.name + ": exactly_one_stage_zone_AOV", len(aovs) == 1)
        geometry = tree.nodes.get(PREFIX + "grade world position")
        axes = tree.nodes.get(PREFIX + "grade position axes")
        side = tree.nodes.get(PREFIX + "grade sides")
        front = tree.nodes.get(PREFIX + "grade front falloff")
        height = tree.nodes.get(PREFIX + "grade height falloff")
        zone = tree.nodes.get(PREFIX + "foreground and side zone")
        check(
            material.name + ": stage_zone_world_position",
            bool(geometry and axes)
            and geometry.type == "NEW_GEOMETRY"
            and linked_from(axes.inputs[0], geometry, "Position"),
        )
        for label, node, low, high in (
            ("side", side, spec["aisle_half_width"], spec["side_falloff_end"]),
            ("front", front, -4, 0.5),
            ("height", height, 1.5, 3.5),
        ):
            check(
                material.name + ": stage_zone_" + label + "_range",
                bool(node)
                and node.type == "MAP_RANGE"
                and node.clamp
                and node.interpolation_type == "SMOOTHSTEP"
                and near(node.inputs["From Min"].default_value, low)
                and near(node.inputs["From Max"].default_value, high)
                and near(node.inputs["To Min"].default_value, 0)
                and near(node.inputs["To Max"].default_value, 1),
            )
        absolute = first_source(side.inputs["Value"]) if side else None
        check(
            material.name + ": stage_zone_uses_XY_and_height",
            bool(absolute and axes and side and front and height)
            and absolute.type == "MATH"
            and absolute.operation == "ABSOLUTE"
            and linked_from(absolute.inputs[0], axes, "X")
            and linked_from(front.inputs["Value"], axes, "Y")
            and linked_from(height.inputs["Value"], axes, "Z")
            and linked_from(side.inputs["Value"], absolute),
        )
        maximum = first_source(zone.inputs[0]) if zone else None
        below = first_source(zone.inputs[1]) if zone else None
        in_front = first_source(maximum.inputs[1]) if maximum else None
        graph_ok = bool(zone and maximum and below and in_front and aovs)
        if graph_ok:
            graph_ok = (
                zone.type == "MATH"
                and zone.operation == "MULTIPLY"
                and linked_from(aovs[0].inputs["Value"], zone)
                and maximum.type == "MATH"
                and maximum.operation == "MAXIMUM"
                and linked_from(maximum.inputs[0], side)
                and in_front.type == "MATH"
                and in_front.operation == "SUBTRACT"
                and not in_front.inputs[0].is_linked
                and near(in_front.inputs[0].default_value, 1)
                and linked_from(in_front.inputs[1], front)
                and below.type == "MATH"
                and below.operation == "SUBTRACT"
                and not below.inputs[0].is_linked
                and near(below.inputs[0].default_value, 1)
                and linked_from(below.inputs[1], height)
            )
        check(material.name + ": front_OR_sides_limited_by_height", graph_ok)
        stage_materials.append(material.name)
    check("stage_zone_materials_present", bool(stage_materials), len(stage_materials))
    tree = scene.compositing_node_group
    inverse = tree.nodes.get(PREFIX + "protect actor in stage grade") if tree else None
    zone = tree.nodes.get(PREFIX + "stage-only spatial grade") if tree else None
    selected = (
        tree.nodes.get(PREFIX + "foreground hierarchy with actor protection")
        if tree
        else None
    )
    render = first_source(zone.inputs[0]) if zone else None
    actor_exclusion = bool(inverse and zone and render)
    if actor_exclusion:
        actor_exclusion = (
            inverse.type == "MATH"
            and inverse.operation == "SUBTRACT"
            and not inverse.inputs[0].is_linked
            and near(inverse.inputs[0].default_value, 1)
            and render.type == "R_LAYERS"
            and linked_from(inverse.inputs[1], render, "ReferenceDuetActor")
            and zone.type == "MATH"
            and zone.operation == "MULTIPLY"
            and linked_from(zone.inputs[0], render, aov_name)
            and linked_from(zone.inputs[1], inverse)
        )
    check("stage_grade_AOV_multiplied_by_inverse_actor", actor_exclusion)
    darkened = first_source(selected.inputs[2]) if selected else None
    gain_ok = bool(selected and darkened and zone)
    if gain_ok:
        gain_ok = (
            selected.type == "MIX_RGB"
            and selected.blend_type == "MIX"
            and linked_from(selected.inputs[0], zone)
            and darkened.type == "MIX_RGB"
            and darkened.blend_type == "MULTIPLY"
            and not darkened.inputs[0].is_linked
            and near(darkened.inputs[0].default_value, 1)
            and not darkened.inputs[2].is_linked
            and near(
                darkened.inputs[2].default_value, [spec["foreground_gain"]] * 3 + [1]
            )
            and bool(connection(selected.inputs[1]))
            and connection(selected.inputs[1]) == connection(darkened.inputs[1])
        )
    check("stage_grade_uses_configured_local_gain_and_original_bypass", gain_ok)
    final = (
        [
            n
            for n in tree.nodes
            if n.type == "GROUP_OUTPUT" and getattr(n, "is_active_output", True)
        ]
        if tree
        else []
    )
    beauty = tree.nodes.get("Caption cache | beauty") if tree else None
    check(
        "stage_grade_reaches_final_and_caption_beauty",
        len(final) == 1
        and bool(beauty and selected)
        and linked_from(final[0].inputs["Image"], selected)
        and linked_from(beauty.inputs["beauty"], selected),
    )
    report["stage_spatial_grade"] = {
        "aov": aov_name,
        "layers": layer_records,
        "materials": stage_materials,
        "configured_local_gain": spec["foreground_gain"],
        "actor_exclusion_graph_valid": actor_exclusion,
        "rendered_for_this_audit": False,
    }


def audit(source, current, spec, check, report):
    scene = bpy.context.scene
    check(
        "input_revision",
        scene.get("character_layer_revision") == spec["input_revision"],
    )
    check("transfer_revision", scene.get("reference_transfer_revision") == spec["id"])
    shadow_pool = str(getattr(scene.eevee, "shadow_pool_size", "unavailable"))
    check(
        "EEVEE_shadow_pool_matches_profile",
        shadow_pool == str(spec["lighting"]["shadow_pool_mb"]),
        {
            "actual_RNA_value": shadow_pool,
            "expected_MB": spec["lighting"]["shadow_pool_mb"],
        },
    )
    for name in ("materials", "mmd_groups", "color", "render", "actions"):
        first, second = source[name], current[name]
        if name == "materials":
            first, second = sorted(first), sorted(second)
        check("retained_" + name, first == second)
    original_images_retained = all(
        current["images"].get(name) == image for name, image in source["images"].items()
    )
    check(
        "retained_original_file_images", original_images_retained, len(source["images"])
    )
    check(
        "retained_original_packed_payloads",
        all(
            current["file_payloads"].get(name) == value
            for name, value in source["file_payloads"].items()
        ),
    )
    check(
        "all_file_images_packed",
        bool(current["images"])
        and all(image["packed"] for image in current["images"].values()),
    )
    pose_checks = []
    for frame, expected in source["states"].items():
        actual = current["states"].get(frame, {})
        actors = actual.get("actors", {})
        structure = set(actors) == set(expected["actors"]) and all(
            set(actors[a]) == set(bones) for a, bones in expected["actors"].items()
        )
        error = (
            max(
                (
                    abs(value - actors[a][bone][i])
                    for a, bones in expected["actors"].items()
                    for bone, values in bones.items()
                    for i, value in enumerate(values)
                ),
                default=1e100,
            )
            if structure
            else 1e100
        )
        camera_error = max(
            (
                abs(a - b)
                for a, b in zip(
                    expected["camera_matrix"], actual.get("camera_matrix", [])
                )
            ),
            default=1e100,
        )
        lens_error = abs(expected["lens"] - actual.get("lens", 1e100))
        pose_checks.append(
            {
                "frame": int(frame),
                "pose_error": error,
                "camera_error": camera_error,
                "lens_error": lens_error,
            }
        )
    check(
        "nine_sampled_poses_and_camera",
        all(
            max(item["pose_error"], item["camera_error"], item["lens_error"]) < EPSILON
            for item in pose_checks
        ),
        pose_checks,
    )
    check(
        "no_runtime_physics_in_any_scene",
        all(other.rigidbody_world is None for other in bpy.data.scenes),
    )
    material_records = []
    expected_hair = set(spec["materials"]["hair"]["materials"])
    expected_cloth = set(spec["materials"]["cloth"]["materials"])
    changed_hair, changed_cloth = set(), set()
    for name, old in source["materials"].items():
        if name not in current["materials"]:
            continue
        new = current["materials"][name]
        tree = bpy.data.materials[name].node_tree
        actor, kind = new["actor"], new["role"]
        old_extra, new_extra = (
            source["extra_materials"][name],
            current["extra_materials"][name],
        )
        for key in ("mmd_inputs", "alpha_links", "closure", "pbr"):
            check(name + ": retained_" + key, old[key] == new[key])
        check(
            name + ": retained_mmd_values",
            old_extra["mmd_inputs"] == new_extra["mmd_inputs"],
        )
        check(
            name + ": retained_other_closure_values",
            old_extra["other_closures"] == new_extra["other_closures"],
        )
        check(name + ": same_PBR_nodes", set(old_extra["pbr"]) == set(new_extra["pbr"]))
        cloth_selected = (
            actor in spec["materials"]["cloth"].get("actors", [])
            and name in expected_cloth
            and kind == "cloth"
        )
        for node_name, inputs in old_extra["pbr"].items():
            actual = new_extra["pbr"].get(node_name, {})
            for socket_name, old_socket in inputs.items():
                permitted = (
                    cloth_selected
                    and node_name == "Aether v2 | material-specific physical response"
                    and socket_name in SHEEN_INPUTS
                )
                check(
                    name + ": " + node_name + "/" + socket_name + " preserved",
                    permitted or actual.get(socket_name) == old_socket,
                )
        surface = tree.nodes.get(
            "Aether v2 | controlled toon surface"
        ) or tree.nodes.get("Look v3 | NPR surface")
        active = upstream(surface.inputs["Color"])
        material_output = next(
            (
                n
                for n in tree.nodes
                if n.type == "OUTPUT_MATERIAL" and n.is_active_output
            ),
            None,
        )
        all_active = (
            upstream(material_output.inputs["Surface"]) if material_output else set()
        )
        if kind == "features":
            check(
                name + ": features_unchanged",
                old["emission_color"] == new["emission_color"]
                and not any(item.startswith(PREFIX) for item in active),
            )
            continue

        def item(suffix, tree=tree):
            return tree.nodes.get(PREFIX + suffix)

        def linked(socket, other, output=None):
            return (
                bool(other)
                and len(socket.links) == 1
                and socket.links[0].from_node == other
                and (output is None or socket.links[0].from_socket.name == output)
            )

        def control(suffix, prefix=PREFIX, tree=tree, name=name, all_active=all_active):
            result = tree.nodes.get(prefix + suffix)
            check(
                name + ": reachable_switch_" + suffix,
                bool(result)
                and result.type == "VALUE"
                and result.name in all_active
                and near(result.outputs[0].default_value, 1),
            )
            return result

        palette, selected, combined = (
            item("designed two color palette"),
            item("shading bypass"),
            item("form times directional response"),
        )
        check(
            name + ": transfer_material_revision",
            bpy.data.materials[name].get("reference_transfer_revision") == spec["id"],
        )
        for label, n in (
            ("palette", palette),
            ("shading bypass", selected),
            ("form response", combined),
        ):
            check(name + ": active_" + label, bool(n) and n.name in active)
        enabled = control("enable designed shading")
        control("enable artistic emissive rim")
        base = tree.nodes.get("Character layers | base times one palette")
        check(
            name + ": single_palette_application",
            bool(base and selected and palette)
            and selected.blend_type == "MIX"
            and linked(base.inputs[2], selected)
            and linked(selected.inputs[0], enabled)
            and connection(selected.inputs[1]) == old_extra["palette_source"]
            and linked(selected.inputs[2], palette)
            and linked(palette.inputs[0], combined),
        )
        if palette:
            category = "gold_hair" if actor == "aether" and kind == "hair" else kind
            ramp = palette.color_ramp
            positions = spec.get("palette_positions", {}).get(
                kind, [0.30, 0.82 if kind in {"face", "hair"} else 0.70]
            )
            check(
                name + ": configured_palette",
                ramp.interpolation == "EASE"
                and len(ramp.elements) == 2
                and all(
                    near(e.color, rgba)
                    for e, rgba in zip(ramp.elements, spec["palettes"][category])
                )
                and all(
                    near(element.position, value)
                    for element, value in zip(ramp.elements, positions)
                ),
                {
                    "actual_positions": [e.position for e in ramp.elements],
                    "expected_positions": positions,
                },
            )
        geometry, position = item("surface geometry"), item("actual key position")
        delta, normal = item("surface to key"), item("key facing normal")
        probe, rgb, bw, response = (
            item(s)
            for s in (
                "key facing diffuse probe",
                "key facing illumination",
                "key facing luminance",
                "key facing response",
            )
        )
        key = scene.objects.get(f"Reference duet | {actor} | key")
        check(
            name + ": actual_key_position_drivers",
            key is not None and position_driver_ok(tree, position, key),
        )
        check(
            name + ": actual_head_position_drivers",
            position_driver_ok(
                tree,
                item("head position"),
                scene.objects.get(f"Quality | {actor} | head origin"),
            ),
        )
        probe_graph = bool(
            geometry
            and delta
            and normal
            and probe
            and rgb
            and bw
            and response
            and combined
        )
        if probe_graph:
            probe_graph = (
                delta.operation == "SUBTRACT"
                and linked(delta.inputs[0], position)
                and linked(delta.inputs[1], geometry, "Position")
                and normal.operation == "NORMALIZE"
                and linked(normal.inputs[0], delta)
                and probe.type == "BSDF_DIFFUSE"
                and near(probe.inputs["Color"].default_value, [1, 1, 1, 1])
                and linked(probe.inputs["Normal"], normal)
                and linked(rgb.inputs[0], probe)
                and linked(bw.inputs[0], rgb)
                and combined.operation == "MULTIPLY"
                and linked(combined.inputs[1], response)
            )
        check(name + ": key_facing_probe_graph", probe_graph)
        compensated = item("distance compensated illumination")
        check(
            name + ": fixed_calibrated_combined_response",
            bool(response and compensated and bw)
            and linked(response.inputs["Value"], compensated)
            and bw.name in upstream(response.inputs["Value"])
            and response.clamp
            and response.interpolation_type == "SMOOTHSTEP"
            and near(
                response.inputs["From Min"].default_value,
                spec["shadow_response"]["low"],
            )
            and near(
                response.inputs["From Max"].default_value,
                spec["shadow_response"]["high"],
            ),
        )
        if kind == "face" and old_extra["sdf_source"]:
            soft = item("soft face form before occlusion")
            floor = spec["shadow_response"]["face_form_floor"]
            scale = (
                soft.inputs[1].links[0].from_node
                if soft and soft.inputs[1].is_linked
                else None
            )
            check(
                name + ": SDF_softened_before_directional_response",
                bool(soft and scale and combined)
                and soft.operation == "ADD"
                and near(soft.inputs[0].default_value, floor)
                and scale.type == "MATH"
                and scale.operation == "MULTIPLY"
                and connection(scale.inputs[0]) == old_extra["sdf_source"]
                and bool(old_extra["sdf_source"])
                and near(scale.inputs[1].default_value, 1 - floor)
                and linked(combined.inputs[0], soft),
            )
        else:
            check(
                name + ": geometric_form_before_response",
                bool(combined) and linked(combined.inputs[0], item("form bands")),
            )
            if kind == "face":
                check(
                    name + ": no_fabricated_SDF_for_source_overlay",
                    not item("soft face form before occlusion"),
                )
        ao_nodes = [
            tree.nodes[n] for n in active if tree.nodes[n].type == "AMBIENT_OCCLUSION"
        ]
        check(
            name + ": one_contact_AO",
            len(ao_nodes) == 1
            and ao_nodes[0].name == "Character layers | single contact AO"
            and "Character layers | one contact application" in active,
        )
        for suffix in ("AO strength", "enable lighting"):
            n = tree.nodes.get("Character layers | " + suffix)
            check(
                name + ": retained_layer_switch_" + suffix,
                bool(n) and n.type == "VALUE" and n.name in active,
            )
        if name in expected_hair and actor in spec["materials"].get("actors", []):
            for suffix in ("hair permission enable", "hair illumination gate enable"):
                control(suffix, MATERIAL_PREFIX)
            final = tree.nodes.get(MATERIAL_PREFIX + "hair final controlled highlight")
            band = tree.nodes.get("Character layers | one directional hair highlight")
            bound = tree.nodes.get(
                MATERIAL_PREFIX + "hair combined illumination bounded"
            )
            check(
                name + ": illumination_gated_original_hair_band",
                bool(final and band and bound)
                and linked(band.inputs[0], final)
                and linked(bound.inputs["Value"], response)
                and "Character layers | single hair highlight"
                in upstream(band.inputs[0]),
            )
            changed_hair.add(name)
        if cloth_selected:
            control("cloth sheen enable", MATERIAL_PREFIX)
            physical = tree.nodes.get("Aether v2 | material-specific physical response")
            switch = tree.nodes.get(MATERIAL_PREFIX + "cloth sheen enable")
            tint = tree.nodes.get(MATERIAL_PREFIX + "cloth Sheen Tint selector")
            rough = tree.nodes.get(MATERIAL_PREFIX + "cloth Sheen Roughness selector")
            old_pbr = old_extra["pbr"].get(physical.name, {}) if physical else {}
            tint_original = old_pbr.get("Sheen Tint", {})
            tint_ok = (
                bool(physical and switch and tint and rough)
                and linked(physical.inputs["Sheen Tint"], tint)
                and linked(physical.inputs["Sheen Roughness"], rough)
                and linked(tint.inputs[0], switch)
                and tint.blend_type == "MIX"
                and near(
                    tint.inputs[2].default_value,
                    spec["materials"]["cloth"]["sheen_tint"],
                )
            )
            if tint_ok:
                tint_ok = connection(tint.inputs[1]) == tint_original.get("links") and (
                    bool(tint_original.get("links"))
                    or near(tint.inputs[1].default_value, tint_original["default"])
                )
            rough_original = old_pbr.get("Sheen Roughness", {})
            enabled_delta = (
                rough.inputs[1].links[0].from_node
                if rough and rough.inputs[1].is_linked
                else None
            )
            delta = (
                enabled_delta.inputs[1].links[0].from_node
                if enabled_delta and enabled_delta.inputs[1].is_linked
                else None
            )

            def original_rough(socket, rough_original=rough_original):
                return connection(socket) == rough_original.get("links") and (
                    bool(rough_original.get("links"))
                    or near(socket.default_value, rough_original.get("default", -1))
                )

            rough_ok = (
                bool(rough and enabled_delta and delta)
                and rough.operation == "ADD"
                and original_rough(rough.inputs[0])
                and enabled_delta.type == "MATH"
                and enabled_delta.operation == "MULTIPLY"
                and linked(enabled_delta.inputs[0], switch)
                and delta.type == "MATH"
                and delta.operation == "SUBTRACT"
                and near(
                    delta.inputs[0].default_value,
                    spec["materials"]["cloth"]["sheen_roughness"],
                )
                and original_rough(delta.inputs[1])
            )
            check(name + ": cloth_sheen_selectors", tint_ok and rough_ok)
            changed_cloth.add(name)
        material_records.append(
            {
                "material": name,
                "actor": actor,
                "role": kind,
                "source_has_face_SDF": bool(old_extra["sdf_source"]),
                "active_transfer_nodes": sorted(
                    n for n in active if n.startswith((PREFIX, MATERIAL_PREFIX))
                ),
            }
        )
    check(
        "all_selected_hair_controls_present",
        changed_hair == expected_hair,
        sorted(changed_hair),
    )
    check(
        "all_selected_cloth_controls_present",
        changed_cloth == expected_cloth,
        sorted(changed_cloth),
    )
    check(
        "original_face_SDF_materials_present",
        any(
            old["role"] == "face" and source["extra_materials"][name]["sdf_source"]
            for name, old in source["materials"].items()
        ),
    )
    report["materials"] = material_records
    # The authored static light offsets were constructed against the 4200 pose.
    scene.frame_set(4200)
    bpy.context.view_layer.update()
    lights = []
    for actor in ("aksiniya", "aether"):
        key = scene.objects.get(f"Reference duet | {actor} | key")
        for label in ("key", "fill", "rim", "reflection"):
            light = scene.objects.get(f"Reference duet | {actor} | {label}")
            check(
                actor + ": present_light_" + label,
                bool(light) and light.type == "LIGHT" and not light.hide_render,
            )
            if not light:
                continue
            collection = light.light_linking.receiver_collection
            receivers = list(collection.all_objects) if collection else []
            check(
                light.name + ": correct_actor_receivers",
                bool(receivers)
                and all(obj.get("performer_id") == actor for obj in receivers),
            )
            check(
                light.name + ": configured_power",
                near(light.data.energy, spec["lighting"][label + "_watts"]),
            )
            check(light.name + ": casts_shadow", light.data.use_shadow)
            if label != "key":
                check(
                    light.name + ": diffuse_disabled",
                    near(light.data.diffuse_factor, 0),
                )
            else:
                check(
                    light.name + ": key_diffuse_enabled",
                    light.data.diffuse_factor > 0
                    and near(light.data.size, spec["lighting"]["key_size"]),
                )
                head = scene.objects.get(f"Quality | {actor} | head origin")
                offset = (
                    list(light.matrix_world.translation - head.matrix_world.translation)
                    if head
                    else []
                )
                check(
                    light.name + ": authored_4200_key_offset",
                    near(offset, spec["lighting"]["key_offset"]),
                    offset,
                )
            if label == "reflection":
                check(
                    light.name + ": isolated_reflection_shape",
                    light.data.type == "AREA"
                    and light.data.shape == "RECTANGLE"
                    and near(light.data.specular_factor, 1)
                    and near(light.data.volume_factor, 0)
                    and near(light.data.size, spec["lighting"]["reflection_width"])
                    and near(light.data.size_y, spec["lighting"]["reflection_height"])
                    and key is not None
                    and collection == key.light_linking.receiver_collection,
                )
            lights.append(
                {
                    "name": light.name,
                    "energy": light.data.energy,
                    "diffuse": light.data.diffuse_factor,
                    "receivers": len(receivers),
                }
            )
    report["lights"] = lights
    for light in scene.objects:
        if (
            light.type != "LIGHT"
            or light.hide_render
            or light.name.startswith("Reference duet |")
        ):
            continue
        collection = light.light_linking.receiver_collection
        check(
            light.name + ": stage_only_receivers",
            collection is not None
            and all(not obj.get("performer_id") for obj in collection.all_objects),
        )
    stage_controls = []
    for material in bpy.data.materials:
        if material.get("performer_id") or not material.node_tree:
            continue
        tree = material.node_tree
        switch = tree.nodes.get(PREFIX + "enable stage side control")
        if switch:
            surface = tree.nodes.get("Focused light | responsive stage surface")
            active = upstream(surface.inputs["Base Color"]) if surface else set()
            check(
                material.name + ": stage_side_switch_reachable",
                switch.type == "VALUE"
                and near(switch.outputs[0].default_value, 1)
                and switch.name in active
                and PREFIX + "stage side hierarchy" in active,
            )
            stage_controls.append(material.name)
    check("stage_side_controls_present", bool(stage_controls), stage_controls)
    tree = scene.compositing_node_group
    final = (
        [
            n
            for n in tree.nodes
            if n.type == "GROUP_OUTPUT" and getattr(n, "is_active_output", True)
        ]
        if tree
        else []
    )
    beauty = tree.nodes.get("Caption cache | beauty") if tree else None
    check(
        "caption_beauty_matches_final_output",
        len(final) == 1
        and bool(beauty)
        and bool(connection(final[0].inputs["Image"]))
        and connection(final[0].inputs["Image"]) == connection(beauty.inputs["beauty"]),
    )
    stage_grade_audit(scene, spec["stage"], check, report)
    outputs = [
        {"scene": other.name, "node": n.name, "muted": n.mute}
        for other in bpy.data.scenes
        if other.compositing_node_group
        for n in other.compositing_node_group.nodes
        if n.type == "OUTPUT_FILE"
    ]
    check(
        "all_scenes_File_Output_muted",
        bool(outputs) and all(n["muted"] for n in outputs),
        outputs,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "current", "profile", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.output.exists():
        raise FileExistsError(args.output)
    report = {
        "source": str(args.source),
        "current": str(args.current),
        "profile": str(args.profile),
        "read_only": True,
        "rendered": False,
        "project_saved": False,
        "preferences_changed": False,
        "art_status": "pending",
        "user_art_approval": False,
        "checks": [],
        "errors": [],
    }

    def check(name, passed, details=None):
        report["checks"].append(
            {"name": name, "passed": bool(passed), "details": details}
        )

    try:
        spec = json.loads(args.profile.read_text(encoding="utf-8-sig"))
        check(
            "source_sha256_matches_profile",
            hashlib.sha256(args.source.read_bytes()).hexdigest()
            == spec["source_sha256"],
        )
        bpy.ops.wm.open_mainfile(filepath=str(args.source))
        source = retained_capture()
        bpy.ops.wm.open_mainfile(filepath=str(args.current))
        current = retained_capture()
        report["source_summary"] = {
            key: source[key] for key in ("render", "color", "actions", "file_payloads")
        }
        report["current_summary"] = {
            key: current[key] for key in ("render", "color", "actions", "file_payloads")
        }
        audit(source, current, spec, check, report)
        report["profile_id"] = spec["id"]
        report["current_sha256"] = hashlib.sha256(args.current.read_bytes()).hexdigest()
    except Exception as error:  # noqa: BLE001 -- report every native audit failure, then exit nonzero
        report["errors"].append(
            {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            }
        )
    report["failed_checks"] = [item for item in report["checks"] if not item["passed"]]
    report["passed"] = (
        bool(report["checks"]) and not report["errors"] and not report["failed_checks"]
    )
    report["limits"] = [
        "Independent reopening and native graph/data audit; no renders or visual quality approval.",
        "Pose/camera equality samples nine times; action curve signatures also compare keys, handles and interpolation.",
        "Key-facing Diffuse is calibrated combined illumination, not isolated shadow visibility.",
        "Configured EEVEE shadow pool is read from RNA; absence of runtime exhaustion warnings requires separate render logs.",
        "Stage grade checks its spatial/actor-exclusion algebra and final/cache wiring; it does not measure actual AOV coverage or visual quality.",
        "Art remains pending; video decoding, audio, color roundtrip, caption boundaries and visual review are separate gates.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(
        "REFERENCE_TRANSFER_VERIFIED",
        json.dumps(
            {
                "passed": report["passed"],
                "checks": len(report["checks"]),
                "failed_checks": report["failed_checks"],
                "errors": report["errors"],
                "output": str(args.output),
            },
            ensure_ascii=True,
        ),
        flush=True,
    )
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
