"""Capture actual Goo node parameters in an empty process; never open production."""

import json
import sys
from pathlib import Path

import bpy

OUT = Path("D:/codex/output/Goo-Basics-Study-2026-11-17")
OUT.mkdir(parents=True, exist_ok=True)
# Use the proven local extra-node registry to avoid guessing registration identifiers.
matrix = json.loads(
    Path(
        "D:/codex/output/Goo-MME-Feature-Study-2026-11-16/feature-matrix.json"
    ).read_text(encoding="utf-8")
)
TYPES = sorted(matrix["additional_nodes"])


def value(item):
    if isinstance(item, (bool, str, int)) or item is None:
        return item
    if isinstance(item, float):
        return item if abs(item) < 1e35 else str(item)
    if isinstance(item, bpy.types.ID):
        return {"name": item.name, "type": item.bl_rna.identifier}
    try:
        return [value(x) for x in item]
    except TypeError:
        return str(item)


def prop_info(obj, prop):
    result = {"type": prop.type, "label": prop.name, "description": prop.description}
    if prop.type == "ENUM":
        result["items"] = [
            {"id": p.identifier, "label": p.name, "description": p.description}
            for p in prop.enum_items
        ]
    for field in ("hard_min", "hard_max", "soft_min", "soft_max", "unit", "subtype"):
        if hasattr(prop, field):
            result[field] = value(getattr(prop, field))
    if prop.type not in {"POINTER", "COLLECTION"}:
        try:
            result["default_observed"] = value(getattr(obj, prop.identifier))
        except (AttributeError, TypeError):
            pass
    return result


def socket_info(socket):
    result = {
        "name": socket.name,
        "identifier": socket.identifier,
        "type": socket.bl_idname,
        "hidden": socket.hide,
        "enabled": socket.enabled,
    }
    if hasattr(socket, "default_value"):
        result["default_observed"] = value(socket.default_value)
        result["value_rna"] = prop_info(
            socket, socket.bl_rna.properties["default_value"]
        )
    return result


mat = bpy.data.materials.new("Goo basics inventory only")
mat.use_nodes = True
base = set(bpy.types.ShaderNode.bl_rna.properties.keys())
nodes = {}
for name in TYPES:
    n = mat.node_tree.nodes.new(name)
    props = {
        p.identifier: prop_info(n, p)
        for p in n.bl_rna.properties
        if not p.is_readonly and p.identifier not in base
    }
    variants = {}
    for key, spec in props.items():
        if spec["type"] != "ENUM":
            continue
        original = getattr(n, key)
        rows = []
        for item in spec["items"]:
            try:
                setattr(n, key, item["id"])
                rows.append(
                    {
                        "value": item["id"],
                        "active_inputs": [
                            s.name for s in n.inputs if s.enabled and not s.hide
                        ],
                    }
                )
            except (TypeError, ValueError):
                pass
        setattr(n, key, original)
        variants[key] = rows
    nodes[name] = {
        "label": n.bl_label,
        "description": n.bl_description,
        "inputs": [socket_info(s) for s in n.inputs],
        "outputs": [socket_info(s) for s in n.outputs],
        "properties": props,
        "enum_socket_variants": variants,
    }
    if hasattr(n, "color_ramp"):
        ramp = n.color_ramp
        nodes[name]["ramp_settings"] = {
            "color_mode": ramp.color_mode,
            "interpolation": ramp.interpolation,
            "hue_interpolation": ramp.hue_interpolation,
            "elements": [
                {"position": e.position, "color": list(e.color)} for e in ramp.elements
            ],
        }
    mat.node_tree.nodes.remove(n)

settings = {}
for label, obj, words in (
    (
        "material",
        mat,
        ("light_group", "shadow_id", "surface_render_method", "backface", "raytrace"),
    ),
    ("eevee", bpy.context.scene.eevee, ("shadow", "ray_tracing", "taa", "samples")),
    (
        "light",
        bpy.data.lights.new("Inventory light", "AREA"),
        (
            "light_group",
            "energy",
            "color",
            "diffuse_factor",
            "specular_factor",
            "use_shadow",
            "size",
        ),
    ),
):
    settings[label] = {
        p.identifier: prop_info(obj, p)
        for p in obj.bl_rna.properties
        if any(w in p.identifier for w in words)
    }

report = {
    "binary": bpy.app.binary_path,
    "version": bpy.app.version_string,
    "build_hash": bpy.app.build_hash.decode(),
    "production_loaded": False,
    "preferences_saved": False,
    "rendered": False,
    "node_count": len(nodes),
    "nodes": nodes,
    "settings": settings,
    "limits": "Observed defaults and one-enum-at-a-time sockets; not all combinations or visual behavior verified",
}
filename = (
    sys.argv[sys.argv.index("--") + 1]
    if "--" in sys.argv
    else "parameter-inventory.json"
)
assert Path(filename).name == filename and filename.endswith(".json")
target = OUT / filename
with target.open("x", encoding="utf-8") as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
print(
    json.dumps(
        {
            k: report[k]
            for k in ("version", "build_hash", "node_count", "production_loaded")
        }
    ),
    flush=True,
)
