# -*- coding: utf-8 -*-
# ruff: noqa: UP009
"""Record the second user-requested Ikhor brightness reduction, stills only."""

import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-MME-Reference-Light-v1")
OUT = ROOT / "production-v6"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


report = read(OUT / "preparation.json")
assert report["revision"] == 6 and report["independent_reopen_passed"]
assert not report["video_created"] and not report["aksiniya_materials_modified"]
assert (
    hashlib.sha256(Path(report["project"]).read_bytes()).hexdigest()
    == report["project_sha256"]
)
log = Path(
    "D:/codex/temp/citlali-fringe-study-2026-11-17/mme-balanced-ikhor-v6.log"
).read_text(encoding="utf-8", errors="replace")
assert "IKHOR_BALANCED_STILLS_COMPLETE" in log
assert not any(s in log.lower() for s in ("traceback", "shadow buffer full", "error:"))
for name in (
    "balanced-double-4290.jpg",
    "ikhor-balanced-hero-4290.jpg",
    "ikhor-v5-v6-comparison.png",
):
    assert (OUT / name).is_file()
report["art_status"] = "pending user review"
report["user_feedback_on_v5"] = "感觉伊科尔还是有点太亮了，请你再降一些"
report["manual_observation"] = (
    "Matching v5/v6 comparison viewed: darker broad hair/skin/white cloth surfaces with clearer sleeve and torso separation; bright silhouette retained. Static4290 only."
)
save(OUT / "preparation.json", report)
save(ROOT / "settings.json", report)
save(REPO / "presets/lighting/mme-reference-light-still-v3.json", report)
state = read(REPO / "catalog/current_state.json")
assert state["active_iteration"]["id"] == "mme-reference-light-balanced-still-v2"
state["previous_mme_light_iteration"] = dict(
    state["active_iteration"],
    art_status="revision_requested",
    user_feedback=report["user_feedback_on_v5"],
)
state["active_iteration"].update(
    id="mme-reference-light-balanced-still-v3",
    project=report["project"],
    project_sha256=report["project_sha256"],
    scope=report["scope"],
    art_status="pending user review",
)
state["current_task"] = (
    "猪猪反馈v5伊科尔仍太亮，已另存v6进一步降低脸／皮肤、头发与白衣大面积辐射，保留原轮廓／金青遮罩保护及眼睛高光。阿克西妮娅、灯光与后期不改；4290双人及半身静帧已实际渲染、独立重开姿态一致，待美术评价。"
)
state["latest_still"].update(
    project=report["project"],
    image=str(OUT / "ikhor-balanced-hero-4290.jpg"),
    baseline=str(ROOT / "production-v5/ikhor-balanced-hero-4290.jpg"),
    double=str(OUT / "balanced-double-4290.jpg"),
    art_status="pending user review",
)
state["production_runtime"]["static_candidate"] = report["project"]
state["latest_production_increment"].update(
    project=report["project"],
    status="v6 further Ikhor-only radiance reduction; static4290 only; art pending",
)
state["requested_visual_revision"].update(
    feedback=report["user_feedback_on_v5"],
    candidate_project=report["project"],
    status="v6 still correction; awaiting user review",
)
save(REPO / "catalog/current_state.json", state)
ledger_path = REPO / "docs/research/MME_REFERENCE_LIGHT_2026_11_17.json"
ledger = read(ledger_path)
ledger["followup_v6"] = report
save(ledger_path, ledger)
launcher_path = ROOT / "Start_Goo_Project.cmd"
launcher = launcher_path.read_text(encoding="utf-8-sig").replace(
    "production-v5\\Franken_MME_Balanced_Light_Still.blend",
    "production-v6\\Franken_MME_Balanced_Light_Still.blend",
)
assert "production-v6\\Franken_MME_Balanced_Light_Still.blend" in launcher
launcher_path.write_text(launcher, encoding="utf-8")
shutil.copy2(
    REPO / "docs/MME_REFERENCE_LIGHT_STILLS_2026_11_17.md", ROOT / "制作说明.md"
)
(ROOT / "README.md").write_text(
    "# 伊科尔亮度修订 · v6静帧\n\n"
    "按猪猪反馈，在v5基础上进一步降低伊科尔大面积亮区。\n\n"
    "- [最新双人画面](production-v6/balanced-double-4290.jpg)\n"
    "- [半身静帧](production-v6/ikhor-balanced-hero-4290.jpg)\n"
    "- [前后对照：左v5／右v6](production-v6/ikhor-v5-v6-comparison.png)\n"
    "- 工程入口：Start_Goo_Project.cmd\n\n"
    "仅4290静帧，未生成视频或新物理；待猪猪评价。\n",
    encoding="utf-8",
)
print("IKHOR_V6_STILLS_RECORDED")
