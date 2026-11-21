"""Hide the two user-rejected wedding light arcs in a new saved revision."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

SOURCE_SHA = "8425c1827fd296fe19e17225e5e1e748de249bf11cae25ff888c6b010242f993"
NAMES = ("Bold wedding | blue vow arc", "Bold wedding | gold vow arc")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    source = Path(bpy.data.filepath)
    assert sha(source) == SOURCE_SHA
    assert not args.output_dir.exists()
    changes = []
    for name in NAMES:
        obj = bpy.data.objects[name]
        assert obj.type == "CURVE" and obj.get("bold_wedding_fx")
        changes.append({"object": name, "before": {"hide_render": obj.hide_render, "hide_viewport": obj.hide_viewport},
                        "after": {"hide_render": True, "hide_viewport": True}})
        obj.hide_render = True
        obj.hide_viewport = True
    args.output_dir.mkdir(parents=True)
    project = args.output_dir / "Franken_Duet_Clean_Game.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project), compress=True)
    report = {"source": str(source), "source_sha256": SOURCE_SHA,
              "project": str(project), "project_sha256": sha(project), "changes": changes,
              "scope": "Only these two visible curve effects disabled in render and viewport, as requested; stage geometry/lights and prior irradiance cache retained. Original arc data remains reversible.",
              "user_requested": True}
    (args.output_dir / "arc-removal.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WEDDING_ARCS_REMOVED", report["project_sha256"], flush=True)


if __name__ == "__main__":
    main()
