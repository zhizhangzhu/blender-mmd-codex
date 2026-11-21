"""Read local Blender APIs needed by the tutorial lighting/outline lab."""

import bpy
import json

s = bpy.context.scene
root = next(o for o in s.objects if getattr(o, "mmd_type", None) == "ROOT")
print("ROOT_DISPLAY_SIZE", root.empty_display_size)
print(
    "EDGE_MATERIALS",
    json.dumps(
        [
            {
                "name": m.name,
                "enabled": m.mmd_material.enabled_toon_edge,
                "weight": m.mmd_material.edge_weight,
                "alpha": m.mmd_material.alpha,
            }
            for m in bpy.data.materials
            if m.node_tree and m.node_tree.nodes.get("mmd_shader")
        ],
        ensure_ascii=False,
    ),
)
t = bpy.data.node_groups.new("Tutorial API probe", "CompositorNodeTree")
n = t.nodes.new("CompositorNodeGlare")
print(
    "GLARE_INPUTS",
    [
        (i.name, str(i.default_value) if hasattr(i, "default_value") else "")
        for i in n.inputs
    ],
)
print(
    "GLARE_PROPERTIES",
    [
        (p.identifier, p.type)
        for p in n.bl_rna.properties
        if p.identifier in {"glare_type", "quality", "threshold", "size", "mix"}
    ],
)
print("GLARE_OUTPUTS", [i.name for i in n.outputs])
for kind in [
    "ShaderNodeMix",
    "ShaderNodeMixRGB",
    "ShaderNodeMath",
    "CompositorNodeMath",
]:
    try:
        candidate = t.nodes.new(kind)
        if kind == "ShaderNodeMix":
            candidate.data_type = "RGBA"
        print(
            "COMPOSITOR_NODE",
            kind,
            [(i.name, i.enabled) for i in candidate.inputs],
            [o.name for o in candidate.outputs],
        )
    except RuntimeError:
        print("COMPOSITOR_NODE_UNAVAILABLE", kind)
for kind in ["Fog Glow", "FOG_GLOW"]:
    try:
        n.inputs["Type"].default_value = kind
        print("GLARE_TYPE_ACCEPTED", kind)
    except TypeError:
        pass
sh = bpy.data.node_groups.new("Tutorial shader API probe", "ShaderNodeTree")
aov_node = sh.nodes.new("ShaderNodeOutputAOV")
print(
    "AOV_PROPERTIES",
    [
        (p.identifier, p.type)
        for p in aov_node.bl_rna.properties
        if "aov" in p.identifier or p.identifier == "name"
    ],
)
aov = s.view_layers[0].aovs.add()
aov.name, aov.type = "TutorialGlow", "VALUE"
s.view_layers[0].use_pass_material_index = True
s.view_layers[0].update_render_passes()
r = t.nodes.new("CompositorNodeRLayers")
r.scene = s
print("RENDER_LAYER_OUTPUTS", [i.name for i in r.outputs])
bpy.data.node_groups.remove(sh)
print(
    "COMPOSITOR",
    [
        (p.identifier, p.type)
        for p in s.bl_rna.properties
        if "composit" in p.identifier
        or "node_tree" in p.identifier
        or p.identifier == "use_nodes"
    ],
)
print(
    "CAMERA_SENSORS",
    s.camera.data.sensor_fit,
    s.camera.data.sensor_height,
    s.camera.data.lens,
)
bpy.data.node_groups.remove(t)
