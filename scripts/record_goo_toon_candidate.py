"""Record the verified opaque-toon candidate without claiming a new video exists."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Jelly-Eyes-v1")
production = ROOT / "production-v16"
prep = json.loads((production / "preparation.json").read_text(encoding="utf-8"))
verification = json.loads(
    (production / "master-verification.json").read_text(encoding="utf-8")
)
assert verification["passed"]
path = REPO / "catalog/current_state.json"
state = json.loads(path.read_text(encoding="utf-8"))
state.update(
    as_of="2026-11-17",
    current_task="眼透已搁置。已恢复不透明刘海，新增分层发影、暖鼻影、受控亮肤与双人300帧几何刘海投影；production-v16独立重开及实际渲染AOV核查中，接着输出同段五秒黑边字幕原唱样片。尚未产生本版新视频。",
)
state["active_iteration"] = {
    "id": "goo-eye-hair-stage-v1",
    "status": "native-master-verified-render-in-progress",
    "project": prep["project"],
    "project_sha256": prep["project_sha256"],
    "new_video_delivered": False,
    "eye_see_through": "deferred by user; extra transparency disabled",
    "art_status": "pending user review",
    "user_art_approval": False,
    "guide": "docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md",
    "scope": "Opaque toon hair, warm geometric face-shadow sequence4140-4439, luminous skin; original5s1080p30 sample; no full song",
    "next_action": "等待独立验证与本版实际渲染／编码；不复用旧v4的beauty缓存。",
}
state["pending_eye_hair_stage_render"] = {
    "status": "rendering",
    "project": prep["project"],
    "project_sha256": prep["project_sha256"],
    "iteration": "quick-5s-v16",
    "new_video_completed": False,
    "output_frames": 150,
    "source_frames": [4140, 4438],
    "post_output_video_qa": "skipped at user request",
    "eye_see_through": "deferred",
}
state["latest_still"] = {
    "project": prep["project"],
    "image": str(production / "portrait-4290.jpg"),
    "frame": 4290,
    "resolution": [1280, 720],
    "art_status": "pending user review",
    "guide": "docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md",
}
if "latest_quick_preview" in state:
    state["latest_quick_preview"].update(
        art_status="revision_requested",
        user_art_approval=False,
        user_feedback="猪猪指出眼透无效、变黑或透明过于刻意，现已搁置眼透，优先补足发影与亮肤。",
    )
path.write_text(
    json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("OPAQUE_TOON_CANDIDATE_RECORDED")
