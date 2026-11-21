# 材质响应续读：球面反射色与布料纤维光

2026-11-13。猪猪，本轮只做一手图文阅读与仓库源码核对，新增两个待验证判断。没有打开生产 `.blend`、渲染、安装引擎或改参数；以下实验均未执行，不代表完成游戏 Shader 移植或提升已获认可。

已读[现行分层](CHARACTER_LAYER_REFINEMENT.md)、[前轮一手研究](NPR_PRIMARY_STUDY_2026_11_13.md)、[质感精修](SURFACE_REFINEMENT.md)、[鸣潮研究](WUWA_TOON_STUDY.md)及项目入口。前轮的高光许可／偏移、暗部高光门控不再列作新发现。

## 实际取得的证据

| 一手来源 | 本轮读到的范围 | 边界 |
| --- | --- | --- |
| [Blender 官方 Principled BSDF](https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html) | 官方搜索索引返回的 Base Color、Metallic、Roughness、Layers、Sheen 参数正文，标题为5.2 LTS。 | `latest`与固定`5.2`页面直接打开均402；未读取整页或插图，也未据此验证本机节点行为。 |
| [MMD Tools 作者仓库 material.py](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/mmd_tools/core/material.py) | `update_sphere_texture_type`、`__get_shader_uv`、`__get_shader`相关源码，核对球面坐标与 Color 输出位置。 | `main`未锁提交，不能当成本机4.5.14逐字快照。 |
| [Unity 官方 UTS MatCap设置，0.11.1-preview](https://docs.unity3d.com/Packages/com.unity.toonshader@0.11/manual/MatCap.html) | HTML正文中的 MatCap定义、混合、相机与UV遮罩职责。 | 未播放GIF、查看独立图片或运行Unity；UTS MatCap不能与PMX球面实现直接画等号。 |

UTS把MatCap作为预制材质／光照图像表达，另设乘／加混合和UV区域遮罩。MMD Tools已读源码则把普通球面坐标由法线转到相机空间后映射，并把球面合成后的颜色接出`Color`；SubTexture模式另用UV。两者支持先区分“视角相关颜色表达”与“区域数据”的研究方向。[UTS说明](https://docs.unity3d.com/Packages/com.unity.toonshader@0.11/manual/MatCap.html)、[MMD Tools源码](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/mmd_tools/core/material.py)

现有自制控制图R是金色候选，G由R生成美术粗糙度，B由底图亮度生成绘制亮部候选；并非独立测得的三种光学数据，尤其G不包含同一金属区内的精细粗糙度变化。见`make_surface_masks.py:21–30`。本轮不改这些通道，不复用为纤维方向图。

## 新增一：两人的金属反射色源并不一致，应先做分支输入消融

Principled的Base Color参与金属反射着色；Metallic=1时没有漫反射。因而把已含视角相关亮部的颜色送入金属Base Color，可能同时影响反射形状与反射颜色。这是需检查的耦合，不能只凭“发白”便判定重复高光。[官方参数说明，索引正文](https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html)

仓库存在一个具体的不对称：`mmd_surface_refine.py:185–187`为阿克西妮娅的`Surface | masked gold response`直接接`mmd_shader.Color/Alpha`；`aether_look_revision.py:136–146、250–254`为空的金属取`mmd_base_tex`经白平衡与暖金调整后的颜色。`prepare_character_layers.py:330–349`只调整既有金属的Metallic／Roughness和布料／皮革混合，未统一两人的金属色源。**这只是构建源码证据；没有核实最新保存工程仍保持全部连接，更没有证明球面已造成可见缺陷。**

建议只选一个已确认仍用MMD Color、球面启用且非恒色的金属区域，先追踪最终输出，再在独立副本比较：

```text
C_s = 原 MMD Color
C_0 = 复制相同输入，只将 Sphere Tex Fac 设为0所得的 Color
PBR_BaseColor(u) = (1-u) * C_s + u * C_0     # u=0／1
```

这是诊断输入选择器，不是原游戏公式。`C_0`仍保留PMX颜色、底图、Toon等，**不能命名为raw albedo**。只切换该金属PBR分支，NPR仍用原`C_s`，Alpha始终沿原连接；遮罩、Metallic=0.88、现行粗糙度、灯光、曝光、后期均固定。不对已经采用底图色源的空重复此操作，也不全局关闭PMX球面。

先取同一4290帧输出两种PBR输入预览与最终图；随后分别固定灯绕相机、固定相机移灯，沿用三轴测试中的24帧范围。检查“源颜色随视角变化”是否也在反射上重复形成明暗／色偏，金饰是否更易读，而不是只统计变亮像素。若现行球面未启用、两输入无差异或去除后丢失作者设计，则结束该项，保留原版。无差异也是有效结果。

## 新增二：白布已有Sheen入口，先确认小权重分支的贡献

官方将Sheen描述为细小表面纤维的柔和边缘反射；它属于独立的顶层，不能用普通镜面粗糙度代替。该机制可作为柔软织物候选，但不能据白色便认定是绒布；光滑缎面与毛领另作判断。[官方Sheen说明，索引正文](https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html)

空的创建脚本已给cloth物理分支`Sheen Weight=0.15`（`aether_look_revision.py:232`），当前分层脚本再把该分支混合设为0.12，皮革为0.16。故不能报告“原来没有布料纤维光”。应先核实保存工程的实际Sheen输入和最终连接；在不透明、金属遮罩为0的局部，分支贡献可示意为：

```text
L(s) ≈ (1-w) * N + w * P(s)
ΔL ≈ w * [P(s) - P(0)]          # 本项 w固定0.12
```

`P(s)`指包含层间影响的整个物理响应，不是单独相加的白光；不能把`0.12×0.15`解释为最终亮度或精确能量占比。图中若还有外层金属混合、透明或反射限制，贡献还需另核。当前结果可能弱，也可能已经足够；本轮未测。

可检验提案：只选空的一块已确认属于cloth的白布，排除金边／皮肤／毛领，保留physical mix=0.12及现有底色、普通Roughness、Sheen Tint／Roughness、法线、Alpha。先比较Sheen Weight=0与实际基准值；基准若确为0.15，再单独试0.30。每次只改此一项，固定曝光与无Glow输出。必要时另看物理分支的独立诊断图，不能把它称为已拆出的物理render pass。

固定姿态／灯光绕拍时，观察白布是否出现宽而柔和的掠射响应，同时保留褶皱和彩色暗部；固定相机移灯时，与相邻金属的有方向反射作同条件比较。若只有整片白色抬升、外缘洗掉、动态游动或看成塑料，则拒绝该档。最终图无可辨差异时先记录分支权重／遮挡／输出限制，不同时提高physical mix再叠分析式白高光。已有分析式布料光泽是否仍连到输出也须先追踪，避免重新叠回已绕过的历史节点。

## 交接边界

本轮新增的是“金属反射色源不对称”的源码定位和“现有Sheen在0.12分支内验贡献”的实验设计，均未证明美术收益。发丝继续使用现有分析式发带，未新增第三项发带策略；官方索引标出的Cycles专用各向异性也不能当作本机EEVEE现成功能。完整来源与本地文件哈希见[账本](research/MATERIAL_RESPONSE_STUDY.json)。
