"""Unsaved 1080p benchmark of constant-one palette bypass pruning only.

Blender --background --disable-autoexec --python-exit-code 1 --python this.py --
--output-dir D:/codex/temp/MMD-Bold-Wedding-v1/benchmark/run-v1
Use --inspect-only to perform no renders. No project or preferences are saved.
"""

import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

import bpy
import numpy as np

SOURCE = Path(
    "D:/codex/output/MMD-Guanhai-Transfer-v1/production-v3/Franken_Duet_Reference_Transfer.blend"
)
SOURCE_SHA256 = "a86716008af6801f8518618ca48a2c3b728aee7d9efe04cd7314eca97f929c28"
PREFIX = "Reference transfer | "


def plain(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)


def curves(animation):
    if not animation or not animation.action:
        return []
    action = animation.action
    result = list(getattr(action, "fcurves", ()))
    for layer in getattr(action, "layers", ()):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                result.extend(bag.fcurves)
    return result


def animated(socket):
    animation = socket.id_data.animation_data
    if not animation:
        return False
    path = socket.path_from_id("default_value")
    return bool(animation.nla_tracks) or any(
        c.data_path == path for c in list(animation.drivers) + curves(animation)
    )


def socket_id(socket):
    return {
        "node": socket.node.name,
        "socket": socket.name,
        "identifier": socket.identifier,
    }


def reachable(tree, assumed_selected=None):
    assumed_selected = assumed_selected or {}
    pending = [
        n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output
    ]
    pending.extend(n for n in tree.nodes if n.type == "OUTPUT_AOV")
    seen = set()
    while pending:
        node = pending.pop()
        if node.name in seen:
            continue
        seen.add(node.name)
        if node.name in assumed_selected:
            pending.append(assumed_selected[node.name])
            continue
        pending.extend(
            link.from_node for socket in node.inputs for link in socket.links
        )
    # RNA enum is abbreviated (SHADERTORGB); use the stable node class ID.
    return sorted(n for n in seen if tree.nodes[n].bl_idname == "ShaderNodeShaderToRGB")


def settings(scene):
    return {
        "engine": scene.render.engine,
        "frame": scene.frame_current,
        "resolution": [
            scene.render.resolution_x,
            scene.render.resolution_y,
            scene.render.resolution_percentage,
        ],
        "fps": scene.render.fps,
        "fps_base": scene.render.fps_base,
        "use_compositing": scene.render.use_compositing,
        "use_sequencer": scene.render.use_sequencer,
        "use_motion_blur": scene.render.use_motion_blur,
        "compositor_device": getattr(scene.render, "compositor_device", None),
        "compositor_precision": getattr(scene.render, "compositor_precision", None),
        "eevee": {
            p: plain(getattr(scene.eevee, p))
            for p in (
                "taa_render_samples",
                "taa_samples",
                "shadow_pool_size",
                "use_raytracing",
                "volumetric_tile_size",
                "volumetric_samples",
                "volumetric_start",
                "volumetric_end",
                "use_volumetric_shadows",
            )
            if hasattr(scene.eevee, p)
        },
        "camera": scene.camera.name,
        "camera_dof": scene.camera.data.dof.use_dof,
        "world": scene.world.name if scene.world else None,
        "color": {
            p: getattr(scene.view_settings, p)
            for p in ("view_transform", "look", "exposure", "gamma")
        },
        "image": {
            p: plain(getattr(scene.render.image_settings, p))
            for p in ("file_format", "color_depth", "color_mode")
        },
    }


def inventory(scene):
    probes = []
    for obj in scene.objects:
        if obj.type in {"LIGHT_PROBE", "LIGHTPROBE"}:
            probes.append(
                {
                    "name": obj.name,
                    "type": getattr(obj.data, "type", None),
                    "hide_render": obj.hide_render,
                }
            )
    compositor = scene.compositing_node_group
    return {
        "lights": [
            {
                "name": o.name,
                "type": o.data.type,
                "energy": o.data.energy,
                "shadow": o.data.use_shadow,
            }
            for o in scene.objects
            if o.type == "LIGHT" and not o.hide_render
        ],
        "probes": probes,
        "compositor_nodes": [
            {"name": n.name, "type": n.bl_idname, "mute": n.mute}
            for n in compositor.nodes
        ]
        if compositor
        else [],
        "note": "Inventory only; this benchmark does not isolate compositor/probe cost.",
    }


def inspect():
    candidates, records, errors = [], [], []
    for material in bpy.data.materials:
        tree = material.node_tree
        bypass = tree.nodes.get(PREFIX + "shading bypass") if tree else None
        if not bypass:
            continue
        problems = []
        if bypass.type != "MIX_RGB" or bypass.blend_type != "MIX":
            problems.append("not an ordinary MIX")
        if bypass.use_clamp or bypass.use_alpha:
            problems.append("clamp/alpha behavior needs separate analysis")
        factor = bypass.inputs[0]
        control = factor.links[0].from_node if len(factor.links) == 1 else None
        if (
            not control
            or control.type != "VALUE"
            or control.name != PREFIX + "enable designed shading"
        ):
            problems.append("factor does not have the expected constant Value control")
        elif abs(control.outputs[0].default_value - 1) > 0.0000001 or animated(
            control.outputs[0]
        ):
            problems.append("factor is not a static exact one")
        if animated(factor):
            problems.append("factor default is animated")
        selected = (
            bypass.inputs[2].links[0].from_socket
            if len(bypass.inputs[2].links) == 1
            else None
        )
        if (
            selected is None
            or selected.node.name != PREFIX + "designed two color palette"
        ):
            problems.append("selected input is not the expected new palette")
        elif any(
            abs(e.color[3] - 1) > 0.0000001 for e in selected.node.color_ramp.elements
        ):
            problems.append("selected palette has nonopaque alpha")
        destinations = [link.to_socket for link in bypass.outputs[0].links]
        if not destinations:
            problems.append("bypass has no destinations")
        record = {
            "material": material.name,
            "actor": material.get("performer_id"),
            "bypass": bypass.name,
            "factor": control.outputs[0].default_value if control else None,
            "selected": socket_id(selected) if selected is not None else None,
            "destinations": [socket_id(s) for s in destinations],
            "reachable_ShaderToRGB_before": reachable(tree),
            "problems": problems,
        }
        if selected is not None:
            record["predicted_reachable_ShaderToRGB_after"] = reachable(
                tree, {bypass.name: selected.node}
            )
        records.append(record)
        if problems:
            errors.append({"material": material.name, "problems": problems})
        else:
            candidates.append((tree, bypass, selected, destinations, record))
    if len(records) != 38:
        errors.append({"expected_bypass_materials": 38, "actual": len(records)})
    return candidates, records, errors


def render(scene, name, output):
    print("BOLD_BENCH_RENDER_START", name, flush=True)
    path = output / (name + ".png")
    scene.render.filepath = str(path)
    started = time.perf_counter()
    outcome = bpy.ops.render.render(write_still=True, scene=scene.name)
    seconds = time.perf_counter() - started
    assert outcome == {"FINISHED"} and path.is_file(), (
        "Render did not produce the requested PNG: " + str(outcome)
    )
    pixels = display_pixels(path)
    assert pixels.size == 1920 * 1080 * 4 and np.isfinite(pixels).all()
    print("BOLD_BENCH_RENDER_COMPLETE", name, seconds, flush=True)
    return pixels, {
        "name": name,
        "render_seconds_including_original_PNG_write": seconds,
        "decoded_PNG_pixel_sha256": hashlib.sha256(pixels.tobytes()).hexdigest(),
        "saved_image": str(path),
    }


def comparison(a, b):
    delta = np.abs(a.astype(np.float64) - b.astype(np.float64))
    pixels = delta.reshape((-1, 4))
    return {
        "exact": bool(np.array_equal(a, b)),
        "max_absolute_rgba": float(delta.max()),
        "mean_absolute_rgba": float(delta.mean()),
        "rmse_rgba": float(np.sqrt(np.mean(delta * delta))),
        "pixels_changed_above_1e-6": int(
            np.count_nonzero(pixels.max(axis=1) > 0.000001)
        ),
        "pixels_changed_above_1e-4": int(np.count_nonzero(pixels.max(axis=1) > 0.0001)),
    }


def display_pixels(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        values = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(values)
        assert list(image.size) == [1920, 1080]
        return values
    finally:
        bpy.data.images.remove(image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame", type=int, default=4290)
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument(
        "--skip-warmup",
        action="store_true",
        help="Recovery mode: two calls only; timing is not a controlled warm comparison",
    )
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    assert args.frame == 4290, "Benchmark contract is the source 4290 pose"
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
    args.output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "source": str(SOURCE),
        "source_sha256": SOURCE_SHA256,
        "saved_project": False,
        "saved_preferences": False,
        "rendered_frames": 0,
        "inspect_only": args.inspect_only,
        "controlled_same_process_warmup": not args.skip_warmup,
        "errors": [],
    }
    try:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
        scene = bpy.context.scene
        scene.frame_set(args.frame)
        bpy.context.view_layer.update()
        outputs = []
        for other in bpy.data.scenes:
            if other.compositing_node_group:
                for node in other.compositing_node_group.nodes:
                    if node.type == "OUTPUT_FILE":
                        outputs.append(
                            {
                                "scene": other.name,
                                "node": node.name,
                                "originally_muted": node.mute,
                            }
                        )
                        node.mute = True
        report["inherited_FileOutputs_muted"] = outputs
        report["settings"] = settings(scene)
        assert report["settings"]["resolution"] == [1920, 1080, 100]
        assert report["settings"]["image"]["file_format"] == "PNG", (
            "Preserve the original PNG settings"
        )
        report["inventory"] = inventory(scene)
        candidates, records, errors = inspect()
        report["inspection"] = records
        report["errors"].extend(errors)
        if errors:
            raise ValueError(
                "Unsafe or unexpected bypass; no renders/pruning performed"
            )
        print("BOLD_BENCH_STATIC_INSPECTION_OK", len(candidates), flush=True)
        if not args.inspect_only:
            warm, warm_record = None, None
            if not args.skip_warmup:
                warm, warm_record = render(scene, "warmup-source-4290", args.output_dir)
                report["rendered_frames"] += 1
            baseline, baseline_record = render(
                scene, "baseline-source-4290", args.output_dir
            )
            report["rendered_frames"] += 1
            for tree, bypass, selected, destinations, record in candidates:
                for destination in destinations:
                    tree.links.new(selected, destination)
                record["reachable_ShaderToRGB_after"] = reachable(tree)
                record["reversal"] = {
                    "restore_from": socket_id(bypass.outputs[0]),
                    "destinations": [socket_id(s) for s in destinations],
                }
            bpy.context.view_layer.update()
            assert settings(scene) == report["settings"], "Render settings changed"
            pruned, pruned_record = render(scene, "pruned-source-4290", args.output_dir)
            report["rendered_frames"] += 1
            report["renders"] = ([warm_record] if warm_record else []) + [
                baseline_record,
                pruned_record,
            ]
            if warm is not None:
                report["warmup_vs_baseline_saved_PNG"] = comparison(warm, baseline)
            report["baseline_vs_pruned_saved_PNG"] = comparison(baseline, pruned)
            baseline_time = baseline_record[
                "render_seconds_including_original_PNG_write"
            ]
            pruned_time = pruned_record["render_seconds_including_original_PNG_write"]
            report["timing"] = {
                "baseline_seconds": baseline_time,
                "pruned_seconds": pruned_time,
                "speedup_ratio": baseline_time / pruned_time,
                "reduction_percent": 100
                * (baseline_time - pruned_time)
                / baseline_time,
            }
            same_pixels = report["baseline_vs_pruned_saved_PNG"]["exact"]
            report["worth_applying_for_speed"] = (
                not args.skip_warmup
                and same_pixels
                and baseline_time / pruned_time >= 1.10
            )
            report["recommendation"] = (
                "Apply these destination relinks only to a new production copy; keep reversal records"
                if report["worth_applying_for_speed"]
                else "No demonstrated >=10% speed benefit with exact output pixels; do not expand this benchmark"
            )
        report["source_hash_unchanged"] = (
            hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
        )
        report["passed"] = not report["errors"] and report["source_hash_unchanged"]
    except Exception as error:  # noqa: BLE001 -- Preserve unexpected native failures in the diagnostic report.
        report["passed"] = False
        report["errors"].append(
            {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            }
        )
    report["limits"] = [
        "Only the 38 static-factor-one palette bypass output links may change; all old nodes are retained and relinking restores the fallback controls.",
        "Same frame, 1080p, original samples, lights, probes, compositor, materials, motion blur, DOF and display transform; inherited disk outputs muted.",
        "Normally one warm-up and one timed sample per condition; --skip-warmup recovery is explicitly not a controlled warm comparison. Pruning may cause shader compilation in its timed sample. Timing is not a robust average or a full-animation throughput prediction.",
        "Structural ShaderToRGB reachability is not proof of actual shader evaluation cost; GPU compiler optimization may already remove a constant branch.",
        "No compositor/probe/light changes, production saves, preference saves, or process termination.",
    ]
    with (args.output_dir / "benchmark.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(
        "BOLD_BENCH_COMPLETE",
        json.dumps(
            {
                "passed": report.get("passed"),
                "rendered_frames": report["rendered_frames"],
                "timing": report.get("timing"),
                "worth_applying_for_speed": report.get("worth_applying_for_speed"),
                "errors": report["errors"],
                "report": str(args.output_dir / "benchmark.json"),
            },
            ensure_ascii=True,
        ),
        flush=True,
    )
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
