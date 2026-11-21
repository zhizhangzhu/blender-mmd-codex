"""Validate and register only the completed clean-character, no-arc five seconds.

--dry-run is entirely read-only, including previews, temp folders and catalog.
Use --print-contract to list the required manual/coverage fields and report
paths. No evidence, approval, listening result or image review is invented.
"""

import argparse
import binascii
import copy
import hashlib
import json
import math
import re
import shutil
import struct
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
from review_video_color import CONTRACT

REPO = Path(__file__).resolve().parents[1]
IDENTITY = "duet-clean-game-v1"
DEFAULT_ROOT = Path("D:/codex/output/MMD-Clean-Game-Characters-v1")
DEFAULT_CACHE = Path("D:/codex/temp/MMD-Clean-Game-Characters-v1/final-cache")
BASELINE = Path("D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1")
MASTER_SHA = "0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4"
SOURCE_SHA = "f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692"
MATERIAL_SHA = "8425c1827fd296fe19e17225e5e1e748de249bf11cae25ff888c6b010242f993"
PROOF_SHA = {
    "production-v1/master-verification.json": "e4b658fb6a4e9d7132ea6207d732ba8e3282df8f2bd1045311f55f4835f8cb23",
    "production-v2/master-verification.json": "37a183d210a010c800d783dd76f64f0c191c1c13d8491fea467959ec71cf24c0",
}
FRAMES = list(range(4140, 4440))
CASES = ("head-turn", "key-orbit", "camera-orbit")
STRIP_INDICES = [0, 4, 9, 14, 19, 23]
DOCS = ("CLEAN_GAME_CHARACTER_REFINEMENT.md", "CREDITS_AKSINIYA_IKHOR.md")
RESEARCH = (
    "FEMALE_CLEAN_NPR_REFERENCE_2026_11_14.json",
    "IKHOR_PRINCE_REFERENCE_2026_11_14.json",
    "GRAY_EYED_PRIMORDIAL_MODEL_2026_11_14.json",
    "PRIMORDIAL_ONE_BACKGROUND_MODEL_2026_11_14.json",
)
LICENSES = ("festivities-GPL-3.0.txt", "festivities-sources.json", "Ikhor-RM.txt")
CAP = "captions-5s/"
REQUIRED_REPORTS = (
    "production-v1/preparation.json",
    "production-v1/master-verification.json",
    "production-v2/arc-removal.json",
    "production-v2/master-verification.json",
    "diagnostics/diagnostic-records.json",
    "diagnostic-review/diagnostics-verification.json",
    "native-5s/chunks.json",
    "native-5s/sample-report.json",
    "native-5s/video-qa/video-verification.json",
    "native-5s/audio-verification.json",
    "native-5s/seam-qa/seam-verification.json",
    CAP + "caption-layer-audit.json",
    CAP + "resolved-caption-profile.json",
    CAP + "video-qa/video-verification.json",
    CAP + "bare-video-qa/video-verification.json",
    CAP + "video-qa-audio.json",
    CAP + "bare-video-qa-audio.json",
    CAP + "color-verification.json",
    CAP + "seam-qa/seam-verification.json",
    CAP + "bare-seam-qa/seam-verification.json",
    CAP + "color-roundtrip/color-audit.json",
    "caption-coverage-final.json",
    "manual-review.json",
)
NO_PASSED_FIELD = {
    "production-v1/preparation.json",
    "production-v2/arc-removal.json",
    "diagnostics/diagnostic-records.json",
    "native-5s/chunks.json",
    "native-5s/sample-report.json",
    CAP + "resolved-caption-profile.json",
    CAP + "color-roundtrip/color-audit.json",
}
_HASHES = {}


def need(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path, fresh=False):
    path = Path(path).resolve(strict=True)
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns)
    if fresh or key not in _HASHES:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1048576), b""):
                digest.update(block)
        _HASHES[key] = digest.hexdigest()
    return _HASHES[key]


def same_path(a, b):
    return bool(a) and Path(a).resolve() == Path(b).resolve()


def finite(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def png_header(path, color_type):
    with path.open("rb") as stream:
        header = stream.read(33)
    need(
        len(header) == 33
        and header[:8] == b"\x89PNG\r\n\x1a\n"
        and header[12:16] == b"IHDR",
        f"Invalid PNG header: {path}",
    )
    need(
        struct.unpack(">I", header[29:33])[0] == binascii.crc32(header[12:29]),
        f"Invalid PNG IHDR CRC: {path}",
    )
    width, height, depth, mode, compression, filtering, _ = struct.unpack(
        ">IIBBBBB", header[16:29]
    )
    need(
        (width, height, depth, mode, compression, filtering)
        == (1920, 1080, 16, color_type, 0, 0),
        f"Unexpected PNG16 dimensions/type: {path}",
    )


def validate_video(report, movie, root):
    need(
        report.get("passed") is True
        and same_path(report.get("video"), movie)
        and report.get("sha256") == sha(movie),
        f"Video QA not bound to actual movie: {movie}",
    )
    need(
        report.get("width") == 1920
        and report.get("height") == 1080
        and abs(report.get("fps", 0) - 60) < 0.01
        and report.get("declared_frames") == report.get("decoded_frames") == 300
        and abs(report.get("seconds", 0) - 5) < 0.02
        and {"vide", "soun"} <= set(report.get("mp4_stream_types", [])),
        f"Incomplete video decode: {movie}",
    )
    need(
        len(report.get("representative_frames", [])) == 12,
        f"Missing decoded representative frame inventory: {movie}",
    )
    qa = root / (
        "native-5s/video-qa"
        if movie.parent.name == "native-5s"
        else "captions-5s/video-qa"
        if "Wedding_REVIEW" in movie.name
        else "captions-5s/bare-video-qa"
    )
    need(
        all((qa / f).is_file() for f in report["representative_frames"])
        and (qa / "video-contact-sheet.jpg").is_file(),
        f"Missing decoded QA images: {qa}",
    )


def validate_audio(report, movie):
    need(
        report.get("passed") is True and same_path(report.get("video"), movie),
        f"Audio report points elsewhere: {movie}",
    )
    need(
        report.get("sample_rate") == 48000
        and report.get("channels") == 2
        and abs(report.get("seconds", 0) - 5) <= 0.2
        and report.get("expected_seconds") == 5
        and report.get("nonzero_samples", 0) > 1000
        and finite(report.get("rms"))
        and report["rms"] > 0.0001
        and finite(report.get("peak"))
        and 0 < report["peak"] <= 1,
        f"Invalid decoded stereo audio: {movie}",
    )


def validate_seams(report, movie, boundaries, sheet):
    rows = report.get("boundaries", [])
    need(
        report.get("passed") is True
        and same_path(report.get("video"), movie)
        and [r.get("boundary") for r in rows] == boundaries
        and sheet.is_file(),
        f"Wrong/missing seam QA: {movie}",
    )
    need(
        all(
            r.get("no_large_jump") is True
            and r.get("frames") == list(range(b - 2, b + 3))
            for r, b in zip(rows, boundaries)
        ),
        f"Incomplete seam range: {movie}",
    )


def contract():
    return {
        "required_reports": REQUIRED_REPORTS,
        "qa_report_sha256": "All required reports except manual-review.json, keyed by exact relative path",
        "manual_review": {
            "passed": True,
            "project_sha256": MASTER_SHA,
            "movie_sha256": "actual",
            "bare_sha256": "actual",
            "qa_report_sha256": "Map every REQUIRED_REPORTS relative path except manual-review.json to its actual SHA256",
            "full_song_complete": False,
            "user_art_approval": False,
            "final_beauty_sampled": True,
            "caption_boundaries_sampled": True,
            "repaired_wrist_windows_sampled": True,
            "beauty_sampled_frames": "At least 12 unique global frames spread over all three thirds of 4140..4439",
            "caption_boundary_frames": "All global boundary-3..boundary+4 at 4161,4244,4270,4310 (32 unique frames)",
            "wrist_sampled_frames": [4186, 4190, 4218, 4220, 4225, 4317, 4318],
            "diagnostics": {
                "project_sha256": MASTER_SHA,
                "records_sha256": "actual",
                "verification_sha256": "actual",
                "reviewed_cases": CASES,
                "sampled_indices": STRIP_INDICES,
                "motion_blur_disabled": True,
            },
            "render_provenance": {
                "project_sha256": MASTER_SHA,
                "sample_report_sha256": "actual",
                "chunks_sha256": "actual",
                "caption_cache": str(DEFAULT_CACHE),
                "old_beauty_reused": False,
                "old_actor_reused": False,
            },
            "audio": {
                "source": "fixed original vocal FLAC",
                "source_sha256": "actual",
                "audio_start_seconds": 4139 / 60,
                "gain": 0.87,
                "source_track_confirmed": True,
                "verification_method": "actual method, not an invented result",
            },
            "observations": ["Actual original observations"],
            "unresolved_issues": ["Actual limitations; an empty list is permitted"],
        },
        "coverage_final": {
            "passed": True,
            "project_sha256": MASTER_SHA,
            "cache": str(DEFAULT_CACHE),
            "frames": 300,
            "source_frames": "Exact full list 4140..4439",
            "roi_source": "actual inherited positive ROI report",
            "roi_source_sha256": "actual",
            "pose_source_sha256": SOURCE_SHA,
            "static_inheritance_reports": "Two path/sha256 records, accepted 321 and 26 reports",
            "records": "300 {frame,sha256:actual actor PNG,regions:each actor x head/body with roi_xyxy,mean,minimum_mean,passed}",
            "failures": [],
        },
    }


def validate(root, cache):
    project = root / "production-v2/Franken_Duet_Clean_Game.blend"
    movie = root / (CAP + "Franken_Duet_5s_CleanGame_Wedding_REVIEW.mp4")
    bare = root / (CAP + "Franken_Duet_5s_CleanGame_NoCaptions.mp4")
    expected_files = [
        project,
        movie,
        bare,
        *(root / p for p in REQUIRED_REPORTS),
        *(REPO / "docs" / p for p in DOCS),
        *(REPO / "docs/research" / p for p in RESEARCH),
        *(BASELINE / "licenses" / p for p in LICENSES),
    ]
    missing = [str(p) for p in expected_files if not p.is_file()]
    need(not missing, "Missing required artifacts:\n" + "\n".join(missing))
    need(
        not (root / "delivery.json").exists(),
        "delivery.json already exists; registration is not an overwrite operation",
    )
    need(sha(project) == MASTER_SHA, "Final project is not the pinned arc-hidden v2")
    evidence = {p: read(root / p) for p in REQUIRED_REPORTS}
    evidence_hashes = {p: sha(root / p) for p in REQUIRED_REPORTS}
    for name, data in evidence.items():
        if name not in NO_PASSED_FIELD:
            need(
                data.get("passed") is True
                and not data.get("failed_checks")
                and not data.get("errors"),
                f"Failed evidence: {name}",
            )
    for name, expected in PROOF_SHA.items():
        need(
            evidence_hashes[name] == expected,
            "Changed fixed independent proof: " + name,
        )
    material, delta = (
        evidence["production-v1/master-verification.json"],
        evidence["production-v2/master-verification.json"],
    )
    need(
        material.get("project_sha256") == MATERIAL_SHA
        and material.get("source_sha256") == SOURCE_SHA
        and len(material.get("checks", [])) == 321
        and all(c["passed"] is True for c in material["checks"])
        and material.get("beauty_300_reuse_eligible") is False,
        "Invalid 321-check material lineage",
    )
    need(
        delta.get("project_sha256") == MASTER_SHA
        and delta.get("source_sha256") == MATERIAL_SHA
        and len(delta.get("checks", [])) == 26
        and all(c["passed"] is True for c in delta["checks"])
        and delta.get("beauty_300_reuse_eligible") is False
        and delta.get("arcs_hidden") is True,
        "Invalid 26-check arc-hidden lineage",
    )
    inherited_static = delta["inherited_full_static_capture"]
    need(
        sha(inherited_static["path"]) == inherited_static["sha256"]
        and sha(inherited_static["script"]) == inherited_static["script_sha256"],
        "Missing full-static supplemental evidence",
    )
    prep = evidence["production-v1/preparation.json"]
    need(
        prep.get("source_sha256") == SOURCE_SHA
        and prep.get("project_sha256") == MATERIAL_SHA
        and sha(prep["source"]) == SOURCE_SHA,
        "Wrong original v7 source/preparation",
    )
    for actor in ("aksiniya", "ikhor"):
        for kind in ("profiles", "modules"):
            item = prep[kind][actor]
            need(sha(item["path"]) == item["sha256"], f"Changed frozen {actor} {kind}")
        need(
            read(prep["profiles"][actor]["path"]) == prep["profiles"][actor]["data"],
            "Profile differs from saved applied parameters",
        )
    manual = evidence["manual-review.json"]
    need(
        manual.get("project_sha256") == MASTER_SHA
        and manual.get("movie_sha256") == sha(movie)
        and manual.get("bare_sha256") == sha(bare)
        and manual.get("user_art_approval") is False
        and manual.get("full_song_complete") is False,
        "Manual review is unbound or claims art/full-song approval",
    )
    need(
        all(
            manual.get("qa_report_sha256", {}).get(p) == h
            for p, h in evidence_hashes.items()
            if p != "manual-review.json"
        ),
        "Manual QA report hashes are missing/stale; use --print-contract",
    )
    for key in (
        "final_beauty_sampled",
        "caption_boundaries_sampled",
        "repaired_wrist_windows_sampled",
    ):
        need(manual.get(key) is True, "Incomplete actual manual review: " + key)
    sampled = manual.get("beauty_sampled_frames", [])
    need(
        len(sampled) >= 12
        and len(sampled) == len(set(sampled))
        and set(sampled) <= set(FRAMES)
        and all(
            any(first <= f <= last for f in sampled)
            for first, last in ((4140, 4239), (4240, 4339), (4340, 4439))
        ),
        "Beauty review must contain 12 distinct global frames spread over the whole segment",
    )
    need(
        {4186, 4190, 4218, 4220, 4225, 4317, 4318}
        <= set(manual.get("wrist_sampled_frames", [])),
        "Missing actual repaired-wrist window samples",
    )
    need(
        isinstance(manual.get("observations"), list)
        and any(str(v).strip() for v in manual["observations"])
        and isinstance(manual.get("unresolved_issues"), list),
        "Actual observations/limitations must be explicit",
    )
    diagnostic = evidence["diagnostic-review/diagnostics-verification.json"]
    records = evidence["diagnostics/diagnostic-records.json"]
    bind = manual.get("diagnostics", {})
    need(
        bind.get("project_sha256") == MASTER_SHA
        and bind.get("records_sha256")
        == evidence_hashes["diagnostics/diagnostic-records.json"]
        and bind.get("verification_sha256")
        == evidence_hashes["diagnostic-review/diagnostics-verification.json"]
        and set(bind.get("reviewed_cases", [])) == set(CASES)
        and bind.get("sampled_indices") == STRIP_INDICES
        and bind.get("motion_blur_disabled") is True,
        "Diagnostics lack explicit frozen-v2 launch/manual binding",
    )
    need(
        diagnostic.get("neutral") is True
        and records.get("neutral") is True
        and records.get("frames_per_case") == 24
        and records.get("fps") == 24
        and records.get("resolution") == [1280, 720]
        and len(records.get("rendered_records", [])) == 72,
        "Expected the new neutral 72-frame diagnostics",
    )
    need(
        {c["case"] for c in diagnostic["cases"]} == set(CASES), "Wrong diagnostic cases"
    )
    for case in CASES:
        row = next(c for c in diagnostic["cases"] if c["case"] == case)
        local = [r for r in records["rendered_records"] if r["case"] == case]
        need(
            row["decoded_frames"] == row["unique_frames"] == 24
            and row["fps"] == 24
            and row["max_axis_error"] < 0.0001
            and row["sha256"] == sha(root / "diagnostics" / (case + ".mp4"))
            and [r["frame"] for r in local] == list(range(24))
            and all(set(r["actors"]) == {"aksiniya", "ikhor"} for r in local)
            and (root / "diagnostic-review" / (case + "-face-strip.jpg")).is_file(),
            "Incomplete/mismatched diagnostic case " + case,
        )
    chunks = evidence["native-5s/chunks.json"]
    sample = evidence["native-5s/sample-report.json"]
    render = manual.get("render_provenance", {})
    need(
        render.get("project_sha256") == MASTER_SHA
        and render.get("sample_report_sha256")
        == evidence_hashes["native-5s/sample-report.json"]
        and render.get("chunks_sha256") == evidence_hashes["native-5s/chunks.json"]
        and same_path(render.get("caption_cache"), cache)
        and render.get("old_beauty_reused") is False
        and render.get("old_actor_reused") is False,
        "No explicit fresh-v2 render provenance",
    )
    need(
        same_path(chunks.get("source_blend"), project)
        and same_path(chunks.get("caption_cache"), cache)
        and [chunks.get(k) for k in ("width", "height", "fps")] == [1920, 1080, 60],
        "Wrong native render manifest",
    )
    local_cursor, source_cursor, boundaries = 1, 4140, []
    for item in chunks["chunks"]:
        need(
            item.get("reused") is False
            and item["start"] == local_cursor
            and item["source_start"] == source_cursor
            and item["end"] >= item["start"]
            and item["source_end"] - item["source_start"]
            == item["end"] - item["start"],
            "Reused/gapped/overlapping native render chunks are forbidden",
        )
        chunk = Path(item["path"])
        need(
            chunk.is_file()
            and chunk.resolve().parent == (root / "native-5s/chunks").resolve(),
            "Chunk is outside this fresh render",
        )
        progress = read(chunk.with_suffix(".progress.json"))
        need(
            progress.get("complete") is True
            and progress.get("start") == item["source_start"]
            and progress.get("end") == progress.get("last_frame") == item["source_end"],
            "Chunk rendering not complete",
        )
        local_cursor, source_cursor = item["end"] + 1, item["source_end"] + 1
        boundaries.append(item["end"])
    need(
        local_cursor == 301 and source_cursor == 4440,
        "Native chunks do not cover exactly all 300 requested frames",
    )
    boundaries = boundaries[:-1]
    need(
        sample.get("source_frames") == [4140, 4439]
        and sample.get("frames") == 300
        and sample.get("seconds") == 5
        and same_path(sample.get("project"), project)
        and same_path(sample.get("caption_cache_directory"), cache)
        and sample.get("linear_archive_reused_frames_need_separate_validation") is False
        and sample.get("camera_motion_changed") is False
        and sample.get("physics_changed") is False,
        "Wrong/stale/reused native sample",
    )
    native_movie = Path(sample["movie"])
    need(
        native_movie.is_file()
        and native_movie.resolve().parent == (root / "native-5s").resolve(),
        "Native sample movie is outside this render",
    )
    validate_video(
        evidence["native-5s/video-qa/video-verification.json"], native_movie, root
    )
    validate_audio(evidence["native-5s/audio-verification.json"], native_movie)
    validate_seams(
        evidence["native-5s/seam-qa/seam-verification.json"],
        native_movie,
        boundaries,
        root / "native-5s/seam-qa/seam-contact-sheet.jpg",
    )
    for qa, media, audio_qa, seam_qa in (
        ("video-qa", movie, "video-qa-audio.json", "seam-qa"),
        ("bare-video-qa", bare, "bare-video-qa-audio.json", "bare-seam-qa"),
    ):
        validate_video(evidence[CAP + qa + "/video-verification.json"], media, root)
        validate_audio(evidence[CAP + audio_qa], media)
        validate_seams(
            evidence[CAP + seam_qa + "/seam-verification.json"],
            media,
            boundaries,
            root / CAP / seam_qa / "seam-contact-sheet.jpg",
        )
    profile = read(REPO / "presets/typography/duet-blue-gold-wedding-v1.json")
    caption = evidence[CAP + "caption-layer-audit.json"]
    need(
        caption.get("profile")
        == profile
        == evidence[CAP + "resolved-caption-profile.json"]
        and caption.get("output_color_contract") == CONTRACT
        and same_path(caption.get("cache"), cache)
        and caption.get("size") == [1920, 1080]
        and caption.get("frames") == 300
        and caption.get("preview_only") is False
        and caption.get("all_behind_opaque_actor_pixels_protected") is True
        and caption.get("front_uses_no_face_or_character_mask") is True,
        "Incomplete or altered caption profile/layer audit",
    )
    need(
        profile["render_start_frame"] == 4140
        and profile["render_frames"] == 300
        and profile["source_start_frame"] == 4141
        and [c["start_frame"] for c in profile["cues"]]
        == [4141, 4162, 4245, 4271, 4311],
        "Caption source boundaries changed",
    )
    caption_rows = caption["records"]
    need(
        [r["global_frame"] for r in caption_rows] == FRAMES,
        "Caption audit does not contain all 300 native frames",
    )
    front, behind = 0, 0
    for row in caption_rows:
        typography = row["global_frame"] + 1
        cue = next(
            c
            for c in profile["cues"]
            if c["start_frame"] <= typography < c["end_frame"]
        )
        need(
            row["typography_frame"] == typography
            and (row["group"], row["order"], row["key_mode"])
            == (cue["id"], cue["order"], cue["key_mode"]),
            "Caption per-frame cue mismatch",
        )
        if row["order"] == "behind":
            behind += 1
            need(
                finite(row["protected_error_before_encoding"])
                and row["protected_error_before_encoding"] < 0.00001,
                "Rear captions modify opaque actors",
            )
        elif row["changed_opaque_actor_pixels"] > 100:
            front += 1
    need(
        behind == 87
        and front > 0
        and caption["front_frames_with_character_overlap"] == front
        and caption["group_order_sets"]
        == {c["id"]: [c["order"]] for c in profile["cues"]},
        "Caption whole-group ordering not demonstrated",
    )
    boundary_frames = {
        f
        for c in profile["cues"][1:]
        for f in range(c["start_frame"] - 4, c["start_frame"] + 4)
    }
    need(
        len(boundary_frames) == 32
        and boundary_frames <= set(manual.get("caption_boundary_frames", [])),
        "Missing 32 consecutive global caption-boundary samples",
    )
    colors = evidence[CAP + "color-verification.json"]
    need(colors.get("contract") == CONTRACT, "Wrong final SDR review color contract")
    for media in (movie, bare):
        matching = [r for r in colors["videos"] if same_path(r.get("video"), media)]
        need(
            len(matching) == 1
            and matching[0]["sha256"] == sha(media)
            and matching[0]["decoded_color_metadata"],
            "Final mux color metadata is unbound",
        )
        need(
            all(
                all(
                    token in line
                    for token in (
                        "color_range:tv",
                        "color_space:bt709",
                        "color_primaries:bt709",
                        "color_trc:iec61966-2-1",
                    )
                )
                for line in matching[0]["decoded_color_metadata"]
            ),
            "Decoded final color tags are wrong",
        )
    color_audit = evidence[CAP + "color-roundtrip/color-audit.json"]
    need(
        same_path(color_audit.get("video"), movie)
        and color_audit.get("best_reconstruction_matrix") == "bt709"
        and color_audit.get("reference_global_frame") == 4250
        and color_audit.get("reference_typography_frame") == 4251,
        "Actual-pixel color roundtrip does not identify the intended 709 matrix",
    )
    audio_profile = read(REPO / "presets/projects/franken-duet-full-v1.json")["audio"]
    audio = manual.get("audio", {})
    need(
        same_path(audio.get("source"), audio_profile["bgm"])
        and Path(audio_profile["bgm"]).suffix.lower() == ".flac"
        and sha(audio_profile["bgm"])
        == audio.get("source_sha256")
        == audio_profile["bgm_sha256"]
        and abs(audio.get("audio_start_seconds", 0) - 4139 / 60) < 1e-8
        and audio.get("gain") == 0.87
        and audio.get("source_track_confirmed") is True
        and bool(str(audio.get("verification_method", "")).strip()),
        "Selected original vocal FLAC provenance is incomplete",
    )
    cache_layers = {}
    for layer, mode in (("beauty", 2), ("actor", 0)):
        files = sorted((cache / layer).glob("*.png"))
        need(
            {p.name for p in files} == {f"frame_{f:04d}{layer}.png" for f in FRAMES},
            "Cache frame set is incomplete: " + layer,
        )
        cache_layers[layer] = []
        for p in files:
            png_header(p, mode)
            cache_layers[layer].append({"file": p.name, "sha256": sha(p)})
    coverage = evidence["caption-coverage-final.json"]
    need(
        coverage.get("project_sha256") == MASTER_SHA
        and same_path(coverage.get("cache"), cache)
        and coverage.get("frames") == 300
        and coverage.get("source_frames") == FRAMES
        and not coverage.get("failures")
        and coverage.get("pose_source_sha256") == SOURCE_SHA
        and sha(coverage["roi_source"]) == coverage.get("roi_source_sha256"),
        "Coverage is stale, incomplete or unbound",
    )
    roi_source = read(coverage["roi_source"])
    need(
        roi_source.get("passed") is True
        and roi_source.get("tested_frames") == 300
        and roi_source.get("project_sha256") == SOURCE_SHA
        and roi_source.get("frame_range") == [4140, 4439],
        "Inherited ROI source is not the accepted complete v7 positive audit",
    )
    inherit = {
        str(Path(p["path"]).resolve()): p["sha256"]
        for p in coverage["static_inheritance_reports"]
    }
    need(
        inherit == {str((root / p).resolve()): h for p, h in PROOF_SHA.items()},
        "Coverage does not bind both accepted static proofs",
    )
    need(
        [r["frame"] for r in coverage["records"]] == FRAMES,
        "Coverage lacks every actual actor PNG",
    )
    for row in coverage["records"]:
        need(
            row["sha256"]
            == sha(cache / "actor" / f"frame_{row['frame']:04d}actor.png"),
            "Coverage actor PNG bytes changed",
        )
        regions = row["regions"]
        need(
            len(regions) == 4
            and {(r["actor"], r["region"]) for r in regions}
            == {(a, r) for a in ("aksiniya", "ikhor") for r in ("head", "body")},
            "Coverage misses a person/region",
        )
        need(
            all(
                r.get("passed") is True
                and finite(r.get("mean"))
                and finite(r.get("minimum_mean"))
                and 0.05 <= r["minimum_mean"] <= r["mean"] <= 1.00001
                and len(r.get("roi_xyxy", [])) == 4
                for r in regions
            ),
            "A projected actor interior is missing",
        )
    return {
        "project": project,
        "movie": movie,
        "bare": bare,
        "native_movie": native_movie,
        "manual": manual,
        "evidence": evidence,
        "evidence_hashes": evidence_hashes,
        "cache_layers": cache_layers,
        "prep": prep,
        "inherited_static": inherited_static,
        "coverage": coverage,
        "boundaries": boundaries,
    }


def append_unique(items, value):
    if value and value not in items:
        items.append(copy.deepcopy(value))


def package_plan(root, cache, data, date):
    library_path, state_path = (
        REPO / "catalog/library.json",
        REPO / "catalog/current_state.json",
    )
    profile_path = REPO / "presets/projects/franken-duet-full-v1.json"
    registry_hashes = {
        library_path: sha(library_path),
        state_path: sha(state_path),
        profile_path: sha(profile_path),
    }
    library, state = read(library_path), read(state_path)
    profile = read(profile_path)
    old_profile = copy.deepcopy(profile)
    recipe_path = REPO / "presets/recipes" / (IDENTITY + ".json")
    need(
        not recipe_path.exists()
        and not any(e["id"] == IDENTITY for e in library["entries"]),
        "This identity is already registered",
    )
    project, movie, bare = data["project"], data["movie"], data["bare"]
    limits = [
        "仅原帧4140–4439、1080p60的五秒；技术通过，美术待猪猪评价，全曲未完成。",
        "两份本地参考各实际检查四张清晰帧，未完整连续观看；作者Shader/MME未知，女性正式角色名与原作者未独立核定。",
        "321项人物材质检查与26项去弧增量检查为两级独立证据；袖修/动作继承4139–4441范围，未新增物理或零碰撞认证。",
        "仅隐藏两道蓝金弧，数据保留可逆；Probe未重烘，内部缓存负载未另作独立认证。",
        "缺失作者自改y1脸图，继续原FaceDiffuse回退；完整体积阴影未开启，可见光束含美术Emission。",
        "旧beauty/actor与旧视频未复用；人工仅覆盖manual-review列明抽样，不称300帧美术逐帧批准或风格达标。",
        *[str(v) for v in data["manual"]["unresolved_issues"]],
    ]
    recipe = {
        "id": IDENTITY,
        "status": "verified-five-second-review-art-pending",
        "project": str(project),
        "project_sha256": MASTER_SHA,
        "source": data["prep"]["source"],
        "source_sha256": SOURCE_SHA,
        "video": str(movie),
        "without_captions_video": str(bare),
        "performers": {"aksiniya": "Full HimeTanaka", "ikhor": "Full HinaSuzuki"},
        "source_frames": [4140, 4439],
        "frames": 300,
        "fps": 60,
        "seconds": 5,
        "resolution": [1920, 1080],
        "caption_cache": str(cache),
        "audio_start_seconds": 4139 / 60,
        "audio_gain": 0.87,
        "character_profiles": [
            "presets/quality/aksiniya-clean-game-v1.json",
            "presets/quality/ikhor-clean-game-v1.json",
        ],
        "project_profile": profile_path.relative_to(REPO).as_posix(),
        "caption_profile": "presets/typography/duet-blue-gold-wedding-v1.json",
        "stage_profile": "presets/stages/hesperides-bold-wedding-v1.json",
        "static_proofs": PROOF_SHA,
        "diagnostics": "diagnostic-review/diagnostics-verification.json",
        "native_manifest": "native-5s/chunks.json",
        "arcs_hidden": True,
        "physics_changed": False,
        "physical_validation_frames": [4139, 4441],
        "old_beauty_reused": False,
        "full_song_complete": False,
        "user_art_approval": False,
        "output_color_contract": CONTRACT,
        "limits": limits,
    }
    old = state.get("latest_review")
    if old:
        for entry in library["entries"]:
            if entry["id"] == old["entry_id"]:
                review = {
                    "status": old.get("art_status"),
                    "as_of": date,
                    "feedback": old.get("user_feedback"),
                    "user_art_approval": old.get("user_art_approval", False),
                }
                if entry.get("art_review") != review:
                    append_unique(
                        entry.setdefault("art_review_history", []),
                        entry.get("art_review"),
                    )
                    entry["art_review"] = review
        append_unique(
            state.setdefault("review_history", []), state.get("previous_review")
        )
        append_unique(state["review_history"], old)
        state["previous_review"] = copy.deepcopy(old)
    append_unique(
        state.setdefault("iteration_history", []), state.get("active_iteration")
    )
    state["latest_review"] = {
        "entry_id": IDENTITY,
        "project": str(project),
        "video": str(movie),
        "sha256": sha(movie),
        "delivery_report": str(root / "delivery.json"),
        "scope": {
            "frames": [4140, 4439],
            "fps": 60,
            "resolution": [1920, 1080],
            "seconds": 5,
            "aspect": "landscape",
        },
        "technical_status": "passed-limited-scope",
        "art_status": "pending",
        "user_art_approval": False,
        "user_feedback": "人物干净明亮NPR与去蓝金光弧五秒已输出；限定技术检查通过，等待猪猪实际美术评价。",
    }
    state["as_of"] = date
    state["current_task"] = (
        "已完成阿克西妮娅＋伊科尔干净明亮人物NPR、去光弧五秒；技术限定通过，美术待评价，不恢复全曲。"
    )
    state["full_song"].update(delivered=False, rendering_now=False)
    state["active_iteration"] = {
        "id": IDENTITY,
        "status": "delivered-limited-scope",
        "user_authorized": True,
        "project": str(project),
        "project_sha256": MASTER_SHA,
        "delivery_report": str(root / "delivery.json"),
        "scope": "4140–4439,1080p60,5s",
        "full_song": False,
        "user_art_approval": False,
        "geometry_collision_certified": False,
        "physics_changed": False,
        "arcs_hidden": True,
        "old_beauty_reused": False,
    }
    hero = root / "review/native-source-4290.png"
    library["entries"].insert(
        0,
        {
            "id": IDENTITY,
            "title": "清透新誓 · 阿克西妮娅 × 伊科尔",
            "subtitle": "独立人物材质适配，保留袖修与指定礼堂，按要求隐藏蓝金光弧。",
            "collection": "CHARACTER / CLEAN NPR",
            "category": "character",
            "family": "genshin",
            "aspect": "landscape",
            "status": "motion",
            "image": str(hero),
            "video": str(movie),
            "diagnostic_video": str(bare),
            "diagnostic_label": "无字幕审片 · 5s",
            "duration": 5,
            "fps": 60,
            "project": str(project),
            "docs": list(DOCS),
            "configs": [
                *recipe["character_profiles"],
                recipe["caption_profile"],
                recipe_path.relative_to(REPO).as_posix(),
            ],
            "look": [
                "保原配色的分区明暗",
                "局部鼻区SDF修订",
                "许可白布中间层",
                "克制亮边与金属反射",
                "去除身后蓝金光弧",
            ],
            "compatibility": "Blender5.2.2 EEVEE；仅绑定本轮已核SHA工程与两角色独立映射。",
            "evidence": [
                "人物材质321项与去弧26项分别验证",
                "最终v2三轴72原生帧",
                "新300原生帧、双人字幕覆盖与两版完整解码/音轨与色彩/接缝",
            ],
            "art_review": {
                "status": "pending",
                "as_of": date,
                "feedback": "等待猪猪实际美术评价",
            },
            "limits": limits,
            "command": "See docs/CLEAN_GAME_CHARACTER_REFINEMENT.md and scripts/package_clean_game_duet.py --print-contract.",
        },
    )
    library["updated"] = date
    for doc in DOCS:
        group = next(
            (g for g in library["knowledge_groups"] if g.get("id") == "render"), None
        )
        if group and not any(
            doc in g.get("docs", []) for g in library["knowledge_groups"]
        ):
            group["docs"].insert(0, doc)
    # Keep the existing full-song target and original full-song v5 history.
    # A completed five-second iteration changes the continuation pointers, not
    # the actor assignment, Full VMDs, camera, audio or original asset contract.
    production_snapshot = {
        key: copy.deepcopy(old_profile[key])
        for key in (
            "production_scene",
            "integration_verification",
            "render_output",
            "production_scene_scope",
            "current_iteration_scope",
            "sample_delivery",
            "status",
        )
        if key in old_profile
    }
    production_snapshot["archived_as_of"] = date
    production_snapshot["superseded_by_recipe"] = recipe_path.relative_to(
        REPO
    ).as_posix()
    append_unique(profile.setdefault("production_history", []), production_snapshot)
    append_unique(
        profile.setdefault("previous_sample_deliveries", []),
        old_profile.get("sample_delivery"),
    )
    profile["production_scene"] = str(project)
    profile["integration_verification"] = str(
        root / "production-v2/master-verification.json"
    )
    profile["render_output"] = str(root / "captions-5s")
    profile["status"] = (
        "Clean-character, arc-hidden five-second review delivered; art pending; full song and full-song physics not delivered"
    )
    profile["current_iteration_scope"] = dict(
        old_profile.get("current_iteration_scope", {}),
        kind="clean-character-materials-and-hidden-wedding-arcs",
        requested_seconds=5,
        source_frames=[4140, 4439],
        fps=60,
        resolution=[1920, 1080],
        sample_output=str(root / "captions-5s"),
        sample_movie=str(movie),
        status="completed and technically verified; user art review pending",
        full_movie="not delivered or rendering",
        arcs_hidden=True,
        physics_changed=False,
    )
    profile["production_scene_scope"] = dict(
        old_profile.get("production_scene_scope", {}),
        delivered_frames=[4140, 4439],
        full_song_physics_ready=False,
        full_song_delivered=False,
        material_and_arc_revision=IDENTITY,
        project_sha256=MASTER_SHA,
    )
    profile["sample_delivery"] = {
        "movie": str(movie),
        "video_sha256": sha(movie),
        "without_captions_video": str(bare),
        "without_captions_sha256": sha(bare),
        "project": str(project),
        "project_sha256": MASTER_SHA,
        "source_frames": [4140, 4439],
        "frames": 300,
        "seconds": 5,
        "fps": 60,
        "resolution": [1920, 1080],
        "camera_motion_changed": False,
        "physics_changed": False,
        "physics_change_scope": "No new physics; inherit the accepted native cloth/sleeve/corrective evidence only within 4139-4441",
        "verified": {
            "video": True,
            "audio": True,
            "seams": True,
            "color": True,
            "caption_coverage": True,
            "neutral_diagnostics": True,
        },
        "delivery_report": str(root / "delivery.json"),
        "recipe": recipe_path.relative_to(REPO).as_posix(),
        "arcs_hidden": True,
        "full_song_complete": False,
        "user_art_approval": False,
    }
    profile["latest_clean_game_project"] = str(project)
    profile["latest_clean_game_review"] = str(movie)
    profile["latest_clean_game_recipe"] = recipe_path.relative_to(REPO).as_posix()
    allowed_profile_updates = {
        "production_scene",
        "integration_verification",
        "render_output",
        "status",
        "current_iteration_scope",
        "production_scene_scope",
        "sample_delivery",
        "production_history",
        "previous_sample_deliveries",
        "latest_clean_game_project",
        "latest_clean_game_review",
        "latest_clean_game_recipe",
    }
    need(
        all(
            profile[key] == value
            for key, value in old_profile.items()
            if key not in allowed_profile_updates
        ),
        "Unexpected project contract change: actors/Full VMDs/audio/camera/full-song target and historical fields must remain exact",
    )
    provenance = {
        "project": str(project),
        "project_sha256": MASTER_SHA,
        "source_frames": [4140, 4439],
        "frames": 300,
        "caption_cache": str(cache),
        "old_beauty_reused": False,
        "old_actor_reused": False,
        "layers": data["cache_layers"],
        "native_manifest_sha256": data["evidence_hashes"]["native-5s/chunks.json"],
    }
    delivery = {
        "id": IDENTITY,
        "project": str(project),
        "project_sha256": MASTER_SHA,
        "source_sha256": SOURCE_SHA,
        "movie": str(movie),
        "movie_sha256": sha(movie),
        "without_captions_video": str(bare),
        "without_captions_sha256": sha(bare),
        "source_frames": [4140, 4439],
        "frames": 300,
        "fps": 60,
        "seconds": 5,
        "resolution": [1920, 1080],
        "performers": ["aksiniya", "ikhor"],
        "reports": {
            p: {"path": str(root / p), "sha256": h}
            for p, h in data["evidence_hashes"].items()
        },
        "manual_review": data["manual"],
        "static_check_levels": {"material_v1": 321, "arc_delta_v2": 26},
        "static_proofs": PROOF_SHA,
        "diagnostic_frames": 72,
        "cache_provenance": str(root / "final-cache-provenance.json"),
        "output_color_contract": CONTRACT,
        "physical_validation_frames": [4139, 4441],
        "project_profile": str(profile_path),
        "project_profile_sha256": hashlib.sha256(json_bytes(profile)).hexdigest(),
        "full_song_complete": False,
        "user_art_approval": False,
        "art_status": "pending",
        "old_beauty_reused": False,
        "arcs_hidden": True,
        "limits": limits,
    }
    return {
        "recipe_path": recipe_path,
        "recipe": recipe,
        "library_path": library_path,
        "library": library,
        "state_path": state_path,
        "state": state,
        "profile_path": profile_path,
        "profile": profile,
        "registry_hashes": registry_hashes,
        "provenance": provenance,
        "delivery": delivery,
        "hero": hero,
    }


def bundled_document(source):
    def link(match):
        target = match.group(1)
        if ":" in target or target.startswith(("#", "/")):
            return match.group(0)
        path, marker, anchor = target.partition("#")
        actual = (source.parent / path).resolve()
        need(actual.is_file(), "Broken documentation link: " + str(actual))
        replacement = (
            actual.name
            if actual.parent == REPO / "docs" and actual.name in DOCS
            else (
                "research/" + actual.name
                if actual.parent == REPO / "docs/research" and actual.name in RESEARCH
                else actual.as_posix()
            )
        )
        return "](" + replacement + (marker + anchor if marker else "") + ")"

    return re.sub(r"\]\(([^)\s]+)\)", link, source.read_text(encoding="utf-8-sig"))


def json_bytes(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def commit(root, cache, data, plan):
    temp = (
        Path("D:/codex/temp/MMD-Clean-Game-Characters-v1/packaging") / uuid.uuid4().hex
    )
    temp.mkdir(parents=True, exist_ok=False)

    def atomic(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = temp / (uuid.uuid4().hex + ".tmp")
        pending.write_bytes(content)
        pending.replace(path)

    copies = [(REPO / "docs/research" / p, root / "research" / p) for p in RESEARCH]
    copies += [(BASELINE / "licenses" / p, root / "licenses" / p) for p in LICENSES]
    copies += [
        (
            cache / "beauty" / f"frame_{f:04d}beauty.png",
            root / "review" / f"native-source-{f}.png",
        )
        for f in (4290, 4250)
    ]
    copies += [
        (
            Path(data["inherited_static"]["path"]),
            root / "evidence/v2-full-static-capture.json",
        ),
        (
            Path(data["inherited_static"]["script"]),
            root / "evidence/verify-arcs-full-static.py",
        ),
        (
            Path(data["coverage"]["roi_source"]),
            root / "evidence/inherited-caption-rois.json",
        ),
    ]
    copied = {}
    for source, destination in copies:
        if destination.exists():
            need(
                sha(destination) == sha(source),
                "Refusing to overwrite different bundle content: " + str(destination),
            )
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        need(
            sha(destination) == sha(source), "Bundle copy changed: " + str(destination)
        )
        copied[str(destination.relative_to(root))] = sha(destination)
    for name in DOCS:
        atomic(root / name, bundled_document(REPO / "docs" / name).encode("utf-8"))
        copied[name] = sha(root / name)
    atomic(root / "final-cache-provenance.json", json_bytes(plan["provenance"]))
    atomic(
        root / "README.md",
        (
            "# 清透新誓 · 阿克西妮娅 × 伊科尔\n\n"
            "最终工程：production-v2/Franken_Duet_Clean_Game.blend；字幕与无字幕视频在captions-5s。\n\n"
            "原帧4140–4439，1920×1080／60fps，300原生帧／五秒；指定原唱FLAC→AAC。人物材质独立适配，保留袖修、动作、相机和礼堂；蓝金两弧仅隐藏。\n\n"
            "321项材质与26项增量静态验证分别登记；72帧诊断、新300帧与两版技术检查、实际人工抽样见delivery.json。美术待猪猪评价，全曲未完成。\n\n"
            "未复制私人参考视频或其抽帧。来源、社区镜像许可边界与继承组件见CREDITS_AKSINIYA_IKHOR.md及licenses。指南内未打包的知识链接明确指向本机源码仓库。\n"
        ).encode(),
    )
    for path, expected in plan["registry_hashes"].items():
        need(
            sha(path, fresh=True) == expected,
            "Catalog changed during validation; rerun to preserve new feedback: "
            + str(path),
        )
    need(
        not plan["recipe_path"].exists() and not (root / "delivery.json").exists(),
        "Another registration appeared during packaging",
    )
    need(
        sha(data["project"], fresh=True) == MASTER_SHA
        and sha(data["movie"], fresh=True) == data["manual"]["movie_sha256"]
        and sha(data["bare"], fresh=True) == data["manual"]["bare_sha256"],
        "Project/movie changed during packaging",
    )
    for name, expected in data["evidence_hashes"].items():
        need(sha(root / name) == expected, "Evidence changed during packaging: " + name)
    plan["delivery"]["bundled_files"] = copied
    plan["delivery"]["cache_provenance_sha256"] = sha(
        root / "final-cache-provenance.json"
    )
    registry = [
        (plan["recipe_path"], plan["recipe"]),
        (plan["profile_path"], plan["profile"]),
        (plan["library_path"], plan["library"]),
        (plan["state_path"], plan["state"]),
    ]
    backups = {
        path: path.read_bytes() if path.exists() else None for path, _ in registry
    }
    for index, (path, _) in enumerate(registry):
        path.relative_to(REPO)
        if backups[path] is not None:
            (temp / f"registry-before-{index}.json").write_bytes(backups[path])
    written = []
    try:
        for path, payload in registry:
            atomic(path, json_bytes(payload))
            written.append(path)
        need(
            sha(plan["profile_path"], fresh=True)
            == plan["delivery"]["project_profile_sha256"],
            "Registered project profile differs from the delivery binding",
        )
        # Final delivery marker is written only after every artifact and registry
        # update succeeds. Roll back the registry if this final write fails.
        atomic(root / "delivery.json", json_bytes(plan["delivery"]))
    except BaseException:
        for path in reversed(written):
            if backups[path] is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, backups[path])
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument(
        "--date", default=datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(contract(), ensure_ascii=False, indent=2))
        return
    root, cache = args.root.resolve(), args.cache.resolve()
    try:
        need(
            root.is_relative_to(Path("D:/codex/output").resolve()),
            "User-facing deliveries must stay under D:/codex/output",
        )
        need(
            cache.is_relative_to(Path("D:/codex/temp").resolve()),
            "Temporary caches must stay under D:/codex/temp",
        )
        data = validate(root, cache)
        # Resolve every guide link even for dry-run; it must be reviewable before
        # registry writes. This stage only builds strings and Python objects.
        for name in DOCS:
            bundled_document(REPO / "docs" / name)
        plan = package_plan(root, cache, data, args.date)
        if not args.dry_run:
            commit(root, cache, data, plan)
        print(
            json.dumps(
                {
                    "passed": True,
                    "dry_run": args.dry_run,
                    "registered": not args.dry_run,
                    "identity": IDENTITY,
                    "project_sha256": MASTER_SHA,
                    "required_reports": len(REQUIRED_REPORTS),
                    "cache_frames_per_layer": 300,
                    "full_song_complete": False,
                    "user_art_approval": False,
                    "delivery": str(root / "delivery.json"),
                    "registry_files": [
                        str(plan[k])
                        for k in (
                            "recipe_path",
                            "profile_path",
                            "library_path",
                            "state_path",
                        )
                    ],
                },
                ensure_ascii=False,
            )
        )
    except Exception as error:  # noqa: BLE001 - CLI boundary reports failure and exits nonzero.
        print(
            json.dumps(
                {
                    "passed": False,
                    "dry_run": args.dry_run,
                    "registered": False,
                    "error": type(error).__name__,
                    "message": str(error),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
