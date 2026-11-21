"""Check and resume the MMD learning queue offline; never run experiments or fetch URLs."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "catalog/learning_queue.json"
STAGES = ("hypothesis", "still_passed", "motion_passed", "reopen_passed", "integrated")
REQUIRED = {
    "still_passed": {"still"},
    "motion_passed": {"still", "motion"},
    "reopen_passed": {"still", "motion", "reopen"},
    "integrated": {"still", "motion", "reopen", "integration"},
}
STATIC_REQUIRED = {
    "still_passed": {"still"},
    "reopen_passed": {"still", "reopen"},
    "integrated": {"still", "reopen", "integration"},
}
SHA = re.compile(r"[0-9a-f]{64}\Z")
PIN = re.compile(r"(?:git:[0-9a-f]{40}|sha256:[0-9a-f]{64})\Z")


def canonical_url(value):
    """Ignore tracking/section anchors, retain semantic queries and version paths."""
    parts = urlsplit(value)
    if parts.scheme not in {"https", "http"} or not parts.hostname:
        raise ValueError("Source must be a public HTTP(S) URL")
    if parts.username or parts.password:
        raise ValueError("Source URL must not contain credentials")
    host = parts.hostname.lower()
    port = parts.port
    if port and (parts.scheme, port) not in {("https", 443), ("http", 80)}:
        host += f":{port}"
    path = parts.path or "/"
    # A raw and a GitHub blob URL are the same source at the same revision.
    if host == "raw.githubusercontent.com":
        bits = path.strip("/").split("/", 3)
        if len(bits) == 4:
            host = "github.com"
            path = f"/{bits[0]}/{bits[1]}/blob/{bits[2]}/{bits[3]}"
    query = sorted(
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"spm_id_from", "fbclid", "gclid"}
    )
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(query), ""))


def resolve_file(value, root):
    path = Path(value)
    return path if path.is_absolute() else root / path


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate(data, root=ROOT, check_artifacts=False):
    errors = []
    sources, cards = data.get("sources", []), data.get("cards", [])
    if data.get("schema_version") != 1 or not sources or not cards:
        return ["Expected schema_version 1 with nonempty sources and cards"]
    source_ids, card_ids, seen = set(), set(), set()
    for source in sources:
        sid = source.get("id")
        if not sid or sid in source_ids:
            errors.append(f"Duplicate or empty source id: {sid}")
        source_ids.add(sid)
        try:
            key = (canonical_url(source["url"]), source["revision"])
            if key in seen:
                errors.append(f"Duplicate canonical source/revision: {sid}")
            seen.add(key)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"Invalid source {sid}: {exc}")
        for name in ("title", "author", "kind", "version", "refresh_trigger", "limits"):
            if not source.get(name):
                errors.append(f"{sid}: missing {name}")
        reading = source.get("reading", {})
        if reading.get("level") not in {"sections", "index_excerpt", "discovered"}:
            errors.append(f"{sid}: invalid reading level")
        if not reading.get("scope"):
            errors.append(f"{sid}: missing actual reading scope")
        ledger = reading.get("ledger")
        if not ledger or not resolve_file(ledger, root).is_file():
            errors.append(f"{sid}: missing provenance ledger")
        if source.get("revision_locked") and not PIN.fullmatch(
            source.get("revision") or ""
        ):
            errors.append(
                f"{sid}: locked revision needs git:<commit> or sha256:<content hash>"
            )
    for card in cards:
        cid = card.get("id")
        if not cid or cid in card_ids:
            errors.append(f"Duplicate or empty card id: {cid}")
        card_ids.add(cid)
        status = card.get("status")
        if status not in (*STAGES, "rejected", "superseded"):
            errors.append(f"{cid}: invalid status {status}")
        validation_scope = card.get("validation_scope", "motion")
        if validation_scope not in {"stills", "motion"}:
            errors.append(f"{cid}: validation_scope must be stills or motion")
        if validation_scope == "stills" and status == "motion_passed":
            errors.append(f"{cid}: static scope cannot claim motion_passed")
        if type(card.get("priority")) is not int or card["priority"] not in range(3):
            errors.append(f"{cid}: priority must be 0, 1 or 2")
        for name in (
            "title",
            "topic",
            "gap",
            "hypothesis",
            "novelty",
            "next_action",
            "bypass",
            "fixed_variables",
            "checks",
            "reject_if",
            "limits",
        ):
            if not card.get(name):
                errors.append(f"{cid}: missing {name}")
        refs = card.get("source_ids", [])
        if not refs or len(refs) != len(set(refs)) or set(refs) - source_ids:
            errors.append(f"{cid}: invalid source references")
        checks = card.get("checks", {})
        check_keys = ("still", "reopen", "integration") if validation_scope == "stills" else ("still", "motion", "reopen", "integration")
        if not all(checks.get(key) for key in check_keys):
            errors.append(f"{cid}: missing test/acceptance scope")
        baseline = card.get("baseline", {})
        if not baseline.get("path"):
            errors.append(f"{cid}: missing baseline path")
        needed = (STATIC_REQUIRED if validation_scope == "stills" else REQUIRED).get(
            status, set()
        )
        if needed and not SHA.fullmatch(baseline.get("sha256") or ""):
            errors.append(f"{cid}: passed stage requires frozen baseline SHA256")
        if needed and baseline.get("kind") not in {
            "production_blend",
            "simulation_blend",
        }:
            errors.append(
                f"{cid}: passed stage requires an experiment blend, not a selection manifest"
            )
        if needed and any(
            s.get("reading", {}).get("level") == "discovered"
            for s in sources
            if s.get("id") in refs
        ):
            errors.append(f"{cid}: unread sources cannot support a passed experiment")
        evidence = card.get("evidence", [])
        types = {item.get("kind") for item in evidence}
        if needed - types:
            errors.append(f"{cid}: missing evidence kinds {sorted(needed - types)}")
        for item in evidence:
            if not item.get("path") or not SHA.fullmatch(item.get("sha256") or ""):
                errors.append(f"{cid}: evidence requires path and SHA256")
            elif not resolve_file(item["path"], root).is_file():
                errors.append(f"{cid}: evidence file missing: {item['path']}")
            else:
                path = resolve_file(item["path"], root)
                if check_artifacts and digest(path) != item["sha256"]:
                    errors.append(f"{cid}: evidence hash mismatch: {item['path']}")
                try:
                    report = json.loads(path.read_text(encoding="utf-8-sig"))
                    if (
                        report.get("card_id") != cid
                        or report.get("baseline_sha256") != baseline.get("sha256")
                        or report.get("stage") != item.get("kind")
                        or report.get("result") != "passed"
                        or not report.get("scope")
                        or not report.get("artifacts")
                    ):
                        errors.append(
                            f"{cid}: evidence is not a passing report for this card/baseline/stage"
                        )
                    for artifact in report.get("artifacts", []):
                        artifact_path = resolve_file(artifact.get("path", ""), root)
                        if not artifact_path.is_file() or not SHA.fullmatch(
                            artifact.get("sha256") or ""
                        ):
                            errors.append(f"{cid}: missing/invalid report artifact")
                        elif (
                            check_artifacts
                            and digest(artifact_path) != artifact["sha256"]
                        ):
                            errors.append(f"{cid}: report artifact hash mismatch")
                except (ValueError, UnicodeError, AttributeError, TypeError):
                    errors.append(f"{cid}: evidence must be a structured stage report")
        if check_artifacts and needed and baseline.get("path"):
            path = resolve_file(baseline["path"], root)
            if not path.is_file() or digest(path) != baseline.get("sha256"):
                errors.append(f"{cid}: baseline missing or hash mismatch")
        # Copied/adapted implementation needs a pinned, licensed source;
        # borrowing a documented principle does not claim code compatibility.
        for sid in card.get("implementation_sources", []):
            source = next((s for s in sources if s.get("id") == sid), {})
            if sid not in refs:
                errors.append(f"{cid}: implementation source must also be referenced")
            if needed and (
                not source.get("revision_locked") or not source.get("license_verified")
            ):
                errors.append(
                    f"{cid}: implementation source {sid} needs revision/license check"
                )
        if status in {"rejected", "superseded"} and not card.get("closure_reason"):
            errors.append(f"{cid}: closed card needs a reason")
    by_id = {c.get("id"): c for c in cards}
    for card in cards:
        dependencies = card.get("depends_on", [])
        if len(dependencies) != len(set(dependencies)) or set(dependencies) - card_ids:
            errors.append(f"{card['id']}: unknown/duplicate dependency")
    visiting, done = set(), set()

    def visit(cid):
        if cid in visiting:
            errors.append(f"Cyclic learning dependency: {cid}")
            return
        if cid in done:
            return
        visiting.add(cid)
        for dep in by_id[cid].get("depends_on", []):
            if dep in by_id:
                visit(dep)
        visiting.remove(cid)
        done.add(cid)

    for cid in by_id:
        visit(cid)
    return errors


def plan(data, limit=3, validation_scope=None):
    """Deterministic small queue. Not an execution permit or background worker."""
    by_id = {c["id"]: c for c in data["cards"]}
    active = [
        c
        for c in data["cards"]
        if c["status"] not in {"integrated", "rejected", "superseded"}
    ]
    result = []
    for card in sorted(active, key=lambda c: (c["priority"], c["id"])):
        waiting = [
            dep
            for dep in card.get("depends_on", [])
            if by_id[dep]["status"] != "integrated"
        ]
        if waiting:
            continue
        next_action = card["next_action"]
        if card["status"] != "hypothesis":
            stage = {
                "still_passed": "motion",
                "motion_passed": "reopen",
                "reopen_passed": "integration",
            }[card["status"]]
            scope = validation_scope or card.get("validation_scope", "motion")
            if scope == "stills" and stage == "motion":
                stage = "reopen"
            next_action = f"{stage}: {card['checks'][stage]}"
        result.append(
            {
                "id": card["id"],
                "title": card["title"],
                "priority": card["priority"],
                "status": card["status"],
                "next_action": next_action,
                "sources": card["source_ids"],
                "baseline_frozen": bool(card["baseline"].get("sha256")),
                "validation_scope": validation_scope or card.get("validation_scope", "motion"),
                "motion_not_implied": (validation_scope or card.get("validation_scope")) == "stills",
            }
        )
        if len(result) >= limit:
            break
    return result


def blocked(data):
    by_id = {c["id"]: c for c in data["cards"]}
    return [
        {
            "id": c["id"],
            "waiting_for": [
                {"id": dep, "status": by_id[dep]["status"]}
                for dep in c.get("depends_on", [])
                if by_id[dep]["status"] != "integrated"
            ],
        }
        for c in data["cards"]
        if c["status"] not in {"integrated", "rejected", "superseded"}
        and any(by_id[dep]["status"] != "integrated" for dep in c.get("depends_on", []))
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "plan", "lookup"])
    parser.add_argument("--registry", type=Path, default=DEFAULT)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument(
        "--url", help="Find prior reading before downloading a source again"
    )
    parser.add_argument("--check-artifacts", action="store_true")
    parser.add_argument(
        "--scope", choices=["stills", "motion"],
        help="Planning scope only; does not rewrite historical evidence or grant video permission",
    )
    parser.add_argument(
        "--output", type=Path, help="New JSON report; existing files are never replaced"
    )
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 10:
        parser.error("--limit must be between 1 and 10")
    data = json.loads(args.registry.read_text(encoding="utf-8-sig"))
    errors = validate(data, check_artifacts=args.check_artifacts)
    report = {
        "passed": not errors,
        "errors": errors,
        "registry_sha256": digest(args.registry),
        "counts": {"sources": len(data["sources"]), "cards": len(data["cards"])},
        "limits": "Offline structure/provenance check only; no fetching, experiments, rendering or art approval",
    }
    if not errors and args.command == "plan":
        report["next"] = plan(data, args.limit, args.scope)
        report["blocked"] = blocked(data)
    if not errors and args.command == "lookup":
        if not args.url:
            parser.error("lookup requires --url")
        url = canonical_url(args.url)
        report["matches"] = [
            {"id": s["id"], "version": s["version"], "reading": s["reading"]}
            for s in data["sources"]
            if canonical_url(s["url"]) == url
        ]
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
