"""Blender-side runtime for the blender-mmd-codex plugin."""

from __future__ import annotations


bl_info = {
    "name": "Blender MMD Codex",
    "author": "blender-mmd-codex contributors",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "Properties > Scene",
    "description": "MMD model checks and reference-video workflow helpers",
    "category": "Animation",
}


try:
    import bpy
except ImportError:  # Allows syntax and unit checks outside Blender.
    bpy = None  # type: ignore[assignment]


if bpy is not None:
    from bpy.props import StringProperty

    from .operators.health import MMD_CODEX_OT_check_scene
    from .operators.model_check import MMD_CODEX_OT_check_model
    from .operators.reference_video import MMD_CODEX_OT_add_reference_video
    from .panels.main import MMD_CODEX_PT_main

    _CLASSES = (
        MMD_CODEX_OT_check_scene,
        MMD_CODEX_OT_check_model,
        MMD_CODEX_OT_add_reference_video,
        MMD_CODEX_PT_main,
    )

    def register() -> None:
        """Register operators, panel, and scene properties with Blender."""

        for cls in _CLASSES:
            bpy.utils.register_class(cls)
        bpy.types.Scene.mmd_codex_status = StringProperty(
            name="MMD Codex 狀態",
            description="最近一次 MMD Codex 檢查結果",
            default="尚未執行檢查",
        )
        bpy.types.Scene.mmd_codex_reference_path = StringProperty(
            name="參考影片",
            description="最近一次加入 Blender 的 MMD 參考影片路徑",
            default="",
            subtype="FILE_PATH",
        )

    def unregister() -> None:
        """Unregister scene properties, panel, and operators from Blender."""

        for property_name in ("mmd_codex_reference_path", "mmd_codex_status"):
            if hasattr(bpy.types.Scene, property_name):
                delattr(bpy.types.Scene, property_name)
        for cls in reversed(_CLASSES):
            bpy.utils.unregister_class(cls)

else:

    def register() -> None:
        """Explain why registration is unavailable outside Blender."""

        raise RuntimeError("blender_addon 必須由 Blender Python 載入")

    def unregister() -> None:
        """Remain importable for static checks outside Blender."""

        return None
