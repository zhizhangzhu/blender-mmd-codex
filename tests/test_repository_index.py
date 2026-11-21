"""Check that navigation covers files and never executes scanned Python."""

import tempfile
import unittest
from pathlib import Path

from scripts.repository_index import GENERATED, build_index, documents


class RepositoryIndexTests(unittest.TestCase):
    def test_indexes_sources_but_excludes_cache_and_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "scripts/example.py",
                "docs/guide.md",
                ".git/secret",
                "scripts/__pycache__/cached.pyc",
                ".ruff_cache/data",
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('"""Sample module."""\n', encoding="utf-8")
            names = {item["path"] for item in build_index(root)["entries"]}
            self.assertEqual(names, {"scripts/example.py", "docs/guide.md", *GENERATED})

    def test_scanning_does_not_execute_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "render_example.py"
            path.write_text(
                '"""Do not run."""\nraise RuntimeError("executed")\n', encoding="utf-8"
            )
            entry = next(
                e for e in build_index(root)["entries"] if e["path"] == path.name
            )
            self.assertEqual(entry["summary"], "Do not run.")

    def test_generated_files_do_not_change_the_next_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = build_index(root)
            for name, content in documents(before).items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            self.assertEqual(before, build_index(root))

    def test_render_mention_is_not_reported_as_executed_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "example.py"
            path.write_text('"""bpy.ops.render.render()"""\n', encoding="utf-8")
            entry = next(
                e for e in build_index(root)["entries"] if e["path"] == path.name
            )
            self.assertNotIn("native_render_call", entry.get("static_hints", []))
            path.write_text("bpy.ops.render.render()\n", encoding="utf-8")
            entry = next(
                e for e in build_index(root)["entries"] if e["path"] == path.name
            )
            self.assertIn("native_render_call", entry["static_hints"])


if __name__ == "__main__":
    unittest.main()
