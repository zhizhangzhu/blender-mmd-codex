# 进阶质感：插件学习、材质与光影实测

2026-11-09。猪猪提出进一步提高质感，并提供 Ray-MMD、材质分类、AO、体积光、Toon、M4Layer 和效果链等方向；随后指定半兰伯特教程，本轮重点转向该参考，同时保留独立光影实验。半兰伯特视频、简介和评论的实际阅读记录见 [HALF_LAMBERT_STUDY.md](HALF_LAMBERT_STUDY.md)。

## 当前最需要补的能力

目前人物大部分通过分析式 NPR + Emission 显示，舞台有实际灯光，但人物并未自动获得完整物理投影/反射/GI。提高采样或单纯增加灯光数量，不能补齐这些职责。当前更有效的顺序是：按材质设计明暗输入 → 检查法线和控制贴图 → 局部遮挡/接触关系 → 金属等特定材质响应 → 舞台气氛 → 后期。艺术取舍按风格决定，不能要求所有角色统一硬色阶或强泛光。

## 原作者资料与本机状态

| 工具/方法 | 原作者资料与用途 | 本轮实测状态 |
| --- | --- | --- |
| Paper Anime Render Helper | [官方扩展页](https://extensions.blender.org/add-ons/paperzhu-animehelper-extension/)，作者教程入口 BV1YaPYz5EDX | 已安装 2.5.0；阅读本机高光/描边/Toon 源码。在当前 MMD 材质副本上调用高光函数返回 False，在 Principled 测试材质返回 True；不是插件“失效”，而是输入结构不同。没有把全模型强转后宣称导入语义保持 |
| Abnormal | [BNPR 原仓库](https://github.com/bnpr/Abnormal)、[法线球形化教程](https://bnpr.gitbook.io/bnpr/shaders/toon-shading-nbpr-abnormal-normal-sphering) | 从作者 release 获取源码，代码版本 1.1.6、发布 tag `V1.1.16`（两者写法不同）；在 Blender 5.2.2 工厂偏好进程成功注册六个算子后注销。未永久安装、未保存偏好，也未验证 GUI 模态编辑器完整操作 |
| 咖啡工具 | [作者仓库](https://github.com/kafeijk/mmd_kafei_tools)，本机 1.9.2 | 阅读本机法线转移源码：用 Data Transfer 传自定义角点法线，需要匹配源/目标拓扑，PMX→PMX 分支会跳过。它不是无需源数据的自动艺术法线修复 |
| Goo Engine | [DillonGoo 原仓库](https://github.com/dillongoostudios/goo-engine) | 原作者说明为 Blender 定制分支，含 NPR 节点与灯组；不是普通 `.zip` 材质插件。未下载替换当前 Blender；第三方 5.2 移植不能与原作者构建混称 |
| Malt | [BNPR 原仓库/说明](https://github.com/bnpr/Malt)、[发布页](https://github.com/bnpr/Malt/releases) | 已读 README：NPR 渲染框架、自定义节点/管线、OpenGL 4.5 等要求。发布页有多个 Blender 分支版本；未安装，也未验证当前 MMD Color/Alpha、AOV、Cryptomatte 与材质迁移，不能当作一键升级当前工程 |

Abnormal 下载和注册记录在 `D:\codex\temp\mmd-quality-abnormal-v001` 与交付根目录 `abnormal-registration.json`。本轮面部法线实验使用 Blender 原生 custom split normals API，不能因此声称是通过 Abnormal GUI 完成；注册通过也不等于 UI 编辑和渲染全流程通过。

## 用户提出的 MMD/MME 方案如何理解

[Ray-MMD 原作者 README](https://github.com/ray-cast/ray-mmd/blob/master/README.md)明确其运行环境是 MMD/MME、HLSL/DX9，并描述物理材质、软阴影、AO、体积、泛光等职责。它能作为学习结构，但不会在 Blender 导入 `.fx` 后自动得到相同渲染。金属/布料/皮肤需要各自的参数与纹理，使用 PBR 本身并不保证消除塑料感；不匹配的粗糙度和高光反而可能加重问题。

[M4Layer 原作者页](https://sorairo.pictures/3dcg/mme-effects/m4layer/)描述后期与 Shader 两种版本、RT 分层合成和遮罩；Release 11 还提供分混合模式预设。它不是把任意互不兼容的着色器直接相加就保证正确的通用开关。本仓库用 Blender 的材质节点、AOV、Cryptomatte 和合成树划分相应职责，已实现的能力按具体实验记录，不声称运行了 M4Layer。

G-Buffer、SSAO、Bloom 等是渲染架构中的不同步骤，不能由“堆多个效果”自动变成完整延迟渲染器。当前没有重写 Blender 渲染后端，也没有把局部 AO 节点冒称自行实现的 SSAO。现有 MMD Tools 轮廓是反向外壳，不是法线/深度 Edge Detection。

## 本机逐项实验

输出 `D:\codex\output\MMD-Quality-Lab-v1\render-v001`，同一源工程、相机和动作帧 421/540/601，每方案另载源场景，50% 分辨率、48 samples；共六方案 18 张实际静帧。旧输出节点先移除，原工程、源几何和缓存未覆盖。

| 方案 | 实现 | 实际结果与判断 |
| --- | --- | --- |
| 面部法线 | 仅对 `颜` 材质角点法线与椭球方向混合 0.5，保留顶点、UV、Shape Keys 和动作 | 597 个面部顶点的相关角点参与候选计算；原版材质面部已很平，当前姿态全图平均差约 0.0038/255，收益有限，不能拿“用了高级法线”当作明显提升证据 |
| 局部 AO | 距离 0.035，16 样本；衣发/配饰分强度，排除面部、眼睛、眼线和重复叠层 | 实际 AO AOV 呈现衣领、饰件和衣物交接；不是全白无效节点。源帧 421 的 AOV 有约 15.5 万个处于黑白之间的 AO 值像素；beauty 平均差约 0.160/255，刻意较轻 |
| 金属配饰混合 | 配饰材质叠 0.35 原生 Principled，metallic 0.75、roughness 0.28、coat 0.12；保留 MMD Color/Alpha | 只改变配饰响应，平均差约 0.163/255；没有专门绘制 roughness/metallic 掩码，仍只是验证分区混合，不全局替换皮肤和布料 |
| 三者组合 | 法线 + AO + 配饰 | 平均差约 0.325/255；与单项结果一起检查，未默认改写已认可的风格 v1 |
| 组合 + 体积光 | 有界雾盒，原生 Volume Scatter、两个 Spot，启用体积阴影 | 实际参与场景散射，平均差约 8.36/255；会明显改变氛围和对比，但当前近景舞台未形成特别醒目的光柱。不是屏幕上画一层假光束，也不因有雾就称为电影级 |

平均差来自同姿态 PNG，是效果发生的位置/量级证据，不是画质评分。效果还需服务内容：粉色平面风格不默认加实体舞台浓雾，柔光方向不默认改成所有材质强硬色阶。

所有方案均比较顶点位置哈希及三个姿态的全部骨骼矩阵哈希，保持一致；没有重新做物理或修改动作。`quality-matrix.jpg` 为六方案静帧总览，`combined/quality-study.blend` 与 `volume/quality-study.blend` 保存实验工程。半兰伯特的另三方案见单独文档。

### 版本与节点限制

[Blender 的 EEVEE 节点支持文档](https://docs.blender.org/manual/en/latest/render/eevee/limitations/nodes_support.html)随版本变化，本机 probe 和渲染结果优先。当前 5.2 实测 AO 节点可生成有效信号；没有照搬旧版本全局 AO 开关，`only_local` 也没有被当作已验证能力。原生 Shader to RGB 不保证所有 PBR 效果、通道和引擎兼容，不能称为一个接上去即可拥有完整物理渲染的节点。

粗糙度、金属度、法线和控制贴图的语义必须核实。当前 PMX 的颜色/球面贴图不等于教程角色完整的游戏光照贴图组；没有把未提供的专用贴图记成已取得素材。以后可以制作适配本模型的遮罩和带状发丝高光，这比继续增加全局泛光更值得做对照。

## 复用入口与后续取舍

`scripts/mmd_quality_probe.py` 核对节点和已安装插件兼容性；`scripts/abnormal_probe.py` 只用于独立进程注册测试；`scripts/mmd_quality_lab.py` 执行逐项试验，参数在 `presets/quality/npr-detail-lab-v1.json`。这是实验参数层，不直接加入已验收的风格 catalog。

```powershell
& 'E:\tools\Blender Foundation\Blender 5.2\blender.exe' --background `
  'D:\codex\output\MMD-Style-Presets-v1\clips\gosari-portrait-v1\scene\typography-source.blend' `
  --disable-autoexec --python-exit-code 1 --python scripts/mmd_quality_lab.py -- `
  --output-dir 'D:\codex\output\quality-lab-new' --preset presets/quality/npr-detail-lab-v1.json
```

优先继续精修已实现的半兰伯特分区梯度与局部 AO；Abnormal 适合今后有明确需求时进行可视化法线编辑；Malt/Goo 是另立渲染路线的研究候选，需单独验证现有模型、物理、材质与输出通道。当前不把换引擎当作质量保证，也不让已认可的两类风格被实验参数覆盖。
