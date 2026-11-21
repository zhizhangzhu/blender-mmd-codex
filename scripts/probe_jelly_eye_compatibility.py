"""Exercise the user's privately cached add-on without installing preferences."""

import argparse
import hashlib
import json
import sys
import traceback
from pathlib import Path

import bpy


def coordinates(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = [tuple(vertex.co) for vertex in mesh.vertices]
    evaluated.to_mesh_clear()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--reopen", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    root = Path("D:/codex/temp/jelly-eye-study-v1")
    sys.path.insert(0, str(root))
    import jelly_eye_pro as addon

    output = Path("D:/codex/output/MMD-Jelly-Eyes-v1/study")
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "runtime": bpy.app.version_string,
        "build": bpy.app.build_hash.decode(),
        "label": args.label,
        "installed": False,
        "reopen": args.reopen,
    }
    try:
        addon.register()
        report["registration"] = True
        saved = root / (args.label + ".blend")
        if args.reopen:
            bpy.ops.wm.open_mainfile(filepath=str(saved))
            expected = json.loads((output / (args.label + ".json")).read_text())
        else:
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.object.delete(use_global=False)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12)
            obj = bpy.context.object
            obj.name = "Eye"
            obj.shape_key_add(name="Basis")
            blink = obj.shape_key_add(name="blink")
            for vertex in blink.data:
                vertex.co.z *= 0.8
            for frame, value in ((1, 0), (8, 0), (12, 1), (16, 0), (48, 0)):
                blink.value = value
                blink.keyframe_insert("value", frame=frame)
            scene = bpy.context.scene
            scene.render.fps = 60
            scene.frame_start, scene.frame_end = 1, 48
            settings = scene.jelly_eye
            settings.auto_detect = False
            settings.force_selected = True
            settings.blink_obj, settings.blink_key = obj, "blink"
            settings.bake_start, settings.bake_end = 1, 48
            report["setup"] = addon.core.setup(bpy.context, [obj])
            report["bake_info"] = settings.bake_info
            report["nodes"] = len(
                bpy.data.node_groups[addon.nodes.NODE_GROUP_NAME].nodes
            )
        obj = bpy.data.objects["Eye"]
        report["samples"] = []
        for frame in (1, 12, 16, 20, 30, 48):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            on = coordinates(obj)
            mods = [m for m in obj.modifiers if m.type == "NODES"]
            for mod in mods:
                mod.show_viewport = False
            bpy.context.view_layer.update()
            off = coordinates(obj)
            for mod in mods:
                mod.show_viewport = True
            bpy.context.view_layer.update()
            delta = max(
                sum((a - b) ** 2 for a, b in zip(x, y)) ** 0.5 for x, y in zip(on, off)
            )
            report["samples"].append(
                {
                    "frame": frame,
                    "max_delta": delta,
                    "geometry_sha256": hashlib.sha256(repr(on).encode()).hexdigest(),
                }
            )
        assert max(x["max_delta"] for x in report["samples"]) > 0.001
        report["geometry_evaluation"] = True
        if args.reopen:
            report["identical_after_reopen"] = report["samples"] == expected["samples"]
            assert report["identical_after_reopen"]
        else:
            bpy.ops.wm.save_as_mainfile(filepath=str(saved))
        addon.unregister()
        report["unregistration"] = True
        report["passed"] = True
    except Exception:  # noqa: BLE001 - persist the compatibility failure before exiting
        report["error"] = traceback.format_exc()
        report["passed"] = False
    suffix = "-reopen" if args.reopen else ""
    (output / (args.label + suffix + ".json")).write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("JELLY_COMPAT", json.dumps(report), flush=True)
    if not report["passed"]:
        raise RuntimeError(report["error"])


if __name__ == "__main__":
    main()
