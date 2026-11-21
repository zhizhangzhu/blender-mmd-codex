"""Finalize only an actually encoded eye/hair/stage sample; no MP4 decoding."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Jelly-Eyes-v1")
TEMP = Path("D:/codex/temp/MMD-Jelly-Eyes-v1/quick-5s-v16")
ID = "goo-eye-hair-stage-v1"
GUIDE = "JELLY_EYE_HAIR_STAGE_IMPLEMENTATION.md"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    prep = read(ROOT / "production-v16/preparation.json")
    verified = read(ROOT / "production-v16/master-verification.json")
    info = read(ROOT / "quick-5s-v16/preview-info.json")
    native = read(TEMP / "render-complete.json")
    assert verified["passed"]
    shadow_probe = read(ROOT / "production-v16/rendered-shadow-sequence-check.json")
    assert len({row["frame"] for row in shadow_probe}) >= 2
    assert all(row["mean_abs_error"] < 0.009 for row in shadow_probe)
    assert info["project_sha256"] == native["project_sha256"] == prep["project_sha256"]
    assert (
        hashlib.sha256(Path(prep["project"]).read_bytes()).hexdigest()
        == prep["project_sha256"]
    )
    assert native["output_frames"] == 150 and native["resolution"] == [1920, 1080]
    assert (
        info["caption_stroke_pixels_at_1080"] == 3
        and info["caption_shadow_opacity"] == 0.45
    )
    movie = Path(info["video"])
    assert movie.is_file() and movie.stat().st_size > 0
    log = (TEMP / "render.log").read_text(encoding="utf-8", errors="replace")
    render_log = {
        "shadow_buffer_full_messages": log.lower().count("shadow buffer full"),
        "completed_frame_log_entries": log.count("QUICK_PREVIEW_RENDER "),
        "scope": "Renderer log only; MP4 decode/playback skipped at user request",
    }
    assert render_log["shadow_buffer_full_messages"] == 0, render_log
    assert render_log["completed_frame_log_entries"] == 150, render_log
    delivery = dict(
        info,
        status="delivered-review-sample",
        user_art_approval=False,
        art_status="pending user review",
        master_verification=verified,
        rendered_shadow_aov_verification=shadow_probe,
        render_log_check=render_log,
        post_output_checks="Skipped at user request; no MP4 decoding or playback",
        settings=str(ROOT / "effect-settings.json"),
        limitations=[
            "Jelly baked only4080-4441; no full-song validation or clothing resimulation",
            "Ikhor has no source blink in this five-second interval; setup present but no new blink authored",
            "Eye see-through deferred by user; additional hair transparency disabled",
            "Face bang shadow baked4140-4439 from actual hair geometry with artistic local distance/height permissions; nose mask is authored",
            "Stage hybrid PBR and emission controls reuse original architectural probes; no new GI bake",
            "Native global shadow resolution scale0.75 to fit the build maximum2048MB pool; independent512x512 face-shadow sequence unchanged",
        ],
    )
    save(ROOT / "delivery.json", delivery)
    save(ROOT / "render-log-check.json", render_log)
    save(
        ROOT / "quick-5s-v13/not-for-delivery.json",
        {
            "status": "discarded",
            "reason": "421 shadow buffer full messages in full render log; missing shadows possible",
            "replaced_by": str(movie),
            "post_output_mp4_decoded": False,
        },
    )
    save(ROOT / "master-verification.json", verified)
    state = read(REPO / "catalog/current_state.json")
    state["as_of"] = "2026-11-17"
    state["current_task"] = (
        "已完成不透明刘海、分层冷暖发影、300帧逐帧几何刘海投影、暖鼻影和受控亮肤；保留果冻眼、眼部高光、强轮廓泛光及舞台材质。150帧1080p30五秒原唱黑边字幕样片已编码；眼透按猪猪要求搁置，未做视频输出后解码／播放检查。"
    )
    state["active_iteration"] = {
        "id": ID,
        "status": "delivered-review-sample",
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
        "video": str(movie),
        "quick_preview": str(movie),
        "new_video_delivered": True,
        "caption_profile": "presets/typography/duet-blue-gold-wedding-v1.json",
        "scope": "150 native1080p30 frames, five seconds, original-vocal FLAC and locked whole-group captions",
        "art_status": "pending user review",
        "user_art_approval": False,
        "master_verification": verified,
        "render_log_check": render_log,
        "guide": "docs/" + GUIDE,
        "next_action": "由猪猪审看本轮样片；未恢复全曲。",
    }
    state["latest_quick_preview"] = delivery
    state["production_runtime"].update(
        production_project=prep["project"],
        preview_entry="scripts/run_goo_eye_hair_stage_preview.py",
    )
    state["previous_requested_visual_revision"] = state.get("requested_visual_revision")
    state["requested_visual_revision"] = {
        "date": "2026-11-17",
        "feedback": "增加面部与头发阴影，保持明亮通透肤色；参考崩铁人物的分层卡渲。眼透明确搁置。",
        "candidate_project": prep["project"],
        "guide": "docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md",
        "eye_see_through": "deferred",
        "status": "new sample encoded; awaiting user review",
    }
    state["latest_user_visual_request"] = {
        "date": "2026-11-17",
        "reference": "User HSR/Pela face image",
        "requirements": [
            "clearer face/hair shadows",
            "luminous skin while retaining shadow shapes",
            "strong rim bloom and bright eye highlights",
        ],
        "eye_see_through": "deferred by user",
    }
    state["latest_production_increment"] = {
        "date": "2026-11-17",
        "project": prep["project"],
        "guide": "docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md",
        "status": "five-second sample encoded; art awaiting user review",
        "eye_see_through": "disabled/deferred",
        "animated_face_shadow_files": 600,
    }
    state["latest_learning"] = {
        "date": "2026-11-17",
        "guide": "docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md",
        "ledger": "docs/research/STAR_RAIL_FACE_HAIR_2026_11_17.json",
        "scope": "Actual author-source reading: StarRailNPRShader face/hair/shared lighting/depth helpers and docs, plus Nilo public lighting example; local geometric approximation implemented",
        "official_game_shader_obtained": False,
    }
    state["latest_still"] = {
        "project": prep["project"],
        "image": str(ROOT / "production-v16/portrait-4290.jpg"),
        "frame": 4290,
        "resolution": [1280, 720],
        "art_status": "pending user review",
        "guide": "docs/" + GUIDE,
    }
    state["pending_eye_hair_stage_render"].update(
        status="complete",
        new_video_completed=True,
        beauty_files=150,
        actor_files=150,
        resume_requires_user_instruction=False,
        video=str(movie),
    )
    save(REPO / "catalog/current_state.json", state)
    runtime = read(REPO / "presets/runtime/goo-v1.json")
    runtime.update(
        production_project=prep["project"],
        preview_entry="scripts/run_goo_eye_hair_stage_preview.py",
    )
    save(REPO / "presets/runtime/goo-v1.json", runtime)
    project = read(REPO / "presets/projects/franken-duet-full-v1.json")
    project.update(
        production_scene=prep["project"],
        current_goo_working_scene=prep["project"],
        render_output=str(movie.parent),
        latest_captioned_review=str(movie),
        status="Eye jelly, bright highlights, opaque hair toon ramps, animated geometric face hair-shadows, luminous skin and stage surfaces integrated; eye see-through deferred; captioned five-second sample encoded; post-output QA skipped; full song not delivered",
    )
    save(REPO / "presets/projects/franken-duet-full-v1.json", project)
    library = read(REPO / "catalog/library.json")
    if any(x["id"] == ID for x in library["entries"]):
        raise RuntimeError("Already packaged; inspect existing state before repeating")
    entry = copy.deepcopy(
        next(x for x in library["entries"] if x["id"] == "goo-window-wrap-v1")
    )
    entry.update(
        id=ID,
        title="果冻眼 · 明亮肤色与分层发影",
        subtitle="原生果冻眼、眼睛高光、不透明刘海、逐帧几何发影、暖鼻影、强轮廓泛光与舞台材质；眼透搁置。",
        collection="GOO / EYES & HAIR",
        category="character",
        image=str(ROOT / "production-v16/portrait-4290.jpg"),
        video=str(movie),
        project=prep["project"],
        report=str(ROOT / "delivery.json"),
        docs=[GUIDE, "STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md"],
        configs=[
            "presets/lighting/goo-eye-hair-stage-v1.json",
            "presets/runtime/goo-v1.json",
            "presets/typography/duet-blue-gold-wedding-v1.json",
        ],
        scripts=[
            "scripts/prepare_goo_eye_hair_stage.py",
            "scripts/prepare_goo_opaque_toon_v11.py",
            "scripts/bake_goo_face_hair_shadows.py",
            "scripts/finalize_goo_toon_shadow_master.py",
            "scripts/check_goo_rendered_shadow_aovs.py",
            "scripts/verify_goo_eye_hair_stage.py",
            "scripts/run_goo_eye_hair_stage_preview.py",
        ],
        look=[
            "随眨眼的果冻弹动",
            "高光与虹膜颜色分离",
            "刘海保持原有不透明度",
            "冷暖发束色带与逐帧几何刘海投影",
            "受控亮肤与独立暖鼻影",
            "纯轮廓泛光",
            "石材／金属／烛光分区",
        ],
        evidence=[
            "插件普通与Goo5.2临时注册／烘焙／独立重开",
            "原动作与十时点眼外顶点保持",
            "独立重开600张阴影文件与实际渲染帧号核查；两人有效脸部近景已观察",
            "150帧实际新渲染与字幕原唱编码完成",
        ],
        limits=delivery["limitations"]
        + ["No post-output MP4 QA; art awaiting user review"],
    )
    library["entries"].insert(0, entry)
    library["featured"] = ID
    save(REPO / "catalog/library.json", library)
    ledger = read(REPO / "docs/research/JELLY_EYE_2026_11_16.json")
    ledger.update(
        video_completed=True,
        video=str(movie),
        post_output_video_qa=False,
        production_project=prep["project"],
        production_project_sha256=prep["project_sha256"],
        verification=str(ROOT / "production-v16/master-verification.json"),
        eye_see_through="deferred by user",
    )
    save(REPO / "docs/research/JELLY_EYE_2026_11_16.json", ledger)
    settings = read(REPO / "presets/lighting/goo-eye-hair-stage-v1.json")
    settings.update(
        project=prep["project"],
        project_sha256=prep["project_sha256"],
        eye_peek={
            "status": "deferred by user",
            "additional_transparency": 0,
            "original_pmx_alpha_preserved": True,
        },
        face_skin_gain=1.16,
        face_nose_form={
            "kind": "model-local UV authored mask",
            "warm_multiplier": [1, 0.74, 0.60],
            "amount": 0.60,
        },
        hair_value_ramps={
            "interval": [0.32, 0.72],
            "silver_dark_multiplier": [0.62, 0.68, 0.85],
            "gold_dark_multiplier": [0.72, 0.58, 0.43],
        },
        animated_face_hair_shadows=prep["animated_hair_shadows"],
        study="docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md",
        validation_scope="Saved project independent reopen; native600 shadow files; actual rendered UV/visibility AOV comparison; original actions/cameras and eye-only GN preserved; final MP4 QA skipped by user",
    )
    settings["hair"] = [
        {
            "material": row["material"],
            "native_form_weight": row["native_form_weight"],
            "native_visibility_mapping_min": row["shadow_min"],
            "additional_eye_transparency": 0,
        }
        for row in prep["revision"]["hair"]
    ]
    settings["face_shadows"] = [
        {
            "material": row["material"],
            "skin_gain": row["skin_gain"],
            "native_visibility_mapping_min": row["shadow_min"],
            "original_face_form_retained": True,
            "verified_model_face_sdf": (row["material"] == "颜"),
        }
        for row in prep["revision"]["faces"]
    ]
    settings["head_key_lights"] = prep["revision"]["lights"]
    settings["shadow_budget"] = prep["shadow_memory_revision"]
    study_ledger = read(REPO / "docs/research/STAR_RAIL_FACE_HAIR_2026_11_17.json")
    study_ledger["local_transfer"].update(
        project=prep["project"],
        project_sha256=prep["project_sha256"],
        saved_master_report=str(ROOT / "production-v16/master-verification.json"),
        actual_rendered_shadow_sampling_report=str(
            ROOT / "production-v16/rendered-shadow-sequence-check.json"
        ),
    )
    study_ledger["shadow_budget_revision"] = prep["shadow_memory_revision"]
    save(REPO / "docs/research/STAR_RAIL_FACE_HAIR_2026_11_17.json", study_ledger)
    save(REPO / "presets/lighting/goo-eye-hair-stage-v1.json", settings)
    save(ROOT / "effect-settings.json", settings)
    launcher = ROOT / "Start_Goo_Project.cmd"
    launcher.write_text(
        launcher.read_text(encoding="utf-8-sig").replace(
            "production-v4", "production-v16"
        ),
        encoding="utf-8",
    )
    shutil.copy2(REPO / "docs" / GUIDE, ROOT / "制作说明.md")
    shutil.copy2(
        REPO / "docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md", ROOT / "卡渲学习记录.md"
    )
    shutil.copy2(
        REPO / "docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md",
        ROOT / "STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md",
    )
    delivery_guide = ROOT / "制作说明.md"
    delivery_guide.write_text(
        delivery_guide.read_text(encoding="utf-8").replace(
            "(GOO_FEATURES_AND_MME_MECHANISMS.md)",
            "(D:/codex/workspace/blender-mmd-codex/docs/GOO_FEATURES_AND_MME_MECHANISMS.md)",
        ),
        encoding="utf-8",
    )
    (ROOT / "README.md").write_text(
        "# 果冻眼、亮肤与发影整合样片\n\n"
        "猪猪，本轮五秒样片已实际完成。\n\n"
        "- 视频：[五秒字幕原唱](quick-5s-v16/" + movie.name + ")\n"
        "- 工程入口：双击 `Start_Goo_Project.cmd`，先注册便携MMD插件再打开production-v16。\n"
        "- 对照：[双人近景](production-v16/portrait-4290.jpg)、[银发近景](production-v16/eye-controls-v3/aksiniya-4290-effects-on.jpg)、[金发近景](production-v16/eye-controls-v3/ikhor-4290-effects-on.jpg)。\n"
        "- 参数：effect-settings.json；独立重开：master-verification.json；制作范围：制作说明.md。\n\n"
        "字幕保留黑边框和投影，使用指定FLAC原唱。果冻眼原插件无需另装，工程内存原生GN与烘焙曲线。眼透已搁置，刘海保持不透明；hair-shadows是此工程必需的相对路径动态阴影序列，请与blend一起保留。\n\n"
        "仅验证本片段。伊科尔原五秒没有眨眼触发，未擅自添加；未恢复全曲。按约定跳过输出后视频解码／播放审片，美术待猪猪评价。\n",
        encoding="utf-8",
    )
    print("EYE_HAIR_STAGE_DELIVERED", movie, flush=True)


if __name__ == "__main__":
    main()
