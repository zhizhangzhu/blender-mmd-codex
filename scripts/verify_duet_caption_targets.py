"""Read-only, static v6-to-v7 audit of a caption-only Cryptomatte target fix.

Blender --background --disable-autoexec --python-exit-code 1 --python this.py --
  --source pinned-v6.blend --current caption-fixed-v7.blend --output new.json

Only the named Cryptomatte's matte_id and its derived read-only entries may
change. No frame sweep, render, save, preference or registry update occurs.
"""

import argparse
import json
import math
from pathlib import Path
import sys
import traceback

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_ikhor_sleeve_repair as capture

SOURCE_SHA = "201e2632befaf0a16f17b931963626a91bbc6b8f7e58d148d5047298a530de01"
CRYPTO_NAME = "Caption | both performers native object coverage"
ACTOR_CACHE = "Caption cache | actor"
BEAUTY_CACHE = "Caption cache | beauty"
PERFORMERS = frozenset({"aksiniya", "ikhor"})
_ORIGINAL_RNA = capture.rna
_TARGET_POINTER = None
_RAW_MODE = False


def normalized_rna(value, **kwargs):
    if (not _RAW_MODE and value is not None and hasattr(value, "as_pointer")
            and value.as_pointer() == _TARGET_POINTER):
        kwargs["skip"] = set(kwargs.get("skip", ())) | {"matte_id", "entries"}
    return _ORIGINAL_RNA(value, **kwargs)


def differences(a, b, path=""):
    """Every captured difference, without the truncation used by quick probes."""
    if type(a) is not type(b):
        return [{"path": path, "source": a, "current": b}]
    if isinstance(a, dict):
        result = []
        for key in sorted(a.keys() | b.keys()):
            child = path + "/" + str(key)
            if key not in a:
                result.append({"path": child, "kind": "added", "current": b[key]})
            elif key not in b:
                result.append({"path": child, "kind": "removed", "source": a[key]})
            else:
                result.extend(differences(a[key], b[key], child))
        return result
    if isinstance(a, list):
        if len(a) != len(b):
            return [{"path": path, "source": a, "current": b}]
        return [d for i, (x, y) in enumerate(zip(a, b))
                for d in differences(x, y, path + "/" + str(i))]
    return [] if a == b else [{"path": path, "source": a, "current": b}]


def graph_record(tree, start):
    """Conservative traversal includes muted links as potential dependencies."""
    reachable, queue = set(), [start]
    while queue:
        node = queue.pop()
        if node.name in reachable:
            continue
        reachable.add(node.name)
        queue.extend(l.to_node for l in tree.links if l.from_node == node)
    outputs = [{"node": l.from_node.name, "socket": l.from_socket.identifier,
                "to_node": l.to_node.name, "to_socket": l.to_socket.identifier}
               for l in tree.links if l.from_node == start]
    return {"reachable_nodes": sorted(reachable), "direct_outputs": outputs}


def beauty_dependencies(tree):
    seeds = [n for n in tree.nodes if n.name == BEAUTY_CACHE or n.type in {"COMPOSITE", "GROUP_OUTPUT"}]
    names, queue = set(), seeds[:]
    while queue:
        node = queue.pop()
        if node.name in names:
            continue
        names.add(node.name)
        queue.extend(l.from_node for l in tree.links if l.to_node == node)
    full = capture.node_tree(tree)
    return {"outputs": sorted(n.name for n in seeds), "nodes": {n: full["nodes"][n] for n in sorted(names)},
            "links": [l for l in full["links"] if l[0] in names and l[2] in names]}


def capture_file(path):
    global _TARGET_POINTER, _RAW_MODE
    capture.native.reopen(path)
    capture._ACTION_CACHE.clear()
    scene = bpy.context.scene
    saved_frames = {s.name: {"frame": s.frame_current, "subframe": s.frame_subframe} for s in bpy.data.scenes}
    tree = scene.compositing_node_group
    crypto = tree.nodes.get(CRYPTO_NAME) if tree else None
    if not crypto or crypto.bl_idname != "CompositorNodeCryptomatteV2":
        raise ValueError("Missing exact caption Cryptomatte node")
    _TARGET_POINTER = crypto.as_pointer()
    _RAW_MODE = True
    capture.fixed_frame()
    raw_tree = capture.node_tree(tree)
    detail = {"matte_id": crypto.matte_id,
              "entries": [{"name": e.name, "encoded_hash": e.encoded_hash} for e in crypto.entries],
              "entries_read_only": crypto.bl_rna.properties["entries"].is_readonly,
              "entry_fields_read_only": all(p.is_readonly for e in crypto.entries for p in e.bl_rna.properties),
              "graph": graph_record(tree, crypto)}
    actor_meshes = {who: sorted(o.name for o in scene.objects
                               if o.type == "MESH" and o.get("performer_id") == who and not o.hide_render)
                    for who in sorted(PERFORMERS)}
    expected = sorted(n for meshes in actor_meshes.values() for n in meshes)
    selected = [n.strip() for n in crypto.matte_id.split(",") if n.strip()]
    detail.update(actual_actor_meshes=actor_meshes, expected_mesh_names=expected,
                  selected_mesh_names=selected)
    _RAW_MODE = False
    static, _, _, _ = capture.capture_static()
    # The reused helper normally grants eight sleeve curves a delta exception.
    # This process disables that whitelist entirely; additionally inventory all
    # Actions in full, including names, layers, slots, curves and handles.
    static["complete_actions"] = {a.name: capture.action_record(a) for a in bpy.data.actions}
    static["saved_scene_frames"] = saved_frames
    static["active_scene"] = scene.name
    static["beauty_dependency_graph"] = beauty_dependencies(tree)
    return static, raw_tree, detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "current", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.output.exists():
        raise FileExistsError(args.output)
    report = {"schema": "duet-caption-target-delta-v1", "source": str(args.source),
              "project": str(args.current), "checks": [], "errors": [],
              "read_only": True, "rendered": False, "project_saved": False,
              "frame_sweep_performed": False, "user_art_approval": False,
              "geometry_collision_certified": False,
              "allowed_difference": {"node": CRYPTO_NAME, "properties": ["matte_id", "derived read-only entries"]},
              "scene_custom_property_exceptions": [],
              "difference_granularity": "All static datablock/Action hash changes plus full compositor property differences, without truncation."}

    def check(name, value, details=None):
        report["checks"].append({"name": name, "passed": bool(value), "details": details})

    try:
        report["source_sha256"] = capture.native.sha(args.source)
        report["project_sha256"] = capture.native.sha(args.current)
        report["audit_script_sha256"] = capture.native.sha(__file__)
        report["capture_helper_sha256"] = capture.native.sha(capture.__file__)
        report["native_helper_sha256"] = capture.native.sha(capture.native.__file__)
        check("source is the pinned technically accepted v6, never rejected v4", report["source_sha256"] == SOURCE_SHA)
        if report["source_sha256"] != SOURCE_SHA:
            raise ValueError("Refusing an unpinned beauty source")
        baseline_path = args.source.parent / "master-verification.json"
        baseline = capture.read(baseline_path)
        report["v6_49_check_baseline"] = {"path": str(baseline_path), "sha256": capture.native.sha(baseline_path),
                                          "project_sha256": baseline.get("project_sha256")}
        check("v6 existing independent 49-check report is passed and SHA-bound",
              baseline.get("passed") is True and baseline.get("delta_verified") is True
              and baseline.get("project_sha256") == SOURCE_SHA and len(baseline.get("checks", [])) == 49
              and all(c.get("passed") is True for c in baseline["checks"]) and not baseline.get("errors"))
        root = args.source.parent.parent
        report["inherited_v6_sleeve_evidence"] = {}
        for name in ("geometry-verification.json", "visual-review.json", "independent-visual-review.json"):
            evidence = root / "sleeve-review" / name
            record = capture.read(evidence)
            report["inherited_v6_sleeve_evidence"][name] = {
                "path": str(evidence), "sha256": capture.native.sha(evidence),
                "project_sha256": record.get("project_sha256"), "passed": record.get("passed")}
            check("inherited v6 sleeve evidence: " + name,
                  record.get("passed") is True and record.get("project_sha256") == SOURCE_SHA)
        # No old sleeve, corrective, name, scene-property or orphan-data delta
        # permissions are inherited. This audit has one fixed node exception.
        capture.ALLOWED_BONES = frozenset()
        capture.CORRECTIVE_ENABLED = False
        capture.ANNOTATIONS = set()
        capture.rna = normalized_rna
        source, source_tree, source_crypto = capture_file(args.source)
        print("CAPTION_TARGET_SOURCE_CAPTURED", flush=True)
        current, current_tree, current_crypto = capture_file(args.current)
        print("CAPTION_TARGET_CURRENT_CAPTURED", flush=True)
        report["source_crypto"], report["current_crypto"] = source_crypto, current_crypto
        report["static_differences"] = differences(source, current)
        report["compositor_property_differences"] = differences(source_tree, current_tree)
        report["crypto_selection_differences"] = differences(source_crypto, current_crypto)
        report["source_normalized_static_sha256"] = capture.digest(source)
        report["current_normalized_static_sha256"] = capture.digest(current)
        for category in source:
            delta = differences(source[category], current.get(category))
            check("unchanged " + category, not delta, delta or None)
        check("saved active frame remains 4290 in both projects",
              source["saved_scene_frames"][source["active_scene"]] == {"frame": 4290, "subframe": 0.0}
              and source["saved_scene_frames"] == current["saved_scene_frames"])
        for label, detail in (("source", source_crypto), ("current", current_crypto)):
            outputs = detail["graph"]["direct_outputs"]
            check(label + " Cryptomatte feeds only actor cache, with no beauty/Composite path",
                  detail["graph"]["reachable_nodes"] == sorted([CRYPTO_NAME, ACTOR_CACHE])
                  and len(outputs) == 1 and outputs[0]["socket"] == "Matte"
                  and outputs[0]["to_node"] == ACTOR_CACHE and outputs[0]["to_socket"] == "Item_1", detail["graph"])
        expected = current_crypto["expected_mesh_names"]
        check("exactly one currently renderable mesh for each actual performer",
              set(current_crypto["actual_actor_meshes"]) == PERFORMERS
              and all(len(v) == 1 for v in current_crypto["actual_actor_meshes"].values()) and len(expected) == 2,
              current_crypto["actual_actor_meshes"])
        selected = current_crypto["selected_mesh_names"]
        check("Cryptomatte names equal the two current meshes with no missing/stale/duplicate target",
              len(selected) == len(set(selected)) == 2 and sorted(selected) == expected)
        entries = current_crypto["entries"]
        check("only internally derived read-only entries match the fixed target list",
              current_crypto["entries_read_only"] and current_crypto["entry_fields_read_only"]
              and [e["name"] for e in entries] == selected and len(entries) == 2
              and all(math.isfinite(e["encoded_hash"]) and e["encoded_hash"] != 0 for e in entries))
        check("selection actually changes from the stale v6 target",
              source_crypto["matte_id"] != current_crypto["matte_id"])
        allowed_path = "/nodes/" + CRYPTO_NAME + "/settings/matte_id"
        check("the only raw compositor property change is the fixed matte_id",
              bool(report["compositor_property_differences"])
              and all(d["path"] == allowed_path for d in report["compositor_property_differences"]))
        check("beauty dependency graph contains no caption Cryptomatte",
              CRYPTO_NAME not in current["beauty_dependency_graph"]["nodes"])
        sample_path = root / "native-5s-v2" / "sample-report.json"
        sample = capture.read(sample_path)
        report["reused_beauty_provenance"] = {"source_project": str(args.source), "source_sha256": SOURCE_SHA,
            "sample_report": str(sample_path), "sample_report_sha256": capture.native.sha(sample_path),
            "native_source_frames": sample.get("source_frames"), "frames": sample.get("frames"),
            "caption_cache_directory": sample.get("caption_cache_directory"),
            "reason": "Complete geometry, materials, rigs, all Actions, camera, lights and every beauty/output dependency are identical; only a disconnected caption-mask selection changes. Reuse is from v6, never rejected v4."}
        check("reused complete 300 beauty frames identify the pinned v6 path and requested segment",
              Path(sample.get("project", "")).resolve() == args.source.resolve()
              and sample.get("source_frames") == [4140, 4439] and sample.get("frames") == 300
              and sample.get("seconds") == 5)
        check("source file bytes unchanged", capture.native.sha(args.source) == report["source_sha256"])
        check("current file bytes unchanged", capture.native.sha(args.current) == report["project_sha256"])
    except Exception as error:
        report["errors"].append({"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
    report["failed_checks"] = [c for c in report["checks"] if not c["passed"]]
    report["passed"] = bool(report["checks"]) and not report["failed_checks"] and not report["errors"]
    report["beauty_300_reuse_eligible"] = report["passed"]
    report["passed_scope"] = "Static caption-target-only v6-to-v7 delta and unchanged beauty dependency graph; existing v6 geometry/physics/art sampling evidence is inherited, not rerun as a new 303-frame scan. Corrected actor-cache PNGs and final captioned movie still need their own QA. No user artistic approval is implied."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print("DUET_CAPTION_TARGETS_VERIFIED", json.dumps({"passed": report["passed"], "checks": len(report["checks"]),
          "failed": report["failed_checks"], "errors": report["errors"], "output": str(args.output)}, ensure_ascii=True), flush=True)
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
