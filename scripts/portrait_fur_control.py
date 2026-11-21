"""Original Normal/key fur palette on the pinned Clean v2 Aksiniya material.

Only the exact shared neck/wrist fur material, 毛领, changes. apply(scene,
settings=None), set_gain(scene, 0..1), remove(scene). Zero physically restores
the original palette input; remove also restores the original complete graph.
The new palette multiplies the ORIGINAL MMD Color at the existing palette
application, before the one existing AO and the separate new/old rim branches.
No Color/Alpha/sphere input, texture, physical closure, geometry, Action, lamp,
compositor, preference or file is changed. This module does not save or render.

The geometric Normal dot current key direction supplies fur shape; the old
distance-compensated combined Diffuse can retain its fixed response permission.
This is not a pure cast-shadow visibility signal. No final-color floor or clamp,
new AO, copied light probe, outline or additional Emission closure is introduced.
"""

import copy
import hashlib
import json
import math
from pathlib import Path

import bpy

PREFIX = "Portrait relight | fur | "
STATE = "portrait_fur_control_state"
SOURCE_SHA256 = "0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4"
DEFAULT_SETTINGS = {
    "id": "portrait-fur-form-v1",
    "gain": 1.0,
    "verify_source_hash": True,
    "form_range": [-0.12, 0.76],
    "use_combined_response": True,
    "response_range": [0.055, 0.34],
    "palette": [
        [0.16, [0.60, 0.60, 0.75, 1.0]],
        [0.58, [0.84, 0.83, 0.94, 1.0]],
        [0.90, [1.02, 1.02, 1.02, 1.0]],
    ],
}


def _plain(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return [_plain(x) for x in value]


def _number(value, label, low=0.0, high=1.0):
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Invalid fur " + label)
    return value


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
    if tree.nodes.get(name) or len(name.encode("utf-8")) > 62:
        raise ValueError("Duplicate/overlong fur node: " + name)
    node = tree.nodes.new(kind)
    node.name = node.label = name
    return node


def _plug(tree, value, socket):
    if hasattr(value, "is_output"):
        tree.links.new(value, socket)
    else:
        socket.default_value = value


def _vector(tree, operation, first, second, label):
    node = _node(tree, "ShaderNodeVectorMath", label)
    node.operation = operation
    _plug(tree, first, node.inputs[0])
    if second is not None:
        _plug(tree, second, node.inputs[1])
    return node.outputs["Value"] if operation == "DOT_PRODUCT" else node.outputs[0]


def _smooth(tree, value, limits, label):
    node = _node(tree, "ShaderNodeMapRange", label)
    node.clamp, node.interpolation_type = True, "SMOOTHSTEP"
    _plug(tree, value, node.inputs["Value"])
    node.inputs["From Min"].default_value, node.inputs["From Max"].default_value = (
        limits
    )
    return node.outputs["Result"]


def _contract(scene):
    actor = scene.objects.get("阿克西妮娅2_mesh")
    material = bpy.data.materials.get("毛领")
    if (
        not actor
        or actor.type != "MESH"
        or actor.get("performer_id") != "aksiniya"
        or actor.hide_render
    ):
        raise ValueError("Missing exact Aksiniya visible mesh")
    if (
        not material
        or material not in actor.data.materials[:]
        or material.get("source_mmd_material_name") != "毛领"
        or material.get("character_layer_role") != "fur"
    ):
        raise ValueError("Missing audited neck/wrist fur material")
    if any(
        o.get("performer_id") != "aksiniya"
        for o in scene.objects
        if o.type == "MESH" and material in o.data.materials[:]
    ):
        raise ValueError("Fur material has a non-Aksiniya user")
    tree = material.node_tree
    required = {
        "mmd_shader": "ShaderNodeGroup",
        "Reference transfer | surface geometry": "ShaderNodeNewGeometry",
        "Reference transfer | shading bypass": "ShaderNodeMixRGB",
        "Character layers | base times one palette": "ShaderNodeMixRGB",
        "Reference transfer | key facing response": "ShaderNodeMapRange",
    }
    for name, kind in required.items():
        if not tree.nodes.get(name) or tree.nodes[name].bl_idname != kind:
            raise ValueError("Missing audited fur node: " + name)
    target = tree.nodes["Reference transfer | shading bypass"].inputs[2]
    if len(target.links) != 1:
        raise ValueError("Fur palette must have one original source")
    multiply = tree.nodes["Character layers | base times one palette"]
    chroma = tree.nodes.get("Character layers | source color and chroma")
    if (
        multiply.blend_type != "MULTIPLY"
        or not multiply.inputs[1].is_linked
        or not chroma
        or multiply.inputs[1].links[0].from_node != chroma
        or not chroma.inputs["Color"].is_linked
        or chroma.inputs["Color"].links[0].from_node.name != "mmd_shader"
    ):
        raise ValueError("Fur no longer multiplies retained MMD Color once")
    if (
        not multiply.inputs[2].is_linked
        or multiply.inputs[2].links[0].from_node.name
        != "Reference transfer | shading bypass"
    ):
        raise ValueError("Fur palette application path changed")
    response = tree.nodes["Reference transfer | key facing response"]
    if not response.inputs["Value"].is_linked:
        raise ValueError("Missing original combined response signal")
    if scene.objects.get("Reference duet | aksiniya | key") is None:
        raise ValueError("Missing actual current Aksiniya key")
    return material, target, response.inputs["Value"].links[0].from_socket


def set_gain(scene, value):
    """Zero physically reconnects the exact old palette source and default."""
    value = _number(value, "gain")
    material = bpy.data.materials.get("毛领")
    if not material or STATE not in material:
        raise ValueError("Fur control is not installed")
    tree, state = material.node_tree, json.loads(material[STATE])
    target = tree.nodes[state["target"]["node"]].inputs[state["target"]["index"]]
    original = state["original"]
    descriptor = state["final"] if value else original
    for link in list(target.links):
        tree.links.remove(link)
    target.default_value = state["original_default"]
    tree.links.new(tree.nodes[descriptor["node"]].outputs[descriptor["index"]], target)
    tree.nodes[state["gain_node"]].outputs[0].default_value = value
    state["gain"] = value
    material[STATE] = json.dumps(state, ensure_ascii=False)
    return {
        "material": material.name,
        "gain": value,
        "original_directly_connected": value == 0,
    }


def remove(scene):
    """Restore the original fur graph and remove this module's state."""
    material = bpy.data.materials.get("毛领")
    if not material or STATE not in material:
        return []
    set_gain(scene, 0)
    for node in list(material.node_tree.nodes):
        if node.name.startswith(PREFIX):
            material.node_tree.nodes.remove(node)
    del material[STATE]
    return [material.name]


def apply(scene, settings=None):
    """Install only 毛领's upstream palette; return a serializable change report."""
    spec = copy.deepcopy(DEFAULT_SETTINGS)
    for key, value in (settings or {}).items():
        if key not in spec:
            raise ValueError("Unknown fur setting: " + key)
        spec[key] = copy.deepcopy(value)
    _number(spec["gain"], "gain")
    for key in ("form_range", "response_range"):
        lo, hi = spec[key]
        _number(lo, key, -1 if key == "form_range" else 0, 8)
        _number(hi, key, -1 if key == "form_range" else 0, 8)
        if not lo < hi:
            raise ValueError("Increasing fur range required")
    positions = [point[0] for point in spec["palette"]]
    if len(positions) < 2 or positions != sorted(set(positions)):
        raise ValueError("Fur palette requires ordered unique points")
    for position, rgba in spec["palette"]:
        _number(position, "palette position")
        if len(rgba) != 4 or rgba[3] != 1:
            raise ValueError("Fur palette alpha must remain one")
        for value in rgba[:3]:
            _number(value, "linear palette multiplier", 0, 2)
    source = Path(bpy.data.filepath)
    if spec["verify_source_hash"]:
        with source.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != SOURCE_SHA256:
                raise ValueError("Fur control only accepts the pinned Clean v2 SHA")
    material, target, raw_response = _contract(scene)
    tree = material.node_tree
    if STATE in material or any(n.name.startswith(PREFIX) for n in tree.nodes):
        raise ValueError("Refusing repeated fur control installation")
    original = target.links[0].from_socket
    original_record, old_default = _descriptor(original), _plain(target.default_value)
    geometry = tree.nodes["Reference transfer | surface geometry"]
    key = scene.objects["Reference duet | aksiniya | key"]
    try:
        position = _node(tree, "ShaderNodeCombineXYZ", "current key position")
        for index in range(3):
            driver = position.inputs[index].driver_add("default_value").driver
            variable = driver.variables.new()
            variable.name, variable.type = "key_position", "TRANSFORMS"
            variable.targets[0].id = key
            variable.targets[0].transform_space = "WORLD_SPACE"
            variable.targets[0].transform_type = "LOC_" + "XYZ"[index]
            driver.expression = "key_position"
        to_key = _vector(
            tree,
            "SUBTRACT",
            position.outputs[0],
            geometry.outputs["Position"],
            "surface to actual key",
        )
        direction = _vector(tree, "NORMALIZE", to_key, None, "unit key direction")
        normal = _vector(
            tree, "NORMALIZE", geometry.outputs["Normal"], None, "unit actual normal"
        )
        no_l = _vector(tree, "DOT_PRODUCT", normal, direction, "actual Normal dot key")
        factor = _smooth(tree, no_l, spec["form_range"], "fur form permission")
        if spec["use_combined_response"]:
            response = _smooth(
                tree, raw_response, spec["response_range"], "old combined response"
            )
            product = _node(tree, "ShaderNodeMath", "form times response")
            product.operation = "MULTIPLY"
            _plug(tree, factor, product.inputs[0])
            _plug(tree, response, product.inputs[1])
            factor = product.outputs[0]
        palette = _node(tree, "ShaderNodeValToRGB", "fur linear multipliers")
        palette.color_ramp.interpolation = "EASE"
        while len(palette.color_ramp.elements) < len(spec["palette"]):
            palette.color_ramp.elements.new(0.5)
        for element, (position_value, rgba) in zip(
            palette.color_ramp.elements, spec["palette"]
        ):
            element.position, element.color = position_value, rgba
        tree.links.new(factor, palette.inputs[0])
        gain = _node(tree, "ShaderNodeValue", "gain")
        gain.outputs[0].default_value = spec["gain"]
        select = _node(tree, "ShaderNodeMixRGB", "original palette bypass")
        select.blend_type, select.use_clamp = "MIX", False
        tree.links.new(gain.outputs[0], select.inputs[0])
        tree.links.new(original, select.inputs[1])
        tree.links.new(palette.outputs[0], select.inputs[2])
        state = {
            "id": spec["id"],
            "target": _descriptor(target, False),
            "original": original_record,
            "original_default": old_default,
            "final": _descriptor(select.outputs[0]),
            "gain_node": gain.name,
            "gain": spec["gain"],
        }
        material[STATE] = json.dumps(state, ensure_ascii=False)
        set_gain(scene, spec["gain"])
    except Exception:
        for link in list(target.links):
            tree.links.remove(link)
        target.default_value = old_default
        tree.links.new(original, target)
        for node in list(tree.nodes):
            if node.name.startswith(PREFIX):
                tree.nodes.remove(node)
        if STATE in material:
            del material[STATE]
        raise
    texture = tree.nodes.get("mmd_base_tex")
    return {
        "id": spec["id"],
        "source_sha256": SOURCE_SHA256,
        "material": material.name,
        "settings": spec,
        "changes": state,
        "key_object": key.name,
        "original_mmd_color": _descriptor(tree.nodes["mmd_shader"].outputs["Color"]),
        "base_texture": texture.image.filepath if texture and texture.image else None,
        "base_image": texture.image.name if texture and texture.image else None,
        "combined_signal": _descriptor(raw_response),
        "semantics": "Current geometric Normal dot per-point actual key direction drives a linear multiplier palette, optionally times retained combined-response permission, applied once to retained MMD Color before original AO and separate rims",
        "saved": False,
        "rendered": False,
        "new_AO_or_probe_or_closure": False,
        "other_materials_geometry_actions_alpha_sphere_rim_changed": False,
        "limits": [
            "No new fur shader or mesh; existing normals are retained",
            "Combined response is not isolated shadow visibility",
            "Appearance and neck/wrist separation require rendered review",
        ],
    }
