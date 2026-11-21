"""Register an actually rendered and reviewed character-layer study in Atlas."""

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
IDENTITY = "duet-character-layers-v1"
DOC = "CHARACTER_LAYER_REFINEMENT.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    sample = root / "captions-5s-v1"
    movie = sample / "Franken_Duet_5s_CharacterLayers_Wedding_REVIEW.mp4"
    bare = sample / "Franken_Duet_5s_CharacterLayers_NoCaptions.mp4"
    project = root / "production-v2/Franken_Duet_Character_Layers.blend"
    master = read(root / "master-verification.json")
    manual = read(root / "manual-review.json")
    audit = read(sample / "caption-layer-audit.json")
    required_reports = [master, manual, audit]
    required_reports += [
        read(sample / name)
        for name in [
            "video-qa/video-verification.json",
            "bare-video-qa/video-verification.json",
            "video-qa-audio.json",
            "bare-video-qa-audio.json",
            "color-verification.json",
            "seam-qa/seam-verification.json",
        ]
    ]
    assert all(report["passed"] for report in required_reports)
    assert audit["frames"] == 300
    assert manual["movie_sha256"] == sha(movie) and manual["bare_sha256"] == sha(bare)
    assert project.is_file() and not manual.get("user_art_approval")
    review = root / "review"
    review.mkdir(exist_ok=True)
    previous = read(REPO / "presets/recipes/duet-grounded-color-v1.json")
    before = cache_picture(Path(previous["cache"]), 4290, review / "before-4290.png")
    after = cache_picture(args.cache, 4290, review / "after-4290.png")
    panel(
        [(before, "前版 · 叠加受光"), (after, "新版 · 分层受光与材质")],
        review / "before-after.jpg",
    )
    comparisons = [
        {
            "id": "character-layers-before-after",
            "title": "人物受光 / 同帧改进",
            "subtitle": "相同4290帧原生beauty，显示变换和相机保持一致。",
            "before_label": "Grounded前版",
            "after_label": "新人物层",
            "before": str(before),
            "after": str(after),
            "doc": DOC,
        }
    ]
    effects = []
    controls = root / "layer-controls-v2"
    complete = controls / "complete.png"
    a = np.asarray(Image.open(complete).convert("RGB"), dtype=np.float32)
    for key, title in [
        ("lighting-off", "一次受光色带"),
        ("ao-off", "短距接触AO"),
        ("hair-highlight-off", "方向性发丝高光"),
        ("cast-shadows-off", "原生灯光投影"),
    ]:
        off = controls / (key + ".png")
        b = np.asarray(Image.open(off).convert("RGB"), dtype=np.float32)
        delta = np.abs(a - b)
        assert delta.max() > 1, (key, "No measured visual effect")
        effects.append(
            {
                "layer": key,
                "mean_rgb_delta_255": float(delta.mean()),
                "max_rgb_delta_255": float(delta.max()),
            }
        )
        comparisons.append(
            {
                "id": "character-layers-" + key,
                "title": title + " / 同帧开关",
                "subtitle": "其余层保留；投影关闭不移除SDF与烘焙GI；色带关闭不移除物理闭包。",
                "before_label": "关",
                "after_label": "开",
                "before": str(off),
                "after": str(complete),
                "doc": DOC,
            }
        )
    boundaries = review_boundaries(movie, audit, review)
    recipe_path = "presets/recipes/" + IDENTITY + ".json"
    limits = [
        "限定同一双人模型、礼堂、灯组和五秒横屏；尚非全曲，待猪猪美术评价",
        "MMD Color保留原模型合成，并非已提取纯游戏Albedo",
        "综合Diffuse响应包含真实遮挡，但不是纯投影通道；Goo未运行",
        "没有新增空的原游戏Lightmap或鸣潮HM/HN；并非游戏Shader完整移植",
        "胸部适用性、动态检查边界和浏览器状态见独立报告",
    ]
    recipe = {
        "id": IDENTITY,
        "status": "verified-five-second-study",
        "project": str(project),
        "source": previous["project"],
        "character_profile": "presets/quality/duet-character-layers-v1.json",
        "caption_profile": "presets/typography/duet-blue-gold-wedding-v1.json",
        "cache": str(args.cache),
        "video": str(movie),
        "without_captions_video": str(bare),
        "frames": [4140, 4439],
        "fps": 60,
        "resolution": [1920, 1080],
        "audio_project": "presets/projects/franken-duet-full-v1.json",
        "audio_start_seconds": 4139 / 60,
        "output_color_contract": CONTRACT,
        "controls": effects,
        "diagnostic_records": str(root / "diagnostics-v3/diagnostic-records.json"),
        "user_art_approval": False,
        "limits": limits,
    }
    write(REPO / recipe_path, recipe)
    entry = {
        "id": IDENTITY,
        "title": "映光 · 人物材质分层",
        "subtitle": "一次受光色带、受控接触、银蓝与金色发带，保留五官与金属分区。",
        "collection": "CHARACTER / LAYERED LIGHT",
        "category": "character",
        "family": "genshin",
        "aspect": "landscape",
        "status": "motion",
        "image": str(after),
        "video": str(movie),
        "diagnostic_video": str(bare),
        "diagnostic_label": "无字幕人物审片 · 5s",
        "duration": 5,
        "fps": 60,
        "project": str(project),
        "docs": [
            DOC,
            "CHARACTER_LAYER_AUDIT.md",
            "CHARACTER_NPR_PLAYBOOK.md",
            "CHEST_SECONDARY_MOTION_VALIDATION.md",
        ],
        "configs": [
            recipe["character_profile"],
            recipe["caption_profile"],
            recipe_path,
        ],
        "look": [
            "分区明暗色",
            "SDF与真实遮挡",
            "短距离AO",
            "主灯驱动发丝",
            "保留透明与金属遮罩",
        ],
        "compatibility": "Blender 5.2.2 EEVEE；输入仅Grounded production-v3；原始VMD、礼堂、蓝金字幕和FLAC。",
        "evidence": [
            "原生300帧1080p60完整解码及音轨验证",
            "最终人物链三轴72原生帧测试",
            "同帧1080p四种层开关",
            "独立重开动作／相机／贴图与节点可达性检查",
        ],
        "limits": limits,
        "command": "See docs/CHARACTER_LAYER_REFINEMENT.md; scripts require version-matched inputs and new output directories.",
    }
    catalog = read(REPO / "catalog/library.json")
    catalog["entries"] = [entry] + [
        e for e in catalog["entries"] if e["id"] != IDENTITY
    ]
    catalog["comparisons"] = comparisons + [
        p
        for p in catalog["comparisons"]
        if p["id"] not in {c["id"] for c in comparisons}
    ]
    homes = {
        "render": [DOC, "CHARACTER_LAYER_AUDIT.md", "NPR_NEXT_EXPERIMENTS.md"],
        "production": ["CHEST_SECONDARY_MOTION_VALIDATION.md"],
        "tools": ["BROWSER_AUTONOMY.md"],
    }
    new_docs = {d for docs in homes.values() for d in docs}
    for group in catalog["knowledge_groups"]:
        group["docs"] = homes.get(group["id"], []) + [
            d for d in group["docs"] if d not in new_docs
        ]
    catalog["updated"] = "2026-11-13"
    write(REPO / "catalog/library.json", catalog)
    state = read(REPO / "catalog/current_state.json")
    prior_review = state["latest_review"]
    if prior_review["entry_id"] != IDENTITY:
        state["previous_review"] = prior_review
    new_review = {
        "entry_id": IDENTITY,
        "project": str(project),
        "video": str(movie),
        "sha256": sha(movie),
        "delivery_report": str(root / "delivery.json"),
        "scope": {
            "frames": [4140, 4439],
            "fps": 60,
            "resolution": [1920, 1080],
            "seconds": 5,
            "aspect": "landscape",
        },
        "technical_status": "passed-limited-scope",
        "art_status": "pending",
        "user_feedback": "新版人物分层已生成，等待猪猪实际审看；前版提出的质量目标继续保留",
        "user_art_approval": False,
    }
    if prior_review["entry_id"] == IDENTITY:
        for key in ("art_status", "user_feedback", "user_art_approval"):
            new_review[key] = prior_review[key]
    state["latest_review"] = new_review
    state["browser_research"] = {
        "date": "2026-11-13",
        "in_app_connection": "discovery_available_getTab_timeout",
        "runtime_service_exists": True,
        "chrome_control": "unavailable",
        "new_bilibili_transcript_obtained": False,
        "evidence": "docs/research/BROWSER_ACCESS_VALIDATION.json",
    }
    state["active_iteration"]["status"] = "delivered-limited-scope"
    state["current_task"] = (
        "新版五秒与分层、物理适用性、浏览器诊断交付；等待美术反馈；不自动恢复全曲"
    )
    write(REPO / "catalog/current_state.json", state)
    delivery = {
        "movie": str(movie),
        "movie_sha256": sha(movie),
        "without_captions_video": str(bare),
        "project": str(project),
        "frames": 300,
        "seconds": 5,
        "output_color_contract": CONTRACT,
        "video_audio_verified": True,
        "manual_review": manual,
        "caption_groups": audit["group_order_sets"],
        "boundary_review_frames": boundaries,
        "effect_controls": effects,
        "master_verification": master,
        "three_axis_diagnostics": str(
            root / "diagnostics-v3/Shader_Stability_3_Cases.mp4"
        ),
        "chest_validation": str(root / "CHEST_SECONDARY_MOTION_VALIDATION.md"),
        "chest_source_evidence": "D:/codex/output/MMD-Chest-Motion-Validation-v1/source-validation-v3/validation-report.json",
        "new_chest_simulation_performed": False,
        "previous_movie_preserved": True,
        "full_song_complete": False,
        "user_art_approval": False,
    }
    for doc in [
        DOC,
        "CHARACTER_LAYER_AUDIT.md",
        "CHEST_SECONDARY_MOTION_VALIDATION.md",
        "BROWSER_AUTONOMY.md",
        "NPR_NEXT_EXPERIMENTS.md",
    ]:
        shutil.copyfile(REPO / "docs" / doc, root / doc)
    old = Path("D:/codex/output/MMD-Duet-Shadow-Color-v1")
    shutil.copyfile(old / "CREDITS.md", root / "CREDITS.md")
    for original in (old / "licenses").glob("*"):
        if original.is_file():
            (root / "licenses").mkdir(exist_ok=True)
            shutil.copyfile(original, root / "licenses" / original.name)
    write(root / "delivery.json", delivery)
    (root / "README.md").write_text(
        f"# 映光 · 人物受光与材质\n\n五秒原声审片：`{movie}`\n\n无字幕：`{bare}`\n\n工程：`{project}`\n\n限定300原生帧／1080p60；未做全曲；等待猪猪美术反馈。字幕为独立Python后期。\n\nreview含同帧前后和字幕连续边界，layer-controls-v2含开关图，diagnostics-v3含转头、移灯、绕拍。胸部适用性与浏览器连接见同目录指南。\n",
        encoding="utf-8",
    )
    print("CHARACTER_LAYER_REVIEW_PACKAGED", movie, flush=True)


if __name__ == "__main__":
    main()
