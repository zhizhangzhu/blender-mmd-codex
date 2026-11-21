"""Continue the requested rim/glow revision with bounded shadowed window air."""

import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs
from snapshot_goo_scene import capture

SOURCE = Path(
    "D:/codex/output/MMD-Goo-Rim-Glow-v1/production-v1/Franken_Duet_Goo_Rim_Glow.blend"
)
ROOT = Path("D:/codex/output/MMD-Goo-Tyndall-Rim-v1")
PREFIX = "Goo Tyndall | "


def node(tree, kind, name):
    item = tree.nodes.new(kind)
    item.name = item.label = PREFIX + name
    return item


def main():
    expected = json.loads(
        (SOURCE.parent / "preparation.json").read_text(encoding="utf-8")
    )
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == expected["project_sha256"]
    production = ROOT / "production-v1"
    production.mkdir(parents=True, exist_ok=False)
    register_addons()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    mute_file_outputs()
    before = capture()
    changes = {"rims": [], "glows": [], "old_volume_factors": {}}
    rotation = scene.camera.matrix_world.to_quaternion()
    for material in bpy.data.materials:
        if not material.node_tree or material.get("performer_id") not in (
            "aksiniya",
            "ikhor",
        ):
            continue
        tree = material.node_tree
        for side, local, color in (
            ("left", (-0.65, 0.95, -0.50), (0.97, 1.0, 1.12)),
            ("right", (0.65, 0.80, -0.60), (0.78, 0.93, 1.16)),
        ):
            gain = tree.nodes.get(
                "Portrait relight | rimink | " + side + " HDR gain only"
            )
            if not gain:
                continue
            gain.inputs[1].default_value *= 1.35
            direction = tree.nodes[
                "Portrait relight | rimink | " + side + " direction cosine"
            ]
            assert not direction.inputs[1].is_linked
            direction.inputs[1].default_value = rotation @ Vector(local).normalized()
            rgb = tree.nodes["Portrait relight | rimink | " + side + " warm HDR RGB"]
            rgb.inputs[0].default_value = color
            changes["rims"].append(
                {
                    "material": material.name,
                    "side": side,
                    "gain": gain.inputs[1].default_value,
                    "direction_world": list(direction.inputs[1].default_value),
                    "color": list(color),
                }
            )
    # Only this controlled source illuminates the new rear air. Other surfaces retain their lights.
    for obj in scene.objects:
        if obj.type == "LIGHT":
            changes["old_volume_factors"][obj.name] = obj.data.volume_factor
            obj.data.volume_factor = 0
    material = bpy.data.materials.new(
        PREFIX + "bounded scattering with feathered edges"
    )
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    out = node(tree, "ShaderNodeOutputMaterial", "volume output")
    coordinates = node(tree, "ShaderNodeTexCoord", "normalized volume bounds")
    split = node(tree, "ShaderNodeSeparateXYZ", "bound coordinates")
    tree.links.new(coordinates.outputs["Generated"], split.inputs[0])
    masks = []
    for axis in ("X", "Y", "Z"):
        center = node(tree, "ShaderNodeMath", axis + " center")
        center.operation = "SUBTRACT"
        center.inputs[1].default_value = 0.5
        tree.links.new(split.outputs[axis], center.inputs[0])
        absolute = node(tree, "ShaderNodeMath", axis + " absolute distance")
        absolute.operation = "ABSOLUTE"
        tree.links.new(center.outputs[0], absolute.inputs[0])
        fade = node(tree, "ShaderNodeMapRange", axis + " soft boundary")
        fade.clamp = True
        fade.interpolation_type = "SMOOTHSTEP"
        fade.inputs["From Min"].default_value = 0.33
        fade.inputs["From Max"].default_value = 0.50
        fade.inputs["To Min"].default_value = 1
        fade.inputs["To Max"].default_value = 0
        tree.links.new(absolute.outputs[0], fade.inputs["Value"])
        masks.append(fade.outputs["Result"])
    density = masks[0]
    for index, factor in enumerate((*masks[1:], 0.025)):
        multiply = node(tree, "ShaderNodeMath", "density factor " + str(index))
        multiply.operation = "MULTIPLY"
        tree.links.new(density, multiply.inputs[0])
        if hasattr(factor, "is_output"):
            tree.links.new(factor, multiply.inputs[1])
        else:
            multiply.inputs[1].default_value = factor
        density = multiply.outputs[0]
    scatter = node(tree, "ShaderNodeVolumeScatter", "real shadowed light scattering")
    scatter.inputs["Color"].default_value = (0.86, 0.93, 1, 1)
    scatter.inputs["Anisotropy"].default_value = 0.25
    tree.links.new(density, scatter.inputs["Density"])
    tree.links.new(scatter.outputs[0], out.inputs["Volume"])
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 7.4, 4.3))
    air = bpy.context.object
    air.name = PREFIX + "rear window air only"
    air.scale = (7.0, 4.9, 4.1)
    air.data.materials.append(material)
    receivers = bpy.data.collections.new(PREFIX + "stage and volume receivers")
    stage = bpy.data.collections["Portrait day stage | stage receivers"]
    for obj in stage.all_objects:
        receivers.objects.link(obj)
    receivers.objects.link(air)
    light = scene.objects["Goo daylight v2 | window gobo source"]
    light.light_linking.receiver_collection = receivers
    light.data.volume_factor = 1.4
    light.data.spot_blend = 0.32
    light.data.color = (0.93, 0.97, 1.0)
    # Retain the original gobo geometry and matching ground shadows.
    light.data.use_shadow = True
    volume_settings = {}
    if hasattr(scene.eevee, "use_volumetric_shadows"):
        scene.eevee.use_volumetric_shadows = True
    for name in (
        "use_volumetric_shadows",
        "volumetric_samples",
        "volumetric_shadow_samples",
        "volumetric_tile_size",
    ):
        if hasattr(scene.eevee, name):
            volume_settings[name] = getattr(scene.eevee, name)
    tree = scene.compositing_node_group
    for name, strength, threshold, size in (
        ("眩光", 0.22, 1.15, 0.05),
        ("Wedding | stage halo", 0.23, 1.20, 0.055),
        ("Wedding | actor halo", 0.28, 0.12, 0.037),
    ):
        glare = tree.nodes[name]
        for key, value in (
            ("Strength", strength),
            ("Threshold", threshold),
            ("Size", size),
        ):
            glare.inputs[key].default_value = value
        changes["glows"].append(
            {"node": name, "strength": strength, "threshold": threshold, "size": size}
        )
    scene.render.compositor_device = "GPU"
    scene.render.compositor_precision = "FULL"
    scene.render.use_persistent_data = True
    # Keep the existing color transform; expose what is actually installed instead of naming it ACES.
    color = {
        "view_transform": scene.view_settings.view_transform,
        "look": scene.view_settings.look,
        "exposure": scene.view_settings.exposure,
    }
    after = capture()
    preserved = {
        key: before[key] == after[key]
        for key in ("actions", "images", "samples", "fps", "engine")
    }
    preserved["original_meshes"] = all(
        after["geometry"].get(key) == value for key, value in before["geometry"].items()
    )
    assert all(preserved.values()), preserved
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.use_motion_blur = False
    scene.render.use_sequencer = False
    scene.eevee.taa_render_samples = 24
    scene.frame_set(4290)
    scene.render.filepath = str(production / "portrait-4290.png")
    project = production / "Franken_Duet_Goo_Tyndall_Rim.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    report = {
        "source": str(SOURCE),
        "source_sha256": expected["project_sha256"],
        "project": str(project),
        "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
        "changes": changes,
        "preserved": preserved,
        "volume": {
            "bounds": [[-7, 2.5, 0.2], [7, 12.3, 8.4]],
            "density_peak": 0.025,
            "emission": False,
            "settings": volume_settings,
            "source": light.name,
            "gobo_geometry_inherited": True,
        },
        "color_management": color,
        "compositor_device": scene.render.compositor_device,
        "physics_resimulated": False,
        "art_status": "pending review",
    }
    (production / "preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.eevee.taa_render_samples = 32
    for frame, label in ((4140, "opening"), (4290, "portrait")):
        scene.frame_set(frame)
        scene.render.filepath = str(production / f"{label}-{frame}.png")
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        print("TYNDALL_STILL", frame, time.perf_counter() - started, flush=True)
    print("GOO_TYNDALL_RIM_SAVED", project, flush=True)


if __name__ == "__main__":
    main()
