"""Fix the adapted Face Factor's incoming-vector contract in a new master."""

import argparse
import json
import sys
import warnings
from pathlib import Path

import bpy

warnings.filterwarnings("ignore", category=DeprecationWarning)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", type=Path, required=True)
parser.add_argument("--archive-dir", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
args.output_dir.mkdir(parents=True, exist_ok=False)
scene = bpy.context.scene
group = bpy.data.node_groups["Genshin study | festivities Face Factor | aether"]
assert (
    group.get("quality_light_vector_contract") != "incoming"
    and "Quality | incoming vector contract" not in group.nodes
), "Already adapted; do not negate twice"
normal = group.nodes["Vector Math.006"]
original = normal.inputs[0].links[0].from_socket
negate = group.nodes.new("ShaderNodeVectorMath")
negate.name = "Quality | incoming vector contract"
negate.operation = "SCALE"
negate.inputs[3].default_value = -1
group.links.new(original, negate.inputs[0])
group.links.new(negate.outputs[0], normal.inputs[0])
group["quality_light_vector_contract"] = "incoming"
archive = scene.compositing_node_group.nodes["Quality | scene-linear EXR archive"]
archive.directory = str(args.archive_dir)
archive.file_name = "duet_####"
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "16"
scene.render.resolution_percentage = 100
for frame in [4200, 4420]:
    scene.frame_set(frame)
    scene.render.filepath = str(args.output_dir / f"preview-{frame}.png")
    bpy.ops.render.render(write_still=True)
scene.frame_set(4140)
project = args.output_dir / "Franken_Duet_Quality_Master.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(project))
(args.output_dir / "face-contract.json").write_text(
    json.dumps(
        {
            "face_factor_light_vector": "head-minus-key (incoming)",
            "own_face_sdf_light_vector": "key-minus-head (towards key)",
            "reason": "Native opposite-sign still controls: front-lit face should not become globally shaded",
            "project": str(project),
        },
        indent=2,
    ),
    encoding="utf-8",
)
print("FACE_CONTRACT_MASTER_READY", str(project), flush=True)
