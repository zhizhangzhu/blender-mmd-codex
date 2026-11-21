"""Test/extract a downloaded stage archive and compare it with existing assets.

Uses a fresh extraction directory and never changes the downloaded archive or
the previous asset tree. Rejects paths/links that could escape that directory.
"""

import argparse
import hashlib
import json
import ntpath
import os
import subprocess
from pathlib import Path, PurePosixPath


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def seven_zip(executable, *arguments):
    result = subprocess.run(
        [str(executable), *map(str, arguments), "-sccUTF-8"],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise RuntimeError(
            f"7-Zip failed ({result.returncode}): {result.stdout[-3000:]}"
        )
    return result.stdout


def inventory(root):
    return {
        path.relative_to(root).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--seven-zip", type=Path, required=True)
    parser.add_argument("--extract-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    assert args.archive.is_file() and args.previous.is_dir()
    assert not args.archive.name.endswith(".downloading")
    assert not args.extract_dir.exists() and not args.report_dir.exists()
    listing = seven_zip(args.seven_zip, "l", "-slt", "-ba", args.archive)
    entries = []
    destination = args.extract_dir.resolve()
    for paragraph in listing.replace("\r\n", "\n").split("\n\n"):
        properties = dict(
            line.split(" = ", 1) for line in paragraph.splitlines() if " = " in line
        )
        if "Path" not in properties:
            continue
        name = properties["Path"].replace("\\", "/")
        parts = PurePosixPath(name)
        if (
            parts.is_absolute()
            or ntpath.splitdrive(name)[0]
            or ".." in parts.parts
            or ":" in name
        ):
            raise ValueError(f"Unsafe archive entry: {name}")
        if any("link" in key.lower() for key in properties):
            raise ValueError(f"Archive link requires explicit review: {name}")
        target = destination.joinpath(*parts.parts).resolve()
        if os.path.commonpath([str(destination), str(target)]) != str(destination):
            raise ValueError(f"Entry escapes extraction root: {name}")
        entries.append(name)
    test_log = seven_zip(args.seven_zip, "t", "-bd", "-bsp0", args.archive)
    print("ARCHIVE_INTEGRITY_PASSED", len(entries), "entries", flush=True)
    args.extract_dir.mkdir(parents=True, exist_ok=False)
    extract_log = seven_zip(
        args.seven_zip, "x", "-y", "-bd", "-bsp0", "-o" + str(destination), args.archive
    )
    candidates = list(args.extract_dir.rglob("Hesperides.blend"))
    if len(candidates) != 1:
        raise ValueError(
            f"Expected one Hesperides.blend; found {len(candidates)} in {destination}"
        )
    extracted = candidates[0].parent
    old, new = inventory(args.previous), inventory(extracted)
    common = sorted(old.keys() & new.keys())
    changed = [name for name in common if old[name] != new[name]]
    extras = sorted(new.keys() - old.keys())
    missing = sorted(old.keys() - new.keys())
    render_files = [
        name
        for name in new
        if Path(name).suffix.lower()
        in {".pmm", ".emm", ".conf", ".blend", ".vmd", ".vpd", ".x"}
    ]
    report = {
        "archive": str(args.archive),
        "archive_bytes": args.archive.stat().st_size,
        "archive_sha256": sha256(args.archive),
        "archive_integrity_passed": True,
        "archive_entry_count": len(entries),
        "extraction_directory": str(destination),
        "extracted_asset_root": str(extracted),
        "previous_asset_root": str(args.previous),
        "new_file_count": len(new),
        "previous_file_count": len(old),
        "identical_files": len(common) - len(changed),
        "changed_files": changed,
        "new_only_files": extras,
        "previous_only_files": missing,
        "all_asset_files_identical": not (changed or extras or missing),
        "render_or_configuration_files": render_files,
        "files_outside_asset_root": [
            str(path.relative_to(destination))
            for path in destination.rglob("*")
            if path.is_file() and not path.is_relative_to(extracted)
        ]
        if hasattr(Path, "is_relative_to")
        else [],
        "new_inventory": new,
        "previous_inventory": old,
    }
    args.report_dir.mkdir(parents=True, exist_ok=False)
    (args.report_dir / "archive-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.report_dir / "7zip-test.txt").write_text(test_log, encoding="utf-8")
    (args.report_dir / "7zip-extract.txt").write_text(extract_log, encoding="utf-8")
    summary = {
        key: value
        for key, value in report.items()
        if key not in {"new_inventory", "previous_inventory"}
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
