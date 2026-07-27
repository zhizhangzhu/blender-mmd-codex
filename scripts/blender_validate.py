"""Validate Blender, its Python API, and optionally this project's Add-on."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence


Runner = Callable[..., subprocess.CompletedProcess[str]]
BPY_MARKER = "BLENDER_MMD_CODEX_BPY_OK"
ADDON_MARKER = "BLENDER_MMD_CODEX_ADDON_OK"


@dataclass(frozen=True)
class ValidationReport:
    """Collect validation checks without hiding individual failures."""

    executable: str
    version: str | None
    blender_ok: bool
    python_api_ok: bool
    addon_ok: bool | None
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Return whether every requested validation check passed."""

        addon_passed = self.addon_ok is None or self.addon_ok
        return self.blender_ok and self.python_api_ok and addon_passed


def _run(
    executable: Path,
    arguments: list[str],
    runner: Runner,
    timeout: float,
) -> tuple[int, str]:
    """Run one Blender command and return its exit code and combined output."""

    try:
        result = runner(
            [str(executable), *arguments],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return 127, str(error)
    return result.returncode, f"{result.stdout or ''}\n{result.stderr or ''}"


def _addon_expression(addon_path: Path) -> str:
    """Create a Blender Python expression that imports and registers the Add-on."""

    parent = str(addon_path.expanduser().resolve().parent).replace("\\", "\\\\").replace("'", "\\'")
    module = addon_path.name
    return (
        "import sys; "
        f"sys.path.insert(0, r'{parent}'); "
        f"import {module}; {module}.register(); {module}.unregister(); "
        f"print('{ADDON_MARKER}')"
    )


def validate_blender(
    executable: Path,
    addon_path: Path | None = None,
    runner: Runner = subprocess.run,
    timeout: float = 30.0,
) -> ValidationReport:
    """Run version, bpy, and optional Add-on registration checks."""

    version_code, version_output = _run(executable, ["--version"], runner, timeout)
    version = None
    if version_code == 0:
        from .blender_detect import parse_blender_version

        version = parse_blender_version(version_output)
    errors: list[str] = []
    blender_ok = version_code == 0 and version is not None
    if not blender_ok:
        errors.append("Blender --version 驗證失敗")

    python_code, python_output = _run(
        executable,
        [
            "--background",
            "--factory-startup",
            "--python-expr",
            f"import bpy; print('{BPY_MARKER}')",
        ],
        runner,
        timeout,
    )
    python_api_ok = python_code == 0 and BPY_MARKER in python_output
    if not python_api_ok:
        errors.append("Blender Python API 驗證失敗")

    addon_ok: bool | None = None
    if addon_path is not None:
        addon_code, addon_output = _run(
            executable,
            [
                "--background",
                "--factory-startup",
                "--python-expr",
                _addon_expression(addon_path),
            ],
            runner,
            timeout,
        )
        addon_ok = addon_code == 0 and ADDON_MARKER in addon_output
        if not addon_ok:
            errors.append("Blender Add-on 載入或 register/unregister 驗證失敗")

    return ValidationReport(
        executable=str(executable),
        version=version,
        blender_ok=blender_ok,
        python_api_ok=python_api_ok,
        addon_ok=addon_ok,
        errors=tuple(errors),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Validate Blender from the command line and emit JSON."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--addon-path", type=Path)
    args = parser.parse_args(argv)
    report = validate_blender(args.executable, args.addon_path)
    payload = asdict(report)
    payload["ok"] = report.ok
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
