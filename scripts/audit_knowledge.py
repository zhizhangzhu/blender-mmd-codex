"""Validate current production facts, knowledge links and offline packaging.

Read-only except the requested JSON report. Does not render, simulate or certify
visual quality. Optional artifact checks are local workstation checks.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

if __package__:
    from .knowledge_route import validate as validate_task_routes
    from .learning_queue import validate as validate_learning_queue
    from .mmd_studio import audit as audit_studio
else:
    from knowledge_route import validate as validate_task_routes
    from learning_queue import validate as validate_learning_queue
    # Script-path use: the package import keeps the studio's relative imports valid.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.mmd_studio import audit as audit_studio

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def local_links(path):
    text = re.sub(r"```[\s\S]*?```", "", path.read_text(encoding="utf-8-sig"))
    for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
        target = match.group(1).strip().strip("<>")
        if not target or target.startswith("#") or urlsplit(target).scheme:
            continue
        yield (path.parent / unquote(target.split("#")[0])).resolve()


def audit(check_artifacts=False, site=None):
    errors, checks = [], []
    state = read(ROOT / "catalog/current_state.json")
    pipeline = read(ROOT / "catalog/production_pipeline.json")
    library = read(ROOT / "catalog/library.json")
    gates = pipeline["gates"]
    assert gates and len({g["id"] for g in gates}) == len(gates)
    assert all(g["required_evidence"] and g["exit"] for g in gates)
    ids = [e["id"] for e in library["entries"] + library["style_packages"]]
    assert len(ids) == len(set(ids))
    latest = state["latest_review"]
    assert latest["entry_id"] in ids
    assert latest["art_status"] in {"revision_requested", "pending", "approved"}
    assert not (
        latest["art_status"] == "revision_requested" and latest["user_art_approval"]
    )
    scope = latest["scope"]
    assert (scope["frames"][1] - scope["frames"][0] + 1) / scope["fps"] == scope[
        "seconds"
    ]
    checks.append(
        "current facts, distinct art/technical status and quality gate structure"
    )
    documents = list((ROOT / "docs").glob("*.md"))
    for path in [
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        *documents,
        *(ROOT / "skills").rglob("SKILL.md"),
    ]:
        for target in local_links(path):
            if not target.is_file():
                errors.append(
                    f"Broken local link in {path.relative_to(ROOT)}: {target}"
                )
    assigned = [d for g in library["knowledge_groups"] for d in g["docs"]]
    if len(assigned) != len(set(assigned)):
        errors.append("Duplicate document home")
    for name in assigned:
        if not (ROOT / "docs" / name).is_file():
            errors.append(f"Missing knowledge document: {name}")
    checks.append(
        "active Markdown links and unique knowledge groups; dated snapshots excluded"
    )
    ledgers = list((ROOT / "docs/research").glob("*.json"))
    for path in [
        *(ROOT / "catalog").glob("*.json"),
        *(ROOT / "presets").rglob("*.json"),
        *ledgers,
    ]:
        read(path)
    checks.append("catalog, preset and research JSON parse")
    errors.extend(validate_task_routes(read(ROOT / "catalog/task_routes.json"), ROOT))
    checks.append(
        "task routes, unique aliases, scoped tool entries and repository references"
    )
    queue = read(ROOT / "catalog/learning_queue.json")
    errors.extend(validate_learning_queue(queue, ROOT, check_artifacts))
    checks.append(
        "learning source deduplication, provenance, dependencies and evidence-stage contracts"
    )
    studio = audit_studio(ROOT, check_artifacts)
    errors.extend(studio["errors"])
    checks.append("current still/frozen source, studio evidence, scoped preferences, model policy and reference studies")
    if check_artifacts:
        movie = Path(latest["video"])
        if (
            not movie.is_file()
            or hashlib.sha256(movie.read_bytes()).hexdigest() != latest["sha256"]
        ):
            errors.append("Latest review video missing or hash mismatch")
        for path in (
            latest["project"],
            latest["delivery_report"],
            state["project_contract"]["bgm"],
        ):
            if not Path(path).is_file():
                errors.append(f"Missing current artifact: {path}")
        for entry in library["entries"]:
            for name in ("image", "video", "diagnostic_video", "project"):
                if entry.get(name) and not Path(entry[name]).is_file():
                    errors.append(f"Missing {entry['id']} {name}: {entry[name]}")
            for name in entry["configs"]:
                if not (ROOT / name).is_file():
                    errors.append(f"Missing config {name}")
        checks.append(
            "current source video hash, project/BGM/reports and registered artifact existence; no re-render or re-decode"
        )
    if site:
        manifest = read(site / "build-manifest.json")
        if (
            manifest["catalog_sha256"]
            != hashlib.sha256((ROOT / "catalog/library.json").read_bytes()).hexdigest()
        ):
            errors.append("Offline catalog is stale")
        data_text = (site / "data.js").read_text(encoding="utf-8")
        db = json.loads(data_text.removeprefix("window.MMD_LIBRARY=").rstrip(";\n"))
        if db.get("current_state") != state:
            errors.append("Offline production facts are stale")
        selected = next(e for e in db["entries"] if e["id"] == latest["entry_id"])
        if selected.get("art_review", {}).get("status") != latest["art_status"]:
            errors.append("Offline art feedback lost")
        for doc in db["documents"].values():
            for target in re.findall(r'href="([^"]+)"', doc["html"]):
                if (
                    target.startswith("#learn/")
                    and unquote(target[7:]) not in db["documents"]
                ):
                    errors.append(f"Broken reader route {target}")
                if (
                    target.startswith("downloads/")
                    and not (site / unquote(target)).is_file()
                ):
                    errors.append(f"Missing offline download {target}")
        checks.append(
            "offline facts/feedback, reader routes and local downloads; static checks only"
        )
    return {
        "passed": not errors,
        "checks": checks,
        "errors": errors,
        "counts": {
            "documents": len(documents),
            "presets": len(list((ROOT / "presets").rglob("*.json"))),
            "research_ledgers": len(ledgers),
            "entries_with_style_packages": len(ids),
            "learning_sources": len(queue["sources"]),
            "learning_cards": len(queue["cards"]),
            "studio": studio["counts"],
        },
        "limits": "No new renderer/plugin/physics experiment or browser interaction; this report cannot certify visual quality",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-artifacts", action="store_true")
    parser.add_argument("--site", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.check_artifacts, args.site)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
