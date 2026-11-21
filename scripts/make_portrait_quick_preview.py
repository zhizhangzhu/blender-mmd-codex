"""Produce only one captioned 1080p five-second review; skip post-output QA."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
from composite_duet_official_captions import picture, render_frame
from review_video_color import encoder_arguments
from stable_caption_layers import cue_at

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Portrait-Relight-v1")
TEMP = Path("D:/codex/temp/MMD-Portrait-Relight-v1/quick-5s-v2")
BLENDER = Path("E:/tools/Blender Foundation/Blender 5.2/blender.exe")
FFMPEG = Path(
    "D:/codex/temp/blender-mmd-video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--temp", type=Path, default=TEMP)
    parser.add_argument("--iteration", default="quick-5s-v2")
    parser.add_argument("--label", default="PortraitRelight")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--blender", type=Path, default=BLENDER)
    parser.add_argument("--goo", action="store_true")
    parser.add_argument(
        "--abort-shadow-overflow",
        action="store_true",
        help="Stop this owned renderer if its log reports shadow buffer overflow",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=REPO / "presets/typography/duet-blue-gold-wedding-v1.json",
    )
    parser.add_argument(
        "--reuse-cache",
        action="store_true",
        help="Caption-only edit using the exact saved project's existing native cache",
    )
    args = parser.parse_args()
    assert args.label.isalnum() and Path(args.iteration).name == args.iteration
    task_temp = args.temp
    project_path = (
        args.project or args.root / "production-v1/Franken_Duet_Portrait_Relight.blend"
    )
    output = args.root / args.iteration
    if args.reuse_cache:
        provenance = json.loads(
            (task_temp / "render-complete.json").read_text(encoding="utf-8")
        )
        assert Path(provenance["project"]).resolve() == project_path.resolve()
        assert (
            hashlib.sha256(project_path.read_bytes()).hexdigest()
            == provenance["project_sha256"]
        )
        assert (
            provenance["source_frames"] == [4140, 4438]
            and provenance["source_frame_step"] == 2
        )
        assert provenance["output_frames"] == 150 and provenance["resolution"] == [
            1920,
            1080,
        ]
    if args.reuse_cache and output.exists():
        if any(output.iterdir()):
            raise FileExistsError(
                "Refusing to overwrite existing caption outputs: " + str(output)
            )
    else:
        output.mkdir(parents=True, exist_ok=False)
    if not args.reuse_cache:
        task_temp.mkdir(parents=True, exist_ok=False)
        with (task_temp / "render.log").open("w", encoding="utf-8") as log:
            command = [
                str(args.blender),
                "--background",
                *(["--factory-startup"] if args.goo else []),
                "--disable-autoexec",
                "--python-exit-code",
                "1",
                "--python",
                str(REPO / "scripts/render_portrait_quick_cache.py"),
                "--",
                "--project",
                str(project_path),
                "--temp",
                str(task_temp),
                *(["--goo"] if args.goo else []),
            ]
            if args.abort_shadow_overflow:
                renderer = subprocess.Popen(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                while renderer.poll() is None:
                    time.sleep(2)
                    content = (task_temp / "render.log").read_text(
                        encoding="utf-8", errors="replace"
                    )
                    if "shadow buffer full" in content.lower():
                        renderer.terminate()
                        renderer.wait(timeout=30)
                        raise RuntimeError(
                            "Owned renderer stopped: shadow buffer overflow; no video encoded"
                        )
                content = (task_temp / "render.log").read_text(
                    encoding="utf-8", errors="replace"
                )
                if "shadow buffer full" in content.lower():
                    raise RuntimeError(
                        "Renderer reported shadow overflow; no video encoded"
                    )
                if renderer.returncode:
                    raise subprocess.CalledProcessError(renderer.returncode, command)
            else:
                subprocess.run(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
    print("QUICK_RENDER_COMPLETE_COMPOSITING_CAPTIONS", flush=True)
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    project = json.loads(
        (REPO / "presets/projects/franken-duet-full-v1.json").read_text(
            encoding="utf-8"
        )
    )
    captions = cv2.VideoCapture(profile["source"])
    captions.set(cv2.CAP_PROP_POS_FRAMES, profile["source_start_frame"])
    movie = output / f"Franken_Duet_5s_{args.label}_SUB_1080P.mp4"
    command = [
        str(FFMPEG),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-n",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        "1920x1080",
        "-r",
        "30",
        "-i",
        "pipe:0",
        "-ss",
        str(4139 / 60),
        "-i",
        project["audio"]["bgm"],
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        *encoder_arguments(),
        "-c:a",
        "aac",
        "-b:a",
        "256k",
        "-ar",
        "48000",
        "-af",
        "volume=0.87",
        "-t",
        "5",
        "-movflags",
        "+faststart",
        str(movie),
    ]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for frame in range(4140, 4440, 2):
            base = picture(task_temp / "cache/beauty" / f"frame_{frame:04d}beauty.png")
            actor = picture(task_temp / "cache/actor" / f"frame_{frame:04d}actor.png")
            ok, bgr = captions.read()
            if not ok:
                raise RuntimeError("Could not read the existing subtitle source")
            source_frame = (
                profile["source_start_frame"] + frame - profile["render_start_frame"]
            )
            typography = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
            result, _, _ = render_frame(
                base, actor, typography, profile, cue_at(profile, source_frame)
            )
            encoder.stdin.write(
                np.rint(np.clip(result, 0, 1) * 255).astype(np.uint8).tobytes()
            )
            if frame < 4438:
                captions.grab()
        encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError("Captioned preview encoding failed")
    finally:
        captions.release()
        if encoder.poll() is None:
            encoder.kill()
            encoder.wait()
    delivery = json.loads(
        (task_temp / "render-complete.json").read_text(encoding="utf-8")
    )
    delivery.update(
        video=str(movie),
        seconds=5,
        subtitles="existing blue-gold locked front/behind groups",
        bgm=project["audio"]["bgm"],
        audio_start=4139 / 60,
        variants=1,
        user_requested_no_post_output_checks=True,
        art_status="pending user review",
    )
    delivery.update(
        caption_profile=str(args.profile),
        reused_scene_cache=args.reuse_cache,
        cache_directory=str(task_temp / "cache"),
        caption_stroke_pixels_at_1080=profile["stroke_pixels_at_1080"],
        caption_shadow_opacity=profile["shadow_opacity"],
    )
    (output / "preview-info.json").write_text(
        json.dumps(delivery, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    state_path = REPO / "catalog/current_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["current_task"] = (
        "已产出1080p30五秒带字幕原声快样片；字幕参数与画面缓存来源见 latest_quick_preview，按要求跳过输出后检查。"
    )
    state["latest_quick_preview"] = delivery
    state["active_iteration"].update(
        new_video_delivered=True,
        video=str(movie),
        quick_preview=str(movie),
        caption_profile=str(args.profile),
        scope="150 frames at 1080p30 quick captioned preview; post-output QA skipped by user",
        next_action="由猪猪直接审看快样片；尚不将新链登记为动态或正式成片验收通过。",
    )
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("QUICK_CAPTIONED_PREVIEW_COMPLETE", movie, flush=True)


if __name__ == "__main__":
    main()
