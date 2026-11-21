"""Finalize the actual encoded rim/glow review sample without post-output video QA."""

import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Goo-Rim-Glow-v1")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    preparation = read(ROOT / "production-v1/preparation.json")
    delivery = read(ROOT / "quick-5s-v1/preview-info.json")
    assert delivery["project_sha256"] == preparation["project_sha256"]
    assert (
        delivery["output_frames"] == 150 and Path(delivery["video"]).stat().st_size > 0
    )
    delivery.update(
        status="encoded-review-sample",
        art_status="pending user review",
        post_output_qa="skipped per existing user preference",
        changes=preparation["changes"],
        preservation=preparation["preserved"],
    )
    write(ROOT / "delivery.json", delivery)
    shutil.copyfile(REPO / "docs/GOO_RIM_GLOW_REVISION.md", ROOT / "调整说明.md")
    shutil.copyfile(REPO / "scripts/goo_runtime.py", ROOT / "Goo_Startup.py")
    launcher = (
        "@echo off\n"
        'set "BLENDER_USER_CONFIG=D:/codex/workspace/goo-engine/5.2.1-community/portable/config"\n'
        'set "BLENDER_USER_SCRIPTS=D:/codex/workspace/goo-engine/5.2.1-community/portable/scripts"\n'
        'start "" "D:/codex/workspace/goo-engine/5.2.1-community/blender-5.2.1-git.0051aee0-windows64/blender.exe" '
        '--disable-autoexec --python "%~dp0Goo_Startup.py" "%~dp0production-v1\\Franken_Duet_Goo_Rim_Glow.blend"\n'
    )
    (ROOT / "Start_Goo_Project.cmd").write_text(launcher, encoding="utf-8")
    state_path = REPO / "catalog/current_state.json"
    state = read(state_path)
    previous = state["active_iteration"]
    state.setdefault("iteration_history", []).append(previous)
    state["active_iteration"] = {
        "id": "goo-rim-glow-v1",
        "status": "delivered-review-sample",
        "project": preparation["project"],
        "project_sha256": preparation["project_sha256"],
        "video": delivery["video"],
        "quick_preview": delivery["video"],
        "new_video_delivered": True,
        "user_art_approval": False,
        "scope": "150 frames at 1080p30, five seconds, one captioned original-vocal sample",
        "post_output_checks": "skipped per user preference",
        "next_action": "猪猪审看人物亮边、高光与场景泛光加强版。",
    }
    state["current_task"] = (
        "已完成Goo人物边缘光、高光和场景泛光加强版五秒样片；1080p30、单版字幕、指定原唱，按既定约定跳过输出后检查，待猪猪审看。"
    )
    state["latest_quick_preview"] = delivery
    state["latest_production_increment"] = {
        "entry_id": "goo-rim-glow-v1",
        "project": preparation["project"],
        "project_sha256": preparation["project_sha256"],
        "image": str(ROOT / "controls/after-4290.png"),
        "guide": "docs/GOO_RIM_GLOW_REVISION.md",
        "art_status": "pending user review",
        "new_video_delivered": True,
    }
    runtime_path = REPO / "presets/runtime/goo-v1.json"
    runtime = read(runtime_path)
    runtime.update(
        production_project=preparation["project"],
        preview_entry="scripts/run_goo_rim_glow_preview.py",
    )
    write(runtime_path, runtime)
    write(ROOT / "runtime.json", runtime)
    state["production_runtime"] = runtime
    write(state_path, state)
    spec_path = REPO / "presets/projects/franken-duet-full-v1.json"
    spec = read(spec_path)
    spec["production_scene"] = preparation["project"]
    spec["goo_rim_glow_v1"] = {
        "project_sha256": preparation["project_sha256"],
        "video": delivery["video"],
        "post_output_qa": "skipped per user preference",
    }
    write(spec_path, spec)
    preset = {
        "id": "goo-rim-glow-v1",
        "source": preparation["source"],
        "source_sha256": preparation["source_sha256"],
        "guide": "docs/GOO_RIM_GLOW_REVISION.md",
        "changes": preparation["changes"],
        "production_project": preparation["project"],
    }
    write(REPO / "presets/lighting/goo-rim-glow-v1.json", preset)
    write(ROOT / "lighting-settings.json", preset)
    print("GOO_RIM_GLOW_DELIVERED", delivery["video"], flush=True)


if __name__ == "__main__":
    main()
