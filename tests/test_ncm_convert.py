"""Protect original music and reject ambiguous or invalid conversion outputs."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ncm_convert import audio_format, collect_inputs, convert_one
from scripts.mux_production_audio import project_audio


class NcmConversionTests(unittest.TestCase):
    def test_batch_deduplicates_and_finds_uppercase_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "song.NCM"
            source.write_bytes(b"CTENFDAM")
            (root / "other.txt").write_text("ignored")
            self.assertEqual(collect_inputs([root, source]), [source.resolve()])

    def test_recursive_same_basename_cannot_overwrite_another_song(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["one", "two"]:
                sub = root / name
                sub.mkdir()
                (sub / "song.ncm").write_bytes(b"CTENFDAM")
            with self.assertRaisesRegex(ValueError, "collision"):
                collect_inputs([root], recursive=True)

    def test_invalid_header_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "song.ncm"
            source.write_bytes(b"not NCM")
            with self.assertRaises(ValueError):
                convert_one(
                    source, root / "out", root / "temp", Path("backend"), Path("ffmpeg")
                )
            self.assertFalse((root / "out").exists())

    def test_existing_output_is_preserved_without_running_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "song.ncm"
            source.write_bytes(b"CTENFDAM")
            out = root / "out"
            out.mkdir()
            original = out / "song.flac"
            original.write_bytes(b"keep this")
            with patch("scripts.ncm_convert.run") as backend:
                with self.assertRaises(FileExistsError):
                    convert_one(
                        source, out, root / "temp", Path("backend"), Path("ffmpeg")
                    )
                backend.assert_not_called()
            self.assertEqual(original.read_bytes(), b"keep this")

    def test_decode_failure_never_publishes_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "song.ncm"
            original = b"CTENFDAMsource bytes"
            source.write_bytes(original)

            def extract(command):
                (Path(command[-1]) / "song.flac").write_bytes(b"fLaCbroken")

            with (
                patch("scripts.ncm_convert.run", side_effect=extract),
                patch(
                    "scripts.ncm_convert.verify_audio",
                    side_effect=ValueError("decode failed"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "decode failed"):
                    convert_one(
                        source,
                        root / "out",
                        root / "temp",
                        Path("backend"),
                        Path("ffmpeg"),
                    )
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(list((root / "out").iterdir()), [])

    def test_format_is_based_on_signature_not_file_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "pretend.flac"
            source.write_bytes(b"ID3music")
            self.assertEqual(audio_format(source), "mp3")

    def test_project_uses_selected_bgm_and_checks_its_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            music = root / "vocal.flac"
            music.write_bytes(b"selected vocal")
            recipe = root / "project.json"
            recipe.write_text(
                json.dumps(
                    {
                        "audio": {
                            "bgm": str(music),
                            "bgm_sha256": hashlib.sha256(
                                music.read_bytes()
                            ).hexdigest(),
                            "instrumental": "must not be used.wav",
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(project_audio(recipe), music)
            music.write_bytes(b"different file")
            with self.assertRaisesRegex(ValueError, "checksum"):
                project_audio(recipe)

    def test_project_never_silently_falls_back_to_instrumental(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = Path(directory) / "project.json"
            recipe.write_text(
                json.dumps({"audio": {"instrumental": "old.wav"}}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "no selected"):
                project_audio(recipe)


if __name__ == "__main__":
    unittest.main()
