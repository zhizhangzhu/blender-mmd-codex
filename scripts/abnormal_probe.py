"""Temporarily register a pinned Abnormal source in an isolated process."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import bpy

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
report = {
    "blender": bpy.app.version_string,
    "source": str(args.source),
    "preferences_saved": False,
    "modal_editor_tested": False,
}
try:
    spec = importlib.util.spec_from_file_location(
        "quality_abnormal",
        args.source / "__init__.py",
        submodule_search_locations=[str(args.source)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    report["bl_info"] = module.bl_info
    module.register()
    report["registered"] = True
    report["operators"] = dir(bpy.ops.abnormal)
    module.unregister()
    report["unregistered"] = True
except Exception as exc:
    report["error"] = type(exc).__name__ + ": " + str(exc)
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("x", encoding="utf-8") as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print("ABNORMAL_PROBE", json.dumps(report, ensure_ascii=False), flush=True)
