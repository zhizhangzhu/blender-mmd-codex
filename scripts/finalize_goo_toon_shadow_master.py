"""Relocate the baked shadow sequences without Blender remapping them to the source folder."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from prepare_goo_eye_hair_stage import PREFIX, ROOT

register_addons()
old = ROOT / "production-v12/Franken_Duet_Goo_Eye_Hair_Stage.blend"
production = ROOT / "production-v13"
production.mkdir(exist_ok=False)
shutil.copytree(old.parent / "hair-shadows", production / "hair-shadows")
shutil.copy2(
    old.parent / "hair-shadow-manifest.json", production / "hair-shadow-manifest.json"
)
bpy.ops.wm.open_mainfile(filepath=str(old), load_ui=False, use_scripts=False)
for actor, face in (("aksiniya", "颜"), ("ikhor", "颜.001")):
    tex = bpy.data.materials[face].node_tree.nodes[
        PREFIX + "geometry derived hair shadow"
    ]
    print(
        "BEFORE_SEQUENCE",
        actor,
        tex.image.source,
        tex.image.filepath,
        tex.image_user.frame_start,
        tex.image_user.frame_duration,
        flush=True,
    )
    tex.image.filepath = f"//hair-shadows/{actor}_0001.png"
    tex.image_user.frame_start = 4140
    tex.image_user.frame_duration = 300
    tex.image_user.frame_offset = 0
    tex.image_user.use_auto_refresh = True
project = production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
bpy.context.scene.frame_set(4290)
bpy.ops.wm.save_as_mainfile(filepath=str(project), relative_remap=False)
prep = json.loads((old.parent / "preparation.json").read_text(encoding="utf-8"))
prep.update(
    source=str(old),
    source_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
    project=str(project),
    project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
)
(production / "preparation.json").write_text(
    json.dumps(prep, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("TOON_SHADOW_PORTABLE_MASTER", flush=True)
