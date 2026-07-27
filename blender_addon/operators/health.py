"""Scene-level Blender environment and object-count checks."""

import bpy


class MMD_CODEX_OT_check_scene(bpy.types.Operator):
    """Report basic scene counts before an MMD workflow starts."""

    bl_idname = "mmd_codex.check_scene"
    bl_label = "檢查目前場景"
    bl_description = "檢查目前場景中的物件、模型與骨架數量"

    def execute(self, context):
        """Count scene objects and write a concise result to the Scene property."""

        objects = context.scene.objects
        mesh_count = sum(1 for obj in objects if obj.type == "MESH")
        armature_count = sum(1 for obj in objects if obj.type == "ARMATURE")
        context.scene.mmd_codex_status = (
            f"場景檢查完成：物件 {len(objects)}、Mesh {mesh_count}、骨架 {armature_count}"
        )
        self.report({"INFO"}, context.scene.mmd_codex_status)
        return {"FINISHED"}
