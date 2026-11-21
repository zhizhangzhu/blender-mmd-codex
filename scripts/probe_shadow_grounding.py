"""Read actual light, material, foot and floor data before grounding changes."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

scene = bpy.context.scene
actors = [o for o in scene.objects if o.type == "ARMATURE" and o.get("performer_id")]
hidden = []
for obj in scene.objects:
    volume = obj.type == "MESH" and any(
        m
        and m.node_tree
        and any(
            n.type == "OUTPUT_MATERIAL"
            and n.inputs["Volume"].is_linked
            and not n.inputs["Surface"].is_linked
            for n in m.node_tree.nodes
        )
        for m in obj.data.materials
    )
    if obj.hide_render or (obj.type == "MESH" and obj.get("performer_id")) or volume:
        hidden.append((obj, obj.hide_get()))
        obj.hide_set(True)
samples = []
for number in (4140, 4200, 4250, 4290, 4439):
    scene.frame_set(number)
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    for arm in actors:
        for bone in arm.pose.bones:
            if bone.mmd_bone.name_j not in {"左足首", "右足首", "左つま先", "右つま先"}:
                continue
            point = arm.matrix_world @ bone.matrix.translation
            ok, hit, normal, face, ground, _ = scene.ray_cast(
                graph, point + Vector((0, 0, 0.5)), Vector((0, 0, -1)), distance=10
            )
            samples.append(
                {
                    "frame": number,
                    "actor": arm["performer_id"],
                    "bone": bone.mmd_bone.name_j,
                    "point": list(point),
                    "floor": list(hit) if ok else None,
                    "object": ground.name if ok else None,
                }
            )
for obj, value in hidden:
    obj.hide_set(value)
lights = []
for obj in scene.objects:
    if obj.type != "LIGHT" or obj.hide_render:
        continue
    properties = {
        p.identifier: str(getattr(obj.data, p.identifier))
        for p in obj.data.bl_rna.properties
        if "shadow" in p.identifier
    }
    lights.append(
        {
            "name": obj.name,
            "type": obj.data.type,
            "position": list(obj.location),
            "watts": obj.data.energy,
            "size": getattr(obj.data, "size", None),
            "radius": getattr(obj.data, "shadow_soft_size", None),
            "receivers": obj.light_linking.receiver_collection.name
            if obj.light_linking.receiver_collection
            else None,
            "blockers": obj.light_linking.blocker_collection.name
            if obj.light_linking.blocker_collection
            else None,
            "shadow": properties,
        }
    )
materials = []
for material in bpy.data.materials:
    if not material.node_tree:
        continue
    response = material.node_tree.nodes.get("Quality | bounded real illumination")
    if response and material.get("performer_id"):
        materials.append(
            {
                "name": material.name,
                "actor": material.get("performer_id"),
                "source_name": material.get("source_mmd_material_name"),
                "response": {
                    s.name: s.default_value
                    for s in response.inputs
                    if s.name in {"From Min", "From Max", "To Min", "To Max"}
                    and s.type == "VALUE"
                },
                "ao_distance": material.node_tree.nodes["Quality | short-range contact"]
                .inputs["Distance"]
                .default_value,
            }
        )
report = {
    "project": bpy.data.filepath,
    "feet": samples,
    "lights": lights,
    "actor_response": materials,
    "eevee_shadows": {
        p.identifier: str(getattr(scene.eevee, p.identifier))
        for p in scene.eevee.bl_rna.properties
        if "shadow" in p.identifier
    },
}
output = Path(sys.argv[sys.argv.index("--") + 1])
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("SHADOW_GROUNDING_PROBED", flush=True)
