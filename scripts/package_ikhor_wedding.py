"""Register only the completed, hash-bound Aksiniya/Ikhor five-second review."""

import argparse
import re
import shutil
from pathlib import Path

from package_duet_captions import cache_picture
from package_reference_transfer import read, sha, write
from review_video_color import CONTRACT

REPO = Path(__file__).resolve().parents[1]
IDENTITY = "franken-ikhor-bold-wedding-v1"
GUIDE = "IKHOR_BOLD_WEDDING_PRODUCTION.md"
CREDITS = "CREDITS_AKSINIYA_IKHOR.md"
REJECTED_SHA = "283acdf2f1063fae32b0ed49caed07952706ff4d7b9ed1675490fa7ad021a0c1"
DOCS = (GUIDE, CREDITS, "IKHOR_SLEEVE_REPAIR.md")
RESEARCH = (
    "GRAY_EYED_PRIMORDIAL_MODEL_2026_11_14.json",
    "PRIMORDIAL_ONE_BACKGROUND_MODEL_2026_11_14.json",
)


def copy_guide(source, destination):
    """Keep bundled links local; make remaining repository references explicit."""

    def resolve_link(match):
        target = match.group(1)
        if ":" in target or target.startswith(("#", "/")):
            return match.group(0)
        path, marker, anchor = target.partition("#")
        actual = (source.parent / path).resolve()
        assert actual.is_file(), actual
        if actual.parent == REPO / "docs" and actual.name in DOCS:
            link = actual.name
        elif actual.parent == REPO / "docs/research" and actual.name in RESEARCH:
            link = "research/" + actual.name
        else:
            link = actual.as_posix()
        return "](" + link + (marker + anchor if marker else "") + ")"

    content = re.sub(
        r"\]\(([^)\s]+)\)", resolve_link, source.read_text(encoding="utf-8-sig")
    )
    destination.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--master-sha256", required=True)
    parser.add_argument("--production-dir", default="production-v7")
    parser.add_argument("--native-dir", default="native-5s-v2")
    parser.add_argument("--caption-dir", default="captions-5s-v3")
    parser.add_argument("--date", default="2026-11-14")
    args = parser.parse_args()
    root = args.root.resolve()
    assert not (root / "delivery.json").exists()
    project = root / args.production_dir / "Franken_Aksiniya_Ikhor_Bold_Wedding.blend"
    sample = root / args.caption_dir
    master_sha = sha(project)
    assert master_sha == args.master_sha256 and master_sha != REJECTED_SHA
    production = Path(args.production_dir).as_posix()
    captions = Path(args.caption_dir).as_posix()
    movie = sample / "Franken_Duet_5s_Ikhor_Wedding_REVIEW.mp4"
    bare = sample / "Franken_Duet_5s_Ikhor_NoCaptions.mp4"
    for doc in DOCS:
        assert (REPO / "docs" / doc).is_file()
    research_sources = [REPO / "docs/research" / name for name in RESEARCH]
    ikhor_terms = project.parents[2] / "MMD-Ikhor-Model-v1/source/Ikhor/RM.txt"
    other_licenses = [
        path
        for path in Path("D:/codex/output/MMD-Guanhai-Transfer-v1/licenses").glob("*")
        if path.is_file()
    ]
    for path in [*research_sources, ikhor_terms, *other_licenses]:
        assert path.is_file(), path
    evidence_paths = [
        f"{production}/master-verification.json",
        "sleeve-review/geometry-verification.json",
        "sleeve-review/visual-review.json",
        "diagnostic-review/diagnostics-verification.json",
        "caption-matte-review/cache-provenance-v3.json",
        "caption-matte-review/coverage-positive.json",
        "caption-matte-review/matte-verification.json",
        f"{captions}/caption-layer-audit.json",
        f"{captions}/video-qa/video-verification.json",
        f"{captions}/bare-video-qa/video-verification.json",
        f"{captions}/video-qa-audio.json",
        f"{captions}/bare-video-qa-audio.json",
        f"{captions}/color-verification.json",
        f"{captions}/seam-qa/seam-verification.json",
        "manual-review.json",
    ]
    evidence = {name: read(root / name) for name in evidence_paths}
    assert all(report["passed"] for report in evidence.values())
    master_report = evidence[evidence_paths[0]]
    assert master_sha == master_report["project_sha256"]
    assert master_report["beauty_300_reuse_eligible"] is True
    beauty_source_sha = master_report["source_sha256"]
    for name in (
        "sleeve-review/geometry-verification.json",
        "sleeve-review/visual-review.json",
    ):
        assert evidence[name]["project_sha256"] == beauty_source_sha
    integration = read(root / "production-v6/sleeve-integration.json")
    assert integration["project_sha256"] == beauty_source_sha
    matte_provenance = evidence["caption-matte-review/cache-provenance-v3.json"]
    assert matte_provenance["project_sha256"] == master_sha
    assert matte_provenance["beauty_source_project_sha256"] == beauty_source_sha
    assert matte_provenance["beauty_identical_to_verified_v6"] is True
    assert matte_provenance["rejected_v4_frames_reused"] is False
    assert Path(matte_provenance["caption_cache"]).resolve() == args.cache.resolve()
    assert evidence["caption-matte-review/matte-verification.json"]["source_sha256"] == master_sha
    coverage = evidence["caption-matte-review/coverage-positive.json"]
    assert coverage["project_sha256"] == master_sha and coverage["tested_frames"] == 300
    assert coverage["behind_frames_tested"] == 87
    assert sha(Path(matte_provenance["source_matte_report"])) == matte_provenance["source_matte_report_sha256"]
    intent = read(root / "final-render-intent-v6.json")
    assert intent["project_sha256"] == beauty_source_sha
    assert intent["reused_rejected_frames"] is False
    beauty_project = Path(master_report["source"]).resolve()
    assert Path(intent["project"]).resolve() == beauty_project
    assert Path(intent["fresh_caption_cache"]).resolve() == Path(matte_provenance["source_beauty_cache"]).resolve()
    assert (
        Path(intent["fresh_native_output"]).resolve()
        == (root / args.native_dir).resolve()
    )
    chunks = read(root / args.native_dir / "chunks.json")
    assert Path(chunks["source_blend"]).resolve() == beauty_project
    assert Path(chunks["caption_cache"]).resolve() == Path(matte_provenance["source_beauty_cache"]).resolve()
    assert chunks["fps"] == 60 and chunks["width"] == 1920 and chunks["height"] == 1080
    cursor = 4140
    for chunk in chunks["chunks"]:
        assert chunk["reused"] is False and chunk["source_start"] == cursor
        cursor = chunk["source_end"] + 1
    assert cursor == 4440
    sample_report = read(root / args.native_dir / "sample-report.json")
    assert (
        sample_report["source_frames"] == [4140, 4439]
        and sample_report["frames"] == 300
    )
    assert Path(sample_report["project"]).resolve() == beauty_project
    cache_evidence = {}
    for layer in ("beauty", "actor"):
        files = sorted((args.cache / layer).glob("*.png"))
        assert {path.name for path in files} == {
            f"frame_{frame:04d}{layer}.png" for frame in range(4140, 4440)
        }
        cache_evidence[layer] = [
            {"file": path.name, "sha256": sha(path)} for path in files
        ]
    write(
        root / "final-cache-provenance.json",
        {
            "project_sha256": master_sha,
            "caption_cache": str(args.cache),
            "layers": cache_evidence,
            "beauty_reused_from_approved_v6": True,
            "rejected_v4_frames_reused": False,
            "scope": "Caption-only v7 delta independently preserves beauty DAG; byte-exact approved v6 beauty plus fresh corrected v7 actor cache, complete frame sets and hashes. Not an artistic/collision certificate.",
        },
    )
    manual = evidence["manual-review.json"]
    assert manual["project_sha256"] == master_sha
    assert manual["movie_sha256"] == sha(movie)
    assert manual["bare_sha256"] == sha(bare)
    assert (
        manual["user_art_approval"] is False and manual["full_song_complete"] is False
    )
    for key, actual_movie in (("video-qa", movie), ("bare-video-qa", bare)):
        video_report = evidence[f"{captions}/{key}/video-verification.json"]
        assert video_report["decoded_frames"] == 300
        assert Path(video_report["video"]).resolve() == actual_movie.resolve()
        assert video_report["sha256"] == sha(actual_movie)
    caption_audit = evidence[f"{captions}/caption-layer-audit.json"]
    assert Path(caption_audit["cache"]).resolve() == args.cache.resolve()
    assert caption_audit["frames"] == 300 and caption_audit["preview_only"] is False
    assert manual["final_beauty_sampled"] is True
    assert manual["caption_boundaries_sampled"] is True
    assert manual["repaired_wrist_windows_sampled"] is True
    assert len(manual["beauty_sampled_frames"]) >= 12
    assert len(manual["caption_boundary_frames"]) >= 32
    root.joinpath("review").mkdir(exist_ok=True)
    hero = cache_picture(args.cache, 4290, root / "review/native-4290.png")
    wide = cache_picture(args.cache, 4250, root / "review/native-4250.png")
    limits = [
        "仅原帧4140–4439的五秒横屏；全曲未交付，等待猪猪美术认可",
        "伊科尔新原生物理只验证4139–4441，不把完整body动作等同全曲衣发烘焙",
        "v4因袖壁穿手退回并停渲；新袖修复范围与连续几何/画面检查见sleeve-review，不复用旧v4帧",
        "缺失作者自改y1脸图，明确回退同包原FaceDiffuse；未取得验证过的FaceSDF",
        "灯／环任务部件在婚礼版隐藏并同步关闭轮廓；原PMX未覆盖",
        "Diffuse是综合受光近似；可见光束含美术体积Emission，不称完整Ray/Goo或观海子原始Shader",
        "阿克西妮娅鼻影、部分手掌肤色、强蓝边与辉光主次仍可精修；最终人工范围另记",
        "原初之人仅定位配布，未下载模型包或加入当前场景",
    ]
    recipe_path = f"presets/recipes/{IDENTITY}.json"
    recipe = {
        "id": IDENTITY,
        "status": "verified-five-second-review-art-pending",
        "project": str(project),
        "project_sha256": master_sha,
        "video": str(movie),
        "without_captions_video": str(bare),
        "performers": {"aksiniya": "Full HimeTanaka", "ikhor": "Full HinaSuzuki"},
        "source_frames": [4140, 4439],
        "resolution": [1920, 1080],
        "fps": 60,
        "seconds": 5,
        "audio_start_seconds": 4139 / 60,
        "audio_gain": 0.87,
        "physical_validation_frames": [4139, 4441],
        "character_profile": "presets/quality/ikhor-character-v1.json",
        "motion_profile": "presets/quality/ikhor-native-motion-v1.json",
        "sleeve_repair_profile": "presets/quality/ikhor-sleeve-repair-v1.json",
        "sleeve_integration": str(root / "production-v6/sleeve-integration.json"),
        "caption_target_repair": str(root / production / "caption-target-repair.json"),
        "sleeve_repair_evidence": "sleeve-review/visual-review.json",
        "stage_profile": "presets/stages/hesperides-bold-wedding-v1.json",
        "caption_profile": "presets/typography/duet-blue-gold-wedding-v1.json",
        "caption_cache": str(args.cache),
        "output_color_contract": CONTRACT,
        "full_song_complete": False,
        "user_art_approval": False,
        "limits": limits,
    }
    library = read(REPO / "catalog/library.json")
    state = read(REPO / "catalog/current_state.json")
    assert state["latest_review"]["entry_id"] == "duet-guanhai-transfer-v1"
    assert not any(e["id"] == IDENTITY for e in library["entries"])
    old_review = state["latest_review"]
    old_entry = next(e for e in library["entries"] if e["id"] == old_review["entry_id"])
    old_entry["art_review"] = {
        "status": old_review["art_status"],
        "as_of": args.date,
        "feedback": old_review["user_feedback"],
    }
    if state.get("previous_review"):
        state.setdefault("review_history", []).append(state["previous_review"])
    state["previous_review"] = old_review
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
        "user_feedback": "已按用户要求用伊科尔替换空并完成大胆蓝金婚礼五秒；待实际审看，美术边界见交付报告",
        "user_art_approval": False,
    }
    state["as_of"] = args.date
    state["current_task"] = (
        "已交付阿克西妮娅＋伊科尔大胆婚礼五秒，技术验收通过、美术待评价；原初之人仅定位配布供未来第二场景，不恢复全曲"
    )
    state["project_contract"]["replacement_status"] = (
        "Ikhor now occupies the Hina slot in the latest delivered project/video; Aether reviews retained as history"
    )
    state["active_iteration"] = {
        "id": IDENTITY,
        "status": "delivered-limited-scope",
        "user_authorized": True,
        "scope": "frames4140–4439,1080p60,5s",
        "full_song": False,
        "project": str(project),
        "project_sha256": master_sha,
        "delivery_report": str(root / "delivery.json"),
        "sleeve_repair_profile": recipe["sleeve_repair_profile"],
        "sleeve_visual_review": str(root / "sleeve-review/visual-review.json"),
        "geometry_collision_certified": False,
        "rejected_v4_frames_reused": False,
    }
    state["latest_supplemental_reading"] = {
        "date": args.date,
        "guide": "docs/LOCAL_CORRECTIVE_SHAPES.md",
        "ledger": "docs/research/SLEEVE_CORRECTIVE_EXTERNAL_2026_11_14.json",
        "scope": "Five official documentation bodies plus one5.2.2 source function; no video playback",
        "limits": "v6 one-shape LBS case tested separately; Corrective Smooth, Preserve Volume inverse and pose drivers not tested",
    }
    state["future_assets"]["primordial_human"].update(
        {
            "status": "exact-distribution-page-found; model-package-not-downloaded; not-in-current-scene",
            "url": "https://www.aplaybox.com/details/model/5eSouS8HksfA",
            "source_ledger": "docs/research/PRIMORDIAL_ONE_BACKGROUND_MODEL_2026_11_14.json",
        }
    )
    library["entries"].insert(
        0,
        {
            "id": IDENTITY,
            "title": "誓约之光 · 阿克西妮娅 × 伊科尔",
            "subtitle": "白衣与金饰分层，蓝金双弧、局部发光和仪式光束。",
            "collection": "CEREMONY / BLUE + GOLD",
            "category": "stage",
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
                GUIDE, CREDITS, "IKHOR_SLEEVE_REPAIR.md",
                "LOCAL_CORRECTIVE_SHAPES.md", "CHARACTER_NPR_PLAYBOOK.md",
            ],
            "configs": [
                recipe["character_profile"],
                recipe["motion_profile"],
                recipe["sleeve_repair_profile"],
                recipe["stage_profile"],
                recipe["caption_profile"],
                recipe_path,
            ],
            "look": [
                "人物／环境／舞台三层光",
                "材质局部HDR与窄边光",
                "双弧与柔化体积光束",
                "新角色衣发与袖部局部修复",
                "整组蓝金字幕",
            ],
            "compatibility": "Blender5.2.2 EEVEE；仅绑定已核对PMX、角色烘焙和指定婚礼基线。",
            "evidence": [
                "1049项基线核查与最终工程独立差量核查",
                "72基线帧转头／移灯／绕拍；最终袖部连续检查另记",
                "两版各300帧完整解码及音轨／色彩／接缝检查",
            ],
            "limits": limits,
            "command": "See docs/IKHOR_BOLD_WEDDING_PRODUCTION.md; fingerprint-bound inputs and fresh directories only.",
        },
    )
    library["updated"] = args.date
    for doc, group in [
        (GUIDE, next(g for g in library["knowledge_groups"] if g["id"] == "render")),
        (
            CREDITS,
            next(
                g
                for g in library["knowledge_groups"]
                if "CREDITS_FRANKEN_DUET.md" in g["docs"]
            ),
        ),
    ]:
        if doc not in group["docs"]:
            group["docs"].insert(0, doc)
    previous = Path("D:/codex/output/MMD-Guanhai-Transfer-v1/review")
    for suffix, title, before, after, subtitle in [
        (
            "overall",
            "新旧整体 / 换角与仪式光",
            previous / "native-4290.png",
            hero,
            "同4290帧与原相机，同时换角色和光效，不能当成单一Shader对照。",
        ),
        (
            "wide",
            "礼堂全貌 / 双弧与光束",
            previous / "native-4250.png",
            wide,
            "同4250帧与原相机；包含换角、局部Emission、舞台灯和美术体积光束等多项变化。",
        ),
        (
            "sleeve",
            "袖口动态 / 同帧修正",
            root / "production-v4/native-4290.png",
            hero,
            "同角色／身体动作／材质／灯／相机；前为退回的v4袖壁穿腕，后为局部袖动态与修形后的完整原生帧。",
        ),
    ]:
        library["comparisons"].insert(
            0,
            {
                "id": IDENTITY + "-" + suffix,
                "title": title,
                "subtitle": subtitle,
                "before_label": "前版",
                "after_label": "新版",
                "before": str(before),
                "after": str(after),
                "doc": GUIDE,
            },
        )
    profile = read(REPO / "presets/projects/franken-duet-full-v1.json")
    replaced = next((p for p in profile["performers"] if p["id"] == "aether"), None)
    if replaced:
        profile.setdefault("superseded_performers", []).append(replaced)
        updated = dict(replaced)
        updated.update(
            id="ikhor",
            display_name="伊科尔",
            model="D:/codex/output/MMD-Ikhor-Model-v1/source/Ikhor/Ikhor.pmx",
            model_source="https://www.aplaybox.com/details/model/L6PalbSZMmTW",
        )
        profile["performers"] = [
            updated if p["id"] == "aether" else p for p in profile["performers"]
        ]
    profile["latest_ikhor_wedding_project"] = str(project)
    profile["latest_ikhor_wedding_review"] = str(movie)
    profile["status"] = (
        "Aksiniya/Ikhor five-second review delivered; art pending; full song and full-song Ikhor physics not delivered"
    )
    profile["active_contract_state"] = "catalog/current_state.json"
    profile["historical_full_song_production"] = {
        key: profile.get(key)
        for key in ("production_scene", "integration_verification", "render_output")
    }
    profile["production_scene"] = str(project)
    profile["integration_verification"] = str(
        root / production / "master-verification.json"
    )
    profile["render_output"] = str(sample)
    profile["production_scene_scope"] = {
        "body_action": "full native Hime/Hina choreography retained",
        "physics_validated_frames": [4139, 4441],
        "delivered_frames": [4140, 4439],
        "full_song_physics_ready": False,
        "full_song_delivered": False,
    }
    profile["production_requirements"] = [
        requirement.replace("Map Aether materials", "Map Ikhor materials")
        for requirement in profile["production_requirements"]
    ]
    profile["stage"]["status"] = (
        "Selected Hesperides hall retained; latest five-second Ikhor bold-wedding review verified, art pending; full-song rendering stopped"
    )
    profile["current_iteration_scope"] = {
        "kind": "ikhor-replacement-bold-wedding-and-local-sleeve-repair",
        "requested_seconds": 5,
        "source_frames": [4140, 4439],
        "fps": 60,
        "resolution": [1920, 1080],
        "sample_output": str(sample),
        "sample_movie": str(movie),
        "status": "completed and technically verified; user art review pending",
        "full_movie": "not delivered or rendering",
    }
    old_sample = profile.get("sample_delivery")
    history = profile.setdefault("previous_sample_deliveries", [])
    if old_sample and not any(
        item.get("movie") == old_sample.get("movie") for item in history
    ):
        history.append(old_sample)
    profile["sample_delivery"] = {
        "movie": str(movie),
        "video_sha256": sha(movie),
        "project": str(project),
        "project_sha256": master_sha,
        "source_frames": [4140, 4439],
        "frames": 300,
        "seconds": 5,
        "camera_motion_changed": False,
        "physics_changed": True,
        "physics_change_scope": "Ikhor native local cloth bake plus8-sleeve local repair and one left corrective; not full-song physics",
        "verified": {"video": True, "audio": True, "seams": True},
        "delivery_report": str(root / "delivery.json"),
        "full_song_complete": False,
        "user_art_approval": False,
    }
    profile["character_style"]["adaptation"] = (
        "Retain Aksiniya's silver/navy palette; Ikhor's own blonde/white/cyan/gold materials mapped independently; preserve authored camera."
    )
    delivery = {
        "movie": str(movie),
        "movie_sha256": sha(movie),
        "without_captions_video": str(bare),
        "project": str(project),
        "project_sha256": master_sha,
        "source_frames": [4140, 4439],
        "frames": 300,
        "seconds": 5,
        "fps": 60,
        "resolution": [1920, 1080],
        "performers": ["aksiniya", "ikhor"],
        "reports": evidence_paths,
        "native_render_manifest": str(root / args.native_dir / "chunks.json"),
        "cache_provenance": str(root / "final-cache-provenance.json"),
        "sleeve_integration": recipe["sleeve_integration"],
        "manual_review": manual,
        "output_color_contract": CONTRACT,
        "physics_validated_frames": [4139, 4441],
        "full_song_complete": False,
        "user_art_approval": False,
        "primordial_human_in_scene": False,
        "limits": limits,
    }
    for doc in DOCS:
        copy_guide(REPO / "docs" / doc, root / doc)
    (root / "research").mkdir(exist_ok=True)
    for source in research_sources:
        shutil.copyfile(source, root / "research" / source.name)
    (root / "licenses").mkdir(exist_ok=True)
    shutil.copyfile(
        ikhor_terms,
        root / "licenses/Ikhor-RM.txt",
    )
    for old in other_licenses:
        shutil.copyfile(old, root / "licenses" / old.name)
    (root / "README.md").write_text(
        "# 誓约之光 · 阿克西妮娅 × 伊科尔\n\n"
        f"最终工程：`{production}/Franken_Aksiniya_Ikhor_Bold_Wedding.blend`。v4因袖壁穿手退回，前面版本为保留的过程／失败记录，未复用旧帧。\n\n"
        f"字幕原声版：`{captions}/Franken_Duet_5s_Ikhor_Wedding_REVIEW.mp4`；无字幕版：`{captions}/Franken_Duet_5s_Ikhor_NoCaptions.mp4`。\n\n"
        "1920×1080／60fps，原帧4140–4439，300原生帧、五秒；指定原声FLAC为输入，MP4音轨编码AAC。字幕在外部合成。\n\n"
        "伊科尔已替换空，独立重建材质与新衣发烘焙；新物理仅验证4139–4441，完整body动作保留不等于全曲物理或全曲成片。\n\n"
        "巨型原初之人仅找到配布页，未进场景。技术与人工抽样见delivery.json；美术仍待猪猪评价。来源与限制见CREDITS_AKSINIYA_IKHOR.md及licenses。\n\n"
        "本目录三份指南互链；其余知识内链明确指向本机仓库，不把此成片文件夹当独立源码包。完整离线知识浏览见MMD-Atlas-v1。\n",
        encoding="utf-8",
    )
    assert sha(project) == master_sha, "The master changed during packaging"
    # Copy/check every deliverable before advancing current registry; delivery is last.
    write(REPO / recipe_path, recipe)
    write(REPO / "catalog/library.json", library)
    write(REPO / "catalog/current_state.json", state)
    write(REPO / "presets/projects/franken-duet-full-v1.json", profile)
    write(root / "delivery.json", delivery)
    print("IKHOR_WEDDING_DELIVERED", movie, flush=True)


if __name__ == "__main__":
    main()
