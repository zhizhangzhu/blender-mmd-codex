# -*- coding: utf-8 -*-
# ruff: noqa: UP009
"""Record organization and route research; never execute or modify a scene."""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("D:/codex/output/MMD-Repo-Organization-2026-11-17")
CACHE = Path("D:/codex/temp/MME-Deep-Study-2026-11-16")
DATE = "2026-11-17"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


OUTPUT.mkdir(exist_ok=True)
state_path = ROOT / "catalog/current_state.json"
state = read(state_path)
active = state["active_iteration"]
assert active["id"] == "mme-reference-light-balanced-still-v3"
assert sha(Path(active["project"])) == active["project_sha256"]
packages = []
for entry in read(ROOT / "docs/research/MME_DEEP_STUDY_2026_11_16.json")["archives"]:
    path = CACHE / "packages" / entry["archive"]
    observed = sha(path) if path.is_file() else None
    assert observed == entry["sha256"], str(path)
    packages.append(
        {"archive": entry["archive"], "source": entry["source"], "sha256": observed}
    )
native = []
for path in Path("E:/tools").rglob("*"):
    if not path.is_file():
        continue
    name = path.name.lower()
    if (
        "mikumikudance" in name
        or "mmeffect" in name
        or (path.suffix.lower() == ".exe" and re.search("miku|mmd|pmx|pmd", name))
    ):
        native.append(str(path))
ledger = {
    "date": DATE,
    "guide": "docs/MMD_MME_GOO_WORKFLOW.md",
    "lab_guide": "docs/MME_NATIVE_LEARNING_LAB.md",
    "recipe": "presets/workflows/mmd-mme-goo-v1.json",
    "local_environment": {
        "recursive_search": "E:/tools: MikuMikuDance/MMEffect names, and miku/mmd/pmx/pmd exe names",
        "additional_top_level_directory_checks": [
            "D:/Program Files",
            "C:/Users/Administrator/Downloads",
            "D:/codex/workspace",
        ],
        "native_matches": native,
        "scope": "Scoped search only, not all disks or every installation location",
        "native_mmd_started": False,
        "native_mme_executed": False,
        "software_installed": False,
        "renderer_started": False,
    },
    "cached_packages_verified": packages,
    "cache_reading": [
        "msToonCoordinator2.1 full readme: native loading, Main/RT assignment and controller diagnostic stages",
        "PowerShader preset explanations: Main/MMD/AllShadow/NoShadow/Toon roles",
        "Diffusion readme: independent Tr and Si controls and default strength warning",
    ],
    "online_primary_reading": [
        {
            "url": "https://sites.google.com/view/vpvp/",
            "scope": "MMD x64 distribution and runtime links",
        },
        {
            "url": "https://bowlroll.net/file/35013",
            "scope": "MME x64 0.37 package metadata, not package README",
        },
        {
            "url": "https://github.com/ray-cast/ray-mmd",
            "scope": "README runtime and feature list; original HLSL/DX9 environment",
        },
        {
            "url": "https://github.com/MikuMikuShaders/LightBloom",
            "scope": "README native requirements and threshold/radius/layer controls",
        },
        {
            "url": "https://note.com/mashimashi_note/n/n2c2144638054",
            "scope": "ShadeColorRT, pseudoSSS and Shade_Normal restrictions",
        },
        {
            "url": "https://github.com/MMD-Blender/blender_mmd_tools",
            "scope": "Maintainer supported data formats; fileio.py VPD current pose export operator",
        },
    ],
    "recommendation": "Test a full native MMD/MME still baseline first, use Goo for assets and verified deformation/simulation, postpone split-engine composition",
    "new_findings": [
        "msTC requires Main and RT assignments; merely loading Shade.x does not reproduce it",
        "Shade_Normal does not use ExcellentShadow cast shadows; relevant to the missing fringe shadow problem",
        "Native MME already has multi-light, volume, DOF and bloom implementations; these are not categorical Goo-only features",
    ],
    "production_project_changed": False,
    "video_created": False,
    "cases_executed": [],
    "third_party_complete_source_redistributed": False,
}
save(ROOT / "docs/research/MMD_MME_GOO_ROUTE_2026_11_17.json", ledger)
state["repository_organization"] = {
    "date": DATE,
    "guide": "docs/REPOSITORY_ORGANIZATION_2026_11_17.md",
    "navigation": "docs/REPOSITORY_GUIDE.md",
    "index": "catalog/repository_index.json",
    "snapshot": "docs/history/2026-11-17/repository-before-organization",
    "production_files_moved": False,
    "historical_experiments_deleted": False,
}
state["workflow_evaluation"] = {
    "date": DATE,
    "status": "proposal_ready_native_not_run",
    "guide": ledger["guide"],
    "recipe": ledger["recipe"],
    "native_runtime_verified": False,
    "current_goo_project_retained": active["project"],
}
state["previous_learning_before_native_route"] = state["latest_learning"]
state["latest_learning"] = {
    "date": DATE,
    "guide": ledger["guide"],
    "ledger": "docs/research/MMD_MME_GOO_ROUTE_2026_11_17.json",
    "scope": "Native MME assignment, shadow RT compatibility, supported interchange and scoped local runtime search; no native execution",
}
state["current_task"] = (
    "已整理仓库入口、脚本／文件分类、快照和历史状态说明，并完成原生MMD／MME主渲＋Goo补充分工方案。原生环境尚未运行，当前制作候选仍为Goo v6静帧，待猪猪评价；本轮未改工程或渲染。"
)
save(state_path, state)


def delivery_document(relative):
    path = ROOT / relative
    content = path.read_text(encoding="utf-8-sig")

    def absolute_link(match):
        target = match.group(2)
        if target.startswith("#") or urlsplit(target).scheme:
            return match.group(0)
        resolved = (path.parent / target).resolve().as_posix()
        return "[" + match.group(1) + "](" + resolved + ")"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", absolute_link, content)


for relative in (
    "docs/MMD_MME_GOO_WORKFLOW.md",
    "docs/MME_NATIVE_LEARNING_LAB.md",
    "docs/REPOSITORY_ORGANIZATION_2026_11_17.md",
):
    (OUTPUT / Path(relative).name).write_text(
        delivery_document(relative), encoding="utf-8"
    )
save(OUTPUT / "native-environment-and-sources.json", ledger)
(OUTPUT / "README.md").write_text(
    "# 仓库整理与原生 MMD MME 方案\n\n"
    "建议先用MMD／MME建立完整静帧基准，Goo做模型和复杂变形／模拟辅助；暂不把人物与场景拆到不同引擎。\n\n"
    "- [完整分工方案](MMD_MME_GOO_WORKFLOW.md)\n"
    "- [原生预设学习实验](MME_NATIVE_LEARNING_LAB.md)\n"
    "- [整理记录](REPOSITORY_ORGANIZATION_2026_11_17.md)\n\n"
    "本轮只整理与研究；未安装MMD／MME、未迁移生产工程、未生成视频。\n",
    encoding="utf-8",
)
print(
    json.dumps(
        {
            "packages_verified": len(packages),
            "native_runtime_matches": native,
            "production_sha_unchanged": active["project_sha256"],
            "delivery": str(OUTPUT),
        },
        ensure_ascii=False,
    )
)
