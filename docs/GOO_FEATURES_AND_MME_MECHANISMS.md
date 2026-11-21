# Goo 与 MME：节点机制、源码增量与独立实验

2026-11-16。本轮回应猪猪“深入学习 Goo 相对于 Blender 的功能和各种 MME 预设”。实际进行了外部原作者资料／源码阅读、三个本机运行时的 RNA 对照和 28 张独立实验渲染。没有加载、修改生产工程，没有重新渲染或检查已交付视频。此前的 [MME 原包研究](MME_TO_GOO_LIGHTING_STUDY.md)继续有效；本篇记录实质增量，不把旧阅读重新计数。

## 运行时与功能边界

| 本机运行时 | 构建 | 可创建的 ShaderNode 类型数 |
| --- | --- | --- |
| 普通 Blender 5.2.2 LTS | d13f752e3b9c | 99 |
| Goo 5.2.1 LTS 社区移植 | 0051aee03764 | 112 |
| Goo 4.3.2 实验版 | ba60b2412c76 | 114 |

这是工厂空场景里实际创建节点后的清单，不是宣传页统计。5.2.1 相对于本机普通 5.2.2 多出的 13 类节点，在本机旧 Goo 4.3.2 中也存在。两个 5.2 构建存在补丁版本差异，不能由类型数量比较性能或所有兼容性。旧构建的 CombineRGB、SeparateRGB 等旧 Blender 节点差异不能算成 Goo 专属功能的损失。

当前使用的是 [NaMgAl-Studio 社区移植](https://github.com/NaMgAl-Studio/goo-engine-5.2.0)，不是 DillonGoo 官方发布的同版本二进制。[原 Goo README](https://github.com/dillongoostudios/goo-engine/blob/goo-engine-main/README.md)的重点是 EEVEE/NPR。此次读取社区 main 源码；用本机构建短 SHA 定位公开源文件返回 404，因此源码与二进制没有完成同提交锁定。下述“实测”以本机构建为准；源码解释保持独立。

| 相对普通 Blender 增加的类型 | 用途 | 本轮证据 |
| --- | --- | --- |
| Shader Info | 分别读漫反射受光、投影、自阴影、环境光、Half-lambert | 节点存在、源码、阴影／功率对照 |
| Light Info | 读取指定灯的颜色与功率 | 节点存在、源码、三次跨帧改灯实渲 |
| Screenspace Info | 采样场景颜色和深度 | 节点存在、源码、双开关与偏移正例 |
| Curvature | 屏幕深度差的曲率／rim 信号 | 节点存在、源码、原始和放大信号实渲；尚非可用生产 rim |
| Set Depth | 改写着色表面的光栅深度 | 节点存在、源码、连接输入后的遮挡反转 |
| OKLab Color Ramp | 在不同色彩空间插值 | 与普通 RGB 色带同端点实渲 |
| SDF Primitive | 解析距离形状 | 心形距离遮罩实渲；不是生成网格 |
| SDF Op | 距离场布尔／平滑组合 | 节点及枚举存在，未做组合渲染验证 |
| SDF Vector Op | 距离场坐标处理 | 节点及枚举存在，未完整实作 |
| SDF Noise | 程序距离扰动 | 节点存在，未实作 |
| Hex Grid Texture | 六边形纹理 | 节点存在，未实作 |
| Twirl | 旋转扭曲坐标 | 节点存在，未实作 |
| Water Ripples | 程序涟漪 | 节点存在，未实作；没有验证真实水体模拟 |

此外材质增加 light_group_bits、light_group_shadow_bits、check_shadow_id 和 light_groups 等属性。本轮没有发现专属 Cel 或 Anime Line 节点；Toon BSDF、Shader to RGB、Principled、景深等本来就有，不能都归为 Goo 新功能。也没有仅凭引擎名承诺所有 Cycles 路径和所有 Blender 插件兼容。

## 六个值得带入后续制作的实测结论

### 1. Shadow ID 决定 Cast / Self 的语义

同一平面、同一遮挡立方体、同一太阳，输出 R=Cast、G=Self、B=0。接收点 9×9 ROI：

| 条件 | 线性 RGB | 解释 |
| --- | --- | --- |
| 关闭 check_shadow_id，遮挡物独立 | 0,0,0 | 两路都变暗，不能声称已拆开 |
| 开启，遮挡物独立 | 0,1,0 | 外部投影进入 Cast |
| 开启，遮挡物合并到接收网格对象 | 1,0,0 | 同对象遮挡进入 Self |

MMD 的发、脸、衣服可能在同一 mesh 对象里；“自己的头发投到自己的脸”是否进入 Self 与对象身份有关。不能只按节点名称推断角色语义，更不能不检查对象组织就把某一路关闭。原生地面影子、脸部设计阴影、AO 仍须分清。

### 2. Half-lambert 不等于真实遮挡，也不等于灯光能量

R=Half-lambert、G=Diffuse Shading 亮度、B=Cast。在正对太阳的平面上，太阳功率 1→4，R 保持 1，G 从 0.318115→1.272461；加遮挡后 R 仍为 1，G 仍为 0.318115，B 降为 0。此设置中 Diffuse Shading 是未乘阴影的受光项，且可大于 1。

社区当前源码在每灯方向上计算 0.5·dot(L,N)+0.5，再进入聚合。Half-lambert 是形体包裹项，阴影需另接；不能当成已经乘过遮挡的最终照明，也不能在 HDR 受光上照搬固定 0–1 色带。多灯聚合策略仍须按灯组单独标定。

### 3. 材质灯组也控制普通 BSDF

红／蓝两盏太阳，普通 Principled 材质单选红组输出约 (0.949665,0,0)，单选蓝组输出约 (0,0,0.949665)。Shader Info 继承材质组也分别取得红／蓝；给 Shader Info 设 Own 蓝组，则能覆盖材质的红组选择。

因此人物受光与场景灯光有更直接的分工入口，普通材质并非完全在组外。该证据只覆盖简单直接光；没有验证所有探针、反射、体积、多重集合和透明路径。Goo 材质灯组、阴影许可与 Blender 对象灯光链接也不能混为同一个开关。

Light Info 另测功率 1→4→2，输出实际同步为 1→4→2，第二次无需手动重编译材质。Perceptual Power 是结合灯颜色感知量的输出，在白灯测试为约 0.976074×功率，不是表面照度，也没有距离衰减的含义；这只是三次跨帧修改，不等于已验收长动画驱动。

### 4. Screenspace 与 Set Depth 都有容易漏掉的前提

场景 Ray Tracing 关闭时，Screenspace 颜色为黑；只开启场景开关仍黑。同时开启材质 use_raytrace_refraction 后，前景 Emission 面可取得后方红蓝画面。View Position 接入偏移后，采样区实际移到蓝色；Scene Depth 在该测试为 5.0。读取到的是相机缓存，不是任意离屏世界的完整数据。当前源码还对层次、可取得的背景缓冲有约束，不能保证任意透明层递归采样。

Set Depth 的隐藏 View Depth 输入若未连接，当前源码会替换为本片元自身深度；只给 default_value=6 不生效。连接 Value=6 后，本来在前的蓝面被红背景遮住，实渲 ROI 从蓝变红。它能做风格化深度排序，但没有移动网格、修复物理碰撞或证明阴影同步改变。

### 5. Curvature“黑输出”已有纠正证据

此前球体肉眼看黑，曾怀疑 forward／屏幕资源路径；本轮读取线性 EXR，Scene Rim 原始最大值为 0.001437187，乘 500 后为 0.71875。额外连接 Shader Info 强制相关路径，并未改变这组最大值。这组对照不支持把先前黑图归咎于缺少 Shader Info。

当前源码使用屏幕深度采样，内有很小的量级与参考屏幕步长。放大后的球体大面积内部也亮起来，并不是干净细轮廓。500 是观察用增益，不是推荐预设；生产人物继续保留已验证的分区方向 rim。今后需要分辨率、镜头运动、深度断层与时间闪烁测试后才能采用。

### 6. 新插值与 SDF 不是自动质量提升

相同红蓝端点，OKLab 色带的中部比本次 RGB 色带更低饱和；不能宣传它自动鲜亮或自动去灰。人物仍需有意识地设计明暗色。SDF Primitive 心形已实际渲染；还需给宽平面坐标做宽高比补偿，才不会把图案横向拉伸。解析 SDF 遮罩并不等于原神脸影贴图、头部光向映射、体积模型或网格生成。

## MME 原包：这次新增读到了什么

前一批 PowerShader、PAToon、tn_PostPointLight、wDark、PostRimLightToon、PostRimLighting、M4Layer 等原包的范围与对应方式见前篇。本轮额外取得 BeamMan 作者官方归档中的五个小包，并补上此前遗漏的 HAToon `.hlsl` 核心阅读。没有运行 MMD `.fx` 或第三方程序，没有把它们称为已移植插件。

| 新读内容 | 已读机制与边界 | 对 Goo 制作的启发（尚未改生产） |
| --- | --- | --- |
| HAToon2 r14 HACore，501–577 行 | 形体 dot、扩展 half-lambert、真实 shadowValue、镜面和 Toon 查表分别计算；输出有按有效灯数平均再 saturate 的处理 | 用清晰的“信号→许可→色彩”分层；不能把其多灯平均、LDR 截断原样套给 HDR 光组 |
| msToonCoordinator Shade.fx，350–510 行 | 多尺度模糊影遮罩，在边界调整 HSY，再独立组合高光、两路补光；最终恢复原 Alpha | 伪 SSS 是影边颜色设计，不是厚度散射；可借鉴有限影边色带，必须防止跨人物／背景漏色 |
| NewToon v1.0，说明与着色核心 339–419 行 | 亮暗部分保留纹理／球面；按法线方向增亮、加深；九点阴影采样后，与形体项取 min 再混合明暗色 | 卡渲层次由影色、过渡、实际遮挡共同决定；不是“多加灯”就会得到参考图。源码在阴影图范围外还会直接回亮部，说明覆盖范围同样关键 |
| GodRay v2.5，说明、径向模糊及合成段 | 遮罩围绕投影中心做多次径向采样，再柔化合成 | 镜头效果可用屏幕遮罩／后期思路实现；不能把它叫真实体积投影 |
| GodRay Marching v1.0.2，说明、338–421 行等 | 沿相机射线在球形范围内采样，用光源周围距离图判断遮挡，并检查可见表面，附带距离衰减；最后还有加色及乘色步骤 | 有空间遮挡需求时采用有界体积与阴影；“Marching”也不自动等于物理能量守恒散射。说明与实际 fx 的默认循环数不同，参数应以具体包为准 |
| PostFog：两个说明、DrawHeight/DrawZ 与混合核心 | Height 路径记录世界 y；Z 路径实际存相机到表面的距离长度；再混合雾色。NoFog 可按对象／材质排除 | 是深度／高度后期，不是灯照亮雾。人物保护和舞台范围要明确；移到 Blender 时上轴和深度定义须转换 |
| DropShadow 0.3，说明与 UV／模糊／上色段 | 对屏幕剪影作偏移、缩放、两轴模糊，并用图案和颜色填充 | 适合 PV 图形化投影；不能替代用户要求的脚下真实接触影和方向落地影 |

来源入口为 [BeamMan 作者页](https://w.atwiki.jp/beamman/)与[作者归档](https://beammanp.github.io/BeamMan-MME-Archive/)。作者页已提示原 uploader 服务即将结束，故本轮沿官方新归档取包，而非追逐旧转载链接。原包 SHA、具体文件和阅读范围保存在[来源账本](research/GOO_FEATURE_MME_MECHANISMS_2026_11_16.json)。HAToon 与 msTC 原作者入口分别是 [HAToon2](https://sorairo.pictures/3dcg/mme-effects/hatoon2/)与[msToonCoordinator](https://note.com/mashimashi_note/n/n2c2144638054)。

## 对猪猪参考图的下一步判断

人物柔亮仍应从底色、脸影设计、形体明暗与投影的独立控制入手；保留深色衣服和五官，限定方向和区域的 rim，再用克制的 Glow 扩散高亮。不能把整张脸 Emission 提白，或把新 Curvature 信号当成全身白圈。

礼堂蓝天、室内曝光、方向窗光、真实落地影、金属反射和体积可见度需要分开处理。窗外有方向光是合理布置，必须实际穿过可通光的开口；继续增加同向主光的可读性，比堆方向混乱的补灯更可控。GodRay／Fog 的学习提示应保留人物排除范围，避免重新出现灰雾洗脸。

下一轮若获具体制作指令，优先在副本检查两人 mesh 对象的 Shadow ID 归属，再比较材质光组与原有光组的差异；其次才是有限影边颜色与新体积方案。每项应有同帧关闭对照和短动态，不一次叠加所有新节点。当前 28 张是机制实验，不是新的美术样片，也不能证明参考风格已经匹配。

## 可复查文件

实验交付目录：`D:/codex/output/Goo-MME-Feature-Study-2026-11-16`。包括 28 张 PNG、10 份 measurements.json、4 个独立研究 blend、feature-matrix.json 和 study-summary.json。原始 EXR／第三方源码私存 `D:/codex/temp/Goo-MME-Feature-Study-2026-11-16`。图片显示用 Standard；数值来自线性 32-bit EXR，不能拿 PNG 像素值复算 HDR 数字。

Screenspace 研究工程已用工厂偏好独立重开，重新渲染的线性 RGBA 与保存前原图最大／平均绝对差均为 0；其余三个研究工程只保存，未逐一重开。早期重开脚本曾把 scene.use_nodes 错当成合成总开关而提前中止，已改为检查 render.use_compositing 后完成验证，记录在 reopen-verification.json。新增五份 Python 脚本／改动通过 Ruff；知识链接与 JSON 审计通过。这些检查不认证最终美术质量。

复现入口：[节点清单脚本](../scripts/inventory_goo_features.py)、[独立实验脚本](../scripts/study_goo_feature_mechanisms.py)。实验脚本只创建工厂空场景，不接受生产工程输入；各 case 输出目录必须不存在。原始早期 EXR 路径和后加 case 的分目录路径以每份报告为准。
