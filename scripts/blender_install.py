"""Install Blender portable archives with path-traversal protection."""

from __future__ import annotations

import argparse
import os
import platform
import tarfile
import zipfile
from pathlib import Path
from typing import Sequence


class InstallationError(RuntimeError):
    """Raised when a portable Blender archive cannot be installed safely."""


def _safe_member_path(root: Path, member_name: str) -> Path:
    """Resolve an archive member and reject paths outside the install directory."""

    destination = (root / member_name).resolve()
    resolved_root = root.resolve()
    if destination != resolved_root and resolved_root not in destination.parents:
        raise InstallationError(f"封存檔包含不安全路徑：{member_name}")
    return destination


def _extract_zip(archive: Path, destination: Path) -> None:
    """Extract a ZIP archive after validating every member path."""

    with zipfile.ZipFile(archive) as handle:
        members = handle.infolist()
        for member in members:
            _safe_member_path(destination, member.filename)
        handle.extractall(destination)


def _extract_tar(archive: Path, destination: Path) -> None:
    """Extract a tar archive while rejecting links and traversal paths."""

    with tarfile.open(archive, mode="r:*") as handle:
        members = handle.getmembers()
        for member in members:
            if member.issym() or member.islnk():
                raise InstallationError(f"不允許 portable 安裝包內含連結：{member.name}")
            _safe_member_path(destination, member.name)
        handle.extractall(destination)


def find_blender_executable(root: Path, system_name: str | None = None) -> Path:
    """Find the Blender executable inside an extracted portable installation."""

    system = (system_name or platform.system()).lower()
    names = ["blender.exe", "Blender"] if system.startswith("win") else ["Blender", "blender"]
    if system.startswith("darwin"):
        names.insert(0, "Blender.app/Contents/MacOS/Blender")
    for name in names:
        matches = sorted(root.rglob(name))
        for match in matches:
            if match.is_file():
                return match.resolve()
    raise InstallationError(f"安裝包內找不到 Blender 執行檔：{root}")


def install_portable_archive(
    archive: Path,
    install_dir: Path,
    system_name: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Extract a ZIP or tar archive into a new directory and return Blender's path."""

    archive = archive.expanduser().resolve()
    install_dir = install_dir.expanduser().resolve()
    if not archive.is_file():
        raise InstallationError(f"找不到安裝包：{archive}")
    if install_dir.exists() and any(install_dir.iterdir()) and not overwrite:
        raise InstallationError(f"安裝目錄已有內容，為避免覆寫而停止：{install_dir}")
    install_dir.mkdir(parents=True, exist_ok=True)

    try:
        if archive.name.endswith(".zip"):
            _extract_zip(archive, install_dir)
        elif archive.name.endswith(".tar.xz") or archive.name.endswith(".tar.gz"):
            _extract_tar(archive, install_dir)
        else:
            raise InstallationError("目前只支援 ZIP、tar.xz 與 tar.gz portable 安裝包")
        executable = find_blender_executable(install_dir, system_name)
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        raise InstallationError(f"解壓縮 Blender 安裝包失敗：{error}") from error
    return executable


def main(argv: Sequence[str] | None = None) -> int:
    """Install a portable archive from the command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--install-dir", type=Path, required=True)
    parser.add_argument("--system")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    executable = install_portable_archive(
        args.archive,
        args.install_dir,
        system_name=args.system,
        overwrite=args.overwrite,
    )
    print(executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
