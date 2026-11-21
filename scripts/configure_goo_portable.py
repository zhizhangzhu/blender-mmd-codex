"""Save only the dedicated Goo preferences, after a factory-startup bootstrap."""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons

expected = Path('D:/codex/workspace/goo-engine/5.2.1-community/portable/config').resolve()
actual = Path(bpy.utils.user_resource('CONFIG', create=True)).resolve()
assert actual == expected, (actual, expected)
report = register_addons()
assert all(report.values()), report
bpy.ops.wm.save_userpref()
print('GOO_ISOLATED_PREFERENCES_SAVED', actual / 'userpref.blend', report, flush=True)
