"""Register the completed portrait still, never replacing the latest video."""

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
OUT = Path("D:/codex/output/MMD-Portrait-Relight-v1")
PRODUCTION = OUT / "production-v1"
IDENTITY = "portrait-relight-v1"
GUIDE = "PORTRAIT_RELIGHT_IMPLEMENTATION.md"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256") if hasattr(hashlib, "file_digest") else None
        if digest is None:
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1048576), b""):
                digest.update(block)
        return digest.hexdigest()


def main():
    preparation = read(PRODUCTION / "preparation.json")
    audit = read(PRODUCTION / "master-verification.json")
    assert audit["passed"] and preparation["source_unchanged"] and preparation["preferences_unchanged"]
    reopen = read(OUT / "verification/reopen-render.json")
    assert reopen["project_unchanged"] and max(reopen["comparison_with_pre_save_1080"]["max_abs_8bit_rgb"]) <= 1
    snapshots = PRODUCTION / "reproduce"
    assert sha(snapshots / "prepare_portrait_relight.py") == preparation["script_sha256"]
    assert sha(snapshots / "portrait-relight-v1.json") == preparation["settings_sha256"]
    for module, expected in preparation["modules"].items():
        assert sha(snapshots / (module + ".py")) == expected
    picture, project = Path(preparation["picture"]), Path(preparation["project"])
    assert Path(audit["current"]).resolve() == project.resolve()
    protected_files = next(c for c in audit["checks"] if c["name"] == "on_disk_inputs_and_preferences_unchanged")
    assert protected_files["passed"]
    assert protected_files["detail"]["before"]["current"] == preparation["project_sha256"]
    assert Path(reopen["project"]).resolve() == project.resolve()
    assert reopen["project_sha256"] == preparation["project_sha256"]
    assert sha(picture) == preparation["picture_sha256"]
    assert sha(project) == preparation["project_sha256"]
    preview = OUT / "Portrait_Relight_Preview.jpg"
    with Image.open(picture) as image:
        assert image.size == (3840, 2160)
        image.resize((1920, 1080), Image.Resampling.LANCZOS).save(preview, quality=96, subsampling=0)
        # Native pixels, not sharpened/rescaled character details.
        image.crop((520, 160, 1160, 960)).save(OUT / "Aksiniya_Native_Detail.png")
        image.crop((2810, 510, 3410, 1310)).save(OUT / "Ikhor_Native_Detail.png")
    baseline = OUT / "baseline-1080/baseline-4290.png"
    candidate = OUT / "preview-v8/complete-4290.png"
    a, b = read(baseline.parent / "preparation.json"), read(candidate.parent / "preparation.json")
    assert a["source_sha256"] == b["source_sha256"] == preparation["source_sha256"]
    assert a["render"] == b["render"] and a["frame"] == b["frame"] == 4290
    assert a["camera_lens"] == b["camera_lens"]
    assert sha(baseline) == a["picture_sha256"] and sha(candidate) == b["picture_sha256"]
    assert all(b[key] == preparation[key] for key in ("settings_sha256", "modules", "script_sha256"))
    comparison = Image.new("RGB", (1920, 584), (15, 20, 29))
    draw = ImageDraw.Draw(comparison)
    for x, path, label in ((0, baseline, "BEFORE | Clean v2"), (960, candidate, "AFTER | Portrait relight")):
        with Image.open(path) as image:
            assert image.size == (1920, 1080)
            comparison.paste(image.resize((960, 540), Image.Resampling.LANCZOS), (x, 44))
        draw.text((x + 18, 15), label, fill=(235, 236, 240))
    comparison.save(OUT / "Before_After_4290.jpg", quality=96, subsampling=0)
    credits = REPO / "docs/CREDITS_AKSINIYA_IKHOR.md"
    shutil.copy2(credits, OUT / credits.name)
    for name in ("festivities-GPL-3.0.txt", "festivities-sources.json", "Ikhor-RM.txt"):
        source = Path("D:/codex/output/MMD-Clean-Game-Characters-v1/licenses") / name
        assert source.is_file(), str(source)
        destination = OUT / "licenses" / name
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(source, destination)
    delivery = {"id": IDENTITY, "scope": "one still at source frame 4290; no new video or simulation",
                "project": str(project), "project_sha256": sha(project),
                "image": str(picture), "image_sha256": sha(picture), "preview": str(preview),
                "resolution": [3840, 2160], "samples": 128, "dof": True, "motion_blur": False,
                "source_sha256": preparation["source_sha256"],
                "preparation": str(PRODUCTION / "preparation.json"),
                "independent_audit": str(PRODUCTION / "master-verification.json"),
                "reopen_render": str(OUT / "verification/reopen-render.json"),
                "reopen_comparison_max_8bit_rgb_delta": reopen["comparison_with_pre_save_1080"]["max_abs_8bit_rgb"],
                "technical_status": "passed-bounded-still-and-independent-reopen",
                "art_status": "pending-user-review", "user_art_approval": False,
                "remaining": ["Aksiniya face still has less designed shadow than reference",
                              "Ikhor raised palm is more pink/dark than face",
                              "New lighting/material branches have no motion stability validation"],
                "reproduce": str(PRODUCTION / "reproduce"),
                "comparison": {"before": str(baseline), "after": str(candidate),
                               "resolution": [1920, 1080], "samples": 64,
                               "same_camera_frame_dof_view_transform": True}}
    write(OUT / "delivery.json", delivery)
    state_path = REPO / "catalog/current_state.json"
    state = read(state_path)
    old_video = dict(state["latest_review"])
    state["as_of"] = "2026-11-15"
    state["current_task"] = "已实际完成双人人物重新布光4K静帧与独立重开；待猪猪评价。仅静帧，本轮不渲染新五秒或全曲。"
    state["latest_still"] = {"entry_id": IDENTITY, **delivery}
    state["current_learning_round"]["implementation_followup"] = {"id": IDENTITY, "delivery": str(OUT / "delivery.json"), "new_project_created": True, "new_video_delivered": False}
    state["current_learning_round"]["status"] = "initial-reading-and-controls-completed; bounded-still-implementation-in-latest_still"
    state["active_iteration"] = {"id": IDENTITY, "status": delivery["technical_status"],
                                 "user_authorized": True, "source_project_sha256": preparation["source_sha256"],
                                 "project": str(project), "project_sha256": sha(project), "image": str(picture),
                                 "report": str(OUT / "delivery.json"), "guide": "docs/" + GUIDE,
                                 "protocol": "presets/lighting/portrait-relight-v1.json",
                                 "scope": delivery["scope"], "physics_changed": False,
                                 "new_video_delivered": False, "full_song": False, "user_art_approval": False,
                                 "next_action": "先审静帧肤色/衣发明暗/暖边；新链尚需转头、移灯、绕拍和原段动态，不沿用Clean旧72帧结论。"}
    assert state["latest_review"] == old_video
    write(state_path, state)
    path = REPO / "catalog/library.json"
    library = read(path)
    entry = {"id": IDENTITY, "title": "暗场婚礼 · 明亮人物与暖边", "subtitle": "4K静帧：分区材质、粉紫暗面、窄暖边与冷蓝礼堂。",
             "collection": "PORTRAIT / WEDDING RELIGHT", "category": "stage", "family": "guanhaizi",
             "aspect": "landscape", "status": "still", "image": str(picture), "project": str(project),
             "docs": [GUIDE, "PORTRAIT_LIGHTING_AND_SHADOW_STUDY.md"],
             "configs": ["presets/lighting/portrait-relight-v1.json"],
             "scripts": ["scripts/prepare_portrait_relight.py", "scripts/portrait_key_fill.py", "scripts/portrait_rim_ink.py", "scripts/portrait_fur_control.py", "scripts/verify_portrait_relight.py"],
             "report": str(OUT / "delivery.json"),
             "look": ["明亮人物/冷暗礼堂", "窄暖色轮廓光", "深蓝布料与金属分离", "粉紫皮肤暗面", "景深与局部舞台压光"],
             "compatibility": "Blender5.2.2 EEVEE；迁移入口仅接受固定Clean v2 SHA，新工程不可重复安装。角色实际主光/综合受光、原SDF与解析面形代理分层，非原作者Shader复刻。",
             "evidence": ["4290原相机61.73465mm，3840x2160/128samples/DOF，MB关闭",
                          "同相机1080p64samples原版/新版对照；完整Action/几何/贴图/原Alpha独立重开保护核查",
                          "阿克原SDF保留；伊科解析face是美术形体代理，非SDF或纯投影；两条细光弧保持隐藏"],
             "art_review": {"status": "pending", "as_of": "2026-11-15", "feedback": "待猪猪审静帧；阿克脸平、伊科举手偏红暗仍是差距。"},
             "limits": ["仅4290静帧；新分支无动态认证，无新五秒/全曲。", "参考引擎/Shader/灯组未知，未达到或认证作者/游戏品质。", "物理与袖口沿用原有有界证据；没有新增模拟。"],
             "command": "Read docs/PORTRAIT_RELIGHT_IMPLEMENTATION.md; pinned source, fresh output and MMD camera registration required."}
    library["entries"] = [entry] + [e for e in library["entries"] if e["id"] != IDENTITY]
    library["updated"], library["featured"] = "2026-11-15", IDENTITY
    compare = {"id": "portrait-relight-4290", "title": "原版 / 暗场人物重新布光", "subtitle": "同一帧4290、原相机、1080p64samples、相同DOF/曝光/显示变换；这是整套布光材质修改前后，不是单变量实验。",
               "before_label": "Clean v2 原版", "after_label": "重新布光静帧", "before": str(baseline), "after": str(candidate), "doc": GUIDE}
    library["comparisons"] = [compare] + [c for c in library["comparisons"] if c["id"] != compare["id"]]
    for group in library["knowledge_groups"]:
        group["docs"] = [name for name in group["docs"] if name != GUIDE]
        if group["id"] == "lighting":
            group["docs"].insert(0, GUIDE)
    write(path, library)
    queue_path = REPO / "catalog/learning_queue.json"
    queue = read(queue_path)
    card = next(c for c in queue["cards"] if c["id"] == "portrait-received-light-calibration")
    card["related_implementation"] = {"guide": "docs/" + GUIDE, "delivery": str(OUT / "delivery.json"),
                                      "scope": "实际4K单帧/独立重开；原综合探针非纯visibility，未补齐卡片全部动态关卡",
                                      "stage_promotion": False, "new_video": False,
                                      "evidence_reports": [{"path": str(p), "sha256": sha(p)} for p in (OUT / "delivery.json", PRODUCTION / "preparation.json", PRODUCTION / "master-verification.json", OUT / "verification/reopen-render.json")]}
    card["baseline"]["scope"] = "冻结Clean v2；初轮三诊断未保存工程，后续重新布光已另存新工程，见related_implementation"
    card["checks"]["reopen"] = "已有4290静帧新工程、独立结构重开与同帧重渲一致证据；完整动态后仍需重开相关抽样，不升动态关卡。"
    card["limits"] = ["本轮已有4K单帧、新工程和独立保存重开；卡片全部受光/动态验收尚未完成，维持hypothesis并保留有界实施证据。", "新链无转头/移灯/绕拍/交叠连续画面，无新五秒或用户美术认可。", "paierer/观海子Shader未知，保留指定礼堂，不因风格名宣称品质达标。"]
    card["next_action"] = "本轮已产出4K重新布光静帧并独立重开；先收用户美术评价，再补yaw/pitch/roll、移灯、绕拍与交叠，不能把旧Clean动态结论转到新链。"
    write(queue_path, queue)
    print("PORTRAIT_STILL_PACKAGED", project, picture)


if __name__ == "__main__":
    main()
