"""Reversible daylight base for the two audited Hesperides duet files.

apply(scene, settings=None) restores retained authored ToonBased/MatCap diffuse
plus its existing GGX/Alpha surface, with a bounded real-light response and
stage-only broad Area fills. It never renders, saves, bakes, changes World,
camera, actors, geometry, Actions, preferences, or compositor. The sky is owned
by the caller. This is a local hybrid approximation, not the author's Ray BRDF.

The Focused PBR branch remains the physical bypass. set_gain(scene, 0) restores
every intercepted original input link/default and disables only the new lamps.
Ground-only copies keep their existing PBR/contact path by default.
"""

import copy
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

PREFIX = "Portrait day stage | "
STATE = "portrait_day_stage_state"
LIGHT_STATE = "portrait_day_stage_lights"
SOURCE_SHAS = {
    "0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4",
    "1a038359425bbbe50e327b669dcd4a19ee69158846e29a1af3bbcbc9908a6489",
}
MATERIALS = {
    "mat_9.001",
    "mat_10.001",
    "mat_12.001",
    "mat_14.001",
    "mat_15.001",
    *("mat_20." + str(i).zfill(3) for i in range(7, 13)),
    "mat_22.001",
    "mat_24.001",
    "mat_26.001",
    "mat_28.001",
    "mat_51.001",
    "mat_52.001",
    "mat_54.001",
    "mat_55.001",
    "mat_61.001",
}
GROUND = {
    "Stage art | ground only | mat_10.001",
    "Stage art | ground only | mat_20.010",
}
DEFAULT_SETTINGS = {
    "id": "portrait-day-stage-v1",
    "gain": 1.0,
    "verify_source_hash": True,
    "preserve_ground_only": True,
    "diffuse_response_range": [0.02, 0.35],
    "diffuse_response_output": [0.82, 1.06],
    "diffuse_tint": [0.96, 0.975, 1.04, 1.0],
    "matcap_relative_gain": 0.60,
    "material_overrides": {},
    "lights": {
        "enabled": True,
        "specular_factor": 0.60,
        "items": [
            {
                "name": "left daylight soft",
                "position": [-12, 14, 10],
                "target": [0, 18, 4],
                "energy": 3000,
                "size": 16,
                "color": [0.76, 0.84, 1.0],
            },
            {
                "name": "right daylight soft",
                "position": [12, 14, 10],
                "target": [0, 18, 4],
                "energy": 2600,
                "size": 16,
                "color": [0.91, 0.91, 1.0],
            },
            {
                "name": "high diffuse bounce",
                "position": [0, 22, 18],
                "target": [0, 22, 0],
                "energy": 4200,
                "size": 18,
                "color": [0.88, 0.91, 1.0],
            },
        ],
    },
}


def _plain(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return [_plain(item) for item in value]


def _merge(base, changes):
    result = copy.deepcopy(base)
    for key, value in changes.items():
        if key not in result:
            raise ValueError("Unknown daylight setting: " + key)
        if key == "material_overrides":
            result[key] = copy.deepcopy(value)
        elif isinstance(result[key], dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _number(value, label, low=0, high=1):
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Invalid daylight " + label)
    return value


def _source(socket):
    if socket.is_linked:
        if len(socket.links) != 1:
            raise ValueError("Expected one daylight input source")
        return socket.links[0].from_socket
    return _plain(getattr(socket, "default_value", None))


def _descriptor(socket, output=True):
    return {
        "node": socket.node.name,
        "index": list(socket.node.outputs if output else socket.node.inputs).index(
            socket
        ),
        "identifier": socket.identifier,
    }


def _node(tree, kind, label):
    name = PREFIX + label
    if len(name.encode("utf-8")) > 63 or tree.nodes.get(name):
        raise ValueError("Duplicate or overlong daylight node: " + name)
    result = tree.nodes.new(kind)
    result.name = result.label = name
    return result


def _plug(tree, source, target):
    if hasattr(source, "is_output"):
        tree.links.new(source, target)
    else:
        target.default_value = source


def _record_change(tree, target, modified, records):
    old = _source(target)
    records.append(
        {
            "target": _descriptor(target, False),
            "original": {"source": _descriptor(old)}
            if hasattr(old, "is_output")
            else {"default": old},
            "original_default": _plain(getattr(target, "default_value", None)),
            "modified": _descriptor(modified),
        }
    )
    tree.links.new(modified, target)


def _multiply(tree, first, second, label):
    result = _node(tree, "ShaderNodeMixRGB", label)
    result.blend_type, result.use_clamp = "MULTIPLY", False
    result.inputs[0].default_value = 1
    _plug(tree, first, result.inputs[1])
    _plug(tree, second, result.inputs[2])
    return result.outputs[0]


def _upstream_nodes(socket):
    pending = [socket.node]
    seen = {}
    while pending:
        node = pending.pop()
        if node.name in seen:
            continue
        seen[node.name] = node
        pending.extend(link.from_node for inp in node.inputs for link in inp.links)
    return seen


def _contract(scene, name):
    material = bpy.data.materials.get(name)
    if (
        not material
        or material.get("stage_id") != "hesperides_hall"
        or material.get("performer_id")
    ):
        raise ValueError("Missing exact daylight stage material: " + name)
    users = [
        obj
        for obj in scene.objects
        if obj.type == "MESH" and material in obj.data.materials[:]
    ]
    if not users or any(obj.get("performer_id") for obj in users):
        raise ValueError("Daylight material has missing/shared actor users: " + name)
    tree = material.node_tree
    if (
        not tree
        or STATE in material
        or any(n.name.startswith(PREFIX) for n in tree.nodes)
    ):
        raise ValueError("Refusing repeated daylight installation: " + name)
    output = next(
        n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
    )
    focused = tree.nodes.get("Focused light | responsive stage surface")
    choice = tree.nodes.get("Reference | ToonBased vs ordinary PBR")
    if (
        not focused
        or focused.type != "BSDF_PRINCIPLED"
        or _source(output.inputs["Surface"]).node != focused
    ):
        raise ValueError(
            "Stage is no longer on the audited Focused PBR branch: " + name
        )
    if (
        not choice
        or choice.type != "MIX_SHADER"
        or choice.inputs[0].is_linked
        or abs(choice.inputs[0].default_value - 1) > 1e-6
    ):
        raise ValueError("Missing enabled retained ToonBased branch: " + name)
    nodes = _upstream_nodes(_source(choice.inputs[2]))
    emissions = [n for n in nodes.values() if n.type == "EMISSION"]
    ggx = [n for n in nodes.values() if n.type == "BSDF_PRINCIPLED"]
    if len(emissions) != 1 or len(ggx) != 1:
        raise ValueError("Ambiguous retained diffuse/GGX closure: " + name)
    quality = tree.nodes.get("Quality | preserve chroma with scalar shading")
    if (
        not quality
        or quality.name not in nodes
        or quality.type != "MIX_RGB"
        or quality.blend_type != "MULTIPLY"
    ):
        raise ValueError(
            "Retained diffuse does not have the audited old attenuation: " + name
        )
    # Later night-look multipliers also wrap the old Quality output. Recover
    # the authored color before both, rather than merely brightening that chain.
    authored = _source(quality.inputs[1])
    if not hasattr(authored, "is_output"):
        raise ValueError("Missing retained authored diffuse texture chain: " + name)
    return material, output, focused, choice, emissions[0], ggx[0], authored


def _lights(scene, spec, gain):
    receiver_name = PREFIX + "stage receivers"
    if bpy.data.collections.get(receiver_name) or LIGHT_STATE in scene:
        raise ValueError("Refusing repeated daylight lamps")
    receivers = bpy.data.collections.new(receiver_name)
    scene.collection.children.link(receivers)
    stage_objects = [
        o
        for o in scene.objects
        if o.type == "MESH"
        and not o.get("performer_id")
        and any(m and m.get("stage_id") == "hesperides_hall" for m in o.data.materials)
    ]
    for obj in stage_objects:
        receivers.objects.link(obj)
    records = []
    for item in spec["items"]:
        name = PREFIX + item["name"]
        if bpy.data.objects.get(name) or bpy.data.lights.get(name):
            raise ValueError("Daylight lamp already exists: " + name)
        data = bpy.data.lights.new(name, "AREA")
        data.energy = item["energy"] * gain
        data.color, data.size = item["color"], item["size"]
        data.use_shadow, data.volume_factor = True, 0
        data.diffuse_factor, data.specular_factor = 1, spec["specular_factor"]
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = item["position"]
        obj.rotation_euler = (
            (Vector(item["target"]) - obj.location).to_track_quat("-Z", "Y").to_euler()
        )
        obj.light_linking.receiver_collection = receivers
        obj.hide_render = obj.hide_viewport = not bool(gain)
        records.append(
            {
                "object": obj.name,
                "full_energy": item["energy"],
                "position": item["position"],
                "target": item["target"],
                "color": item["color"],
                "size": item["size"],
                "receiver_collection": receivers.name,
            }
        )
    scene[LIGHT_STATE] = json.dumps(records, ensure_ascii=False)
    return {
        "lights": records,
        "stage_receivers": sorted(o.name for o in stage_objects),
        "actor_receivers": [],
    }


def set_gain(scene, gain):
    """Zero physically restores old material inputs and disables new stage lamps."""
    gain = _number(gain, "gain")
    changed = []
    for material in bpy.data.materials:
        if STATE not in material:
            continue
        state, tree = json.loads(material[STATE]), material.node_tree
        for record in state["targets"]:
            descriptor = record["target"]
            target = tree.nodes[descriptor["node"]].inputs[descriptor["index"]]
            for link in list(target.links):
                tree.links.remove(link)
            if (
                hasattr(target, "default_value")
                and record["original_default"] is not None
            ):
                target.default_value = record["original_default"]
            chosen = record["modified"] if gain else record["original"].get("source")
            if chosen:
                tree.links.new(
                    tree.nodes[chosen["node"]].outputs[chosen["index"]], target
                )
            elif (
                "default" in record["original"]
                and record["original"]["default"] is not None
            ):
                target.default_value = record["original"]["default"]
        tree.nodes[state["gain_node"]].outputs[0].default_value = gain
        changed.append(material.name)
    for record in json.loads(scene.get(LIGHT_STATE, "[]")):
        obj = scene.objects[record["object"]]
        obj.data.energy = record["full_energy"] * gain
        obj.hide_render = obj.hide_viewport = not bool(gain)
    return changed


def apply(scene, settings=None):
    """Install the controlled stage-only hybrid base; return actual graph changes."""
    spec = _merge(DEFAULT_SETTINGS, settings or {})
    gain = _number(spec["gain"], "gain")
    _number(spec["matcap_relative_gain"], "MatCap gain", 0, 2)
    for key in ("diffuse_response_range", "diffuse_response_output"):
        lo, hi = spec[key]
        _number(lo, key, 0, 4)
        _number(hi, key, 0, 4)
        if lo >= hi:
            raise ValueError("Expected increasing daylight range: " + key)
    if len(spec["diffuse_tint"]) != 4 or spec["diffuse_tint"][3] != 1:
        raise ValueError("Daylight tint must have alpha one")
    for value in spec["diffuse_tint"][:3]:
        _number(value, "diffuse tint", 0, 2)
    source = Path(bpy.data.filepath)
    source_sha = None
    if spec["verify_source_hash"]:
        with source.open("rb") as stream:
            source_sha = hashlib.file_digest(stream, "sha256").hexdigest()
        if source_sha not in SOURCE_SHAS:
            raise ValueError(
                "Daylight base accepts only the audited Clean/portrait-v2 source SHAs"
            )
    targets = MATERIALS | (set() if spec["preserve_ground_only"] else GROUND)
    if set(spec["material_overrides"]) - targets:
        raise ValueError("Daylight override outside the exact material whitelist")
    plans = [_contract(scene, name) for name in sorted(targets)]
    for item in spec["lights"]["items"]:
        _number(item["energy"], "lamp energy", 0, 20000)
        _number(item["size"], "lamp size", 0.01, 50)
        if (Vector(item["target"]) - Vector(item["position"])).length < 0.01:
            raise ValueError("Daylight lamp target overlaps position")
    report = {
        "id": spec["id"],
        "source_sha256": source_sha,
        "settings": spec,
        "materials": [],
        "ground_only_preserved": spec["preserve_ground_only"],
        "semantics": "Retained authored ToonBased/MatCap diffuse and original GGX/Alpha, modulated by bounded combined real illumination; not full Ray or isolated shadow visibility",
        "rendered": False,
        "saved": False,
        "world_camera_actors_actions_geometry_compositor_changed": False,
    }
    for material, output, focused, choice, emission, ggx, authored in plans:
        tree, records = material.node_tree, []
        override = spec["material_overrides"].get(material.name, {})
        if set(override) - {"diffuse_tint", "matcap_relative_gain"}:
            raise ValueError("Unsupported daylight material override")
        probe = _node(tree, "ShaderNodeBsdfDiffuse", "white illumination probe")
        probe.inputs["Color"].default_value = (1, 1, 1, 1)
        if focused.inputs["Normal"].is_linked:
            tree.links.new(_source(focused.inputs["Normal"]), probe.inputs["Normal"])
        rgb = _node(tree, "ShaderNodeShaderToRGB", "combined real illumination")
        tree.links.new(probe.outputs[0], rgb.inputs[0])
        gray = _node(tree, "ShaderNodeRGBToBW", "combined illumination luma")
        tree.links.new(rgb.outputs[0], gray.inputs[0])
        response = _node(tree, "ShaderNodeMapRange", "bounded daylight response")
        response.clamp, response.interpolation_type = True, "SMOOTHSTEP"
        tree.links.new(gray.outputs[0], response.inputs["Value"])
        for key, value in zip(
            ("From Min", "From Max", "To Min", "To Max"),
            spec["diffuse_response_range"] + spec["diffuse_response_output"],
        ):
            response.inputs[key].default_value = value
        diffuse = _multiply(
            tree,
            authored,
            response.outputs["Result"],
            "authored diffuse times response",
        )
        diffuse = _multiply(
            tree,
            diffuse,
            override.get("diffuse_tint", spec["diffuse_tint"]),
            "blue violet diffuse tint",
        )
        _record_change(tree, emission.inputs["Color"], diffuse, records)
        matcap = tree.nodes.get("Reference | masked additive MatCap")
        if matcap:
            amount = _node(tree, "ShaderNodeMath", "relative authored MatCap gain")
            amount.operation = "MULTIPLY"
            _plug(tree, _source(matcap.inputs[0]), amount.inputs[0])
            amount.inputs[1].default_value = override.get(
                "matcap_relative_gain", spec["matcap_relative_gain"]
            )
            _record_change(tree, matcap.inputs[0], amount.outputs[0], records)
        control = _node(tree, "ShaderNodeValue", "gain")
        control.outputs[0].default_value = gain
        selected = _node(
            tree, "ShaderNodeMixShader", "Focused PBR or authored daylight"
        )
        tree.links.new(control.outputs[0], selected.inputs[0])
        tree.links.new(focused.outputs[0], selected.inputs[1])
        tree.links.new(choice.outputs[0], selected.inputs[2])
        _record_change(tree, output.inputs["Surface"], selected.outputs[0], records)
        state = {"targets": records, "gain_node": control.name}
        material[STATE] = json.dumps(state, ensure_ascii=False)
        report["materials"].append(
            {
                "material": material.name,
                "changes": state,
                "restored_GGX": ggx.name,
                "retained_authored_color": _descriptor(authored),
                "MatCap_restored": matcap is not None,
                "old_Quality_scalar_attenuation_bypassed": True,
            }
        )
    if spec["lights"]["enabled"]:
        report["lighting"] = _lights(scene, spec["lights"], gain)
    set_gain(scene, gain)
    json.dumps(report, ensure_ascii=False, allow_nan=False)
    return report
