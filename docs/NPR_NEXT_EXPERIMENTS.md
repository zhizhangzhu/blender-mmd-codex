# 人物 NPR 下一轮三个实验

记录日期：2026-11-13。状态：**研究建议，尚未实施或在 Blender 中验证**。本轮只读下列官方／作者图文的可访问文字，不安装插件，不修改正在渲染的工程。未取得 Gosari542／观海子的工程、Shader 或原始素材，也未进行新的逐镜视频分析；这些实验不能作为已达到其质量的证据。

## 基线与阅读范围

主任务提供的当前改动是：保留 `MMDShaderDev.Color/Alpha` 及 PMX 球面语义；Color 乘一次综合 Diffuse／SDF 材质色带、一次短距 AO，并增加跟随头轴与实际主灯的发带；PBR 金属与透明分支保留。节点位于 `Character layers |` 前缀下，职责为 `single material palette`／`single contact AO`／`one directional hair highlight`，详见 [当前人物分层说明](CHARACTER_LAYER_REFINEMENT.md)。本子任务没有打开 `.blend`、检查节点或验证最终五秒成片，以上属于主任务实现说明。

`MMDShaderDev.Color` 不是游戏原始 albedo；不能把整理颜色职责等同于已取得干净底色。Aksi 有原 `FaceLightmap`，Aether 缺配套身体／头发 Lightmap，须逐角色核对。原 Face SDF 的通用 Goo 接口部分不兼容普通 Blender，目前仅复用可运行组件，不能称完整恢复 Goo。

| 资料 | 实际读取范围与可采用的事实 |
| --- | --- |
| [MooaToon 作者：Controlling the Shape of Shadows](https://mooatoon.com/en/docs/Tutorial/ControlTheShapeOfShadows) | `Custom Normal Shadow`、`Modify Shadow Gradient`、`Distance Field Facial Shadow` 的文字：法线、明暗阈值偏移、AO、按角度设计的脸影是不同控制。未运行示例，未逐张检查网页插图。 |
| [akasaki1211：sdf_shadow_threshold_map](https://github.com/akasaki1211/sdf_shadow_threshold_map) | README 的输入顺序、反向梯度、8／16 bit 与中间图选项；这是作者的阈值图生成工具说明，未下载或运行。 |
| [MooaToon 作者：Add Stylized Hair Highlights](https://mooatoon.com/en/docs/Tutorial/AddStylizedHairHighlights) | `Tangent Transfer` 与 `Specular Mask` 的文字：切线可控制高光形状，许可遮罩可去掉不需要的高光。未实施其 Houdini／UE 流程。 |
| [Unity 官方 UTS：Three Color Map and Control Map Settings](https://github.com/Unity-Technologies/com.unity.toonshader/blob/master/com.unity.toonshader/Documentation~/Basic.md) | 正文的亮部／两级阴影色图与线性 `Shading Position Map`；仅借鉴数据职责，不导入 Unity Shader。 |
| [Blender 官方 5.2：Data Transfer](https://docs.blender.org/manual/id/5.2/modeling/modifiers/modify/data_transfer.html)、[Normal Edit](https://docs.blender.org/manual/nb/latest/modeling/modifiers/normals/normal_edit.html)、[Passes](https://docs.blender.org/manual/nb/5.2/render/layers/passes.html) | 读取官方搜索索引返回的正文，直开部分英文页失败。确认法线传递／混合／顶点组能力，以及 Shader to RGB 应以 Combined 验收。`latest` 会漂移，不能代替本地 5.2 实测。 |

## E1：左右分别设计的脸影阈值图

**假设**：现有 SDF 仍有鼻尖、嘴周或左右脸形状不合适时，问题可能在作者控制图和坐标约定，而非需要更亮的补光。作者资料支持先设计各受光角度的脸影，再生成阈值图；不证明当前模型附带贴图拥有该语义。[脸影作者说明](https://mooatoon.com/en/docs/Tutorial/ControlTheShapeOfShadows#distance-field-facial-shadow)

- 下一轮先确认原 `FaceLightmap`／可运行 SDF 的真实通道，只有形状输入不足才替换，不再乘第二遍脸影。两角色独立核对 UV；左右不对称时使用两张自绘图。先画同侧主灯 0°／45°／90° 三张二值遮罩，再检查每像素随角度的变化是否适合单阈值表达。非单调变化须改图或分段，不靠全脸增亮掩盖。
- 在头部局部坐标计算光方向：点／聚光灯从头部参考点指向实际灯位置，太阳灯用其世界方向；约定前、右、上并保存调试图。面积灯中心方向仅作为美术近似。左右选择取带符号方位角，阈值范围、白黑含义与生成时的 `reverse` 约定一并记录；先显示黑白遮罩，后接肤色。
- 独立开关：`exp_face_threshold_map`；关时回到现有 SDF。保留当前平整脸部 Diffuse 探针和真实遮挡路径，不能把此图当作头发投影，也不恢复 0.95 脸亮度下限。
- 测试：固定曝光、相机、灯能量；对每个角色检查灯方位 -90°／-45°／0°／45°／90°，再检查当前片段中转头／张嘴的连续小段。通过条件是左右不翻转、正面过零不跳变、鼻口没有孤立黑岛，并保留可读脸影；具体参数须记录，不能逐帧自动归一化。

**普通 Blender 5.2 EEVEE：原理可实现，项目未验证。** 纹理采样、向量与标量数学可用普通节点／驱动表达；UE 的 Face Forward 烘焙、材质 ID 射线和屏幕空间头发阴影不是随之移植的功能。

## E2：只选一簇刘海做法线包络 A/B

**假设**：若头发形体明暗沿零碎三角面断裂，先整理该簇的受光法线可能比再加一道高光有效。Blender 内置 Data Transfer 可传递 Custom Normals，并以顶点组控制混合；Normal Edit 也可生成并混合方向。[Blender 官方说明](https://docs.blender.org/manual/id/5.2/modeling/modifiers/modify/data_transfer.html)

- 只在诊断副本选一簇紧随头部的刘海，建立平滑简化包络，传递面角 Custom Normals；用专用顶点组限制范围，混合强度先比较 0／0.25／0.5。以上是试验档位，不是已标定参数。保留原法线，关闭修饰器即可复原。
- 固定现有发带与高光，只看 Diffuse 形体。确认该分支实际读取改后的法线；若 Shader 仍用统一头轴法线，先输出法线调试色，不能从“看起来没变”判断方法无效。
- 独立开关：`exp_hair_normal_envelope`，对应单个修饰器的视口／渲染开关。禁止把该修饰器同时加到脸、毛领或原描边外壳；先检查描边挤出是否共用法线，存在耦合时须先隔离。
- 测试：相同五个灯方位，并检查该簇摆动最明显的连续段；观察面片断裂、发根接缝、侧面体积与反向受光。若包络在变形后滑动，或光带变成不分发束的一片亮区，淘汰这一配置。当前 PMX 权重和物理不改。

**普通 Blender 5.2 EEVEE：内置能力可用，蒙皮／描边耦合未验证。** 法线和切线职责不同；本实验控制形体明暗，并未实现 MooaToon 的切线传递高光模型。[作者的切线与高光遮罩说明](https://mooatoon.com/en/docs/Tutorial/AddStylizedHairHighlights)

## E3：把阈值偏移、AO 强度、高光许可写成明确控制图

**假设**：同一暗纹同时充当底色、AO 和色带偏移，容易形成重复压暗。UTS 将颜色图与固定阴影位置图分开；这里提出以下本工程的数据约定，而非声称已有 HM／HN／Lightmap 就是这些通道。[Unity 官方控制图说明](https://github.com/Unity-Technologies/com.unity.toonshader/blob/master/com.unity.toonshader/Documentation~/Basic.md)

| 新建的独立灰度图 | 中性值与接法 | 单项关闭 |
| --- | --- | --- |
| `form_bias` | Non-Color，0.5 中性；仅在形体受光进入一次色带前试 `D' = clamp(D + k * (2M - 1), 0, 1)`，先测 `k=0.05`。 | `k=0` |
| `ao_strength` | Non-Color，1 保留当前短距 AO；用其调节现有那一次 AO 的强度，0 为不施加，不能额外再乘 AO。 | 旁路回现有 AO 强度 |
| `hair_highlight_allow` | Non-Color，1 允许现有发带／高光，0 禁止；仅裁除不应出现的亮区。 | 遮罩恒为 1 |

- `D` 必须是可辨认的形体输入。**当前综合 Diffuse 若含真实遮挡而无法拆分，不把 `form_bias` 直接接到它上面**；先在单主灯、无外部遮挡的诊断副本验证，再决定是否需要明确的上游接口，避免把真实投影也推亮。
- 独立总开关：`exp_control_maps`；三图先分开预览，通道语义验证后才讨论打包。AO 图不能重新画进 Color；未经模型 UV／通道检查的现有贴图一律不自动接线。
- 测试：依次只开一个控制。阈值图应移动明暗交界；AO 强度只改变现有 AO；高光许可只删减原高光。对两角色分别检查领口、衣褶和发尖，最后检查连续镜头是否出现 UV 接缝或闪烁。

**普通 Blender 5.2 EEVEE：节点运算可实现，语义及效果未验证。** 色图按颜色管理，数据图用 Non-Color；以 Combined beauty 加独立开关对比验收，不能把 Shader to RGB 的拆分通道误称为纯投影／纯 Diffuse。[Blender 官方通道限制](https://docs.blender.org/manual/nb/5.2/render/layers/passes.html)

建议顺序 E1 → E2 → E3；一次只评估一个实验。通过静帧后仍须连续动态与独立重开检查；未通过前不写入生产预设，不升级质量状态。
