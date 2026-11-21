"""Read installed/enabled MMD add-ons and registered APIs inside Blender.

Run with Blender --background --disable-autoexec --python-exit-code 1
--python scripts/blender_inventory.py -- --output <new-report.json>.
Omit --factory-startup to inspect saved user preferences. No preferences or
blend files are saved. Installed metadata is parsed without importing add-ons.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def addon_metadata(directory: Path) -> dict:
    """Read a manifest or literal bl_info; never execute plugin source."""
    manifest = directory / "blender_manifest.toml"
    if manifest.is_file():
        import tomllib

        with manifest.open("rb") as stream:
            data = tomllib.load(stream)
        return {key: data.get(key) for key in ("id", "name", "version", "blender_version_min", "website")}
    source = directory / "__init__.py"
    if source.is_file():
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "bl_info" for t in node.targets):
                data = ast.literal_eval(node.value)
                return {key: data.get(key) for key in ("name", "version", "blender", "description", "tracker_url")}
    return {}


def operator_inventory(bpy, namespace: str) -> list[dict]:
    result = []
    group = getattr(bpy.ops, namespace)
    for name in dir(group):
        if name.startswith("_"):
            continue
        try:
            rna = getattr(group, name).get_rna_type()
            result.append({"id": f"{namespace}.{name}", "label": rna.name,
                           "properties": [p.identifier for p in rna.properties if p.identifier != "rna_type"]})
        except (AttributeError, RuntimeError):
            continue
    return result


def collect() -> dict:
    import bpy

    enabled = set(bpy.context.preferences.addons.keys())
    installed = []
    roots = [(Path(bpy.utils.user_resource("SCRIPTS")) / "addons", "")]
    roots += [(Path(path) / "addons", "") for path in bpy.utils.script_paths()]
    for repo in bpy.context.preferences.extensions.repos:
        if repo.directory:
            roots.append((Path(repo.directory), f"bl_ext.{repo.module}."))
    seen = set()
    warnings = []
    for root, prefix in roots:
        if not root.is_dir():
            continue
        for directory in sorted(root.iterdir()):
            if not directory.is_dir() or directory.name.startswith((".", "_")):
                continue
            identity = (str(directory.resolve()), prefix)
            if identity in seen:
                continue
            seen.add(identity)
            try:
                metadata = addon_metadata(directory)
            except (OSError, ValueError, SyntaxError) as error:
                warnings.append(f"{directory}: {error}")
                continue
            if not metadata:
                continue
            module = prefix + directory.name
            installed.append({"module": module, "path": str(directory), **metadata,
                              "enabled_in_preferences": module in enabled,
                              "loaded_in_process": module in sys.modules,
                              "register_completed": bool(getattr(sys.modules.get(module), "__addon_enabled__", False))})
    scene = bpy.context.scene
    devices = []
    cycles = bpy.context.preferences.addons.get("cycles")
    if cycles:
        try:
            # Query only. Do not change the selected backend or device flags.
            for backend in ("OPTIX", "CUDA"):
                for device in cycles.preferences.get_devices_for_type(backend):
                    item = {"name": device.name, "type": device.type, "use": device.use}
                    if item not in devices:
                        devices.append(item)
        except Exception as error:
            warnings.append(f"Cycles device query: {error}")
    namespaces = ("mmd_tools", "mmr", "mmd_kafei_tools", "paper_helper")
    return {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "blender": {"version": bpy.app.version_string, "executable": bpy.app.binary_path,
                    "python": sys.version, "background": bpy.app.background},
        "enabled_addons": sorted(enabled), "installed_addons": installed,
        "operators": {ns: operator_inventory(bpy, ns) for ns in namespaces},
        "cycles_devices": devices,
        "scene": {"file": bpy.data.filepath, "objects": len(scene.objects),
                  "engine": scene.render.engine, "fps": scene.render.fps / scene.render.fps_base,
                  "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                  "view_transform": scene.view_settings.view_transform},
        "warnings": warnings,
        "limits": ["This is a separate background process, not the open GUI scene.",
                   "Registered operators do not prove PMX/VMD import, physics, or render quality.",
                   "Device discovery does not prove successful GPU rendering."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    report = collect()
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Refuse to replace an earlier diagnostic report.
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(payload + "\n")
        print(f"BLENDER_MMD_CODEX_INVENTORY_OK: {args.output}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
