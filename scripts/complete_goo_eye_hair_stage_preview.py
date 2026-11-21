"""Wait for the existing orphaned render, then encode its completed native cache."""

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("D:/codex/output/MMD-Jelly-Eyes-v1")
TEMP = Path("D:/codex/temp/MMD-Jelly-Eyes-v1/quick-5s-v4")
os.chdir(REPO)
sys.path.insert(0, "D:/codex/temp/mmd-gallery-tools")
sys.path.insert(0, str(REPO / "scripts"))
last = None
while not (TEMP / "render-complete.json").is_file():
    progress = json.loads((TEMP / "progress.json").read_text(encoding="utf-8"))
    if progress["rendered"] != last:
        last = progress["rendered"]
        print("WAIT_EXISTING_RENDER", last, "/150", flush=True)
    if time.time() - (TEMP / "progress.json").stat().st_mtime > 1800:
        raise RuntimeError("Existing render progress has not advanced for 30 minutes")
    time.sleep(5)
from make_portrait_quick_preview import main

sys.argv = [
    __file__,
    "--root",
    str(ROOT),
    "--temp",
    str(TEMP),
    "--iteration",
    "quick-5s-v4",
    "--label",
    "GooEyeHairStage",
    "--project",
    str(ROOT / "production-v4/Franken_Duet_Goo_Eye_Hair_Stage.blend"),
    "--profile",
    str(REPO / "presets/typography/duet-blue-gold-wedding-v1.json"),
    "--reuse-cache",
]
if __name__ == "__main__":
    main()
