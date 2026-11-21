"""Independently reopen the master and compare original motion/geometry, never video QA."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from snapshot_goo_scene import capture

ROOT = Path("D:/codex/output/MMD-Goo-Tyndall-Rim-v1")
prep = json.loads((ROOT / "production-v7/preparation.json").read_text(encoding="utf-8"))
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
checks = {
    "actions": before["actions"] == after["actions"],
    "original_mesh_coordinates": all(
        after["geometry"].get(k) == v for k, v in before["geometry"].items()
    ),
    "images_and_packing": before["images"] == after["images"],
    "five_sampled_poses_morphs_cameras": before["samples"] == after["samples"],
    "fps": before["fps"] == after["fps"],
    "original_objects_retained": set(before["objects"]) <= set(after["objects"]),
}
scene = bpy.context.scene
tree = scene.compositing_node_group
output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
checks["caption_beauty_matches_final_tonemapped_image"] = (
    output.inputs["Image"].links[0].from_socket
    == tree.nodes["Caption cache | beauty"].inputs["beauty"].links[0].from_socket
)
checks["volume_shadows_enabled"] = scene.eevee.use_volumetric_shadows
checks["new_volume_no_emission"] = not any(
    n.type in ("EMISSION", "PRINCIPLED_VOLUME")
    for n in bpy.data.materials[
        "Goo Tyndall | bounded scattering with feathered edges"
    ].node_tree.nodes
)
report = {
    "project": str(project),
    "project_sha256": prep["project_sha256"],
    "checks": checks,
    "image_differences": {
        "added_or_changed": [x for x in after["images"] if x not in before["images"]],
        "missing_or_changed": [x for x in before["images"] if x not in after["images"]],
    },
    "passed": all(checks.values()),
    "new_objects": sorted(set(after["objects"]) - set(before["objects"])),
    "scope": "Independent saved-master structural and five-time pose comparison; no video decode or art certification",
}
with (ROOT / "master-preservation-v2.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
assert report["passed"]
