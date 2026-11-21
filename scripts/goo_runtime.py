"""Initialize the isolated Goo 5.2 runtime, without changing global preferences."""
import os
import sys
from pathlib import Path

import bpy

RUNTIME = Path('D:/codex/workspace/goo-engine/5.2.1-community/blender-5.2.1-git.0051aee0-windows64')
ADDONS = ('mmd_tools', 'mmd_kafei_tools', 'Paperzhu_animehelper_extension', 'MikuMikuRig')


def register_addons():
    import addon_utils
    if not hasattr(bpy.types, 'ShaderNodeShaderInfo'):
        raise RuntimeError('This project needs Goo shader nodes; use the configured Goo executable')
    configured = Path(os.environ.get('BLENDER_USER_SCRIPTS', str(RUNTIME / '5.2/scripts')))
    bundled = configured / 'addons'
    if not (bundled / 'mmd_tools').is_dir():
        bundled = RUNTIME / '5.2/scripts/addons'
    sys.path.insert(0, str(bundled))
    report = {}
    for name in ADDONS:
        module = addon_utils.enable(name, default_set=True, persistent=True)
        report[name] = bool(module and getattr(module, '__addon_enabled__', False))
        if module and not Path(module.__file__).resolve().is_relative_to(RUNTIME.parent.resolve()):
            raise RuntimeError('A global add-on was loaded instead of the Goo portable copy: ' + str(module.__file__))
    if not report['mmd_tools']:
        raise RuntimeError('MMD Tools must register before loading the camera and project')
    return report


if __name__ == '__main__':
    print('GOO_PORTABLE_ADDONS', register_addons(), flush=True)
