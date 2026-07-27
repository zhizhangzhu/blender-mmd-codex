"""Main Blender Properties panel for the first MMD Codex slice."""

import bpy


class MMD_CODEX_PT_main(bpy.types.Panel):
    """Expose scene checks and reference-video import in Blender Properties."""

    bl_label = "Blender MMD Codex"
    bl_idname = "MMD_CODEX_PT_main"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "SCENE"

    def draw(self, context):
        """Draw the first workflow controls and current status."""

        layout = self.layout
        scene = context.scene
        layout.label(text="MMD 工作流程")
        layout.operator("mmd_codex.check_scene", icon="VIEWZOOM")
        layout.operator("mmd_codex.check_model", icon="ARMATURE_DATA")
        layout.operator("mmd_codex.add_reference_video", icon="FILE_MOVIE")
        box = layout.box()
        box.label(text="目前狀態")
        box.label(text=scene.mmd_codex_status)
        if scene.mmd_codex_reference_path:
            box.label(text="參考影片已加入時間軸")
