"""Same-camera face ink comparison and face-shell ablation renders."""

import argparse
import copy
import json
import sys
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_outlines import apply_outlines
from mmd_caption_render import output_file
from mmd_quality_lab import position_hash, pose_hash

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--preset", type=Path, required=True)
p.add_argument("--output-dir", type=Path, required=True)
p.add_argument("--frames", type=int, nargs="+", default=[661, 781, 900])
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
args.output_dir.mkdir(parents=True, exist_ok=False)
source = bpy.data.filepath
settings = json.loads(args.preset.read_text(encoding="utf-8"))
reports = []
for mode in ["previous", "face-features-only", "face-black", "face-black-wide"]:
    bpy.ops.wm.open_mainfile(filepath=source)
    scene = bpy.context.scene
    tree = scene.compositing_node_group
    for n in list(tree.nodes):
        if n.bl_idname == "CompositorNodeOutputFile":
            tree.nodes.remove(n)
    dest = args.output_dir / mode
    dest.mkdir()
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    mesh = next(
        o
        for o in scene.objects
        if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
    )
    positions = position_hash(mesh)
    poses = {f: pose_hash(scene, arm, f) for f in args.frames}
    report = {"mode": mode, "source": source, "frames": args.frames}
    if mode != "previous":
        variant_settings = copy.deepcopy(settings)
        if mode == "face-features-only":
            variant_settings["material_overrides"]["颜"]["alpha"] = 0
        if mode == "face-black-wide":
            variant_settings["material_overrides"]["颜"]["width_scale"] = 2.5
        report["outlines"] = apply_outlines(scene, variant_settings)
        counts = {
            m.name: len(m.node_tree.nodes) for m in bpy.data.materials if m.node_tree
        }
        apply_outlines(scene, variant_settings)
        assert counts == {
            m.name: len(m.node_tree.nodes) for m in bpy.data.materials if m.node_tree
        }
        report["repeat_does_not_add_nodes"] = True
    assert position_hash(mesh) == positions and all(
        pose_hash(scene, arm, f) == v for f, v in poses.items()
    )
    report["geometry_and_pose_unchanged"] = True
    layer = scene.view_layers[0]
    layer.use_pass_cryptomatte_material = True
    layer.update_render_passes()
    crypto = tree.nodes.new("CompositorNodeCryptomatteV2")
    crypto.source = "RENDER"
    crypto.scene = scene
    crypto.layer_name = layer.name + ".CryptoMaterial"
    crypto.matte_id = "mmd_edge.颜"
    output_file(tree, dest / "diagnostics", "face-edge", crypto.outputs["Matte"], False)
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 64
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    for frame in args.frames:
        scene.frame_set(frame)
        scene.render.filepath = str(dest / f"frame-{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    if mode == "face-black":
        bpy.ops.wm.save_as_mainfile(filepath=str(dest / "face-ink.blend"))
    (dest / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    reports.append(report)
    print("FACE_INK_VARIANT_OK", mode, flush=True)
(args.output_dir / "review-report.json").write_text(
    json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
)
