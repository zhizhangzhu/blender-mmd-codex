import sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
register_addons()
bpy.ops.wm.open_mainfile(filepath='D:/codex/output/MMD-Jelly-Eyes-v1/production-v9/Franken_Duet_Goo_Eye_Hair_Stage.blend')
for name in ('前鬓','鬓.001'):
    tree=bpy.data.materials[name].node_tree
    done,active=set(),[]
    cycles=[]
    def visit(n):
        if n.name in active:
            cycles.append(active[active.index(n.name):]+[n.name]);return
        if n.name in done:return
        active.append(n.name)
        for s in n.inputs:
            for l in s.links:visit(l.from_node)
        active.pop();done.add(n.name)
    for n in tree.nodes:visit(n)
    print('DAG_CYCLES',name,cycles,flush=True)
    for n in tree.nodes:
        if n.name.startswith('Eye hair v1 | opaque hair') or n.name.endswith('one directional hair highlight') or n.name.endswith('one hair highlight application'):
            print('ROUTE',name,n.name,[(s.name,s.links[0].from_node.name if s.is_linked else str(getattr(s,'default_value',''))) for s in n.inputs],flush=True)
