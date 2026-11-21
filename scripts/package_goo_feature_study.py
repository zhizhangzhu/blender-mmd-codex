"""Collect existing isolated research evidence; does not load Blender or production media."""

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = Path("D:/codex/output/Goo-MME-Feature-Study-2026-11-16")
TEMP = Path("D:/codex/temp/Goo-MME-Feature-Study-2026-11-16")
GUIDE = "GOO_FEATURES_AND_MME_MECHANISMS.md"
LEDGER = "GOO_FEATURE_MME_MECHANISMS_2026_11_16.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


inventories = {
    name: read(TEMP / filename)
    for name, filename in (
        ("goo52", "goo52-rna.json"),
        ("blender52", "blender52-rna.json"),
        ("goo43", "goo43-rna.json"),
    )
}
extra = sorted(
    set(inventories["goo52"]["node_types"])
    - set(inventories["blender52"]["node_types"])
)
assert len(extra) == 13
assert set(extra) <= set(inventories["goo43"]["node_types"])
matrix = {
    "runtimes": {
        name: {key: value[key] for key in ("binary", "version", "build_hash")}
        | {"shader_node_count": len(value["node_types"])}
        for name, value in inventories.items()
    },
    "additional_nodes": {
        name: {
            key: inventories["goo52"]["node_types"][name][key]
            for key in ("label", "inputs", "outputs")
        }
        | {"present_in_local_goo43": True}
        for name in extra
    },
    "additional_material_properties": sorted(
        set(inventories["goo52"]["material"])
        - set(inventories["blender52"]["material"])
    ),
    "limits": "RNA existence is not complete rendering compatibility; Blender patch versions differ",
}
reports = {
    path.parent.name: read(path) for path in sorted(OUT.glob("*/measurements.json"))
}
assert len(reports) == 10
assert sum(len(report["results"]) for report in reports.values()) == 28


def roi(case, label):
    return reports[case]["results"][label]["ground_origin_mean"]


checks = {
    "shadow_id_off_both_dark": roi("shadows", "shadow_id_off") == [0, 0, 0],
    "shadow_external_cast_only": roi("shadows", "shadow_external") == [0, 1, 0],
    "shadow_same_object_self_only": roi("shadows", "shadow_same_object") == [1, 0, 0],
    "screenspace_global_switch_alone_black": roi("screen_depth", "screen_global_only")
    == [0, 0, 0],
    "screenspace_both_switches_positive": sum(
        roi("screen_depth", "screen_color_enabled")
    )
    > 0.99,
    "screenspace_linked_position_changes_sample": roi("screen_depth", "screen_shifted")
    == [0, 0, 1],
    "depth_unlinked_default_ignored": roi("set_depth", "depth_moved_behind")
    == [0, 0, 1],
    "depth_linked_input_changes_occlusion": roi(
        "set_depth_linked", "depth_moved_behind"
    )
    == [1, 0, 0],
    "diffuse_unshadowed_but_cast_changes": roi("signals", "signals_power1")[1]
    == roi("signals", "signals_occluded")[1]
    and roi("signals", "signals_occluded")[2] == 0,
    "diffuse_preserves_hdr": roi("signals", "signals_power4")[1] > 1,
    "half_lambert_unchanged_by_power_in_this_setup": roi("signals", "signals_power1")[0]
    == roi("signals", "signals_power4")[0],
    "light_info_changes_without_manual_recompile": roi("light_info", "light_info_2")[0]
    == 4,
    "curvature_nonzero_small_signal": 0
    < reports["curvature"]["results"]["curvature_raw"]["rgb_max"]
    < 0.002,
}
reopen = read(OUT / "reopen-verification.json")
checks["one_saved_study_reopened"] = reopen["passed"]
assert all(checks.values()), checks
pngs = sorted(OUT.glob("*/*.png"))
blends = sorted(OUT.glob("*/*.blend"))
assert len(pngs) == 28 and len(blends) == 4
assert all(
    Path(item["linear_exr"]).is_file()
    for report in reports.values()
    for item in report["results"].values()
)
summary = {
    "date": "2026-11-16",
    "scope": "Incremental external reading and factory-only Goo experiments",
    "png_render_count": len(pngs),
    "saved_study_blends": [str(path) for path in blends],
    "suites": list(reports),
    "numeric_controls": checks,
    "reports": reports,
    "reopen": reopen,
    "production_loaded": False,
    "production_modified": False,
    "production_video_qa_performed": False,
    "limits": "Primitive scenes; no new character/volume/MME execution or production temporal validation. Only Screenspace blend reopened.",
}
release = "https://github.com/BeamManP/BeamMan-MME-Archive/releases/download/"
urls = {
    "GodRay_v2_5.zip": release + "BeamMan2/BeamMan2_33_GodRay_v2_5_32_64_MMM.zip",
    "GodRay_Marching_v1_0_2.zip": release
    + "BeamMan3/BeamMan3_23_GodRay_Marching_v1_0_2.zip",
    "PostFog.zip": release + "BeamMan/BeamMan_35_PostFog.zip",
    "DropShadow_0_3.zip": release + "BeamMan2/BeamMan2_4_DropShadow_0_3.zip",
    "NewToon_v1_0.zip": release + "BeamMan/BeamMan_197_NewToon_v1_0.zip",
    "HAToon2_r14.zip": "https://sorairo.pictures/3dcg/mme-effects/hatoon2/",
}
archives = read(TEMP / "archive-index.json")
for entry in archives:
    entry["source_url"] = urls[entry["archive"]]
    entry["downloaded_this_round"] = entry["archive"] != "HAToon2_r14.zip"
source_base = "https://github.com/NaMgAl-Studio/goo-engine-5.2.0/blob/main/"
source_paths = [
    "README.md",
    "source/blender/draw/engines/eevee/shaders/eevee_nodetree_lib.bsl.hh",
    "source/blender/draw/engines/eevee/shaders/eevee_forward_lib.bsl.hh",
    "source/blender/nodes/shader/nodes/node_shader_curvature.cc",
    "source/blender/nodes/shader/nodes/node_shader_light_info.cc",
    "source/blender/nodes/shader/nodes/node_shader_set_depth.cc",
    "source/blender/gpu/shaders/material/gpu_shader_material_curvature.glsl",
    "source/blender/gpu/shaders/material/gpu_shader_material_screenspace_info.glsl",
    "source/blender/gpu/shaders/material/gpu_shader_material_set_depth.glsl",
    "source/blender/gpu/shaders/material/gpu_shader_material_light_info.glsl",
]
ledger = {
    "date": "2026-11-16",
    "guide": "docs/" + GUIDE,
    "previous_ledger": "docs/research/MME_DEEP_STUDY_2026_11_16.json",
    "incremental_not_all_49_authors_mastered": True,
    "goo_sources": [source_base + path for path in source_paths],
    "original_goo": "https://github.com/dillongoostudios/goo-engine/blob/goo-engine-main/README.md",
    "source_read_scope": {
        "README": "Original Goo introduction and community README read",
        "nodetree": "Curvature 353-416; Screenspace 417-459; Shader Info 464-529; targeted subsequent raycast definitions",
        "forward": "Targeted hl computation, light accumulation and output; not all 21 KB read",
        "node_and_glsl": "Listed short Curvature, Light Info, Set Depth and GLSL bridge implementations read; Shader Info interface revisited",
        "source_binary_commit_lock": "Unresolved: local build short SHA not found by GitHub fetch; current main code is supporting explanation, runtime experiments are separate evidence",
    },
    "author_distribution": [
        "https://w.atwiki.jp/beamman/",
        "https://beammanp.github.io/BeamMan-MME-Archive/",
        "https://github.com/BeamManP/BeamMan-MME-Archive/blob/main/data.json",
    ],
    "archives": archives,
    "mme_read_scope": {
        "GodRay_v2_5": "13-line usage; directional radial blur 148-185, Gaussian and composite portions; not every declaration",
        "GodRay_Marching": "25-line usage; constants; 338-421 ray march, visibility and final additive/multiplicative composite; selected filters",
        "PostFog": "Both 3-line usages; DrawHeight/DrawZ 35-61; HeightFog 84-101 and ZFog 83-91",
        "DropShadow": "19-line readme; fx 122-135, 139-151, 157-191 and technique passages; duplicate pattern variants not reread",
        "NewToon": "12-line usage; 339-419 shading core and targeted standard Toon/edge expressions; not full619 lines",
        "HAToon2": "Previously cached archive; newly decoded .hlsl; HACore 501-577 incl. light accumulation, not full generator nor all622 lines",
        "msToonCoordinator": "Prior cache Shade.fx 350-510; Gaussian mask, HSY boundary, threshold and final Alpha; selected common code; no MMD execution",
    },
    "failed_source": "HgSpot Seesaa author page timed out; no HgSpot archive obtained and no new claim based on unseen page",
    "experiment_output": str(OUT),
    "feature_matrix": str(OUT / "feature-matrix.json"),
    "summary": str(OUT / "study-summary.json"),
    "production_modified": False,
    "third_party_full_text_redistributed": False,
}
write_new(OUT / "feature-matrix.json", matrix)
write_new(OUT / "study-summary.json", summary)
write_new(REPO / "docs/research" / LEDGER, ledger)
write_new(OUT / "source-ledger.json", ledger)
guide = (REPO / "docs" / GUIDE).read_text(encoding="utf-8")
guide = guide.replace(
    "(research/" + LEDGER + ")",
    "(source-ledger.json)",
)
guide = guide.replace(
    "(MME_TO_GOO_LIGHTING_STUDY.md)",
    "(" + (REPO / "docs/MME_TO_GOO_LIGHTING_STUDY.md").as_posix() + ")",
)
guide = guide.replace("(../scripts/", "(" + (REPO / "scripts").as_posix() + "/")
with (OUT / "学习笔记.md").open("x", encoding="utf-8") as stream:
    stream.write(guide)
with (OUT / "README.md").open("x", encoding="utf-8") as stream:
    stream.write(
        "# Goo / MME 独立研究\n\n[学习笔记](学习笔记.md) · [节点对照](feature-matrix.json) · [实测汇总](study-summary.json)\n\n"
    )
    stream.write(
        "28 张机制图、4 个研究工程；未改生产工程或视频。Screenspace 工程独立重开与线性原图差值为零，其余工程只保存。\n\n"
    )
    for case, report in reports.items():
        stream.write(f"- {case}：[数值报告]({case}/measurements.json)\n")
        for label in report["results"]:
            stream.write(f"  - [{label}]({case}/{label}.png)\n")
state_path = REPO / "catalog/current_state.json"
state = read(state_path)
state["latest_learning"] = {
    "date": "2026-11-16",
    "topic": "Goo vs Blender features and incremental MME source mechanisms",
    "guide": "docs/" + GUIDE,
    "ledger": "docs/research/" + LEDGER,
    "output": str(OUT),
    "runtimes_inventoried": 3,
    "additional_shader_node_types": 13,
    "primitive_experiment_renders": 28,
    "new_author_mme_packages": 5,
    "production_modified": False,
    "production_video_qa_performed": False,
}
state_path.write_text(
    json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
library_path = REPO / "catalog/library.json"
library = read(library_path)
group = next(item for item in library["knowledge_groups"] if item["id"] == "render")
assert GUIDE not in group["docs"]
group["docs"].insert(0, GUIDE)
library_path.write_text(
    json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "controls": checks,
            "pngs": len(pngs),
            "blends": len(blends),
            "guide_sha256": hashlib.sha256(
                (OUT / "学习笔记.md").read_bytes()
            ).hexdigest(),
        },
        ensure_ascii=False,
        indent=2,
    )
)
