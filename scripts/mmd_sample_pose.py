"""Export selected evaluated bone matrices for before/after integration checks."""

import argparse
import bpy
import json
import sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--frames", type=int, nargs="+", required=True)
p.add_argument("--output", type=Path, required=True)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
names = [
    "頭",
    "手首.L",
    "手首.R",
    "足首.L",
    "足首.R",
    "qun_0_5",
    "pj_0_5",
    "Bone_HairB01_L",
]
report = {}
for frame in args.frames:
    bpy.context.scene.frame_set(frame)
    report[str(frame)] = {
        n: {
            "location": list(arm.pose.bones[n].matrix.translation),
            "quaternion": list(arm.pose.bones[n].matrix.to_quaternion()),
        }
        for n in names
    }
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("x", encoding="utf-8") as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print("POSE_SAMPLES_OK", args.output)
