"""Temporary full-body framing to make the requested floor shadows visible."""
from pathlib import Path
import bpy
from mathutils import Vector

root = Path("D:/codex/output/MMD-Sunlit-Wedding-v4")
bpy.ops.wm.read_userpref()
bpy.ops.preferences.addon_enable(module="bl_ext.blender_org.mmd_tools")
bpy.ops.wm.open_mainfile(filepath=str(root / "production-v2/Franken_Duet_Portrait_Relight.blend"), use_scripts=False, load_ui=False)
scene = bpy.context.scene
scene.frame_set(4290)
camera_data = bpy.data.cameras.new("Window shadow study camera")
camera = bpy.data.objects.new(camera_data.name, camera_data)
scene.collection.objects.link(camera)
camera.location = (0, -5.5, 2.6)
camera.rotation_euler = (Vector((.2, .4, .5)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.lens = 32
scene.camera = camera
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.eevee.taa_render_samples = 32
scene.render.filepath = str(root / "fullbody-shadow.png")
bpy.ops.render.render(write_still=True)
