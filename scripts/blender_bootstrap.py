"""Coordinate Blender detection, verified portable installation, and validation."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from .blender_detect import BlenderInstallation, detect_blender
from .blender_download import build_official_artifact, download_file
from .blender_install import InstallationError, install_portable_archive
from .blender_validate import ValidationReport, validate_blender


@dataclass(frozen=True)
class BootstrapResult:
    """Describe the outcome of a non-destructive or confirmed bootstrap attempt."""

    status: str
    message: str
    installation: BlenderInstallation | None = None
    validation: ValidationReport | None = None


def bootstrap(
    version: str | None,
    install_dir: Path,
    addon_path: Path | None,
    confirm_install: bool,
    sha256: str | None,
) -> BootstrapResult:
    """Detect Blender, or install an explicitly confirmed and verified portable build."""

    existing = detect_blender()
    if existing:
        validation = validate_blender(Path(existing.executable), addon_path)
        status = "ready" if validation.ok else "existing_blender_needs_attention"
        return BootstrapResult(status, "已找到現有 Blender。", existing, validation)

    if not confirm_install:
        return BootstrapResult(
            "confirmation_required",
            "尚未找到 Blender；下載與安裝前需要使用者確認。",
        )
    if not version:
        return BootstrapResult("version_required", "安裝前必須指定完整 Blender 版本。")
    if not sha256:
        return BootstrapResult("sha256_required", "安裝前必須提供官方下載檔的 SHA-256。")

    artifact = build_official_artifact(version)
    install_dir = install_dir.expanduser().resolve()
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="blender-mmd-codex-") as temporary:
        archive = Path(temporary) / artifact.filename
        download_file(artifact.url, archive, sha256)
        executable = install_portable_archive(archive, install_dir, artifact.system)

    installation = BlenderInstallation(str(executable), artifact.version, "portable")
    validation = validate_blender(executable, addon_path)
    status = "ready" if validation.ok else "installed_needs_attention"
    return BootstrapResult(status, "Blender portable 版本已安裝並完成驗證。", installation, validation)


def _result_to_dict(result: BootstrapResult) -> dict[str, object]:
    """Convert nested dataclasses into JSON-compatible data."""

    payload = asdict(result)
    if result.validation is not None:
        payload["validation"]["ok"] = result.validation.ok  # type: ignore[index]
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    """Run the bootstrap flow from the command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version")
    parser.add_argument("--install-dir", type=Path, default=Path("portable_blender"))
    parser.add_argument("--addon-path", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="確認下載與安裝；未提供此旗標時只做偵測或回報需要確認。",
    )
    args = parser.parse_args(argv)
    result = bootstrap(args.version, args.install_dir, args.addon_path, args.yes, args.sha256)
    print(json.dumps(_result_to_dict(result), ensure_ascii=False, indent=2))
    return 0 if result.status == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
