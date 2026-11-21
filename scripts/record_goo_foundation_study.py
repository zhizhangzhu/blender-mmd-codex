# -*- coding: utf-8 -*-
# ruff: noqa: UP009
"""Record actual Goo foundation reading and isolated controls, not full mastery."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
OUT = Path("D:/codex/output/Goo-Basics-Study-2026-11-17")
PRIVATE = Path("D:/codex/temp/Goo-Official-Basics-2026-11-17")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, obj):
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


inventory = read(OUT / "parameter-inventory-v2.json")
measurements = read(OUT / "light-group-controls/measurements.json")
reopen = read(OUT / "light-group-controls/reopen-verification.json")
assert inventory["node_count"] == 13 and not inventory["production_loaded"]
assert measurements["measurements"]["A_vs_C_max_abs_linear_difference"] == 0
assert reopen["passed"]
source_lock = read(PRIVATE / "goo-engine-v4.4-release/source-lock.json")
acquisitions = read(PRIVATE / "goo-engine-v4.4-release/sources.json")
read_files = [
    "node_shader_shader_info.cc",
    "node_shader_light_info.cc",
    "node_shader_curvature.cc",
    "node_shader_water_ripples.cc",
    "node_shader_screenspace_info.cc",
]
for name in read_files:
    assert (PRIVATE / "goo-engine-v4.4-release" / name).is_file()
ledger = {
    "date": "2026-11-17",
    "guide": "docs/GOO_FOUNDATIONS_AND_PARAMETERS.md",
    "user_priority": "Goo primary, learn basic functionality and parameter meanings before advanced rendering; native MMD route deferred",
    "official_sources": [
        "https://www.dillongoostudios.com/gooengine",
        "https://www.dillongoostudios.com/gooengine-features",
        "https://github.com/dillongoostudios/goo-engine/branches/all",
    ],
    "official_website_scope": "Main page and complete feature directory read, including shading, procedural nodes and non-render UI additions; author images not analysed and linked videos not played",
    "official_source_lock": source_lock,
    "default_branch_note": "goo-engine-main 8457395892beec33d4605ef9d894a1aff4a8d79f lacks the Half-lambert output in its Shader Info declaration; use release branch for current official reference",
    "acquisitions": acquisitions,
    "actually_read_source_files": read_files,
    "source_read_scope": "Short node declarations, input fallbacks, UI selectors and GPU bridges; not a full renderer code audit or a proof that every source variant is compiled",
    "runtime": {
        k: inventory[k] for k in ("binary", "version", "build_hash", "node_count")
    },
    "inventory": str(OUT / "parameter-inventory-v2.json"),
    "inventory_scope": inventory["limits"],
    "new_static_evidence": measurements,
    "independent_reopen": reopen,
    "prior_evidence": "docs/research/GOO_FEATURE_MME_MECHANISMS_2026_11_16.json",
    "all_basics_mastered": False,
    "pending": [
        "SDF mode-specific formulas and paired controls",
        "additional shader parameter variation tests",
        "non-render official UI features in community port",
        "broader version/animation behavior",
    ],
    "production_loaded_or_modified": False,
    "native_mmd_started": False,
    "video_created": False,
    "third_party_complete_sources_in_repo": False,
}
save(REPO / "docs/research/GOO_FOUNDATIONS_2026_11_17.json", ledger)
state = read(REPO / "catalog/current_state.json")
if state["latest_learning"].get("guide") != ledger["guide"]:
    state["previous_learning_before_goo_foundations"] = state["latest_learning"]
state["latest_learning"] = {
    "date": "2026-11-17",
    "guide": ledger["guide"],
    "ledger": "docs/research/GOO_FOUNDATIONS_2026_11_17.json",
    "scope": "Official basics, local 13-node parameter inventory, single-vs-multiple key light group controls and independent reopen; incomplete foundation curriculum",
}
state["workflow_evaluation"].update(
    status="goo_primary_foundations_first",
    guide=ledger["guide"],
    native_mmd_route="deferred_by_user",
    mme_compatibility_layer="not_started",
)
state["current_task"] = (
    "猪猪选择继续Goo，要求先掌握基础功能和参数，再学高阶内容。已读官网完整功能清单与官方4.4发布分支部分节点，提取本机13类专属节点参数，完成单主光／反向双灯／灯组排除三张独立球体静帧和重开一致性验证。基础课程仍未全部完成，人物v6工程未修改，原生MMD与通用MME兼容层暂缓。"
)
save(REPO / "catalog/current_state.json", state)
route_path = REPO / "presets/workflows/mmd-mme-goo-v1.json"
route = read(route_path)
route["selection_status"] = "deferred_by_user_in_favour_of_goo_foundations"
save(route_path, route)
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 19)
board = Image.new("RGB", (640, 3 * 395), (23, 27, 34))
draw = ImageDraw.Draw(board)
for i, (name, caption) in enumerate(
    (
        ("A-single-key", "A  单主光：连续明暗与三段色带"),
        ("B-two-opposite-lights", "B  相反双灯进入同组：明暗被推平"),
        ("C-fill-excluded-from-key-group", "C  补灯排除主光组：恢复A的层次"),
    )
):
    board.paste(
        Image.open(OUT / "light-group-controls" / (name + ".png")).convert("RGB"),
        (0, i * 395 + 35),
    )
    draw.text((12, i * 395 + 7), caption, fill="white", font=font)
board.save(OUT / "basic-light-group-comparison.jpg", quality=94)
path = REPO / ledger["guide"]
content = path.read_text(encoding="utf-8")


def absolute_link(match):
    target = match.group(2)
    if urlsplit(target).scheme or target.startswith("#"):
        return match.group(0)
    return (
        "[" + match.group(1) + "](" + (path.parent / target).resolve().as_posix() + ")"
    )


(OUT / "Goo基础功能与参数.md").write_text(
    re.sub(r"\[([^\]]+)\]\(([^)]+)\)", absolute_link, content), encoding="utf-8"
)
save(OUT / "study-summary.json", ledger)
(OUT / "README.md").write_text(
    "# Goo 基础学习\n\n先基础参数，再高阶卡渲；当前尚未全部掌握。\n\n"
    "- [基础说明与学习顺序](Goo基础功能与参数.md)\n"
    "- [本机参数完整清单](parameter-inventory-v2.json)\n"
    "- [灯组基础对照](basic-light-group-comparison.jpg)\n"
    "- [实际阅读与实验记录](study-summary.json)\n\n"
    "本轮没有加载人物工程，没有生成视频。\n",
    encoding="utf-8",
)
print(
    json.dumps(
        {
            "nodes": 13,
            "native_static_controls": 3,
            "reopen_passed": reopen["passed"],
            "all_basics_mastered": False,
        },
        ensure_ascii=False,
    )
)
