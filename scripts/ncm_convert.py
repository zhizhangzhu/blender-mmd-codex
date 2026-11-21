"""Convert local NCM files with ncmdump; preserve native FLAC/MP3 by default.

Requires the author's ncmdump executable and FFmpeg. Conversion stays offline,
never deletes inputs, rejects output collisions, and fully decodes each result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

LOCAL_NCMDUMP = Path("D:/codex/temp/ncm-audio-tools/ncmdump-1.5.1/ncmdump.exe")
LOCAL_FFMPEG = Path(
    "D:/codex/temp/blender-mmd-video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
)


def executable(explicit, variable, name, local):
    selected = explicit or os.environ.get(variable) or shutil.which(name)
    if selected is None and local.is_file():
        selected = local
    if selected is None or not Path(selected).is_file():
        raise FileNotFoundError(
            f"Set --{name} or {variable} to the installed executable"
        )
    return Path(selected).resolve()


def collect_inputs(paths, recursive=False):
    found = []
    for raw in paths:
        path = Path(raw).resolve()
        if path.is_dir():
            candidates = path.rglob("*") if recursive else path.iterdir()
            found.extend(
                sorted(
                    p for p in candidates if p.is_file() and p.suffix.lower() == ".ncm"
                )
            )
        elif path.is_file() and path.suffix.lower() == ".ncm":
            found.append(path)
        else:
            raise ValueError(f"Not an NCM file or directory: {path}")
    found = list(dict.fromkeys(found))
    if not found:
        raise ValueError("No NCM files selected")
    names = {}
    for path in found:
        key = path.stem.casefold()
        if key in names:
            raise ValueError(
                f"Output name collision: {names[key]} and {path}; choose separate output directories"
            )
        names[key] = path
    return found


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def audio_format(path):
    with path.open("rb") as stream:
        head = stream.read(4)
    if head == b"fLaC":
        return "flac"
    if head[:3] == b"ID3" or (
        len(head) >= 2 and head[0] == 255 and head[1] & 224 == 224
    ):
        return "mp3"
    raise ValueError("Extracted audio has no recognized FLAC/MP3 signature")


def flac_info(path):
    with path.open("rb") as stream:
        if stream.read(4) != b"fLaC":
            raise ValueError("Not a native FLAC stream")
        result = {"tags": {}}
        while True:
            header = stream.read(4)
            if len(header) != 4:
                raise ValueError("Truncated FLAC metadata")
            size = int.from_bytes(header[1:], "big")
            block = stream.read(size)
            if len(block) != size:
                raise ValueError("Truncated FLAC block")
            kind = header[0] & 127
            if kind == 0:
                if len(block) != 34:
                    raise ValueError("Invalid FLAC STREAMINFO")
                packed = int.from_bytes(block[10:18], "big")
                rate = packed >> 44
                total = packed & ((1 << 36) - 1)
                if not rate or not total:
                    raise ValueError("FLAC has no declared sample rate or sample count")
                result.update(
                    {
                        "sample_rate": rate,
                        "channels": ((packed >> 41) & 7) + 1,
                        "bits_per_sample": ((packed >> 36) & 31) + 1,
                        "total_samples": total,
                        "duration_seconds": total / rate,
                        "stream_md5": block[18:34].hex(),
                    }
                )
            elif kind == 4:
                # Vorbis comments are descriptive only; they never choose paths.
                def number(offset):
                    if offset + 4 > len(block):
                        raise ValueError("Truncated FLAC comments")
                    return struct.unpack_from("<I", block, offset)[0]

                vendor_size = number(0)
                offset = 4 + vendor_size
                count = number(offset)
                offset += 4
                for _ in range(count):
                    length = number(offset)
                    offset += 4
                    if offset + length > len(block):
                        raise ValueError("Truncated FLAC comment")
                    field = block[offset : offset + length].decode(
                        "utf-8", errors="replace"
                    )
                    offset += length
                    if "=" in field:
                        key, value = field.split("=", 1)
                        result["tags"].setdefault(key.upper(), []).append(value)
            if header[0] & 128:
                break
    if "sample_rate" not in result:
        raise ValueError("Missing FLAC STREAMINFO")
    return result


def run(command):
    result = subprocess.run(
        [str(p) for p in command],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise RuntimeError(
            f"{Path(command[0]).name} failed ({result.returncode}):\n{result.stderr[-3000:]}\n{result.stdout[-1000:]}"
        )
    return result


def verify_audio(path, ffmpeg):
    decoded = run(
        [
            ffmpeg,
            "-hide_banner",
            "-v",
            "error",
            "-xerror",
            "-nostdin",
            "-i",
            path,
            "-map",
            "0:a:0",
            "-vn",
            "-c:a",
            "pcm_s32le",
            "-progress",
            "pipe:2",
            "-nostats",
            "-f",
            "hash",
            "-hash",
            "sha256",
            "-",
        ]
    )
    digest = re.search(r"SHA256=([0-9a-fA-F]{64})", decoded.stdout)
    times = re.findall(r"^out_time_us=(\d+)$", decoded.stderr, re.MULTILINE)
    if not digest or not times or int(times[-1]) <= 0:
        raise ValueError(
            "Audio decode did not produce a complete duration and PCM checksum"
        )
    result = {
        "full_decode_passed": True,
        "decoded_seconds": int(times[-1]) / 1_000_000,
        "pcm_s32le_sha256": digest.group(1).lower(),
    }
    if audio_format(path) == "flac":
        result.update(flac_info(path))
        if abs(result["duration_seconds"] - result["decoded_seconds"]) > 0.05:
            raise ValueError("FLAC sample count and decoded duration disagree")
    else:
        result["duration_seconds"] = result["decoded_seconds"]
    return result


def publish(source, target):
    # Exclusive creation protects existing files even if another process races us.
    with target.open("xb") as output:
        try:
            with source.open("rb") as stream:
                shutil.copyfileobj(stream, output)
        except BaseException:
            output.close()
            target.unlink()  # only our just-created partial output
            raise


def convert_one(source, output_dir, temp_dir, ncmdump, ffmpeg, requested="auto"):
    source = Path(source).resolve()
    with source.open("rb") as stream:
        if stream.read(8) != b"CTENFDAM":
            raise ValueError(f"Not a supported NCM file: {source}")
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / (source.stem + ".conversion.json")
    lyrics_source = source.with_suffix(".lrc")
    lyrics_output = output_dir / (source.stem + ".lrc")
    targets = [
        report_path,
        output_dir / (source.stem + ".flac"),
        output_dir / (source.stem + ".mp3"),
    ]
    if lyrics_source.is_file():
        targets.append(lyrics_output)
    for target in targets:
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite {target}")
    original_hash = sha256(source)
    with tempfile.TemporaryDirectory(prefix="ncm-", dir=temp_dir) as directory:
        stage = Path(directory)
        run([ncmdump, source, "-o", stage])
        extracted = [
            p
            for p in stage.iterdir()
            if p.is_file() and p.suffix.lower() in {".mp3", ".flac"}
        ]
        if len(extracted) != 1:
            raise ValueError(
                f"Expected one extracted audio file, found {len(extracted)}"
            )
        native = extracted[0]
        native_format = audio_format(native)
        selected = native_format if requested == "auto" else requested
        if selected not in {"flac", "mp3"}:
            raise ValueError("Choose auto, flac, or mp3")
        prepared = native
        transcoded = selected != native_format
        if transcoded:
            prepared = stage / ("transcoded." + selected)
            codec = (
                ["-c:a", "flac", "-compression_level", "8"]
                if selected == "flac"
                else ["-c:a", "libmp3lame", "-q:a", "2"]
            )
            run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-v",
                    "error",
                    "-nostdin",
                    "-n",
                    "-i",
                    native,
                    "-map",
                    "0:a:0",
                    "-vn",
                    "-map_metadata",
                    "0",
                    *codec,
                    prepared,
                ]
            )
        validation = verify_audio(prepared, ffmpeg)
        if sha256(source) != original_hash:
            raise ValueError("Source NCM changed during conversion")
        destination = output_dir / (source.stem + "." + selected)
        report = {
            "source": str(source),
            "source_sha256": original_hash,
            "output": str(destination),
            "output_sha256": sha256(prepared),
            "native_format": native_format,
            "output_format": selected,
            "transcoded": transcoded,
            "native_audio_preserved_without_reencoding": not transcoded,
            "source_ncm_unchanged": True,
            "ncmdump": str(ncmdump),
            "ncmdump_sha256": sha256(ncmdump),
            "ncmdump_source": "https://github.com/taurusxin/ncmdump",
            "ffmpeg": str(ffmpeg),
            "lyrics": str(lyrics_output) if lyrics_source.is_file() else None,
            "audio": validation,
        }
        publish(prepared, destination)
        if lyrics_source.is_file():
            publish(lyrics_source, lyrics_output)
        with report_path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", nargs="+", type=Path, help="NCM files or directories")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument(
        "--temp-dir",
        type=Path,
        default=Path("D:/codex/temp/ncm-convert")
        if os.name == "nt"
        else Path(tempfile.gettempdir()) / "ncm-convert",
    )
    p.add_argument("--format", choices=["auto", "flac", "mp3"], default="auto")
    p.add_argument("--recursive", action="store_true")
    p.add_argument("--ncmdump", type=Path)
    p.add_argument("--ffmpeg", type=Path)
    args = p.parse_args()
    ncmdump = executable(args.ncmdump, "NCMDUMP_EXE", "ncmdump", LOCAL_NCMDUMP)
    ffmpeg = executable(args.ffmpeg, "FFMPEG_EXE", "ffmpeg", LOCAL_FFMPEG)
    for source in collect_inputs(args.inputs, args.recursive):
        report = convert_one(
            source, args.output_dir, args.temp_dir, ncmdump, ffmpeg, args.format
        )
        print(
            json.dumps(
                {
                    "output": report["output"],
                    "native_format": report["native_format"],
                    "transcoded": report["transcoded"],
                    "seconds": report["audio"]["duration_seconds"],
                    "full_decode_passed": True,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
