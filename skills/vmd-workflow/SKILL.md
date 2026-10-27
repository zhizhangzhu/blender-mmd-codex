---
name: vmd-workflow
description: 使用已安装的 MMD Tools 在 Blender 中套用或检查人物、表情、相机 VMD 与 VPD，处理目标选择、骨名映射和时间设置。
---

# VMD 动作与相机

使用 MMD Tools 的现成导入器，不为普通套用重写 VMD 二进制解析。先确认真实 Blender 实例和扩展，再读取当前 `bpy.ops.mmd_tools.import_vmd` 的 RNA 参数。

完整操作示例见同级技能的 [Blender 操作参考](../mmd-production/references/blender-operations.md)；安装时同时保留该技能包。

1. 确认输入是真实 VMD/VPD，并区分人物骨骼、表情、相机和灯光轨道。只有 MP4/MOV 时使用影片参考流程，不承诺还原原始动作。
2. 人物模型根同时接收骨骼和表情；仅选 Armature 或 Mesh 会缩小导入范围。相机动作单独选择目标相机，导入后检查 MMD 相机层级和活动 `scene.camera`。
3. 只选择本次目标并设为 active，在第 1 帧导入，明确 margin、模型/动作统一比例及骨名映射。PMX 映射优先使用保存的日文骨名。
4. 先保存已有作品的副本。`create_new_action=True` 会清除目标相关对象当前动画并重置姿态；仅在确实替换动作时使用。叠加表情/口型要检查 Action/NLA 和通道。
5. 明确 `update_scene_settings` 是否允许重设 30 fps 和帧范围。人物和镜头使用一致时间策略，输出前再统一设置范围。
6. 回读骨骼、Shape Keys、Action 和相机数据，在明显不同的帧检查实际变化；检查未匹配骨名、IK、表情及相机控制属性。只返回 `FINISHED` 不代表有效套用。

报告输入、选定目标、比例、帧率/范围、实际导入轨道和仍需处理的差异。原始 VMD 导出时检查当前导出器支持的轨道；驱动/NLA 等需先按实际要求烘焙，不能保证所有 MMD 特有效果完整往返。
