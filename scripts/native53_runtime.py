"""Register the isolated native5.3 MMD camera dependency before opening a project."""

import argparse
import os
import sys
from pathlib import Path

import bpy

BASE = Path("D:/codex/workspace/blender-runtimes/5.3.0")
EXECUTABLE = BASE / "blender-5.3.0-windows-x64/blender.exe"
CONFIG = BASE / "portable/config"
SCRIPTS = BASE / "portable/scripts"
BUILD = "02f0899d78e3"


def register_mmd():
    import addon_utils

    assert bpy.app.version[:3] == (5, 3, 0)
    assert bpy.app.build_hash.decode() == BUILD
    scripts = Path(os.environ.get("BLENDER_USER_SCRIPTS", "")).resolve()
    assert scripts == SCRIPTS.resolve(), "Use the isolated native53 portable scripts"
    assert Path(os.environ.get("BLENDER_USER_CONFIG", "")).resolve() == CONFIG.resolve()
    sys.path.insert(0, str(SCRIPTS / "modules"))
    sys.path.insert(0, str(SCRIPTS / "addons"))
    import opencc

    assert (
        Path(opencc.__file__)
        .resolve()
        .is_relative_to((SCRIPTS / "modules/opencc").resolve())
    )
    module = addon_utils.enable("mmd_tools", default_set=False, persistent=True)
    assert module and getattr(module, "__addon_enabled__", False)
    assert (
        Path(module.__file__)
        .resolve()
        .is_relative_to((SCRIPTS / "addons/mmd_tools").resolve())
    )
    return {
        "mmd_tools": module.__file__,
        "opencc": opencc.__file__,
        "preferences_saved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    assert args.project.is_file()
    assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
    print("NATIVE53_PORTABLE_DEPENDENCIES", register_mmd(), flush=True)
    bpy.ops.wm.open_mainfile(
        filepath=str(args.project), load_ui=not bpy.app.background, use_scripts=False
    )
    scene = bpy.context.scene
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    assert abs(scene.camera.data.lens - 61.73465) < 0.01
    print(
        "NATIVE53_PROJECT_READY", scene.camera.name, scene.camera.data.lens, flush=True
    )


if __name__ == "__main__":
    main()
