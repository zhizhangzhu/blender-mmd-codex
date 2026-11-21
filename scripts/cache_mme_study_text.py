"""Privately decode author archive text; do not execute or redistribute effects."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--root", type=Path, default=Path("D:/codex/temp/MME-Deep-Study-2026-11-16")
)
ROOT = parser.parse_args().root
report = []
for archive in sorted((ROOT / "packages").glob("*.zip")):
    out = ROOT / "text" / archive.stem
    out.mkdir(parents=True, exist_ok=True)
    record = {
        "archive": archive.name,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": [],
    }
    with zipfile.ZipFile(archive) as z:
        for number, info in enumerate(z.infolist()):
            name = info.filename
            if not info.flag_bits & 0x800:
                try:
                    name = name.encode("cp437").decode("cp932")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            suffix = PurePosixPath(name).suffix.lower()
            if suffix not in (
                ".txt",
                ".fx",
                ".fxsub",
                ".hlsl",
                ".fxh",
                ".glsl",
                ".md",
                ".ini",
                ".conf",
            ):
                continue
            data = z.read(info)
            encodings = (
                ("utf-16",)
                if data.startswith((b"\xff\xfe", b"\xfe\xff"))
                else ("utf-8-sig", "cp932", "cp1252")
            )
            for encoding in encodings:
                try:
                    value = data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                value = data.decode("utf-8", errors="replace")
                encoding = "utf-8-replacement"
            target = out / f"{number:03d}-{PurePosixPath(name).name}.txt"
            with target.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(value.replace("\r\n", "\n").replace("\r", "\n"))
            record["files"].append(
                {
                    "name": name,
                    "text": str(target),
                    "encoding": encoding,
                    "bytes": len(data),
                    "lines": len(value.splitlines()),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    report.append(record)
(ROOT / "archive-index.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        [{"archive": r["archive"], "text_files": len(r["files"])} for r in report]
    )
)
