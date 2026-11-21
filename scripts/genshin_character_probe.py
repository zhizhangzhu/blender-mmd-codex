"""Inventory actual duet material inputs before adapting game-style shading."""

import json
import sys
from pathlib import Path

import bpy

out = Path(sys.argv[sys.argv.index("--") + 1])
out.mkdir(parents=True, exist_ok=False)
scene = bpy.context.scene
scene.frame_set(4200)
materials = []
for mat in bpy.data.materials:
    actor = mat.get("performer_id")
    if not actor or not mat.node_tree:
        continue
    tree = mat.node_tree
    base = tree.nodes.get("mmd_base_tex")
    item = {
        "name": mat.name,
        "actor": actor,
        "source_name": mat.get("source_mmd_material_name"),
        "category": mat.get("look_category"),
        "aether_surface": mat.get("aether_surface"),
        "base_image": base.image.name if base and base.image else None,
        "base_image_path": base.image.filepath if base and base.image else None,
        "nodes": [],
    }
    for n in tree.nodes:
        if any(
            w in n.name
            for w in [
                "light response",
                "toon bands",
                "chroma",
                "eye",
                "face",
                "head",
                "key",
                "light",
                "crease",
                "ink",
                "sheen",
                "band",
                "balance",
            ]
        ):
            item["nodes"].append(
                {
                    "name": n.name,
                    "type": n.bl_idname,
                    "inputs": [
                        {
                            "name": s.name,
                            "value": list(s.default_value)
                            if hasattr(getattr(s, "default_value", None), "__len__")
                            and not isinstance(s.default_value, str)
                            else getattr(s, "default_value", None),
                            "linked": s.is_linked,
                        }
                        for s in n.inputs
                        if hasattr(s, "default_value")
                    ],
                }
            )
    materials.append(item)
objects = []
for o in scene.objects:
    item = {
        "name": o.name,
        "type": o.type,
        "actor": o.get("performer_id"),
        "parent": o.parent.name if o.parent else None,
        "hide_render": o.hide_render,
        "location": list(o.location),
    }
    if o.type == "ARMATURE":
        item["heads"] = [
            {
                "name": b.name,
                "japanese": b.mmd_bone.name_j,
                "head": list(b.bone.head_local),
                "tail": list(b.bone.tail_local),
                "matrix": [list(row) for row in b.bone.matrix_local],
            }
            for b in o.pose.bones
            if b.mmd_bone.name_j == "頭"
        ]
    if (
        o.type == "MESH"
        and o.get("performer_id")
        and any(m.type == "ARMATURE" for m in o.modifiers)
    ):
        counts = {}
        for f in o.data.polygons:
            mat = o.data.materials[f.material_index]
            counts[mat.name] = counts.get(mat.name, 0) + 1
        item["polygons"] = counts
        item["uv_layers"] = [u.name for u in o.data.uv_layers]
    objects.append(item)
report = {
    "source": bpy.data.filepath,
    "materials": materials,
    "objects": objects,
    "camera": scene.camera.name,
    "world": scene.world.name,
    "view_transform": scene.view_settings.view_transform,
    "frame_range": [scene.frame_start, scene.frame_end],
    "fps": scene.render.fps,
}
(out / "probe.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
for m in materials:
    print(
        "ACTOR_MATERIAL",
        m["actor"],
        m["name"],
        m["source_name"],
        m["category"],
        m["aether_surface"],
        m["base_image"],
        flush=True,
    )
print(
    "STAGE_ROOTS",
    [
        (o["name"], o["location"])
        for o in objects
        if o["type"] == "EMPTY"
        and any(w in o["name"] for w in ["Hall", "Hesperides", "head"])
    ],
    flush=True,
)
