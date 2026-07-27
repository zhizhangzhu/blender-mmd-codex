"""Import rendered MMD videos into Blender's Video Sequence Editor."""

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper


class MMD_CODEX_OT_add_reference_video(bpy.types.Operator, ImportHelper):
    """Add a user-provided MMD video as a timeline reference."""

    bl_idname = "mmd_codex.add_reference_video"
    bl_label = "加入 MMD 參考影片"
    bl_description = "將 MMD 渲染影片加入 Video Sequence Editor 作為視覺參考"
    filename_ext = ".mp4"
    filter_glob: StringProperty(
        default="*.mp4;*.mov;*.mkv;*.webm;*.avi",
        options={"HIDDEN"},
    )

    def execute(self, context):
        """Insert the selected movie at frame 1 and save its path on the scene."""

        scene = context.scene
        scene.sequence_editor_create()
        bpy.ops.sequencer.movie_strip_add(
            filepath=self.filepath,
            frame_start=1,
            channel=1,
        )
        scene.mmd_codex_reference_path = self.filepath
        scene.mmd_codex_status = "已加入 MMD 參考影片，可在時間軸對照模型動作"
        self.report({"INFO"}, scene.mmd_codex_status)
        return {"FINISHED"}
