"""Minimal MMD-shaped model checks for the first Add-on slice."""

import bpy


class MMD_CODEX_OT_check_model(bpy.types.Operator):
    """Check selected objects for the Mesh and Armature pair used by MMD models."""

    bl_idname = "mmd_codex.check_model"
    bl_label = "檢查選取模型"
    bl_description = "檢查選取物件是否包含 Mesh 與 Armature"

    def execute(self, context):
        """Inspect selected objects and report missing basic MMD components."""

        selected = list(context.selected_objects)
        mesh_count = sum(1 for obj in selected if obj.type == "MESH")
        armature_count = sum(1 for obj in selected if obj.type == "ARMATURE")
        if not selected:
            message = "模型檢查失敗：請先選取 MMD 模型物件"
            level = {"WARNING"}
        elif not mesh_count or not armature_count:
            message = f"模型檢查警告：Mesh {mesh_count}、骨架 {armature_count}"
            level = {"WARNING"}
        else:
            message = f"模型基本檢查完成：Mesh {mesh_count}、骨架 {armature_count}"
            level = {"INFO"}
        context.scene.mmd_codex_status = message
        self.report(level, message)
        return {"FINISHED"}
