"""Package verified wedding lighting and blue/gold official typography."""

import argparse
import hashlib
import shutil
from pathlib import Path

import numpy as np
from package_duet_captions import cache_picture, review_boundaries
from package_fox_cinema import frame, panel, read, write
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
IDENTITY = "duet-blue-gold-wedding-v1"
DOC = "BLUE_GOLD_WEDDING_STUDY.md"


def controls(root):
    production, review = root / "production-v4", root / "review"
    review.mkdir(exist_ok=True)
    results = []
    for key, number, off, label in [
        ("scattering", 4250, "control-scattering-off-4250.png", "蓝金局部散射"),
        ("halos", 4290, "control-new-halos-off-4290.png", "本轮新增光晕"),
    ]:
        actual = production / f"wedding-{number}.png"
        a = np.asarray(Image.open(actual).convert("RGB"), np.float32)
        b = np.asarray(Image.open(production / off).convert("RGB"), np.float32)
        delta = abs(a - b)
        assert delta.mean() > 0.001, (key, "No visible effect contribution")
        results.append(
            {
                "effect": key,
                "mean_absolute_rgb_difference_255": float(delta.mean()),
                "fraction_pixels_over_one": float((delta.max(2) > 1).mean()),
            }
        )
        panel(
            [(production / off, label + "关"), (actual, label + "开")],
            review / f"{key}-control.jpg",
        )
    write(
        review / "effect-controls.json",
        {
            "measurements": results,
            "limits": "Scattering-off retains spotlight surface illumination and new GI. Halo-off retains previous-version halos. Differences prove presence, not quality.",
            "passed": True,
        },
    )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--controls-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    effects = controls(root)
    if args.controls_only:
        print("WEDDING_EFFECT_CONTROLS_VERIFIED", flush=True)
        return
    assert args.cache
    sample, lighting = root / "captions-5s-v1", root / "lighting-sample-5s-v1"
    movie = sample / "Franken_Duet_5s_Wedding_REVIEW.mp4"
    bare_movie = lighting / "Aether_Duet_5s_REVIEW.mp4"
    master = read(root / "master-verification.json")
    audit = read(sample / "caption-layer-audit.json")
    video = read(sample / "video-qa/video-verification.json")
    for report in (
        master,
        audit,
        video,
        read(sample / "audio-verification.json"),
        read(lighting / "seam-qa/seam-verification.json"),
    ):
        assert report["passed"]
    assert (
        master["wedding_verification"]
        and video["decoded_frames"] == audit["frames"] == 300
    )
    assert audit["profile"]["id"] == "duet-blue-gold-wedding-v1"
    previous = Path("D:/codex/output/MMD-Duet-Soft-Top-Rim-v1")
    old_movie = previous / "captions-5s-v1/Franken_Duet_5s_Captions_REVIEW.mp4"
    old_bare = previous / "lighting-sample-5s-v1/Aether_Duet_5s_REVIEW.mp4"
    assert (
        hashlib.sha256(old_movie.read_bytes()).hexdigest()
        == "84f183c098b97266359e99d29d66e91571b2a08e9cd7f089f35ab07eaba58eee"
    )
    assert (
        hashlib.sha256(old_bare.read_bytes()).hexdigest()
        == "d3e188b6fc4a13f145ec98e08ccdedd100e563df1ba494735e85a0664304f727"
    )
    review = root / "review"
    before = frame(old_bare, 110, review / "previous-4250.png")
    after = cache_picture(args.cache, 4250, review / "wedding-4250.png")
    panel(
        [(before, "柔光礼堂"), (after, "蓝金婚礼 · 同一帧")],
        review / "wedding-before-after.jpg",
    )
    color, mono = (
        sample / "caption-4200.png",
        root / "caption-monochrome-control/caption-4200.png",
    )
    assert color.is_file() and mono.is_file()
    panel(
        [(mono, "同一新场景 · 原字幕色"), (color, "同一新场景 · 蓝金字幕")],
        review / "caption-palette-comparison.jpg",
    )
    boundaries = review_boundaries(movie, audit, review)
    recipe = {
        "id": IDENTITY,
        "status": "verified-five-second-study",
        "user_art_approval": False,
        "project": master["target"],
        "source": master["source"],
        "stage_profile": "presets/stages/hesperides-blue-gold-wedding-v1.json",
        "caption_profile": "presets/typography/duet-blue-gold-wedding-v1.json",
        "caption_cache": str(args.cache),
        "video": str(movie),
        "without_captions_video": str(bare_movie),
        "frames": [4140, 4439],
        "fps": 60,
        "resolution": [1920, 1080],
        "audio_project": "presets/projects/franken-duet-full-v1.json",
        "audio_start_seconds": 68.98333333333333,
        "controls": effects,
        "limits": [
            "Five seconds only; waiting for user art feedback",
            "Art-directed spotlight volume/surface factors; inherited EEVEE volumetric shadows disabled",
            "Final typography is separate Python compositing; not visible in the Blender viewport",
        ],
    }
    write(REPO / f"presets/recipes/{IDENTITY}.json", recipe)
    entry = {
        "id": IDENTITY,
        "title": "誓光 · 蓝金婚礼",
        "subtitle": "人物后方的蓝金光束、走道微光与呼应双人主题色的官方字幕。",
        "collection": "WEDDING / BLUE & GOLD",
        "category": "stage",
        "family": "guanhaizi",
        "aspect": "landscape",
        "status": "motion",
        "image": str(color),
        "video": str(movie),
        "diagnostic_video": str(bare_movie),
        "diagnostic_label": "无字幕灯光版 · 5s",
        "duration": 5,
        "fps": 60,
        "project": master["target"],
        "docs": [
            DOC,
            "SOFT_TOP_RIM_LIGHTING.md",
            "DUET_CAPTION_STABILITY_AND_LIGHTING.md",
        ],
        "configs": [
            recipe["stage_profile"],
            recipe["caption_profile"],
            f"presets/recipes/{IDENTITY}.json",
        ],
        "look": [
            "蓝金后方光束",
            "走道香槟微光",
            "分开的场景／人物光晕",
            "彩色字幕固定层级",
        ],
        "compatibility": "固定双人礼堂五秒横屏；Blender 5.2.2 EEVEE，需官方 Wide 字幕源和原生缓存。",
        "evidence": [
            "300 原生帧／1080p60／指定原声验收",
            "局部散射与本轮光晕的原生同帧开关",
            "独立重开十时点动作／相机相同；最终beauty缓存路由一致",
            "蓝金字幕逐帧层级审计及四处连续切换核对",
        ],
        "limits": [
            "待猪猪美术评价，仅五秒，未扩展全曲或竖屏",
            "体积功率与表面功率为美术分配，未开启完整体积阴影",
            "黑底视频牌面恢复与人物柔边仍是有限范围近似",
        ],
        "command": f'python scripts/composite_duet_official_captions.py --cache-dir "{args.cache}" --profile presets/typography/duet-blue-gold-wedding-v1.json --output-dir "D:/codex/output/Wedding-Captions-New" --ffmpeg "D:/codex/temp/blender-mmd-video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"',
    }
    catalog_file = REPO / "catalog/library.json"
    catalog = read(catalog_file)
    catalog["entries"] = [entry] + [
        e for e in catalog["entries"] if e["id"] != IDENTITY
    ]
    pairs = [
        {
            "id": "wedding-before-after",
            "title": "柔光礼堂 / 蓝金婚礼",
            "subtitle": "同一4250帧、相同相机；字幕关闭。",
            "before_label": "原柔光礼堂",
            "after_label": "蓝金婚礼",
            "before": str(before),
            "after": str(after),
            "doc": DOC,
        },
        {
            "id": "wedding-caption-palette",
            "title": "原字幕色 / 蓝金主题色",
            "subtitle": "同一新场景、同一4200帧，仅更换字幕配色与细柔光。",
            "before_label": "原字幕色",
            "after_label": "蓝金字幕",
            "before": str(mono),
            "after": str(color),
            "doc": DOC,
        },
    ]
    for key, number, off, label in [
        ("scattering", 4250, "control-scattering-off-4250.png", "后方局部散射"),
        ("halos", 4290, "control-new-halos-off-4290.png", "本轮新增光晕"),
    ]:
        pairs.append(
            {
                "id": "wedding-" + key,
                "title": label + " / 原生开关",
                "subtitle": "局部控制；仍保留其他照明与既有光晕。",
                "before_label": label + "关",
                "after_label": label + "开",
                "before": str(root / "production-v4" / off),
                "after": str(root / "production-v4" / f"wedding-{number}.png"),
                "doc": DOC,
            }
        )
    catalog["comparisons"] = pairs + [
        p for p in catalog["comparisons"] if p["id"] not in {r["id"] for r in pairs}
    ]
    group = next(g for g in catalog["knowledge_groups"] if g["id"] == "lighting")
    group["docs"] = [DOC] + [d for d in group["docs"] if d != DOC]
    write(catalog_file, catalog)
    shutil.copyfile(REPO / "docs" / DOC, root / DOC)
    shutil.copyfile(previous / "CREDITS.md", root / "CREDITS.md")
    for original in (previous / "licenses").glob("*"):
        if original.is_file():
            (root / "licenses").mkdir(exist_ok=True)
            shutil.copyfile(original, root / "licenses" / original.name)
    (root / "README.md").write_text(
        f"# 誓光 · 蓝金婚礼\n\n最终原声视频：`{movie}`\n\n无字幕灯光视频：`{bare_movie}`\n\n工程：`{master['target']}`。最终字幕由Python合成，不在Blender视口内。\n\n同段300帧／1080p60／五秒，未扩展全曲，待猪猪美术评价。正式工程production-v4，v1–v3为收敛光束的中间实验。\n\nreview含前后、字幕配色、散射／新增光晕开关和四处连续切换。笔记见 {DOC}。\n",
        encoding="utf-8",
    )
    write(
        root / "delivery.json",
        {
            "movie": str(movie),
            "movie_sha256": video["sha256"],
            "project": master["target"],
            "frames": 300,
            "seconds": 5,
            "video_audio_verified": True,
            "caption_groups": audit["group_order_sets"],
            "boundary_review_frames": boundaries,
            "effect_controls": effects,
            "previous_movies_preserved": True,
            "full_song_complete": False,
            "user_art_approval": False,
        },
    )
    print("BLUE_GOLD_WEDDING_PACKAGED", str(movie), flush=True)


if __name__ == "__main__":
    main()
