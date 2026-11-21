"""Render the final window-air / white-blue rim look from its saved Goo master."""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
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
    "--blender",
    "D:/codex/workspace/goo-engine/5.2.1-community/blender-5.2.1-git.0051aee0-windows64/blender.exe",
    "--root",
    "D:/codex/output/MMD-Goo-Tyndall-Rim-v1",
    "--temp",
    "D:/codex/temp/MMD-Goo-Tyndall-Rim-v1/quick-5s-v1",
    "--iteration",
    "quick-5s-v1",
    "--label",
    "GooTyndallRim",
    "--project",
    "D:/codex/output/MMD-Goo-Tyndall-Rim-v1/production-v7/Franken_Duet_Goo_Tyndall_Rim.blend",
]
from make_portrait_quick_preview import main

if __name__ == "__main__":
    main()
