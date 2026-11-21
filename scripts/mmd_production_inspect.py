"""Print production-relevant material, rig, and physics facts inside Blender."""

import bpy
import json
from collections import Counter

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [
    o
    for o in bpy.data.objects
    if o.type == "MESH"
    and getattr(o, "mmd_type", "NONE") == "NONE"
    and any(m.type == "ARMATURE" for m in o.modifiers)
]
materials = []
for obj in meshes:
    counts = Counter(p.material_index for p in obj.data.polygons)
    for i, mat in enumerate(obj.data.materials):
        if not mat:
            continue
        materials.append(
            {
                "slot": i,
                "name": mat.name,
                "faces": counts[i],
                "diffuse": list(mat.diffuse_color),
                "mmd_diffuse": list(mat.mmd_material.diffuse_color),
                "mmd_alpha": mat.mmd_material.alpha,
                "textures": [
                    {"node": n.name, "image": n.image.name if n.image else None}
                    for n in mat.node_tree.nodes
                    if n.type == "TEX_IMAGE"
                ],
                "nodes": [(n.name, n.bl_idname) for n in mat.node_tree.nodes],
            }
        )
rigids = [o for o in bpy.data.objects if getattr(o, "mmd_type", "NONE") == "RIGID_BODY"]
joints = [o for o in bpy.data.objects if getattr(o, "mmd_type", "NONE") == "JOINT"]
physics = [
    {
        "name": o.name,
        "bone": o.mmd_rigid.bone,
        "type": o.mmd_rigid.type,
        "rb": o.rigid_body is not None,
        "mass": o.rigid_body.mass if o.rigid_body else None,
    }
    for o in rigids
]
report = {
    "armature": arm.name,
    "root": arm.parent.name,
    "materials": materials,
    "rigid_count": len(rigids),
    "joint_count": len(joints),
    "physics_types": dict(Counter(p["type"] for p in physics)),
    "physics": physics,
    "ik": [
        {
            "bone": b.name,
            "mmd_j": b.mmd_bone.name_j,
            "constraints": [(c.name, c.type, c.influence) for c in b.constraints],
        }
        for b in arm.pose.bones
        if any(c.type == "IK" for c in b.constraints)
    ],
    "bone_names": [b.name for b in arm.pose.bones],
    "root_props": [
        (p.identifier, str(getattr(arm.parent.mmd_root, p.identifier, None)))
        for p in arm.parent.mmd_root.bl_rna.properties
        if p.type != "COLLECTION"
    ],
    "eevee_props": [p.identifier for p in bpy.context.scene.eevee.bl_rna.properties],
    "scene_compositor_props": [
        p.identifier
        for p in bpy.context.scene.bl_rna.properties
        if "compos" in p.identifier or "node" in p.identifier
    ],
}
print("PRODUCTION_INSPECT", json.dumps(report, ensure_ascii=False))
