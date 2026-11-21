# MME 卡渲与灯光：原包阅读及 Goo 实作

2026-11-16。目标是猪猪的明亮蓝天礼堂、方向窗光与人物落地影、柔亮人物和局部边缘光。用户给出的千问回答仅作为待验证线索。

后续同日增量：[Goo 节点机制与 MME 深入实验](GOO_FEATURES_AND_MME_MECHANISMS.md)。已纠正下表 Curvature 黑图的解释，补读 HAToon 核心、msTC 影边处理和五个 BeamMan 原包；不改变本篇对应生产版本的历史参数。

## 实际阅读范围

已经读取用户的[49 位作者推荐整理](https://www.bilibili.com/opus/844214760220131363)，并从原作者配布取得 9 个小体积原包，私人缓存与 SHA 见 `docs/research/MME_DEEP_STUDY_2026_11_16.json`。并非已经逐一掌握全部 49 位作者的所有预设。

本轮重点：PowerShader 3.2 的说明、预设、Config 和 Common_Shader 的基础着色及阴影合成段；tn_PostPointLight 0.30 说明与点光函数；wDark 0.51a 全部说明；PostRimLightToon v08 的说明及球面贴图/阴影控制；PostRimLighting r4 的合成、3D rim 与 2D 模糊段；PAToon 2.98b 包内仍标 2.96 的主要说明、影倾向图与控制器；附带 ExcellentShadow 2.4 说明前半；HAToon2 r14 生成器说明主要设置段；M4Layer r12 合成说明；msToonCoordinator 2.1 说明、自动影色核心段及作者图文。没有执行这些第三方程序，也没有在 Goo 中执行 `.fx`。

## 对制作有实质作用的区别

| 预设 | 从原说明或源码确认的机制 | 在本工程的使用方式 |
| --- | --- | --- |
| [PowerShader](https://bowlroll.net/file/195743) | 基于 MMD full.fx；亮部、暗部、贴图、球面、真实遮挡及后期分别控制。Toon 预设另加阈值查表；不是所有模式都等于同一种硬边色块 | 沿用既有 MMD 底色和 Alpha，只调整单份人物明暗色带；Goo Cast Shadows 单独进入受光响应，不以额外 Emission 抹掉暗部 |
| [PAToon](https://bowlroll.net/file/104601) | 形体阴影、真实遮挡方向、球面高光方向可分开调整；影倾向纹理以中灰为中性；不同版本的 LocalShadow 支持不同 | 保留已有脸 SDF/头部代理形体，不强迫真实鼻面法线决定所有脸影；地面投影仍由实际灯光产生 |
| ExcellentShadow（PAToon 随包） | 三类阴影图动态混合并后处理；扩大阴影覆盖会损失细节；需要接收材质支持，不是读入 x 就完成 | 用 Goo 原生阴影输出与真实接收面，明确影子可读性、覆盖和柔度分别控制；不照搬 MMD 的 9000 等单位 |
| [tn_PostPointLight](https://bowlroll.net/file/188141) | 法线点积、空间距离衰减、范围截断与 HDR 上限；作者明确不支持自阴影 | 只借鉴局部补光和法线渐变控制。不能用它解释或替代人物在地面上的投影 |
| [wDark](https://bowlroll.net/file/149977) | 从原点或三个骨骼中心计算距离，保留局部亮区，其余区域变暗；不是光源，也不是单纯相机雾 | 当前明亮礼堂不启用远方整体压暗。必要时可对背景分区调整，不能让人物一起灰掉 |
| [PostRimLightToon](https://bowlroll.net/file/146255) | 后期加法球面贴图，可控制方向/宽度/排除材质；默认压制阴影中的 rim，另有忽略阴影控制 | 复用现有 rim 模块；增加 Goo Cast Shadows 许可，暖侧为主、冷侧降低；保留金色/青色排除与 Alpha |
| [PostRimLighting](https://sorairo.pictures/3dcg/mme-effects/postrimlighting/) | 3D 版用视角、法线和方向控制表面绕光；2D 版从遮罩扩散，只围绕外边缘 | 当前用受控表面亮边，不把视角 grazing 项说成屏幕空间深度描边；Goo Curvature 的黑球实验尚未解决，未冒称可用 |
| [HAToon2](https://sorairo.pictures/3dcg/mme-effects/hatoon2/) | 可编辑的二维色彩查找与合成顺序；可接独立 LocalShadow/HgShadow/ExcellentShadow | 复用已有色带、贴图和控制开关，不安装重复的整套人物材质 |
| [M4Layer](https://sorairo.pictures/3dcg/mme-effects/m4layer/) | RT 分层、合成模式与排除遮罩，本身默认不改变画面 | 保留人物保护和字幕独立合成，不用全画面柔光覆盖所有颜色 |
| [msToonCoordinator 2.1](https://note.com/mashimashi_note/n/n2c2144638054) | 取其它效果的结果再卡通化；影色 RT 独立、支持自动影色和伪 SSS；Normal 路径不等于真实阴影 | 区分配色与遮挡。少量粉/冷色变化放在人物色带里；不把边界饱和处理叫物理皮下散射 |

## Ray 场景部分

补读 [PAToon 2.98 作者说明](https://pip-mmd.hatenablog.com/entry/ar1909483)正文至第⑤项，确认影倾向纹理只是改变出影倾向：即使局部为白色，进入真实遮挡时仍会变暗。Toon、球面及额外控制图的槽位与像素标志有专门约定，不能把同名贴图随意互换。另读 [HgSpotLight 的 Toon 改变版](https://pip-mmd.hatenablog.com/entry/2024/02/24/230134)与[遮罩说明](https://pip-mmd.hatenablog.com/entry/ar945815)：改变包依赖原 HgSpotLight，排除遮罩须匹配该效果的 RT 计算；任意 BlackMask 并不保证通用。Goo 中对应的是材质许可和接收集合的明确选择，而非只给物体换一张黑图。这部分续读未更改已锁定渲染输入。

再次核对 [Ray-MMD README](https://github.com/ray-cast/ray-mmd) 和 [ray.conf](https://github.com/ray-cast/ray-mmd/blob/master/ray.conf)：太阳、IBL、多灯、投影、AO、反射、HDR 后期和色调映射是不同环节。蓝天外观本身不能证明室内获得了正确间接光。本次继续复用已有天空、GGX/Principled、舞台底色及局部真实灯光；没有声称重新实现整个 Ray，也没有把旧 probe 缓存说成已重烘。

窗外放灯合理：太阳使用近似平行光，开口和窗框负责遮挡。新增许多方向混乱的灯容易洗掉阴影；先确定主方向，再用较大低强度灯补暗部。人物卡渲可以使用独立灯组，但其真实地面投影仍须来自同一场景中的遮挡关系。

另复核 [LightBloom 的核心源码](https://github.com/MikuMikuShaders/LightBloom/blob/master/LightBloom.fxsub)中亮度阈值、五级模糊合成及输入/输出变换段：这是亮像素提取与不同尺度光晕，不是整体曝光。原版包含面向其输入约定的逆色调映射；Goo 已在线性空间合成，不能将这一步直接再套一遍。当前复用已有克制的 Glow，没有把整幅画面模糊。再次核对 [FXAA 包装与参数](https://github.com/MikuMikuShaders/FXAA/blob/master/FXAA.fx)，它处理当前帧图像边缘，不能代替灯光投影或保证时间稳定。两项源码阅读是本轮增量，README 在兼容性研究中已经读过。

## 本轮 Goo v2 实作与范围

入口 `scripts/prepare_goo_daylight_v2.py` 只接受 Goo v1 的固定 SHA，新目录另存。调整舞台既有受光范围和灯比，保留蓝天；加强已有小尺寸窗向投影灯，给地面接收材质增加独立原生 Cast Shadows 调制，避免大补光洗掉影子。人物保留原色与脸形，微调肤色/衣服单份色带，降低双侧整圈白边并加入遮挡许可。没有新物理模拟。

外部 Sun 可见性诊断实际显示表演区几乎全黑；几何射线也读到墙面/装饰遮挡，因此没有靠无限加功率假称穿窗成功。第二步 `scripts/add_goo_window_gobo.py` 复用原舞台接收集合，增加镜头外真实遮光条和聚光灯，模拟窗格投出的光带。它产生真实几何投影，但属于灯光附件，不是原窗框逐格投影的认证；原建筑不改。

新增一个独立全身开场相机，4140–4228（输出前 1.5 秒）；4230 起回到原 MMD 相机。原相机及其 Actions 保留。这样新样片可以展示脚与落地影；不将新相机替换成全曲镜头方案。制作诊断时要临时解除相机 marker 绑定，否则 render 会按 marker 再切回近景，单纯赋值 `scene.camera` 不足。

现有 Goo 5.2.1 是 NaMgAl-Studio 社区移植版，非 DillonGoo 原版二进制；实际节点为 Shader Info/Curvature/Light Info，未找到 Qwen 所说的专属 Cel 或 Anime Line 节点。运行时和插件的先前实测见 [Goo 迁移记录](GOO_ENGINE_MIGRATION.md)。

本轮制作图、保存工程和最终视频分别记录状态；静帧不能证明动态完全稳定，用户评价不能由技术测试替代。沿用猪猪此前指定的 1080p30、五秒、单版字幕、指定原唱，跳过输出后的解码和审片。风格与参考仍有差距，不写成原版 MME 复刻成功。

## 许可与缓存

第三方原包与全文只保存在 `D:/codex/temp/MME-Deep-Study-2026-11-16`，不放进仓库或交付工程。PowerShader 说明允许使用/修改/再分发；tn_PostPointLight 明确不允许一般再分发（协作等例外以原文为准）；wDark 不希望原样再分发；PAToon 遵循各上游条款；其它以各随包说明为准。本轮交付的是原创接线/参数与来源总结，没有打包这些 MME。
