"""Render a saved production project to a new H.264 picture master.

The source blend is not overwritten. Mix accompaniment in a separate verified
step with mux_production_audio.py: direct camera rendering produced a silent
AAC stream on the tested Blender 5.2.2 configuration.
"""

import argparse
import bpy
import sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--start", type=int, help="Optional inclusive chunk start")
p.add_argument("--end", type=int, help="Optional inclusive chunk end")
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
if args.output.exists():
    raise FileExistsError(args.output)
args.output.parent.mkdir(parents=True, exist_ok=True)
s = bpy.context.scene
assert s.camera and s.frame_end > s.frame_start
assert s.rigidbody_world is None, "Production must use portable baked physics"
assert (args.start is None) == (args.end is None), "Supply both chunk bounds"
if args.start is not None:
    assert s.frame_start <= args.start <= args.end <= s.frame_end
    s.frame_start = args.start
    s.frame_end = args.end
s.render.resolution_percentage = 100
s.render.image_settings.media_type = "VIDEO"
s.render.image_settings.file_format = "FFMPEG"
s.render.ffmpeg.format = "MPEG4"
s.render.ffmpeg.codec = "H264"
s.render.ffmpeg.constant_rate_factor = "HIGH"
s.render.ffmpeg.ffmpeg_preset = "GOOD"
s.render.ffmpeg.audio_codec = "NONE"
s.render.ffmpeg.audio_bitrate = 256
s.render.ffmpeg.audio_mixrate = 48000
s.render.use_sequencer = False
s.render.filepath = str(args.output)
print(
    "PRODUCTION_RENDER_START",
    s.render.resolution_x,
    s.render.resolution_y,
    s.render.fps,
    s.frame_start,
    s.frame_end,
    flush=True,
)
bpy.ops.render.render(animation=True)
print("PRODUCTION_RENDER_COMPLETE", args.output, flush=True)
