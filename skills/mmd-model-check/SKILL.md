---
name: mmd-model-check
description: 检查 Blender 中的 MMD 模型导入、骨架、材质、贴图、Morph 与物理，定位 PMX/PMD 场景中的具体问题。
---

# MMD 模型检查

通过实际 Blender 工具检查指定模型。MMD Tools 负责 PMX/PMD 导入；本项目 Add-on 的 Mesh/Armature 数量检查只是初步诊断。

1. 确认 Blender、MMD Tools 和当前实例；新文件用 MMD Tools 导入并记录比例，保留模型原目录及贴图相对路径。
2. 从模型根定位其子级 Armature、Mesh、材质、图片、Shape Keys/Morph、刚体和关节。不能拿场景里其他模型的骨架证明目标模型正常。
3. 缺图按 Blender 解析后的实际路径检查，区分打包/生成图片和磁盘文件。先找到模型随附贴图，再修改路径或材质。
4. 检查日文 MMD 骨名与 VMD 映射、IK、权重和动作实际变形。物理从起始帧顺序预热/烘焙后查看头发、裙摆和接触部位。
5. 将实际失败与待检查项分别报告；仅修复本次问题，保存新版本后操作。通过工具返回成功后仍要看代表帧或短片。

详细操作见同级技能的 [Blender 操作参考](../mmd-production/references/blender-operations.md)。报告至少包含输入路径、Blender/插件版本、模型根、骨架与 Mesh、缺图、Morph/动作、物理异常及可复现的下一步。没有发现错误不代表已经通过真实动作与渲染验收。
