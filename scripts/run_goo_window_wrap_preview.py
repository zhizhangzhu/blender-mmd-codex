"""Render the broad-window, stronger-rim revision from the saved Goo master."""

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
    "D:/codex/output/MMD-Goo-Window-Wrap-v1",
    "--temp",
    "D:/codex/temp/MMD-Goo-Window-Wrap-v1/quick-5s-v3",
    "--iteration",
    "quick-5s-v3",
    "--label",
    "GooWindowWrap",
    "--project",
    "D:/codex/output/MMD-Goo-Window-Wrap-v1/production-v3/Franken_Duet_Goo_Window_Wrap.blend",
]
from make_portrait_quick_preview import main

if __name__ == "__main__":
    main()
