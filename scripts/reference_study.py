"""Prepare local reference evidence, separate observations from hypotheses, and build a design brief.

No image understanding is claimed by this CLI. Extracted frames remain unseen until
a reviewing agent records what it actually inspected. No network or Blender calls.
"""

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = {"composition", "value", "color", "material", "line", "optics", "performance", "camera", "timing"}
SHA = re.compile(r"[0-9a-f]{64}\Z")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def local_path(value, root=ROOT):
    path = Path(value)
    return path if path.is_absolute() else root / path


def scaffold(source, kind, title, study_id):
    source = Path(source).resolve(strict=True)
    if not source.is_file() or kind not in {"image", "video"}:
        raise ValueError("A local image/video file and explicit kind are required")
    return {
        "schema_version": 1, "id": study_id, "title": title, "kind": kind,
        "status": "draft", "source": {"path": str(source), "sha256": digest(source)},
        "intent": {"borrow": [], "preserve": []},
        "observations": [], "hypotheses": [], "targets": [], "shots": [],
        "implementation": {"status": "unstarted", "recipe_refs": [], "evidence": []},
        "review": {"art_status": "pending", "user_feedback_provenance": None},
        "media_review": {"audio": {"status": "not_reviewed", "scope": ""},
                         "transcript": {"status": "not_reviewed", "scope": ""}},
        "limits": ["Extraction is not visual inspection", "A single image does not uniquely identify author settings"],
    }


def validate(data, root=ROOT, check_artifacts=False):
    errors = []
    if not isinstance(data, dict):
        return ["Study must be an object"]
    if data.get("schema_version") != 1 or data.get("kind") not in {"image", "video"}:
        errors.append("Unsupported study schema/kind")
    for key in ("id", "title"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"Missing {key}")
    if data.get("status") not in {"draft", "analyzed"}:
        errors.append("Invalid study status")
    source = data.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("path"), str) or not SHA.fullmatch(str(source.get("sha256", ""))):
        errors.append("Source requires local path and SHA256")
    elif check_artifacts:
        path = local_path(source["path"], root)
        if not path.is_file() or digest(path) != source["sha256"]:
            errors.append("Source missing or hash mismatch")
    intent = data.get("intent", {})
    if not isinstance(intent, dict) or any(not isinstance(intent.get(k), list) for k in ("borrow", "preserve")):
        errors.append("Intent requires borrow/preserve lists")
    elif data.get("status") == "analyzed" and not intent["borrow"]:
        errors.append("Analyzed study requires explicit borrowing intent")
    groups = {}
    for group in ("observations", "hypotheses", "targets", "shots"):
        entries = data.get(group)
        if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
            errors.append(f"{group} must be a list of objects")
            groups[group] = []
            continue
        groups[group] = entries
        ids = [item.get("id") for item in entries]
        if any(not isinstance(i, str) or not i for i in ids) or len(set(str(i) for i in ids)) != len(ids):
            errors.append(f"Duplicate/empty {group} id")
    observations = {str(o.get("id")): o for o in groups["observations"]}
    for obs in observations.values():
        if obs.get("dimension") not in DIMENSIONS or not obs.get("description") or not obs.get("locator"):
            errors.append("Observation requires dimension, description and region/time locator")
        if type(obs.get("seen")) is not bool:
            errors.append("Observation seen must explicitly be boolean")
    media_review = data.get("media_review", {})
    for channel in ("audio", "transcript"):
        record = media_review.get(channel) if isinstance(media_review, dict) else None
        if not isinstance(record, dict) or record.get("status") not in {"not_reviewed", "reviewed"} or (record.get("status") == "reviewed" and not record.get("scope")):
            errors.append(f"{channel} review requires status and actual scope")
    for group in ("hypotheses", "targets"):
        for item in groups[group]:
            refs = item.get("observation_ids", [])
            if not isinstance(refs, list) or not refs or any(not isinstance(r, str) or r not in observations for r in refs):
                errors.append(f"{group} requires existing observation references")
            elif data.get("status") == "analyzed" and any(not observations[r].get("seen") for r in refs):
                errors.append("Analyzed conclusions require actually inspected observations")
            required = ("explanation", "test", "prediction") if group == "hypotheses" else ("visual_goal", "controls", "check", "reject_if")
            for key in required:
                if not item.get(key):
                    errors.append(f"{group}: missing {key}")
            if group == "hypotheses":
                if item.get("status") not in {"untested", "supported", "rejected"}:
                    errors.append("Hypothesis needs explicit status")
                if item.get("status") != "untested" and not item.get("evidence_refs"):
                    errors.append("Tested hypothesis needs evidence references")
                evidence_refs = item.get("evidence_refs", [])
                if not isinstance(evidence_refs, list):
                    errors.append("Hypothesis evidence_refs must be a list")
                    evidence_refs = []
                for ref in evidence_refs:
                    if not isinstance(ref, str) or not local_path(ref, root).is_file():
                        errors.append("Missing hypothesis evidence reference")
            elif type(item.get("priority")) is not int or item["priority"] not in range(3):
                errors.append("Target priority must be 0, 1 or 2")
    for shot in groups["shots"]:
        start, end = shot.get("start_seconds"), shot.get("end_seconds")
        if not all(type(t) in (int, float) and math.isfinite(t) for t in (start, end)) or start < 0 or end <= start:
            errors.append("Shot needs a finite increasing nonnegative interval")
            continue
        for field in ("sample_times", "events"):
            if not isinstance(shot.get(field), list):
                errors.append(f"Shot {field} must be a list")
        for time in shot.get("sample_times", []) if isinstance(shot.get("sample_times"), list) else []:
            if type(time) not in (int, float) or not math.isfinite(time) or not start <= time <= end:
                errors.append("Sample time outside shot")
        for event in shot.get("events", []) if isinstance(shot.get("events"), list) else []:
            if not isinstance(event, dict) or type(event.get("time_seconds")) not in (int, float) or not start <= event["time_seconds"] <= end or not event.get("description"):
                errors.append("Invalid shot event")
        review = shot.get("review", {})
        if not isinstance(review, dict) or type(review.get("continuous")) is not bool or (review.get("continuous") and not review.get("scope")):
            errors.append("Shot continuous review requires explicit scope")
    if data.get("kind") == "image" and groups["shots"]:
        errors.append("Image studies cannot claim video shots")
    if data.get("status") == "analyzed" and any(not groups[k] for k in ("observations", "hypotheses", "targets")):
        errors.append("Analyzed study requires observations, hypotheses and executable targets")
    impl = data.get("implementation", {})
    if not isinstance(impl, dict) or impl.get("status") not in {"unstarted", "in_progress", "reconstructed", "transferred"}:
        errors.append("Invalid implementation status")
        impl = {}
    recipe_refs = impl.get("recipe_refs", [])
    if not isinstance(recipe_refs, list):
        errors.append("Recipe references must be a list")
        recipe_refs = []
    for ref in recipe_refs:
        path = local_path(ref, root) if isinstance(ref, str) else None
        if path is None or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            errors.append("Recipe reference must exist inside repository")
    evidence = impl.get("evidence", [])
    if not isinstance(evidence, list):
        errors.append("Implementation evidence must be a list")
        evidence = []
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not SHA.fullmatch(str(item.get("sha256", ""))):
            errors.append("Implementation evidence needs path/hash")
        elif check_artifacts:
            path = local_path(item["path"], root)
            if not path.is_file() or digest(path) != item["sha256"]:
                errors.append("Implementation artifact missing/hash mismatch")
    if impl.get("status") in {"reconstructed", "transferred"} and not evidence:
        errors.append("Reconstruction claim requires actual evidence")
    distinct_evidence = {e["path"] for e in evidence if isinstance(e, dict) and isinstance(e.get("path"), str)}
    if impl.get("status") == "transferred" and (len(distinct_evidence) < 2 or not impl.get("transfer_scope")):
        errors.append("Transfer requires multiple artifacts and declared new conditions")
    review = data.get("review", {})
    if not isinstance(review, dict) or review.get("art_status") not in {"pending", "revision_requested", "approved"}:
        errors.append("Invalid art review")
    elif review.get("art_status") == "approved":
        provenance = review.get("user_feedback_provenance")
        if not isinstance(provenance, str) or not local_path(provenance, root).is_file():
            errors.append("Art approval requires explicit user feedback provenance")
    return errors


def brief(data):
    return {
        "study_id": data["id"], "source": data["source"], "intent": data["intent"],
        "observed": [o for o in data["observations"] if o["seen"]],
        "unverified_observations": [o for o in data["observations"] if not o["seen"]],
        "hypotheses": data["hypotheses"],
        "next_targets": sorted(data["targets"], key=lambda t: (t["priority"], t["id"]))[:3],
        "temporal_limits": [{"shot": s["id"], "review": s["review"]} for s in data["shots"]],
        "media_review": data["media_review"],
        "implementation": data["implementation"], "review": data["review"],
        "limits": "A design brief, not recovered author settings, a dispatched render, or style approval",
    }


def extract(data, output, ffmpeg=None, max_frames=24):
    errors = validate(data, check_artifacts=True)
    if errors:
        raise ValueError("; ".join(errors))
    if not 1 <= max_frames <= 64:
        raise ValueError("max_frames must be 1..64")
    source = local_path(data["source"]["path"])
    if data["kind"] == "video":
        times = sorted({t for s in data["shots"] for t in s["sample_times"]})
        if not times or len(times) > max_frames:
            raise ValueError("Provide bounded shot sample_times within max_frames")
        if ffmpeg is None or not Path(ffmpeg).is_file():
            raise ValueError("Video extraction requires an existing local --ffmpeg executable")
    else:
        times = [None]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"study_id": data["id"], "source": data["source"], "frames": [],
                "limits": "Frames extracted only; none automatically marked visually reviewed"}
    try:
        for n, seconds in enumerate(times):
            suffix = source.suffix.lower() if seconds is None else ".png"
            target = output / f"frame-{n:03d}{suffix}"
            if seconds is None:
                shutil.copyfile(source, target)
            else:
                subprocess.run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
                    "-ss", str(seconds), "-i", str(source), "-frames:v", "1", str(target)],
                    check=True, timeout=90, capture_output=True)
            if not target.is_file() or not target.stat().st_size:
                raise ValueError(f"No decoded frame at {seconds}")
            manifest["frames"].append({"path": str(target.resolve()), "sha256": digest(target),
                                       "seconds": seconds, "seen": False})
        manifest["status"] = "extracted"
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
        (output / "extraction.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
    (output / "extraction.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    cards = "".join(f'<figure><a href="{html.escape(Path(f["path"]).name)}"><img src="{html.escape(Path(f["path"]).name)}"></a><figcaption>{f["seconds"]}s · not reviewed</figcaption></figure>' for f in manifest["frames"])
    (output / "contact.html").write_text('<!doctype html><meta charset="utf-8"><title>Reference samples</title><style>body{background:#202124;color:#eee;font:16px sans-serif}main{display:flex;flex-wrap:wrap}figure{margin:12px;width:320px}img{width:100%}</style><h1>' + html.escape(data["title"]) + '</h1><p>Sampled frames; inspect originals before recording observations.</p><main>' + cards + '</main>', encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "check", "brief", "extract"])
    parser.add_argument("--study", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--kind", choices=["image", "video"])
    parser.add_argument("--title")
    parser.add_argument("--id")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ffmpeg", type=Path)
    parser.add_argument("--max-frames", type=int, default=24)
    parser.add_argument("--check-artifacts", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            if not all((args.source, args.kind, args.title, args.id, args.output)):
                raise ValueError("init requires --source --kind --title --id --output")
            result = scaffold(args.source, args.kind, args.title, args.id)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
        else:
            if args.study is None:
                raise ValueError("--study is required")
            data = load(args.study)
            errors = validate(data, check_artifacts=args.check_artifacts)
            if errors:
                print(json.dumps({"passed": False, "errors": errors}, ensure_ascii=False))
                return 1
            if args.command == "extract":
                if args.output is None:
                    raise ValueError("extract requires a new --output directory")
                result = extract(data, args.output, args.ffmpeg, args.max_frames)
            elif args.command == "brief":
                result = brief(data)
            else:
                result = {"passed": True, "status": data["status"], "limits": "Structure/provenance only; no automatic visual understanding or art approval"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, AttributeError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({"passed": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
