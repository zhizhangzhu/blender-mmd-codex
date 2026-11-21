"""Separate geometry visibility and final compositing from direct volume rendering."""

import json
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goo_runtime import register_addons
from render_portrait_light_controls import mute_file_outputs

register_addons()
bpy.ops.wm.open_mainfile(
    filepath="D:/codex/output/MMD-Goo-Tyndall-Rim-v1/production-v5/Franken_Duet_Goo_Tyndall_Rim.blend",
    load_ui=False,
    use_scripts=False,
)
scene = bpy.context.scene
mute_file_outputs()
scene.frame_set(4290)
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
points = []
for index, target in enumerate(((1.5, 2.7, 0.6), (3.3, 3.2, 0.6))):
    lamp = scene.objects[f"Goo Tyndall v2 | window shaft {index}"]
    for fraction in (0.3, 0.5, 0.7, 0.9):
        point = lamp.location.lerp(Vector(target), fraction)
        projected = world_to_camera_view(scene, scene.camera, point)
        origin = scene.camera.matrix_world.translation.copy()
        direction = (point - origin).normalized()
        hits = []
        for _ in range(6):
            hit, location, normal, poly, obj, matrix = scene.ray_cast(
                deps, origin, direction, distance=(point - origin).length
            )
            if not hit:
                break
            hits.append({"name": obj.name, "location": list(location)})
            origin = location + direction * 0.001
        points.append(
            {
                "lamp": index,
                "fraction": fraction,
                "world": list(point),
                "screen": list(projected),
                "hits": hits,
            }
        )
tree = scene.compositing_node_group
output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
seen, leaves = set(), []


def walk(socket):
    item = socket.node
    key = item.as_pointer()
    if item.type == "R_LAYERS":
        leaves.append({"name": item.name, "socket": socket.name})
    if key in seen:
        return
    seen.add(key)
    for value in item.inputs:
        for link in value.links:
            walk(link.from_socket)


walk(output.inputs["Image"].links[0].from_socket)
folder = Path("D:/codex/temp/MMD-Goo-Rim-Glow-v1")
(folder / "beam-projection.json").write_text(
    json.dumps(
        {"points": points, "render_inputs_to_final": leaves},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(
    json.dumps(
        {"points": points, "render_inputs_to_final": leaves}, ensure_ascii=False
    ),
    flush=True,
)
scene.render.use_compositing = False
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = 16
scene.render.filepath = str(folder / "raw-volume-diagnostic.png")
bpy.ops.render.render(write_still=True)
