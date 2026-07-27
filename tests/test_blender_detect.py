from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess

from scripts.blender_detect import (
    detect_blender,
    find_blender_candidates,
    parse_blender_version,
)


class BlenderDetectTests(unittest.TestCase):
    def test_parse_blender_version(self) -> None:
        self.assertEqual(parse_blender_version("Blender 4.5.1\n"), "4.5.1")
        self.assertIsNone(parse_blender_version("not blender"))

    def test_windows_candidates_include_program_files_versions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / "Blender Foundation" / "Blender 4.5" / "blender.exe"
            executable.parent.mkdir(parents=True)
            executable.write_text("fake", encoding="utf-8")
            candidates = find_blender_candidates(
                system_name="Windows",
                env={"PROGRAMFILES": temporary},
                home=root,
                which=lambda _name: None,
            )
            self.assertIn(executable, candidates)

    def test_detect_blender_requires_a_valid_version_response(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "blender"
            executable.write_text("fake", encoding="utf-8")

            def runner(*_args, **_kwargs):
                return CompletedProcess([], 0, "Blender 4.5.1\n", "")

            installation = detect_blender(
                system_name="Linux",
                home=Path(temporary),
                which=lambda _name: str(executable),
                runner=runner,
            )
            self.assertIsNotNone(installation)
            self.assertEqual(installation.version, "4.5.1")


if __name__ == "__main__":
    unittest.main()
