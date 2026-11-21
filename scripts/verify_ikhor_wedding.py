"""Independently reopen the bounded Aksiniya/Ikhor integration; never render/save.

Blender --background --disable-autoexec --python-exit-code 1 --python this.py --
--source bold-v2.blend --actor Ikhor_Hina_Portable.blend --current new.blend
--profile ikhor-character-v1.json --output new-verification.json
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
from verify_character_layer_master import connection, group_signature, upstream

SOURCE_SHA = "ff05b52f9c64283f8909c41ed7fbc601cfa0034a94df7483690cf688d9d6a694"
ACTOR_SHA = "f864ad0efa936e3e1dde9462bdf42a0245d00158180b3b3c49ee5acf79cc5a4f"
AUDIO_SHA = "3e9c3c62f49523ec2959192dd5a4b698edddf8e78829d89b2c7952f7e1a58d52"
AUDIO = Path(
    "D:/codex/output/Franken-Duet-Full-Audio-v1/HIMEHINA - フランケンシュタインの怪物.flac"
)
FRAMES = [1, 2100, 4140, 4200, 4250, 4290, 4439, 8400, 11899]
PREFIX = "Ikhor character | "
EPS = 0.00001
_ACTION_CACHE = {}
_FRAME_CACHE = {}


def reopen(path):
    _ACTION_CACHE.clear()
    _FRAME_CACHE.clear()
    bpy.ops.wm.open_mainfile(filepath=str(path))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1048576), b""):
            h.update(data)
    return h.hexdigest()


def plain(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bpy.types.ID):
        return value.name
    try:
        return [plain(v) for v in value]
    except TypeError:
        return str(value)


def near(a, b):
    if isinstance(b, (tuple, list)):
        return (
            isinstance(a, (tuple, list))
            and len(a) == len(b)
            and all(near(x, y) for x, y in zip(a, b))
        )
    return a is not None and math.isfinite(float(a)) and abs(float(a) - float(b)) < EPS


def signature(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def socket(socket):
    return {
        "default": plain(getattr(socket, "default_value", None)),
        "links": connection(socket),
    }


def linked(socket, node, output=None):
    return (
        bool(node)
        and len(socket.links) == 1
        and socket.links[0].from_node == node
        and (output is None or socket.links[0].from_socket.name == output)
    )


def active_output(tree):
    return next(
        (n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output),
        None,
    )


def action_signature(action):
    if action is None:
        return None
    if action.as_pointer() in _ACTION_CACHE:
        return _ACTION_CACHE[action.as_pointer()]
    curves = list(getattr(action, "fcurves", ()))
    for layer in getattr(action, "layers", ()):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                curves.extend(bag.fcurves)
    h = hashlib.sha256()
    key_count = 0
    for curve in curves:
        h.update(
            json.dumps(
                {
                    "path": curve.data_path,
                    "index": curve.array_index,
                    "extrapolation": curve.extrapolation,
                    "mute": curve.mute,
                    "keys": len(curve.keyframe_points),
                    "samples": len(curve.sampled_points),
                },
                sort_keys=True,
            ).encode()
        )
        key_count += len(curve.keyframe_points)
        for prop in ("co", "handle_left", "handle_right"):
            values = array("f", [0]) * (2 * len(curve.keyframe_points))
            curve.keyframe_points.foreach_get(prop, values)
            h.update(values.tobytes())
        for prop in (
            "interpolation",
            "handle_left_type",
            "handle_right_type",
            "easing",
        ):
            values = array("i", [0]) * len(curve.keyframe_points)
            curve.keyframe_points.foreach_get(prop, values)
            h.update(values.tobytes())
        samples = array("f", [0]) * (2 * len(curve.sampled_points))
        curve.sampled_points.foreach_get("co", samples)
        h.update(samples.tobytes())
    result = {
        "name": action.name,
        "sha256": h.hexdigest(),
        "curves": len(curves),
        "keys": key_count,
        "range": list(action.frame_range),
    }
    _ACTION_CACHE[action.as_pointer()] = result
    return result


def animation(owner):
    data = getattr(owner, "animation_data", None)
    if not data:
        return None
    return {
        "action": action_signature(data.action),
        "slot": getattr(getattr(data, "action_slot", None), "identifier", None),
        "nla": [
            {
                "name": track.name,
                "mute": track.mute,
                "strips": [
                    {
                        "name": s.name,
                        "action": action_signature(s.action),
                        "start": s.frame_start,
                        "end": s.frame_end,
                        "scale": s.scale,
                        "repeat": s.repeat,
                        "influence": s.influence,
                        "blend": s.blend_type,
                    }
                    for s in track.strips
                ],
            }
            for track in data.nla_tracks
        ],
    }


def animation_semantics(value):
    if isinstance(value, dict):
        # An appended Action can acquire Blender's collision suffix while its
        # slot and every key/handle/interpolation byte remain exactly the same.
        return {
            key: animation_semantics(item)
            for key, item in value.items()
            if not (key == "name" and "sha256" in value and "curves" in value)
        }
    if isinstance(value, list):
        return [animation_semantics(item) for item in value]
    return value


def bulk(collection, prop, kind="f", width=1):
    values = array(kind, [0]) * (width * len(collection))
    collection.foreach_get(prop, values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def geometry(obj):
    mesh = obj.data
    weights = {group.name: hashlib.sha256() for group in obj.vertex_groups}
    names = {group.index: group.name for group in obj.vertex_groups}
    for vertex in mesh.vertices:
        for group in vertex.groups:
            weights[names[group.group]].update(
                array("I", [vertex.index]).tobytes()
                + array("f", [group.weight]).tobytes()
            )
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "positions": bulk(mesh.vertices, "co", width=3),
        "topology": bulk(mesh.loops, "vertex_index", "i"),
        "polygon_materials": bulk(mesh.polygons, "material_index", "i"),
        "uv": {layer.name: bulk(layer.data, "uv", width=2) for layer in mesh.uv_layers},
        "weights": {name: h.hexdigest() for name, h in weights.items()},
        "shapes": {
            key.name: bulk(key.data, "co", width=3)
            for key in mesh.shape_keys.key_blocks
        }
        if mesh.shape_keys
        else {},
        "shape_action": animation(mesh.shape_keys) if mesh.shape_keys else None,
        "source_materials": [
            m.get("source_mmd_material_name", m.name) if m else None
            for m in mesh.materials
        ],
    }


def image_record(image):
    if image is None:
        return None
    path = (
        str(Path(bpy.path.abspath(image.filepath)).resolve())
        if image.source == "FILE"
        else None
    )
    packed = image.packed_file
    return {
        "name": image.name,
        "source": image.source,
        "path": path,
        "packed": bool(packed),
        "sha256": hashlib.sha256(bytes(packed.data)).hexdigest()
        if packed
        else sha(path)
        if path and Path(path).is_file()
        else None,
        "size": list(image.size),
        "colorspace": image.colorspace_settings.name,
    }


def node_record(node):
    result = {
        "type": node.bl_idname,
        "inputs": {s.name: socket(s) for s in node.inputs},
        "group": group_signature(node.node_tree)
        if node.type == "GROUP" and node.node_tree
        else None,
    }
    for name in (
        "operation",
        "blend_type",
        "uv_map",
        "attribute_name",
        "extension",
        "projection",
        "interpolation",
    ):
        if hasattr(node, name):
            result[name] = plain(getattr(node, name))
    if node.type == "TEX_IMAGE":
        result["image"] = image_record(node.image)
    return result


def material_record(material):
    tree = material.node_tree
    properties = {}
    for name in (
        "diffuse_color",
        "ambient_color",
        "specular_color",
        "alpha",
        "shininess",
        "is_double_sided",
        "enabled_toon_edge",
        "edge_weight",
        "sphere_texture_type",
        "is_shared_toon_texture",
        "shared_toon_texture",
        "toon_texture",
    ):
        if hasattr(material.mmd_material, name):
            properties[name] = plain(getattr(material.mmd_material, name))
    return {
        "name": material.name,
        "source_name": material.get("source_mmd_material_name", material.name),
        "mmd": properties,
        "native_nodes": {
            n.name: node_record(n) for n in tree.nodes if n.name.startswith("mmd_")
        }
        if tree
        else {},
        "full_graph": group_signature(tree) if tree else None,
        "surface_render_method": material.surface_render_method,
        "animation": animation(material),
        "tree_animation": animation(tree) if tree else None,
    }


def object_record(obj):
    return {
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "parent_type": obj.parent_type,
        "parent_bone": obj.parent_bone,
        "action": animation(obj),
        "data_action": animation(obj.data) if obj.data else None,
        "geometry": geometry(obj) if obj.type == "MESH" else None,
        "bone_rest": {
            bone.name: [x for row in bone.matrix_local for x in row]
            for bone in obj.data.bones
        }
        if obj.type == "ARMATURE"
        else None,
        "ik": [
            {
                "bone": b.name,
                "name": c.name,
                "type": c.type,
                "mute": c.mute,
                "influence": c.influence,
                "target": getattr(getattr(c, "target", None), "name", None),
                "subtarget": getattr(c, "subtarget", None),
            }
            for b in obj.pose.bones
            for c in b.constraints
        ]
        if obj.type == "ARMATURE"
        else None,
    }


def actor_capture(actor):
    objects = [
        o
        for o in bpy.context.scene.objects
        if o.get("performer_id") == actor
        and o.type in {"MESH", "ARMATURE"}
        and getattr(o, "mmd_type", "") not in {"RIGID_BODY", "JOINT"}
    ]
    materials = {
        m
        for obj in objects
        if obj.type == "MESH"
        for m in obj.data.materials
        if m and m.get("ikhor_role") != "outline" and not m.name.startswith("mmd_edge.")
    }
    return {
        "objects": {o.name: object_record(o) for o in objects},
        "materials": {
            m.get("source_mmd_material_name", m.name): material_record(m)
            for m in materials
        },
        "samples": actor_samples(actor),
    }


def actor_samples(actor):
    sample_scene()
    return _FRAME_CACHE["actors"].get(actor, {})


def sample_scene():
    if _FRAME_CACHE:
        return
    scene = bpy.context.scene
    records, cameras = {}, []
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for obj in scene.objects:
            actor = obj.get("performer_id")
            if (
                not actor
                or obj.type not in {"MESH", "ARMATURE"}
                or getattr(obj, "mmd_type", "") in {"RIGID_BODY", "JOINT"}
            ):
                continue
            records.setdefault(actor, {}).setdefault(str(frame), {})[obj.name] = {
                "world": [x for row in obj.matrix_world for x in row],
                "bones": {
                    bone.name: [x for row in bone.matrix for x in row]
                    for bone in obj.pose.bones
                }
                if obj.type == "ARMATURE"
                else None,
                "shapes": {
                    key.name: key.value for key in obj.data.shape_keys.key_blocks
                }
                if obj.type == "MESH" and obj.data.shape_keys
                else None,
            }
        if scene.camera:
            data = scene.camera.data
            cameras.append(
                {
                    "frame": frame,
                    "world": [x for row in scene.camera.matrix_world for x in row],
                    "lens": data.lens,
                    "shift": [data.shift_x, data.shift_y],
                    "clip": [data.clip_start, data.clip_end],
                    "dof": {
                        name: plain(getattr(data.dof, name))
                        for name in (
                            "use_dof",
                            "focus_object",
                            "focus_distance",
                            "aperture_fstop",
                            "aperture_blades",
                            "aperture_rotation",
                            "aperture_ratio",
                        )
                    },
                }
            )
    _FRAME_CACHE.update(actors=records, camera=cameras)


def camera_capture():
    scene, chain = bpy.context.scene, []
    camera = scene.camera
    obj = camera
    while obj:
        chain.append({"name": obj.name, "record": object_record(obj)})
        obj = obj.parent
    sample_scene()
    return {"name": camera.name, "chain": chain, "samples": _FRAME_CACHE["camera"]}


def sound_capture():
    records = []
    for scene in bpy.data.scenes:
        editor = scene.sequence_editor
        if not editor:
            continue
        strips = getattr(
            editor, "strips_all", getattr(editor, "sequences_all", editor.strips)
        )
        for strip in strips:
            if strip.type != "SOUND":
                continue
            sound = strip.sound
            path = str(Path(bpy.path.abspath(sound.filepath)).resolve())
            packed = sound.packed_file
            records.append(
                {
                    "scene": scene.name,
                    "strip": strip.name,
                    "path": path,
                    "packed": bool(packed),
                    "sha256": hashlib.sha256(bytes(packed.data)).hexdigest()
                    if packed
                    else sha(path)
                    if Path(path).is_file()
                    else None,
                    "mute": strip.mute,
                    "volume": strip.volume,
                    "start": strip.frame_start,
                    "final_start": strip.frame_final_start,
                    "final_end": strip.frame_final_end,
                    "channel": strip.channel,
                }
            )
    return records


def scene_contract():
    scene = bpy.context.scene
    return {
        "scene": scene.name,
        "fps": scene.render.fps,
        "fps_base": scene.render.fps_base,
        "resolution": [
            scene.render.resolution_x,
            scene.render.resolution_y,
            scene.render.resolution_percentage,
        ],
        "frame_range": [scene.frame_start, scene.frame_end],
        "engine": scene.render.engine,
        "color": {
            name: plain(getattr(scene.view_settings, name))
            for name in ("view_transform", "look", "exposure", "gamma")
        },
        "display": scene.display_settings.display_device,
        "world": group_signature(scene.world.node_tree)
        if scene.world and scene.world.use_nodes
        else None,
        "shadow_pool_size": getattr(scene.eevee, "shadow_pool_size", None),
    }


def dormant_helpers():
    return {
        o.name: {
            "actor": o.get("performer_id"),
            "mmd_type": o.mmd_type,
            "hide_render": o.hide_render,
        }
        for o in bpy.data.objects
        if getattr(o, "mmd_type", "") in {"RIGID_BODY", "JOINT"}
        and o.rigid_body is None
        and o.rigid_body_constraint is None
    }


def errors(expected, actual):
    """Maximum float difference with explicit identity/shape agreement."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            return float("inf")
        return max((errors(v, actual[k]) for k, v in expected.items()), default=0)
    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)) or len(expected) != len(actual):
            return float("inf")
        return max((errors(a, b) for a, b in zip(expected, actual)), default=0)
    if isinstance(expected, (float, int)) and not isinstance(expected, bool):
        return (
            abs(expected - actual)
            if isinstance(actual, (float, int)) and math.isfinite(actual)
            else float("inf")
        )
    return 0 if expected == actual else float("inf")


def compare_actor(expected, actual, actor, check, geometry_subset=False):
    check(
        actor + ": actor object identities",
        expected["objects"].keys() == actual["objects"].keys(),
        sorted(actual["objects"]),
    )
    for name, old in expected["objects"].items():
        new = actual["objects"].get(name)
        if new is None:
            continue
        for field in (
            "type",
            "parent",
            "parent_type",
            "parent_bone",
            "action",
            "data_action",
            "bone_rest",
            "ik",
        ):
            check(
                name + ": retained " + field,
                animation_semantics(old[field]) == animation_semantics(new[field])
                if field in {"action", "data_action"}
                else old[field] == new[field],
            )
        if old["geometry"]:
            a, b = old["geometry"], new["geometry"]
            for field in (
                "vertices",
                "edges",
                "polygons",
                "positions",
                "topology",
                "polygon_materials",
                "shapes",
                "shape_action",
            ):
                check(
                    name + ": retained mesh " + field,
                    animation_semantics(a[field]) == animation_semantics(b[field])
                    if field == "shape_action"
                    else a[field] == b[field],
                )
            for field in ("uv", "weights"):
                check(
                    name + ": retained original " + field,
                    all(b[field].get(k) == v for k, v in a[field].items())
                    if geometry_subset
                    else a[field] == b[field],
                )
            check(
                name + ": retained source material slots",
                a["source_materials"]
                == b["source_materials"][: len(a["source_materials"])],
            )
    records = []
    for frame in FRAMES:
        error = errors(expected["samples"][str(frame)], actual["samples"][str(frame)])
        records.append(
            {
                "frame": frame,
                "maximum_pose_world_morph_error": error
                if math.isfinite(error)
                else None,
                "identity_match": math.isfinite(error),
            }
        )
    check(
        actor + ": nine frame pose world and morph equivalence",
        all(
            r["identity_match"] and r["maximum_pose_world_morph_error"] < EPS
            for r in records
        ),
        records,
    )
    return records


def position_drivers(tree, node, target):
    if not node or node.type != "COMBXYZ" or not tree.animation_data:
        return False
    drivers = {curve.data_path: curve.driver for curve in tree.animation_data.drivers}
    for axis, item in zip("XYZ", node.inputs):
        driver = drivers.get(item.path_from_id("default_value"))
        if (
            not driver
            or driver.type != "SCRIPTED"
            or driver.expression != "position"
            or len(driver.variables) != 1
        ):
            return False
        var = driver.variables[0]
        target_data = var.targets[0]
        if not (
            var.type == "TRANSFORMS"
            and var.name == "position"
            and target_data.id == target
            and target_data.transform_type == "LOC_" + axis
            and target_data.transform_space == "WORLD_SPACE"
        ):
            return False
    return True


def ikhor_materials(expected, actual, spec, preparation, check, report):
    mapped = spec["material_roles"]
    check(
        "Ikhor: all 26 source materials mapped",
        set(actual["materials"]) == set(mapped),
        sorted(actual["materials"]),
    )
    exceptions, skin_palettes = [], []
    for name, old in expected["materials"].items():
        new = actual["materials"].get(name)
        if not new:
            continue
        material = bpy.data.materials[new["name"]]
        tree, role = material.node_tree, mapped[name]
        mmd = tree.nodes.get("mmd_shader")
        for prop, value in old["mmd"].items():
            hidden = name == "bq" or name in spec.get("optional_parts", {}).get(
                "hide_materials", []
            )
            optional = (
                name in spec.get("optional_parts", {}).get("hide_materials", [])
                and prop == "alpha"
            )
            expected_property = (
                False
                if hidden and prop == "enabled_toon_edge"
                else 0
                if optional
                else value
            )
            check(
                name + ": original PMX " + prop,
                new["mmd"].get(prop) == expected_property,
            )
            if optional:
                exceptions.append(
                    {
                        "material": name,
                        "property": prop,
                        "source": value,
                        "current": new["mmd"].get(prop),
                    }
                )
        for node_name, original in old["native_nodes"].items():
            current = new["native_nodes"].get(node_name)
            if current is None:
                check(name + ": original native node " + node_name, False)
                continue
            original, current = dict(original), dict(current)
            if "image" in original and not (
                name == "颜" and node_name == "mmd_base_tex"
            ):
                original["image"], current["image"] = (
                    dict(original["image"]) if original["image"] else None,
                    dict(current["image"]) if current["image"] else None,
                )
                if original["image"] and current["image"]:
                    # Appending can legitimately suffix an image datablock name;
                    # actual packed bytes, colorspace, dimensions and path remain.
                    original["image"].pop("name")
                    current["image"].pop("name")
            if name == "颜" and node_name == "mmd_base_tex":
                replacement = current.pop("image", None)
                source_image = original.pop("image", None)
                check(
                    "颜: explicit same-character FaceDiffuse fallback",
                    bool(replacement)
                    and replacement["sha256"] == sha(spec["face_fallback"]["path"])
                    and replacement["packed"]
                    and replacement["colorspace"] == "sRGB",
                    {"source": source_image, "replacement": replacement},
                )
                exceptions.append(
                    {
                        "material": name,
                        "original_image": source_image,
                        "replacement": replacement,
                    }
                )
            if (
                name in spec.get("optional_parts", {}).get("hide_materials", [])
                and node_name == "mmd_shader"
            ):
                original["inputs"], current["inputs"] = (
                    dict(original["inputs"]),
                    dict(current["inputs"]),
                )
                for identifier, value in list(original["inputs"].items()):
                    if identifier == "Alpha":
                        check(
                            name + ": explicit native alpha input override",
                            not value["links"]
                            and not current["inputs"][identifier]["links"]
                            and near(value["default"], 1)
                            and near(current["inputs"][identifier]["default"], 0),
                        )
                        original["inputs"].pop(identifier)
                        current["inputs"].pop(identifier)
            check(
                name + ": retained native texture sphere UV graph " + node_name,
                original == current,
            )
        check(
            name + ": render and identity",
            material.get("performer_id") == "ikhor"
            and material.get("ikhor_character_revision") == spec["id"]
            and material.get("ikhor_material_role") == role
            and material.surface_render_method == old["surface_render_method"],
        )

        def node(suffix, tree=tree):
            return tree.nodes.get(PREFIX + suffix)

        emission, alpha, transparent = (
            node("controlled NPR surface"),
            node("preserve original MMD Alpha"),
            node("original animated PMX transparency"),
        )
        output = active_output(tree)
        check(
            name + ": original MMD Alpha final transparency",
            bool(mmd and alpha and transparent and output)
            and alpha.type == "MIX_SHADER"
            and linked(alpha.inputs[0], mmd, "Alpha")
            and linked(alpha.inputs[1], transparent)
            and transparent.type == "BSDF_TRANSPARENT"
            and linked(output.inputs["Surface"], alpha),
        )
        physical = node("material-specific physical closure")
        mix = node("toon and material physical closure")
        settings = spec["physical"][role]
        if settings["mix"]:
            check(
                name + ": original source color feeds physical closure",
                bool(physical and mix and emission)
                and linked(physical.inputs["Base Color"], mmd, "Color")
                and linked(mix.inputs[1], emission)
                and linked(mix.inputs[2], physical)
                and linked(alpha.inputs[2], mix),
            )
            for field, key, default in (
                ("Specular IOR Level", "specular", 0.3),
                ("Sheen Weight", "sheen", 0),
                ("Coat Weight", "coat", 0),
            ):
                check(
                    name + ": physical " + field,
                    bool(physical)
                    and near(
                        physical.inputs[field].default_value, settings.get(key, default)
                    ),
                )
            if name not in spec["gold_partition"]["materials"]:
                check(
                    name + ": role roughness and metallic",
                    bool(physical)
                    and near(
                        physical.inputs["Roughness"].default_value,
                        settings["roughness"],
                    )
                    and near(
                        physical.inputs["Metallic"].default_value,
                        settings.get("metallic", 0),
                    ),
                )
            else:
                mask = node("gold material partition art permission")
                active = upstream(physical.inputs["Metallic"]) if physical else set()
                check(
                    name + ": selected texture gold metal partition",
                    bool(mask and physical)
                    and mask.name in active
                    and PREFIX + "gold material partition source HSV" in active
                    and near(
                        physical.inputs["Metallic"]
                        .links[0]
                        .from_node.inputs[1]
                        .default_value,
                        spec["gold_partition"]["metallic"],
                    ),
                )
        else:
            check(
                name + ": feature closure without invented physical mix",
                physical is None
                and bool(emission)
                and linked(alpha.inputs[2], emission),
            )
        active = upstream(emission.inputs["Color"]) if emission else set()
        feature = role in {"ink", "eye_white", "iris", "eye_layer", "mouth", "hidden"}
        if feature:
            check(
                name + ": source feature color preserved",
                "mmd_shader" in active
                and PREFIX + "preserved feature color" in active
                and PREFIX + "single material palette" not in active,
            )
        else:
            ao, palette, response = (
                node("single short contact AO"),
                node("single material palette"),
                node("calibrated combined light response"),
            )
            probe, rgb = (
                node("key facing diffuse probe"),
                node("combined actual illumination"),
            )
            palette_values = (
                [
                    {"position": item.position, "color": list(item.color)}
                    for item in palette.color_ramp.elements
                ]
                if palette
                else []
            )
            palette_matches = (
                bool(palette)
                and palette.color_ramp.interpolation == "EASE"
                and len(palette_values) == 2
                and all(
                    near(item["position"], position) and near(item["color"], color)
                    for item, position, color in zip(
                        palette_values, (0.24, 0.80), spec["palettes"][role]
                    )
                )
            )
            check(
                name + ": one AO and palette in primary color",
                sum(tree.nodes[n].type == "AMBIENT_OCCLUSION" for n in active) == 1
                and bool(ao and palette)
                and ao.name in active
                and palette.name in active
                and palette_matches,
                {
                    "role": role,
                    "palette": palette_values,
                    "profile_colors": spec["palettes"][role],
                },
            )
            if role == "skin":
                skin_palettes.append(
                    {
                        "source_material": name,
                        "material": material.name,
                        "palette": palette_values,
                        "profile_colors": spec["palettes"][role],
                        "original_MMD_Color_still_upstream": "mmd_shader" in active,
                    }
                )
            check(
                name + ": AO distance and strength",
                bool(ao)
                and near(
                    ao.inputs["Distance"].default_value,
                    spec["ao"]["face_distance" if role == "face" else "distance"],
                )
                and near(
                    node("contact AO strength").outputs[0].default_value,
                    spec["ao"]["face_strength" if role == "face" else "strength"],
                ),
            )
            check(
                name + ": actual key position driver",
                position_drivers(
                    tree,
                    node("actual key position"),
                    bpy.context.scene.objects.get(spec["helpers"]["key"]),
                ),
            )
            check(
                name + ": key-facing combined probe",
                bool(probe and rgb and response)
                and linked(rgb.inputs[0], probe)
                and PREFIX + "surface to actual key" in upstream(probe.inputs["Normal"])
                and near(
                    response.inputs["From Min"].default_value,
                    spec["lighting_response"]["low"],
                )
                and near(
                    response.inputs["From Max"].default_value,
                    spec["lighting_response"]["high"],
                ),
            )
            check(
                name + ": reachable lighting bypass",
                bool(node("enable single lighting palette"))
                and node("enable single lighting palette").name in active
                and near(
                    node("enable single lighting palette").outputs[0].default_value, 1
                ),
            )
            check(
                name + ": unclamped NPR emission",
                bool(emission)
                and near(emission.inputs["Strength"].default_value, 1)
                and all(
                    not getattr(tree.nodes[n], "use_clamp", False)
                    for n in active
                    if tree.nodes[n].type == "MIX_RGB" and n.startswith(PREFIX)
                ),
            )
            if role == "face":
                softened, form = (
                    node("soft face form before occlusion"),
                    node("form times actual response"),
                )
                check(
                    "颜: soft form before actual response, no fabricated SDF",
                    bool(softened and form and response)
                    and softened.operation == "ADD"
                    and near(
                        softened.inputs[0].default_value,
                        spec["lighting_response"]["face_form_floor"],
                    )
                    and linked(form.inputs[0], softened)
                    and linked(form.inputs[1], response)
                    and PREFIX + "posed face form normal normalized"
                    in upstream(softened.inputs[1])
                    and not any("sdf" in n.lower() for n in active),
                )
            if role == "hair":
                check(
                    name + ": one direction and illumination gated hair band",
                    PREFIX + "single gated hair highlight" in active
                    and PREFIX + "directional hair band" in active
                    and response.name
                    in upstream(node("single gated hair highlight").inputs[1]),
                )
            for label, config in spec["local_emission"].items():
                if name in config["materials"]:
                    strength = node(label + " HDR strength")
                    check(
                        name + ": selective HDR " + label,
                        bool(strength)
                        and near(strength.outputs[0].default_value, config["strength"])
                        and strength.name in active
                        and PREFIX + label + " source HSV" in active,
                    )
        for aov_name in ("ReferenceDuetActor", "StageArtRim", "BoldWeddingEmission"):
            aovs = [
                n
                for n in tree.nodes
                if n.type == "OUTPUT_AOV" and n.aov_name == aov_name
            ]
            check(name + ": exactly one " + aov_name, len(aovs) == 1)
            if len(aovs) != 1:
                continue
            if aov_name == "ReferenceDuetActor":
                check(
                    name + ": actor AOV original animated Alpha",
                    linked(aovs[0].inputs["Value"], mmd, "Alpha"),
                )
            else:
                scale = node(aov_name + " respects Alpha")
                check(
                    name + ": " + aov_name + " original animated Alpha",
                    bool(scale)
                    and scale.type == "VECT_MATH"
                    and scale.operation == "SCALE"
                    and linked(scale.inputs[3], mmd, "Alpha")
                    and linked(aovs[0].inputs["Color"], scale),
                )
    report["material_exceptions"] = exceptions
    report["ikhor_skin_palettes"] = skin_palettes
    check(
        "documented same-character face fallback",
        bool(preparation.get("materials", {}).get("face_fallback")),
    )
    changes = preparation.get("optional_part_visibility_changes", [])
    optional_names = set(spec.get("optional_parts", {}).get("hide_materials", []))
    check("only declared optional quest props hidden", optional_names <= {"环", "灯"})
    for name in optional_names:
        check(
            name + ": optional quest prop Alpha exception documented",
            any(
                item.get("source_name") == name
                and near(item.get("original_alpha"), 1)
                and near(item.get("effective_alpha"), 0)
                for item in changes
            ),
        )
    for name in optional_names | {"bq"}:
        material = bpy.data.materials[actual["materials"][name]["name"]]
        check(
            name + ": transparent material has no opaque hull",
            near(material.mmd_material.alpha, 0)
            and not material.mmd_material.enabled_toon_edge
            and near(material.mmd_material.edge_color[3], 0),
        )


def scene_audit(source, portable, current, spec, preparation, check, report):
    scene = bpy.context.scene
    report["native_contract"] = current["contract"]
    report["camera_samples"] = current["camera"]["samples"]
    check(
        "preserved native frames fps color World and shadow pool",
        source["contract"] == current["contract"],
        current["contract"],
    )
    check(
        "native bounded delivery timebase 1080p60",
        current["contract"]["fps"] == 60
        and near(current["contract"]["fps_base"], 1)
        and current["contract"]["resolution"] == [1920, 1080, 100]
        and current["contract"]["frame_range"] == [4140, 4439],
    )
    check(
        "source Aksiniya camera full Actions and nine poses",
        source["camera"] == current["camera"],
    )
    report["aksiniya_samples"] = compare_actor(
        source["aksiniya"], current["aksiniya"], "aksiniya", check
    )
    for name, original in source["aksiniya"]["materials"].items():
        check(
            "Aksiniya original material graph/inputs/images: " + name,
            current["aksiniya"]["materials"].get(name) == original,
        )
    report["ikhor_samples"] = compare_actor(
        portable, current["ikhor"], "ikhor", check, geometry_subset=True
    )
    report["ikhor_animation_signatures"] = {
        name: {
            "body": item["action"],
            "morph": item["geometry"]["shape_action"] if item["geometry"] else None,
        }
        for name, item in current["ikhor"]["objects"].items()
    }
    ikhor_materials(portable, current["ikhor"], spec, preparation, check, report)
    arms = [o for o in scene.objects if o.type == "ARMATURE" and o.get("performer_id")]
    check(
        "exactly Aksiniya and Ikhor linked armatures",
        len(arms) == 2
        and sorted(o.get("performer_id", "") for o in arms) == ["aksiniya", "ikhor"],
        [{"name": o.name, "actor": o.get("performer_id")} for o in arms],
    )
    report["project_object_actors"] = sorted(
        {
            o.get("performer_id")
            for o in scene.objects
            if o.type in {"MESH", "ARMATURE"} and o.get("performer_id")
        }
    )
    residual = [
        o.name
        for o in bpy.data.objects
        if o.get("performer_id") == "aether"
        or "aether" in o.name.lower()
        and o.type in {"ARMATURE", "LIGHT", "EMPTY"}
    ]
    check("no old Aether linked objects or helpers", not residual, residual)
    physics = [
        o.name for o in bpy.data.objects if o.rigid_body or o.rigid_body_constraint
    ]
    check(
        "all scene rigidbody worlds absent",
        all(s.rigidbody_world is None for s in bpy.data.scenes),
    )
    check("no residual live rigid bodies or joints", not physics, physics)
    dormant = dormant_helpers()
    expected_dormant = {
        name: item
        for name, item in source["dormant_helpers"].items()
        if item["actor"] != "aether"
    }
    check(
        "original dormant non-render PMX helpers retained",
        dormant == expected_dormant
        and all(item["hide_render"] for item in dormant.values()),
        dormant,
    )
    check(
        "Ikhor has no dormant physics helper objects",
        all(item["actor"] != "ikhor" for item in dormant.values()),
    )
    report["dormant_non_live_source_helpers"] = dormant
    check(
        "no residual rigid tracking constraints",
        not any(
            c.name == "mmd_tools_rigid_track"
            for obj in arms
            for b in obj.pose.bones
            for c in b.constraints
        ),
    )
    for actor in ("aksiniya", "ikhor"):
        meshes = [
            o
            for o in scene.objects
            if o.type == "MESH"
            and o.get("performer_id") == actor
            and getattr(o, "mmd_type", "") not in {"RIGID_BODY", "JOINT"}
        ]
        check(
            actor + ": visible render-linked mesh",
            bool(meshes)
            and all(
                not o.hide_render and o.visible_get(view_layer=bpy.context.view_layer)
                for o in meshes
            ),
            [o.name for o in meshes],
        )
    scene.frame_set(4200)
    lights = []
    for label in ("key", "fill", "rim", "reflection"):
        lamp = scene.objects.get("Reference duet | ikhor | " + label)
        check(
            "Ikhor: linked visible " + label,
            bool(lamp)
            and lamp.type == "LIGHT"
            and not lamp.hide_render
            and lamp.get("performer_id") == "ikhor",
        )
        if not lamp:
            continue
        receivers = lamp.light_linking.receiver_collection
        objects = list(receivers.all_objects) if receivers else []
        check(
            "Ikhor " + label + ": isolated receivers",
            bool(objects)
            and all(
                o.get("performer_id") == "ikhor" and o.type == "MESH" for o in objects
            ),
        )
        check(
            "Ikhor " + label + ": correct diffuse contribution",
            lamp.data.diffuse_factor > 0
            if label == "key"
            else near(lamp.data.diffuse_factor, 0),
        )
        if label == "reflection":
            check(
                "Ikhor reflection: specular only wide area",
                lamp.data.type == "AREA"
                and lamp.data.shape == "RECTANGLE"
                and near(lamp.data.specular_factor, 1)
                and near(lamp.data.volume_factor, 0),
            )
        lights.append(
            {
                "name": lamp.name,
                "energy": lamp.data.energy,
                "diffuse": lamp.data.diffuse_factor,
                "receivers": [o.name for o in objects],
            }
        )
    report["ikhor_lights"] = lights
    arm = next(o for o in arms if o.get("performer_id") == "ikhor")
    for label in ("origin", "forward", "up"):
        helper = scene.objects.get("Quality | ikhor | head " + label)
        check(
            "Ikhor posed head " + label,
            bool(helper)
            and helper.get("performer_id") == "ikhor"
            and helper.parent == arm
            and helper.parent_type == "BONE"
            and arm.pose.bones[helper.parent_bone].mmd_bone.name_j == "頭",
        )
    for layer in scene.view_layers:
        for name, kind in (
            ("ReferenceDuetActor", "VALUE"),
            ("StageArtRim", "COLOR"),
            ("BoldWeddingEmission", "COLOR"),
            ("TransferStageZone", "VALUE"),
        ):
            check(
                layer.name + ": AOV " + name,
                layer.aovs.get(name) is not None and layer.aovs[name].type == kind,
            )
    for item in current["ikhor"]["materials"].values():
        material = bpy.data.materials[item["name"]]
        check(
            material.name + ": actor excluded from stage zone AOV",
            not any(
                n.type == "OUTPUT_AOV" and n.aov_name == "TransferStageZone"
                for n in material.node_tree.nodes
            ),
        )
    outlines = []
    for obj in scene.objects:
        if obj.type != "MESH" or obj.get("performer_id") != "ikhor":
            continue
        modifier = obj.modifiers.get("mmd_edge_preview")
        if modifier:
            outlines.append(
                {
                    "mesh": obj.name,
                    "thickness": modifier.thickness,
                    "vertex_group": modifier.vertex_group,
                }
            )
            check(
                obj.name + ": native weighted outlines enabled",
                modifier.type == "SOLIDIFY"
                and modifier.show_render
                and modifier.thickness > 0
                and bool(modifier.vertex_group)
                and modifier.vertex_group in obj.vertex_groups,
            )
    check("Ikhor: native outline modifier exists", bool(outlines), outlines)
    report["outlines"] = outlines
    edge_aovs = []
    for material in bpy.data.materials:
        if (
            material.get("performer_id") != "ikhor"
            or material.get("ikhor_role") != "outline"
        ):
            continue
        edge = (
            material.node_tree.nodes.get("mmd_edge_preview")
            if material.node_tree
            else None
        )
        aovs = (
            [
                n
                for n in material.node_tree.nodes
                if n.type == "OUTPUT_AOV" and n.aov_name == "ReferenceDuetActor"
            ]
            if material.node_tree
            else []
        )
        check(
            material.name + ": original outline Alpha exists",
            bool(edge) and edge.inputs.get("Alpha") is not None,
        )
        if edge and edge.inputs.get("Alpha") and len(aovs) == 1:
            value, alpha = aovs[0].inputs["Value"], edge.inputs["Alpha"]
            check(
                material.name + ": outline actor AOV follows own Alpha",
                connection(value) == connection(alpha)
                and (alpha.is_linked or near(value.default_value, alpha.default_value)),
            )
            edge_aovs.append(
                {
                    "material": material.name,
                    "alpha": socket(alpha),
                    "actor_aov": socket(value),
                }
            )
        else:
            check(material.name + ": exactly one outline actor AOV", False)
    report["outline_alpha_aovs"] = edge_aovs
    check("Ikhor: outline AOV audit covers generated materials", bool(edge_aovs))
    volumes = [
        o
        for o in scene.objects
        if o.type == "MESH"
        and o.name.startswith("Bold wedding |")
        and " luminous volume " in o.name
    ]
    check(
        "six separate artistic beam volumes",
        len(volumes) == 6,
        [o.name for o in volumes],
    )
    report["artistic_beams"] = []
    for obj in volumes:
        material = obj.data.materials[0] if obj.data.materials else None
        tree = material.node_tree if material else None
        volume = (
            tree.nodes.get("Wedding art | luminous shaft, not physical scatter")
            if tree
            else None
        )
        output = active_output(tree) if tree else None
        check(
            obj.name + ": soft emission Volume separate from World",
            bool(volume and output)
            and volume.type == "PRINCIPLED_VOLUME"
            and linked(output.inputs["Volume"], volume)
            and near(volume.inputs["Density"].default_value, 0.001)
            and volume.inputs["Emission Strength"].is_linked
            and sum(
                n.type == "MAP_RANGE" and n.interpolation_type == "SMOOTHSTEP"
                for n in tree.nodes
            )
            >= 3,
        )
        report["artistic_beams"].append(
            {
                "name": obj.name,
                "method": "soft radial Volume Emission; not a physical spot scattering claim",
                "world_y_bounds": [
                    min((obj.matrix_world @ v.co).y for v in obj.data.vertices),
                    max((obj.matrix_world @ v.co).y for v in obj.data.vertices),
                ],
            }
        )
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
        "caption beauty and final output same signal",
        len(final) == 1
        and bool(beauty)
        and bool(connection(final[0].inputs["Image"]))
        and connection(final[0].inputs["Image"]) == connection(beauty.inputs["beauty"]),
    )
    outputs = [
        {"scene": s.name, "node": n.name, "muted": n.mute}
        for s in bpy.data.scenes
        if s.compositing_node_group
        for n in s.compositing_node_group.nodes
        if n.type == "OUTPUT_FILE"
    ]
    check(
        "every scene FileOutput muted",
        bool(outputs) and all(n["muted"] for n in outputs),
        outputs,
    )
    check(
        "timeline original FLAC audio retained",
        source["audio"] == current["audio"],
        current["audio"],
    )
    check(
        "fixed original vocal FLAC SHA256", AUDIO.is_file() and sha(AUDIO) == AUDIO_SHA
    )
    check(
        "active project sound is fixed FLAC",
        any(not s["mute"] and s["sha256"] == AUDIO_SHA for s in current["audio"]),
        current["audio"],
    )
    used = {}

    def images(tree, seen=None):
        seen = set() if seen is None else seen
        if not tree or tree.as_pointer() in seen:
            return
        seen.add(tree.as_pointer())
        for n in tree.nodes:
            if n.type == "TEX_IMAGE" and n.image and n.image.source == "FILE":
                used[n.image.name] = image_record(n.image)
            if n.type == "GROUP":
                images(n.node_tree, seen)

    for obj in scene.objects:
        if obj.type == "MESH" and not obj.hide_render:
            for material in obj.data.materials:
                if material:
                    images(material.node_tree)
    images(scene.world.node_tree if scene.world and scene.world.use_nodes else None)
    missing = [
        record
        for record in used.values()
        if record["sha256"] is None or not all(record["size"])
    ]
    report["render_used_missing_images"] = missing
    report["render_used_image_count"] = len(used)
    report["all_file_image_count"] = len(
        [i for i in bpy.data.images if i.source == "FILE"]
    )
    check("no missing images on render-linked material graphs", not missing, missing)
    check(
        "render-used file images packed",
        bool(used) and all(i["packed"] for i in used.values()),
    )
    check(
        "declared bounded physics window",
        list(scene.get("ikhor_physics_validated_frames", [])) == [4139, 4441],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "actor", "current", "profile", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--preparation", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.output.exists():
        raise FileExistsError(args.output)
    report = {
        "source": str(args.source),
        "actor": str(args.actor),
        "current": str(args.current),
        "project": str(args.current),
        "profile": str(args.profile),
        "checks": [],
        "errors": [],
        "read_only": True,
        "rendered": False,
        "project_saved": False,
        "preferences_changed": False,
        "art_status": "pending",
        "user_art_approval": False,
    }

    def check(name, passed, details=None):
        report["checks"].append(
            {"name": name, "passed": bool(passed), "details": details}
        )

    try:
        report["source_sha256"], report["actor_sha256"], report["project_sha256"] = (
            sha(args.source),
            sha(args.actor),
            sha(args.current),
        )
        report["current_sha256"] = report["project_sha256"]
        check("pinned Bold Wedding v2 source", report["source_sha256"] == SOURCE_SHA)
        check("pinned verified native Ikhor actor", report["actor_sha256"] == ACTOR_SHA)
        actor_evidence = json.loads(
            (args.actor.parent / "append-verification.json").read_text(
                encoding="utf-8-sig"
            )
        )
        check(
            "independent portable evidence bound to actual actor",
            actor_evidence.get("passed") is True
            and actor_evidence.get("project_sha256") == ACTOR_SHA
            and actor_evidence.get("participating_rigid_bodies", 0) == 514
            and actor_evidence.get("participating_dynamic_rigid_bodies", 0) == 481
            and len(actor_evidence.get("samples", [])) == 9,
        )
        report["native_physics_evidence"] = {
            key: actor_evidence.get(key)
            for key in (
                "project_sha256",
                "participating_rigid_bodies",
                "participating_dynamic_rigid_bodies",
                "physics_simulation_source_frames",
                "physical_scope",
                "timebase",
                "full_song_physics_validated",
            )
        }
        spec = json.loads(args.profile.read_text(encoding="utf-8-sig"))
        report["profile_sha256"], report["audit_script_sha256"] = (
            sha(args.profile),
            sha(__file__),
        )
        check(
            "unchanged original Ikhor PMX",
            sha(spec["source_pmx"]) == spec["source_pmx_sha256"],
        )
        preparation = json.loads(
            (
                args.preparation
                or args.current.parent / "ikhor-wedding-preparation.json"
            ).read_text(encoding="utf-8-sig")
        )
        check(
            "producer bound same actor and source",
            preparation["source_sha256"] == SOURCE_SHA
            and preparation["actor_sha256"] == ACTOR_SHA,
        )
        reopen(args.source)
        source = {
            "aksiniya": actor_capture("aksiniya"),
            "camera": camera_capture(),
            "contract": scene_contract(),
            "audio": sound_capture(),
            "dormant_helpers": dormant_helpers(),
        }
        print("IKHOR_AUDIT_SOURCE_CAPTURED", flush=True)
        reopen(args.actor)
        portable = actor_capture("ikhor")
        print("IKHOR_AUDIT_PORTABLE_CAPTURED", flush=True)
        reopen(args.current)
        current = {
            "aksiniya": actor_capture("aksiniya"),
            "ikhor": actor_capture("ikhor"),
            "camera": camera_capture(),
            "contract": scene_contract(),
            "audio": sound_capture(),
        }
        print("IKHOR_AUDIT_CURRENT_CAPTURED", flush=True)
        scene_audit(source, portable, current, spec, preparation, check, report)
        check(
            "readonly current file bytes unchanged",
            sha(args.current) == report["project_sha256"],
        )
    except Exception as error:  # noqa: BLE001 -- Preserve unexpected native audit failures in the JSON report.
        report["errors"].append(
            {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            }
        )
    report["failed_checks"] = [c for c in report["checks"] if not c["passed"]]
    report["passed"] = (
        bool(report["checks"]) and not report["failed_checks"] and not report["errors"]
    )
    report["limits"] = [
        "Native data, graph and nine-time pose/curve audit only; no render, decoded video/audio or visual approval.",
        "Physics is genuinely new for Ikhor but only the declared local window; full VMD body/morph retention is not full-song physical validation.",
        "FaceDiffuse is an explicit fallback for missing edited y1.png, not restoration or a verified original SDF.",
        "HSV metal/emission masks, AOVs and Volume Emission beams are artistic controls, not recovered physical light/material passes.",
        "Outline actor AOVs are checked against their actual MMD edge Alpha input; actual coverage and halo appearance require render review.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(
        "IKHOR_WEDDING_VERIFIED",
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
