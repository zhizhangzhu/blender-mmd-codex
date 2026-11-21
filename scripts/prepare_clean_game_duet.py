"""Build a new, character-only clean NPR revision from the caption-fixed v7."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean_aksiniya_materials
import clean_ikhor_materials

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692"


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
    scene = bpy.context.scene
    crypto = scene.compositing_node_group.nodes["Caption | both performers native object coverage"]
    crypto_before = crypto.matte_id
    assert "Ikhor | mesh | Ikhor_mesh" in crypto_before and "空_mesh" not in crypto_before
    profiles, modules, reports = {}, {}, {}
    for actor, module in [("aksiniya", clean_aksiniya_materials), ("ikhor", clean_ikhor_materials)]:
        path = ROOT / "presets/quality" / f"{actor}-clean-game-v1.json"
        spec = json.loads(path.read_text(encoding="utf-8-sig"))
        profiles[actor] = {"path": str(path), "sha256": sha(path), "data": spec}
        modules[actor] = {"path": module.__file__, "sha256": sha(module.__file__)}
        reports[actor] = module.apply(scene, spec)
    assert crypto.matte_id == crypto_before
    scene["clean_game_refinement"] = "duet-clean-game-v1"
    scene["clean_game_source_sha256"] = SOURCE_SHA
    bpy.context.view_layer.update()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    project = args.output_dir / "Franken_Duet_Clean_Game.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project), compress=True)
    report = {
        "id": "duet-clean-game-v1", "source": str(source), "source_sha256": SOURCE_SHA,
        "project": str(project), "project_sha256": sha(project),
        "profiles": profiles, "modules": modules, "implementation": reports,
        "caption_crypto_targets": crypto.matte_id,
        "scope": "Character material refinement only; original bodies, sleeve repair, choreography, scene, lights, exposure, camera and caption targets retained. Independent reopen and render verification pending.",
        "render_complete": False, "full_song_complete": False, "user_art_approval": False,
    }
    (args.output_dir / "preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert sha(source) == SOURCE_SHA
    print("CLEAN_GAME_CANDIDATE_SAVED", report["project_sha256"], flush=True)


if __name__ == "__main__":
    main()
