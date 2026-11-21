"""Readable MMD inverse-hull ink, retaining model edge/vertex weights."""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mmd_caption_render import output_file


def apply_outlines(scene, settings):
    materials = []
    overrides = settings.get("material_overrides", {})
    for mat in list(bpy.data.materials):
        category = mat.get("look_category")
        if (
            category not in settings["colors_linear"]
            or not mat.mmd_material.enabled_toon_edge
        ):
            continue
        if mat.name.endswith("+") or mat.mmd_material.alpha <= 0.001:
            continue
        specific = overrides.get(mat.name, {})
        mat.mmd_material.edge_color = (
            *specific.get("color_linear", settings["colors_linear"][category]),
            specific.get("alpha", settings["alpha"][category]),
        )
        materials.append(mat.name)
    groups = []
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        mod = obj.modifiers.get("mmd_edge_preview")
        vg = obj.vertex_groups.get("mmd_edge_preview")
        if not mod or not vg:
            continue
        if "outline_source_weights" not in obj:
            values = []
            for vertex in obj.data.vertices:
                values.append(
                    next((g.weight for g in vertex.groups if g.group == vg.index), 0)
                )
            obj["outline_source_weights"] = values
        values = obj["outline_source_weights"]
        if len(values) != len(obj.data.vertices):
            raise ValueError("Outline topology changed")
        scales = {}
        for poly in obj.data.polygons:
            mat = obj.data.materials[poly.material_index]
            if not mat or mat.name not in materials:
                continue
            scale = overrides.get(mat.name, {}).get(
                "width_scale", settings["width_scale"][mat["look_category"]]
            )
            for vertex in poly.vertices:
                scales[vertex] = min(scales.get(vertex, scale), scale)
        for index, scale in scales.items():
            vg.add([index], min(1, float(values[index]) * scale), "REPLACE")
        mod.show_render = True
        mod.show_viewport = True
        groups.append(
            {
                "mesh": obj.name,
                "base_modifier_thickness": mod.thickness,
                "adjusted_vertices": len(scales),
            }
        )
    if not groups:
        raise ValueError("Create MMD Tools toon edges before applying the ink preset")
    features = None
    if settings.get("face_features"):
        from mmd_face_ink import apply_face_features

        features = apply_face_features(settings["face_features"])
    return {
        "materials": materials,
        "groups": groups,
        "settings": settings,
        "method": "MMD inverse hull, not screen-space edge detection",
        "face_features": features,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--preset", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    settings = json.loads(args.preset.read_text(encoding="utf-8"))
    source = bpy.data.filepath
    args.output_dir.mkdir(parents=True, exist_ok=False)
    reports = []
    for mode in ["off", "legacy", "ink"]:
        bpy.ops.wm.open_mainfile(filepath=source)
        s = bpy.context.scene
        tree = s.compositing_node_group
        for n in list(tree.nodes):
            if n.bl_idname == "CompositorNodeOutputFile":
                tree.nodes.remove(n)
        dest = args.output_dir / mode
        dest.mkdir()
        report = {"mode": mode}
        if mode == "off":
            for obj in s.objects:
                if obj.type == "MESH" and obj.modifiers.get("mmd_edge_preview"):
                    obj.modifiers["mmd_edge_preview"].show_render = False
        elif mode == "ink":
            report.update(apply_outlines(s, settings))
        layer = s.view_layers[0]
        layer.use_pass_cryptomatte_material = True
        layer.update_render_passes()
        crypto = tree.nodes.new("CompositorNodeCryptomatteV2")
        crypto.source = "RENDER"
        crypto.scene = s
        crypto.layer_name = layer.name + ".CryptoMaterial"
        crypto.matte_id = ",".join(
            m.name
            for m in bpy.data.materials
            if m.name.startswith("mmd_edge.") and m.name != "mmd_edge.disabled"
        )
        output_file(
            tree, dest / "diagnostics", "outline", crypto.outputs["Matte"], False
        )
        s.render.resolution_percentage = 50
        s.eevee.taa_render_samples = 48
        s.render.image_settings.media_type = "IMAGE"
        s.render.image_settings.file_format = "PNG"
        for frame in [421, 601]:
            s.frame_set(frame)
            s.render.filepath = str(dest / f"frame-{frame:04d}.png")
            bpy.ops.render.render(write_still=True)
        if mode == "ink":
            bpy.ops.wm.save_as_mainfile(filepath=str(dest / "surface-ink-study.blend"))
        (dest / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        reports.append(report)
        print("OUTLINE_VARIANT_OK", mode, flush=True)
    (args.output_dir / "outline-report.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
