"""Read task knowledge routes without importing production code or starting tools."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "catalog/task_routes.json"
TOOL_MODES = {
    "inspect_runtime_bootstrap",
    "historical_inspect_only",
    "isolated_research_only",
    "inspect_input_and_side_effects",
}


def references(data):
    yield from data["common_read"]
    yield data["state_contract"]["runtime"]
    for route in data["routes"]:
        yield from route["read"]
        yield from route["parameters"]
        yield from (tool["path"] for tool in route["tools"])


def validate(data, root=ROOT):
    errors = []
    names = set()
    try:
        if data["schema_version"] != 1 or not data["routes"]:
            errors.append("Unsupported or empty routing registry")
        for route in data["routes"]:
            for name in [route["id"], *route["aliases"]]:
                key = name.casefold()
                if not key or key in names:
                    errors.append(f"Duplicate/empty route name: {name}")
                names.add(key)
            for field in ("label", "read", "decisions", "evidence_required", "limits"):
                if not route[field]:
                    errors.append(f"Empty {route['id']}.{field}")
            for tool in route["tools"]:
                if tool["mode"] not in TOOL_MODES or not tool["scope"]:
                    errors.append(f"Unclassified tool in {route['id']}")
        for name in references(data):
            path = (root / name).resolve()
            if Path(name).is_absolute() or not path.is_relative_to(root.resolve()):
                errors.append(f"Reference escapes repository: {name}")
            elif not path.is_file():
                errors.append(f"Missing route reference: {name}")
    except (KeyError, TypeError, AttributeError) as exc:
        errors.append(f"Malformed route registry: {exc}")
    return errors


def select(data, query):
    query = query.strip().casefold()
    return next(
        (
            route
            for route in data["routes"]
            if query
            in {route["id"].casefold(), *(a.casefold() for a in route["aliases"])}
        ),
        None,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--task", help="Exact route id or documented alias; use --list")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    data = json.loads(DEFAULT.read_text(encoding="utf-8-sig"))
    errors = validate(data)
    if errors:
        print(json.dumps({"passed": False, "errors": errors}, ensure_ascii=False))
        return 1
    if args.check:
        result = {
            "passed": True,
            "routes": len(data["routes"]),
            "limits": data["purpose"],
        }
    elif args.list:
        result = [
            {key: route[key] for key in ("id", "label", "aliases")}
            for route in data["routes"]
        ]
    else:
        route = select(data, args.task)
        if route is None:
            parser.error("Unknown task; use --list for exact ids and aliases")
        result = {
            "common_read": data["common_read"],
            "state_contract": data["state_contract"],
            "route": route,
            "limits": data["purpose"],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
