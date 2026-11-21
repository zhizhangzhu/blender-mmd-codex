"""Ensure reading plugin metadata never executes plugin source."""
import tempfile
import unittest
from pathlib import Path

from scripts.blender_inventory import addon_metadata


class InventoryMetadataTests(unittest.TestCase):
    def test_static_metadata_does_not_import_bpy_or_execute_plugin(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "__init__.py").write_text(
                "import bpy\nraise RuntimeError('must never execute')\n"
                "bl_info = {'name': '例子', 'version': (1, 2, 3)}\n", encoding="utf-8")
            metadata = addon_metadata(directory)
            self.assertEqual(metadata["name"], "例子")
            self.assertEqual(metadata["version"], (1, 2, 3))

    def test_computed_metadata_is_rejected_without_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "__init__.py").write_text("bl_info = dict(name='computed')", encoding="utf-8")
            with self.assertRaises(ValueError):
                addon_metadata(directory)
