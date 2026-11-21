"""Read camera, lighting and motion controls without modifying the source file."""

import json
import sys
from pathlib import Path

import bpy


def props(data):
    names = [p.identifier for p in data.bl_rna.properties]
    return {
        n: str(getattr(data, n))
        for n in names
        if any(k in n for k in ("motion", "dof", "bokeh", "jitter"))
    }


scene = bpy.context.scene
report = {
    "render": props(scene.render),
    "eevee": props(scene.eevee),
    "camera": {},
    "lights": [],
}
for frame in (4140, 4200, 4290, 4439):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    camera = scene.camera
    heads = {}
    for arm in scene.objects:
        if arm.type == "ARMATURE" and arm.get("performer_id"):
            bone = next(b for b in arm.pose.bones if b.mmd_bone.name_j == "頭")
            point = arm.matrix_world @ bone.matrix.translation
            heads[arm["performer_id"]] = list(point)
    report["camera"][frame] = {
        "name": camera.name,
        "location": list(camera.matrix_world.translation),
        "lens": camera.data.lens,
        "sensor_width": camera.data.sensor_width,
        "dof": {
            p.identifier: str(getattr(camera.data.dof, p.identifier))
            for p in camera.data.dof.bl_rna.properties
        },
        "heads": heads,
    }
for obj in scene.objects:
    if obj.type == "LIGHT":
        report["lights"].append(
            {
                "name": obj.name,
                "position": list(obj.matrix_world.translation),
                "type": obj.data.type,
                "watts": obj.data.energy,
                "color": list(obj.data.color),
                "hidden": obj.hide_render,
            }
        )
report["compositor"] = [
    {"name": n.name, "type": n.type} for n in scene.compositing_node_group.nodes
]
report["materials"] = [
    {"name": m.name, "stage": m.get("stage_id"), "actor": m.get("performer_id")}
    for m in bpy.data.materials
    if m.node_tree
]
out = Path(sys.argv[sys.argv.index("--") + 1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("CINEMA_SCENE_PROBE_COMPLETE", flush=True)
