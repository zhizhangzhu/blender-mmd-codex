# Blender 中的 MMD 操作

## 运行时优先

本文以 Blender 4.5 LTS + MMD Tools 4.5.x 为基线。MMD Tools 4.x 支持 Blender 4.2 以上；改用其他版本时读取当前 RNA/API，不套用旧界面坐标。通过 MCP 的专用工具检查对象，只有专用工具缺少操作时才用小段 `execute_blender_code`。

在 Blender Python 中可查询真实操作符参数：

```python
import bpy
op = bpy.ops.mmd_tools.import_vmd.get_rna_type()
print([(p.identifier, p.type) for p in op.properties])
print(bpy.app.version_string)
print(list(bpy.context.preferences.addons.keys()))
```

扩展安装的 Python 包可能叫 `bl_ext.blender_org.mmd_tools`，手工扩展可能在 `bl_ext.user_default` 下。`bpy.ops.mmd_tools.*` 操作符名不因包路径变化；需要内部模块时从实际已启用扩展解析包名，不假定能 `import mmd_tools`。

## PMX/PMD 导入

保留原目录和贴图。导入前记录已有对象和当前场景，选择一致的比例（MMD Tools 4.5.x 默认 `0.08`）：

```python
before = set(bpy.data.objects)
result = bpy.ops.mmd_tools.import_model(filepath=model_path, scale=0.08, save_log=False)
assert result == {'FINISHED'}, result
created = [o for o in bpy.data.objects if o not in before]
print([(o.name, o.type, getattr(o, 'mmd_type', None)) for o in created])
```

在新建对象中定位 `mmd_type == 'ROOT'` 的模型根、其 Armature 和 Mesh。记录输入路径、导入比例、骨骼的日文 MMD 名称、缺失图片、材质、Shape Keys/Morph、刚体和关节。缺图检查图片的实际解析路径，打包图片或 Generated 图片不应算作丢失。不要用“场景里存在任意 Mesh/Armature”代替目标模型检查。

## 人物 VMD

选择模型根会将动作套用到该模型的骨骼和表情；只选 Armature 会只处理骨骼，只选 Mesh 会只处理形态动画。先退出编辑模式，清除其他对象选择，设置唯一 active 对象。将时间线放到第 1 帧并明确 margin，避免从当前中间帧追加。

```python
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
target.select_set(True)
bpy.context.view_layer.objects.active = target
bpy.context.scene.frame_set(1)
result = bpy.ops.mmd_tools.import_vmd(
    filepath=motion_path, scale=0.08, margin=0,
    bone_mapper='PMX', update_scene_settings=False, save_log=False,
)
assert result == {'FINISHED'}, result
```

`PMX` 映射使用模型保存的日文骨名，适合已改成英文显示名的 PMX。`BLENDER` 使用实际骨名，`RENAMED_BONES` 依导入命名规则重写动作名；先检查命名再选，不直接批量改骨。

注意 `create_new_action=True` 会清除目标模型各相关对象当前绑定的动画并重置姿态。需要替换动作时先保存副本并明确选择，叠加口型/表情时先检查已有 Action/NLA 与通道，不能将该选项当作无影响的默认。`update_scene_settings=True` 会重设帧率为 30 并更新范围；人物与相机导入时应使用同一时间策略，最终统一设定范围。

读回实际 Action、帧范围、骨骼/Shape Key 关键帧，并在几个有明显运动的帧对比变换。导入返回成功但没有匹配骨骼不等于成功套用。Blender 4.4+ 有分层/分槽 Action，检查时按实际 API 读取，别仅假定 `action.fcurves` 永远可用。

## 相机 VMD 与镜头修改

先新建或精确选定一台相机，单独选中，再用同一 `import_vmd` 操作符导入相机文件。MMD Tools 会建立 MMD 相机控制结构；将 `scene.camera` 指向真正的 CAMERA 对象。人物动作 VMD 和相机 VMD 扩展名相同，应检查文件包含的轨道，不凭扩展名判别。

导入后识别实际控制根、子相机及各自的动画。位置/旋转、距离和视角可能分布在不同对象与属性上；移动被驱动的子相机可能在下一帧被覆盖。先打印控制结构与当前 Action，修改对应的控制属性或关键帧，再检查开头、转身、切镜与结尾。若要整体平移镜头轨迹，修改控制根的相关位置曲线或添加一个明确的父级偏移，并同时验证主体取景。不得为了修一个镜头把人物移动到别处而改变原舞台关系。

## 材质、骨骼与物理

MMD Tools 自带 MMD 材质节点，先查看导入结果再决定改成 Toon/NPR 或其他材质。MME/Ray-MMD 的 `.fx` 不能作为 Blender 着色器直接套用。材质和合成节点按当前 Blender 的节点类型与插槽构建，保留原材质副本。

物理装配、SDEF 和 Morph 绑定等操作需要检查当前 `bpy.ops.mmd_tools` RNA 和目标根。先确认模型/动作比例一致、场景碰撞对象、刚体形状、质量及碰撞组，再看头发/裙摆；从起始预热帧顺序计算或烘焙，不能跳到中间帧后据此判断完整模拟。需要 Append 的 Rigify 或刚体转布料时读取相应文档，不在普通 VMD 导入时自动转换整套骨架。

来源：[MMD Tools 当前版本说明](https://github.com/MMD-Blender/blender_mmd_tools)、[维护者开发指南](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/DEVELOPER_GUIDE.md)、[旧 Wiki 的模型/动作/相机语义](https://github.com/powroupi/blender_mmd_tools/wiki/Documentation)。旧 Wiki 的 Blender 2.x 安装步骤和部分渲染设置已过时，参数以运行时和当前源代码为准。
