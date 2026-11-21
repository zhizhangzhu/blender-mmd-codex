"""Read-only entry to studio knowledge, current scope, reference studies and learning.

Does not open Blender, render, dispatch models, train weights or modify project state.
"""

import argparse
import json
import re
from pathlib import Path

from . import knowledge_route, learning_queue, reference_study, studio_registry, studio_tasks, studio_scene_contract, studio_lessons

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def inspect_state(state, root=ROOT, check_artifacts=False):
    errors = []
    active = state.get("active_iteration", {})
    if not isinstance(active, dict) or not active.get("project"):
        return ["Missing active iteration/project"]
    if active.get("user_art_approval") and active.get("art_status") != "approved":
        errors.append("Current user approval contradicts art status")
    if not re.fullmatch(r"[0-9a-f]{64}", active.get("project_sha256", "")):
        errors.append("Current project needs a frozen SHA256")
    if check_artifacts:
        projects = [(active.get("project"), active.get("project_sha256"))]
        migration = state.get("blender53_migration_request", {})
        if migration.get("goo_frozen"):
            projects.append((migration.get("source_project"), migration.get("source_sha256")))
        for name, sha in set(projects):
            if not name:
                errors.append("Missing frozen source path")
                continue
            path = Path(name)
            if not path.is_file() or studio_registry.digest(path) != sha:
                errors.append(f"Current/frozen project missing or hash mismatch: {name}")
        for key in ("still", "verification", "acceptance"):
            if active.get(key) and not Path(active[key]).is_file():
                errors.append(f"Missing current {key}: {active[key]}")
    return errors


def audit(root=ROOT, check_artifacts=False):
    root = Path(root)
    data = read(root / "catalog/studio.json")
    state = read(root / "catalog/current_state.json")
    policy = read(root / "catalog/model_policy.json")
    errors = studio_registry.validate(data, root, check_artifacts)
    errors += studio_tasks.validate_policy(policy)
    errors += inspect_state(state, root, check_artifacts)
    try:
        lesson_result = studio_lessons.retrieve(data, root=root)
        errors.extend("Lesson " + item["id"] + ": " + item["error"] for item in lesson_result["skipped"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append("Lesson registry: " + str(exc))
    studies = sorted((root / "catalog/reference_studies").glob("*.json"))
    study_ids = set()
    for path in studies:
        study = read(path)
        errors.extend(f"{path.name}: {e}" for e in reference_study.validate(study, root, check_artifacts))
        if study.get("id") in study_ids:
            errors.append("Duplicate reference study id")
        study_ids.add(study.get("id"))
    benches = read(root / "catalog/scene_benches.json")
    bench_ids = set()
    for bench in benches["entries"]:
        name = bench["id"].casefold()
        profile = (root / bench["profile"]).resolve()
        if name in bench_ids or not profile.is_relative_to(root.resolve()) or not profile.is_file():
            errors.append("Duplicate/invalid scene bench profile: " + bench["id"])
            continue
        bench_ids.add(name)
        errors.extend(f"{bench['id']}: {e}" for e in studio_scene_contract.validate(read(profile), root, check_artifacts))
    return {"passed": not errors, "errors": errors,
            "counts": {"capabilities": len(data["capabilities"]), "preferences": len(data["preferences"]),
                       "curriculum": len(data["curriculum"]), "reference_studies": len(studies), "scene_benches": len(benches["entries"])},
            "limits": "Structure, references and optional hashes only; no new visual capability, render or art approval certified"}


def context(task=None, query="", limit=3, root=ROOT):
    root = Path(root)
    routes = read(root / "catalog/task_routes.json")
    route = knowledge_route.select(routes, task) if task else None
    if task and route is None:
        raise ValueError("Unknown task route; use knowledge_route --list")
    data = read(root / "catalog/studio.json")
    result = studio_registry.context(data, read(root / "catalog/current_state.json"), query,
                                     route["id"] if route else None, limit)
    lesson_result = studio_lessons.retrieve(data, query=query, route=route["id"] if route else None, root=root)
    result["lessons"] = lesson_result["lessons"][:limit]
    result["lesson_errors"] = lesson_result["skipped"]
    result["route"] = route
    result["supervision"] = read(root / "catalog/model_policy.json")
    selected = []
    for path in sorted((root / "catalog/reference_studies").glob("*.json")):
        study = read(path)
        haystack = json.dumps(study, ensure_ascii=False).casefold()
        if route and route["id"] == "reference" or query and any(t in haystack for t in query.casefold().split()):
            selected.append({"path": path.relative_to(root).as_posix(), "brief": reference_study.brief(study)})
    result["reference_studies"] = selected[:limit]
    result["scene_benches"] = read(root / "catalog/scene_benches.json")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "status", "context", "learn", "benches", "lessons"])
    parser.add_argument("--task")
    parser.add_argument("--query", default="")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--check-artifacts", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 10:
        parser.error("--limit must be 1..10")
    try:
        result = audit(check_artifacts=args.check_artifacts)
        if not result["passed"] or args.command == "check":
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(not result["passed"])
        state = read(ROOT / "catalog/current_state.json")
        if args.command == "context":
            result = context(args.task, args.query, args.limit)
        elif args.command == "lessons":
            route = knowledge_route.select(read(ROOT / "catalog/task_routes.json"), args.task) if args.task else None
            if args.task and route is None:
                raise ValueError("Unknown task route; use knowledge_route --list")
            result = studio_lessons.retrieve(read(ROOT / "catalog/studio.json"), args.query,
                                            route["id"] if route else None, ROOT)
        elif args.command == "benches":
            result = read(ROOT / "catalog/scene_benches.json")
        elif args.command == "learn":
            scope = "stills" if state.get("render_delivery_policy", {}).get("default") == "stills_only" else None
            data = read(ROOT / "catalog/learning_queue.json")
            errors = learning_queue.validate(data, ROOT)
            if errors:
                raise ValueError("; ".join(errors))
            result = {"project_scope": scope, "next": learning_queue.plan(data, args.limit, scope),
                      "curriculum": read(ROOT / "catalog/studio.json")["curriculum"],
                      "requires_current_gap_check": True,
                      "capability_next_exercises": [{"id": c["id"], "exercise": c["next_exercise"]} for c in read(ROOT / "catalog/studio.json")["capabilities"]],
                      "limits": "Learning plan only; no permission to generate video or auto-promote capability"}
        else:
            result["current"] = {key: state.get(key) for key in ("as_of", "current_task", "active_iteration", "blender53_migration_request", "render_delivery_policy")}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({"passed": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
