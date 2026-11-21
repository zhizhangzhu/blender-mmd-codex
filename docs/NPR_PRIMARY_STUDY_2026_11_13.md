# 2026-11-13 一手图文续读：发丝高光的形状与阴影策略

本轮只新增两个窄主题：**许可遮罩与高光形状偏移的算子位置**，以及**高光在暗部的保留策略**。这是文献阅读与源码核对，不是 Blender 实装或新质量样片；没有打开最新 `.blend`、渲染、改动作／物理／相机，也没有取得参考作者的 Shader。

先读了[下一轮三个实验](NPR_NEXT_EXPERIMENTS.md)、[现行分层](CHARACTER_LAYER_REFINEMENT.md)、[人物手册](CHARACTER_NPR_PLAYBOOK.md)。旧 E1 的脸影阈值图、E2 的法线包络、E3 的三类控制图不再计作新发现。本次没有得到足以新增一个脸部 SDF 方案的实质结论。

## 实际读到什么

| 来源 | 本轮读取范围 | 没有读取／验证的内容 |
| --- | --- | --- |
| [MooaToon 作者：Add Stylized Hair Highlights](https://mooatoon.com/en/docs/Tutorial/AddStylizedHairHighlights) | 页面正文可读，重点检查 Specular Mask、Specular Ramp Offset、Specular Color Ramp 小节。 | 未逐图打开网页插图、运行 Houdini／UE 示例或取得其着色器实现。页面的 GitHub 编辑链接另开失败：Cache miss。 |
| [Unity 官方：Highlight Settings，0.11.1-preview](https://docs.unity3d.com/Packages/com.unity.toonshader@0.11/manual/Highlight.html) | 返回 HTML 文本，实际读取 Highlight Mask、Highlight Blending on Shadows 等正文；另读了[官方仓库当前文档](https://github.com/Unity-Technologies/com.unity.toonshader/blob/master/com.unity.toonshader/Documentation~/Highlight.md)。 | 没有运行 Unity；固定版本网页与 master 不是同一版本快照。 |
| [Unity 官方 BuiltIn 高光合成源码](https://github.com/Unity-Technologies/com.unity.toonshader/blob/master/com.unity.toonshader/Runtime/Shaders/BuiltIn/UCTS_DoubleShadeWithFeather.cginc) | 定位 `_TweakHighColorMask_var`、`Set_FinalShadowMask`、`Set_HighColor` 的实际表达式，核对遮罩与阴影衰减的顺序。 | master 未锁提交；只核对这个 BuiltIn 文件的相关段落，不外推到 URP／HDRP，也没有移植代码。 |

另打开 MooaToon 的[阴影形状页](https://mooatoon.com/en/docs/Tutorial/ControlTheShapeOfShadows)正文核对既有知识，没有把该页的旧知识重新计入本轮主题。完整访问记录与本地源码哈希见[来源账本](research/NPR_PRIMARY_STUDY_2026_11_13.json)。

## 新增一：黑色许可区与偏移图不能互换

作者把 Specular Color Map 用作高光许可；另给 Specular Ramp Offset 输入控制形状。前者删减不需要的亮区，后者改变进入亮带的范围。作者还展示用降低亮度的副本作为 Offset 调整尖角；这不意味着任意现有遮罩可以直接复用到任意 Shader 的同名输入。[作者小节](https://mooatoon.com/en/docs/Tutorial/AddStylizedHairHighlights#draw-a-specular-mask-to-precisely-control-highlight-shapes)

本工程多了一条可定位的核对结果：`prepare_character_layers.py` 第294–305行把现有 `Surface | mask channels` 的 B 通道转换成 `0.35 + 0.65B` 再乘亮带。因此，即使 B 为0，该分支仍保留35%的亮带，**它是有下限的强度调节，不是可完全排除高光的许可遮罩**。`make_surface_masks.py` 第27–30行显示 B 是从源图 RGB 亮度阈值得到的候选，并非作者绘制的光学许可图。此结论仅针对已读源码；最新保存工程的实际连接仍需单独核对。

旧 E3 只提出增加许可图；这里新增的是先区分“删亮区”与“移动亮带边界”，并为现有分析式发带确定插入位置。当前源代码的主响应可记为 `q = max(1 - (T·H)^2, 0)`，再取 `q^p`；`T` 是现有头轴投影生成的切线近似，不能称为完成了 MooaToon 切线传递。

**可关闭的验证提案，未实施：**只选阿克西妮娅的一簇刘海，保留既有方向、指数、颜色与强度，不添加第二条亮带。在原 `q^p` 前试独立数据图 `O` 的居中偏移，在之后试许可图 `M`：

```text
q2 = clamp(q + k * (2O - 1), 0, 1)
H_new = H_gain * M_existing * M * pow(q2, p)
```

这段是本工程提出的诊断表达式，不是对作者 Shader 的还原。`O=0.5` 为本实验自行规定的中性值；`k=0` 关闭偏移。`M=1` 关闭新增许可，`M=0` 须让本条新增亮带严格归零。`M_existing` 暂保留原来的有下限调节，以免一次改变多个既有因素。

- 首先用黑／灰／白测试条检查许可图，不以最终头发颜色代替高光信号预览；底图、球面或金属分支的亮部可能仍然存在。
- 然后固定 `M=1`，在同一簇中画一个平滑 `O`，只比较 `k=0／0.01／0.02`。这些是研究档位，不是质量参数；先输出 `q`、`q2` 与亮带，再看 Combined。
- 最后才同时启用两项。检查固定灯转头、固定头移灯、相机绕拍各24帧；专看尖角、UV接缝、亮带断裂与时间闪烁。若偏移造成整束常亮、动态边缘抖动，淘汰该配置。

**误区：**不能把高光许可图当切线方向图，也不能把乘完高光后的亮度改变说成亮带形状已经得到正确设计。灰度许可也可能改变肉眼可见轮廓，因此必须用上游标量与单项开关辨认机制，不能只比较截图面积。

## 新增二：高光暗部保留是另一项策略

UTS 官方文档把 UV 高光遮罩与暗部高光强度单独列项。相关 BuiltIn 源码也先计算遮罩高光，再按最终明暗遮罩 `S` 乘形如 `1-S+rS` 的系数：`r=1` 保留，`r=0` 完全压掉被该遮罩标记的高光。[官方设置说明](https://docs.unity3d.com/Packages/com.unity.toonshader@0.11/manual/Highlight.html#highlight-blending-on-shadows)、[官方合成源码](https://github.com/Unity-Technologies/com.unity.toonshader/blob/master/com.unity.toonshader/Runtime/Shaders/BuiltIn/UCTS_DoubleShadeWithFeather.cginc)

值得保留的限制是：这个文件的 `Set_FinalShadowMask` 本身结合半兰伯特、系统阴影开关与控制图等输入；它不是纯几何可见性。**可调暗部高光是一项美术策略，不能由变量名推断为物理遮挡分离。**这也不能证明“漫反射暗的地方不应该有高光”。

本工程已读的 `prepare_character_layers.py` 第254–320行中，新发带使用方向、蓝通道与强度，随后 Screen 合成；没有把前面的综合受光 `factor` 接进本条发带的衰减。这是本次源码层新增定位，不是断言当前成片已经出现不合理暗部高光。

**可关闭的验证提案，未实施：**在独立副本中，把现有发带强度送入 Screen 之前增加一个开关。先沿用人物头发已有、经标定的受光响应 `F`，明确称为“综合受光美术门控”：

```text
G = (1-enable) + enable * (r + (1-r) * F)
H_gated = H_existing * G
```

`enable=0` 或 `r=1` 均回到原发带；建议只对照 `r=1／0.35／0`，不直接选一档晋升。`F` 取哪个节点插口必须写进实验报告，不能从最终发色反推。保持原 AO 只应用一次，禁止把新门控乘回整张人物底色。

- 同一姿态依次比较主灯无遮挡、只增加代理遮挡块、只改变补光三个独立条件。输出 `F`、门控前后高光和 Combined，检查衰减是否局限于本条发带。
- 补光也会改变当前 `F`，所以补光增强时门控重新变亮只能说明综合受光响应。即使看起来正确，也不能报告为“实现纯主灯可见性”。
- 再跑三轴与原动作连续段。若暗部亮带整体消失导致发型失去可读性，或综合信号在多灯下使高光随补光突变，保留原版，记录失败。后续若改用独立几何可见性输入，应成为另一项实验，重新验证。

## 本轮能交接的结论

本次新增的是两项输入职责与源码缺口定位，尚未证明实际美术收益。推荐先用严格许可的零值检查澄清现有控制，再单独验证偏移；暗部门控作为后续可选实验。三项开关的关态均须对齐原发带；不重跑一次性人物迁移，不修改现行工程或质量状态。

普通 Blender 5.2.2 EEVEE 的标量运算足以表达以上诊断，但本轮没有建节点或跑本机测试。没有恢复 Goo，没有获得空缺失的 Lightmap，也没有据此匹配原神、鸣潮或参考作者的最终质量。
