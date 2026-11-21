"""Replace the Hina slot with an independently baked Ikhor in a new hall copy.

This tool accepts only the inspected Bold Wedding v2 master and the verified
Ikhor collection. It does not import an FBX, rebuild the existing cast, run live
physics, or retime the already retimed animation again.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from genshin_material_adapt import head_axes
from ikhor_character_materials import apply_ikhor_materials
from mmd_hesperides_stage import aim
from prepare_bold_wedding import mute_outputs
from verify_duet_integration import snapshot

SOURCE_SHA = "ff05b52f9c64283f8909c41ed7fbc601cfa0034a94df7483690cf688d9d6a694"
FRAMES = [1, 2100, 4140, 4200, 4250, 4290, 4439, 8400, 11899]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1048576), b""):
            h.update(part)
    return h.hexdigest()


def keep_snapshot(scene):
    result = snapshot(scene)
    result["actors"] = {"aksiniya": result["actors"]["aksiniya"]}
    return result


def new_helpers(scene, arm):
    controller = head_axes(scene, arm)
    for label in ("origin", "forward", "up"):
        previous = f"Genshin study | world head {label} | ikhor"
        obj = scene.objects[previous]
        obj.name = f"Quality | ikhor | head {label}"
        obj["performer_id"] = "ikhor"
    controller["performer_id"] = "ikhor"
    return controller


def install_edges(scene, root, materials):
    # Retain source enabled-edge/vertex semantics. Only palette and thickness
    # are adjusted; eye and ink planes are not given a new opaque silhouette.
    before = {m.as_pointer() for m in bpy.data.materials}
    for material in materials:
        if material.mmd_material.alpha <= 0.001:
            material.mmd_material.enabled_toon_edge = False
            material.mmd_material.edge_color = (0, 0, 0, 0)
            continue
        role = material.get("ikhor_role", material.get("look_category", "cloth"))
        if not material.mmd_material.enabled_toon_edge:
            continue
        material.mmd_material.edge_color = (
            (0.065, 0.018, 0.025, 0.94)
            if role in {"face", "skin"}
            else (0.008, 0.010, 0.022, 1.0)
        )
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    assert bpy.ops.mmd_tools.edge_preview_setup(action="CREATE") == {"FINISHED"}
    modifiers = []
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        obj["performer_id"] = "ikhor"
        mod = obj.modifiers.get("mmd_edge_preview")
        if mod:
            original = mod.thickness
            mod.thickness *= 0.58
            modifiers.append(
                {
                    "mesh": obj.name,
                    "source_thickness": original,
                    "thickness": mod.thickness,
                }
            )
    for material in bpy.data.materials:
        if material.as_pointer() in before:
            continue
        material["performer_id"] = "ikhor"
        material["ikhor_role"] = "outline"
        if material.node_tree:
            aov = material.node_tree.nodes.new("ShaderNodeOutputAOV")
            aov.aov_name = "ReferenceDuetActor"
            edge_shader = material.node_tree.nodes.get("mmd_edge_preview")
            assert edge_shader and edge_shader.inputs.get("Alpha")
            alpha = edge_shader.inputs["Alpha"]
            if alpha.is_linked:
                material.node_tree.links.new(
                    alpha.links[0].from_socket, aov.inputs["Value"]
                )
            else:
                aov.inputs["Value"].default_value = alpha.default_value
    return modifiers


def artist_beam_volume(scene):
    """Add deliberately art-directed luminous cone volumes behind the duet.

    The real spots remain for stage lighting. These soft radial emission
    volumes are a separate visible effect, not evidence of physical spot-light
    scattering/shadow restoration. They never extend into the actor area.
    """
    records = []
    for lamp in [
        o
        for o in scene.objects
        if o.type == "LIGHT"
        and o.name.startswith("Bold wedding |")
        and " beam " in o.name
    ]:
        origin = lamp.matrix_world.translation.copy()
        axis = lamp.matrix_world.to_quaternion() @ Vector((0, 0, -1))
        length = 4.7
        center = origin + axis * length / 2
        bpy.ops.mesh.primitive_cone_add(
            vertices=24, radius1=0.012, radius2=0.21, depth=length, location=center
        )
        obj = bpy.context.object
        obj.name = lamp.name.replace(" beam ", " luminous volume ")
        obj.rotation_euler = axis.to_track_quat("Z", "Y").to_euler()
        obj["bold_wedding_fx"] = True
        material = bpy.data.materials.new(obj.name)
        material.use_nodes = True
        tree = material.node_tree
        tree.nodes.clear()

        def scalar(operation, a, b=None, node_tree=tree):
            n = node_tree.nodes.new("ShaderNodeMath")
            n.operation = operation
            for s, v in zip(n.inputs, [a, b]):
                if v is None:
                    continue
                if hasattr(v, "is_output"):
                    node_tree.links.new(v, s)
                else:
                    s.default_value = v
            return n.outputs[0]

        def smooth(value, lo, hi, node_tree=tree):
            n = node_tree.nodes.new("ShaderNodeMapRange")
            n.clamp = True
            n.interpolation_type = "SMOOTHSTEP"
            node_tree.links.new(value, n.inputs["Value"])
            n.inputs["From Min"].default_value = lo
            n.inputs["From Max"].default_value = hi
            return n.outputs[0]

        coordinates = tree.nodes.new("ShaderNodeTexCoord")
        split = tree.nodes.new("ShaderNodeSeparateXYZ")
        tree.links.new(coordinates.outputs["Generated"], split.inputs[0])
        x = scalar("MULTIPLY_ADD", split.outputs["X"], 2)
        x.node.inputs[2].default_value = -1
        y = scalar("MULTIPLY_ADD", split.outputs["Y"], 2)
        y.node.inputs[2].default_value = -1
        radius = scalar(
            "SQRT", scalar("ADD", scalar("MULTIPLY", x, x), scalar("MULTIPLY", y, y))
        )
        fraction = scalar("MULTIPLY_ADD", split.outputs["Z"], 0.95)
        fraction.node.inputs[2].default_value = 0.05
        normalized = scalar("DIVIDE", radius, fraction)
        radial = scalar("SUBTRACT", 1, smooth(normalized, 0.25, 0.96))
        axial = scalar(
            "MULTIPLY",
            smooth(split.outputs["Z"], 0.015, 0.10),
            scalar("SUBTRACT", 1, smooth(split.outputs["Z"], 0.78, 1.0)),
        )
        value = scalar("MULTIPLY", scalar("MULTIPLY", radial, axial), 1.15)
        volume = tree.nodes.new("ShaderNodeVolumePrincipled")
        volume.name = "Wedding art | luminous shaft, not physical scatter"
        volume.inputs["Density"].default_value = 0.001
        volume.inputs["Color"].default_value = (*lamp.data.color, 1)
        volume.inputs["Emission Color"].default_value = (*lamp.data.color, 1)
        tree.links.new(value, volume.inputs["Emission Strength"])
        output = tree.nodes.new("ShaderNodeOutputMaterial")
        tree.links.new(volume.outputs[0], output.inputs["Volume"])
        obj.data.materials.append(material)
        records.append(
            {
                "object": obj.name,
                "source_spot": lamp.name,
                "origin": list(origin),
                "length": length,
                "strength": 1.15,
                "method": "soft radial art-directed volume emission",
            }
        )
    return records


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--actor", type=Path, required=True)
    p.add_argument("--actor-report", type=Path, required=True)
    p.add_argument("--profile", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--stills", type=int, nargs="*", default=[4250, 4290])
    p.add_argument("--percentage", type=int, default=67)
    p.add_argument("--art-beams", action="store_true")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    source = Path(bpy.data.filepath)
    assert sha(source) == SOURCE_SHA
    scene = bpy.context.scene
    assert scene.get("bold_wedding_revision") == "hesperides-bold-wedding-v1"
    assert not scene.get("ikhor_wedding_revision") and scene.rigidbody_world is None
    actor_report = json.loads(args.actor_report.read_text(encoding="utf-8-sig"))
    # The integrator requires the producer's verified append manifest, never a
    # candidate filename or baked-cache flag as a proxy for real simulation.
    assert actor_report.get("passed") is True
    actor_sha = sha(args.actor)
    assert actor_report["project_sha256"] == actor_sha
    args.output_dir.mkdir(parents=True, exist_ok=False)
    mute_outputs()
    old_poses = {}
    for frame in FRAMES:
        scene.frame_set(frame)
        old_poses[frame] = keep_snapshot(scene)
    scene.frame_set(4200)
    bpy.context.view_layer.update()
    old_origin = scene.objects[
        "Quality | aether | head origin"
    ].matrix_world.translation.copy()
    light_templates = []
    for label in ("key", "fill", "rim", "reflection"):
        old = scene.objects[f"Reference duet | aether | {label}"]
        clone = old.copy()
        clone.data = old.data.copy()
        clone.parent = None
        clone.name = f"Reference duet | ikhor | {label}"
        clone["performer_id"] = "ikhor"
        scene.collection.objects.link(clone)
        light_templates.append(
            (clone, old.matrix_world.translation.copy() - old_origin)
        )
    # Remove source Aether from every linked scene, along with his named posed
    # helpers. Preserve the hall, Aksiniya, camera and all original files.
    remove = set()
    for obj in bpy.data.objects:
        if obj.get("performer_id") == "aether" or (
            "aether" in obj.name.lower() and obj.type in {"LIGHT", "EMPTY"}
        ):
            remove.add(obj)
            remove.update(obj.children_recursive)
    assert not any(o.get("performer_id") == "aksiniya" for o in remove)
    assert scene.camera not in remove
    bpy.data.batch_remove(ids=remove)
    with bpy.data.libraries.load(str(args.actor), link=False) as (available, loaded):
        assert "Ikhor | character" in available.collections
        loaded.collections = ["Ikhor | character"]
    collection = loaded.collections[0]
    scene.collection.children.link(collection)
    bpy.context.view_layer.update()
    arm = next(
        o
        for o in collection.all_objects
        if o.type == "ARMATURE" and o.get("performer_id") == "ikhor"
    )
    assert arm.parent and scene.rigidbody_world is None
    assert not any(o.rigid_body for o in collection.all_objects)
    material_set = {
        m
        for o in collection.all_objects
        if o.type == "MESH"
        for m in o.data.materials
        if m
    }
    for material in material_set:
        assert material.get("performer_id") == "ikhor"
    expected_new = {}
    for frame in FRAMES:
        scene.frame_set(frame)
        expected_new[frame] = snapshot(scene)["actors"]["ikhor"]
    scene.frame_set(4200)
    new_helpers(scene, arm)
    bpy.context.view_layer.update()
    origin = scene.objects[
        "Quality | ikhor | head origin"
    ].matrix_world.translation.copy()
    receiver = bpy.data.collections.new("Reference duet | receivers | ikhor")
    scene.collection.children.link(receiver)
    for obj in collection.all_objects:
        if obj.type == "MESH":
            receiver.objects.link(obj)
    for light, offset in light_templates:
        light.location = origin + offset
        aim(light, origin - Vector((0, 0, 0.15)))
        light.light_linking.receiver_collection = receiver
        light["performer_id"] = "ikhor"
    spec = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    optional_changes = []
    for material in material_set:
        name = material.get("source_mmd_material_name", material.name)
        if name in spec.get("optional_parts", {}).get("hide_materials", []):
            optional_changes.append(
                {
                    "material": material.name,
                    "source_name": name,
                    "original_alpha": material.mmd_material.alpha,
                    "effective_alpha": 0,
                    "reason": "Optional quest collar omitted in wedding look; original PMX retained",
                }
            )
            material.mmd_material.alpha = 0
    material_report = apply_ikhor_materials(scene, arm, spec)
    edge_report = install_edges(scene, arm.parent, material_set)
    # Discard only unused missing placeholders, after the explicit face fallback.
    placeholders = []
    for image in list(bpy.data.images):
        if (
            image.source == "FILE"
            and image.users == 0
            and not image.packed_file
            and not Path(bpy.path.abspath(image.filepath)).is_file()
        ):
            placeholders.append(image.name)
            bpy.data.images.remove(image)
    beams = artist_beam_volume(scene) if args.art_beams else []
    for layer in scene.view_layers:
        layer.update_render_passes()
    scene["ikhor_wedding_revision"] = "franken-ikhor-bold-wedding-v1"
    scene["ikhor_physics_validated_frames"] = [4139, 4441]
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.resolution_percentage = args.percentage
    for frame in args.stills:
        scene.frame_set(frame)
        scene.render.filepath = str(args.output_dir / f"ikhor-wedding-{frame}.png")
        bpy.ops.render.render(write_still=True)
        print("IKHOR_WEDDING_STILL", frame, flush=True)
    for frame in FRAMES:
        scene.frame_set(frame)
        assert keep_snapshot(scene) == old_poses[frame], frame
        assert snapshot(scene)["actors"]["ikhor"] == expected_new[frame], frame
    scene.frame_set(4140)
    scene.render.resolution_percentage = 100
    bpy.ops.file.pack_all()
    target = args.output_dir / "Franken_Aksiniya_Ikhor_Bold_Wedding.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    report = {
        "source": str(source),
        "source_sha256": SOURCE_SHA,
        "actor": str(args.actor),
        "actor_sha256": actor_sha,
        "actor_report": str(args.actor_report),
        "project": str(target),
        "materials": material_report,
        "optional_part_visibility_changes": optional_changes,
        "outlines": edge_report,
        "removed_aether_objects": len(remove),
        "unused_missing_placeholders_removed": placeholders,
        "new_art_beams": beams,
        "unchanged_aksiniya_and_camera_frames": FRAMES,
        "unchanged_ikhor_native_pose_frames": FRAMES,
        "all_file_outputs_muted": True,
        "full_song_rendered": False,
        "validated_source_frames": [4140, 4439],
        "fps": 60,
        "limits": [
            "Ikhor native physics was newly baked only for the declared sample window, not the full song",
            "Face uses explicitly recorded fallback for absent edited y1.png",
            "New HDR and visible beam volumes are artistic effects, not a recovered game/reference shader",
        ],
    }
    (args.output_dir / "ikhor-wedding-preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("IKHOR_WEDDING_READY", target, flush=True)


if __name__ == "__main__":
    main()
