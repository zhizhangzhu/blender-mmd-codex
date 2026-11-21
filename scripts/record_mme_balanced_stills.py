# -*- coding: utf-8 -*-
# ruff: noqa: UP009
# The local Python 3.9 CLI required an explicit encoding for long CJK literals.
"""Record the observed overbright feedback and bounded still correction."""

import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-MME-Reference-Light-v1")
OUT = ROOT / "production-v5"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


report = read(OUT / "preparation.json")
assert (
    hashlib.sha256(Path(report["project"]).read_bytes()).hexdigest()
    == report["project_sha256"]
)
assert report["independent_reopen_passed"] and not report["video_created"]
log = Path(
    "D:/codex/temp/citlali-fringe-study-2026-11-17/mme-balanced-ikhor-v5.log"
).read_text(encoding="utf-8", errors="replace")
assert "IKHOR_BALANCED_STILLS_COMPLETE" in log
assert not any(s in log.lower() for s in ("traceback", "shadow buffer full", "error:"))
for name in (
    "balanced-double-4290.jpg",
    "ikhor-balanced-hero-4290.jpg",
    "aksiniya-before-v3-comparison.png",
    "ikhor-v3-v5-comparison.png",
):
    assert (OUT / name).is_file()
report["art_status"] = "pending user review"
report["manual_observation"] = (
    "Compared v3/v5 matching hero and double frames: reduced broad white sleeve and lower garment radiance, retained bright silhouette; face remains intentionally bright. Aksiniya before/v3 differences are visible but small; no strong improvement claimed."
)
report["discarded_iteration"] = (
    "v4 palette rollback alone changed too little; not main candidate"
)
save(OUT / "preparation.json", report)
save(ROOT / "settings.json", report)
save(REPO / "presets/lighting/mme-reference-light-still-v2.json", report)
state = read(REPO / "catalog/current_state.json")
state["previous_mme_light_iteration"] = state["active_iteration"]
state["previous_mme_light_iteration"]["art_status"] = "revision_requested"
state["previous_mme_light_iteration"]["user_feedback"] = (
    "伊科尔有点过曝光；阿克西妮娅有任何区别吗？"
)
state["active_iteration"] = {
    "id": "mme-reference-light-balanced-still-v2",
    "project": report["project"],
    "project_sha256": report["project_sha256"],
    "status": "still-candidate-complete",
    "scope": report["scope"],
    "new_video_delivered": False,
    "user_art_approval": False,
    "art_status": "pending user review",
    "eye_see_through": "deferred",
    "guide": "docs/MME_REFERENCE_LIGHT_STILLS_2026_11_17.md",
    "next_action": "按猪猪静帧反馈继续调整；不自动生成视频。",
}
state["current_task"] = (
    "猪猪反馈上一轮伊科尔过亮、阿克西妮娅变化不明显。已同机位核对并提供阿克西妮娅前后裁切；其色温／明暗变化较小，不称明显改善。v4回收色带变化不足，v5单独收敛伊科尔大面积材质辐射、保护已有轮廓与饰边；实际输出双人／半身静帧、独立重开姿态哈希相同，待美术评价。"
)
state["latest_still"] = {
    "project": report["project"],
    "image": str(OUT / "ikhor-balanced-hero-4290.jpg"),
    "baseline": str(ROOT / "production-v3/ikhor-clear-hero-4290.jpg"),
    "double": str(OUT / "balanced-double-4290.jpg"),
    "frame": 4290,
    "resolution": [1000, 1100],
    "art_status": "pending user review",
    "guide": "docs/MME_REFERENCE_LIGHT_STILLS_2026_11_17.md",
}
state["production_runtime"]["static_candidate"] = report["project"]
state["latest_production_increment"].update(
    project=report["project"],
    status="Ikhor broad radiance reduced; Aksiniya v3 retained; static4290 only; art pending",
)
state["requested_visual_revision"].update(
    feedback="伊科尔过亮；询问阿克西妮娅是否有区别。",
    candidate_project=report["project"],
    status="v5 still correction; awaiting user review",
)
save(REPO / "catalog/current_state.json", state)
ledger_path = REPO / "docs/research/MME_REFERENCE_LIGHT_2026_11_17.json"
ledger = read(ledger_path)
ledger["user_review_v3"] = "Ikhor overbright; Aksiniya change questioned"
ledger["followup"] = report
save(ledger_path, ledger)
launcher_path = ROOT / "Start_Goo_Project.cmd"
launcher = launcher_path.read_text(encoding="utf-8-sig").replace(
    "production-v3\\Franken_MME_Clear_Light_Still.blend",
    "production-v5\\Franken_MME_Balanced_Light_Still.blend",
)
assert "production-v5\\Franken_MME_Balanced_Light_Still.blend" in launcher
launcher_path.write_text(launcher, encoding="utf-8")
shutil.copy2(
    REPO / "docs/MME_REFERENCE_LIGHT_STILLS_2026_11_17.md", ROOT / "制作说明.md"
)
(ROOT / "README.md").write_text(
    "# 人物光影静帧修订\n\n"
    "上一轮伊科尔偏亮；v5只收敛伊科尔大面积受光材质，阿克西妮娅沿用v3。\n\n"
    "- [最新双人画面](production-v5/balanced-double-4290.jpg)\n"
    "- [伊科尔前后对照：左v3／右v5](production-v5/ikhor-v3-v5-comparison.png)\n"
    "- [阿克西妮娅前后对照：左研究前／右v3](production-v5/aksiniya-before-v3-comparison.png)\n"
    "- 工程入口：Start_Goo_Project.cmd\n\n"
    "仅4290静帧，未生成视频或新物理；脸部仍偏明亮，待猪猪评价。\n",
    encoding="utf-8",
)
print("BALANCED_STILLS_RECORDED")
