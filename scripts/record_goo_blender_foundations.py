# -*- coding: utf-8 -*-
# ruff: noqa: UP009
"""Record the bounded input/display experiments and official reading, not production gains."""

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
OUT = Path("D:/codex/output/Goo-Blender-Official-Study-2026-11-18")
INPUTS = Path("D:/codex/output/Goo-Input-Matrix-Study-2026-11-18")
CACHE = Path("D:/codex/temp/Goo-Blender-Official-Study-2026-11-18")
GUIDE = "docs/GOO_BLENDER_FOUNDATIONS_2026_11_18.md"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
matrix = {}
for build in ("goo52", "goo43"):
    result = read(INPUTS / build / "measurements.json")
    reopen = read(INPUTS / build / "reopen-verification.json")
    assert reopen["passed"] and reopen["max_abs_linear_rgba_difference"] == 0
    assert not result["production_loaded"]
    delta = result["deltas_vs_default"]
    assert delta["N-down"]["diffuse_bsdf_combined"]["max_abs_scaled"] > 0.03
    for panel in ("half_lambert", "diffuse", "cast", "self"):
        assert delta["L-real-move"][panel]["max_abs_scaled"] > 0
        if build == "goo52":
            assert delta["N-down"][panel]["max_abs_scaled"] == 0
            assert delta["P-offset"][panel]["max_abs_scaled"] == 0
        else:
            assert delta["P-offset"][panel]["max_abs_scaled"] > 0
    assert build != "goo43" or delta["N-down"]["half_lambert"]["max_abs_scaled"] > 0.8
    matrix[build] = {"measurements": result, "reopen": reopen}

# This is a labelled contact sheet of our own research renders, not a new render.
sheet = Image.new("RGB", (1100, 1610), "#17202e")
draw = ImageDraw.Draw(sheet)
draw.text(
    (20, 10),
    "Shader Info input controls | Compare changes WITHIN each build",
    font=font,
    fill="white",
)
draw.text(
    (20, 38),
    "Columns: Half-Lambert | Diffuse x0.1 | Cast | Self | Diffuse BSDF -> RGB x0.1",
    font=small,
    fill="#c3d2e6",
)
row = 0
for build in ("goo52", "goo43"):
    for label in ("A-default", "N-down", "P-offset"):
        y = 72 + row * 252
        draw.text((20, y), build + " / " + label, font=font, fill="white")
        with Image.open(INPUTS / build / (label + ".png")) as im:
            sheet.paste(im.convert("RGB"), (70, y + 24))
        row += 1
sheet.save(OUT / "input-comparison.jpg", quality=94)

color = read(OUT / "color-controls/measurements.json")
assert all(case["source_linear_max_difference"] == 0 for case in color["cases"])
chart = Image.new("RGB", (880, 630), "#17202e")
draw = ImageDraw.Draw(chart)
draw.text(
    (20, 10),
    "One linear float buffer; different display saves | sRGB, look None",
    font=font,
    fill="white",
)
draw.text(
    (235, 40),
    "0.18 | 0.5 | 1 | 2 | 4 | warm | blue | HDR blue",
    font=small,
    fill="white",
)
sampling = {
    "method": "Pillow decoded RGB8 centre samples of display PNG; source files are 16-bit; not linear data",
    "cases": {},
}
for i, case in enumerate(color["cases"]):
    label = case["id"]
    y = 74 + i * 106
    draw.text((20, y + 25), label, font=font, fill="white")
    with Image.open(OUT / "color-controls" / (label + ".png")) as im:
        im = im.convert("RGB")
        chart.paste(im, (220, y))
        sampling["cases"][label] = {
            patch["id"]: list(im.getpixel((j * 80 + 40, 40)))
            for j, patch in enumerate(color["patches"])
        }
chart.save(OUT / "display-transform-comparison.jpg", quality=95)
save(OUT / "color-controls/display-samples-rgb8.json", sampling)

sources = []
seen = set()
for manifest in (
    "acquisition.json",
    "acquisition52.json",
    "acquisition52-colour-retry.json",
):
    for source in read(CACHE / manifest):
        if source["id"] in seen:
            continue
        seen.add(source["id"])
        text_path = CACHE / (source["id"] + ".txt")
        source["private_body_path"] = text_path.as_posix()
        source["body_sha256"] = hashlib.sha256(text_path.read_bytes()).hexdigest()
        source["reading_scope"] = "full extracted article text"
        if source["id"] == "goo-features":
            source["reading_scope"] = (
                "targeted reread: lighting/shadows, light groups, Light Info and screen resources; other feature list previously read"
            )
        elif source["id"] == "blender52-color-management":
            source["reading_scope"] = (
                "index only; substantive child articles separately read"
            )
        sources.append(source)
sources.extend(
    [
        {
            "url": "https://github.com/dillongoostudios/goo-engine/blob/goo-engine-v4.4-release/source/blender/nodes/shader/nodes/node_shader_shader_info.cc",
            "reading_scope": "targeted reread: declaration, defaults and default position/normal forwarding",
        },
        {
            "url": "https://github.com/dillongoostudios/goo-engine/blob/goo-engine-v4.4-release/source/blender/gpu/shaders/material/gpu_shader_material_shader_info.glsl",
            "reading_scope": "new full short wrapper; forwards arguments to calc_shader_info; callee not acquired",
            "binary_commit_match": "not established",
        },
    ]
)
ledger = {
    "date": "2026-11-18",
    "guide": GUIDE,
    "sources": sources,
    "acquisition_limits": [
        "Web reader failed on several public manuals; ordinary public HTTP fetch succeeded, no authentication or access controls bypassed",
        "Initial 5.2 colour subpage requests failed; corrected settings link from actual index and reused previously successful normal User-Agent; all three succeeded",
        "Three guessed release-branch implementation paths returned 404; complete calc_shader_info backend not acquired, wrapper is not full backend audit",
        "4.4 manual and online 5.2 manual differ from community binary; documentation is not proof of local implementation",
    ],
    "matrix_controls": matrix,
    "display_controls": color,
    "display_sampling": sampling,
    "visual_inspection": "Native A/N-down/P-offset and real light control stills plus labelled contact sheets; display patches checked; not characters",
    "findings": [
        "In scoped 5.2 point-light controls, linked Normal and WorldPosition do not affect four Shader Info outputs; physical light changes and ordinary Diffuse BSDF Normal do",
        "Existing 4.3 build responds to Normal on Half-Lambert/Diffuse and to position on all four outputs; not an official 4.4 binary validation",
        "Both saved research blends reproduce exact linear RGBA on independent reopen",
        "Display view/exposure changes generated PNG output while source linear float pixels remain identical",
    ],
    "unverified": [
        "Ambient and other light types",
        "Normal Edit on current Goo runtime",
        "all shadow tuning parameters in production",
        "animation",
        "other Goo nodes and interface features",
    ],
    "production_loaded": False,
    "production_modified": False,
    "new_character_render": False,
    "video_created": False,
    "eye_see_through": "deferred",
    "all_basics_mastered": False,
    "reference_quality_achieved": False,
}
save(REPO / "docs/research/GOO_BLENDER_FOUNDATIONS_2026_11_18.json", ledger)
course_path = REPO / "presets/workflows/goo-foundations-v1.json"
course = read(course_path)
course["date"] = "2026-11-18"
course["blender_foundation_guide"] = GUIDE
for module in course["modules"]:
    if module["id"] == "F0":
        module["status"] = (
            "official_reading_and_new_display_output_controls_verified_not_character_calibration"
        )
        module["new_evidence"] = (OUT / "color-controls/measurements.json").as_posix()
    elif module["id"] == "F2":
        module["status"] = (
            "partial_four_outputs_two_build_input_controls_and_reopen_verified"
        )
        module["new_evidence"] = [
            (INPUTS / build / "measurements.json").as_posix()
            for build in ("goo52", "goo43")
        ]
        module["remaining"] = (
            "Ambient, other lights/meshes/animation, current mesh-normal modifier route; not all shadow parameters mastered"
        )
save(course_path, course)
state_path = REPO / "catalog/current_state.json"
state = read(state_path)
if state["latest_learning"].get("guide") != GUIDE:
    state["previous_learning_before_blender_foundations"] = state["latest_learning"]
state["as_of"] = "2026-11-18"
state["latest_learning"] = {
    "date": "2026-11-18",
    "guide": GUIDE,
    "ledger": "docs/research/GOO_BLENDER_FOUNDATIONS_2026_11_18.json",
    "scope": "Official Goo targeted reread/new wrapper, Blender 4.4/5.2 foundation articles, two-build input controls and independent reopen, display-only charts; no production changes",
}
state["current_task"] = (
    "继续Goo官网／官方GitHub与Blender官方基础学习。已扩展四路输入及WorldPosition双版本静帧控制并独立重开；当前5.2社区版覆盖输入无响应、旧4.3对照有效。补读法线／灯影／色彩正文并完成五张显示转换图；人物v6未改、未达参考质量，眼透仍暂缓，仅静帧。"
)
save(state_path, state)
shutil.copyfile(REPO / GUIDE, OUT / "Goo与Blender基础学习.md")
save(
    OUT / "study-summary.json",
    {
        "guide": GUIDE,
        "ledger": "docs/research/GOO_BLENDER_FOUNDATIONS_2026_11_18.json",
        "production_modified": False,
        "all_basics_mastered": False,
        "reading_sources": len(sources),
        "matrix_cases": 10,
        "independent_reopens": 2,
        "display_save_cases": 5,
    },
)
print(
    json.dumps(
        {"recorded": True, "sources": len(sources), "sampling": sampling["cases"]},
        ensure_ascii=False,
    )
)
