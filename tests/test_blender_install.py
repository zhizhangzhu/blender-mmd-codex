from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.blender_install import InstallationError, install_portable_archive


class BlenderInstallTests(unittest.TestCase):
    def test_install_portable_zip_finds_blender_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "blender.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("blender-4.5.1/blender", "fake executable")
            executable = install_portable_archive(archive, root / "install", "Linux")
            self.assertEqual(executable.name, "blender")

    def test_install_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("../../outside.txt", "unsafe")
            with self.assertRaises(InstallationError):
                install_portable_archive(archive, root / "install", "Linux")
            self.assertFalse((root.parent / "outside.txt").exists())


if __name__ == "__main__":
    unittest.main()
