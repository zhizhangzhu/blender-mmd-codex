"""Exercise MP4 stream inspection independently of Blender and video encoding."""

import struct
import tempfile
import unittest
from pathlib import Path

from scripts.verify_video import boxes, stream_types


def atom(kind, payload=b""):
    return struct.pack(">I4s", len(payload) + 8, kind) + payload


class VideoContainerTests(unittest.TestCase):
    def test_finds_both_video_and_audio_tracks(self):
        def track(kind):
            handler = atom(b"hdlr", b"\0" * 8 + kind + b"\0" * 12)
            return atom(b"trak", atom(b"mdia", handler))

        data = (
            atom(b"ftyp", b"isom")
            + atom(b"mdat", b"compressed samples")
            + atom(b"moov", track(b"vide") + track(b"soun"))
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "example.mp4"
            path.write_bytes(data)
            self.assertEqual(stream_types(path), ["vide", "soun"])

    def test_rejects_truncated_container(self):
        with self.assertRaises(ValueError):
            list(boxes(struct.pack(">I4s", 100, b"moov")))

    def test_supports_extended_size_boxes(self):
        data = struct.pack(">I4sQ", 1, b"free", 20) + b"data"
        self.assertEqual(list(boxes(data)), [(b"free", 16, 20)])


if __name__ == "__main__":
    unittest.main()
