"""Refine the NPC SDF mapping and shadow cost before the 5-second render."""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from genshin_material_adapt import own_face_factor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--face-map", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    scene.frame_set(4200)
    mat = next(
        m
        for m in bpy.data.materials
        if m.get("performer_id") == "aksiniya"
        and m.get("source_mmd_material_name") == "颜"
    )
    controller = bpy.data.objects["Genshin study | head axes | aksiniya"]
    fac = own_face_factor(mat.node_tree, controller, args.face_map)
    ramp = mat.node_tree.nodes["Look v3 | Soft toon bands"]
    mat.node_tree.links.new(fac, ramp.inputs[0])
    palette = [(0.87, 0.79, 0.85, 1), (1.0, 0.99, 1.01, 1), (1.04, 1.02, 1.04, 1)]
    for i, element in enumerate(ramp.color_ramp.elements):
        element.color = palette[min(i, 2)]
    for material in bpy.data.materials:
        if not material.node_tree:
            continue
        node = material.node_tree.nodes.get("Genshin study | supplied hair MatCap")
        if node:
            node.inputs["高光明暗度"].default_value = 0.025
    shadow_lights = []
    for obj in scene.objects:
        if obj.type != "LIGHT" or obj.hide_render:
            continue
        if obj.data.type == "POINT" or obj.name.endswith((" | fill", " | rim")):
            obj.data.use_shadow = False
        elif obj.name.startswith("Reference | "):
            obj.data.use_shadow = "left window key" in obj.name
        if obj.data.use_shadow:
            shadow_lights.append(obj.name)
    scene.eevee.shadow_ray_count = 1
    bpy.ops.file.pack_all()
    project = args.output_dir / "Franken_Duet_Reference_Genshin.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    timings = []
    for frame in [4200, 4420]:
        scene.frame_set(frame)
        scene.render.filepath = str(args.output_dir / f"preview-{frame}.png")
        start = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        timings.append({"frame": frame, "seconds": time.perf_counter() - start})
    report = {
        "project": str(project),
        "face_change": "NPC supplied FaceLightmap used directly; removed mismatched generic avatar eye/nose correction",
        "hair_matcap_strength": 0.025,
        "shadow_lights": shadow_lights,
        "point_light_shadows": False,
        "screen_reflections_retained": scene.eevee.use_raytracing,
        "timings": timings,
    }
    (args.output_dir / "refinement-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("REFERENCE_DUET_REFINED", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
