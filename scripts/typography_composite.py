"""Composite native-aspect typography with cue-specific front/back placement.

Uses actual object/material Cryptomatte PNGs, scene picture PNGs and an official
black-background typography video. Layer order is an editorial choice per cue.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def srgb_to_linear(value):
    return np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(value):
    value = np.clip(value, 0, 1)
    return np.where(
        value <= 0.0031308, value * 12.92, 1.055 * value ** (1 / 2.4) - 0.055
    )


def over(base, premult, alpha):
    return base * (1 - alpha[..., None]) + premult


def protect_layer(premult, alpha, actor, face, order, protection):
    if order not in {"front", "behind"}:
        raise ValueError("Unknown layer order")
    if protection not in {"none", "face", "character"}:
        raise ValueError("Unknown protection mode")
    mask = (
        actor
        if order == "behind" or protection == "character"
        else face
        if protection == "face"
        else np.zeros_like(actor)
    )
    keep = 1 - mask
    return premult * keep[..., None], alpha * keep


def matte_image(path, margin):
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(path)
    # A small hard holdout margin protects hair antialiasing and outlines.
    mask = (image > 2).astype(np.float32)
    if margin:
        mask = cv2.dilate(mask, np.ones((2 * margin + 1, 2 * margin + 1), np.uint8))
    return mask


def glyph_layer(alpha, tint, settings=None):
    settings = settings or {}
    h, w = alpha.shape
    premult = np.zeros((h, w, 3), np.float32)
    result_alpha = np.zeros((h, w), np.float32)
    radius = settings.get("stroke_radius_pixels", 1)
    stroke = cv2.dilate(alpha, np.ones((2 * radius + 1, 2 * radius + 1), np.uint8))
    glow = cv2.GaussianBlur(
        alpha, (0, 0), settings.get("glow_sigma_pixels", 3.0)
    ) * settings.get("glow_strength", 0.12)
    for coverage, rgb in [
        (glow, settings.get("glow_rgb", (0.82, 0.48, 0.76))),
        (stroke * 0.90, settings.get("stroke_rgb", (0.18, 0.10, 0.28))),
        (alpha, tint),
    ]:
        color = srgb_to_linear(np.asarray(rgb, np.float32))
        premult = premult * (1 - coverage[..., None]) + color * coverage[..., None]
        result_alpha = result_alpha * (1 - coverage) + coverage
    return premult, result_alpha


def validate_profile(profile):
    previous = 0.0
    for cue in profile["cues"]:
        if cue["start"] < previous or cue["end"] <= cue["start"]:
            raise ValueError("Overlapping or reversed cues")
        if cue["order"] not in {"front", "behind"} or cue["protect"] not in {
            "none",
            "face",
            "character",
        }:
            raise ValueError("Unsupported caption layer option")
        previous = cue["end"]


def infer_end_frame(cache_dir, start):
    frames = []
    for path in (Path(cache_dir) / "beauty").glob("frame_*beauty.png"):
        match = re.fullmatch(r"frame_(\d+)beauty", path.stem)
        if match and int(match.group(1)) >= start:
            frames.append(int(match.group(1)))
    if not frames:
        raise ValueError("No beauty frames at or after requested start")
    return max(frames)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache-dir", type=Path, required=True)
    p.add_argument("--typography", type=Path, required=True)
    p.add_argument("--profile", type=Path)
    p.add_argument("--ffmpeg", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--start-frame", type=int, default=421)
    p.add_argument("--end-frame", type=int)
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--style-package", type=Path)
    args = p.parse_args()
    inferred_end = args.end_frame is None
    if inferred_end:
        args.end_frame = infer_end_frame(args.cache_dir, args.start_frame)
    recipe = None
    if args.style_package:
        from style_presets import load_package

        recipe = load_package(args.style_package)
    profile_path = args.profile or (Path(recipe["typography_path"]) if recipe else None)
    if profile_path is None:
        p.error("Provide --profile or --style-package")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if recipe:
        if profile["aspect"] != recipe["typography"]["aspect"]:
            raise ValueError("Style and typography must use the same aspect")
        profile.update(recipe["post"]["typography"])
    validate_profile(profile)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    first = args.cache_dir / "beauty" / f"frame_{args.start_frame:04d}beauty.png"
    with Image.open(first) as image:
        w, h = image.size
    aspect = profile["aspect"]
    assert abs(w / h - aspect[0] / aspect[1]) < 0.001
    if recipe:
        profile["character_margin_pixels"] = round(
            recipe["layout"]["character_margin_height"] * h
        )
        profile["face_margin_pixels"] = round(
            recipe["layout"]["face_margin_height"] * h
        )
        if recipe["post"]["background"]["mode"] == "argyle":
            profile["character_margin_pixels"] = max(
                profile["character_margin_pixels"],
                round(recipe["layout"]["sticker_width_height"] * h) + 1,
            )
    glyph_settings = dict(recipe["post"]["typography"]) if recipe else {}
    if recipe:
        glyph_settings["stroke_radius_pixels"] = max(1, round(h / 960))
        glyph_settings["glow_sigma_pixels"] = 3 * h / 960
    source = cv2.VideoCapture(str(args.typography))
    assert source.isOpened()
    source_fps = source.get(cv2.CAP_PROP_FPS)
    assert abs(source_fps - args.fps) < 0.01
    source_width, source_height = (
        source.get(cv2.CAP_PROP_FRAME_WIDTH),
        source.get(cv2.CAP_PROP_FRAME_HEIGHT),
    )
    assert abs(source_width / source_height - w / h) < 0.001, (
        "Choose a native-aspect asset; no automatic crop"
    )
    source.set(
        cv2.CAP_PROP_POS_FRAMES, round(profile["source_start_seconds"] * source_fps)
    )
    picture = args.output_dir / "typography-picture.mp4"
    command = [
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
        f"{w}x{h}",
        "-framerate",
        str(args.fps),
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
        "-movflags",
        "+faststart",
        str(picture),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    checks = []
    total = args.end_frame - args.start_frame + 1
    samples = {
        0,
        round(total / 8),
        round(total / 4),
        round(total / 2) - 1,
        round(total / 2),
        round(total * 0.75),
        total - 1,
    }
    contact = Image.new("RGB", (270 * 4, (round(270 * h / w) + 30) * 2), "#20202b")
    cell_h = round(270 * h / w)
    sample_number = 0
    comparison_done = False
    try:
        for index, frame in enumerate(range(args.start_frame, args.end_frame + 1)):
            with Image.open(
                args.cache_dir / "beauty" / f"frame_{frame:04d}beauty.png"
            ) as im:
                base_rgb = np.asarray(im.convert("RGB"), dtype=np.float32) / 255
            if recipe:
                from style_post import apply_post

                soft_actor = (
                    cv2.imread(
                        str(args.cache_dir / "matte" / f"frame_{frame:04d}matte.png"),
                        cv2.IMREAD_GRAYSCALE,
                    ).astype(np.float32)
                    / 255
                )
                soft_face = (
                    cv2.imread(
                        str(args.cache_dir / "face" / f"frame_{frame:04d}face.png"),
                        cv2.IMREAD_GRAYSCALE,
                    ).astype(np.float32)
                    / 255
                )
                base_rgb = apply_post(
                    base_rgb, soft_actor, soft_face, index / args.fps, recipe
                )
            base = srgb_to_linear(base_rgb)
            actor = matte_image(
                args.cache_dir / "matte" / f"frame_{frame:04d}matte.png",
                profile["character_margin_pixels"],
            )
            face = matte_image(
                args.cache_dir / "face" / f"frame_{frame:04d}face.png",
                profile["face_margin_pixels"],
            )
            assert 0 < actor.mean() < 0.95 and 0 < face.mean() < actor.mean()
            ok, type_bgr = source.read()
            assert ok, "Typography source ended early"
            # A monochrome black-backed video yields a luma holdout, not the
            # original RGBA. Black inside white cards remains a cutout.
            alpha = cv2.resize(
                type_bgr.max(axis=2).astype(np.float32) / 255,
                (w, h),
                interpolation=cv2.INTER_AREA,
            )
            t = index / args.fps
            cue = next(
                (c for c in profile["cues"] if c["start"] <= t < c["end"]),
                {"order": "front", "protect": "none", "opacity": 0},
            )
            alpha *= cue.get("opacity", profile["opacity"])
            premult, layer_alpha = glyph_layer(
                alpha,
                profile["tint_srgb"],
                glyph_settings,
            )
            color, coverage = protect_layer(
                premult, layer_alpha, actor, face, cue["order"], cue["protect"]
            )
            result = np.clip(over(base, color, coverage), 0, 1)
            delta = np.abs(result - base)
            strict = (
                actor
                if cue["order"] == "behind" or cue["protect"] == "character"
                else face
                if cue["protect"] == "face"
                else None
            )
            protected_error = (
                float(delta[strict > 0.99].max()) if strict is not None else None
            )
            if strict is not None:
                assert protected_error < 1e-6
            checks.append(
                {
                    "frame": frame,
                    "order": cue["order"],
                    "protect": cue["protect"],
                    "protected_max_linear_delta": protected_error,
                    "changed_character_pixels": int(
                        np.count_nonzero((delta.max(axis=2) > 0.001) & (actor > 0.99))
                    ),
                    "face_fraction": float(face.mean()),
                }
            )
            rgb = (linear_to_srgb(result) * 255 + 0.5).astype(np.uint8)
            process.stdin.write(rgb.tobytes())
            if index in samples:
                im = Image.fromarray(rgb)
                im.save(args.output_dir / f"sample-{frame:04d}.png")
                x, y = (sample_number % 4) * 270, (sample_number // 4) * (cell_h + 30)
                contact.paste(im.resize((270, cell_h)), (x, y))
                ImageDraw.Draw(contact).text(
                    (x + 6, y + cell_h + 7),
                    f"{t:.2f}s {cue['order']} / {cue['protect']}",
                    fill="white",
                )
                sample_number += 1
            if (
                not comparison_done
                and np.count_nonzero((alpha > 0.1) & (face > 0.99)) > 100
            ):
                compare = Image.new("RGB", (w * 3, h + 30), "#20202b")
                for column, (order, protect, label) in enumerate(
                    [
                        ("behind", "character", "Behind character"),
                        ("front", "face", "Front / protect face"),
                        ("front", "none", "Front / no holdout"),
                    ]
                ):
                    pc, pa = protect_layer(
                        premult, layer_alpha, actor, face, order, protect
                    )
                    out = (linear_to_srgb(over(base, pc, pa)) * 255 + 0.5).astype(
                        np.uint8
                    )
                    compare.paste(Image.fromarray(out), (column * w, 30))
                    ImageDraw.Draw(compare).text(
                        (column * w + 10, 10), label, fill="white"
                    )
                compare.save(args.output_dir / "layer-order-comparison.png")
                comparison_done = True
    finally:
        source.release()
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("Video encoding failed")
    contact.save(args.output_dir / "caption-contact-sheet.jpg", quality=95)
    report = {
        "profile": profile,
        "style_package": recipe,
        "glyph_effect_pixels": glyph_settings,
        "typography_source": str(args.typography),
        "cache_dir": str(args.cache_dir),
        "dimensions": [w, h],
        "frames": len(checks),
        "frame_range": [args.start_frame, args.end_frame],
        "end_frame_inferred_from_cache": inferred_end,
        "fps": args.fps,
        "source_timing_manually_verified": False,
        "layer_order_comparison_created": comparison_done,
        "protected_frames": sum(
            c["protected_max_linear_delta"] is not None for c in checks
        ),
        "maximum_protected_linear_delta": max(
            (c["protected_max_linear_delta"] or 0) for c in checks
        ),
        "intentional_foreground_character_changes": sum(
            c["changed_character_pixels"] for c in checks if c["order"] == "front"
        ),
        "checks": checks,
    }
    (args.output_dir / "caption-verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "TYPOGRAPHY_COMPOSITE_OK",
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in {"checks", "profile", "style_package"}
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
