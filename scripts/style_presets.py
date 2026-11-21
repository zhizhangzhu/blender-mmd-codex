"""Load independent render, post and aspect-specific direction recipes."""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "presets" / "styles"


def load_package(path):
    path = Path(path).resolve()
    package = json.loads(path.read_text(encoding="utf-8"))
    if package.get("schema_version") != 1:
        raise ValueError("Unsupported style package version")
    if package.get("aspect") not in {"portrait", "landscape"}:
        raise ValueError("Style package must explicitly select an aspect")
    result = copy.deepcopy(package)
    for key in ["render", "post", "typography"]:
        ref = (path.parent / package[key]).resolve()
        result[key] = json.loads(ref.read_text(encoding="utf-8"))
        result[key + "_path"] = str(ref)
    expected = [9, 16] if package["aspect"] == "portrait" else [16, 9]
    if result["typography"]["aspect"] != expected:
        raise ValueError("Typography aspect does not match direction package")
    for key in ["render", "post"]:
        if result[key].get("schema_version") != 1:
            raise ValueError("Unsupported component version")
    if result["camera"]["strategy"] != package["aspect"]:
        raise ValueError("Camera must be explicitly designed for selected aspect")
    if result["post"]["background"]["mode"] not in {"scene", "argyle", "neon"}:
        raise ValueError("Unknown post background mode")
    result["package_path"] = str(path)
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--package", type=Path)
    parser.add_argument("--verify-render-report", type=Path)
    parser.add_argument("--verify-post-report", type=Path)
    parser.add_argument("--source-project", type=Path)
    parser.add_argument("--percentage", type=int, default=50)
    parser.add_argument("--samples", type=int, default=48)
    args = parser.parse_args()
    if args.verify_render_report or args.verify_post_report:
        recipe = load_package(args.package)
        path = args.verify_render_report or args.verify_post_report
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["style_package"] != recipe:
            raise ValueError("Cached stage uses different style settings")
        if args.verify_render_report:
            if report["source_project"] != str(args.source_project) or report[
                "quality"
            ] != {"percentage": args.percentage, "samples": args.samples}:
                raise ValueError("Cached stage source or quality differs")
            if report["frames"] != [421, 660] or report["fps"] != 60:
                raise ValueError("Cached frame range differs")
            for folder, suffix in [
                ("beauty", "beauty"),
                ("matte", "matte"),
                ("face", "face"),
            ]:
                for frame in range(421, 661):
                    image = (
                        Path(report["cache_dir"])
                        / folder
                        / f"frame_{frame:04d}{suffix}.png"
                    )
                    if not image.is_file() or image.stat().st_size < 100:
                        raise ValueError("Incomplete cached image sequence")
        elif (
            report["frames"] != 240
            or not (path.parent / "typography-picture.mp4").is_file()
        ):
            raise ValueError("Incomplete cached post stage")
        print("CACHED_STYLE_STAGE_VERIFIED", path)
    elif args.package:
        print(json.dumps(load_package(args.package), ensure_ascii=False, indent=2))
    elif args.list:
        print((ROOT / "catalog.json").read_text(encoding="utf-8"))
    else:
        parser.error("Choose --list or --package")
