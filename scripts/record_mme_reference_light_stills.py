# -*- coding: utf-8 -*-
"""Publish the observed native-Goo MME-inspired still candidate; never encode video."""

import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-MME-Reference-Light-v1")
OUT = ROOT / "production-v3"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


report = read(OUT / "preparation.json")
assert report["independent_reopen_passed"] and not report["video_created"]
assert (
    hashlib.sha256(Path(report["project"]).read_bytes()).hexdigest()
    == report["project_sha256"]
)
for f in (
    "clear-double-4290.jpg",
    "before-double-4290.jpg",
    "ikhor-clear-hero-4290.jpg",
    "ikhor-soft-hero-4290.jpg",
    "ikhor-before-hero-4290.jpg",
):
    assert (OUT / f).is_file()
log = Path(
    "D:/codex/temp/citlali-fringe-study-2026-11-17/mme-hero-final.log"
).read_text(encoding="utf-8", errors="replace")
assert "shadow buffer full" not in log.lower() and "MME_HERO_STILLS_COMPLETE" in log
report["render_log_shadow_overflow_messages"] = 0
report["art_status"] = "pending user review"
report["soft_variant_visual_note"] = (
    "Small visible difference in this bright scene; clear version selected as main candidate"
)
save(OUT / "preparation.json", report)
save(ROOT / "settings.json", report)
save(REPO / "presets/lighting/mme-reference-light-still-v1.json", report)
guide = "MME_REFERENCE_LIGHT_STILLS_2026_11_17.md"
shutil.copy2(REPO / "docs" / guide, ROOT / "制作说明.md")
shutil.copy2(
    "D:/codex/output/MMD-Citlali-Fringe-Shadow-v1/Goo_Startup.py",
    ROOT / "Goo_Startup.py",
)
launcher = Path(
    "D:/codex/output/MMD-Citlali-Fringe-Shadow-v1/Start_Goo_Project.cmd"
).read_text(encoding="utf-8-sig")
launcher = launcher.replace(
    "production-v3\\Franken_Citlali_Fringe_Shadow_Still.blend",
    "production-v3\\Franken_MME_Clear_Light_Still.blend",
)
(ROOT / "Start_Goo_Project.cmd").write_text(launcher, encoding="utf-8")
state = read(REPO / "catalog/current_state.json")
state["previous_mme_light_iteration"] = state["active_iteration"]
state["current_task"] = (
    "已按新MME借物表及蓝白人物参考试做静帧：调整侧上人物主光、暖肤冷衣影、白衣亮部、金青饰边保护和高亮扩散；v1色阶异常判废，v3为清透主候选。已实际渲染同机位半身／双人前后对照，姿态重开哈希一致；仅4290静帧，无新视频或物理。待猪猪审看。"
)
state["active_iteration"] = {
    "id": "mme-reference-light-still-v1",
    "project": report["project"],
    "project_sha256": report["project_sha256"],
    "status": "still-candidate-complete",
    "scope": "Static4290; native Goo lighting/material adaptation of MME principles; no original.fx execution",
    "new_video_delivered": False,
    "user_art_approval": False,
    "art_status": "pending user review",
    "eye_see_through": "deferred",
    "guide": "docs/" + guide,
    "next_action": "按猪猪静帧反馈继续调整；不自动生成视频。",
}
state["latest_still"] = {
    "project": report["project"],
    "image": str(OUT / "ikhor-clear-hero-4290.jpg"),
    "baseline": str(OUT / "ikhor-before-hero-4290.jpg"),
    "double": str(OUT / "clear-double-4290.jpg"),
    "frame": 4290,
    "resolution": [1000, 1100],
    "guide": "docs/" + guide,
    "art_status": "pending user review",
}
state["production_runtime"]["static_candidate"] = report["project"]
state["latest_production_increment"] = {
    "date": "2026-11-17",
    "project": report["project"],
    "scope": "stills only",
    "guide": "docs/" + guide,
    "status": "native saved/reopened/rendered; art pending",
}
state["requested_visual_revision"] = {
    "date": "2026-11-17",
    "feedback": "参考myhlz水印蓝白人物截图与借物表，综合MME技巧改善光影，允许调整光源；只看静帧。",
    "candidate_project": report["project"],
    "guide": "docs/" + guide,
    "status": "still candidate; awaiting user review",
}
save(REPO / "catalog/current_state.json", state)
save(
    REPO / "docs/research/MME_REFERENCE_LIGHT_2026_11_17.json",
    {
        "date": "2026-11-17",
        "guide": "docs/" + guide,
        "reference_inputs": [
            "codex-clipboard-c5dffe61-e144-4f50-a89e-82c3b1c68aa3.png",
            "codex-clipboard-42c7c4f4-ea79-402b-aec2-6a549d967576.png",
            "codex-clipboard-91262f94-e0df-424d-8d6d-58295cbfd83c.png",
            "codex-clipboard-24852f11-d044-47fe-a9a0-8ef7b8c8598e.jpg",
            "Screenshot_2026-11-17-11-31-27-00_149003a2d400f6.jpg",
        ],
        "credit_limit": "Author list, not exact effect/preset proof. Rui is credited under particles; do not infer the primary Ray shader.",
        "private_cache": "D:/codex/temp/MME-Deep-Study-2026-11-16/text",
        "actual_rereading": [
            "PowerShader preset explanations; selected Common_Shader shadow/specular/texture passages",
            "Diffusion full readme and Gaussian/screen/strength composition section",
            "msToonCoordinator material permissions, shadow RT/pseudo SSS descriptions and Shade code excerpts",
        ],
        "original_fx_executed": False,
        "third_party_complete_source_redistributed": False,
        "local_implementation": report["scope"],
        "project": report["project"],
        "project_sha256": report["project_sha256"],
        "video_created": False,
        "failures": [
            "v1 stage RGB curve created posterization and white cloth reconstruction lost detail; rejected",
            "Strong soft variant had little perceptual benefit in this scene; clear candidate selected",
        ],
    },
)
(ROOT / "README.md").write_text(
    "# MME式蓝白人物光影 · 静帧候选\n\n- [清透半身](production-v3/ikhor-clear-hero-4290.jpg)\n- [同机位修改前](production-v3/ikhor-before-hero-4290.jpg)\n- [双人画面](production-v3/clear-double-4290.jpg)\n- [柔光对照](production-v3/ikhor-soft-hero-4290.jpg)\n- 工程入口：Start_Goo_Project.cmd\n\n保存原生Goo灯光／材质适配，没有运行原生MME.fx。保留修正发型、动作和窄刘海投影。只验证4290静帧，没有新视频或物理；与参考仍有差距，待猪猪评价。\n",
    encoding="utf-8",
)
print("MME_REFERENCE_LIGHT_STILLS_RECORDED")
