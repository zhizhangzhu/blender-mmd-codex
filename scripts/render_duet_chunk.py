"""Render one recoverable production chunk and expose progress as JSON."""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--progress", type=Path, required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--linear-archive-dir", type=Path)
    parser.add_argument("--caption-cache-dir", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.output.exists():
        raise FileExistsError(args.output)
    scene = bpy.context.scene
    if args.caption_cache_dir:
        nodes = [
            n
            for n in scene.compositing_node_group.nodes
            if n.name.startswith("Caption cache | ")
        ]
        assert {n.name.split(" | ")[-1] for n in nodes} == {"beauty", "actor"}
        for node in nodes:
            node.directory = str(args.caption_cache_dir / node.name.split(" | ")[-1])
            node.file_name = "frame_####"
            node.mute = False
    if args.linear_archive_dir and scene.compositing_node_group:
        archive = scene.compositing_node_group.nodes.get(
            "Quality | scene-linear EXR archive"
        )
        if archive:
            archive.directory = str(args.linear_archive_dir)
            archive.file_name = "duet_####"
    assert scene.rigidbody_world is None and scene.get("production_duet_complete_scene")
    scene.frame_start, scene.frame_end = args.start, args.end
    scene.render.resolution_percentage = 100
    scene.render.image_settings.media_type = "VIDEO"
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.audio_codec = "NONE"
    scene.render.use_sequencer = False
    scene.render.filepath = str(args.output)
    started = time.time()

    def update(_scene):
        result = {
            "start": args.start,
            "end": args.end,
            "last_frame": scene.frame_current,
            "elapsed_seconds": time.time() - started,
            "complete": False,
        }
        temporary = args.progress.with_suffix(".tmp")
        temporary.write_text(json.dumps(result), encoding="utf-8")
        temporary.replace(args.progress)

    bpy.app.handlers.render_post.append(update)
    bpy.ops.render.render(animation=True)
    result = json.loads(args.progress.read_text(encoding="utf-8"))
    result["complete"] = True
    args.progress.write_text(json.dumps(result), encoding="utf-8")
    print("DUET_CHUNK_COMPLETE", args.start, args.end, flush=True)


if __name__ == "__main__":
    main()
