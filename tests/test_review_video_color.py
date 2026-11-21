"""Exercise the actual encoder/filter/mux path that previously lost color tags."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.review_video_color import encoder_arguments

FFMPEG = os.environ.get("MMD_TEST_FFMPEG")


@unittest.skipUnless(
    FFMPEG and Path(FFMPEG).is_file(),
    "Set MMD_TEST_FFMPEG for native color integration test",
)
class ReviewColorIntegrationTests(unittest.TestCase):
    def test_color_metadata_survives_filters_and_audio_mux_and_levels_roundtrip(self):
        with tempfile.TemporaryDirectory(
            prefix="mmd-color-", dir=os.environ.get("MMD_TEST_TEMP")
        ) as folder:
            picture = Path(folder) / "picture.mp4"
            final = Path(folder) / "audio-muxed.mp4"
            rgb = np.zeros((64, 128, 3), np.uint8)
            for i, color in enumerate(
                ((0, 0, 0), (255, 255, 255), (210, 45, 30), (30, 75, 210))
            ):
                rgb[:, i * 32 : (i + 1) * 32] = color
            subprocess.run(
                [
                    FFMPEG,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-s",
                    "128x64",
                    "-r",
                    "60",
                    "-i",
                    "pipe:0",
                    "-frames:v",
                    "3",
                    "-c:v",
                    "libx264",
                    "-crf",
                    "10",
                    *encoder_arguments(),
                    str(picture),
                ],
                input=rgb.tobytes() * 3,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                [
                    FFMPEG,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(picture),
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=0.05",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    str(final),
                ],
                capture_output=True,
                check=True,
            )
            for video in (picture, final):
                metadata = subprocess.run(
                    [
                        FFMPEG,
                        "-hide_banner",
                        "-i",
                        str(video),
                        "-vf",
                        "showinfo",
                        "-frames:v",
                        "1",
                        "-f",
                        "null",
                        "NUL",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=True,
                ).stderr
                self.assertIn(
                    "color_range:tv color_space:bt709 color_primaries:bt709 color_trc:iec61966-2-1",
                    metadata,
                )
            decoded = subprocess.run(
                [
                    FFMPEG,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(final),
                    "-frames:v",
                    "1",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "pipe:1",
                ],
                capture_output=True,
                check=True,
            ).stdout
            actual = np.frombuffer(decoded, np.uint8).reshape(64, 128, 3)
            self.assertLessEqual(int(actual[32, 16].max()), 1)
            self.assertGreaterEqual(int(actual[32, 48].min()), 253)
            for x in (80, 112):
                self.assertLess(
                    float(
                        abs(
                            actual[20:44, x - 4 : x + 4].astype(float)
                            - rgb[20:44, x - 4 : x + 4]
                        ).mean()
                    ),
                    3,
                )


if __name__ == "__main__":
    unittest.main()
