"""Composite official caption groups onto native duet beauty/matte caches.

The front/behind decision is fixed per editorial group. No facial holdout,
overlap classifier, binary matte threshold or temporal-mask averaging is used.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from review_video_color import CONTRACT, encoder_arguments
from stable_caption_layers import (
    composite,
    continuous_actor_mask,
    cue_at,
    extract_layer,
    layout_layer,
    style_layer,
    validate,
)


def picture(path):
    pixels = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if pixels is None:
        raise FileNotFoundError(path)
    assert pixels.dtype == np.uint16, (path, "Expected native PNG16 cache")
    maximum = np.iinfo(pixels.dtype).max
    value = pixels.astype(np.float32) / maximum
    if value.ndim == 3:
        value = value[:, :, :3][:, :, ::-1]
    return value


def render_frame(base, actor, source, profile, cue):
    height, width = base.shape[:2]
    source = cv2.resize(source, (width, height), interpolation=cv2.INTER_AREA)
    text, alpha = extract_layer(
        source, cue["key_mode"], profile["tint_srgb"], profile.get("palette")
    )
    text, alpha = style_layer(text, alpha, profile)
    text, alpha = layout_layer(text, alpha, cue)
    mask = continuous_actor_mask(
        actor, round(profile["matte_margin_pixels_at_1080"] * height / 1080)
    )
    result = composite(base, text, alpha, mask, cue["order"])
    return result, alpha, mask


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--preview-frames", type=int, nargs="*")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    validate(profile)
    source_path = Path(profile["source"])
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest() == profile["source_sha256"]
    )
    source = cv2.VideoCapture(str(source_path))
    assert (
        source.isOpened() and abs(source.get(cv2.CAP_PROP_FPS) - profile["fps"]) < 0.001
    )
    frames = args.preview_frames or list(
        range(
            profile["render_start_frame"],
            profile["render_start_frame"] + profile["render_frames"],
        )
    )
    first = picture(args.cache_dir / "beauty" / f"frame_{frames[0]:04d}beauty.png")
    height, width = first.shape[:2]
    assert abs(width / height - 16 / 9) < 0.003
    process = None
    if not args.preview_frames:
        expected_frames = set(frames)
        for kind in ("beauty", "actor"):
            actual_frames = {
                int(p.name[6:10])
                for p in (args.cache_dir / kind).glob(f"frame_????{kind}.png")
            }
            assert actual_frames == expected_frames, (
                kind,
                "Incomplete or extra native frames",
            )
        process = subprocess.Popen(
            [
                str(args.ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-n",
                "-f",
                "rawvideo",
                "-pixel_format",
                "rgb24",
                "-video_size",
                f"{width}x{height}",
                "-framerate",
                str(profile["fps"]),
                "-i",
                "pipe:0",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "17",
                "-pix_fmt",
                "yuv420p",
                *encoder_arguments(),
                "-movflags",
                "+faststart",
                str(args.output_dir / "Duet_Captions_Picture.mp4"),
            ],
            stdin=subprocess.PIPE,
        )
    records = []
    by_group = {}
    sample_indices = {round((i + 0.5) * len(frames) / 12) for i in range(12)}
    review_frames = {4200, 4250, 4290}
    for group in profile["cues"][1:]:
        boundary = (
            profile["render_start_frame"]
            + group["start_frame"]
            - profile["source_start_frame"]
        )
        review_frames.update(range(boundary - 3, boundary + 4))
    last_source = None
    try:
        for index, frame in enumerate(frames):
            base = picture(args.cache_dir / "beauty" / f"frame_{frame:04d}beauty.png")
            actor = picture(args.cache_dir / "actor" / f"frame_{frame:04d}actor.png")
            assert base.shape == (height, width, 3) and actor.shape == (height, width)
            assert actor.min() == 0 and actor.max() > 0.999
            assert actor.shape == base.shape[:2] and 0.001 < actor.mean() < 0.85
            source_frame = (
                profile["source_start_frame"] + frame - profile["render_start_frame"]
            )
            if last_source != source_frame - 1:
                source.set(cv2.CAP_PROP_POS_FRAMES, source_frame)
            ok, bgr = source.read()
            assert ok
            last_source = source_frame
            typography = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
            cue = cue_at(profile, source_frame)
            result, alpha, mask = render_frame(base, actor, typography, profile, cue)
            difference = abs(result - base)
            protected_error = (
                float(difference[mask > 0.9999].max())
                if cue["order"] == "behind"
                else None
            )
            if protected_error is not None:
                assert protected_error < 0.00001
            by_group.setdefault(cue["id"], set()).add(cue["order"])
            assert len(by_group[cue["id"]]) == 1
            changed_actor = int(
                np.count_nonzero((difference.max(2) > 0.004) & (actor > 0.999))
            )
            records.append(
                {
                    "global_frame": frame,
                    "typography_frame": source_frame,
                    "group": cue["id"],
                    "order": cue["order"],
                    "key_mode": cue["key_mode"],
                    "protected_error_before_encoding": protected_error,
                    "changed_opaque_actor_pixels": changed_actor,
                    "fractional_matte_pixels": int(
                        np.count_nonzero((actor > 0) & (actor < 1))
                    ),
                    "text_coverage": float(alpha.mean()),
                }
            )
            rgb = np.rint(np.clip(result, 0, 1) * 255).astype(np.uint8)
            if process:
                process.stdin.write(rgb.tobytes())
            if args.preview_frames or index in sample_indices or frame in review_frames:
                Image.fromarray(rgb).save(args.output_dir / f"caption-{frame:04d}.png")
            if args.preview_frames:
                columns = Image.new("RGB", (width * 2, height + 45), "#161b28")
                columns.paste(
                    Image.fromarray(np.rint(base * 255).astype(np.uint8)), (0, 45)
                )
                columns.paste(Image.fromarray(rgb), (width, 45))
                font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 21)
                draw = ImageDraw.Draw(columns)
                draw.text((12, 10), "无字幕 · 同一原生渲染", font=font, fill="white")
                draw.text(
                    (width + 12, 10),
                    f"整组 {cue['order']} · {cue['id']}",
                    font=font,
                    fill="white",
                )
                columns.save(args.output_dir / f"preview-{frame:04d}.jpg", quality=95)
    finally:
        source.release()
        if process:
            process.stdin.close()
    if process and process.wait() != 0:
        raise RuntimeError("Caption encoding failed")
    if not args.preview_frames:
        assert len(records) == profile["render_frames"]
        assert any(
            r["order"] == "front" and r["changed_opaque_actor_pixels"] > 100
            for r in records
        ), "No actual front-of-character text demonstrated"
    report = {
        "profile": profile,
        "output_color_contract": CONTRACT,
        "cache": str(args.cache_dir),
        "size": [width, height],
        "frames": len(records),
        "preview_only": bool(args.preview_frames),
        "group_order_sets": {k: sorted(v) for k, v in by_group.items()},
        "front_frames_with_character_overlap": sum(
            r["order"] == "front" and r["changed_opaque_actor_pixels"] > 100
            for r in records
        ),
        "all_behind_opaque_actor_pixels_protected": True,
        "front_uses_no_face_or_character_mask": True,
        "records": records,
        "limits": [
            "Black-backed MP4 is not original RGBA; black artwork outside a white plate cannot be reconstructed",
            "Native continuous mask insertion over beauty is an edge-protection approximation, not exact independent actor/background RGBA reconstruction",
            "No per-word timing claim; source offset measured from audio envelopes",
        ],
        "passed": True,
    }
    (args.output_dir / "caption-layer-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "resolved-caption-profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("LOCKED_CAPTION_COMPOSITE_COMPLETE", len(records), flush=True)


if __name__ == "__main__":
    main()
