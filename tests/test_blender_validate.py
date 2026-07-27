from __future__ import annotations

import unittest
from pathlib import Path
from subprocess import CompletedProcess

from scripts.blender_validate import validate_blender


class BlenderValidateTests(unittest.TestCase):
    def test_validate_blender_and_addon(self) -> None:
        def runner(command, **_kwargs):
            if "--version" in command:
                return CompletedProcess(command, 0, "Blender 4.5.1\n", "")
            if "--python-expr" in command:
                expression = command[-1]
                if "BLENDER_MMD_CODEX_ADDON_OK" in expression:
                    return CompletedProcess(command, 0, "BLENDER_MMD_CODEX_ADDON_OK\n", "")
                return CompletedProcess(command, 0, "BLENDER_MMD_CODEX_BPY_OK\n", "")
            return CompletedProcess(command, 1, "", "unexpected command")

        report = validate_blender(
            Path("/fake/blender"),
            addon_path=Path("/fake/blender_addon"),
            runner=runner,
        )
        self.assertTrue(report.ok)
        self.assertEqual(report.version, "4.5.1")

    def test_validate_blender_reports_python_failure(self) -> None:
        def runner(command, **_kwargs):
            if "--version" in command:
                return CompletedProcess(command, 0, "Blender 4.5.1\n", "")
            return CompletedProcess(command, 1, "", "bpy failed")

        report = validate_blender(Path("/fake/blender"), runner=runner)
        self.assertFalse(report.ok)
        self.assertIn("Blender Python API 驗證失敗", report.errors)


if __name__ == "__main__":
    unittest.main()
