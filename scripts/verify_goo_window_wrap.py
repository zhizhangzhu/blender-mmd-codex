"""Independently reopen the saved window-wrap master; no output-video QA."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from snapshot_goo_scene import capture

ROOT = Path("D:/codex/output/MMD-Goo-Window-Wrap-v1")
prep = json.loads((ROOT / "production-v3/preparation.json").read_text(encoding="utf-8"))
project = Path(prep["project"])
assert hashlib.sha256(project.read_bytes()).hexdigest() == prep["project_sha256"]
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(project), load_ui=False, use_scripts=False)
after = json.loads(json.dumps(capture()))
before = json.loads(
    Path("D:/codex/temp/MME-Deep-Study-2026-11-16/goo-v2-snapshot.json").read_text(
        encoding="utf-8"
    )
)
scene = bpy.context.scene
tree = scene.compositing_node_group
output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
checks = {
    "actions": before["actions"] == after["actions"],
    "original_meshes": all(
        after["geometry"].get(k) == v for k, v in before["geometry"].items()
    ),
    "images_and_packing": before["images"] == after["images"],
    "five_poses_morphs_cameras": before["samples"] == after["samples"],
    "fps": before["fps"] == after["fps"],
    "original_objects_retained": set(before["objects"]) <= set(after["objects"]),
    "rejected_cones_and_slats_hidden": all(
        scene.objects[name].hide_render
        for name in prep["changes"]["hidden_narrow_shafts"]
    ),
    "beauty_cache_matches_final": output.inputs["Image"].links[0].from_socket
    == tree.nodes["Caption cache | beauty"].inputs["beauty"].links[0].from_socket,
    "real_rim_aov_available": any(
        aov.name == "WindowWrapRim" and aov.type == "COLOR"
        for aov in bpy.context.view_layer.aovs
    ),
    "volume_shadows": scene.eevee.use_volumetric_shadows,
}
report = {
    "project": str(project),
    "project_sha256": prep["project_sha256"],
    "checks": checks,
    "passed": all(checks.values()),
    "scope": "Saved-master original geometry/motion comparison, five time samples, hidden old cones and final caption routing; not video or visual-quality certification",
}
with (ROOT / "master-verification-v3.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
assert report["passed"]
