"""Build official Blender release URLs and download files with SHA-256 verification."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

from .blender_detect import normalize_platform


VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
OFFICIAL_RELEASE_BASE = "https://download.blender.org/release"
Urlopen = Callable[..., object]


@dataclass(frozen=True)
class DownloadArtifact:
    """Describe one versioned Blender package from the official release host."""

    version: str
    system: str
    architecture: str
    filename: str
    url: str
    archive_type: str


def normalize_architecture(value: str | None = None) -> str:
    """Normalize common machine labels to x64 or arm64."""

    name = (value or platform.machine()).strip().lower()
    if name in {"amd64", "x86_64", "x64"}:
        return "x64"
    if name in {"arm64", "aarch64"}:
        return "arm64"
    raise ValueError(f"不支援的 CPU 架構：{value or platform.machine()}")


def _validate_version(version: str) -> str:
    """Validate a concrete Blender version without choosing a moving latest release."""

    normalized = version.strip().lstrip("v")
    if not VERSION_PATTERN.fullmatch(normalized):
        raise ValueError("Blender 版本必須是完整版本，例如 4.5.0")
    return normalized


def build_official_artifact(
    version: str,
    system_name: str | None = None,
    machine: str | None = None,
    base_url: str = OFFICIAL_RELEASE_BASE,
) -> DownloadArtifact:
    """Build a portable package URL for an explicit Blender version."""

    normalized_version = _validate_version(version)
    system = normalize_platform(system_name)
    architecture = normalize_architecture(machine)

    if system == "Windows":
        suffix = "zip"
        platform_name = "windows"
    elif system == "Darwin":
        suffix = "dmg"
        platform_name = "macos"
    elif system == "Linux":
        suffix = "tar.xz"
        platform_name = "linux"
    else:
        raise ValueError(f"不支援的作業系統：{system}")

    filename = f"blender-{normalized_version}-{platform_name}-{architecture}.{suffix}"
    release_series = ".".join(normalized_version.split(".")[:2])
    url = f"{base_url.rstrip('/')}/Blender{release_series}/{filename}"
    return DownloadArtifact(
        version=normalized_version,
        system=system,
        architecture=architecture,
        filename=filename,
        url=url,
        archive_type=suffix,
    )


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the lowercase SHA-256 digest for a local file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: Path, expected: str) -> bool:
    """Compare a file's SHA-256 digest with an expected hexadecimal value."""

    normalized = expected.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError("SHA-256 必須是 64 個十六進位字元")
    return sha256_file(path) == normalized


def download_file(
    url: str,
    destination: Path,
    expected_sha256: str,
    urlopen: Urlopen = urllib.request.urlopen,
    timeout: float = 60.0,
) -> Path:
    """Download one file from an explicit URL and require SHA-256 verification."""

    if not url.startswith("https://download.blender.org/"):
        raise ValueError("只允許從 Blender 官方 HTTPS 下載來源取得檔案")

    destination = destination.expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    try:
        with urlopen(url, timeout=timeout) as response, partial.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
        if not verify_sha256(partial, expected_sha256):
            raise ValueError("下載檔案的 SHA-256 驗證失敗")
        os.replace(partial, destination)
    except Exception:
        if partial.exists():
            partial.unlink()
        raise
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    """Build an artifact description or download it when an output path is supplied."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--system")
    parser.add_argument("--machine")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args(argv)
    artifact = build_official_artifact(args.version, args.system, args.machine)
    if not args.output:
        import json

        print(json.dumps(asdict(artifact), ensure_ascii=False, indent=2))
        return 0
    if not args.sha256:
        parser.error("使用 --output 下載時必須同時提供 --sha256")
    path = download_file(artifact.url, args.output, args.sha256)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
