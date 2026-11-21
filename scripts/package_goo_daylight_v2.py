"""Package the v2 study and preservation evidence; finalize only after encoding."""

import argparse
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Goo-Wedding-v2")
TEMP = Path("D:/codex/temp/MME-Deep-Study-2026-11-16")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    prep = read(ROOT / "production-v2/preparation.json")
    state = read(REPO / "catalog/current_state.json")
    if args.finalize:
        delivery = read(ROOT / "quick-5s-v1/preview-info.json")
        shutil.copyfile(
            REPO / "docs/MME_TO_GOO_LIGHTING_STUDY.md",
            ROOT / "MME_Study_and_Goo_Changes.md",
        )
        delivery["window_pattern"] = prep["window_pattern"]
        delivery["status"] = "encoded-review-sample"
        delivery["production_status"] = (
            "encoded-review-sample; no post-output QA at user request"
        )
        delivery["user_art_approval"] = False
        write(ROOT / "delivery.json", delivery)
        state["active_iteration"].update(
            status="delivered-review-sample",
            new_video_delivered=True,
            project=prep["project"],
            project_sha256=prep["project_sha256"],
            video=delivery["video"],
            next_action="猪猪审看新窗光与卡渲样片；未进行输出后视频验收。",
        )
        state["current_task"] = (
            "已完成 MME 原包重点学习与 Goo 新版窗光/人物卡渲样片：1080p30、五秒、单版字幕指定原唱。按要求跳过输出后检查，美术待猪猪审看。"
        )
        state["latest_quick_preview"] = delivery
        runtime = read(REPO / "presets/runtime/goo-v1.json")
        runtime.update(
            production_project=prep["project"],
            preview_entry="scripts/run_goo_daylight_v2_preview.py",
        )
        write(REPO / "presets/runtime/goo-v1.json", runtime)
        write(ROOT / "runtime.json", runtime)
        shutil.copyfile(
            REPO / "presets/lighting/goo-daylight-v2.json",
            ROOT / "lighting-settings.json",
        )
        shutil.copyfile(
            REPO / "docs/research/MME_DEEP_STUDY_2026_11_16.json",
            ROOT / "research-sources.json",
        )
        state["production_runtime"] = runtime
        spec = read(REPO / "presets/projects/franken-duet-full-v1.json")
        spec["production_scene"] = prep["project"]
        spec["goo_daylight_v2"] = {
            "project_sha256": prep["project_sha256"],
            "video": delivery["video"],
            "fullbody_opening_seconds": 1.5,
            "post_output_qa": "skipped at user request",
        }
        write(REPO / "presets/projects/franken-duet-full-v1.json", spec)
        library = read(REPO / "catalog/library.json")
        library["entries"] = [
            e for e in library["entries"] if e["id"] != "goo-daylight-v2"
        ]
        library["entries"].insert(
            0,
            {
                "id": "goo-daylight-v2",
                "title": "蓝天婚礼 · 窗光与人物投影",
                "subtitle": "Goo 五秒快速审片：斜向窗格光带、真实落地影与受控人物亮边。",
                "collection": "GOO / DAYLIGHT WEDDING",
                "category": "stage",
                "family": "guanhaizi",
                "aspect": "landscape",
                "status": "motion",
                "image": str(ROOT / "production-v2/opening-4140.png"),
                "video": delivery["video"],
                "project": prep["project"],
                "report": str(ROOT / "delivery.json"),
                "docs": ["MME_TO_GOO_LIGHTING_STUDY.md", "GOO_ENGINE_MIGRATION.md"],
                "configs": [
                    "presets/lighting/goo-daylight-v2.json",
                    "presets/runtime/goo-v1.json",
                ],
                "scripts": [
                    "scripts/prepare_goo_daylight_v2.py",
                    "scripts/add_goo_window_gobo.py",
                    "scripts/run_goo_daylight_v2_preview.py",
                ],
                "look": [
                    "明亮蓝天礼堂",
                    "真实窗格遮光附件",
                    "双人落地投影",
                    "粉冷人物明暗与局部亮边",
                ],
                "compatibility": "Goo 5.2.1社区移植版0051aee03764；启动前注册便携MMD插件；不在普通Blender直接重渲。",
                "evidence": [
                    "9个MME原包重点说明/源码学习；不等于全部49位作者效果掌握",
                    "原Actions/网格/贴图及五时点姿态独立重开一致",
                    "150帧1080p30实际渲染与单版字幕原唱编码完成",
                ],
                "art_review": {
                    "status": "pending-user-review",
                    "as_of": "2026-11-16",
                    "feedback": "Awaiting user review",
                },
                "limits": [
                    "按用户要求跳过输出后的解码与审片；不是视频技术验收通过。",
                    "窗格光带由镜头外gobo模拟，并非原窗框逐格投影认证。",
                    "不是原版Ray/PowerShader执行或参考风格达标认证；没有新增物理或全曲。",
                ],
                "command": "Use Start_Goo_Project.cmd in the delivery; preview wrapper refuses to overwrite existing outputs.",
            },
        )
        library.update(updated="2026-11-16", featured="goo-daylight-v2")
        write(REPO / "catalog/library.json", library)
        write(REPO / "catalog/current_state.json", state)
        print("GOO_DAYLIGHT_V2_DELIVERED", delivery["video"])
        return

    before = read(Path("D:/codex/temp/goo-migration-v1/goo-master-reopen.json"))
    after = read(TEMP / "goo-v2-snapshot.json")
    checks = {
        "all_original_actions_identical": before["actions"] == after["actions"],
        "all_original_mesh_coordinates_identical": all(
            after["geometry"].get(k) == v for k, v in before["geometry"].items()
        ),
        "all_images_and_packing_identical": before["images"] == after["images"],
        "sampled_all_bones_identical": all(
            before["samples"][k]["bones"] == after["samples"][k]["bones"]
            for k in before["samples"]
        ),
        "sampled_all_shapes_identical": all(
            before["samples"][k]["shapes"] == after["samples"][k]["shapes"]
            for k in before["samples"]
        ),
        "original_portrait_camera_identical_after_opening": all(
            before["samples"][k]["camera"] == after["samples"][k]["camera"]
            and before["samples"][k]["lens"] == after["samples"][k]["lens"]
            for k in ("4290", "4370", "4438")
        ),
    }
    assert all(checks.values()), checks
    report = {
        "source": "D:/codex/output/MMD-Goo-Wedding-v1/production-v1/Franken_Duet_Goo_Wedding.blend",
        "immediate_source": prep["source"],
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
        "checks": checks,
        "sample_frames": [4140, 4218, 4290, 4370, 4438],
        "added_objects": sorted(set(after["objects"]) - set(before["objects"])),
        "removed_original_objects": sorted(
            set(before["objects"]) - set(after["objects"])
        ),
        "scope": "Independent reopen, source Actions/mesh coordinates and five evaluated poses; not final-video QA or full-song validation",
    }
    write(ROOT / "preservation.json", report)
    index = read(TEMP / "archive-index.json")
    urls = {
        "195743.zip": "https://bowlroll.net/file/195743",
        "188141.zip": "https://bowlroll.net/file/188141",
        "149977.zip": "https://bowlroll.net/file/149977",
        "104601.zip": "https://bowlroll.net/file/104601",
        "146255.zip": "https://bowlroll.net/file/146255",
        "HAToon2_r14.zip": "https://sorairo.pictures/3dcg/mme-effects/hatoon2/",
        "PostRimLighting_r4.zip": "https://sorairo.pictures/3dcg/mme-effects/postrimlighting/",
        "M4Layer_r12.zip": "https://sorairo.pictures/3dcg/mme-effects/m4layer/",
        "msToonCoordinator_v2.1.zip": "https://note.com/mashimashi_note/n/n2c2144638054",
    }
    ledger = {
        "date": "2026-11-16",
        "guide": "docs/MME_TO_GOO_LIGHTING_STUDY.md",
        "roundup": "https://www.bilibili.com/opus/844214760220131363",
        "roundup_authors_indexed": 49,
        "all_49_effect_families_deeply_read": False,
        "private_cache": str(TEMP),
        "archives": [
            {
                "archive": a["archive"],
                "sha256": a["sha256"],
                "source": urls[a["archive"]],
                "private_text_files": len(a["files"]),
                "all_code_fully_read": False,
            }
            for a in index
        ],
        "read_scope": "Original guide details exact primary readme/code sections; downloaded does not mean fully read or executed",
        "additional_primary_sources": [
            "https://github.com/ray-cast/ray-mmd",
            "https://github.com/ray-cast/ray-mmd/blob/master/ray.conf",
            "https://pip-mmd.hatenablog.com/entry/ar1026319",
            "https://github.com/MikuMikuShaders/LightBloom/blob/master/LightBloom.fxsub",
            "https://github.com/MikuMikuShaders/FXAA/blob/master/FXAA.fx",
            "https://pip-mmd.hatenablog.com/entry/ar1909483",
            "https://pip-mmd.hatenablog.com/entry/2024/02/24/230134",
            "https://pip-mmd.hatenablog.com/entry/ar945815",
        ],
        "additional_code_read_scope": {
            "LightBloom": "Threshold, blur/composition and input/output transforms, lines 145-482; not all 555 lines",
            "FXAA": "Quality preset and postprocess wrapper/parameters; not a derivation or port of the compressed NVIDIA core",
        },
        "actually_executed": "Goo native node/material adaptation only; no MME .fx or package executables",
        "video_downloaded": False,
        "third_party_sources_redistributed": False,
        "preproduction_renders_viewed": [
            "production-v1/portrait-4290.png",
            "production-v1/opening-4140.png",
            "production-v1/fullbody-light-study-4290.png",
            "production-v1/external-sun-visibility-study.png",
            "production-v2/opening-4140.png",
        ],
        "known_limits": [
            "External Sun current direction blocked; actual off-camera gobo simulates window pattern",
            "No original PowerShader/Ray execution in Goo",
            "Not all 49 author effects mastered",
            "Goo Curvature rim unresolved and unused",
            "No new physics simulation",
            "No user art approval",
        ],
    }
    write(REPO / "docs/research/MME_DEEP_STUDY_2026_11_16.json", ledger)
    write(
        REPO / "presets/lighting/goo-daylight-v2.json",
        {
            "id": "goo-daylight-v2",
            "source": prep["source"],
            "source_sha256": prep["source_sha256"],
            "production": prep["project"],
            "project_sha256": prep["project_sha256"],
            "runtime": "presets/runtime/goo-v1.json",
            "native_floor_cast_range": [0.48, 1],
            "native_gobo_cast_range": [0.72, 1.09],
            "portal_energy_w": 650,
            "portal_size_m": 0.22,
            "window_pattern": prep["window_pattern"],
            "rim_side_relative_gain": [0.95, 0.34],
            "rim_shadow_permission": [0.32, 1],
            "stage_bounded_response": {"input": [0.05, 0.65], "output": [0.62, 1.24]},
            "camera": {
                "fullbody_opening_source_frames": [4140, 4228],
                "original_from_frame": 4230,
            },
            "preview": {
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "frames": 150,
                "seconds": 5,
                "post_output_checks": False,
            },
            "guide": "docs/MME_TO_GOO_LIGHTING_STUDY.md",
        },
    )
    shutil.copyfile(REPO / "scripts/goo_runtime.py", ROOT / "Goo_Startup.py")
    shutil.copyfile(
        REPO / "docs/GOO_ENGINE_MIGRATION.md", ROOT / "GOO_ENGINE_MIGRATION.md"
    )
    shutil.copyfile(
        REPO / "docs/MME_TO_GOO_LIGHTING_STUDY.md",
        ROOT / "MME_Study_and_Goo_Changes.md",
    )
    shutil.copyfile(
        REPO / "docs/CREDITS_AKSINIYA_IKHOR.md",
        ROOT / "Original_Character_Stage_Credits.md",
    )
    runtime = read(REPO / "presets/runtime/goo-v1.json")
    lines = [
        "@echo off",
        f'set "BLENDER_USER_CONFIG={runtime["user_config"]}"',
        f'set "BLENDER_USER_SCRIPTS={runtime["user_scripts"]}"',
        f'start "" "{runtime["executable"]}" --disable-autoexec --python "%~dp0Goo_Startup.py" "%~dp0production-v2\\Franken_Duet_Goo_Daylight.blend"',
        "",
    ]
    with (ROOT / "Start_Goo_Project.cmd").open("w", encoding="ascii", newline="") as stream:
        stream.write("\r\n".join(lines))
    (ROOT / "README.txt").write_text(
        "猪猪，这一版采用 Goo 5.2.1 社区移植版。\n"
        "双击 Start_Goo_Project.cmd 打开新工程，避免 Windows 用原 Blender 打开。\n"
        "production-v2 是最终样片输入；production-v1 是前一步制作诊断。\n"
        "窗格斜光由镜头外真实遮光片模拟，原建筑保留，人物有真实地面投影。\n"
        "前1.5秒为新增全身开场，之后回到原MMD相机；人物动作和网格未改。\n"
        "样片：quick-5s-v1/Franken_Duet_5s_GooDaylightV2_SUB_1080P.mp4。\n"
        "完成状态以 delivery.json 为准。按要求没有输出后解码、审片。\n"
        "MME 原包学习与尚未验证的范围见 MME_Study_and_Goo_Changes.md。\n",
        encoding="utf-8",
    )
    if state.get("active_iteration", {}).get("id") != "goo-daylight-v2":
        state.setdefault("iteration_history", []).append(
            state.get("active_iteration", {})
        )
    state["active_iteration"] = {
        "id": "goo-daylight-v2",
        "status": "rendering-review-sample",
        "user_authorized": True,
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
        "new_video_delivered": False,
        "guide": "docs/MME_TO_GOO_LIGHTING_STUDY.md",
        "scope": "1080p30, five seconds, one subtitled original-vocal sample; new 1.5-second fullbody opening",
        "post_output_checks": "skipped at user request",
        "art_status": "pending-user-review",
    }
    state["current_task"] = (
        "已读 PowerShader 等 9 个原包的重点说明/源码并完成 Goo v2 制作图与独立姿态保护核对，正在实际渲染新五秒字幕原唱样片。"
    )
    state["preset_reuse_policy"].update(
        powershader_package_read=True,
        tn_postpointlight_package_read=True,
        deep_study_guide="docs/MME_TO_GOO_LIGHTING_STUDY.md",
        deep_study_ledger="docs/research/MME_DEEP_STUDY_2026_11_16.json",
    )
    state["latest_still"] = {
        "entry_id": "goo-daylight-v2",
        "project": prep["project"],
        "project_sha256": prep["project_sha256"],
        "image": str(ROOT / "production-v2/opening-4140.png"),
        "frame": 4140,
        "technical_status": "actual preproduction render viewed; independent source preservation passed",
        "art_status": "pending-user-review",
        "user_art_approval": False,
    }
    write(REPO / "catalog/current_state.json", state)
    write(
        ROOT / "delivery.json",
        {
            "status": "rendering",
            "project": prep["project"],
            "post_output_checks": "skipped at user request",
        },
    )
    print("GOO_DAYLIGHT_V2_PACKAGE_READY")


if __name__ == "__main__":
    main()
