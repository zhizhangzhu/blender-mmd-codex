"""Render the saved eye/hair/stage revision as one captioned original-vocal sample."""

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Jelly-Eyes-v1")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--production", default="production-v16")
parser.add_argument("--iteration", default="quick-5s-v16")
args = parser.parse_args()
assert (
    Path(args.production).name == args.production
    and Path(args.iteration).name == args.iteration
)
PROJECT = ROOT / args.production / "Franken_Duet_Goo_Eye_Hair_Stage.blend"
verification = json.loads(
    (PROJECT.parent / "master-verification.json").read_text(encoding="utf-8")
)
assert verification["passed"] and verification["project"] == str(PROJECT)
if args.production == "production-v16":
    preflight = Path(
        "D:/codex/temp/jelly-eye-study-v1/shadow-budget-v16.log"
    ).read_text(encoding="utf-8", errors="replace")
    assert preflight.count("SHADOW_MEMORY_PREFLIGHT ") == 3
    assert "shadow buffer full" not in preflight.lower()
os.chdir(REPO)
os.environ["BLENDER_USER_CONFIG"] = (
    "D:/codex/workspace/goo-engine/5.2.1-community/portable/config"
)
os.environ["BLENDER_USER_SCRIPTS"] = (
    "D:/codex/workspace/goo-engine/5.2.1-community/portable/scripts"
)
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path.insert(0, "D:/codex/temp/mmd-gallery-tools")
sys.path.insert(0, str(REPO / "scripts"))
sys.argv = [
    __file__,
    "--goo",
    "--abort-shadow-overflow",
    "--blender",
    "D:/codex/workspace/goo-engine/5.2.1-community/blender-5.2.1-git.0051aee0-windows64/blender.exe",
    "--root",
    str(ROOT),
    "--temp",
    "D:/codex/temp/MMD-Jelly-Eyes-v1/" + args.iteration,
    "--iteration",
    args.iteration,
    "--label",
    "GooToonShadow",
    "--project",
    str(PROJECT),
    "--profile",
    str(REPO / "presets/typography/duet-blue-gold-wedding-v1.json"),
]
from make_portrait_quick_preview import main

if __name__ == "__main__":
    main()
