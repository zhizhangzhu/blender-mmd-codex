"""Build the offline MMD Atlas from curated metadata and real local renders.

Run with the temporary gallery tool directory on PYTHONPATH. Runtime output
requires no server, account, network, framework, or package installation.
"""

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote

import bleach
import markdown

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FFMPEG = Path(
    "D:/codex/temp/blender-mmd-video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def document_html(text, output=None):
    rendered = markdown.markdown(
        text, extensions=["tables", "fenced_code", "sane_lists"]
    )
    rendered = bleach.clean(
        rendered,
        tags={
            "h1",
            "h2",
            "h3",
            "h4",
            "p",
            "a",
            "strong",
            "em",
            "code",
            "pre",
            "ul",
            "ol",
            "li",
            "table",
            "thead",
            "tbody",
            "tr",
            "td",
            "th",
            "blockquote",
            "hr",
            "br",
            "del",
        },
        attributes={"a": ["href", "title"], "code": ["class"]},
        protocols={"https", "http"},
        strip=True,
    )

    def link(match):
        target = html.unescape(match.group(1))
        if target.startswith(("https://", "http://")):
            return f'href="{html.escape(target, quote=True)}" target="_blank" rel="noopener noreferrer"'
        filename = Path(unquote(target.split("#")[0])).name
        if filename.endswith(".md") and (ROOT / "docs" / filename).is_file():
            return f'href="#learn/{filename}"'
        local = (ROOT / "docs" / unquote(target.split("#")[0])).resolve()
        if (
            local.is_relative_to(ROOT)
            and local.suffix in {".json", ".md"}
            and local.is_file()
        ):
            relative = local.relative_to(ROOT).as_posix()
            if output is not None:
                destination = output / "downloads" / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(local, destination)
            return f'href="downloads/{html.escape(relative, quote=True)}" download'
        # File paths are already available through explicit copy controls in entries.
        return 'aria-disabled="true"'

    return re.sub(r'href="([^"]*)"', link, rendered)


def apply_current_state(catalog, state):
    """Keep current user feedback authoritative after legacy packagers run."""
    latest = state["latest_review"]
    entry = next(e for e in catalog["entries"] if e["id"] == latest["entry_id"])
    entry["art_review"] = {
        "status": latest["art_status"],
        "as_of": state["as_of"],
        "feedback": latest["user_feedback"],
    }
    if latest["art_status"] == "revision_requested":
        entry["adopted"] = False
        warning = "用户已要求继续提升：" + latest["user_feedback"]
        entry["limits"] = [warning] + [
            s for s in entry["limits"] if not s.startswith("用户已要求继续提升：")
        ]
    catalog["current_state"] = state


def style_entries(catalog):
    result = []
    for item in catalog["style_packages"]:
        entry = dict(item)
        entry.update(
            category="style",
            status="motion",
            duration=4,
            fps=60,
            video=f"D:/codex/output/MMD-Style-Presets-v1/clips/{item['id']}/{item['id']}.mp4",
            docs=["STYLE_PRESETS.md"],
            configs=[f"presets/styles/packages/{item['id']}.json"],
            project=f"D:/codex/output/MMD-Style-Presets-v1/stills/{item['id']}/typography-source.blend",
            look=["渲染／后期模块分开", "独立画幅方案", "动态文字"],
            evidence=["四秒带声技术样片；横 960×540／竖 540×960，60 fps"],
            limits=[
                "根据参考制作的方向，不是原作者参数或同等质量保证",
                "旧单角色研究，不代表最新双人场景已应用该组合",
            ],
            compatibility="阿克西妮娅单角色、已有衣发烘焙；画幅与字幕源分别适配。",
            command=(
                "& .\\scripts\\render_style_suite.ps1 "
                "-OutputRoot 'D:\\codex\\output\\Style-New-Study' "
                "-CacheRoot 'D:\\codex\\temp\\Style-New-Study' "
                f"-PackageIds @('{item['id']}')"
            ),
        )
        package = ROOT / entry["configs"][0]
        params = json.loads(package.read_text(encoding="utf-8-sig"))
        entry["configs"] += [
            str((package.parent / params[key]).resolve().relative_to(ROOT)).replace(
                "\\", "/"
            )
            for key in ["render", "post", "typography"]
        ]
        result.append(entry)
    return result


def build(args):
    # Image processing is needed only when building media, not when checking
    # Markdown links or preserving current art feedback in registry tools.
    from PIL import Image

    output = args.output_dir.resolve()
    marker = output / ".mmd-atlas-build"
    if output.exists():
        if not args.refresh or not marker.is_file() or marker.read_text() != str(ROOT):
            raise FileExistsError(
                "Use a fresh directory, or --refresh on this project's existing gallery"
            )
    else:
        output.mkdir(parents=True)
    marker.write_text(str(ROOT))
    catalog = json.loads((ROOT / "catalog/library.json").read_text(encoding="utf-8"))
    current_path = ROOT / "catalog/current_state.json"
    if current_path.is_file():
        apply_current_state(
            catalog, json.loads(current_path.read_text(encoding="utf-8-sig"))
        )
    for source in sorted((ROOT / "catalog").glob("*.json")):
        destination = output / "downloads/catalog" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    entries = catalog["entries"][:1] + style_entries(catalog) + catalog["entries"][1:]
    identifiers = [entry["id"] for entry in entries]
    assert len(identifiers) == len(set(identifiers)), "Duplicate entry id"
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    provenance = []

    def image_asset(source, key):
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        target = assets / f"{key}.webp"
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
            image.save(target, quality=90, method=6)
            size = list(image.size)
        provenance.append(
            {
                "asset": str(target.relative_to(output)),
                "source": str(source),
                "source_sha256": digest(source),
            }
        )
        return {"src": f"assets/{target.name}", "width": size[0], "height": size[1]}

    for entry in entries:
        if entry.get("diagnostic_video"):
            diagnostic_source = Path(entry["diagnostic_video"])
            diagnostic_target = assets / f"{entry['id']}-diagnostic.mp4"
            shutil.copyfile(diagnostic_source, diagnostic_target)
            provenance.append(
                {
                    "asset": str(diagnostic_target.relative_to(output)),
                    "source": str(diagnostic_source),
                    "source_sha256": digest(diagnostic_source),
                }
            )
            entry["diagnostic_video"] = f"assets/{diagnostic_target.name}"
        if entry.get("video"):
            source = Path(entry["video"])
            if not source.is_file():
                raise FileNotFoundError(source)
            target = assets / f"{entry['id']}.mp4"
            if not target.is_file() or digest(target) != digest(source):
                shutil.copyfile(source, target)
            provenance.append(
                {
                    "asset": str(target.relative_to(output)),
                    "source": str(source),
                    "source_sha256": digest(source),
                }
            )
            entry["video"] = f"assets/{target.name}"
            if not entry.get("image"):
                poster = args.temp_dir / f"{entry['id']}.png"
                poster.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    [
                        str(args.ffmpeg),
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-ss",
                        "1.35",
                        "-i",
                        str(source),
                        "-frames:v",
                        "1",
                        str(poster),
                    ],
                    check=True,
                )
                entry["image"] = str(poster)
        entry["image"] = image_asset(entry["image"], entry["id"])
        entry["parameters"] = []
        for relative in entry["configs"]:
            source = ROOT / relative
            data = json.loads(source.read_text(encoding="utf-8-sig"))
            entry["parameters"].append(
                {"path": relative, "data": data, "download": f"downloads/{relative}"}
            )
        for doc in entry["docs"]:
            assert (ROOT / "docs" / doc).is_file(), doc
    for pair in catalog["comparisons"]:
        pair["before"] = image_asset(pair["before"], f"compare-{pair['id']}-before")
        pair["after"] = image_asset(pair["after"], f"compare-{pair['id']}-after")
        assert (pair["before"]["width"], pair["before"]["height"]) == (
            pair["after"]["width"],
            pair["after"]["height"],
        ), "Comparison needs matching image geometry"
    docs = {}
    for path in sorted((ROOT / "docs").glob("*.md")):
        text = path.read_text(encoding="utf-8-sig")
        title = next(
            (line.lstrip("# ") for line in text.splitlines() if line.startswith("# ")),
            path.stem,
        )
        docs[path.name] = {
            "title": title,
            "html": document_html(text, output),
            "text": text,
            "source": f"downloads/docs/{path.name}",
        }
        target = output / "downloads/docs" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    assigned = [doc for group in catalog["knowledge_groups"] for doc in group["docs"]]
    assert len(assigned) == len(set(assigned)), "Each knowledge document needs one home"
    missing = set(assigned) - set(docs)
    assert not missing, missing
    extra = sorted(set(docs) - set(assigned))
    if extra:
        catalog["knowledge_groups"].append(
            {
                "id": "index",
                "title": "目录与维护",
                "description": "全局入口、知识编排与版本约定。",
                "docs": extra,
            }
        )
    components = []
    for source in sorted((ROOT / "presets").rglob("*.json")):
        relative = source.relative_to(ROOT).as_posix()
        value = json.loads(source.read_text(encoding="utf-8-sig"))
        target = output / "downloads" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        components.append(
            {
                "path": relative,
                "id": value.get("id", source.stem),
                "data": value,
                "download": f"downloads/{relative}",
            }
        )
    catalog.update(entries=entries, documents=docs, components=components)
    catalog.pop("style_packages")
    data = (
        json.dumps(catalog, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    (output / "data.js").write_text(
        "window.MMD_LIBRARY=" + data + ";\n", encoding="utf-8"
    )
    for name in ["index.html", "styles.css", "app.js"]:
        shutil.copyfile(ROOT / "site" / name, output / name)
    shutil.copyfile(ROOT / "site/DESIGN.md", output / "downloads/DESIGN.md")
    (output / "打开预设库.cmd").write_bytes(
        b'@echo off\r\nstart "" "%~dp0index.html"\r\n'
    )
    (output / "README.txt").write_text(
        "猪猪的帧间 MMD 预设库\n\n双击 index.html 或 打开预设库.cmd 即可使用，无需联网或安装。\n"
        "预览、视频、文档与 JSON 已随站点打包；整个目录可移动。\n工程文件体积较大，未复制；详情可复制本机原工程路径。\n"
        "参考方向不代表作者原始预设。静帧实验和研究项保留各自边界，双人全曲尚未完成。\n"
        "收藏保存在当前浏览器；可导出／导入 JSON。复制按钮失败时会展示可手动复制的文本。\n"
        "网站仅用于本地查看已提供素材；原素材授权仍适用。源码和新增项维护见仓库 docs/KNOWLEDGE_INDEX.md。\n",
        encoding="utf-8",
    )
    report = {
        "schema_version": 1,
        "entries": len(entries),
        "documents": len(docs),
        "components": len(components),
        "comparisons": len(catalog["comparisons"]),
        "assets": provenance,
        "catalog_sha256": digest(ROOT / "catalog/library.json"),
        "current_state_sha256": digest(ROOT / "catalog/current_state.json")
        if current_path.is_file()
        else None,
        "pipeline_sha256": digest(ROOT / "catalog/production_pipeline.json"),
        "bytes": sum(
            path.stat().st_size for path in output.rglob("*") if path.is_file()
        ),
        "source_root": str(ROOT),
        "runtime": "offline file://; no server or runtime dependencies",
    }
    (output / "build-manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "assets"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--temp-dir", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument("--refresh", action="store_true")
    build(parser.parse_args())
