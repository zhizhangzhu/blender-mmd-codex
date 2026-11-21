"""Publish only completed stills; retain the old video as rejected hair alignment history."""

import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Ikhor-Hair-Alignment-v1")
production = ROOT / "production-v1"
report = json.loads((production / "repair.json").read_text(encoding="utf-8"))
assert (
    report["reopened_bind_alignment_passed"] and report["non_hair_channels_preserved"]
)
for name in ("scene-4290.jpg", "hair-front-4290.jpg", "hair-three-quarter-4290.jpg"):
    assert (production / name).is_file(), name
shutil.copy2(
    "D:/codex/output/MMD-Jelly-Eyes-v1/Goo_Startup.py", ROOT / "Goo_Startup.py"
)
launcher = Path("D:/codex/output/MMD-Jelly-Eyes-v1/Start_Goo_Project.cmd").read_text(
    encoding="utf-8-sig"
)
launcher = launcher.replace(
    "production-v16\\Franken_Duet_Goo_Eye_Hair_Stage.blend",
    "production-v1\\Ikhor_Hair_Aligned_Still.blend",
)
(ROOT / "Start_Goo_Project.cmd").write_text(launcher, encoding="utf-8")
shutil.copy2(REPO / "docs/IKHOR_HAIR_ALIGNMENT_STILL_REPAIR.md", ROOT / "修复说明.md")
path = REPO / "catalog/current_state.json"
state = json.loads(path.read_text(encoding="utf-8"))
state["current_task"] = (
    "猪猪指出伊科尔头发持续错位；已隔离错误头发烘焙、恢复原始发型并重算4290刘海投影，独立重开后完成原镜头与两张头部静帧。仅静帧验证，未重做头发物理、未制作新视频；待猪猪评价。"
)
state["previous_hair_still_iteration"] = state["active_iteration"]
state["active_iteration"] = {
    "id": "ikhor-hair-alignment-still-v1",
    "project": report["project"],
    "project_sha256": report["project_sha256"],
    "status": "still-repair-candidate",
    "scope": "Static4290; original hair bind restored; no new physical hair motion or video",
    "new_video_delivered": False,
    "art_status": "pending user review",
    "user_art_approval": False,
    "guide": "docs/IKHOR_HAIR_ALIGNMENT_STILL_REPAIR.md",
    "next_action": "猪猪审看静帧；若后续制作视频，另修头发物理并重算动态发影。",
}
state["latest_still"] = {
    "project": report["project"],
    "image": str(production / "hair-front-4290.jpg"),
    "frame": 4290,
    "resolution": [1000, 1000],
    "art_status": "pending user review",
    "guide": "docs/IKHOR_HAIR_ALIGNMENT_STILL_REPAIR.md",
}
state["latest_quick_preview"].update(
    art_status="revision_requested",
    user_art_approval=False,
    user_feedback="伊科尔头发一直错位，包括刘海和左侧分叉；用户要求只修静帧，不生产新样片。",
)
state["production_runtime"]["static_candidate"] = report["project"]
state["requested_visual_revision"] = {
    "date": "2026-11-17",
    "feedback": "伊科尔刘海及侧发持续错位，按用户正确发型参考恢复。只看静帧，不生产新样片。",
    "candidate_project": report["project"],
    "guide": "docs/IKHOR_HAIR_ALIGNMENT_STILL_REPAIR.md",
    "status": "still candidate; awaiting user review",
}
path.write_text(
    json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
(ROOT / "README.md").write_text(
    "# 伊科尔头发归位 · 静帧候选\n\n- [正面](production-v1/hair-front-4290.jpg)\n- [四分之三侧面](production-v1/hair-three-quarter-4290.jpg)\n- [原镜头](production-v1/scene-4290.jpg)\n- 工程：Start_Goo_Project.cmd\n\n恢复原模型头发绑定姿态，隔离错误头发物理烘焙，重算当前帧刘海投影。未新烘焙头发物理，未输出新视频；不是动态修复认证。\n",
    encoding="utf-8",
)
print("IKHOR_HAIR_STILLS_RECORDED")
