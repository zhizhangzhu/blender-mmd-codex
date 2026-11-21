"""Index repository files without importing or executing production scripts."""

import argparse
import ast
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = {
    "catalog/repository_index.json": "Generated machine-readable repository index",
    "docs/REPOSITORY_FILE_INDEX.md": "Generated complete file navigation",
    "scripts/README.md": "Generated script navigation and side-effect hints",
}
IGNORED = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv"}
QUERY_TOOLS = {
    "repository_index.py",
    "audit_knowledge.py",
    "learning_queue.py",
    "knowledge_route.py",
    "mmd_studio.py",
    "studio_registry.py",
    "studio_tasks.py",
    "reference_study.py",
    "studio_scene_contract.py",
}
ROLES = {
    "studio_iteration": "制作、图审与经验闭环",
    "query_and_maintenance": "查询与维护入口",
    "version_recording": "版本登记与打包",
    "version_preparation": "版本制作与迁移",
    "rendering": "渲染与视频输出",
    "diagnostics": "探针与诊断",
    "research": "资料读取与比较",
    "utility": "其他工具与库模块",
}


def role_for(path):
    name = path.name
    if name in {"studio_iteration.py", "studio_review_board.py", "studio_lessons.py", "studio_publish.py", "studio_publish_worker.py"}:
        return "studio_iteration"
    if name in QUERY_TOOLS:
        return "query_and_maintenance"
    if name in {"studio_bench.py", "studio_scene_worker.py"}:
        return "diagnostics"
    if name == "create_studio_fixture.py":
        return "research"
    if name.startswith(("package_", "record_", "complete_", "finish_")):
        return "version_recording"
    if name.startswith(
        (
            "prepare_",
            "finalize_",
            "refine_",
            "apply_",
            "integrate_",
            "add_",
            "repair_",
            "restrain_",
            "save_",
        )
    ):
        return "version_preparation"
    if name.startswith(("render_", "run_goo_", "encode_", "mux_", "assemble_")):
        return "rendering"
    if name.startswith(
        ("probe_", "inspect_", "audit_", "verify_", "diagnose_", "check_", "snapshot_")
    ) or name.endswith("_probe.py"):
        return "diagnostics"
    if name.startswith(
        (
            "study_",
            "fetch_",
            "cache_",
            "extract_",
            "transcribe_",
            "compare_",
            "video_reference_",
        )
    ):
        return "research"
    return "utility"


def summarize(path, relative):
    if relative in GENERATED:
        return GENERATED[relative], []
    if path.suffix.lower() not in {
        ".py",
        ".md",
        ".json",
        ".ps1",
        ".js",
        ".css",
        ".html",
    }:
        return "Repository source or supporting file", []
    source = path.read_text(encoding="utf-8-sig", errors="replace")
    hints = []
    if path.suffix == ".py":
        try:
            tree = ast.parse(source)
            summary = (
                ast.get_docstring(tree)
                or "No module description; read source before use"
            )
            calls = [
                call_name(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)
            ]
            for found, label in (
                ("bpy.ops.render.render" in calls, "native_render_call"),
                (any(n.startswith("bpy.ops.wm.save") for n in calls), "saves_blend"),
                (
                    any(n.startswith("subprocess.") for n in calls),
                    "starts_external_process",
                ),
                (any(n.endswith(".write_text") for n in calls), "writes_text_files"),
            ):
                if found:
                    hints.append(label)
        except SyntaxError:
            summary = "Module summary unavailable in indexing Python; read source"
            hints.append("syntax_not_parsed")
        if "catalog/current_state" in source:
            hints.append("references_current_state")
    elif path.suffix == ".md":
        summary = next(
            (line.lstrip("# ") for line in source.splitlines() if line.startswith("#")),
            "Markdown document",
        )
    elif path.suffix == ".json":
        try:
            data = json.loads(source)
            summary = (
                str(data.get("id") or data.get("purpose") or "JSON data")
                if isinstance(data, dict)
                else "JSON data collection"
            )
        except ValueError:
            summary = "JSON data; validate before use"
    else:
        summary = "Source or configuration; read before use"
    return summary.splitlines()[0][:150], hints


def call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return call_name(node.value) + "." + node.attr
    return ""


def build_index(root):
    paths = {
        p.relative_to(root).as_posix(): p
        for p in root.rglob("*")
        if p.is_file() and not set(p.relative_to(root).parts).intersection(IGNORED)
    }
    # Include generated targets before first write, without self-referential sizes/hashes.
    paths.update({name: root / name for name in GENERATED})
    entries = []
    for name, path in sorted(paths.items()):
        section = "root" if "/" not in name else name.split("/")[0]
        if name.startswith("docs/history/"):
            section = "history"
        elif name.startswith("docs/research/"):
            section = "research_ledgers"
        summary, hints = summarize(path, name)
        item = {"path": name, "section": section, "summary": summary}
        if hints:
            item["static_hints"] = hints
        if section == "scripts" and path.suffix == ".py":
            item["role"] = role_for(path)
            item["execution_status"] = (
                "read_cli_contract"
                if path.name in QUERY_TOOLS
                else "review_input_and_side_effects"
            )
        entries.append(item)
    return {
        "schema_version": 1,
        "purpose": "Navigation only; static hints are not a safety or production certification",
        "excluded_directories": sorted(IGNORED),
        "counts": dict(sorted(Counter(e["section"] for e in entries).items())),
        "entries": entries,
    }


def escape(value):
    return str(value).replace("|", "／").replace("\n", " ")


def documents(index):
    groups = defaultdict(list)
    scripts = defaultdict(list)
    for entry in index["entries"]:
        groups[entry["section"]].append(entry)
        if entry.get("role"):
            scripts[entry["role"]].append(entry)
    all_lines = [
        "# 仓库全文件索引",
        "",
        "自动生成；刷新用`python -m scripts.repository_index --write`。分类只用于导航，不表示逐行审计或可以直接运行。",
        "",
        "[仓库导航](REPOSITORY_GUIDE.md) · [脚本分类](../scripts/README.md)",
        "",
    ]
    for section, entries in sorted(groups.items()):
        all_lines += [
            f"## {section}（{len(entries)}）",
            "",
            "| 文件 | 用途 |",
            "| --- | --- |",
        ]
        for e in entries:
            all_lines.append(
                f"| [{e['path']}](../{e['path']}) | {escape(e['summary'])} |"
            )
        all_lines.append("")
    script_lines = [
        "# 脚本导航",
        "",
        "自动生成；从[当前状态](../catalog/current_state.json)确认工程，再读[工具输入契约](../docs/TOOL_AND_PRESET_MAP.md)。版本脚本保留原路径，避免破坏导入。以下分类和副作用提示是静态启发式，不能替代源码审查。",
        "",
        "## 日常入口",
        "",
        "```powershell",
        "python -m scripts.repository_index --check",
        "python -m scripts.audit_knowledge",
        "python -m scripts.mmd_studio status",
        'python -m scripts.mmd_studio context --task reference --query "白衣 发束"',
        'python -m scripts.mmd_studio lessons --task lighting --query "舞台 白衣"',
        "python -m scripts.learning_queue plan --limit 3",
        "```",
        "",
        "索引工具不执行被扫描的脚本。`--write`只更新索引；`audit_knowledge --output`写报告。诊断脚本仍可能渲染或启动子进程。当前原生MME实验为[方案](../docs/MME_NATIVE_LEARNING_LAB.md)，没有可用的一键MMD主渲承诺。",
        "",
    ]
    for role, title in ROLES.items():
        entries = scripts.get(role, [])
        script_lines += [
            f"## {title}（{len(entries)}）",
            "",
            "| 文件 | 模块说明 | 静态提示 |",
            "| --- | --- | --- |",
        ]
        for e in entries:
            name = Path(e["path"]).name
            hints = (
                ", ".join(e.get("static_hints", [])) or "未检出上述关键字；仍需读源码"
            )
            script_lines.append(
                f"| [{name}]({name}) | {escape(e['summary'])} | {hints} |"
            )
        script_lines.append("")
    return {
        "catalog/repository_index.json": json.dumps(index, ensure_ascii=False, indent=2)
        + "\n",
        "docs/REPOSITORY_FILE_INDEX.md": "\n".join(all_lines),
        "scripts/README.md": "\n".join(script_lines),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    index = build_index(ROOT)
    stale = []
    for relative, content in documents(index).items():
        path = ROOT / relative
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(relative)
    print(
        json.dumps(
            {"files": len(index["entries"]), "counts": index["counts"], "stale": stale},
            ensure_ascii=False,
        )
    )
    return int(bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
