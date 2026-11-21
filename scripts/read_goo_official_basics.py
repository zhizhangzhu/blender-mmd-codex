"""Cache selected official Goo source files privately for parameter study."""

import hashlib
import json
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

BRANCH = "goo-engine-v4.4-release"
OUT = Path("D:/codex/temp/Goo-Official-Basics-2026-11-17") / BRANCH
OUT.mkdir(parents=True, exist_ok=True)
REPO = "dillongoostudios/goo-engine"
API = "https://api.github.com/repos/" + REPO


def get(url):
    request = Request(url, headers={"User-Agent": "Codex-Goo-Basics-Study"})
    with urlopen(request, timeout=35) as response:
        return response.read()


lock = OUT / "source-lock.json"
if lock.exists():
    commit = json.loads(lock.read_text(encoding="utf-8"))["commit"]
else:
    commit = json.loads(get(API + "/commits/" + BRANCH))["sha"]
    lock.write_text(
        json.dumps({"repo": REPO, "branch": BRANCH, "commit": commit}, indent=2),
        encoding="utf-8",
    )
directory = "source/blender/nodes/shader/nodes"
tree_file = OUT / "shader-node-files.json"
if not tree_file.exists():
    tree_file.write_bytes(get(API + "/contents/" + directory + "?ref=" + commit))
entries = json.loads(tree_file.read_text(encoding="utf-8"))
selected = [
    e
    for e in entries
    if any(
        s in e["name"]
        for s in (
            "shader_info",
            "light_info",
            "screenspace",
            "curvature",
            "set_depth",
            "node_shader_sdf",
            "hexagon",
            "hex_grid",
            "water_ripples",
            "twirl",
            "oklab",
        )
    )
]


def fetch(entry):
    url = (
        "https://raw.githubusercontent.com/" + REPO + "/" + commit + "/" + entry["path"]
    )
    path = OUT / entry["name"]
    try:
        if not path.exists():
            data = json.loads(
                get(API + "/contents/" + entry["path"] + "?ref=" + commit)
            )
            path.write_bytes(b64decode(data["content"]))
        return {
            "path": entry["path"],
            "private_file": str(path),
            "url": url,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    except (OSError, ValueError, KeyError) as error:
        return {"path": entry["path"], "url": url, "acquisition_error": str(error)}


with ThreadPoolExecutor(max_workers=3) as executor:
    manifest = list(executor.map(fetch, selected))
(OUT / "sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps({"commit": commit, "files": [e["path"] for e in manifest]}, indent=2))
