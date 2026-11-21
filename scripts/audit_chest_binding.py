"""Read full model/rigid bindings to identify supported chest motion chains."""

import json
import sys
from pathlib import Path

import bpy

scene = bpy.context.scene
report = {"project": bpy.data.filepath, "actors": []}
for arm in [o for o in scene.objects if o.type == "ARMATURE" and o.get("performer_id")]:
    actor = arm["performer_id"]
    meshes = [o for o in scene.objects if o.type == "MESH" and o.get("performer_id") == actor and o.modifiers.get("mmd_armature")]
    counts = {}
    for mesh in meshes:
        for vertex in mesh.data.vertices:
            for group in vertex.groups:
                if group.weight > .001:
                    name = mesh.vertex_groups[group.group].name
                    counts[name] = counts.get(name, 0) + 1
    bones = []
    for bone in arm.pose.bones:
        b = bone.bone
        bones.append({"name":bone.name,"name_j":bone.mmd_bone.name_j,"name_e":bone.mmd_bone.name_e,"parent":bone.parent.name if bone.parent else None,"head":list(b.head_local),"tail":list(b.tail_local),"weighted_vertices":counts.get(bone.name,0),"deform":b.use_deform,"constraints":[c.type+":"+c.name for c in bone.constraints]})
    rigids = []
    for obj in arm.parent.children_recursive:
        if obj.mmd_type == "RIGID_BODY":
            rigid = obj.mmd_rigid
            rigids.append({"name":obj.name,"bone":rigid.bone,"type":rigid.type,"shape":rigid.shape,"location":list(obj.location),"size":list(rigid.size),"physics":{p:getattr(obj.rigid_body,p,None) for p in ['mass','friction','linear_damping','angular_damping','restitution']}})
    joints = []
    for obj in arm.parent.children_recursive:
        if obj.mmd_type == "JOINT":
            c=obj.rigid_body_constraint
            joints.append({"name":obj.name,"first":c.object1.name if c and c.object1 else None,"second":c.object2.name if c and c.object2 else None,"settings":{p:getattr(c,p,None) for p in ['limit_lin_x_lower','limit_lin_x_upper','limit_lin_y_lower','limit_lin_y_upper','limit_lin_z_lower','limit_lin_z_upper','limit_ang_x_lower','limit_ang_x_upper','limit_ang_y_lower','limit_ang_y_upper','limit_ang_z_lower','limit_ang_z_upper','spring_stiffness_x','spring_stiffness_y','spring_stiffness_z','spring_stiffness_ang_x','spring_stiffness_ang_y','spring_stiffness_ang_z']}})
    report['actors'].append({'id':actor,'armature':arm.name,'meshes':[m.name for m in meshes],'bones':bones,'rigids':rigids,'joints':joints})
out=Path(sys.argv[-1]);out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('CHEST_BINDING_AUDIT_READY',flush=True)
