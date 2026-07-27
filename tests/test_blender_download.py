from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.blender_download import (
    build_official_artifact,
    download_file,
    verify_sha256,
)


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size: int) -> bytes:
        chunk, self.content = self.content[:size], self.content[size:]
        return chunk


class BlenderDownloadTests(unittest.TestCase):
    def test_build_official_artifact_uses_explicit_version(self) -> None:
        artifact = build_official_artifact("4.5.1", "Windows", "AMD64")
        self.assertEqual(artifact.filename, "blender-4.5.1-windows-x64.zip")
        self.assertTrue(artifact.url.startswith("https://download.blender.org/"))

    def test_download_requires_and_verifies_sha256(self) -> None:
        content = b"blender archive fixture"
        digest = hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "archive.zip"
            result = download_file(
                "https://download.blender.org/release/Blender4.5/archive.zip",
                destination,
                digest,
                urlopen=lambda *_args, **_kwargs: FakeResponse(content),
            )
            self.assertEqual(result, destination)
            self.assertTrue(verify_sha256(destination, digest))

    def test_download_removes_partial_file_after_hash_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "archive.zip"
            with self.assertRaises(ValueError):
                download_file(
                    "https://download.blender.org/release/Blender4.5/archive.zip",
                    destination,
                    "0" * 64,
                    urlopen=lambda *_args, **_kwargs: FakeResponse(b"bad archive"),
                )
            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_suffix(".zip.part").exists())


if __name__ == "__main__":
    unittest.main()
