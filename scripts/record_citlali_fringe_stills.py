"""Record completed warm-fringe stills and the user's standing still-only policy."""

import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Citlali-Fringe-Shadow-v1")
OUT = ROOT / "production-v3"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


report = read(OUT / "study.json")
assert report["independent_reopen_passed"] and report["poses_preserved"]
assert (
    hashlib.sha256(Path(report["project"]).read_bytes()).hexdigest()
    == report["project_sha256"]
)
for name in (
    "ikhor-warm-contact-4290.jpg",
    "aksiniya-warm-contact-4290.jpg",
    "ikhor-before-4290.jpg",
):
    assert (OUT / name).is_file()
# Normalize metadata for the observed mixed-parameter final master, without altering its saved contents.
report["source_sha256"] = hashlib.sha256(
    Path(report["source"]).read_bytes()
).hexdigest()
report["actors"] = [
    next(
        r
        for r in read(ROOT / "production-v1/study.json")["actors"]
        if r["actor"] == "aksiniya"
    ),
    next(r for r in report["actors"] if r["actor"] == "ikhor"),
]
save(OUT / "study.json", report)
save(REPO / "presets/lighting/citlali-fringe-contact-still-v1.json", report)
save(ROOT / "settings.json", report)
shutil.copy2(
    "D:/codex/output/MMD-Ikhor-Hair-Alignment-v1/Goo_Startup.py",
    ROOT / "Goo_Startup.py",
)
launcher = Path(
    "D:/codex/output/MMD-Ikhor-Hair-Alignment-v1/Start_Goo_Project.cmd"
).read_text(encoding="utf-8-sig")
launcher = launcher.replace(
    "production-v1\\Ikhor_Hair_Aligned_Still.blend",
    "production-v3\\Franken_Citlali_Fringe_Shadow_Still.blend",
)
(ROOT / "Start_Goo_Project.cmd").write_text(launcher, encoding="utf-8")
guide = "CITLALI_WARM_FRINGE_SHADOW_STUDY.md"
shutil.copy2(REPO / "docs" / guide, ROOT / "制作说明.md")
state = read(REPO / "catalog/current_state.json")
state["previous_fringe_still_iteration"] = state["active_iteration"]
state["current_task"] = (
    "已按猪猪的观海子茜特拉莉参考试做暖橙、贴近刘海的窄投影；两人分别标定影宽与颜色，保留修正后的伊科尔发型。已独立重开并输出4290近景与同条件基线，未生成视频，美术待猪猪评价。后续默认只看静帧。"
)
state["active_iteration"] = {
    "id": "citlali-warm-fringe-still-v1",
    "project": report["project"],
    "project_sha256": report["project_sha256"],
    "status": "still-study-complete",
    "scope": "Static4290; per-actor warm narrow contact shadow; no new physics or video",
    "new_video_delivered": False,
    "art_status": "pending user review",
    "user_art_approval": False,
    "eye_see_through": "deferred",
    "guide": "docs/" + guide,
    "next_action": "按猪猪静帧反馈继续迭代；仅明确要求时生成视频。",
}
state["latest_still"] = {
    "project": report["project"],
    "image": str(OUT / "ikhor-warm-contact-4290.jpg"),
    "baseline": str(OUT / "ikhor-before-4290.jpg"),
    "second_actor": str(OUT / "aksiniya-warm-contact-4290.jpg"),
    "frame": 4290,
    "resolution": [900, 900],
    "art_status": "pending user review",
    "guide": "docs/" + guide,
}
state["production_runtime"]["static_candidate"] = report["project"]
state["requested_visual_revision"] = {
    "date": "2026-11-17",
    "feedback": "面部刘海投影参考观海子茜特拉莉视频；后续只看静帧，不生成样片。",
    "candidate_project": report["project"],
    "guide": "docs/" + guide,
    "status": "still candidate; awaiting user review",
}
save(REPO / "catalog/current_state.json", state)
save(
    REPO / "docs/research/CITLALI_FRINGE_2026_11_17.json",
    {
        "date": "2026-11-17",
        "guide": "docs/" + guide,
        "source_video_url": "https://www.bilibili.com/video/BV1xCTe64EEu/",
        "local_frame_read_seconds": 8,
        "frame_resolution": [720, 1280],
        "private_frame": "D:/codex/temp/citlali-fringe-study-2026-11-17/reference-8s.jpg",
        "reading_scope": "One locally extracted frame and user screenshot; no original author shader or whole-video analysis",
        "implementation": report["scope"],
        "project": report["project"],
        "project_sha256": report["project_sha256"],
        "output_policy": "stills only; video requires explicit new request",
    },
)
workflow = REPO / "docs/PRODUCTION_WORKFLOW.md"
content = workflow.read_text(encoding="utf-8-sig")
if "后续输出约定：只看静帧" not in content:
    content = content.replace(
        "\n\n",
        "\n\n2026-11-17后续输出约定：只看静帧／对照图，不默认生成五秒样片或全曲；只有猪猪后来明确要求视频时才进入成片流程。旧输出约定按历史日期理解。\n\n",
        1,
    )
    workflow.write_text(content, encoding="utf-8")
(ROOT / "README.md").write_text(
    "# 暖色刘海投影 · 静帧候选\n\n- [伊科尔修改后](production-v3/ikhor-warm-contact-4290.jpg)\n- [伊科尔修改前](production-v3/ikhor-before-4290.jpg)\n- [阿克西妮娅](production-v3/aksiniya-warm-contact-4290.jpg)\n- 工程入口：Start_Goo_Project.cmd\n\n参考观海子茜特拉莉附图及本地8秒静帧，独立试做暖橙窄影；非作者原Shader。保留已修复发型，仅验证4290静帧，未新做物理或视频。\n",
    encoding="utf-8",
)
print("CITLALI_FRINGE_STILLS_RECORDED")
