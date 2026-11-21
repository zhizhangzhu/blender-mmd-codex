"""Archive a verified soft-top/rim revision with actual lighting comparisons."""

import argparse
import hashlib
import shutil
from pathlib import Path

import numpy as np
from package_duet_captions import cache_picture, review_boundaries
from package_fox_cinema import frame, panel, read, write
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
IDENTITY = "duet-soft-top-rim-v1"
DOC = "SOFT_TOP_RIM_LIGHTING.md"


def effect_controls(root):
    production = root / "production-v2"
    review = root / "review"
    review.mkdir(exist_ok=True)
    results = []
    for key, on, off, label in [
        (
            "direct-soft",
            "soft-4250.png",
            "control-direct-soft-off-4250.png",
            "新增柔光的直接贡献",
        ),
        ("rim", "soft-4290.png", "control-rim-off-4290.png", "人物逆光与补充边缘"),
    ]:
        a = np.asarray(Image.open(production / on).convert("RGB"), np.float32)
        b = np.asarray(Image.open(production / off).convert("RGB"), np.float32)
        delta = abs(a - b)
        assert delta.mean() > 0.01, (key, "No visible light contribution")
        results.append(
            {
                "effect": key,
                "mean_absolute_rgb_difference_255": float(delta.mean()),
                "fraction_pixels_over_one": float((delta.max(2) > 1).mean()),
            }
        )
        panel(
            [(production / off, label + " · 关"), (production / on, label + " · 开")],
            review / f"{key}-control.jpg",
        )
    write(
        review / "effect-controls.json",
        {
            "measurements": results,
            "limits": "Direct-soft off keeps the newly baked GI and albedo. Pixel difference proves a contribution, not quality or reference similarity.",
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
    controls = effect_controls(root)
    if args.controls_only:
        print("SOFT_LIGHT_CONTROLS_VERIFIED", flush=True)
        return
    assert args.cache
    sample = root / "captions-5s-v1"
    lighting = root / "lighting-sample-5s-v1"
    movie = sample / "Franken_Duet_5s_Captions_REVIEW.mp4"
    bare_movie = lighting / "Aether_Duet_5s_REVIEW.mp4"
    master = read(root / "master-verification.json")
    video = read(sample / "video-qa/video-verification.json")
    audit = read(sample / "caption-layer-audit.json")
    for report in (
        master,
        video,
        audit,
        read(sample / "audio-verification.json"),
        read(lighting / "seam-qa/seam-verification.json"),
    ):
        assert report["passed"]
    assert (
        master["softlight_verification"]
        and audit["frames"] == video["decoded_frames"] == 300
    )
    previous_root = Path("D:/codex/output/MMD-Duet-Captions-Contrast-v1")
    old_movie = previous_root / "captions-5s-v2/Franken_Duet_5s_Captions_REVIEW.mp4"
    assert (
        hashlib.sha256(old_movie.read_bytes()).hexdigest()
        == "8c42d49c1163a4d74e89e86b0f65ff838ea3296d02ee14745f57ba6edd0adb5f"
    )
    old_bare = previous_root / "lighting-sample-5s-v1/Aether_Duet_5s_REVIEW.mp4"
    assert (
        hashlib.sha256(old_bare.read_bytes()).hexdigest()
        == "b9e4d421cf9d88230d7a5abefccf40a607609a4e340dfd7cdfe9f3cef6bfc12f"
    )
    review = root / "review"
    before = frame(old_bare, 110, review / "previous-light-4250.png")
    after = cache_picture(args.cache, 4250, review / "soft-light-4250.png")
    panel(
        [(before, "前版 · 暗部偏低"), (after, "柔光／顶光／逆光")],
        review / "lighting-before-after.jpg",
    )
    boundaries = review_boundaries(movie, audit, review)
    recipe = {
        "id": IDENTITY,
        "status": "verified-five-second-study",
        "user_art_approval": False,
        "project": master["target"],
        "source": master["source"],
        "stage_profile": "presets/stages/hesperides-soft-top-rim-v1.json",
        "caption_profile": "presets/typography/duet-official-locked-v2.json",
        "caption_cache": str(args.cache),
        "frames": [4140, 4439],
        "fps": 60,
        "resolution": [1920, 1080],
        "video": str(movie),
        "without_captions_video": str(bare_movie),
        "audio_project": "presets/projects/franken-duet-full-v1.json",
        "audio_start_seconds": 68.98333333333333,
        "controls": controls,
        "limits": [
            "Five seconds only; waiting for user art feedback",
            "NPR rim is art-directed, not fully occlusion-aware physical lighting",
            "Final captions require the separate Python compositor",
        ],
    }
    write(REPO / f"presets/recipes/{IDENTITY}.json", recipe)
    entry = {
        "id": IDENTITY,
        "title": "柔映 · 顶光与逆光",
        "subtitle": "提亮走道与花卉，用柔和顶光和暖色背光保留人物层次。",
        "collection": "SOFT LIGHT / TOP & RIM",
        "category": "stage",
        "family": "guanhaizi",
        "aspect": "landscape",
        "status": "motion",
        "image": str(after),
        "video": str(movie),
        "diagnostic_video": str(bare_movie),
        "diagnostic_label": "无字幕灯光版 · 5s",
        "duration": 5,
        "fps": 60,
        "project": master["target"],
        "docs": [DOC, "DUET_CAPTION_STABILITY_AND_LIGHTING.md"],
        "configs": [recipe["stage_profile"], f"presets/recipes/{IDENTITY}.json"],
        "look": [
            "大面积柔光提亮暗部",
            "上方软光区",
            "暖色后侧亮边",
            "官方字幕固定层级",
        ],
        "compatibility": "固定双人礼堂五秒横屏；Blender 5.2.2 EEVEE。字幕仍需独立合成。",
        "evidence": [
            "300 原生帧／1080p60／指定原声验收",
            "新增柔光直接贡献和人物逆光原生开关对照",
            "独立重开十时点动作、相机与焦距相同；脸部排除补充边缘",
            "官方字幕300帧审计与四处切换连续帧检查",
        ],
        "limits": [
            "根据猪猪过暗反馈的新候选，尚未获美术认可",
            "柔光关闭图保留当前GI；不等于全部提亮关闭",
            "仅五秒，未扩展全曲、竖屏或新运镜",
        ],
        "command": f'python scripts/render_duet_sample.py --blend "{master["target"]}" --output-dir "D:/codex/output/Soft-Light-New/sample" --logs "D:/codex/temp/Soft-Light-New/logs" --start 4140 --frames 300 --workers 2 --caption-cache-dir "D:/codex/temp/Soft-Light-New/cache"',
    }
    catalog_file = REPO / "catalog/library.json"
    catalog = read(catalog_file)
    catalog["entries"] = [entry] + [
        e for e in catalog["entries"] if e["id"] != IDENTITY
    ]
    pairs = [
        {
            "id": "soft-light-before-after",
            "title": "暗部偏低 / 柔光提亮",
            "subtitle": "同一4250帧；场景真实补光，人物曝光与字幕不整体拉升。",
            "before_label": "前版聚焦舞台",
            "after_label": "柔光、顶光与逆光",
            "before": str(before),
            "after": str(after),
            "doc": DOC,
        }
    ]
    for key, actual, control, label in [
        (
            "direct-soft",
            "soft-4250.png",
            "control-direct-soft-off-4250.png",
            "柔光直接贡献",
        ),
        ("rim", "soft-4290.png", "control-rim-off-4290.png", "人物逆光与边缘"),
    ]:
        pairs.append(
            {
                "id": "soft-light-" + key,
                "title": label + " / 原生开关",
                "subtitle": "相同帧、相同相机；柔光关闭时仍保留当前GI和反射率。",
                "before_label": label + "关",
                "after_label": label + "开",
                "before": str(root / "production-v2" / control),
                "after": str(root / "production-v2" / actual),
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
    shutil.copyfile(previous_root / "CREDITS.md", root / "CREDITS.md")
    for original in (previous_root / "licenses").glob("*"):
        if original.is_file():
            (root / "licenses").mkdir(exist_ok=True)
            shutil.copyfile(original, root / "licenses" / original.name)
    (root / "README.md").write_text(
        f"# 柔映 · 顶光与逆光\n\n有字幕原声视频：`{movie}`\n\n无字幕灯光视频：`{bare_movie}`\n\n工程：`{master['target']}`。最终字幕由Python合成，不在Blender视口中。\n\n同段300帧／1080p60／五秒，未扩展全曲，等待猪猪美术评价。正式工程为production-v2，production-v1是地面偏亮的中间实验。\n\nreview含旧新版灯光、柔光／逆光开关和四处字幕切换连续帧；学习与复用说明见 {DOC}。\n",
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
            "effect_controls": controls,
            "previous_movies_preserved": True,
            "full_song_complete": False,
            "user_art_approval": False,
        },
    )
    print("SOFT_TOP_RIM_PACKAGED", str(movie), flush=True)


if __name__ == "__main__":
    main()
