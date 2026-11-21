"""Read camera-ray intersections and render the world alone for sky diagnosis."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

out = Path(sys.argv[sys.argv.index("--") + 1])
out.mkdir(parents=True, exist_ok=False)
scene = bpy.context.scene
camera = scene.camera
graph = bpy.context.evaluated_depsgraph_get()
inverse = camera.calc_matrix_camera(graph, x=1280, y=720).inverted()
rows = []
for x, y in [
    (540, 220),
    (540, 300),
    (390, 300),
    (660, 300),
    (600, 600),
    (100, 620),
    (300, 560),
    (900, 500),
    (820, 300),
    (430, 80),
    (220, 250),
]:
    near = inverse @ Vector((2 * (x + 0.5) / 1280 - 1, 1 - 2 * (y + 0.5) / 720, -1, 1))
    near /= near.w
    direction = (camera.matrix_world.to_3x3() @ near.xyz).normalized()
    origin = camera.matrix_world.translation.copy()
    hits = []
    for _ in range(10):
        hit, point, _normal, index, obj, _matrix = scene.ray_cast(
            graph, origin, direction, distance=300
        )
        if not hit:
            break
        mat = obj.data.materials[obj.data.polygons[index].material_index]
        hits.append({"object": obj.name, "material": mat.name, "point": list(point)})
        origin = point + direction * 0.01
    rows.append({"pixel": [x, y], "hits": hits})
(out / "ray-hits.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
for obj in scene.objects:
    if obj.type in {"MESH", "LIGHT_PROBE"}:
        obj.hide_render = True
scene.render.use_compositing = False
scene.render.resolution_x, scene.render.resolution_y = 640, 360
scene.render.filepath = str(out / "sky-only.png")
bpy.ops.render.render(write_still=True)
print(json.dumps(rows), flush=True)
