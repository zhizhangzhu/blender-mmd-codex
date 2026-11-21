"""Repair stale character names in the caption-only Cryptomatte selection."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

SOURCE_SHA = "201e2632befaf0a16f17b931963626a91bbc6b8f7e58d148d5047298a530de01"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    source = Path(bpy.data.filepath)
    assert sha(source) == SOURCE_SHA
    scene = bpy.context.scene
    tree = scene.compositing_node_group
    node = tree.nodes["Caption | both performers native object coverage"]
    output = tree.nodes["Caption cache | actor"]
    assert node.bl_idname == "CompositorNodeCryptomatteV2"
    assert len(output.inputs[0].links) == 1
    assert output.inputs[0].links[0].from_node == node
    assert output.inputs[0].links[0].from_socket.name == "Matte"
    assert not any(link.from_node == node and link.to_node != output for link in tree.links), "The changed Crypto must feed caption matte only"
    actors = {}
    for actor in ("aksiniya", "ikhor"):
        actors[actor] = sorted(
            obj.name for obj in scene.objects
            if obj.type == "MESH" and obj.get("performer_id") == actor
            and not obj.hide_render and obj.visible_get()
        )
        assert actors[actor], actor
    old = node.matte_id
    new = ",".join(name for names in actors.values() for name in names)
    assert "Ikhor | mesh | Ikhor_mesh" in new and "空_mesh" not in new
    assert old != new
    args.output_dir.mkdir(parents=True, exist_ok=False)
    node.matte_id = new
    project = args.output_dir / "Franken_Aksiniya_Ikhor_Bold_Wedding.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project), compress=True)
    report = {
        "source": str(source), "source_sha256": SOURCE_SHA,
        "project": str(project), "project_sha256": sha(project),
        "changed_node": node.name, "old_matte_id": old, "new_matte_id": new,
        "current_actor_meshes": actors,
        "beauty_output_graph_changed": False,
        "scope": "Caption-only Cryptomatte selection; original geometry, materials, actions, camera, lights, image output and beauty dependencies retained. Independent verification required.",
        "final_caption_reencoded": False,
    }
    (args.output_dir / "caption-target-repair.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("CAPTION_TARGETS_REPAIRED", report["project_sha256"], new, flush=True)


if __name__ == "__main__":
    main()
