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
bpy.context.scene.frame_set(4290)
obj = bpy.data.objects["Ikhor | mesh | Ikhor_mesh"]
ids = {
    i
    for p in obj.data.polygons
    if obj.data.materials[p.material_index].name == "鬓.001"
    for i in p.vertices
}
basis = obj.data.shape_keys.key_blocks[0]
for key in obj.data.shape_keys.key_blocks:
    if abs(key.value) < 1e-6:
        continue
    delta = max((key.data[i].co - basis.data[i].co).length for i in ids)
    if delta > 1e-5:
        print("HAIR_MORPH", key.name, key.value, delta, flush=True)
print("IKHOR_ACTION", obj.find_armature().animation_data.action.name, flush=True)
