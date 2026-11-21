"""Read the fixed current Goo still before making isolated look-development copies."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import graph, mute_file_outputs, plain
from snapshot_goo_scene import capture

SOURCE = Path(
    "D:/codex/output/MMD-MME-Reference-Light-v1/production-v6/Franken_MME_Balanced_Light_Still.blend"
)
EXPECTED = "65766b3befc9031f5c27efb25f91b1516cd2a0cd195b4ea98125bab93c07bf7a"
OUT = Path("D:/codex/temp/Goo-Character-Lookdev-2026-11-18/inspection")


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
    OUT.mkdir(parents=True, exist_ok=False)
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), use_scripts=False, load_ui=False)
    muted = mute_file_outputs()
    baseline = capture()
    (OUT / "baseline.json").write_text(
        json.dumps(baseline, ensure_ascii=False), encoding="utf-8"
    )
    scene = bpy.context.scene
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    mats = {}
    for m in bpy.data.materials:
        if m.get("performer_id") not in ("ikhor", "aksiniya"):
            continue
        mats[m.name] = {"properties": dict(m.items()), "graph": graph(m.node_tree)}
        for n in m.node_tree.nodes if m.node_tree else []:
            if n.bl_idname == "ShaderNodeShaderInfo":
                mats[m.name].setdefault("shader_info", []).append(
                    {
                        "name": n.name,
                        "properties": {
                            p.identifier: plain(getattr(n, p.identifier))
                            for p in n.bl_rna.properties
                            if not p.is_readonly
                            and p.identifier
                            not in (
                                "rna_type",
                                "parent",
                                "texture_mapping",
                                "color_mapping",
                            )
                        },
                    }
                )
    objects = []
    for o in scene.objects:
        if o.type == "LIGHT":
            objects.append(
                {
                    "name": o.name,
                    "type": o.type,
                    "matrix": plain(o.matrix_world),
                    "hidden": o.hide_render,
                    "data": {
                        k: plain(getattr(o.data, k))
                        for k in (
                            "type",
                            "energy",
                            "color",
                            "diffuse_factor",
                            "specular_factor",
                            "volume_factor",
                            "use_shadow",
                        )
                    },
                    "size": getattr(o.data, "size", None),
                    "groups": [g.name for g in o.data.light_groups.groups],
                    "receivers": plain(o.light_linking.receiver_collection),
                }
            )
        elif o.type == "ARMATURE":
            ad = o.animation_data
            objects.append(
                {
                    "name": o.name,
                    "type": o.type,
                    "action": ad.action.name if ad and ad.action else None,
                    "slot": str(ad.action_slot) if ad else None,
                    "bones": [
                        {
                            "name": b.name,
                            "head": plain(b.head),
                            "tail": plain(b.tail),
                            "matrix": plain(b.matrix),
                            "parent": b.parent.name if b.parent else None,
                            "constraints": [
                                {
                                    "type": c.type,
                                    "name": c.name,
                                    "mute": c.mute,
                                    "influence": c.influence,
                                }
                                for c in b.constraints
                            ],
                        }
                        for b in o.pose.bones
                    ],
                }
            )
        elif o.type == "MESH" and any(
            m and m.get("performer_id") in ("aksiniya", "ikhor")
            for m in o.data.materials
        ):
            regions = []
            for i, m in enumerate(o.data.materials):
                ids = {
                    v
                    for p in o.data.polygons
                    if p.material_index == i
                    for v in p.vertices
                }
                if not ids:
                    continue
                coords = [o.data.vertices[v].co for v in ids]
                regions.append(
                    {
                        "slot": i,
                        "material": m.name if m else None,
                        "vertices": len(ids),
                        "min": [min(c[a] for c in coords) for a in range(3)],
                        "max": [max(c[a] for c in coords) for a in range(3)],
                    }
                )
            objects.append(
                {
                    "name": o.name,
                    "type": o.type,
                    "matrix": plain(o.matrix_world),
                    "parent": plain(o.parent),
                    "modifiers": [
                        {
                            "name": m.name,
                            "type": m.type,
                            "viewport": m.show_viewport,
                            "render": m.show_render,
                            "object": plain(getattr(m, "object", None)),
                            "vertex_group": getattr(m, "vertex_group", ""),
                        }
                        for m in o.modifiers
                    ],
                    "regions": regions,
                    "uv": [u.name for u in o.data.uv_layers],
                    "groups": [g.name for g in o.vertex_groups],
                }
            )
    helpers = {
        o.name: {
            "matrix": plain(o.matrix_world),
            "parent": plain(o.parent),
            "bone": o.parent_bone,
        }
        for o in scene.objects
        if "Eye hair v1 | " in o.name and "eye " in o.name
    }
    data = {
        "source": str(SOURCE),
        "source_sha256": EXPECTED,
        "materials": mats,
        "objects": objects,
        "helpers": helpers,
        "compositor": graph(scene.compositing_node_group),
        "world": graph(scene.world.node_tree),
        "view": {
            k: plain(getattr(scene.view_settings, k))
            for k in ("view_transform", "look", "exposure", "gamma")
        },
        "camera": {
            "name": scene.camera.name,
            "lens": scene.camera.data.lens,
            "matrix": plain(scene.camera.matrix_world),
            "dof": scene.camera.data.dof.use_dof,
        },
        "muted_outputs": muted,
    }
    (OUT / "inventory.json").write_text(
        json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print("LOOKDEV_INSPECTION_COMPLETE", OUT, flush=True)


if __name__ == "__main__":
    main()
