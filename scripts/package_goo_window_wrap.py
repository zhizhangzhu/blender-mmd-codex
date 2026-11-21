"""Record the user's revision request, or finalize the actual encoded window-wrap sample."""

import argparse
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Goo-Window-Wrap-v1")
ID = "goo-window-wrap-v1"
GUIDE = "GOO_BROAD_WINDOW_AND_STRONG_RIM.md"
FEEDBACK = "背后两束窄光柱不自然；大窗应产生大片入光；衣发需要更强的轮廓辉光和更明显的芙宁娜式发带高光。"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-revision", action="store_true")
    args = parser.parse_args()
    prep = read(ROOT / "production-v3/preparation.json")
    state_path = REPO / "catalog/current_state.json"
    library_path = REPO / "catalog/library.json"
    state, library = read(state_path), read(library_path)
    if args.record_revision:
        state["active_iteration"].update(
            art_status="revision_requested",
            user_feedback=FEEDBACK,
            user_art_approval=False,
        )
        state["latest_quick_preview"]["art_status"] = "revision_requested"
        state["latest_still"]["art_status"] = "revision_requested"
        state["current_task"] = (
            "正在按用户反馈重做大窗宽幅日照、强衣发轮廓辉光及明显发带高光，新工程已保存并渲染两张制作图，五秒视频输出中。"
        )
        state["requested_visual_revision"] = {
            "date": "2026-11-16",
            "feedback": FEEDBACK,
            "source_iteration": "goo-tyndall-rim-v1",
            "candidate_project": prep["project"],
            "guide": "docs/" + GUIDE,
        }
        for item in library["entries"]:
            if item["id"] == "goo-tyndall-rim-v1":
                item["art_review"] = {
                    "status": "revision_requested",
                    "as_of": "2026-11-16",
                    "feedback": FEEDBACK,
                }
        write(state_path, state)
        write(library_path, library)
        print("WINDOW_WRAP_REVISION_RECORDED", flush=True)
        return
    delivery = read(ROOT / "quick-5s-v3/preview-info.json")
    verification = read(ROOT / "master-verification-v3.json")
    assert (
        verification["passed"] and delivery["project_sha256"] == prep["project_sha256"]
    )
    assert (
        delivery["output_frames"] == 150 and Path(delivery["video"]).stat().st_size > 0
    )
    render_log = Path(
        "D:/codex/temp/MMD-Goo-Window-Wrap-v1/quick-5s-v3/render.log"
    ).read_text(encoding="utf-8", errors="replace")
    shadow_errors = render_log.count("Shadow buffer full")
    assert shadow_errors == 0, "The corrected render still exceeded the shadow pool"
    log_check = {
        "shadow_buffer_full_messages": shadow_errors,
        "scope": "Full render runtime log; no video decoding or playback",
        "abandoned_first_attempt_frames": 67,
        "final_shadow_pool": prep["shadow_pool"],
    }
    write(ROOT / "render-log-check.json", log_check)
    settings = {
        "id": ID,
        "source": prep["source"],
        "source_sha256": prep["source_sha256"],
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
        "changes": prep["changes"],
        "window_basis": prep["window_basis"],
        "volume_bounds": prep["volume_bounds"],
        "volume_density": prep["volume_density"],
        "guide": "docs/" + GUIDE,
        "shadow_pool": prep["shadow_pool"],
    }
    delivery.update(
        status="encoded-review-sample",
        art_status="pending user review",
        user_art_approval=False,
        master_verification=verification,
        render_log_check=log_check,
        post_output_checks="skipped per existing user request",
        settings=str(ROOT / "lighting-settings.json"),
        limitations=[
            "Window-sized fill lights and estimated sun direction, not exact author window/solar reconstruction",
            "Directional NPR rim is an art-controlled surface signal; glow AOV is not a physical light pass",
            "Only 4140/4290 production stills manually observed; no post-output video QA",
            "No new physics or full-song delivery",
        ],
    )
    write(ROOT / "delivery.json", delivery)
    write(ROOT / "lighting-settings.json", settings)
    write(REPO / "presets/lighting/goo-window-wrap-v1.json", settings)
    shutil.copyfile(REPO / "docs" / GUIDE, ROOT / "调整说明.md")
    shutil.copyfile(REPO / "scripts/goo_runtime.py", ROOT / "Goo_Startup.py")
    (ROOT / "Start_Goo_Project.cmd").write_text(
        '@echo off\nset "BLENDER_USER_CONFIG=D:/codex/workspace/goo-engine/5.2.1-community/portable/config"\nset "BLENDER_USER_SCRIPTS=D:/codex/workspace/goo-engine/5.2.1-community/portable/scripts"\nstart "" "D:/codex/workspace/goo-engine/5.2.1-community/blender-5.2.1-git.0051aee0-windows64/blender.exe" --disable-autoexec --python "%~dp0Goo_Startup.py" "%~dp0production-v3\\Franken_Duet_Goo_Window_Wrap.blend"\n',
        encoding="utf-8",
    )
    (ROOT / "README.md").write_text(
        "# 大窗柔光 · 强衣发轮廓\n\n[五秒字幕原唱样片](quick-5s-v3/Franken_Duet_5s_GooWindowWrap_SUB_1080P.mp4) · [近景](production-v3/portrait-4290.png) · [全身](production-v3/opening-4140.png)\n\n[Goo工程入口](Start_Goo_Project.cmd) · [调整说明](调整说明.md) · [参数](lighting-settings.json)\n\n旧两束细锥已隐藏，按大窗尺寸改为宽幅日光；增强衣发轮廓及独立边缘辉光。按既定约定未做输出后视频检查，美术待猪猪评价。\n",
        encoding="utf-8",
    )
    previous = dict(state["active_iteration"])
    old = read(Path("D:/codex/output/MMD-Goo-Tyndall-Rim-v1/delivery.json"))
    if previous.get("id") == "goo-tyndall-rim-v1":
        previous.update(
            project=old["project"],
            project_sha256=old["project_sha256"],
            video=old["video"],
            quick_preview=old["video"],
            art_status="revision_requested",
            user_feedback=FEEDBACK,
            user_art_approval=False,
        )
    history = state.setdefault("iteration_history", [])
    history[:] = [entry for entry in history if entry.get("id") != previous.get("id")]
    history.append(previous)
    state["active_iteration"] = {
        "id": ID,
        "status": "delivered-review-sample",
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
        "video": delivery["video"],
        "quick_preview": delivery["video"],
        "new_video_delivered": True,
        "scope": "150 native1080p30 frames, five seconds, one captioned original-vocal sample",
        "art_status": "pending user review",
        "user_art_approval": False,
        "post_output_checks": "skipped per user request",
        "next_action": "猪猪审看大窗宽幅光、强衣发轮廓辉光与发带高光新版。",
    }
    state["current_task"] = (
        "已完成大窗宽幅日光、强衣发轮廓辉光和明显发带高光的五秒字幕原唱样片；旧两束窄光隐藏，原生1080p30，按约定跳过输出后检查。"
    )
    state["latest_quick_preview"] = delivery
    state["latest_still"] = {
        "entry_id": ID,
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
        "image": str(ROOT / "production-v3/portrait-4290.png"),
        "scope": "1920x1080 native production controls,24 samples;4140/4290 manually observed",
        "art_status": "pending user review",
    }
    state["latest_production_increment"] = {
        **state["latest_still"],
        "guide": "docs/" + GUIDE,
        "new_video_delivered": True,
    }
    state["requested_visual_revision"]["status"] = (
        "new sample delivered; awaiting user review"
    )
    runtime_path = REPO / "presets/runtime/goo-v1.json"
    runtime = read(runtime_path)
    runtime.update(
        production_project=prep["project"],
        preview_entry="scripts/run_goo_window_wrap_preview.py",
    )
    write(runtime_path, runtime)
    write(ROOT / "runtime.json", runtime)
    state["production_runtime"] = runtime
    write(state_path, state)
    project_path = REPO / "presets/projects/franken-duet-full-v1.json"
    project = read(project_path)
    project["production_scene"] = prep["project"]
    project["goo_window_wrap_v1"] = {
        "project_sha256": prep["project_sha256"],
        "video": delivery["video"],
        "post_output_qa": "skipped per user request",
    }
    write(project_path, project)
    group = next(
        item for item in library["knowledge_groups"] if item["id"] == "lighting"
    )
    if GUIDE not in group["docs"]:
        group["docs"].insert(0, GUIDE)
    entry = {
        "id": ID,
        "title": "大窗柔光 · 强衣发轮廓",
        "subtitle": "窗面尺度的宽幅日照、强白蓝衣缘、明显发带高光与专用边缘辉光。",
        "collection": "GOO / WINDOW WRAP",
        "category": "stage",
        "family": "guanhaizi",
        "aspect": "landscape",
        "status": "motion",
        "image": str(ROOT / "production-v3/portrait-4290.png"),
        "video": delivery["video"],
        "project": prep["project"],
        "report": str(ROOT / "delivery.json"),
        "docs": [GUIDE],
        "configs": [
            "presets/lighting/goo-window-wrap-v1.json",
            "presets/runtime/goo-v1.json",
        ],
        "scripts": [
            "scripts/prepare_goo_window_wrap.py",
            "scripts/run_goo_window_wrap_preview.py",
            "scripts/verify_goo_window_wrap.py",
        ],
        "look": [
            "大窗宽幅入光",
            "更宽强白蓝轮廓",
            "明确天使环高光",
            "人物真实rim信号的专用辉光",
        ],
        "compatibility": "Goo5.2.1社区版0051aee03764，先注册便携MMD插件；保留原生动作与贴图。",
        "evidence": [
            "实际测量窗面世界坐标",
            "两张制作图实际查看",
            "独立重开结构与五时点姿态相机检查",
            "150帧原生1080p30新渲染与字幕原唱编码完成",
        ],
        "art_review": {
            "status": "pending-user-review",
            "as_of": "2026-11-16",
            "feedback": "Awaiting user review",
        },
        "limits": delivery["limitations"],
        "command": "Use Start_Goo_Project.cmd. Existing outputs are preserved.",
    }
    library["entries"] = [entry] + [
        item for item in library["entries"] if item["id"] != ID
    ]
    library.update(updated="2026-11-16", featured=ID)
    write(library_path, library)
    print("GOO_WINDOW_WRAP_DELIVERED", delivery["video"], flush=True)


if __name__ == "__main__":
    main()
