"""Package the verified official-caption study and add its offline Atlas entry."""

import argparse
import hashlib
import shutil
from pathlib import Path

import cv2
from package_fox_cinema import frame, panel, read, write
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
DOC = "DUET_CAPTION_STABILITY_AND_LIGHTING.md"
IDENTITY = "duet-captions-focused-v1"


def cache_picture(cache, number, destination):
    pixels = cv2.imread(
        str(cache / "beauty" / f"frame_{number:04d}beauty.png"), cv2.IMREAD_UNCHANGED
    )
    assert pixels.dtype.name == "uint16" and pixels.shape == (1080, 1920, 3)
    cv2.imencode(".png", (pixels / 257).round().astype("uint8"))[1].tofile(
        str(destination)
    )
    return destination


def review_boundaries(movie, audit, destination):
    boundaries = [
        audit["profile"]["render_start_frame"]
        + c["start_frame"]
        - audit["profile"]["source_start_frame"]
        for c in audit["profile"]["cues"][1:]
    ]
    capture = cv2.VideoCapture(str(movie))
    reviewed = []
    for boundary in boundaries:
        canvas = Image.new("RGB", (1440, 2 * 234), "#151b28")
        draw = ImageDraw.Draw(canvas)
        for i, number in enumerate(range(boundary - 3, boundary + 5)):
            capture.set(cv2.CAP_PROP_POS_FRAMES, number - 4140)
            ok, pixels = capture.read()
            assert ok
            canvas.paste(
                Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB)).resize(
                    (360, 202)
                ),
                (i % 4 * 360, i // 4 * 234),
            )
            draw.text(
                (i % 4 * 360 + 6, i // 4 * 234 + 207),
                f"global {number} / type {number + 1}",
                fill="white",
            )
            reviewed.append(number)
        canvas.save(destination / f"boundary-{boundary}-consecutive.jpg", quality=96)
    capture.release()
    return reviewed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    sample = root / "captions-5s-v2"
    lighting = root / "lighting-sample-5s-v1"
    movie = sample / "Franken_Duet_5s_Captions_REVIEW.mp4"
    light_movie = lighting / "Aether_Duet_5s_REVIEW.mp4"
    video = read(sample / "video-qa/video-verification.json")
    audio = read(sample / "audio-verification.json")
    audit = read(sample / "caption-layer-audit.json")
    master = read(root / "master-verification.json")
    for report in (
        video,
        audio,
        audit,
        master,
        read(lighting / "seam-qa/seam-verification.json"),
    ):
        assert report["passed"]
    assert video["decoded_frames"] == audit["frames"] == 300
    assert audit["size"] == [1920, 1080]
    assert len(audit["group_order_sets"]) == 5
    assert audit["front_frames_with_character_overlap"] > 0
    previous = Path(
        "D:/codex/output/MMD-Fox-StageArt-v2/sample-5s-v2/Aether_Duet_5s_REVIEW.mp4"
    )
    assert (
        hashlib.sha256(previous.read_bytes()).hexdigest()
        == "46a240c853ed82a421d399dcc3e2848d2baf966402e789e6c58076b179828868"
    )
    preserved = Path(
        "D:/codex/output/MMD-Quality-Integration-v1/linear-sequence-v2/duet_4200.exr"
    )
    assert (
        hashlib.sha256(preserved.read_bytes()).hexdigest()
        == "bb3a0e66e2b29bf912181e26bd21a645ded0796ca5111c88657985190b0c4529"
    )
    review = root / "review-v2"
    review.mkdir(exist_ok=True)
    before = frame(previous, 110, review / "previous-light-4250.png")
    new_light = cache_picture(args.cache, 4250, review / "focused-light-4250.png")
    panel(
        [(before, "前版舞台 · 同一帧"), (new_light, "聚焦灯光 · 左暖右冷")],
        review / "lighting-before-after.jpg",
    )
    pairs = [
        {
            "id": "caption-focused-light",
            "title": "平均舞台 / 聚焦冷暖",
            "subtitle": "同一 4250 帧、原动作与相机；字幕关闭。",
            "before_label": "前版舞台",
            "after_label": "聚焦灯光",
            "before": str(before),
            "after": str(new_light),
            "doc": DOC,
        }
    ]
    for number, label in ((4200, "整组前景小牌"), (4250, "整组背景大牌")):
        bare = cache_picture(
            args.cache, number, review / f"without-caption-{number}.png"
        )
        caption = sample / f"caption-{number}.png"
        assert caption.is_file()
        panel(
            [(bare, "无字幕 · 同一原生帧"), (caption, label)],
            review / f"caption-{number}-comparison.jpg",
        )
        pairs.append(
            {
                "id": f"caption-locked-{number}",
                "title": label,
                "subtitle": "同一原生 beauty 与官方字幕合成；前景不再局部挖开脸部。",
                "before_label": "无字幕",
                "after_label": label,
                "before": str(bare),
                "after": str(caption),
                "doc": DOC,
            }
        )
    reviewed = review_boundaries(movie, audit, review)
    recipe = {
        "id": IDENTITY,
        "status": "verified-five-second-study",
        "user_art_approval": False,
        "project": master["target"],
        "source": master["source"],
        "stage_profile": "presets/stages/hesperides-focused-light-v3.json",
        "caption_profile": "presets/typography/duet-official-locked-v2.json",
        "caption_cache": str(args.cache),
        "video": str(movie),
        "without_captions_video": str(light_movie),
        "frames": [4140, 4439],
        "fps": 60,
        "resolution": [1920, 1080],
        "bgm": "User-selected vocal FLAC from presets/projects/franken-duet-full-v1.json",
        "audio_start_seconds": 68.98333333333333,
        "typography_source_start_frame": 4141,
        "typography_audio_offset_bgm_minus_source_seconds": -0.03,
        "caption_method": "Official animation with fixed whole-group order; no front facial holdout",
        "limits": audit["limits"]
        + [
            "Five seconds only; full-song groups and portrait layout not adapted",
            "Native .blend contains lighting and mask source; final captions are composited by Python",
        ],
    }
    write(REPO / "presets/recipes" / f"{IDENTITY}.json", recipe)
    entry = {
        "id": IDENTITY,
        "title": "字入光 · 官方动效与冷暖舞台",
        "subtitle": "小字在前，大牌在后；用固定分组和聚焦灯光组织双人画面。",
        "collection": "CAPTIONS / FOCUSED LIGHT",
        "category": "post",
        "family": "guanhaizi",
        "aspect": "landscape",
        "status": "motion",
        "image": str(sample / "caption-4200.png"),
        "video": str(movie),
        "diagnostic_video": str(light_movie),
        "diagnostic_label": "无字幕灯光版 · 5s",
        "duration": 5,
        "fps": 60,
        "project": master["target"],
        "docs": [DOC, "ADVANCED_MMD_SUBTITLES.md", "FOX_STAGE_ART_DEEP_STUDY.md"],
        "configs": [
            recipe["stage_profile"],
            recipe["caption_profile"],
            f"presets/recipes/{IDENTITY}.json",
        ],
        "look": [
            "HIMEHINA 官方动效",
            "整组前后层固定",
            "黑字实心牌面",
            "左暖右冷与局部光区",
        ],
        "compatibility": "本双人礼堂五秒横屏；官方 Wide 字幕源和原生 PNG16 遮罩缓存均需在本机。",
        "evidence": [
            "300 原生帧／1080p60／指定原声验证通过",
            "逐帧审计五组字幕；前景不使用脸部遮罩，背景保护不透明人物",
            "完整教程音频自动转写与 20 个画面核对，重新布置响应光照的舞台",
            "独立重开十时点动作／相机相同，95 张贴图打包，旧归档未改动",
        ],
        "limits": [
            "五秒研究样片，待猪猪美术评价；非全曲完成",
            "黑底 MP4 的牌面重建和柔边插入均有适用范围",
            "场景 .blend 不含最终字幕，需运行缓存合成步骤",
        ],
        "command": f'python scripts/composite_duet_official_captions.py --cache-dir "{args.cache}" --profile presets/typography/duet-official-locked-v2.json --output-dir "D:/codex/output/Duet-Captions-New" --ffmpeg "D:/codex/temp/blender-mmd-video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"',
    }
    catalog_file = REPO / "catalog/library.json"
    catalog = read(catalog_file)
    catalog["entries"] = [entry] + [
        e for e in catalog["entries"] if e["id"] != IDENTITY
    ]
    catalog["comparisons"] = pairs + [
        p for p in catalog["comparisons"] if p["id"] not in {r["id"] for r in pairs}
    ]
    group = next(g for g in catalog["knowledge_groups"] if g["id"] == "post")
    group["docs"] = [DOC] + [d for d in group["docs"] if d != DOC]
    write(catalog_file, catalog)
    shutil.copyfile(REPO / "docs" / DOC, root / DOC)
    source = Path("D:/codex/output/MMD-Fox-StageArt-v2")
    credits = (source / "CREDITS.md").read_text(encoding="utf-8")
    (root / "CREDITS.md").write_text(
        credits
        + "\n\n本次动效字幕：HIMEHINA / Studio LaRa 官方 FrankensteinNoKaibutsu_Video_Full_Typography(Wide).mp4；本工程仅作布局、着色与前后层适配。\n学习参考：MiaoBox《MMD渲染，写给新手的场景打光思路》BV1mdXWB2EtV；观海子《亲亲小狐狸》及简介署名作者。不是作者原工程或原插件。\n",
        encoding="utf-8",
    )
    for original in (source / "licenses").glob("*"):
        if original.is_file():
            (root / "licenses").mkdir(exist_ok=True)
            shutil.copyfile(original, root / "licenses" / original.name)
    (root / "README.md").write_text(
        f"# 字入光 · 五秒双人样片\n\n有字幕原声视频：`{movie}`\n\n无字幕灯光视频：`{light_movie}`\n\n工程：`{master['target']}`。Blender 中为灯光和遮罩源；最终字幕由 Python 第二阶段合成，不在视口中显示。\n\n本轮只制作 4140–4439 的 300 帧、1080p60，不是双人全曲。保留现成相机、人物卡渲和烘焙物理。美术效果待猪猪评价。\n\n`review-v2` 含灯光前后、字幕前后和四个切换处各八张连续帧。学习与复用方法见 `{DOC}`；`captions-5s-v2` 包含逐帧层级审计与音视频验收。最终以 captions-5s-v2／review-v2 为准，captions-5s-v1 为边界检查中间版。旧版本、输入素材与旧线性归档保留。\n",
        encoding="utf-8",
    )
    write(
        root / "delivery.json",
        {
            "movie": str(movie),
            "sha256": video["sha256"],
            "project": master["target"],
            "frames": 300,
            "seconds": 5,
            "caption_groups": audit["group_order_sets"],
            "front_frames_with_character_overlap": audit[
                "front_frames_with_character_overlap"
            ],
            "boundary_review_frames": reviewed,
            "native_matte_and_beauty": str(args.cache),
            "old_movie_and_exr_preserved": True,
            "full_song_complete": False,
            "user_art_approval": False,
            "video_audio_verified": True,
        },
    )
    print("DUET_CAPTIONS_PACKAGED", str(movie), flush=True)


if __name__ == "__main__":
    main()
