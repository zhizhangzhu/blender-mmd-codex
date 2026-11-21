"""Read-only independent audit of the pinned v7 character-material refinement.

Blender --background --disable-autoexec --python-exit-code 1 --python this.py --
  --source production-v7.blend --current clean-game.blend
  --preparation preparation.json --output master-verification.json

The existing sleeve capture helper is used with ALL old delta exceptions
disabled. Material ownership and allowed original-node destinations are rebuilt
from source objects, roles and the two SHA-bound profiles, never from passed
flags in the producer report. A deterministic in-memory replay additionally
checks the entire new graphs. Nothing is rendered or saved to a .blend file.
"""

import argparse
import copy
import importlib
import json
import math
from pathlib import Path
import sys
import traceback

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_ikhor_sleeve_repair as capture

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692"
ACTORS = ("aksiniya", "ikhor")
PREFIXES = {"aksiniya": "Clean Aksiniya | ", "ikhor": "Clean Ikhor | "}
STATE = "clean_aksiniya_material_state"
ANNOTATIONS = {"clean_game_refinement", "clean_game_source_sha256"}
CRYPTO = "Caption | both performers native object coverage"
IK = "Ikhor character | "
MODULES = ("palette", "response_ramp", "highlight_metal", "rim")
ARC_SOURCE_SHA = "8425c1827fd296fe19e17225e5e1e748de249bf11cae25ff888c6b010242f993"
ARC_BASELINE_REPORT_SHA = "e4b658fb6a4e9d7132ea6207d732ba8e3282df8f2bd1045311f55f4835f8cb23"
ARCS = ("Bold wedding | blue vow arc", "Bold wedding | gold vow arc")
_ORIGINAL_ACTION_RECORD = capture.action_record


def strict_action_record(action, filter_sleeves=False, filter_corrective=False):
    # The historical helper omitted the active sleeve Action's name whenever
    # filter_sleeves=True, even with an empty bone whitelist. Keep the name and
    # every curve for ALL owners so an assignment to an identical named copy
    # cannot slip through the otherwise complete Action inventory comparison.
    return _ORIGINAL_ACTION_RECORD(action, filter_sleeves=False, filter_corrective=False)


def differences(a, b, path=""):
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
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return [{"path": path, "source": a, "current": b}]
        return [d for i, (x, y) in enumerate(zip(a, b))
                for d in differences(x, y, path + "/" + str(i))]
    return [] if a == b else [{"path": path, "source": a, "current": b}]


def complete_actions():
    """Include every Action, handles, empty groups, slots and bag routing."""
    result = {}
    for action in bpy.data.actions:
        record = copy.deepcopy(capture.action_record(action))
        record["full_slots"] = [capture.rna(s, root=True) for s in action.slots]
        record["groups"] = [capture.rna(g, root=True, skip={"channels"})
                            for g in getattr(action, "groups", ())]
        record["channel_routing"] = [
            [[{"settings": capture.rna(bag, root=True, skip={"fcurves", "groups"}),
               "groups": [capture.rna(g, root=True, skip={"channels"}) for g in bag.groups],
               "curves": [(c.data_path, c.array_index) for c in bag.fcurves]}
              for bag in getattr(strip, "channelbags", ())]
             for strip in layer.strips] for layer in action.layers]
        result[action.name] = record
    return result


def material_record(material):
    graph = capture.node_tree(material.node_tree)
    if graph is not None:
        # The generic RNA helper intentionally excludes read-only scalars.
        # Socket identifiers are immutable yet semantically essential for
        # independently protecting Alpha inputs and interpreting graph links.
        for node in material.node_tree.nodes:
            for direction in ("inputs", "outputs"):
                for socket, record in zip(getattr(node, direction), graph["nodes"][node.name][direction]):
                    record["identifier"] = socket.identifier
                    record["name"] = socket.name
    return {"settings": capture.rna(material, root=True, skip={"node_tree"}),
            "nodes": graph,
            "animation": capture.animation(material)}


def extras():
    scene = bpy.context.scene
    return {"materials": {m.name: material_record(m) for m in bpy.data.materials},
            "saved_scene_frames": {s.name: {"frame": s.frame_current, "subframe": s.frame_subframe}
                                   for s in bpy.data.scenes},
            "active_scene": scene.name,
            "annotations": {s.name: {k: capture.plain(s[k]) for k in ANNOTATIONS if k in s}
                            for s in bpy.data.scenes},
            "actor_meshes": {who: sorted(o.name for o in scene.objects
                               if o.type == "MESH" and o.get("performer_id") == who and not o.hide_render)
                              for who in ACTORS},
            "crypto": {s.name: capture.node_tree(s.compositing_node_group)
                       for s in bpy.data.scenes if s.compositing_node_group}}


def capture_file(path):
    capture.native.reopen(path)
    capture._ACTION_CACHE.clear()
    extra = extras()
    static, _, _, _ = capture.capture_static()
    static["complete_actions"] = complete_actions()
    static["saved_scene_frames"] = extra["saved_scene_frames"]
    static["active_scene"] = extra["active_scene"]
    return static, extra


def source_contract(profiles):
    """Derive ownership, targets and permitted socket destinations from v7."""
    scene = bpy.context.scene
    ownership, selected, allowed = {}, {}, {}
    for who in ACTORS:
        meshes = [o for o in scene.objects if o.type == "MESH"
                  and o.get("performer_id") == who and not o.hide_render]
        if len(meshes) != 1:
            raise ValueError("Expected exactly one actual renderable mesh for " + who)
        mats = {m.name: m for o in meshes for m in o.data.materials if m and m.node_tree}
        ownership[who] = {name: {"slot_owners": sorted(o.name for o in bpy.data.objects
                                         if o.type == "MESH" and m in o.data.materials[:]),
                                "all_owner_performers": sorted({str(o.get("performer_id"))
                                    for o in bpy.data.objects if o.type == "MESH" and m in o.data.materials[:]}),
                                "source_name": m.get("source_mmd_material_name", name),
                                "role": m.get("character_layer_role" if who == "aksiniya" else "ikhor_material_role")}
                          for name, m in sorted(mats.items())}
        selected[who] = []
        spec = profiles[who]
        for name, mat in sorted(mats.items()):
            role = ownership[who][name]["role"]
            original_name = ownership[who][name]["source_name"]
            tree = mat.node_tree
            endpoints = set()

            def dest(node_name, socket):
                node = tree.nodes[node_name]
                endpoints.add((node_name, node.inputs[socket].identifier))

            def consumers(node_name):
                for link in tree.nodes[node_name].outputs[0].links:
                    endpoints.add((link.to_node.name, link.to_socket.identifier))

            if who == "aksiniya":
                edge = name in (spec["highlight_metal"]["hair_outline_materials"]
                                + spec["palette"]["fur_outline_materials"])
                if edge:
                    dest("mmd_edge_preview", "Color")
                elif role in {"face", "hair", "fur", "cloth", "trim", "gold", "leather"}:
                    if role in spec["palette"]["roles"]:
                        dest("Reference transfer | shading bypass", 2)
                    if role == "face" and name in spec["response_ramp"]["materials"]:
                        dest("Character layers | SDF and native light combined once", 1)
                        dest("Reference transfer | MULTIPLY", 0)
                    hair = tree.nodes.get("Character layers | one directional hair highlight")
                    if role == "hair" and hair and hair.inputs[0].is_linked:
                        dest(hair.name, 0)
                    gold = tree.nodes.get("Surface | masked gold response")
                    if gold and gold.type == "BSDF_PRINCIPLED":
                        dest(gold.name, "Roughness")
                    if role in {"hair", "fur", "cloth", "trim", "gold", "leather"}:
                        dest("Reference transfer | controlled rim amount", 0)
                        for label in ("aksiniya_head_rim", "aksiniya_body_rim"):
                            node = tree.nodes.get("Bold wedding material | " + label + " HDR amount")
                            if node:
                                dest(node.name, 1)
            else:
                white = role == "cloth" and original_name in spec["white_outer"]["materials"]
                palette_role = "white_outer" if white else role if role in {"face", "skin", "hair"} else None
                gold = original_name in spec["gold_highlight"]["materials"]
                if original_name in spec["exclude_materials"] or not (palette_role or gold):
                    continue
                if palette_role:
                    consumers(IK + "single material palette")
                    rim = tree.nodes[IK + "narrow lit-side rim"]
                    dest(rim.inputs[0].links[0].from_node.name, 1)
                    consumers(IK + "rim strength")
                    if white:
                        consumers(IK + "source times single palette")
                if role == "hair":
                    dest(IK + "directional hair band", 1)
                    consumers(IK + "hair band strength")
                if gold:
                    physical = tree.nodes[IK + "material-specific physical closure"]
                    rough = physical.inputs["Roughness"].links[0].from_node
                    dest(rough.inputs[1].links[0].from_node.name, 1)
                    mix = tree.nodes[IK + "gold versus cloth closure mix"]
                    dest(mix.inputs[1].links[0].from_node.name, 1)
            if endpoints:
                selected[who].append(name)
                allowed[name] = sorted(endpoints)
    return ownership, selected, allowed


def input_links(graph, node_name, identifier=None):
    return [l for l in graph["links"] if l[2] == node_name and (identifier is None or l[3] == identifier)]


def audit_material(name, who, old, new, endpoints, check):
    """Original nodes stay exact; only known old input links may be replaced."""
    prefix = PREFIXES[who]
    a, b = old["nodes"], new["nodes"]
    old_names, new_names = set(a["nodes"]), set(b["nodes"])
    added = new_names - old_names
    label = who + "/" + name + ": "
    expected_settings = copy.deepcopy(old["settings"])
    if who == "aksiniya":
        settings = copy.deepcopy(new["settings"])
        settings.get("custom_properties", {}).pop(STATE, None)
    else:
        settings = new["settings"]
    check(label + "only permitted material state property added; original animation/settings preserved",
          settings == expected_settings and old["animation"] == new["animation"])
    check(label + "all original node types, properties, defaults and images unchanged",
          old_names <= new_names and all(a["nodes"][n] == b["nodes"][n] for n in old_names),
          {"removed": sorted(old_names - new_names), "changed": sorted(n for n in old_names & new_names
                                          if a["nodes"][n] != b["nodes"][n])})
    check(label + "only character-specific arithmetic/control nodes added",
          bool(added) and all(n.startswith(prefix) for n in added)
          and all(b["nodes"][n]["settings"]["rna_type"] not in {
              "ShaderNodeEmission", "ShaderNodeBsdfDiffuse", "ShaderNodeShaderToRGB",
              "ShaderNodeAmbientOcclusion", "ShaderNodeOutputAOV", "ShaderNodeOutputMaterial"}
                  and not b["nodes"][n]["settings"]["rna_type"].startswith("ShaderNodeBsdf") for n in added))
    permitted = set(tuple(e) for e in endpoints)
    old_links, new_links = set(a["links"]), set(b["links"])
    removed = old_links - new_links
    incoming = [l for l in new_links - old_links if l[2] in old_names]
    check(label + "original graph rewiring limited to independently derived input destinations",
          all((l[2], l[3]) in permitted for l in removed)
          and all(l[0] in added and (l[2], l[3]) in permitted for l in incoming)
          and all(l[0] in added or l[2] in added for l in new_links - old_links),
          {"removed": sorted(removed), "added_original_node_inputs": sorted(incoming),
           "permitted_destinations": endpoints})
    protected, alpha_sockets = [], []
    for node_name, node in a["nodes"].items():
        kind = node["settings"]["rna_type"]
        special_edge = who == "aksiniya" and name.startswith("mmd_edge.") and node_name == "mmd_edge_preview"
        if ((node_name.startswith("mmd_") and not special_edge)
                or kind in {"ShaderNodeOutputAOV", "ShaderNodeOutputMaterial"}
                or "alpha" in node_name.lower() or "transparency" in node_name.lower()):
            protected.append(node_name)
        for socket in node["inputs"]:
            if "alpha" in socket.get("name", "").lower():
                alpha_sockets.append((node_name, socket["identifier"]))
    check(label + "original MMD ColorAlpha, texture/sphere inputs, all Alpha and AOV/closure outputs preserved",
          all(input_links(a, n) == input_links(b, n) for n in protected)
          and all(input_links(a, n, s) == input_links(b, n, s) for n, s in alpha_sockets),
          {"protected_nodes": protected, "alpha_input_sockets": alpha_sockets})
    check(label + "node-tree settings, interface and animation preserved",
          all(a[k] == b[k] for k in ("settings", "interface", "animation")))
    for node_name in sorted(added):
        settings = b["nodes"][node_name]["settings"]
        if settings["rna_type"] == "ShaderNodeTexImage":
            original = a["nodes"].get("Genshin study | supplied model FaceLightmap")
            check(label + "new image sample uses the identical original SDF only: " + node_name,
                  who == "aksiniya" and name == "颜" and original is not None
                  and settings["image"] == original["settings"]["image"])
    if who == "aksiniya" and name.startswith("mmd_edge."):
        node = bpy.data.materials[name].node_tree.nodes["mmd_edge_preview"]
        color = node.inputs["Color"]
        link = color.links[0] if len(color.links) == 1 else None
        original_color = next(s["default_value"] for s in a["nodes"]["mmd_edge_preview"]["inputs"]
                              if s["name"] == "Color")
        mix = link.from_node if link else None
        check(label + "outline RGB edit keeps both branches' identical original Alpha",
              mix is not None and mix.type == "MIX_RGB"
              and mix.inputs[1].default_value[3] == original_color[3]
              and mix.inputs[2].default_value[3] == original_color[3])


def arc_detail():
    """Cheap source reopen: exact target objects, frames and probe settings."""
    frames = {s.name: {"frame": s.frame_current, "subframe": s.frame_subframe}
              for s in bpy.data.scenes}
    capture.fixed_frame()
    objects = {}
    for name in ARCS:
        obj = bpy.data.objects[name]
        if obj.type != "CURVE" or not obj.get("bold_wedding_fx"):
            raise ValueError("The fixed arc must remain an original wedding FX CURVE: " + name)
        objects[name] = {"settings": capture.rna(obj, root=True, skip=capture.OBJECT_SKIP),
                         "data": capture.identifier(obj.data), "animation": capture.animation(obj)}
    return {"objects": objects, "saved_scene_frames": frames, "active_scene": bpy.context.scene.name,
            "scene_annotations": {s.name: {k: capture.plain(s[k]) for k in ANNOTATIONS if k in s}
                                  for s in bpy.data.scenes},
            "probe_settings": {p.name: capture.rna(p, root=True) for p in bpy.data.lightprobes},
            "cache_file_settings": {p.name: capture.rna(p, root=True) for p in bpy.data.cache_files}}


def audit_arcs_hidden(args):
    """Inherit pinned 321 checks; prove the complete new static delta once.

    The accepted report contains all 38 original material hash substitutions
    and the complete normalized static digest. Reconstructing that exact
    normalization lets one current-file capture prove preservation of EVERY
    category without repeating a full source capture or shader replay.
    """
    report = {"schema": "duet-clean-game-arcs-hidden-audit-v1", "source": str(args.source),
              "project": str(args.current), "checks": [], "errors": [], "arcs_hidden": True,
              "read_only": True, "rendered": False, "project_saved": False,
              "preferences_changed": False, "frame_sweep_performed": False,
              "shader_modules_replayed": False, "source_full_static_recaptured": False,
              "current_full_static_recaptured": True, "user_art_approval": False,
              "geometry_collision_certified": False,
              "allowed_object_changes": {n: ["hide_render", "hide_viewport"] for n in ARCS},
              "scene_custom_property_exceptions": [], "allowed_material_changes": []}

    def check(name, passed, details=None):
        report["checks"].append({"name": name, "passed": bool(passed), "details": details})

    try:
        report["source_sha256"] = capture.native.sha(args.source)
        report["project_sha256"] = capture.native.sha(args.current)
        report["audit_script_sha256"] = capture.native.sha(__file__)
        report["capture_helper_sha256"] = capture.native.sha(capture.__file__)
        report["native_helper_sha256"] = capture.native.sha(capture.native.__file__)
        report["arc_removal_report"] = str(args.preparation)
        report["arc_removal_report_sha256"] = capture.native.sha(args.preparation)
        reused = None
        if args.resume_arcs_static_report:
            if not args.resume_arcs_static_sha256:
                raise ValueError("A reused full-static report requires its explicit SHA256")
            reused_sha = capture.native.sha(args.resume_arcs_static_report)
            reused = capture.read(args.resume_arcs_static_report)
            old_check = "the complete target-object difference is exactly four False-to-True visibility booleans"
            old_failures = reused.get("failed_checks", [])
            archived_script = args.resume_arcs_static_report.parent / "verify_clean_game_duet_before_dimensions_fix.py"
            check("reused complete static capture is SHA-bound to these exact files and has only the resolved bounds check",
                  reused_sha == args.resume_arcs_static_sha256
                  and reused.get("schema") == "duet-clean-game-arcs-hidden-audit-v1"
                  and reused.get("source_sha256") == report["source_sha256"] == ARC_SOURCE_SHA
                  and reused.get("project_sha256") == report["project_sha256"]
                  and reused.get("capture_helper_sha256") == report["capture_helper_sha256"]
                  and reused.get("native_helper_sha256") == report["native_helper_sha256"]
                  and not reused.get("errors") and len(reused.get("checks", [])) == 23
                  and len(old_failures) == 1 and old_failures[0]["name"] == old_check
                  and all(c["passed"] is True for c in reused["checks"] if c["name"] != old_check)
                  and archived_script.is_file()
                  and capture.native.sha(archived_script) == reused.get("audit_script_sha256"))
            report["inherited_full_static_capture"] = {
                "path": str(args.resume_arcs_static_report), "sha256": reused_sha,
                "script": str(archived_script), "script_sha256": reused.get("audit_script_sha256"),
                "original_failed_check": old_failures,
                "resolution": "Hidden viewport curves expose unevaluated fallback dimensions. Independently reopen both files, compare all authored fields, and re-evaluate both current curves with the four visibility flags restored; complete full-static digest was already equal."}
            report["current_full_static_recaptured"] = False
            report["current_full_static_report_reused"] = True
            if not report["checks"][-1]["passed"]:
                raise ValueError("Refusing an unbound or otherwise failed full-static capture")
        check("arc-delta source is the fixed 321-check accepted clean-game v1",
              report["source_sha256"] == ARC_SOURCE_SHA)
        if report["source_sha256"] != ARC_SOURCE_SHA:
            raise ValueError("--arcs-hidden accepts only the pinned clean-game v1 source")
        baseline_path = args.source.parent / "master-verification.json"
        baseline_sha = capture.native.sha(baseline_path)
        baseline = capture.read(baseline_path)
        report["inherited_321_check_audit"] = {"path": str(baseline_path), "sha256": baseline_sha,
            "project_sha256": baseline.get("project_sha256"), "checks": len(baseline.get("checks", [])),
            "audit_script_sha256": baseline.get("audit_script_sha256"),
            "source_normalized_static_sha256": baseline.get("source_normalized_static_sha256"),
            "current_normalized_static_sha256": baseline.get("current_normalized_static_sha256")}
        check("the exact original passed 321-check report is retained and SHA-bound",
              baseline_sha == ARC_BASELINE_REPORT_SHA and baseline.get("passed") is True
              and baseline.get("delta_verified") is True and baseline.get("project_sha256") == ARC_SOURCE_SHA
              and len(baseline.get("checks", [])) == 321
              and all(c.get("passed") is True for c in baseline["checks"]) and not baseline.get("errors")
              and baseline.get("source_normalized_static_sha256") == baseline.get("current_normalized_static_sha256"))
        if baseline_sha != ARC_BASELINE_REPORT_SHA:
            raise ValueError("Refusing a changed 321-check baseline report")
        check("capture/native helper bytes are exactly the accepted baseline versions",
              report["capture_helper_sha256"] == baseline.get("capture_helper_sha256")
              and report["native_helper_sha256"] == baseline.get("native_helper_sha256"))
        proof = capture.read(args.preparation)
        expected_changes = [{"object": name, "before": {"hide_render": False, "hide_viewport": False},
                              "after": {"hide_render": True, "hide_viewport": True}} for name in ARCS]
        check("removal evidence binds actual files and exactly the requested fixed changes",
              proof.get("source_sha256") == ARC_SOURCE_SHA
              and proof.get("project_sha256") == report["project_sha256"]
              and Path(proof.get("source", "")).resolve() == args.source.resolve()
              and Path(proof.get("project", "")).resolve() == args.current.resolve()
              and proof.get("changes") == expected_changes and proof.get("user_requested") is True)
        if args.current_sha256:
            check("arc-hidden candidate matches externally pinned SHA256",
                  report["project_sha256"] == args.current_sha256)
        selected = {n for names in baseline["independent_selected_materials"].values() for n in names}
        substitutions = baseline["raw_static_differences"]
        material_pairs = {}
        for item in substitutions:
            if (not item["path"].startswith("/materials/")
                    or not isinstance(item.get("source"), str) or len(item["source"]) != 64
                    or not isinstance(item.get("current"), str) or len(item["current"]) != 64):
                raise ValueError("The inherited normalization contains a non-material or invalid substitution")
            name = item["path"][len("/materials/"):]
            if name in material_pairs:
                raise ValueError("Duplicate inherited material normalization")
            material_pairs[name] = item
        check("inherited normalization contains exactly the independently accepted 38 actor materials",
              len(material_pairs) == 38 and set(material_pairs) == selected)
        capture.ALLOWED_BONES = frozenset()
        capture.CORRECTIVE_ENABLED = False
        capture.ANNOTATIONS = ANNOTATIONS
        capture.action_record = strict_action_record
        capture.native.reopen(args.source)
        capture._ACTION_CACHE.clear()
        source_detail = arc_detail()
        check("both original source arcs were visible in render and viewport",
              all(source_detail["objects"][n]["settings"][p] is False
                  for n in ARCS for p in ("hide_render", "hide_viewport")))
        print("CLEAN_GAME_ARCS_SOURCE_BINDINGS_CAPTURED", flush=True)
        capture.native.reopen(args.current)
        capture._ACTION_CACHE.clear()
        current_detail = arc_detail()
        report["original_target_objects"] = source_detail["objects"]
        report["current_target_objects"] = current_detail["objects"]
        target_deltas = differences(source_detail["objects"], current_detail["objects"])
        bounds_paths = {"/" + n + "/settings/dimensions/" + str(axis) for n in ARCS for axis in range(3)}
        report["hidden_unevaluated_dimensions_differences"] = [d for d in target_deltas if d["path"] in bounds_paths]
        target_deltas = [d for d in target_deltas if d["path"] not in bounds_paths]
        report["target_object_differences"] = target_deltas
        expected_paths = {"/" + n + "/settings/" + p for n in ARCS
                          for p in ("hide_render", "hide_viewport")}
        check("the complete target-object difference is exactly four False-to-True visibility booleans",
              len(target_deltas) == 4 and {d["path"] for d in target_deltas} == expected_paths
              and all(d.get("source") is False and d.get("current") is True for d in target_deltas), target_deltas)
        for key in ("saved_scene_frames", "active_scene", "scene_annotations", "probe_settings", "cache_file_settings"):
            delta = differences(source_detail[key], current_detail[key])
            check("unchanged direct source/current " + key, not delta, delta or None)
        check("saved active frame is still exactly 4290",
              current_detail["saved_scene_frames"][current_detail["active_scene"]]
              == {"frame": 4290, "subframe": 0.0})
        # Only these four booleans are temporarily restored in memory. This is
        # never saved and never used to render. All other target properties,
        # curve data and EVERY remaining datablock stay strict in the digest.
        try:
            for name in ARCS:
                bpy.data.objects[name].hide_render = False
                bpy.data.objects[name].hide_viewport = False
            normalized_targets = arc_detail()["objects"]
            check("normalized visible curve dimensions and all original object fields exactly equal v1",
                  normalized_targets == source_detail["objects"],
                  differences(source_detail["objects"], normalized_targets) or None)
            if reused is None:
                current, _, _, _ = capture.capture_static()
                current["complete_actions"] = complete_actions()
                current["saved_scene_frames"] = current_detail["saved_scene_frames"]
                current["active_scene"] = current_detail["active_scene"]
            else:
                prior_material_check = next(c for c in reused["checks"]
                    if c["name"] == "all 38 refined material graphs/settings remain byte-for-byte equivalent to accepted v1")
                current = {"materials": {m["material"]: m["actual_v2_sha256"]
                                          for m in prior_material_check["details"]}}
        finally:
            for name in ARCS:
                bpy.data.objects[name].hide_render = True
                bpy.data.objects[name].hide_viewport = True
        print("CLEAN_GAME_ARCS_CURRENT_COMPLETE_STATIC_" + ("CAPTURED" if reused is None else "SHA_BOUND_REUSED"), flush=True)
        material_checks = []
        for name, pair in sorted(material_pairs.items()):
            actual = current["materials"].get(name)
            passed = actual == pair["current"]
            material_checks.append({"material": name, "passed": passed,
                                    "expected_v1_sha256": pair["current"], "actual_v2_sha256": actual})
            if passed:
                current["materials"][name] = pair["source"]
        check("all 38 refined material graphs/settings remain byte-for-byte equivalent to accepted v1",
              all(item["passed"] for item in material_checks), material_checks)
        report["current_normalized_static_sha256"] = (capture.digest(current) if reused is None
                                                      else reused["current_normalized_static_sha256"])
        report["source_normalized_static_sha256"] = baseline["current_normalized_static_sha256"]
        report["static_category_counts"] = ({key: len(value) for key, value in current.items() if isinstance(value, dict)}
                                            if reused is None else reused["static_category_counts"])
        check("complete normalized static digest equals the pinned 321-check baseline; no other change",
              report["current_normalized_static_sha256"] == baseline["current_normalized_static_sha256"],
              {"expected": baseline["current_normalized_static_sha256"],
               "actual": report["current_normalized_static_sha256"],
               "categories": sorted(current) if reused is None else sorted(reused["static_category_counts"]),
               "normalization": "Only four fixed visibility booleans and the exact prior 38 material-hash substitutions; visibility-dependent dimensions must re-evaluate exactly, never authored as a delta"})
        report["current_complete_actions_sha256"] = (capture.digest(current["complete_actions"]) if reused is None
                                                     else reused["current_complete_actions_sha256"])
        report["source_complete_actions_sha256"] = baseline["current_complete_actions_sha256"]
        report["action_count"] = len(current["complete_actions"]) if reused is None else reused["action_count"]
        check("all 11 Actions, handles, slot routing and active assignment names remain exact",
              report["action_count"] == baseline["action_count"] == 11
              and report["current_complete_actions_sha256"] == baseline["current_complete_actions_sha256"])
        crypto = bpy.context.scene.compositing_node_group.nodes[CRYPTO]
        targets = [n.strip() for n in crypto.matte_id.split(",") if n.strip()]
        expected_meshes = sorted(o.name for o in bpy.context.scene.objects if o.type == "MESH"
                                 and o.get("performer_id") in ACTORS and not o.hide_render)
        report["caption_crypto"] = {"selected_names": targets, "expected_actual_meshes": expected_meshes}
        check("caption Crypto still selects both actual performers exactly",
              targets == baseline["caption_crypto"]["selected_names"]
              and len(targets) == len(set(targets)) == 2 and sorted(targets) == expected_meshes)
        for label, path, expected in (("source", args.source, report["source_sha256"]),
                ("current", args.current, report["project_sha256"]),
                ("original 321-check audit", baseline_path, ARC_BASELINE_REPORT_SHA),
                ("arc removal evidence", args.preparation, report["arc_removal_report_sha256"]),
                ("audit script", __file__, report["audit_script_sha256"])):
            check(label + " bytes unchanged during arc audit", capture.native.sha(path) == expected)
        if reused is not None:
            check("reused full-static report bytes unchanged during supplemental verification",
                  capture.native.sha(args.resume_arcs_static_report) == args.resume_arcs_static_sha256)
    except Exception as error:
        report["errors"].append({"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
    report["failed_checks"] = [c for c in report["checks"] if not c["passed"]]
    report["passed"] = bool(report["checks"]) and not report["failed_checks"] and not report["errors"]
    report["delta_verified"] = report["passed"]
    report["prior_geometry_motion_evidence_inheritable"] = report["passed"]
    report["beauty_300_reuse_eligible"] = False
    report["limits"] = [
        "Explicit --arcs-hidden delta mode only: the two fixed wedding FX CURVEs must change hide_render and hide_viewport from False to True. No material, scene property, light, stage-geometry or camera exception is added.",
        "The original 321-check material audit is retained with its fixed SHA. One complete current-file static capture, normalized by precisely those four visibility booleans and the prior report's exact 38 material substitutions, must reproduce its full digest. This includes all meshes/UV/weights/shapes, objects, Actions, all materials/node groups/images, lights/cameras/world/scenes, sound and compositor/Crypto.",
        "Probe and cache-file RNA settings are additionally compared directly between reopened v1 and v2; no probe cache is baked or modified by this audit. Internal engine cache payloads not exposed through RNA are not independently re-certified.",
        "Raw hidden-viewport Object.dimensions can use unevaluated fallback bounds. These six derived values are disclosed separately, and all full object fields including dimensions must exactly match v1 after only the four visibility flags are temporarily restored; curve geometry and authored loc/rot/scale remain strict. A previously completed static capture may be reused only with explicit SHA binding to these exact source/current bytes and the preserved corresponding audit script.",
        "Prior material/geometry/Action evidence is inherited, not rerun as a shader replay or 303-frame motion scan. Only the two arc effects change the stage appearance. All new diagnostics and the complete final beauty/caption/audio checks must identify v2; old beauty frames cannot be reused.",
        "No user art approval or full-song certification is implied.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print("CLEAN_GAME_ARCS_HIDDEN_VERIFIED", json.dumps({"passed": report["passed"],
          "checks": len(report["checks"]), "failed": report["failed_checks"],
          "errors": report["errors"], "output": str(args.output)}, ensure_ascii=True), flush=True)
    if not report["passed"]:
        raise SystemExit(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "current", "preparation", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--current-sha256")
    parser.add_argument("--arcs-hidden", action="store_true",
                        help="Explicit pinned v1-to-v2 arc-visibility delta; --preparation is arc-removal.json")
    parser.add_argument("--resume-arcs-static-report", type=Path,
                        help="Reuse the exact earlier full-static capture while resolving only hidden-curve derived bounds")
    parser.add_argument("--resume-arcs-static-sha256")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.resume_arcs_static_report and not args.arcs_hidden:
        parser.error("--resume-arcs-static-report requires explicit --arcs-hidden")
    if args.arcs_hidden:
        audit_arcs_hidden(args)
        return
    report = {"schema": "duet-clean-game-static-audit-v1", "source": str(args.source),
              "project": str(args.current), "checks": [], "errors": [], "read_only": True,
              "rendered": False, "project_saved": False, "preferences_changed": False,
              "frame_sweep_performed": False, "user_art_approval": False,
              "geometry_collision_certified": False, "allowed_bones": [],
              "allowed_corrective_shapes": [], "permitted_orphan_removals": [],
              "scene_custom_property_exceptions": sorted(ANNOTATIONS)}

    def check(name, passed, details=None):
        report["checks"].append({"name": name, "passed": bool(passed), "details": details})

    try:
        report["source_sha256"] = capture.native.sha(args.source)
        report["project_sha256"] = capture.native.sha(args.current)
        report["audit_script_sha256"] = capture.native.sha(__file__)
        report["capture_helper_sha256"] = capture.native.sha(capture.__file__)
        report["native_helper_sha256"] = capture.native.sha(capture.native.__file__)
        report["preparation"] = str(args.preparation)
        report["preparation_sha256"] = capture.native.sha(args.preparation)
        proof = capture.read(args.preparation)
        check("source is the pinned caption-fixed v7", report["source_sha256"] == SOURCE_SHA)
        if report["source_sha256"] != SOURCE_SHA:
            raise ValueError("Refusing an unpinned source")
        check("producer proof binds actual source and new project bytes/paths",
              proof.get("source_sha256") == SOURCE_SHA
              and proof.get("project_sha256") == report["project_sha256"]
              and Path(proof["source"]).resolve() == args.source.resolve()
              and Path(proof["project"]).resolve() == args.current.resolve()
              and report["source_sha256"] != report["project_sha256"])
        if args.current_sha256:
            check("candidate matches externally pinned SHA256", args.current_sha256 == report["project_sha256"])
        profiles, modules = {}, {}
        report["profiles"], report["modules"] = {}, {}
        for who in ACTORS:
            path = ROOT / "presets" / "quality" / (who + "-clean-game-v1.json")
            profiles[who] = capture.read(path)
            modules[who] = importlib.import_module("clean_" + who + "_materials")
            report["profiles"][who] = {"path": str(path), "sha256": capture.native.sha(path)}
            report["modules"][who] = {"path": modules[who].__file__, "sha256": capture.native.sha(modules[who].__file__)}
            check(who + " profile and material module exactly SHA-bound to builder",
                  report["profiles"][who]["sha256"] == proof["profiles"][who]["sha256"]
                  and profiles[who] == proof["profiles"][who]["data"]
                  and report["modules"][who]["sha256"] == proof["modules"][who]["sha256"])
        baseline_path = args.source.parent / "master-verification.json"
        baseline = capture.read(baseline_path)
        report["inherited_source_audit"] = {"path": str(baseline_path), "sha256": capture.native.sha(baseline_path),
                                              "project_sha256": baseline.get("project_sha256")}
        check("pinned v7 independent source audit passed without errors",
              baseline.get("passed") is True and baseline.get("project_sha256") == SOURCE_SHA
              and all(c.get("passed") is True for c in baseline.get("checks", []))
              and bool(baseline.get("checks")) and not baseline.get("errors"))
        report["inherited_sleeve_evidence"] = baseline.get("inherited_v6_sleeve_evidence", {})
        check("source audit carries all three previously accepted sleeve evidence reports",
              set(report["inherited_sleeve_evidence"]) == {
                  "geometry-verification.json", "visual-review.json", "independent-visual-review.json"})
        for name, item in report["inherited_sleeve_evidence"].items():
            path = Path(item["path"])
            evidence = capture.read(path)
            check("inherited sleeve evidence bytes retained: " + name,
                  path.is_file() and item.get("passed") is True and capture.native.sha(path) == item["sha256"]
                  and evidence.get("passed") is True
                  and evidence.get("project_sha256") == item.get("project_sha256")
                  == "201e2632befaf0a16f17b931963626a91bbc6b8f7e58d148d5047298a530de01")
        capture.ALLOWED_BONES = frozenset()
        capture.CORRECTIVE_ENABLED = False
        capture.ANNOTATIONS = ANNOTATIONS
        capture.action_record = strict_action_record
        check("all historical bone/shape/Action-name delta exceptions disabled",
              not capture.ALLOWED_BONES and capture.CORRECTIVE_ENABLED is False
              and capture.action_record is strict_action_record)
        source, source_extra = capture_file(args.source)
        ownership, selected, allowed = source_contract(profiles)
        report["independent_source_material_ownership"] = ownership
        report["independent_selected_materials"] = selected
        for who in ACTORS:
            records = proof["implementation"][who]["materials"]
            reported = [m["name" if who == "aksiniya" else "material"] for m in records]
            check(who + " producer material list equals independently rebuilt source selection",
                  sorted(reported) == selected[who] and len(reported) == len(set(reported)), reported)
            check(who + " materials owned exclusively by the actual source actor",
                  all(ownership[who][n]["all_owner_performers"] == [who] for n in selected[who]))
        shared = set(ownership[ACTORS[0]]) & set(ownership[ACTORS[1]])
        report["shared_unmodified_source_materials"] = sorted(shared)
        check("the two modified source selections are disjoint and exclude shared source materials",
              not set(selected[ACTORS[0]]) & set(selected[ACTORS[1]])
              and not shared & {n for names in selected.values() for n in names})
        print("CLEAN_GAME_SOURCE_STATIC_CAPTURED", flush=True)
        # Replay is an additional complete new-graph check, not a substitute for
        # the independent original-node/destination/Alpha checks below.
        for who in ACTORS:
            modules[who].apply(bpy.context.scene, profiles[who])
        expected_materials = {n: material_record(bpy.data.materials[n])
                              for names in selected.values() for n in names}
        current, current_extra = capture_file(args.current)
        print("CLEAN_GAME_CURRENT_STATIC_CAPTURED", flush=True)
        all_selected = {n: who for who, names in selected.items() for n in names}
        raw_deltas = differences(source, current)
        report["raw_static_differences"] = raw_deltas
        normalized_current = copy.deepcopy(current)
        for name, who in sorted(all_selected.items()):
            old = source_extra["materials"][name]
            new = current_extra["materials"][name]
            audit_material(name, who, old, new, allowed[name], check)
            delta = differences(expected_materials[name], new)
            check(who + "/" + name + ": complete new graph exactly reproduces the SHA-bound profile",
                  not delta, delta or None)
            normalized_current["materials"][name] = source["materials"][name]
        for category in source:
            delta = differences(source[category], normalized_current.get(category))
            check("unchanged complete static " + category, not delta, delta or None)
        report["source_normalized_static_sha256"] = capture.digest(source)
        report["current_normalized_static_sha256"] = capture.digest(normalized_current)
        report["source_complete_actions_sha256"] = capture.digest(source["complete_actions"])
        report["current_complete_actions_sha256"] = capture.digest(current["complete_actions"])
        report["action_count"] = len(source["complete_actions"])
        check("source has neither new scene annotation",
              all(not p for p in source_extra["annotations"].values()))
        expected_annotations = {n: ({"clean_game_refinement": "duet-clean-game-v1",
                                   "clean_game_source_sha256": SOURCE_SHA}
                                   if n == current_extra["active_scene"] else {})
                                for n in current_extra["annotations"]}
        check("only the two exact new active-scene explanation properties exist",
              current_extra["annotations"] == expected_annotations, current_extra["annotations"])
        check("compositor including all Crypto/AOV/cache routing completely unchanged",
              source_extra["crypto"] == current_extra["crypto"])
        scene = bpy.context.scene
        crypto = scene.compositing_node_group.nodes.get(CRYPTO)
        expected_names = sorted(n for names in current_extra["actor_meshes"].values() for n in names)
        targets = [n.strip() for n in crypto.matte_id.split(",") if n.strip()] if crypto else []
        entries = [{"name": e.name, "encoded_hash": e.encoded_hash} for e in crypto.entries] if crypto else []
        report["caption_crypto"] = {"actual_actor_meshes": current_extra["actor_meshes"],
                                    "selected_names": targets, "entries": entries}
        check("Crypto still names both actual current meshes exactly, without stale Aether",
              len(expected_names) == len(targets) == len(set(targets)) == 2
              and all(len(current_extra["actor_meshes"][who]) == 1 for who in ACTORS)
              and sorted(targets) == expected_names and [e["name"] for e in entries] == targets
              and all(math.isfinite(e["encoded_hash"]) and e["encoded_hash"] != 0 for e in entries))
        check("saved active frame is still exactly the source 4290",
              source["saved_scene_frames"][source["active_scene"]] == {"frame": 4290, "subframe": 0.0}
              and source["saved_scene_frames"] == current["saved_scene_frames"])
        for label, path, expected in (("source", args.source, report["source_sha256"]),
                                     ("current", args.current, report["project_sha256"]),
                                     ("preparation", args.preparation, report["preparation_sha256"]),
                                     ("audit script", __file__, report["audit_script_sha256"])):
            check(label + " file bytes unchanged by audit", capture.native.sha(path) == expected)
        for who in ACTORS:
            for category in ("profiles", "modules"):
                item = report[category][who]
                check(who + " " + category + " bytes unchanged during audit",
                      capture.native.sha(item["path"]) == item["sha256"])
    except Exception as error:
        report["errors"].append({"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
    report["failed_checks"] = [c for c in report["checks"] if not c["passed"]]
    report["passed"] = bool(report["checks"]) and not report["failed_checks"] and not report["errors"]
    report["delta_verified"] = report["passed"]
    report["prior_geometry_motion_evidence_inheritable"] = report["passed"]
    report["beauty_300_reuse_eligible"] = False
    report["limits"] = [
        "Independent static reopen, exact full mesh/UV/weights/shapes/modifiers/rigs and all Action curves/handles/routing. No old eight-bone, corrective-shape, Action-name or orphan-data exception is inherited.",
        "Only independently owned actor-material graphs plus one Aksiniya material state property and two exact scene explanation properties may change. All original node properties/defaults and protected MMD ColorAlpha/sphere/Alpha/AOV inputs remain exact; known shader destinations alone may receive new control links.",
        "Full new shader graphs additionally equal a deterministic in-memory replay of the SHA-bound modules/profiles. This reproducibility check does not establish pixel-equivalent bypass or artistic improvement.",
        "The source's prior sleeve and motion evidence may be inherited only because every geometry and animation datum remains exact. No new 303-frame collision scan or physics simulation was run; inherited evidence retains its original sampling limitations.",
        "Material appearance changed: old beauty frames cannot be reused. New three-axis shader dynamics, ablation renders, 300-frame beauty/Alpha, encode/decode/audio/seam and actual image QA remain separate requirements.",
        "No full-song certification, reference-author shader recovery, game-quality certification or user art approval is implied.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print("CLEAN_GAME_MASTER_VERIFIED", json.dumps({"passed": report["passed"], "checks": len(report["checks"]),
          "failed": report["failed_checks"], "errors": report["errors"], "output": str(args.output)}, ensure_ascii=True), flush=True)
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
