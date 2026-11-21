"""Register the completed bounded reference-transfer review, preserving history."""

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from package_duet_captions import cache_picture
from review_video_color import CONTRACT

REPO = Path(__file__).resolve().parents[1]
IDENTITY = "duet-guanhai-transfer-v1"
DOC = "REFERENCE_TECHNIQUE_TRANSFER.md"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument(
        "--date", default=datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if (root / "delivery.json").exists():
        raise FileExistsError(root / "delivery.json")
    project = root / "production-v3/Franken_Duet_Reference_Transfer.blend"
    sample = root / "captions-5s"
    movie = sample / "Franken_Duet_5s_ReferenceTransfer_Wedding_REVIEW.mp4"
    bare = sample / "Franken_Duet_5s_ReferenceTransfer_NoCaptions.mp4"
    reports = [
        root / "master-verification.json",
        root / "control-verification.json",
        root / "diagnostic-review/diagnostics-verification.json",
        sample / "caption-layer-audit.json",
        sample / "video-qa/video-verification.json",
        sample / "bare-video-qa/video-verification.json",
        sample / "video-qa-audio.json",
        sample / "bare-video-qa-audio.json",
        sample / "color-verification.json",
        sample / "seam-qa/seam-verification.json",
        root / "manual-review.json",
    ]
    evidence = {path.relative_to(root).as_posix(): read(path) for path in reports}
    assert all(report["passed"] for report in evidence.values())
    manual, master = (
        evidence["manual-review.json"],
        evidence["master-verification.json"],
    )
    assert master["current_sha256"] == sha(project)
    assert manual["movie_sha256"] == sha(movie) and manual["bare_sha256"] == sha(bare)
    assert (
        manual["user_art_approval"] is False and manual["full_song_complete"] is False
    )
    assert (
        evidence["captions-5s/video-qa/video-verification.json"]["decoded_frames"]
        == 300
    )
    assert (
        evidence["captions-5s/bare-video-qa/video-verification.json"]["decoded_frames"]
        == 300
    )
    hero = cache_picture(args.cache, 4290, root / "review/native-4290.png")
    cache_picture(args.cache, 4250, root / "review/native-4250.png")
    limits = [
        "限定同一双人、礼堂和原帧4140–4439的五秒；全曲未交付，待猪猪美术评价",
        "借鉴外部教程原理，未恢复观海子原始Shader或达到其质量认证",
        "面向主灯的Diffuse仍是综合受光近似，不是纯visibility",
        "鼻部孤立暗块、脸颊塑形和前景视觉主次仍需精修",
        "本轮未新增游戏Lightmap、胸部solver或衣发烘焙；原有动作物理保留",
    ]
    recipe_path = "presets/recipes/" + IDENTITY + ".json"
    recipe = {
        "id": IDENTITY,
        "status": "verified-five-second-transfer",
        "project": str(project),
        "source": master["source"],
        "character_profile": "presets/quality/duet-guanhai-transfer-v1.json",
        "caption_profile": "presets/typography/duet-blue-gold-wedding-v1.json",
        "cache": str(args.cache),
        "video": str(movie),
        "without_captions_video": str(bare),
        "source_frames": [4140, 4439],
        "fps": 60,
        "resolution": [1920, 1080],
        "audio_start_seconds": 4139 / 60,
        "audio_gain": 0.87,
        "output_color_contract": CONTRACT,
        "user_art_approval": False,
        "limits": limits,
    }
    write(REPO / recipe_path, recipe)
    entry = {
        "id": IDENTITY,
        "title": "映光进阶 · 阴影与礼堂层次",
        "subtitle": "方向化受光、受控边光、镜面专用宽光与人物保护的前景明暗。",
        "collection": "CHARACTER / REFERENCE TRANSFER",
        "category": "character",
        "family": "guanhaizi",
        "aspect": "landscape",
        "status": "motion",
        "image": str(hero),
        "video": str(movie),
        "diagnostic_video": str(bare),
        "diagnostic_label": "无字幕审片 · 5s",
        "duration": 5,
        "fps": 60,
        "project": str(project),
        "docs": [
            DOC,
            "EXTERNAL_MMD_TECHNIQUES_2026_11_13.md",
            "CHARACTER_NPR_PLAYBOOK.md",
        ],
        "configs": [
            recipe["character_profile"],
            recipe["caption_profile"],
            recipe_path,
        ],
        "look": [
            "人物自阴影与形体分工",
            "银蓝／金色受控亮边",
            "金属宽反射",
            "局部前景明暗",
            "保留蓝金字幕",
        ],
        "compatibility": "Blender5.2.2 EEVEE；仅已指纹核对的CharacterLayers production-v2输入。",
        "evidence": [
            "2488项独立工程核查",
            "72原生帧三轴测试",
            "1080p六种开关对照",
            "最终字幕／无字幕各300帧全解码与音色／接缝检查",
        ],
        "limits": limits,
        "command": "See docs/REFERENCE_TECHNIQUE_TRANSFER.md; use exact input fingerprint and fresh output directories.",
    }
    library = read(REPO / "catalog/library.json")
    assert not any(e["id"] == IDENTITY for e in library["entries"])
    state = read(REPO / "catalog/current_state.json")
    state["as_of"] = args.date
    assert state["latest_review"]["entry_id"] == "duet-character-layers-v1"
    for review in [state.get("previous_review"), state["latest_review"]]:
        if not review:
            continue
        old = next(e for e in library["entries"] if e["id"] == review["entry_id"])
        old["art_review"] = {
            "status": review["art_status"],
            "as_of": state["as_of"],
            "feedback": review["user_feedback"],
        }
    if state.get("previous_review"):
        state.setdefault("review_history", []).append(state["previous_review"])
    state["previous_review"] = state["latest_review"]
    state["latest_review"] = {
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
        "user_feedback": "已完成外部技术移植五秒样片；等待猪猪审看，鼻部暗块和舞台前景主次仍待精修",
        "user_art_approval": False,
    }
    state["current_task"] = (
        "外部技术已实际移植并交付同段五秒；完成原生渲染和限定技术验收；美术待用户评价，不自动恢复全曲"
    )
    state["active_iteration"] = {
        "id": IDENTITY,
        "scope": "frames4140–4439, 1920x1080, 60fps, 5s",
        "status": "delivered-limited-scope",
        "user_authorized": True,
        "full_song": False,
    }
    state["current_learning_round"]["implemented_followup"] = {
        "id": IDENTITY,
        "guide": "docs/" + DOC,
        "scope": "limited principles transferred and locally tested; see delivery",
        "delivery": str(root / "delivery.json"),
    }
    state["current_learning_round"]["status"] = (
        "external-reading-completed; selected-principles-transferred-and-tested"
    )
    state["current_learning_round"]["bounded_video_delivered"] = True
    state["current_learning_round"].setdefault(
        "external_reading_report_directory",
        state["current_learning_round"]["report_directory"],
    )
    state["current_learning_round"]["report_directory"] = str(root)
    state["current_learning_round"]["implementation_guide"] = "docs/" + DOC
    library["entries"].insert(0, entry)
    library["updated"] = state["as_of"]
    render_group = next(g for g in library["knowledge_groups"] if g["id"] == "render")
    if DOC not in render_group["docs"]:
        render_group["docs"].insert(0, DOC)
    library["comparisons"].insert(
        0,
        {
            "id": "reference-transfer-before-after",
            "title": "人物与礼堂 / 同帧移植",
            "subtitle": "同4290帧原生beauty，相同显示变换、原动作与相机。",
            "before_label": "前版人物分层",
            "after_label": "外部技术移植",
            "before": str(Path(recipe["source"]).parents[1] / "review/after-4290.png"),
            "after": str(hero),
            "doc": DOC,
        },
    )
    for key, title, before_path, after_path in [
        (
            "stage-wide",
            "礼堂主次 / 同帧远景",
            Path(recipe["source"]).parents[1] / "review/native-4250.png",
            root / "review/native-4250.png",
        ),
        (
            "cast",
            "人物与礼堂投影 / 开关",
            root / "controls-4290/cast-shadows-off.png",
            root / "controls-4290/complete.png",
        ),
        (
            "reflection",
            "镜面专用宽光 / 开关",
            root / "controls-4290/reflection-off.png",
            root / "controls-4290/complete.png",
        ),
        (
            "stage-grade",
            "人物保护的前景明暗 / 开关",
            root / "controls-4290/stage-grade-off.png",
            root / "controls-4290/complete.png",
        ),
    ]:
        library["comparisons"].insert(
            1,
            {
                "id": "reference-transfer-" + key,
                "title": title,
                "subtitle": "限定本轮同帧对照；投影关闭仍保留形体、SDF及烘焙GI。",
                "before_label": "前版" if key == "stage-wide" else "关",
                "after_label": "新版" if key == "stage-wide" else "开",
                "before": str(before_path),
                "after": str(after_path),
                "doc": DOC,
            },
        )
    write(REPO / "catalog/library.json", library)
    write(REPO / "catalog/current_state.json", state)
    profile = read(REPO / "presets/projects/franken-duet-full-v1.json")
    profile["latest_reference_transfer_review"] = str(movie)
    profile["status"] = (
        "latest five-second reference-transfer review rendered and verified; user art review pending; full song not delivered or rendering"
    )
    profile["active_contract_state"] = "catalog/current_state.json"
    write(REPO / "presets/projects/franken-duet-full-v1.json", profile)
    delivery = {
        "movie": str(movie),
        "movie_sha256": sha(movie),
        "without_captions_video": str(bare),
        "project": str(project),
        "project_sha256": sha(project),
        "source_frames": [4140, 4439],
        "frames": 300,
        "seconds": 5,
        "fps": 60,
        "resolution": [1920, 1080],
        "output_color_contract": CONTRACT,
        "reports": list(evidence),
        "master_checks": len(master["checks"]),
        "manual_review": manual,
        "full_song_complete": False,
        "new_chest_simulation_performed": False,
        "user_art_approval": False,
        "limits": limits,
    }
    write(root / "delivery.json", delivery)
    (root / "README.md").write_text(
        "# 外部技术移植 · 五秒审片\n\n"
        "字幕原声版：`captions-5s/Franken_Duet_5s_ReferenceTransfer_Wedding_REVIEW.mp4`\n\n"
        "无字幕版：`captions-5s/Franken_Duet_5s_ReferenceTransfer_NoCaptions.mp4`\n\n"
        "本轮最终工程：`production-v3/Franken_Duet_Reference_Transfer.blend`。production-v1/v2为保留的过程版本。\n\n"
        "原帧4140–4439，300原生帧，1920×1080/60fps；固定FLAC原声输入，MP4编码AAC。未交付全曲。\n\n"
        "工程保留全曲动画；字幕在外部合成。此次正式渲染和验收仅覆盖上述五秒，打开旧GUI不会自动切换到新工程。\n\n"
        "review含同帧对照；controls-4290含六种消融；diagnostics与diagnostic-review含三轴测试；delivery.json登记实际验收。\n\n"
        "鼻部孤立暗块、脸颊塑形及前景主次仍可提升，等待猪猪美术评价。素材署名和随包使用限制见CREDITS.md及licenses。\n",
        encoding="utf-8",
    )
    shutil.copyfile(REPO / "docs" / DOC, root / DOC)
    external_doc = "EXTERNAL_MMD_TECHNIQUES_2026_11_13.md"
    shutil.copyfile(REPO / "docs" / external_doc, root / external_doc)
    (root / "research").mkdir(exist_ok=True)
    for name in (
        "EXTERNAL_TOON_SHADOW_2026_11_13.json",
        "EXTERNAL_RAY_MMD_2026_11_13.json",
        "EXTERNAL_MATERIAL_LIGHTING_2026_11_13.json",
    ):
        shutil.copyfile(REPO / "docs/research" / name, root / "research" / name)
    shutil.copyfile(REPO / "docs/CREDITS_FRANKEN_DUET.md", root / "CREDITS.md")
    old = Path("D:/codex/output/MMD-Duet-Shadow-Color-v1/licenses")
    for original in old.glob("*"):
        if original.is_file():
            (root / "licenses").mkdir(exist_ok=True)
            shutil.copyfile(original, root / "licenses" / original.name)
    print("REFERENCE_TRANSFER_DELIVERED", movie, flush=True)


if __name__ == "__main__":
    main()
