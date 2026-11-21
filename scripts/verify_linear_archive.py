"""Verify numbered multipart EXRs and independently decode their color data."""

import argparse
import io
import json
import re
import struct
import subprocess
from pathlib import Path

import numpy as np


def cstring(stream):
    result = bytearray()
    while True:
        char = stream.read(1)
        if not char:
            raise EOFError("Incomplete EXR header")
        if char == b"\0":
            return result.decode("utf-8", errors="replace")
        result.extend(char)
        if len(result) > 4096:
            raise ValueError("Unbounded EXR header string")


def header(stream):
    fields = {}
    while True:
        name = cstring(stream)
        if not name:
            return fields or None
        kind = cstring(stream)
        size = struct.unpack("<I", stream.read(4))[0]
        if size > 134217728:
            raise ValueError("Invalid EXR attribute size")
        value = stream.read(size)
        if len(value) != size:
            raise EOFError("Incomplete EXR attribute")
        fields[name] = (kind, value)


def exr_parts(path):
    with path.open("rb") as stream:
        magic, version = struct.unpack("<II", stream.read(8))
        assert magic == 20000630, path
        parts = []
        while True:
            fields = header(stream)
            if fields is None:
                break
            channels = []
            data = io.BytesIO(fields["channels"][1])
            while True:
                name = cstring(data)
                if not name:
                    break
                pixel_type = struct.unpack("<I", data.read(4))[0]
                data.read(12)
                channels.append({"name": name, "pixel_type": pixel_type})
            bounds = struct.unpack("<iiii", fields["dataWindow"][1])
            parts.append(
                {
                    "name": fields.get("name", ("", b""))[1].decode("utf-8"),
                    "channels": channels,
                    "size": [bounds[2] - bounds[0] + 1, bounds[3] - bounds[1] + 1],
                    "compression": fields["compression"][1][0],
                }
            )
            if not version & 0x1000:
                break
        return parts


def float_part(ffmpeg, path, index, layer):
    result = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-threads",
            "3",
            "-part",
            str(index),
            "-layer",
            layer,
            "-apply_trc",
            "linear",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-pix_fmt",
            "gbrpf32le",
            "-f",
            "rawvideo",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    )
    pixels = np.frombuffer(result.stdout, dtype="<f4")
    assert pixels.size == 1920 * 1080 * 3, (path, pixels.size)
    assert np.isfinite(pixels).all(), path
    return {
        "minimum": float(pixels.min()),
        "maximum": float(pixels.max()),
        "mean": float(pixels.mean()),
        "finite": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--native-pixels",
        action="store_true",
        help="Read every original channel using OpenEXR >=3.3; FFmpeg conversion alone is not HDR validation",
    )
    args = parser.parse_args()
    paths = [args.archive / f"duet_{frame:04d}.exr" for frame in range(4140, 4440)]
    assert all(path.is_file() for path in paths), "Missing numbered EXRs"
    unexpected = [
        path.name
        for path in args.archive.glob("duet_*.exr")
        if not re.fullmatch(r"duet_\d{4}\.exr", path.name)
    ]
    reference = None
    for path in paths:
        parts = exr_parts(path)
        assert len(parts) == 3, (path, parts)
        assert {part["name"] for part in parts} == {
            "RawBeauty",
            "FinalLinear",
            "ActorMask",
        }, parts
        assert all(part["size"] == [1920, 1080] for part in parts), path
        assert all(
            channel["pixel_type"] == (2 if part["name"] == "ActorMask" else 1)
            for part in parts
            for channel in part["channels"]
        ), path
        assert all(part["compression"] == 3 for part in parts), path
        if reference is None:
            reference = parts
        else:
            assert parts == reference, path
    colors = []
    for frame in [4140, 4290, 4439]:
        path = args.archive / f"duet_{frame}.exr"
        for index, part in enumerate(reference):
            if part["name"] in {"RawBeauty", "FinalLinear"}:
                colors.append(
                    {
                        "frame": frame,
                        "part": part["name"],
                        **float_part(args.ffmpeg, path, index, part["name"]),
                    }
                )
    native = None
    if args.native_pixels:
        import OpenEXR

        bounds = {
            name: {"minimum": float("inf"), "maximum": float("-inf"), "dtype": None}
            for name in ["RawBeauty", "FinalLinear", "ActorMask"]
        }
        for number, path in enumerate(paths):
            with OpenEXR.File(str(path), separate_channels=True) as image:
                for part in image.parts:
                    name = part.name()
                    for channel in part.channels.values():
                        pixels = channel.pixels
                        assert pixels.shape == (1080, 1920), path
                        assert np.isfinite(pixels).all(), (path, name)
                        assert pixels.dtype == (
                            np.float32 if name == "ActorMask" else np.float16
                        )
                        minimum, maximum = float(pixels.min()), float(pixels.max())
                        bounds[name]["minimum"] = min(bounds[name]["minimum"], minimum)
                        bounds[name]["maximum"] = max(bounds[name]["maximum"], maximum)
                        bounds[name]["dtype"] = str(pixels.dtype)
                        if name == "ActorMask":
                            assert minimum >= -0.00001 and maximum <= 1.00001, (
                                path,
                                minimum,
                                maximum,
                            )
            if (number + 1) % 60 == 0:
                print("NATIVE_EXR_PROGRESS", number + 1, "/ 300", flush=True)
        assert bounds["RawBeauty"]["maximum"] > 1, "HDR numerical range missing"
        native = {
            "library": OpenEXR.__version__,
            "frames": len(paths),
            "all_channels_finite": True,
            "parts": bounds,
            "preserved_values_above_one": True,
        }
    raw_index = next(
        index for index, part in enumerate(reference) if part["name"] == "RawBeauty"
    )
    command = [
        str(args.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-xerror",
        "-threads",
        "4",
        "-part",
        str(raw_index),
        "-layer",
        "RawBeauty",
        "-apply_trc",
        "linear",
        "-framerate",
        "60",
        "-start_number",
        "4140",
        "-i",
        str(args.archive / "duet_%04d.exr"),
        "-frames:v",
        "300",
        "-progress",
        "pipe:1",
        "-nostats",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    frames = [
        int(value) for value in re.findall(r"^frame=(\d+)", result.stdout, re.MULTILINE)
    ]
    assert frames and frames[-1] == 300, result.stdout
    report = {
        "passed": True,
        "frames": 300,
        "resolution": [1920, 1080],
        "source_frames": [4140, 4439],
        "parts": reference,
        "sampled_float_data": colors,
        "sampled_float_data_scope": "FFmpeg-decoded conversion may clamp HDR; use native_pixel_verification for original floating point bounds",
        "native_pixel_verification": native,
        "independent_raw_sequence_decode_frames": frames[-1],
        "bytes": sum(path.stat().st_size for path in paths),
        "non_numbered_files_ignored": unexpected,
        "linear_interpretation": "No display TRC applied during independent float decoding",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("LINEAR_ARCHIVE_VERIFIED", report["frames"], report["bytes"], flush=True)


if __name__ == "__main__":
    main()
