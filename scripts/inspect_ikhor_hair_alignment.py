import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

register_addons()
bpy.ops.wm.open_mainfile(
    filepath="D:/codex/output/MMD-Jelly-Eyes-v1/production-v16/Franken_Duet_Goo_Eye_Hair_Stage.blend",
    use_scripts=False,
)
obj = bpy.data.objects["Ikhor | mesh | Ikhor_mesh"]
arm = obj.find_armature()
ids = {
    i
    for p in obj.data.polygons
    if obj.data.materials[p.material_index].name == "鬓.001"
    for i in p.vertices
}
weights = {}
for i in ids:
    for g in obj.data.vertices[i].groups:
        name = obj.vertex_groups[g.group].name
        weights[name] = weights.get(name, 0) + g.weight
print("MODS", [(m.name, m.type) for m in obj.modifiers], flush=True)
print(
    "HEAD",
    [
        (b.name, b.parent.name if b.parent else None)
        for b in arm.data.bones
        if b.name in ("頭", "首")
    ],
    flush=True,
)
for f in (4140, 4290, 4438):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    for name, weight in sorted(weights.items(), key=lambda x: -x[1]):
        b = arm.pose.bones.get(name)
        if b is None:
            continue
        expected = (
            arm.pose.bones["頭"].matrix
            @ arm.data.bones["頭"].matrix_local.inverted()
            @ b.bone.matrix_local
        )
        print(
            "HAIR",
            f,
            name,
            "parent",
            b.parent.name if b.parent else "",
            "w",
            round(weight, 1),
            "local",
            list(b.location),
            "delta_head",
            (b.matrix.translation - expected.translation).length,
            "constraints",
            [(c.name, c.type) for c in b.constraints],
            flush=True,
        )
