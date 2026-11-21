"""Read live character shader paths without rendering or saving the source."""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def val(value):
    if isinstance(value,bpy.types.ID):
        return value.name
    if hasattr(value,"__len__") and not isinstance(value,str):
        return list(value)
    return value


def socket(s):
    return {"name":s.name,"identifier":s.identifier,"type":s.type,"value":val(getattr(s,"default_value",None)),"from":[[l.from_node.name,l.from_socket.name,l.from_socket.identifier] for l in s.links]}


def upstream(output):
    seen=set()
    def visit(n):
        if n.name in seen:
            return
        seen.add(n.name)
        for s in n.inputs:
            for l in s.links: visit(l.from_node)
    visit(output)
    return sorted(seen)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    a.output_dir.mkdir(parents=True,exist_ok=False)
    scene=bpy.context.scene
    for other in bpy.data.scenes:
        if other.compositing_node_group:
            for node in other.compositing_node_group.nodes:
                if node.type=="OUTPUT_FILE":node.mute=True
    scene.frame_set(4290)
    bpy.context.view_layer.update()
    result={"source":bpy.data.filepath,"frame":scene.frame_current,"read_only":True,"rendered":False,"saved_source":False,"materials":[],"lights":[],"helpers":[],"color":{k:getattr(scene.view_settings,k) for k in ("view_transform","look","exposure","gamma")},"world":scene.world.name if scene.world else None,"samples":scene.eevee.taa_render_samples}
    for mat in bpy.data.materials:
        if not mat.get("performer_id") or not mat.node_tree:
            continue
        tree=mat.node_tree
        output=next((n for n in tree.nodes if n.type=="OUTPUT_MATERIAL" and n.is_active_output),None)
        if output is None:continue
        active=upstream(output)
        nodes=[]
        for n in tree.nodes:
            if n.name not in active:continue
            record={"name":n.name,"type":n.bl_idname,"inputs":[socket(s) for s in n.inputs],"outputs":[{"name":s.name,"identifier":s.identifier} for s in n.outputs]}
            if n.type=="GROUP":record["group"]=n.node_tree.name if n.node_tree else None
            if hasattr(n,"operation"):record["operation"]=n.operation
            if hasattr(n,"blend_type"):record["blend_type"]=n.blend_type
            if n.type=="TEX_IMAGE" and n.image:record["image"]={"name":n.image.name,"path":n.image.filepath,"packed":bool(n.image.packed_file),"colorspace":n.image.colorspace_settings.name,"alpha_mode":n.image.alpha_mode}
            if n.type=="VALTORGB":record["ramp"]=[{"position":e.position,"color":list(e.color)} for e in n.color_ramp.elements]
            nodes.append(record)
        result["materials"].append({"name":mat.name,"actor":mat.get("performer_id"),"source_mmd":mat.get("source_mmd_material_name"),"category":mat.get("aether_surface",mat.get("look_category")),"active_nodes":nodes,"all_node_names":[n.name for n in tree.nodes],"drivers":[{"path":d.data_path,"index":d.array_index,"expression":d.driver.expression} for d in tree.animation_data.drivers] if tree.animation_data else []})
    for obj in scene.objects:
        if obj.type=="LIGHT":
            d=obj.data
            result["lights"].append({"name":obj.name,"type":d.type,"location":list(obj.matrix_world.translation),"hidden":obj.hide_render,"watts":d.energy,"color":list(d.color),"size":getattr(d,"size",None),"radius":getattr(d,"shadow_soft_size",None),"diffuse_factor":d.diffuse_factor,"specular_factor":d.specular_factor,"volume_factor":d.volume_factor,"shadows":d.use_shadow,"receivers":[o.name for o in obj.light_linking.receiver_collection.all_objects] if obj.light_linking.receiver_collection else None,"blockers":[o.name for o in obj.light_linking.blocker_collection.all_objects] if obj.light_linking.blocker_collection else None})
        if obj.name.startswith("Quality |") and "head" in obj.name:
            result["helpers"].append({"name":obj.name,"position":list(obj.matrix_world.translation)})
    (a.output_dir/"live-character-contract.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("CHARACTER_CONTRACT_PROBE_READY",len(result["materials"]),flush=True)


if __name__=="__main__":main()
