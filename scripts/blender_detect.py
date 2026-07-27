"""Detect installed Blender executables without modifying the host system."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


VERSION_PATTERN = re.compile(r"\bBlender\s+(\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?)")
Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class BlenderInstallation:
    """Describe one executable that responded as a Blender installation."""

    executable: str
    version: str | None
    source: str


def normalize_platform(value: str | None = None) -> str:
    """Normalize an operating-system label to Windows, Darwin, or Linux."""

    name = (value or platform.system()).strip().lower()
    if name in {"windows", "win32", "win"}:
        return "Windows"
    if name in {"darwin", "macos", "mac"}:
        return "Darwin"
    if name in {"linux", "linux2"}:
        return "Linux"
    return value or platform.system()


def parse_blender_version(output: str) -> str | None:
    """Extract a Blender version from `blender --version` output."""

    match = VERSION_PATTERN.search(output)
    return match.group(1) if match else None


def _add_candidate(candidates: list[Path], value: str | Path | None) -> None:
    """Append a non-empty candidate while preserving discovery order."""

    if value:
        path = Path(value).expanduser()
        if path not in candidates:
            candidates.append(path)


def find_blender_candidates(
    system_name: str | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> list[Path]:
    """Return likely Blender executable paths for a platform.

    The function only builds a candidate list. It does not execute or install anything,
    which makes it safe to use for preflight checks and unit tests.
    """

    system = normalize_platform(system_name)
    variables = dict(os.environ if env is None else env)
    user_home = Path(home or variables.get("USERPROFILE") or variables.get("HOME") or Path.home())
    candidates: list[Path] = []

    _add_candidate(candidates, which("blender"))
    _add_candidate(candidates, which("blender.exe"))

    if system == "Windows":
        roots = [
            variables.get("PROGRAMFILES"),
            variables.get("PROGRAMFILES(X86)"),
            variables.get("LOCALAPPDATA"),
        ]
        for root in filter(None, roots):
            base = Path(root)
            _add_candidate(candidates, base / "Blender Foundation" / "Blender" / "blender.exe")
            for path in sorted((base / "Blender Foundation").glob("Blender*")):
                _add_candidate(candidates, path / "blender.exe")
    elif system == "Darwin":
        _add_candidate(candidates, "/Applications/Blender.app/Contents/MacOS/Blender")
        _add_candidate(candidates, user_home / "Applications/Blender.app/Contents/MacOS/Blender")
    elif system == "Linux":
        for path in ("/usr/bin/blender", "/usr/local/bin/blender", "/snap/bin/blender"):
            _add_candidate(candidates, path)
        for path in sorted(user_home.glob("blender*/blender")):
            _add_candidate(candidates, path)

    return candidates


def probe_blender_version(
    executable: Path,
    runner: Runner = subprocess.run,
    timeout: float = 10.0,
) -> str | None:
    """Run `--version` and return the parsed version, or `None` on failure."""

    try:
        result = runner(
            [str(executable), "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    output = f"{result.stdout or ''}\n{result.stderr or ''}"
    return parse_blender_version(output) if result.returncode == 0 else None


def detect_blender(
    system_name: str | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Runner = subprocess.run,
) -> BlenderInstallation | None:
    """Find the first existing Blender executable that answers `--version`."""

    for candidate in find_blender_candidates(system_name, env, home, which):
        if not candidate.is_file():
            continue
        version = probe_blender_version(candidate, runner)
        if version:
            return BlenderInstallation(str(candidate), version, "discovered")
    return None


def main(argv: Sequence[str] | None = None) -> int:
    """Run detection from the command line and emit a JSON result."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", help="Override the detected operating system")
    args = parser.parse_args(argv)
    installation = detect_blender(system_name=args.system)
    payload = {
        "ok": installation is not None,
        "installation": asdict(installation) if installation else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if installation else 1


if __name__ == "__main__":
    raise SystemExit(main())
