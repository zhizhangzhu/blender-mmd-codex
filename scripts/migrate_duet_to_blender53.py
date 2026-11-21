"""Pinned Goo-to-native5.3 duet migration; audits and static-only conversion."""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_goo_duet_sdf import color, scalar, vector
from finalize_goo_character_lookdev import (
    actor_meshes,
    animation,
    camera_record,
    digest,
    evaluated,
    protected_materials,
    rig_state,
    sha,
)
from inspect_blender53_toon_package import plain, tree_record
from prepare_goo_eye_hair_stage import ACTORS
from refine_goo_character_lookdev import hero_camera, render
from render_portrait_light_controls import mute_file_outputs
from snapshot_goo_scene import capture

SOURCE = Path(
    "D:/codex/output/Goo-Duet-SDF-2026-11-19/final-v1/Franken_Duet_SDF_SourceDOF_Still.blend"
)
SOURCE_SHA = "829f2d88827320c48a19ed76df4dc70af495455e4a660769c2bb53fe461caa69"
AUTHOR = Path(
    "D:/codex/temp/Goo-Face-Shadow-Study-2026-11-18/package53/author-toon.blend"
)
AUTHOR_SHA = "d9696f8f165823e17fb542ce4b157351c657c79e958aefb87fe677d4e71f80fe"
CACHE = Path("D:/codex/temp/Blender53-Duet-Toon-2026-11-19")
ROOT = Path("D:/codex/output/Blender53-Duet-Toon-2026-11-19")
ADDONS = Path("D:/codex/workspace/goo-engine/5.2.1-community/portable/scripts/addons")
PREFIX = "Native53 | "


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def register_native():
    """Register only the verified portable MMD source,never save preferences."""
    import addon_utils

    assert bpy.app.version[:2] == (5, 3)
    configured = Path(os.environ["BLENDER_USER_SCRIPTS"])
    native_addons = configured / "addons"
    if not (native_addons / "mmd_tools").is_dir():
        native_addons = ADDONS
    sys.path.insert(0, str(configured / "modules"))
    sys.path.insert(0, str(native_addons))
    module = addon_utils.enable("mmd_tools", default_set=False, persistent=True)
    assert module and getattr(module, "__addon_enabled__", False)
    assert Path(module.__file__).resolve().is_relative_to(native_addons.resolve())
    return {
        "mmd_tools": module.__file__,
        "other_addons_enabled_by_script": [],
        "preferences_saved": False,
    }


def open_source(runtime):
    assert sha(SOURCE) == SOURCE_SHA
    assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
    if runtime == "goo":
        from goo_runtime import register_addons

        addons = register_addons()
    else:
        addons = register_native()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    mute_file_outputs()
    scene = bpy.context.scene
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    assert abs(scene.camera.data.lens - 61.73465) < 0.01, (
        scene.camera.name,
        scene.camera.data.lens,
    )
    return scene, addons


def tree_owners():
    result = {"Group/" + g.name: g for g in bpy.data.node_groups}
    for kind, owners in (
        ("Material", bpy.data.materials),
        ("World", bpy.data.worlds),
        ("Light", bpy.data.lights),
    ):
        for owner in owners:
            if owner.node_tree:
                result[kind + "/" + owner.name] = owner.node_tree
    for scene in bpy.data.scenes:
        if scene.compositing_node_group:
            result["Compositor/" + scene.name] = scene.compositing_node_group
    return result


def linked_upstream(tree):
    roots = [
        n
        for n in tree.nodes
        if n.type
        in {
            "OUTPUT_MATERIAL",
            "OUTPUT_WORLD",
            "GROUP_OUTPUT",
            "COMPOSITE",
            "OUTPUT_AOV",
        }
    ]
    seen = set()
    while roots:
        node = roots.pop()
        if node.name in seen:
            continue
        seen.add(node.name)
        roots.extend(link.from_node for socket in node.inputs for link in socket.links)
    return sorted(seen)


def audit(runtime):
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f"audit-{runtime}.json"
    assert not dest.exists(), "Keep original audit"
    scene, addons = open_source(runtime)
    snapshot = capture()
    geometry = evaluated(scene)
    np.savez_compressed(CACHE / f"evaluated-{runtime}.npz", **geometry)
    special = (
        "ShaderNodeShaderInfo",
        "ShaderNodeLightInfo",
        "ShaderNodeCurvature",
        "ShaderNodeSdfPrimitive",
        "ShaderNodeSdfOp",
        "ShaderNodeSetDepth",
        "ShaderNodeScreenspaceInfo",
    )
    records = {}
    for label, tree in tree_owners().items():
        detailed = tree_record(tree)
        suspect = [
            n
            for n in detailed["nodes"]
            if n["bl_idname"] in special
            or n["type"] == "UNDEFINED"
            or n["bl_idname"] == "NodeUndefined"
        ]
        records[label] = {
            "kind": tree.bl_idname,
            "node_counts": dict(Counter(n.bl_idname for n in tree.nodes)),
            "nodes": [
                {
                    "name": n["name"],
                    "bl_idname": n["bl_idname"],
                    "group": n["group"],
                    "image": n["image"],
                    "inputs": n["inputs"],
                    "outputs": n["outputs"],
                    "settings": n["settings"],
                }
                for n in detailed["nodes"]
            ],
            "links": detailed["links"],
            "upstream": linked_upstream(tree),
            "suspect_names": [n["name"] for n in suspect],
        }
        if tree.bl_idname == "ShaderNodeTree":
            records[label]["drivers"] = animation(tree)
        for n in suspect:
            obj = tree.nodes[n["name"]]
            for key in ("use_own_light_groups", "light_groups"):
                if hasattr(obj, key):
                    value = getattr(obj, key)
                    n[key] = (
                        {
                            "use_default": value.use_default,
                            "groups": [g.name for g in value.groups],
                        }
                        if key == "light_groups"
                        else value
                    )
            records[label].setdefault("special", []).append(n)
    report = {
        "source": str(SOURCE),
        "source_sha256": SOURCE_SHA,
        "runtime": {
            "version": bpy.app.version_string,
            "build": bpy.app.build_hash.decode(),
            "binary": bpy.app.binary_path,
        },
        "addons": addons,
        "camera": camera_record(scene),
        "snapshot": snapshot,
        "actor_meshes": actor_meshes(scene),
        "rig": rig_state(scene),
        "protected_materials": protected_materials(),
        "trees": records,
        "materials": {
            m.name: {
                "performer": m.get("performer_id"),
                "role": m.get("look_category") or m.get("ikhor_material_role"),
                "shader": m.use_nodes,
                "users": m.users,
            }
            for m in bpy.data.materials
        },
        "lights": [
            {
                "object": o.name,
                "data": o.data.name,
                "type": o.data.type,
                "energy": o.data.energy,
                "color": list(o.data.color),
                "matrix": plain(o.matrix_world),
                "hide_render": o.hide_render,
                "custom": plain(dict(o.data)),
                "groups": plain(o.data.light_groups)
                if hasattr(o.data, "light_groups")
                else None,
            }
            for o in scene.objects
            if o.type == "LIGHT"
        ],
        "images": [
            {
                "name": i.name,
                "packed": bool(i.packed_file),
                "size": list(i.size),
                "path": i.filepath,
                "colorspace": i.colorspace_settings.name,
            }
            for i in bpy.data.images
        ],
        "scene": {
            "engine": scene.render.engine,
            "resolution": [
                scene.render.resolution_x,
                scene.render.resolution_y,
                scene.render.resolution_percentage,
            ],
            "samples": scene.eevee.taa_render_samples,
            "color": [
                scene.display_settings.display_device,
                scene.view_settings.view_transform,
                scene.view_settings.look,
                scene.view_settings.exposure,
                scene.view_settings.gamma,
            ],
        },
        "source_unchanged": sha(SOURCE) == SOURCE_SHA,
    }
    assert report["source_unchanged"]
    write(dest, report)
    print("NATIVE53_DUET_READONLY_AUDIT", runtime, flush=True)


def light_memberships(source_audit):
    result = {}
    for lamp in source_audit["lights"]:
        groups = lamp.get("groups") or {}
        for group in groups.get("groups", []):
            result.setdefault(group["name"], []).append(lamp["object"])
    return result


def native_visibility_group(group_name, members):
    label = PREFIX + "Goo bridge | " + group_name
    if label in bpy.data.node_groups:
        return bpy.data.node_groups[label]
    tree = bpy.data.node_groups.new(label, "ShaderNodeTree")
    for name, kind in (
        ("Diffuse Shading", "NodeSocketColor"),
        ("Cast Shadows", "NodeSocketFloat"),
        ("Self Shadows", "NodeSocketFloat"),
        ("Ambient Lighting", "NodeSocketColor"),
        ("Half-lambert factor", "NodeSocketFloat"),
    ):
        tree.interface.new_socket(name=name, in_out="OUTPUT", socket_type=kind)
    output = tree.nodes.new("NodeGroupOutput")
    tag_name = PREFIX + "bridge member | " + group_name
    for member in members:
        bpy.data.objects[member].data[tag_name] = 1.0
    attr = tree.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "LIGHT"
    attr.attribute_name = tag_name
    shadow = tree.nodes.new("ShaderNodeShadowRaycast")
    shadow.inputs["Softness"].default_value = 1
    evaluate = tree.nodes.new("ShaderNodeLightEvaluation")
    mask = evaluate.outputs["Mask"]
    blocked = scalar(
        tree,
        "MULTIPLY",
        scalar(tree, "SUBTRACT", 1, shadow.outputs["Color"], "blocked light"),
        scalar(tree, "MULTIPLY", attr.outputs["Fac"], mask, "selected valid light"),
        "selected occlusion",
    )
    accumulation = tree.nodes.new("ShaderNodeLightAccumulation")
    tree.links.new(blocked, accumulation.inputs["Diffuse Light"])
    accumulation.inputs["Diffuse Color"].default_value = (1, 1, 1, 1)
    rgb = tree.nodes.new("ShaderNodeShaderToRGB")
    tree.links.new(accumulation.outputs["Shader"], rgb.inputs[0])
    visible = scalar(
        tree,
        "MAXIMUM",
        scalar(
            tree, "SUBTRACT", 1, rgb.outputs["Color"], "one minus selected blockage"
        ),
        0,
        "clamped visible",
    )
    for name in ("Cast Shadows", "Self Shadows"):
        tree.links.new(visible, output.inputs[name])
    geometry = tree.nodes.new("ShaderNodeNewGeometry")
    nol = vector(
        tree,
        "DOT_PRODUCT",
        geometry.outputs["Normal"],
        evaluate.outputs["Direction"],
        "geometry facing selected light",
    )
    half = scalar(
        tree,
        "ADD",
        scalar(tree, "MULTIPLY", nol, 0.5, "half cosine"),
        0.5,
        "half lambert",
    )
    selected = scalar(
        tree,
        "MULTIPLY",
        half,
        scalar(tree, "MULTIPLY", attr.outputs["Fac"], mask, "selected facing light"),
        "selected half lambert",
    )
    facing_accum = tree.nodes.new("ShaderNodeLightAccumulation")
    tree.links.new(selected, facing_accum.inputs["Diffuse Light"])
    facing_accum.inputs["Diffuse Color"].default_value = (1, 1, 1, 1)
    facing_rgb = tree.nodes.new("ShaderNodeShaderToRGB")
    tree.links.new(facing_accum.outputs["Shader"], facing_rgb.inputs[0])
    tree.links.new(facing_rgb.outputs["Color"], output.inputs["Half-lambert factor"])
    tree.links.new(facing_rgb.outputs["Color"], output.inputs["Diffuse Shading"])
    output.inputs["Ambient Lighting"].default_value = (0, 0, 0, 1)
    tree["migration_note"] = (
        "Native53 selected-light total visibility;Cast/Self not separately isolated.Half-Lambert geometry-normal mathematical bridge,not exact Goo renderer implementation"
    )
    return tree


def restore_goo_nodes(source_audit):
    memberships = light_memberships(source_audit)
    report = []
    owners = tree_owners()
    for label, record in source_audit["trees"].items():
        if not record["suspect_names"]:
            continue
        tree = owners[label]
        for old in record.get("special", []):
            assert old["bl_idname"] == "ShaderNodeShaderInfo", old["bl_idname"]
            groups = old.get("light_groups", {}).get("groups", [])
            assert old.get("use_own_light_groups") and len(groups) == 1, (
                label,
                old["name"],
                groups,
            )
            name = groups[0]
            members = memberships[name]
            assert len(members) == 1, (name, members)
            original = tree.nodes[old["name"]]
            original.label = (
                "Unsupported original Goo ShaderInfo;explicit native bridge attached"
            )
            replacement = tree.nodes.new("ShaderNodeGroup")
            replacement.name = PREFIX + "restored | " + old["name"]
            replacement.node_tree = native_visibility_group(name, members)
            restored = []
            for link in record["links"]:
                if link["from"][0] != old["name"]:
                    continue
                destination = tree.nodes[link["to"][0]]
                socket = next(
                    s for s in destination.inputs if s.identifier == link["to"][1]
                )
                tree.links.new(replacement.outputs[link["from"][1]], socket)
                restored.append(link)
            report.append(
                {
                    "tree": label,
                    "old": old["name"],
                    "group": name,
                    "lights": members,
                    "restored_links": restored,
                    "approximation": "Native total shadow substitutes separated Cast/Self;old final min of both collapses to total;no universal equivalence claim",
                }
            )
    return report


def restore_default_light_receivers(source_audit):
    records = []
    for lamp in source_audit["lights"]:
        groups = lamp.get("groups") or {}
        if groups.get("use_default", True):
            continue
        obj = bpy.data.objects[lamp["object"]]
        actor = next((who for who in ACTORS if who in obj.name), None)
        assert actor, (obj.name, groups)
        coll = bpy.data.collections.new(PREFIX + actor + " receiver only")
        coll.objects.link(bpy.data.objects[ACTORS[actor]["mesh"]])
        obj.light_linking.receiver_collection = coll
        records.append(
            {
                "light": obj.name,
                "source_use_default": False,
                "native_receiver": coll.name,
                "objects": [o.name for o in coll.objects],
            }
        )
    return records


def preservation(scene, source_audit):
    state = capture()
    reference = source_audit["snapshot"]
    checks = {
        key: digest(state[key]) == digest(reference[key])
        for key in ("actions", "geometry", "samples", "fps")
    }
    checks["actor_mesh_uv_weights_shapes"] = digest(actor_meshes(scene)) == digest(
        source_audit["actor_meshes"]
    )
    checks["camera_complete_dof_markers"] = (
        camera_record(scene) == source_audit["camera"]
    )
    reference_coords = np.load(CACHE / "evaluated-goo.npz")
    actual = evaluated(scene)
    deltas = {
        key: float(np.max(np.abs(actual[key] - reference_coords[key])))
        for key in actual
    }
    checks["five_pose_coordinates"] = max(deltas.values()) < 1e-7
    return checks, deltas


def baseline(iteration):
    out = ROOT / iteration
    out.mkdir(parents=True, exist_ok=False)
    source_audit = json.loads((CACHE / "audit-goo.json").read_text(encoding="utf-8"))
    scene, addons = open_source("native53")
    checks, deltas = preservation(scene, source_audit)
    assert all(checks.values()), checks
    lights = restore_default_light_receivers(source_audit)
    conversions = restore_goo_nodes(source_audit)
    active = []
    for label, tree in tree_owners().items():
        if not label.startswith(("Material/", "World/", "Compositor/")):
            continue
        upstream = linked_upstream(tree)
        active.extend(
            [label, n.name]
            for n in tree.nodes
            if n.bl_idname == "NodeUndefined" and n.name in upstream
        )
    assert not active, active
    report = {
        "scope": "Native53 technical bridge baseline before author character shader;non-character ground Cast explicitly rebuilt,all other stage materials retained",
        "source": str(SOURCE),
        "source_sha256": SOURCE_SHA,
        "addons": addons,
        "checks": checks,
        "five_pose_coordinate_max_abs": deltas,
        "light_receiver_conversions": lights,
        "goo_node_conversions": conversions,
        "active_undefined_nodes": active,
        "all_undefined_nodes_retained_as_unlinked_originals": sum(
            n.bl_idname == "NodeUndefined"
            for t in tree_owners().values()
            for n in t.nodes
        ),
        "camera_before_actual_render": camera_record(scene),
    }
    import opencc

    report["addons"]["opencc"] = opencc.__file__
    write(out / "baseline-report.json", report)
    render(
        scene, out, "native53-bridge-baseline-duet-4290", scene.camera, (1280, 720), 32
    )
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.eevee.taa_render_samples = 64
    scene.render.filepath = str(out / "native53-bridge-baseline-duet-4290.png")
    project = out / "Franken_Native53_Bridge_Baseline.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report["project"] = str(project)
    report["project_sha256"] = sha(project)
    report["source_unchanged"] = sha(SOURCE) == SOURCE_SHA
    write(out / "baseline-report.json", report)
    print("NATIVE53_DUET_BASELINE_RENDERED", flush=True)


def append_author_shader():
    assert sha(AUTHOR) == AUTHOR_SHA
    watched = ("objects", "meshes", "armatures", "images", "actions")
    before = {key: set(getattr(bpy.data, key).keys()) for key in watched}
    with bpy.data.libraries.load(str(AUTHOR), link=False) as (available, wanted):
        assert "新卡渲着色器" in available.node_groups
        wanted.node_groups = ["新卡渲着色器"]
    group = wanted.node_groups[0]
    assert group and group.bl_idname == "ShaderNodeTree"
    added = {
        key: sorted(set(getattr(bpy.data, key).keys()) - before[key]) for key in watched
    }
    assert not any(added.values()), (
        "Author model/texture dependencies must not enter delivery",
        added,
    )
    group["private_source_sha256"] = AUTHOR_SHA
    return group, added


def author_actor_shader(original, actor):
    group = original.copy()
    group.name = PREFIX + actor + " | actual author shader"
    group["author_group_source"] = "新卡渲着色器"
    group["adaptation"] = (
        "Original native53 shader copied;only light role tagging and per-actor light-allow masks added"
    )
    main_tag = PREFIX + "main | " + actor
    allow_tag = PREFIX + "allowed | " + actor
    for n in group.nodes:
        if (
            n.bl_idname == "ShaderNodeAttribute"
            and n.attribute_type == "LIGHT"
            and n.attribute_name == "主光"
        ):
            n.attribute_name = main_tag
    allowed = group.nodes.new("ShaderNodeAttribute")
    allowed.name = PREFIX + "explicit selected actor lights"
    allowed.attribute_type = "LIGHT"
    allowed.attribute_name = allow_tag
    for accum in [
        n for n in group.nodes if n.bl_idname == "ShaderNodeLightAccumulation"
    ]:
        for name in ("Diffuse Light", "Glossy Light", "Transmission Light"):
            socket = accum.inputs[name]
            if socket.is_linked:
                previous = socket.links[0].from_socket
                gated = color(
                    group,
                    previous,
                    allowed.outputs["Fac"],
                    1,
                    "limit " + accum.name + " " + name,
                    "MULTIPLY",
                )
                group.links.new(gated, socket)
    lights = [
        f"Eye hair v1 | {actor} directional head key",
        f"Reference duet | {actor} | fill",
        f"Reference duet | {actor} | rim",
    ]
    for i, name in enumerate(lights):
        lamp = bpy.data.objects[name].data
        lamp[allow_tag] = 1.0
        lamp[main_tag] = float(i == 0)
        lamp["主光"] = float(i == 0)
        lamp["亮部颜色"] = [1.0, 1.0, 1.0]
        lamp["暗部颜色"] = [1.0, 1.0, 1.0]
    return group, lights


def head_attributes(actor):
    obj = bpy.data.objects[ACTORS[actor]["mesh"]]
    tree = bpy.data.node_groups.new(
        PREFIX + actor + " own head attributes", "GeometryNodeTree"
    )
    tree.interface.new_socket(
        name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
    )
    tree.interface.new_socket(
        name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
    )
    incoming = tree.nodes.new("NodeGroupInput")
    outgoing = tree.nodes.new("NodeGroupOutput")
    origin = bpy.data.objects["Duet SDF 19 | " + actor + " full head basis"]
    axes = {}
    for name in ("front", "right", "up"):
        point = bpy.data.objects["Duet SDF 19 | " + actor + " axis " + name]
        xyz = tree.nodes.new("ShaderNodeCombineXYZ")
        for axis, socket in zip("XYZ", xyz.inputs):
            curve = socket.driver_add("default_value")
            for variable_name, target_obj in (("first", point), ("second", origin)):
                v = curve.driver.variables.new()
                v.name = variable_name
                v.type = "TRANSFORMS"
                v.targets[0].id = target_obj
                v.targets[0].transform_type = "LOC_" + axis
                v.targets[0].transform_space = "WORLD_SPACE"
            curve.driver.expression = "first-second"
        axes[name] = vector(
            tree, "NORMALIZE", xyz.outputs[0], (0, 0, 0), "own world " + name
        )
    left = vector(tree, "SCALE", axes["right"], (0, 0, 0), "own world left")
    # Vector Math SCALE uses its fourth input.
    left.node.inputs[3].default_value = -1
    geometry = incoming.outputs["Geometry"]
    for name, value in (
        ("面部法线", axes["front"]),
        ("前面", axes["front"]),
        ("人物左侧", left),
        ("头顶朝向", axes["up"]),
    ):
        store = tree.nodes.new("GeometryNodeStoreNamedAttribute")
        store.data_type = "FLOAT_VECTOR"
        store.domain = "POINT"
        store.inputs["Name"].default_value = name
        tree.links.new(geometry, store.inputs["Geometry"])
        tree.links.new(value, store.inputs["Value"])
        geometry = store.outputs["Geometry"]
    tree.links.new(geometry, outgoing.inputs["Geometry"])
    modifier = obj.modifiers.new(PREFIX + "head data only", "NODES")
    modifier.node_group = tree
    return tree.name


def own_sdf_closure(tree, actor):
    output = tree.nodes.new("NodeClosureOutput")
    output.name = PREFIX + "own actor SDF closure"
    output.input_items.clear()
    output.output_items.clear()
    output.input_items.new("VECTOR", "UV")
    output.output_items.new("FLOAT", "Threshold")
    incoming = tree.nodes.new("NodeClosureInput")
    incoming.pair_with_output(output)
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.name = PREFIX + "own actor SDF data only"
    tex.extension = "EXTEND"
    if actor == "aksiniya":
        tex.image = tree.nodes["Genshin study | supplied model FaceLightmap"].image
        tree.links.new(incoming.outputs["UV"], tex.inputs["Vector"])
        split = tree.nodes.new("ShaderNodeSeparateColor")
        tree.links.new(tex.outputs["Color"], split.inputs[0])
        value = split.outputs["Red"]
    else:
        tex.image = tree.nodes["Duet SDF 19 | own character face threshold"].image
        uv = tree.nodes.new("ShaderNodeTexCoord")
        tree.links.new(uv.outputs["UV"], tex.inputs["Vector"])
        split = tree.nodes.new("ShaderNodeSeparateColor")
        tree.links.new(tex.outputs["Color"], split.inputs[0])
        light = tree.nodes.new("ShaderNodeLightEvaluation")
        left = tree.nodes.new("ShaderNodeAttribute")
        left.attribute_name = "人物左侧"
        dot = vector(
            tree,
            "DOT_PRODUCT",
            left.outputs["Vector"],
            light.outputs["Direction"],
            "own side light test",
        )
        side = scalar(tree, "GREATER_THAN", dot, 0, "own key on left")
        value = scalar(
            tree,
            "ADD",
            split.outputs["Red"],
            scalar(
                tree,
                "MULTIPLY",
                scalar(
                    tree,
                    "SUBTRACT",
                    split.outputs["Green"],
                    split.outputs["Red"],
                    "own G minus R",
                ),
                side,
                "own side channel delta",
            ),
            "own threshold side selection",
        )
    tree.links.new(value, output.inputs["Threshold"])
    return output.outputs["Closure"], tex.image.name


def connect_author_material(material, actor, group):
    tree = material.node_tree
    old = tree.nodes.get("mmd_shader")
    if not old or material.name.startswith("mmd_edge"):
        return None
    role = (
        material.get("look_category")
        if actor == "aksiniya"
        else material.get("ikhor_material_role")
    )
    if role in {"ink", "hidden", "mouth", "eye_white"} or not role:
        return {
            "material": material.name,
            "role": role,
            "surface": "retained original flat feature/ink/hidden utility;not clothing shader",
        }
    face = material.name in {"颜", "颜.001"}
    role = "face" if face else role
    node = tree.nodes.new("ShaderNodeGroup")
    node.name = PREFIX + "actual author toon shader"
    node.node_tree = group
    values = {
        "阴影强度": 1.0,
        "金属度": 0.0,
        "次表面": 0.0,
        "受到阴影": True,
        "阴影受主光强度影响": True,
        "边缘不覆盖阴影": True,
        "亮部强度": 0.92,
        "亮度": 1.0,
        "Roughness": 0.8,
        "主光高光柔和度": 0.75,
        "主光高光强度": 0.06,
        "环境影响系数": 0.20,
        "环境色": (0.72, 0.79, 0.94, 1),
        "辅光强度": 0.22,
        "轮廓光强度": 0.08,
        "使用SDF阴影": False,
        "柔和阴影": True,
        "忽略日光仰角": False,
        "阴影色": (0.58, 0.64, 0.78, 1),
    }
    if role == "hair":
        values.update(
            {
                "阴影色": (0.49, 0.59, 0.79, 1)
                if actor == "aksiniya"
                else (0.55, 0.39, 0.20, 1),
                "Roughness": 0.58,
                "主光高光强度": 0.10,
                "亮部强度": 0.90,
                "辅光强度": 0.25,
            }
        )
    elif role in {"cloth", "fur"}:
        values.update(
            {
                "亮部强度": 0.86 if actor == "aksiniya" else 0.76,
                "Roughness": 0.84,
                "主光高光强度": 0.035,
                "辅光强度": 0.16,
            }
        )
    elif role == "trim":
        values.update(
            {
                "金属度": 0.65,
                "Roughness": 0.26,
                "主光高光强度": 0.35,
                "亮部强度": 0.86,
                "阴影色": (0.50, 0.47, 0.38, 1),
            }
        )
    elif role in {"face", "skin"}:
        values.update(
            {
                "亮部强度": 0.96 if actor == "aksiniya" else 0.86,
                "阴影色": (0.68, 0.42, 0.38, 1),
                "Roughness": 1.0,
                "主光高光强度": 0.0,
                "环境影响系数": 0.0,
                "辅光强度": 0.12,
                "轮廓光强度": 0.04,
            }
        )
    elif role in {"eye", "iris", "eye_layer"}:
        values.update(
            {
                "受到阴影": False,
                "主光高光强度": 0,
                "Roughness": 1.0,
                "轮廓光强度": 0,
                "辅光强度": 0.05,
                "亮部强度": 0.9,
                "阴影色": (0.9, 0.9, 0.95, 1),
            }
        )
    base = old.outputs["Color"]
    if face:
        values.update({"受到阴影": False, "使用SDF阴影": True})
        if actor == "aksiniya":
            base = tree.nodes["Face ink | Mouth crease"].outputs[0]
        hair = tree.nodes["Eye hair v1 | geometry derived hair shadow"].outputs["Color"]
        tinted = color(
            tree,
            (0.82, 0.58, 0.52, 1),
            (1, 1, 1, 1),
            hair,
            "native independent own bang tint",
        )
        base = color(
            tree, base, tinted, 1, "MMD color and independent actual bangs", "MULTIPLY"
        )
        closure, image = own_sdf_closure(tree, actor)
        tree.links.new(closure, node.inputs["SDF遮罩"])
        normal = tree.nodes.new("ShaderNodeAttribute")
        normal.attribute_name = "面部法线"
        tree.links.new(normal.outputs["Vector"], node.inputs["Normal"])
    else:
        geometry = tree.nodes.new("ShaderNodeNewGeometry")
        tree.links.new(geometry.outputs["Normal"], node.inputs["Normal"])
        image = None
    for name, value in values.items():
        node.inputs[name].default_value = value
    tree.links.new(base, node.inputs["基础色"])
    tree.links.new(old.outputs["Color"], node.inputs["金属色"])
    physical = tree.nodes.get("Ikhor character | material-specific physical closure")
    if role == "cloth" and physical and physical.inputs["Metallic"].is_linked:
        tree.links.new(
            physical.inputs["Metallic"].links[0].from_socket, node.inputs["金属度"]
        )
    outputs = [
        n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
    ]
    assert len(outputs) == 1
    # Some trim has a physical gold mix outside its PMX alpha,while eye layers
    # contain additional corneal mixes. Replace the actual old NPR closure's
    # consumers,not an assumed universal output-wrapper arrangement.
    surface = tree.nodes.get("Look v3 | NPR surface") or tree.nodes.get(
        "Ikhor character | controlled NPR surface"
    )
    assert surface and surface.type == "EMISSION", (
        material.name,
        "Missing audited NPR surface",
    )
    consumers = [link.to_socket for link in list(surface.outputs[0].links)]
    assert consumers, (material.name, "NPR surface has no consumers")
    wrappers = []
    for item in tree.nodes:
        if item.type == "MIX_SHADER" and any(
            s.is_linked and s.links[0].from_node.type == "BSDF_TRANSPARENT"
            for s in item.inputs[1:]
        ):
            factor = item.inputs[0]
            wrappers.append(
                {
                    "node": item.name,
                    "factor": [
                        (l.from_node.name, l.from_socket.identifier)
                        for l in factor.links
                    ],
                    "default": factor.default_value,
                }
            )
    assert wrappers, (material.name, "No original PMX alpha found anywhere in material")
    protected_alpha = digest([(w["node"], w["factor"], w["default"]) for w in wrappers])
    previous = surface.outputs[0]
    for socket in consumers:
        tree.links.new(node.outputs["Shader"], socket)
    after = []
    for w in wrappers:
        factor = tree.nodes[w["node"]].inputs[0]
        after.append(
            (
                w["node"],
                [(l.from_node.name, l.from_socket.identifier) for l in factor.links],
                factor.default_value,
            )
        )
    assert digest(after) == protected_alpha, (material.name, "Alpha factor changed")
    return {
        "material": material.name,
        "role": role,
        "author_group": group.name,
        "opaque_before": [previous.node.name, previous.name],
        "preserved_alpha_wrappers": wrappers,
        "values": values,
        "own_sdf_image": image,
    }


def characters(iteration):
    out = ROOT / iteration
    out.mkdir(parents=True, exist_ok=False)
    register_native()
    baseline_report = json.loads(
        (ROOT / "baseline-v1/baseline-report.json").read_text(encoding="utf-8")
    )
    assert sha(Path(baseline_report["project"])) == baseline_report["project_sha256"]
    bpy.ops.wm.open_mainfile(
        filepath=baseline_report["project"], use_scripts=False, load_ui=False
    )
    scene = bpy.context.scene
    mute_file_outputs()
    source_audit = json.loads((CACHE / "audit-goo.json").read_text(encoding="utf-8"))
    checks, deltas = preservation(scene, source_audit)
    assert all(checks.values()), checks
    original, added = append_author_shader()
    mappings = []
    heads = {}
    selected_lights = {}
    for actor in ACTORS:
        group, lights = author_actor_shader(original, actor)
        selected_lights[actor] = lights
        heads[actor] = head_attributes(actor)
        for material in bpy.data.objects[ACTORS[actor]["mesh"]].data.materials:
            if material and material.get("performer_id") == actor:
                item = connect_author_material(material, actor, group)
                if item:
                    mappings.append(item)
    checks, deltas = preservation(scene, source_audit)
    assert all(checks.values()), checks
    camera = scene.camera
    camera_state = camera_record(scene)
    markers = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    for marker, _ in markers:
        marker.camera = None
    report = {
        "source": str(SOURCE),
        "source_sha256": SOURCE_SHA,
        "native_baseline": baseline_report["project"],
        "author_source_sha256": AUTHOR_SHA,
        "new_imported_model_image_action_ids": added,
        "head_attribute_groups": heads,
        "selected_actor_lights": selected_lights,
        "materials": mappings,
        "checks": checks,
        "five_pose_coordinate_max_abs": deltas,
        "camera_saved": camera_state,
        "renders": [],
    }
    write(out / "character-report.json", report)
    for actor in ACTORS:
        cam = hero_camera(scene, actor)
        render(scene, out, "author53-" + actor + "-4290", cam, (640, 676), 32)
        report["renders"].append("author53-" + actor + "-4290.png")
    render(scene, out, "author53-duet-4290", camera, (1280, 720), 32)
    report["renders"].append("author53-duet-4290.png")
    for marker, old_camera in markers:
        marker.camera = old_camera
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.eevee.taa_render_samples = 64
    scene.render.filepath = str(out / "author53-duet-4290.png")
    checks, deltas = preservation(scene, source_audit)
    assert all(checks.values()), checks
    project = out / "Franken_Duet_Author53_Still.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report.update(
        {
            "project": str(project),
            "project_sha256": sha(project),
            "checks_after_render": checks,
            "source_unchanged": sha(SOURCE) == SOURCE_SHA,
        }
    )
    write(out / "character-report.json", report)
    print("NATIVE53_AUTHOR_CHARACTERS_RENDERED", flush=True)


def shadow_diagnostics():
    out = ROOT / "author-shadow-diagnostics-v1"
    out.mkdir(parents=True, exist_ok=False)
    record = json.loads(
        (ROOT / "author-trial-v2/character-report.json").read_text(encoding="utf-8")
    )
    project = Path(record["project"])
    assert sha(project) == record["project_sha256"]
    register_native()
    report = {
        "source_trial": str(project),
        "source_trial_sha256": record["project_sha256"],
        "controls": [],
    }
    for case in ("author-raycasts-white", "actor-solidify-disabled"):
        bpy.ops.wm.open_mainfile(
            filepath=str(project), load_ui=False, use_scripts=False
        )
        scene = bpy.context.scene
        mute_file_outputs()
        changed = []
        if case == "author-raycasts-white":
            for group in bpy.data.node_groups:
                if not (
                    group.name.startswith(PREFIX)
                    and "actual author shader" in group.name
                ):
                    continue
                white = group.nodes.new("ShaderNodeRGB")
                white.outputs[0].default_value = (1, 1, 1, 1)
                for node in group.nodes:
                    if node.bl_idname == "ShaderNodeShadowRaycast":
                        for link in list(node.outputs["Color"].links):
                            changed.append(
                                [
                                    group.name,
                                    node.name,
                                    link.to_node.name,
                                    link.to_socket.identifier,
                                ]
                            )
                            group.links.new(white.outputs[0], link.to_socket)
        else:
            for actor, spec in ACTORS.items():
                for modifier in scene.objects[spec["mesh"]].modifiers:
                    if modifier.type == "SOLIDIFY" and modifier.show_render:
                        changed.append(
                            {
                                "actor": actor,
                                "modifier": modifier.name,
                                "thickness": modifier.thickness,
                            }
                        )
                        modifier.show_render = False
        assert changed
        render(scene, out, case + "-4290", scene.camera, (1280, 720), 32)
        report["controls"].append(
            {
                "case": case,
                "changes": changed,
                "original_alpha_physical_mix_and_scene_lights_retained": True,
                "source_trial_saved": False,
                "camera": camera_record(scene),
            }
        )
    assert sha(project) == record["project_sha256"] and sha(SOURCE) == SOURCE_SHA
    write(out / "diagnostic-report.json", report)
    print("NATIVE53_AUTHOR_SHADOW_DIAGNOSTICS_RENDERED", flush=True)


def revise_sun_trial():
    out = ROOT / "author-trial-v3"
    out.mkdir(parents=True, exist_ok=False)
    before = json.loads(
        (ROOT / "author-trial-v2/character-report.json").read_text(encoding="utf-8")
    )
    assert sha(Path(before["project"])) == before["project_sha256"]
    register_native()
    bpy.ops.wm.open_mainfile(
        filepath=before["project"], load_ui=False, use_scripts=False
    )
    scene = bpy.context.scene
    mute_file_outputs()
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    changes = []
    for actor in ACTORS:
        parent = scene.objects[f"Eye hair v1 | {actor} directional head key"]
        light = bpy.data.lights.new(PREFIX + actor + " author SUN adapter", "SUN")
        light.energy = 3.0
        light.angle = 0.15
        light.color = (1, 1, 1)
        obj = bpy.data.objects.new(light.name, light)
        scene.collection.objects.link(obj)
        obj.parent = parent
        obj.light_linking.receiver_collection = parent.light_linking.receiver_collection
        assert obj.light_linking.receiver_collection
        main_tag = PREFIX + "main | " + actor
        allow_tag = PREFIX + "allowed | " + actor
        light[main_tag] = 1.0
        light[allow_tag] = 1.0
        light["主光"] = 1.0
        light["亮部颜色"] = [1.0, 1.0, 1.0]
        light["暗部颜色"] = [1.0, 1.0, 1.0]
        parent.data[main_tag] = 0.0
        parent.data[allow_tag] = 0.0
        group = bpy.data.node_groups[PREFIX + actor + " | actual author shader"]
        geometry = group.nodes.new("ShaderNodeNewGeometry")
        offset = vector(
            group,
            "SCALE",
            geometry.outputs["True Normal"],
            (0, 0, 0),
            "ray origin true normal",
        )
        offset.node.inputs[3].default_value = 0.0006
        rays = []
        for node in list(group.nodes):
            if node.bl_idname != "ShaderNodeShadowRaycast":
                continue
            base = (
                node.inputs["Position"].links[0].from_socket
                if node.inputs["Position"].is_linked
                else geometry.outputs["Position"]
            )
            shifted = vector(
                group, "ADD", base, offset, "ray origin 0.6mm " + node.name
            )
            group.links.new(shifted, node.inputs["Position"])
            rays.append(node.name)
        changes.append(
            {
                "actor": actor,
                "new_sun": obj.name,
                "parent_original_head_key": parent.name,
                "sun_energy": light.energy,
                "sun_angle": light.angle,
                "receivers": [
                    o.name for o in obj.light_linking.receiver_collection.objects
                ],
                "original_key_energy_unchanged": parent.data.energy,
                "ray_origin_bias_m": 0.0006,
                "ray_nodes": rays,
                "author_receives_shadows_kept": True,
            }
        )
    source = json.loads((CACHE / "audit-goo.json").read_text(encoding="utf-8"))
    checks, deltas = preservation(scene, source)
    assert all(checks.values()), checks
    report = {
        **before,
        "iteration": "author-trial-v3",
        "parent_trial": before["project"],
        "sun_contract_correction": changes,
        "checks": checks,
        "five_pose_coordinate_max_abs": deltas,
        "renders": ["author53-duet-4290.png"],
    }
    write(out / "character-report.json", report)
    render(scene, out, "author53-duet-4290", scene.camera, (1280, 720), 32)
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.eevee.taa_render_samples = 64
    project = out / "Franken_Duet_Author53_Still.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report.update(
        {
            "project": str(project),
            "project_sha256": sha(project),
            "source_unchanged": sha(SOURCE) == SOURCE_SHA,
        }
    )
    write(out / "character-report.json", report)
    print("NATIVE53_AUTHOR_SUN_TRIAL_RENDERED", flush=True)


def face_contract_trial():
    out = ROOT / "author-trial-v4"
    out.mkdir(parents=True, exist_ok=False)
    before = json.loads(
        (ROOT / "author-trial-v3/character-report.json").read_text(encoding="utf-8")
    )
    assert sha(Path(before["project"])) == before["project_sha256"]
    register_native()
    bpy.ops.wm.open_mainfile(
        filepath=before["project"], load_ui=False, use_scripts=False
    )
    scene = bpy.context.scene
    mute_file_outputs()
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    original = scene.camera
    camera_before = camera_record(scene)
    markers = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    for marker, _ in markers:
        marker.camera = None
    shader = bpy.data.materials["颜"].node_tree.nodes[
        PREFIX + "actual author toon shader"
    ]
    assert not shader.inputs["翻转uv"].default_value
    cam = hero_camera(scene, "aksiniya")
    for flipped in (False, True):
        shader.inputs["翻转uv"].default_value = flipped
        render(
            scene,
            out,
            "aksiniya-uv-flip-" + str(flipped).lower() + "-4290",
            cam,
            (640, 676),
            32,
        )
    for marker, camera in markers:
        marker.camera = camera
    scene.camera = original
    assert camera_record(scene) == camera_before
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.eevee.taa_render_samples = 64
    project = out / "Franken_Duet_Author53_Still.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        **before,
        "iteration": "author-trial-v4",
        "parent_trial": before["project"],
        "own_map_uv_contract": {
            "aksiniya_flip_uv": True,
            "reason": "Own map mirror uses left-dot>0,where author default uses left-dot<0",
            "ikhor": "Own R/G selection uses original UV,not mirrored UV",
        },
        "validation_scope_this_step": "Pinned v3 project;only Aks face flipUV differs;original camera/DOF restored;complete final preservation checked in final mode",
        "project": str(project),
        "project_sha256": sha(project),
        "renders": [
            "aksiniya-uv-flip-false-4290.png",
            "aksiniya-uv-flip-true-4290.png",
        ],
        "source_unchanged": sha(SOURCE) == SOURCE_SHA,
    }
    write(out / "character-report.json", report)
    print("NATIVE53_AUTHOR_FACE_CONTRACT_RENDERED", flush=True)


def active_undefined():
    result = []
    visited = set()

    def visit(label, tree):
        key = tree.as_pointer()
        if key in visited:
            return
        visited.add(key)
        names = linked_upstream(tree)
        for n in tree.nodes:
            if n.name not in names:
                continue
            if n.bl_idname == "NodeUndefined":
                result.append([label, n.name])
            if n.type == "GROUP" and n.node_tree:
                visit(label + "/" + n.name, n.node_tree)

    for label, tree in tree_owners().items():
        if label.startswith(("Material/", "World/", "Compositor/")):
            visit(label, tree)
    return result


def remove_unlinked_unknowns():
    removed = []
    retained = []
    seen = set()
    for label, tree in tree_owners().items():
        if tree.as_pointer() in seen:
            continue
        seen.add(tree.as_pointer())
        for node in list(tree.nodes):
            if node.bl_idname != "NodeUndefined":
                continue
            entry = {
                "tree": label,
                "node": node.name,
                "outgoing_links": sum(len(s.links) for s in node.outputs),
            }
            if entry["outgoing_links"] == 0:
                removed.append(entry)
                tree.nodes.remove(node)
            else:
                retained.append(entry)
    assert not active_undefined(), active_undefined()
    return {
        "removed_only_zero_outgoing": removed,
        "retained": retained,
        "original_archival_contract": str(CACHE / "audit-goo.json"),
    }


def final_preservation(scene, source):
    checks, deltas = preservation(scene, source)
    light_errors = []
    for item in source["lights"]:
        obj = scene.objects[item["object"]]
        same = (
            obj.data.type == item["type"]
            and abs(obj.data.energy - item["energy"]) < 1e-6
            and max(abs(a - b) for a, b in zip(obj.data.color, item["color"])) < 1e-7
            and max(
                abs(obj.matrix_world[i][j] - item["matrix"][i][j])
                for i in range(4)
                for j in range(4)
            )
            < 1e-6
            and obj.hide_render == item["hide_render"]
        )
        if not same:
            light_errors.append(item["object"])
    checks["all_original_light_transforms_energy_color_visible"] = not light_errors
    source_color = source["scene"]["color"]
    checks["source_color_management"] = [
        scene.display_settings.display_device,
        scene.view_settings.view_transform,
        scene.view_settings.look,
        scene.view_settings.exposure,
        scene.view_settings.gamma,
    ] == source_color
    checks["no_live_undefined"] = not active_undefined()
    image_errors = []
    for item in source["images"]:
        image = bpy.data.images.get(item["name"])
        if (
            image is None
            or list(image.size) != item["size"]
            or image.colorspace_settings.name != item["colorspace"]
        ):
            image_errors.append(item["name"])
    checks["original_images_sizes_colorspaces"] = not image_errors
    return checks, {
        "coordinate_max_abs": deltas,
        "light_errors": light_errors,
        "image_errors": image_errors,
    }


def final_prepare(parent_iteration):
    from native53_runtime import register_mmd

    out = ROOT / "final-v1"
    out.mkdir(parents=True, exist_ok=False)
    addons = register_mmd()
    accepted = json.loads(
        (ROOT / parent_iteration / "character-report.json").read_text(encoding="utf-8")
    )
    assert sha(Path(accepted["project"])) == accepted["project_sha256"]
    bpy.ops.wm.open_mainfile(
        filepath=accepted["project"], load_ui=False, use_scripts=False
    )
    scene = bpy.context.scene
    mute_file_outputs()
    scene.frame_set(4290)
    source = json.loads((CACHE / "audit-goo.json").read_text(encoding="utf-8"))
    cleanup = remove_unlinked_unknowns()
    checks, details = final_preservation(scene, source)
    assert all(checks.values()), checks
    camera = scene.camera
    markers = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    for marker, _ in markers:
        marker.camera = None
    report = {
        "source": str(SOURCE),
        "source_sha256": SOURCE_SHA,
        "parent_trial": accepted["project"],
        "author_source_sha256": AUTHOR_SHA,
        "runtime": {
            "version": bpy.app.version_string,
            "build": bpy.app.build_hash.decode(),
            "binary": bpy.app.binary_path,
            "addons": addons,
        },
        "implementation_script_sha256": sha(Path(__file__)),
        "scope": "4290 native53 original-author shader candidate;own actor data,scene bridge residuals recorded;no video/physics/eye see-through",
        "checks": checks,
        "details": details,
        "unknown_cleanup": cleanup,
        "source_camera_full_dof": source["camera"],
        "own_sdf_contract": accepted.get("own_map_uv_contract"),
        "actor_sun_and_bias": accepted.get("sun_contract_correction"),
        "materials": accepted["materials"],
        "renders": [],
    }
    write(out / "finalization.json", report)
    for enabled in (True, False):
        for name in ("颜", "颜.001"):
            bpy.data.materials[name].node_tree.nodes[
                PREFIX + "actual author toon shader"
            ].inputs["使用SDF阴影"].default_value = enabled
        tag = "sdf-on" if enabled else "sdf-off"
        for actor in ACTORS:
            cam = hero_camera(scene, actor)
            render(scene, out, tag + "-" + actor + "-4290", cam, (850, 900), 64)
            report["renders"].append(tag + "-" + actor + "-4290.png")
        render(scene, out, tag + "-duet-4290", camera, (1920, 1080), 64)
        report["renders"].append(tag + "-duet-4290.png")
    for name in ("颜", "颜.001"):
        bpy.data.materials[name].node_tree.nodes[
            PREFIX + "actual author toon shader"
        ].inputs["使用SDF阴影"].default_value = True
    for marker, old_camera in markers:
        marker.camera = old_camera
    scene.camera = camera
    scene.render.filepath = str(out / "sdf-on-duet-4290.png")
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.eevee.taa_render_samples = 64
    checks, details = final_preservation(scene, source)
    assert all(checks.values()), checks
    project = out / "Franken_Duet_Author53_Still.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report.update(
        {
            "project": str(project),
            "project_sha256": sha(project),
            "checks_after_render": checks,
            "details_after_render": details,
            "source_unchanged": sha(SOURCE) == SOURCE_SHA,
            "director_review": "pending actual final images",
        }
    )
    write(out / "finalization.json", report)
    print("NATIVE53_AUTHOR_FINAL_PREPARED", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=(
            "audit",
            "baseline",
            "characters",
            "shadow-diagnostics",
            "sun-trial",
            "face-contract",
            "finalize",
        ),
        required=True,
    )
    parser.add_argument("--runtime", choices=("goo", "native53"), default="native53")
    parser.add_argument("--iteration", default="baseline-v1")
    parser.add_argument("--from-iteration", default="author-trial-v4")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.mode == "audit":
        audit(args.runtime)
    elif args.mode == "baseline":
        baseline(args.iteration)
    elif args.mode == "characters":
        characters(args.iteration)
    elif args.mode == "shadow-diagnostics":
        shadow_diagnostics()
    elif args.mode == "sun-trial":
        revise_sun_trial()
    elif args.mode == "face-contract":
        face_contract_trial()
    elif args.mode == "finalize":
        final_prepare(args.from_iteration)


if __name__ == "__main__":
    main()
