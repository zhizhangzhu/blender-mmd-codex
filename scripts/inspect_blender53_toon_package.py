"""Read a pinned private toon package with scripts disabled; never render/save it."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy


def plain(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, bpy.types.ID):
        return {"id": value.name_full, "type": value.bl_rna.identifier}
    if hasattr(value, "items"):
        return {str(key): plain(item) for key, item in value.items()}
    try:
        return [plain(item) for item in value]
    except TypeError:
        return str(value)


def settings(owner):
    result = {}
    for prop in owner.bl_rna.properties:
        key = prop.identifier
        if key == "rna_type" or prop.type in {"COLLECTION", "POINTER"}:
            continue
        if key in {"dimensions", "width", "height", "location", "select"}:
            continue
        try:
            result[key] = plain(getattr(owner, key))
        except (AttributeError, TypeError, ValueError):
            result[key] = "unavailable"
    return result


def socket_record(socket):
    return {
        "name": socket.name,
        "identifier": socket.identifier,
        "bl_idname": socket.bl_idname,
        "type": socket.type,
        "enabled": socket.enabled,
        "linked": socket.is_linked,
        "value": plain(getattr(socket, "default_value", None)),
    }


def tree_record(tree):
    return {
        "type": tree.bl_idname,
        "nodes": [
            {
                "name": node.name,
                "label": node.label,
                "bl_idname": node.bl_idname,
                "type": node.type,
                "settings": settings(node),
                "group": node.node_tree.name
                if getattr(node, "node_tree", None)
                else None,
                "image": node.image.name if getattr(node, "image", None) else None,
                "inputs": [socket_record(s) for s in node.inputs],
                "outputs": [socket_record(s) for s in node.outputs],
            }
            for node in tree.nodes
        ],
        "links": [
            {
                "from": [link.from_node.name, link.from_socket.identifier],
                "to": [link.to_node.name, link.to_socket.identifier],
                "valid": link.is_valid,
            }
            for link in tree.links
        ],
        "interface": [
            {
                "name": item.name,
                "item_type": item.item_type,
                "in_out": getattr(item, "in_out", None),
                "socket_type": getattr(item, "socket_type", None),
                "default": plain(getattr(item, "default_value", None)),
            }
            for item in tree.interface.items_tree
        ],
    }


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    assert sha(args.project) == args.expected_sha
    assert not args.output.exists()
    assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
    bpy.ops.wm.open_mainfile(
        filepath=str(args.project), load_ui=False, use_scripts=False
    )
    assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
    trees, tree_labels, tree_owners = {}, {}, {}

    def add_tree(label, tree):
        key = tree.as_pointer()
        if key not in trees:
            trees[key] = tree
            tree_labels[key] = label
            tree_owners[key] = []
        tree_owners[key].append(label)

    for group in bpy.data.node_groups:
        add_tree("Group/" + group.name, group)
    for owner_type, kind in (
        ("Material", bpy.data.materials),
        ("Light", bpy.data.lights),
        ("World", bpy.data.worlds),
    ):
        for owner in kind:
            tree = owner.node_tree
            if tree:
                add_tree(owner_type + "/" + owner.name, tree)
    for scene in bpy.data.scenes:
        tree = getattr(scene, "compositing_node_group", None)
        if tree:
            add_tree("SceneCompositor/" + scene.name, tree)
    muted = []
    for tree in trees.values():
        for node in tree.nodes:
            if node.type == "OUTPUT_FILE":
                muted.append(
                    {"tree": tree.name, "node": node.name, "was_muted": node.mute}
                )
                node.mute = True
    report = {
        "project": str(args.project),
        "project_sha256": sha(args.project),
        "runtime": {
            "version": list(bpy.app.version),
            "build": bpy.app.build_hash.decode(),
            "binary": bpy.app.binary_path,
        },
        "saved_file_version": plain(getattr(bpy.data, "version", None)),
        "scripts_auto_execute": bpy.context.preferences.filepaths.use_scripts_auto_execute,
        "file_outputs_muted_in_memory": muted,
        "scene": {
            scene.name: {
                "frame": scene.frame_current,
                "range": [scene.frame_start, scene.frame_end],
                "engine": scene.render.engine,
                "camera": plain(scene.camera),
                "resolution": [
                    scene.render.resolution_x,
                    scene.render.resolution_y,
                    scene.render.resolution_percentage,
                ],
                "view": settings(scene.view_settings),
                "render": settings(scene.render),
                "rigid_body_world": (
                    {"enabled": getattr(scene.rigidbody_world, "enabled", None)}
                    if scene.rigidbody_world
                    else None
                ),
            }
            for scene in bpy.data.scenes
        },
        "objects": [
            {
                "name": obj.name,
                "type": obj.type,
                "parent": plain(obj.parent),
                "data": plain(obj.data),
                "hide_render": obj.hide_render,
                "materials": [
                    slot.material.name if slot.material else None
                    for slot in obj.material_slots
                ],
                "vertex_groups": [g.name for g in obj.vertex_groups]
                if obj.type == "MESH"
                else [],
                "modifiers": [
                    {"name": m.name, "type": m.type, "show_render": m.show_render}
                    for m in obj.modifiers
                ],
            }
            for obj in bpy.data.objects
        ],
        "images": [
            {
                "name": image.name,
                "filepath": image.filepath,
                "source": image.source,
                "packed": bool(image.packed_file),
                "size": list(image.size),
                "colorspace": image.colorspace_settings.name,
                "alpha_mode": image.alpha_mode,
            }
            for image in bpy.data.images
        ],
        "meshes": [
            {
                "name": mesh.name,
                "vertices": len(mesh.vertices),
                "polygons": len(mesh.polygons),
                "uv_layers": [uv.name for uv in mesh.uv_layers],
                "shape_keys": [key.name for key in mesh.shape_keys.key_blocks]
                if mesh.shape_keys
                else [],
            }
            for mesh in bpy.data.meshes
        ],
        "lights": [
            {
                "object": obj.name,
                "data": obj.data.name,
                "settings": settings(obj.data),
                "object_custom_properties": plain(dict(obj.items())),
                "data_custom_properties": plain(dict(obj.data.items())),
            }
            for obj in bpy.data.objects
            if obj.type == "LIGHT"
        ],
        "texts": [
            {
                "name": text.name,
                "use_module": text.use_module,
                "content": text.as_string(),
            }
            for text in bpy.data.texts
        ],
        "trees": {tree_labels[key]: tree_record(tree) for key, tree in trees.items()},
        "tree_owners": {
            tree_labels[key]: owners for key, owners in tree_owners.items()
        },
        "rendered": False,
        "saved": False,
    }
    report["undefined_nodes"] = [
        {"tree": name, "node": node["name"], "bl_idname": node["bl_idname"]}
        for name, tree in report["trees"].items()
        for node in tree["nodes"]
        if "Undefined" in node["bl_idname"] or node["type"] == "UNDEFINED"
    ]
    assert sha(args.project) == args.expected_sha
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "TOON_PACKAGE_READONLY_INSPECTED",
        args.output,
        "undefined",
        len(report["undefined_nodes"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
