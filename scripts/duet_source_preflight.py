"""Read duet source data using the installed MMD Tools PMX/VMD readers.

No Blender import, retarget, physics bake or visual validation is implied.
Run with system Python; only the add-on's standalone data readers are loaded.
"""

import argparse
import gc
import hashlib
import importlib.util
import json
import unicodedata
import wave
from pathlib import Path


def reader(root, kind):
    spec = importlib.util.spec_from_file_location(
        "duet_reader_" + kind, root / kind / "__init__.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def norm(value):
    return unicodedata.normalize("NFKC", value)


def span(keys):
    values = [k.frame_number for k in keys]
    return [min(values), max(values)] if values else None


def motion_report(path, vmd):
    data = vmd.File()
    data.load(filepath=str(path))
    return data, {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bone_tracks": len(data.boneAnimation),
        "bone_frames": span(k for keys in data.boneAnimation.values() for k in keys),
        "morph_tracks": len(data.shapeKeyAnimation),
        "morph_frames": span(
            k for keys in data.shapeKeyAnimation.values() for k in keys
        ),
        "camera_keys": len(data.cameraAnimation),
        "camera_frames": span(data.cameraAnimation),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", type=Path, required=True)
    p.add_argument("--reader-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    project = json.loads(args.project.read_text(encoding="utf-8"))
    pmx, vmd = reader(args.reader_root, "pmx"), reader(args.reader_root, "vmd")
    report = {
        "project_id": project["id"],
        "status": "source_data_preflight_only",
        "performers": [],
        "cameras": [],
    }
    essential = [
        "センター",
        "上半身",
        "下半身",
        "頭",
        "左腕",
        "右腕",
        "左ひじ",
        "右ひじ",
        "左足",
        "右足",
        "左ひざ",
        "右ひざ",
    ]
    for performer in project["performers"]:
        source = Path(performer["model"])
        model = pmx.load(str(source))
        motion, info = motion_report(Path(performer["motion"]), vmd)
        bones = {norm(b.name) for b in model.bones}
        morphs = {norm(m.name) for m in model.morphs}
        info.update(
            {
                "performer": performer["display_name"],
                "motion_part": performer["motion_part"],
                "model": str(source),
                "model_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "model_name": model.name,
                "vertices": len(model.vertices),
                "bones": len(model.bones),
                "rigids": len(model.rigids),
                "joints": len(model.joints),
                "materials": [m.name for m in model.materials],
                "model_height_pmx_y_up": max(v.co[1] for v in model.vertices)
                - min(v.co[1] for v in model.vertices),
                "missing_textures": [
                    t.path for t in model.textures if not Path(t.path).is_file()
                ],
                "matched_bone_tracks_nfkc": len(
                    {norm(n) for n in motion.boneAnimation} & bones
                ),
                "unmatched_multikey_bone_tracks": [
                    n
                    for n, keys in motion.boneAnimation.items()
                    if len(keys) > 2 and norm(n) not in bones
                ],
                "missing_essential_bones": [
                    n for n in essential if norm(n) not in bones
                ],
                "matched_morphs_nfkc": sorted(
                    n for n in motion.shapeKeyAnimation if norm(n) in morphs
                ),
                "unmatched_morphs_nfkc": sorted(
                    n for n in motion.shapeKeyAnimation if norm(n) not in morphs
                ),
                "source_center_samples": [
                    {"frame": k.frame_number, "location_mmd_xyz": list(k.location)}
                    for k in motion.boneAnimation.get("センター", [])[
                        :: max(1, len(motion.boneAnimation.get("センター", [])) // 6)
                    ]
                ],
            }
        )
        report["performers"].append(info)
        del motion, model
        gc.collect()
    camera_root = Path(project["camera"]["downloaded_package"])
    for path in sorted(camera_root.rglob("*.vmd")):
        motion, info = motion_report(path, vmd)
        report["cameras"].append(info)
        del motion
    with wave.open(project["audio"]["instrumental"], "rb") as audio:
        report["instrumental"] = {
            "seconds": audio.getnframes() / audio.getframerate(),
            "sample_rate": audio.getframerate(),
            "channels": audio.getnchannels(),
        }
    report["source_files_and_core_bones_present"] = all(
        not x["missing_textures"]
        and not x["missing_essential_bones"]
        and not x["unmatched_multikey_bone_tracks"]
        for x in report["performers"]
    )
    report["limits"] = [
        "VMD frames are source 30 fps; Blender frame offset and 60 fps retiming remain to be verified.",
        "Morph aliases are not guessed from similar names; expressive shapes need visual mapping.",
        "Source motion, camera and audio durations differ; full-song timeline is not resolved by this report.",
        "Not a Blender import, physics bake, camera composition pass, render or final video.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(
        "DUET_PREFLIGHT_OK",
        json.dumps(
            {
                "core_data_present": report["source_files_and_core_bones_present"],
                "performers": [
                    {
                        "name": p["performer"],
                        "part": p["motion_part"],
                        "frames": p["bone_frames"],
                        "matched_bones": p["matched_bone_tracks_nfkc"],
                    }
                    for p in report["performers"]
                ],
                "camera_files": len(report["cameras"]),
                "output": str(args.output),
            },
            ensure_ascii=False,
        ),
    )


if __name__ == "__main__":
    main()
