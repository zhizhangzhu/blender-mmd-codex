# -*- coding: utf-8 -*-
# ruff: noqa: UP009
"""Record reference observations and the bounded Normal-input experiment."""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
OUT = Path("D:/codex/output/Goo-Reference-Normal-Study-2026-11-17")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


result = read(OUT / "measurements.json")
assert result["max_abs_default_vs_up"] == 0
assert result["max_abs_default_vs_down"] == 0
assert result["positive_control_up_vs_down"] > 0.99
assert result["independent_reopen_max_abs"] == 0
refs = []
for filename in (
    "codex-clipboard-5fc40036-aef6-4f73-821b-ee556a997da4.png",
    "codex-clipboard-402815a8-d771-4a84-ba9f-93e67de1a493.png",
    "codex-clipboard-5fbf5980-4b85-48ed-b610-231e0ce25f70.png",
):
    path = Path("C:/Users/ADMINI~1/AppData/Local/Temp") / filename
    with Image.open(path) as im:
        size = list(im.size)
    refs.append(
        {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "dimensions": size,
        }
    )
guide = "docs/GOO_REFERENCE_FACE_HAIR_STUDY_2026_11_17.md"
ledger = {
    "date": "2026-11-17",
    "guide": guide,
    "references": refs,
    "reference_scope": "Three supplied stills visually inspected, not animation or shader/engine identification; no user reference copies redistributed",
    "visual_targets": [
        "calm coloured skin with selected warm shadow shapes",
        "cool hair with clear strand masses and contained highlight bands",
        "thin region-specific outlines",
        "readable iris structure and selective eye glints",
        "separate cloth/metal/gem highlight behavior",
        "limited global bloom",
    ],
    "reading": {
        "official_url": "https://github.com/dillongoostudios/goo-engine/blob/goo-engine-v4.4-release/source/blender/nodes/shader/nodes/node_shader_shader_info.cc",
        "community_url": "https://github.com/NaMgAl-Studio/goo-engine-5.2.0/blob/main/source/blender/draw/engines/eevee/shaders/eevee_nodetree_lib.bsl.hh",
        "scope": "Revisited input fallback and shader_info_eval Normal/position paths; not new full-source reading or same-commit binary lock",
    },
    "experiment": result,
    "finding": "In the scoped local Half-lambert control, linked up/down Normal does not change pixels; explicit dot-product positive control does",
    "production_modified": False,
    "new_character_render": False,
    "eye_see_through": "still deferred",
    "all_basics_mastered": False,
}
save(REPO / "docs/research/GOO_REFERENCE_NORMAL_2026_11_17.json", ledger)
course_path = REPO / "presets/workflows/goo-foundations-v1.json"
course = read(course_path)
for module in course["modules"]:
    if module["id"] == "F2":
        module["status"] = "partial_new_normal_input_runtime_limit_verified"
        module["new_evidence"] = str(OUT / "measurements.json")
        module["remaining"] = (
            "Normal on other outputs, WorldPosition, and more light types not covered by new control"
        )
save(course_path, course)
state_path = REPO / "catalog/current_state.json"
state = read(state_path)
if state["latest_learning"].get("guide") != guide:
    state["previous_learning_before_normal_control"] = state["latest_learning"]
state["latest_learning"] = {
    "date": "2026-11-17",
    "guide": guide,
    "ledger": "docs/research/GOO_REFERENCE_NORMAL_2026_11_17.json",
    "scope": "New reference observations, Normal-input controls with analytic positive control and independent reopen; no production modification",
}
state["current_task"] = (
    "继续Goo基础学习，以新三张近景为质量目标。已发现并实测当前5.2社区构建的Half-Lambert对Normal连接无响应，显式点积正对照有效，重开一致；基础参数表已纠正。当前人物v6未改，尚未达到参考质量，眼透仍暂缓。"
)
state["latest_user_visual_request"] = {
    "date": "2026-11-17",
    "reference": "Three new face/hair closeup images",
    "guide": guide,
    "requirements": ledger["visual_targets"],
    "eye_see_through": "deferred",
    "quality_achieved": False,
}
save(state_path, state)
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 19)
board = Image.new("RGB", (3 * 384, 2 * 424), (36, 40, 48))
draw = ImageDraw.Draw(board)
for index, (name, label) in enumerate(
    (
        ("A-info-default-normal", "A  默认Normal"),
        ("B-info-normal-up", "B  Normal接向上"),
        ("C-info-normal-down", "C  Normal接向下"),
        ("D-math-normal-up", "D  显式点积：向上"),
        ("E-math-normal-down", "E  显式点积：向下"),
    )
):
    x, y = index % 3 * 384, index // 3 * 424
    draw.text((x + 10, y + 10), label, fill="white", font=font)
    im = Image.open(OUT / (name + ".png")).convert("RGBA")
    board.paste(im, (x, y + 40), im)
draw.text(
    (2 * 384 + 14, 424 + 110),
    "A/B/C相同；D/E可变化\n仅当前构建与测试路径\n不代表全部输出与版本",
    fill="white",
    font=font,
)
board.save(OUT / "normal-input-comparison.jpg", quality=94)
path = REPO / guide


def absolute_link(match):
    target = match.group(2)
    if urlsplit(target).scheme or target.startswith("#"):
        return match.group(0)
    return (
        "[" + match.group(1) + "](" + (path.parent / target).resolve().as_posix() + ")"
    )


(OUT / "近景参考与法线基础验证.md").write_text(
    re.sub(r"\[([^\]]+)\]\(([^)]+)\)", absolute_link, path.read_text(encoding="utf-8")),
    encoding="utf-8",
)
save(OUT / "study-summary.json", ledger)
print(
    json.dumps(
        {
            "cases": len(result["cases"]),
            "reference_count": len(refs),
            "reopen_max_abs": result["independent_reopen_max_abs"],
            "quality_achieved": False,
        }
    )
)
