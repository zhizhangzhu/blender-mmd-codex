"""Register the finished actual encoded sample; never decode or watch output media."""

import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Goo-Tyndall-Rim-v1")
GUIDE = "GOO_TYNDALL_RIM_PRODUCTION.md"
ID = "goo-tyndall-rim-v1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    prep = read(ROOT / "production-v7/preparation.json")
    delivery = read(ROOT / "quick-5s-v1/preview-info.json")
    preservation = read(ROOT / "master-preservation-v2.json")
    assert preservation["passed"]
    assert delivery["project_sha256"] == prep["project_sha256"]
    assert (
        delivery["output_frames"] == 150 and Path(delivery["video"]).stat().st_size > 0
    )
    base = read(
        Path("D:/codex/output/MMD-Goo-Rim-Glow-v1/production-v1/preparation.json")
    )
    settings = {
        "id": ID,
        "base_rim_highlight_glow": base["changes"],
        "white_blue_rims": prep["changes"]["rims"],
        "final_glows": prep["changes"]["glows"],
        "volume_density": prep["volume_density_control"],
        "volume_bounds": prep["final_volume_bounds"],
        "window_shafts": prep["final_window_shafts"],
        "color_management": prep["color_management"],
        "guide": "docs/" + GUIDE,
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
    }
    delivery.update(
        status="encoded-review-sample",
        art_status="pending user review",
        user_art_approval=False,
        post_output_checks="skipped per existing user request",
        master_preservation=preservation,
        settings=str(ROOT / "lighting-settings.json"),
        limitations=[
            "Window-oriented interior lamps and slat accessories; not original exterior architectural transmission certification",
            "Shaft visibility remains composition-dependent and weaker than the reference",
            "No post-output video decode, audio recheck or visual review; not technical video QA passed",
            "No new physics, no full-song delivery, no literal MME execution or full reference shader match",
        ],
    )
    write(ROOT / "delivery.json", delivery)
    write(ROOT / "lighting-settings.json", settings)
    write(REPO / "presets/lighting/goo-tyndall-rim-v1.json", settings)
    shutil.copyfile(REPO / "docs" / GUIDE, ROOT / "调整说明.md")
    shutil.copyfile(REPO / "scripts/goo_runtime.py", ROOT / "Goo_Startup.py")
    launcher = '@echo off\nset "BLENDER_USER_CONFIG=D:/codex/workspace/goo-engine/5.2.1-community/portable/config"\nset "BLENDER_USER_SCRIPTS=D:/codex/workspace/goo-engine/5.2.1-community/portable/scripts"\nstart "" "D:/codex/workspace/goo-engine/5.2.1-community/blender-5.2.1-git.0051aee0-windows64/blender.exe" --disable-autoexec --python "%~dp0Goo_Startup.py" "%~dp0production-v7\\Franken_Duet_Goo_Tyndall_Rim.blend"\n'
    (ROOT / "Start_Goo_Project.cmd").write_text(launcher, encoding="utf-8")
    (ROOT / "README.md").write_text(
        "# 白蓝轮廓 · 窗光柔辉\n\n[五秒带字幕原唱样片](quick-5s-v1/Franken_Duet_5s_GooTyndallRim_SUB_1080P.mp4) · [近景图](production-v7/portrait-4290.png) · [全身图](production-v7/opening-4140.png)\n\n[打开Goo工程](Start_Goo_Project.cmd) · [调整说明](调整说明.md) · [参数](lighting-settings.json) · [交付记录](delivery.json)\n\n最终工程在production-v7，早期版本是试图。输出后的解码／审片按此前约定跳过，美术待猪猪评价。\n",
        encoding="utf-8",
    )
    state_path = REPO / "catalog/current_state.json"
    state = read(state_path)
    history = state.setdefault("iteration_history", [])
    previous = dict(state["active_iteration"])
    if previous.get("id") == "goo-daylight-v2":
        old_delivery = read(Path("D:/codex/output/MMD-Goo-Wedding-v2/delivery.json"))
        previous.update(
            project=old_delivery["project"],
            video=old_delivery["video"],
            quick_preview=old_delivery["video"],
            project_sha256=old_delivery["project_sha256"],
        )
    if not any(item.get("id") == previous.get("id") for item in history):
        history.append(previous)
    history.append(
        {
            "id": "goo-rim-glow-intermediate",
            "status": "stopped-after-reference-clarification",
            "rendered_frames": 35,
            "total_frames": 150,
            "video_delivered": False,
            "output": "D:/codex/output/MMD-Goo-Rim-Glow-v1",
        }
    )
    state["active_iteration"] = {
        "id": ID,
        "status": "delivered-review-sample",
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
        "video": delivery["video"],
        "quick_preview": delivery["video"],
        "new_video_delivered": True,
        "scope": "150 frames at native1080p30, five seconds, one locked-caption original-vocal sample",
        "post_output_checks": "skipped per user request",
        "art_status": "pending user review",
        "next_action": "猪猪审看白蓝亮边、高光泛光和窗向体积样片；参考差距仍保留。",
    }
    state["current_task"] = (
        "已完成白蓝人物亮边、高光泛光、固定Reinhard高光肩部及窗向体积光新版五秒样片；原生1080p30，字幕和指定原唱，按约定跳过输出后检查。"
    )
    state["latest_quick_preview"] = delivery
    state["latest_production_increment"] = {
        "entry_id": ID,
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
        "image": str(ROOT / "production-v7/portrait-4290.png"),
        "guide": "docs/" + GUIDE,
        "new_video_delivered": True,
        "art_status": "pending user review",
    }
    state["latest_still"] = {
        "entry_id": ID,
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
        "image": str(ROOT / "production-v7/portrait-4290.png"),
        "scope": "1280x720 production control still, 24 samples; 4140 and 4290 manually observed",
        "art_status": "pending user review",
    }
    state["latest_user_visual_request"] = {
        "date": "2026-11-16",
        "features": [
            "clear window-oriented volumetric shafts with edge falloff",
            "high-luminance bloom and gentle highlight compression",
            "strong upper-rear white-blue character rim",
            "soft colored face shadows and fine hair highlight",
            "cool-white dreamy atmosphere with retained details",
        ],
        "guide": "docs/" + GUIDE,
    }
    runtime_path = REPO / "presets/runtime/goo-v1.json"
    runtime = read(runtime_path)
    runtime.update(
        production_project=prep["project"],
        preview_entry="scripts/run_goo_tyndall_rim_preview.py",
    )
    write(runtime_path, runtime)
    write(ROOT / "runtime.json", runtime)
    state["production_runtime"] = runtime
    write(state_path, state)
    spec_path = REPO / "presets/projects/franken-duet-full-v1.json"
    spec = read(spec_path)
    spec["production_scene"] = prep["project"]
    spec["goo_tyndall_rim_v1"] = {
        "project_sha256": prep["project_sha256"],
        "video": delivery["video"],
        "post_output_qa": "skipped per user request",
    }
    write(spec_path, spec)
    library_path = REPO / "catalog/library.json"
    library = read(library_path)
    group = next(
        item for item in library["knowledge_groups"] if item["id"] == "lighting"
    )
    if GUIDE not in group["docs"]:
        group["docs"].insert(0, GUIDE)
    entry = {
        "id": ID,
        "title": "白蓝轮廓 · 窗光柔辉",
        "subtitle": "加强人物亮边／高光、窗向散射与高亮泛光；五秒快速审片。",
        "collection": "GOO / TYNDALL RIM",
        "category": "stage",
        "family": "guanhaizi",
        "aspect": "landscape",
        "status": "motion",
        "image": str(ROOT / "production-v7/portrait-4290.png"),
        "video": delivery["video"],
        "project": prep["project"],
        "report": str(ROOT / "delivery.json"),
        "docs": [GUIDE, "GOO_RIM_GLOW_REVISION.md"],
        "configs": [
            "presets/lighting/goo-tyndall-rim-v1.json",
            "presets/runtime/goo-v1.json",
        ],
        "scripts": [
            "scripts/run_goo_tyndall_rim_preview.py",
            "scripts/verify_goo_tyndall_master.py",
        ],
        "look": [
            "后上方白蓝亮边",
            "发带与金属高光",
            "窗向局部散射",
            "固定高光压缩与分区泛光",
        ],
        "compatibility": "Goo5.2.1社区版0051aee03764；先注册便携MMD插件，不用普通Blender直接重渲。",
        "evidence": [
            "最终工程独立重开与原Actions、网格、五时点姿态相机对照",
            "两张最终制作图实际查看",
            "150帧原生1080p30与指定原唱字幕实际编码完成",
        ],
        "art_review": {
            "status": "pending-user-review",
            "as_of": "2026-11-16",
            "feedback": "Awaiting user review",
        },
        "limits": delivery["limitations"],
        "command": "Use Start_Goo_Project.cmd; existing outputs are preserved.",
    }
    library["entries"] = [entry] + [
        item for item in library["entries"] if item["id"] != ID
    ]
    library.update(updated="2026-11-16", featured=ID)
    write(library_path, library)
    print("GOO_TYNDALL_RIM_DELIVERED", delivery["video"], flush=True)


if __name__ == "__main__":
    main()
