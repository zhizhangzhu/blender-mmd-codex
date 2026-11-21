"""Inspect locally supported compositor matte and text-output APIs."""

import bpy

s = bpy.context.scene
layer = s.view_layers[0]
layer.use_pass_cryptomatte_object = True
layer.use_pass_cryptomatte_material = True
layer.update_render_passes()
t = bpy.data.node_groups.new("Caption API probe", "CompositorNodeTree")
for kind in [
    "CompositorNodeRLayers",
    "CompositorNodeCryptomatteV2",
    "CompositorNodeOutputFile",
    "ShaderNodeMath",
]:
    n = t.nodes.new(kind)
    if kind == "CompositorNodeRLayers":
        n.scene = s
    print(
        "CAPTION_NODE",
        kind,
        "INPUTS",
        [i.name for i in n.inputs],
        "OUTPUTS",
        [i.name for i in n.outputs],
    )
    if kind in {"CompositorNodeCryptomatteV2", "CompositorNodeOutputFile"}:
        print(
            "CAPTION_PROPERTIES",
            [(p.identifier, p.type) for p in n.bl_rna.properties if not p.is_readonly],
        )
    if kind == "CompositorNodeOutputFile":
        print(
            "FILE_MEDIA",
            [
                (p.identifier, [(i.identifier, i.name) for i in p.enum_items])
                for p in n.format.bl_rna.properties
                if p.type == "ENUM" and p.identifier in {"media_type", "file_format"}
            ],
        )
        print(
            "FILE_COLLECTIONS",
            [
                (p.identifier, p.type)
                for p in n.bl_rna.properties
                if p.type in {"COLLECTION", "POINTER"}
            ],
        )
        for name in ["file_output_items", "file_slots", "layer_slots"]:
            items = getattr(n, name, None)
            if items is not None:
                print(
                    "FILE_ITEMS",
                    name,
                    [(p.identifier, p.type) for p in items.bl_rna.properties],
                    [f.identifier for f in items.bl_rna.functions],
                )
                print(
                    "FILE_NEW_PARAMETERS",
                    [
                        (
                            p.identifier,
                            p.type,
                            [i.identifier for i in p.enum_items]
                            if p.type == "ENUM"
                            else "",
                        )
                        for p in items.bl_rna.functions["new"].parameters
                    ],
                )
                try:
                    item = items.new("RGBA", "beauty")
                    print(
                        "FILE_NEW_OK",
                        [(p.identifier, p.type) for p in item.bl_rna.properties],
                        [i.name for i in n.inputs],
                    )
                except Exception as exc:
                    print("FILE_NEW_ERROR", str(exc))
                if len(items):
                    print(
                        "FILE_ITEM_PROPERTIES",
                        [(p.identifier, p.type) for p in items[0].bl_rna.properties],
                    )
    if kind == "CompositorNodeCryptomatteV2":
        n.scene = s
        for name in ["layer_name", "matte_id", "source"]:
            print("CRYPTO_PROPERTY", name, getattr(n, name, "ABSENT"))
print(
    "CHARACTER_MESHES",
    [
        o.name
        for o in s.objects
        if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)
    ],
)
bpy.data.node_groups.remove(t)
