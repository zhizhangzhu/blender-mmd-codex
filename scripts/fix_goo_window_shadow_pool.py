"""Increase the inherited full shadow pool; keep the revision's art graph unchanged."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

ROOT = Path("D:/codex/output/MMD-Goo-Window-Wrap-v1")
source = ROOT / "production-v1/Franken_Duet_Goo_Window_Wrap.blend"
prep = json.loads((source.parent / "preparation.json").read_text(encoding="utf-8"))
assert hashlib.sha256(source.read_bytes()).hexdigest() == prep["project_sha256"]
register_addons()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
scene = bpy.context.scene
mute_file_outputs()
production = ROOT / "production-v3"
production.mkdir(exist_ok=False)
old = scene.eevee.shadow_pool_size
scene.eevee.shadow_pool_size = "2048"
shadow_limits = []
for name, limit in (
    ("Goo window wrap | parallel window daylight", 0.005),
    ("Goo window wrap | large window 0", 0.01),
    ("Goo window wrap | large window 1", 0.01),
):
    data = scene.objects[name].data
    previous = data.shadow_maximum_resolution
    data.shadow_maximum_resolution = max(previous, limit)
    shadow_limits.append(
        {
            "light": name,
            "before": previous,
            "after": data.shadow_maximum_resolution,
            "use_shadow": data.use_shadow,
        }
    )
scene.frame_set(4290)
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 24
project = production / "Franken_Duet_Goo_Window_Wrap.blend"
scene.render.filepath = str(production / "portrait-4290.png")
bpy.ops.wm.save_as_mainfile(filepath=str(project))
report = {
    **prep,
    "source": str(source),
    "source_sha256": prep["project_sha256"],
    "project": str(project),
    "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
    "original_tyndall_source_sha256": prep["source_sha256"],
    "shadow_pool": {
        "before": old,
        "after": scene.eevee.shadow_pool_size,
        "resolution_limits": shadow_limits,
        "reason": "Actual render log Shadow buffer full, 6600-7700+ pages requested for6144; raise pool and bound broad window shadow texel precision; actor key lamps and art graph unchanged",
        "abandoned_partial_frames": 67,
    },
}
(production / "preparation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("SHADOW_POOL_REVISED", old, scene.eevee.shadow_pool_size, flush=True)
for frame, label in ((4290, "portrait"), (4140, "opening")):
    scene.frame_set(frame)
    scene.render.filepath = str(production / f"{label}-{frame}.png")
    bpy.ops.render.render(write_still=True)
    print("WINDOW_WRAP_NATIVE_PREFLIGHT", frame, flush=True)
