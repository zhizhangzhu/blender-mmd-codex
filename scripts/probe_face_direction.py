"""Compare Face Factor light-direction conventions in independent stills."""

import json
import sys
import warnings
from pathlib import Path

import bpy

warnings.filterwarnings("ignore",category=DeprecationWarning)
root=Path(sys.argv[sys.argv.index("--")+1])
root.mkdir(parents=True,exist_ok=False)
scene=bpy.context.scene
scene.frame_set(4200)
scene.render.resolution_percentage=67
scene.eevee.taa_render_samples=24
scene.render.image_settings.media_type="IMAGE"
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_depth="8"
for n in scene.compositing_node_group.nodes:
    if n.type=="OUTPUT_FILE":n.mute=True
group=bpy.data.node_groups["Genshin study | festivities Face Factor | aether"]
dump=[]
for node in group.nodes:
    if node.type in ["VECT_MATH","MATH","COMBXYZ","SEPXYZ","REROUTE","GROUP"]:
        dump.append({"name":node.name,"type":node.bl_idname,"operation":getattr(node,"operation",None),"inputs":[{"index":i,"default":list(s.default_value) if hasattr(getattr(s,"default_value",None),"__len__") else getattr(s,"default_value",None),"links":[[l.from_node.name,list(l.from_node.outputs).index(l.from_socket)] for l in s.links]} for i,s in enumerate(node.inputs)]})
(root/"group-contract.json").write_text(json.dumps(dump,ensure_ascii=False,indent=2),encoding="utf-8")
normal=group.nodes["Vector Math.006"]
original=normal.inputs[0].links[0].from_socket
for label,sign in [("toward",1),("away",-1)]:
    if sign==1:group.links.new(original,normal.inputs[0])
    else:
        negate=group.nodes.new("ShaderNodeVectorMath")
        negate.operation="SCALE"
        negate.inputs[3].default_value=-1
        group.links.new(original,negate.inputs[0])
        group.links.new(negate.outputs[0],normal.inputs[0])
    scene.render.filepath=str(root/f"face-light-{label}.png")
    bpy.ops.render.render(write_still=True)
print("FACE_DIRECTION_CONTROLS_COMPLETE",str(root),flush=True)
