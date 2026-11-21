"""Package the verified shadow/color review without replacing accepted baselines."""

import argparse
import hashlib
import shutil
from pathlib import Path

import numpy as np
from package_duet_captions import cache_picture, review_boundaries
from package_fox_cinema import panel, read, write
from PIL import Image
from review_video_color import CONTRACT

REPO = Path(__file__).resolve().parents[1]
IDENTITY = "duet-grounded-color-v1"
DOC = "SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md"


def controls(root):
    production = root / "production-v3"
    review = root / "review"
    review.mkdir(exist_ok=True)
    actual = production / "grounded-4250.png"
    a = np.asarray(Image.open(actual).convert("RGB"), np.float32)
    results = []
    for key, filename, title in [
        ("cast", "control-key-shadow-off-4250.png", "人物主投影"),
        ("contact", "control-contact-off-4250.png", "近地接触AO"),
    ]:
        off = production / filename
        b = np.asarray(Image.open(off).convert("RGB"), np.float32)
        delta = abs(a - b)
        assert delta.mean() > 0.01 and delta.max() > 2
        results.append(
            {
                "effect": key,
                "mean_absolute_rgb_difference_255": float(delta.mean()),
                "max_difference": float(delta.max()),
                "fraction_pixels_over_one": float((delta.max(2) > 1).mean()),
            }
        )
        panel(
            [(off, title + "关"), (actual, title + "开")], review / f"{key}-control.jpg"
        )
        crops = []
        for source, label in [(off, "关"), (actual, "开")]:
            path = review / f"{key}-floor-{label}.png"
            Image.open(source).crop((565, 775, 1610, 1060)).save(path)
            crops.append((path, title + label + " · 地面局部"))
        panel(crops, review / f"{key}-floor-control.jpg")
    for key, off_name, title in [
        ("self-shadow", "control-self-cast-off-4290.png", "人物真实遮挡"),
        ("ink", "control-previous-ink-4290.png", "人物描边宽度"),
    ]:
        on, off = production / "grounded-4290.png", production / off_name
        delta = abs(
            np.asarray(Image.open(on).convert("RGB"), np.float32)
            - np.asarray(Image.open(off).convert("RGB"), np.float32)
        )
        assert delta.mean() > 0.01 and delta.max() > 2
        results.append(
            {
                "effect": key,
                "mean_absolute_rgb_difference_255": float(delta.mean()),
                "max_difference": float(delta.max()),
            }
        )
        old_label, new_label = (
            ("遮挡关闭", "遮挡开启") if key == "self-shadow" else ("旧线宽", "加粗线宽")
        )
        panel(
            [(off, title + old_label), (on, title + new_label)],
            review / f"{key}-control.jpg",
        )
        for actor, box in [
            ("aksiniya", (285, 235, 535, 475)),
            ("aether", (1435, 385, 1695, 660)),
        ]:
            crops = []
            for path, label in [(off, old_label), (on, new_label)]:
                target = review / f"{key}-{actor}-{label}.png"
                Image.open(path).crop(box).save(target)
                crops.append((target, title + " · " + label))
            panel(crops, review / f"{key}-{actor}-control.jpg", width=500)
    write(
        review / "effect-controls.json",
        {
            "measurements": results,
            "limits": "Same-frame native controls retain all other lighting and GI. Numeric differences prove a contribution, not quality; stochastic render variation is not fully excluded.",
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
        print("GROUNDING_CONTROLS_PACKAGED", flush=True)
        return
    assert args.cache
    sample, review = root / "captions-5s-v2", root / "review"
    movie = sample / "Franken_Duet_5s_Grounded_Wedding_REVIEW.mp4"
    bare = sample / "Franken_Duet_5s_Grounded_NoCaptions.mp4"
    master = read(root / "master-verification-v3.json")
    audit = read(sample / "caption-layer-audit.json")
    color = read(sample / "color-verification.json")
    manual = read(root / "manual-review.json")
    reports = [master, audit, color, manual]
    reports += [
        read(sample / p)
        for p in (
            "video-qa/video-verification.json",
            "bare-video-qa/video-verification.json",
            "video-qa-audio.json",
            "bare-video-qa-audio.json",
            "seam-qa/seam-verification.json",
        )
    ]
    assert all(r["passed"] for r in reports)
    assert master["grounding_verification"] and audit["frames"] == 300
    assert manual["movie_sha256"] == hashlib.sha256(movie.read_bytes()).hexdigest()
    assert manual["bare_sha256"] == hashlib.sha256(bare.read_bytes()).hexdigest()
    old = Path("D:/codex/output/MMD-Duet-Blue-Gold-Wedding-v1")
    old_movie = old / "captions-5s-v1/Franken_Duet_5s_Wedding_REVIEW.mp4"
    assert (
        hashlib.sha256(old_movie.read_bytes()).hexdigest()
        == "b3dc258a07b3295f597e668522b29d4c0385db0c85684ca7edc554cac28f89c9"
    )
    before = cache_picture(
        Path("D:/codex/temp/Duet-Blue-Gold-Wedding-v1/final-cache"),
        4250,
        review / "shadows-before-4250.png",
    )
    after = cache_picture(args.cache, 4250, review / "shadows-after-4250.png")
    panel(
        [(before, "旧蓝金婚礼"), (after, "新版 · 接地与受光")],
        review / "grounding-before-after.jpg",
    )
    boundaries = review_boundaries(movie, audit, review)
    recipe_path = f"presets/recipes/{IDENTITY}.json"
    recipe = {
        "id": IDENTITY,
        "status": "verified-five-second-study",
        "project": master["target"],
        "source": master["source"],
        "shadow_profile": "presets/stages/hesperides-grounded-shadows-v1.json",
        "graphic_profile": "presets/quality/duet-graphic-self-shadow-v1.json",
        "caption_profile": "presets/typography/duet-blue-gold-wedding-v1.json",
        "inherited_lighting": [
            "presets/stages/hesperides-soft-top-rim-v1.json",
            "presets/stages/hesperides-blue-gold-wedding-v1.json",
        ],
        "output_color_contract": CONTRACT,
        "cache": str(args.cache),
        "video": str(movie),
        "without_captions_video": str(bare),
        "frames": [4140, 4439],
        "fps": 60,
        "resolution": [1920, 1080],
        "audio_project": "presets/projects/franken-duet-full-v1.json",
        "audio_start_seconds": 4139 / 60,
        "controls": effects,
        "user_art_approval": False,
        "limits": [
            "仅五秒横屏样片，尚非全曲，待猪猪美术评价",
            "美术化灯光链接、近地AO，脸部SDF与真实遮挡组合",
            "SDR电脑sRGB审片约定，非BT.1886调色监看母版",
            "未确认PotPlayer具体设置及其与其他播放器的一致性",
        ],
    }
    write(REPO / recipe_path, recipe)
    entry = {
        "id": IDENTITY,
        "title": "落影 · 接地与色彩",
        "subtitle": "刘海与身体的真实遮挡、加厚黑线、脚底接触，配套明确色彩的蓝金婚礼审片。",
        "collection": "GROUNDING / SDR REVIEW",
        "category": "stage",
        "family": "guanhaizi",
        "aspect": "landscape",
        "status": "motion",
        "image": str(after),
        "video": str(movie),
        "diagnostic_video": str(bare),
        "diagnostic_label": "无字幕接地版 · 5s",
        "duration": 5,
        "fps": 60,
        "project": master["target"],
        "docs": [DOC, "BLUE_GOLD_WEDDING_STUDY.md", "FOX_STAGE_ART_DEEP_STUDY.md"],
        "configs": [
            recipe["shadow_profile"],
            recipe["graphic_profile"],
            recipe["caption_profile"],
            *recipe["inherited_lighting"],
            recipe_path,
        ],
        "look": [
            "定向地面投影",
            "几何近地AO",
            "SDF与真实刘海投影",
            "分区加粗近黑描边",
            "明确SDR色彩",
        ],
        "compatibility": "双人礼堂横屏五秒；Blender 5.2.2 EEVEE；需官方字幕源、原声FLAC及原生缓存。",
        "evidence": [
            "300原生帧／1080p60／指定原声验证",
            "十时点动作／相机相同，95贴图打包",
            "同帧主投影／接触AO／自身投影／线宽原生开关",
            "编码及混音后四项色彩标记验证，矩阵像素往返核对",
            "固定字幕层级逐帧审计，连续切换目视检查",
        ],
        "limits": recipe["limits"],
        "command": f'python scripts/composite_duet_official_captions.py --cache-dir "{args.cache}" --profile presets/typography/duet-blue-gold-wedding-v1.json --output-dir "D:/codex/output/Grounded-New-Captions" --ffmpeg "D:/codex/temp/blender-mmd-video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"',
    }
    catalog_file = REPO / "catalog/library.json"
    catalog = read(catalog_file)
    catalog["entries"] = [entry] + [
        e for e in catalog["entries"] if e["id"] != IDENTITY
    ]
    for previous in catalog["entries"]:
        if previous["id"] == "duet-blue-gold-wedding-v1":
            warning = "旧MP4缺明确色彩标签；新的审片色彩流程见落影版，原文件保留"
            if warning not in previous["limits"]:
                previous["limits"].append(warning)
    pairs = [
        {
            "id": "grounding-before-after",
            "title": "旧蓝金婚礼 / 接地与受光",
            "subtitle": "同一4250帧、原生beauty缓存，避免旧视频未知色彩矩阵干扰。",
            "before_label": "旧蓝金婚礼",
            "after_label": "新增接地",
            "before": str(before),
            "after": str(after),
            "doc": DOC,
        }
    ]
    for key, filename, title in [
        ("cast", "control-key-shadow-off-4250.png", "人物主投影"),
        ("contact", "control-contact-off-4250.png", "近地接触AO"),
    ]:
        pairs.append(
            {
                "id": "grounding-" + key,
                "title": title + " / 原生开关",
                "subtitle": "同帧，其他灯光与GI保留；完整图与地面局部见交付review。",
                "before_label": title + "关",
                "after_label": title + "开",
                "before": str(root / "production-v3" / filename),
                "after": str(root / "production-v3/grounded-4250.png"),
                "doc": DOC,
            }
        )
    for key, filename, title in [
        ("self-shadow", "control-self-cast-off-4290.png", "人物真实遮挡"),
        ("ink", "control-previous-ink-4290.png", "人物描边加粗"),
    ]:
        pairs.append(
            {
                "id": "grounding-" + key,
                "title": title + " / 原生对照",
                "subtitle": "同一4290帧；自身阴影控制保留SDF和形体明暗；线宽控制保留新边色。",
                "before_label": "遮挡关" if key == "self-shadow" else "旧线宽",
                "after_label": "遮挡开" if key == "self-shadow" else "加粗线宽",
                "before": str(root / "production-v3" / filename),
                "after": str(root / "production-v3/grounded-4290.png"),
                "doc": DOC,
            }
        )
    catalog["comparisons"] = pairs + [
        p for p in catalog["comparisons"] if p["id"] not in {x["id"] for x in pairs}
    ]
    group = next(g for g in catalog["knowledge_groups"] if g["id"] == "lighting")
    group["docs"] = [DOC] + [d for d in group["docs"] if d != DOC]
    write(catalog_file, catalog)
    shutil.copyfile(REPO / "docs" / DOC, root / DOC)
    shutil.copyfile(old / "CREDITS.md", root / "CREDITS.md")
    for original in (old / "licenses").glob("*"):
        if original.is_file():
            (root / "licenses").mkdir(exist_ok=True)
            shutil.copyfile(original, root / "licenses" / original.name)
    (root / "README.md").write_text(
        f"# 落影 · 接地与色彩\n\n最终原声视频：`{movie}`\n\n无字幕版：`{bare}`\n\n工程：`{master['target']}`。字幕独立Python合成，不在Blender视口中。\n\n300原生帧／1080p60／五秒，仅同段；未扩展全曲，待猪猪美术评价。review含同帧前后、投影与接触开关及连续字幕切换。色彩合同为SDR电脑sRGB审片，PotPlayer具体设置未确认。\n",
        encoding="utf-8",
    )
    with (root / "README.md").open("a", encoding="utf-8") as stream:
        stream.write(
            "\n最终版本为production-v3／captions-5s-v2。人物刘海与身体使用真实遮挡，脸部SDF保留，黑线按材质分区加厚。production-v2为弃用的脸部凹凸实验；lighting-sample-5s-v1是追加要求前中止的部分渲染，不能当最终视频。\n"
        )
    write(
        root / "delivery.json",
        {
            "movie": str(movie),
            "movie_sha256": hashlib.sha256(movie.read_bytes()).hexdigest(),
            "without_captions_video": str(bare),
            "project": master["target"],
            "frames": 300,
            "seconds": 5,
            "output_color_contract": CONTRACT,
            "video_audio_verified": True,
            "manual_review": manual,
            "caption_groups": audit["group_order_sets"],
            "boundary_review_frames": boundaries,
            "effect_controls": effects,
            "previous_movie_preserved": True,
            "full_song_complete": False,
            "user_art_approval": False,
            "potplayer_settings_verified": False,
        },
    )
    print("GROUNDED_REVIEW_PACKAGED", movie, flush=True)


if __name__ == "__main__":
    main()
