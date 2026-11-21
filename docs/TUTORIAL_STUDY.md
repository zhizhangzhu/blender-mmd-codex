# 卡渲、打光、镜头和 MME：教程研究与本机试验

研究日期：2026-11-09。目标是继续改善阿克西妮娅试作，学习 Gosari542 参考中干净的人物、清楚的材质层次和有选择的镜头表达。这轮交付是**研究工程、逐项对照和四秒技术试样**，不是替换已有二十秒成片的新正式版本。

## 资料阅读状态

区分「检索到标题/简介」「读到完整正文或源码」「在本机验证」。视频标题和搜索摘要不能充当完整观看记录。本轮没有声称看完以下 B 站视频；它们保留为后续观看入口，具体技术判断以实际读到的原作者文字、源码及本机试验为依据。

| B 站入口 | 作者/主题 | 本轮状态与用途 |
| --- | --- | --- |
| [新手进阶3：水面、自发光、阳光照射](https://www.bilibili.com/video/BV15x411i7GY/) | RedialC；页面合集另列打光技巧、2D 风格 Ray、相机绑定、雾气等课题 | 标题、简介及合集目录已检索；播放页抓取受限，未完整观看 |
| [LS_ToonShader 2.1 使用教程与配布](https://www.bilibili.com/video/BV1Wg41117rT/) | LenXiaoA / BRUSH233；卡渲着色器教程 | 已核实简介中的作者和配布入口；未下载着色器，未声称可直接用于 Blender |
| [简单讲讲 MMD 里的镜头曲线和一些小方法](https://www.bilibili.com/video/BV1cV4y147Fj/) | 千月其一；镜头曲线、平滑过渡、K 帧演示 | 标题、作者与合集目录已检索；曲线技术结论另查 Blender 官方文档 |
| [MMD 动画运镜的导入和微调](https://www.bilibili.com/video/BV1mwto6LEek/) | 知知呜Blender；VMD 相机导入与调整 | 已读取简介；作为已有镜头适配流程的补充入口 |

已实际阅读的主要材料：

| 原作者/官方材料 | 提取的学习重点 | 本轮应用状态 |
| --- | --- | --- |
| [Niku：Ray-MMD 1.5.2 的 2D 工作流](https://www.nikunokoya.com/posts/mmd-raycast/) | 分配人物/舞台材质、眼睛遮挡控制、局部打光和效果顺序 | 阅读完整正文；用于理解 MMD 各层职责，没有照搬其参数 |
| [綾ぽむ：MMD 效果制作记录](https://note.com/pompom0313/n/n8a63014653e6) | 肤色/眼睛/头发分别处理；轮廓光和描边使用排除遮罩；按层比较效果 | 阅读文字流程；在 Blender 验证分材质轮廓光与局部泛光，没有复用作者对照图片 |
| [Rui：LightBloom 说明](https://github.com/MikuMikuShaders/LightBloom/blob/master/README.md)与[着色源码](https://github.com/MikuMikuShaders/LightBloom/blob/master/LightBloom.fxsub) | 阈值、范围、强度各司其职；控制器数值有自己的映射 | 阅读参数说明与提亮/模糊相关源码；用 Blender 原生 Glare 作效果概念试验，未在 Blender 运行此 MME |
| [BNPR：基础 NPR 着色器](https://bnpr.gitbook.io/bnpr/shaders/the-most-basic-npr-shaders) | 将光照信号、色带、基础贴图和透明分别处理 | 已读；本轮保留 PMX Color/Alpha，改进灯光输入 |
| [BNPR：球形化法线](https://bnpr.gitbook.io/bnpr/shaders/toon-shading-nbpr-abnormal-normal-sphering) | 法线可以专门为卡渲阴影设计；面部与身体需要不同处理 | 已读；未安装 Abnormal，也未修改本模型法线，兼容性未验证 |
| [Blender：相机](https://docs.blender.org/manual/en/latest/render/cameras.html)、[曲线柄](https://docs.blender.org/manual/en/latest/editors/graph_editor/fcurves/properties.html) | 焦距、取景、焦点、光圈和曲线过冲 | 官方页面已直接读取；验证固定焦距移动机位、焦点跟随、两种景别和硬切边界 |
| [Blender：Glare](https://docs.blender.org/manual/en/latest/compositing/types/filter/glare.html)、[Light Linking](https://docs.blender.org/manual/en/latest/render/lights/light_linking.html) | 提亮阈值与模糊范围分开；限制灯光/效果的作用对象 | 已读；AOV 效果遮罩已验证，原生 Light Linking 未应用，不能与下面的节点驱动混称 |

Blender 官方页面在搜索工具中部分读取失败，但直接访问公开页面成功，正文与访问状态保存在 `D:\codex\temp\blender-mmd-tutorial-research-v001`。这是资料读取记录，不是额外安装的运行依赖。

## 对目前工程最有用的认识

v2 人物通过 Emission 显示绘制色与分析式 Toon 明暗，方向是常量。舞台面积灯确实照亮舞台，但移动这些灯不会相应改变人物的整套着色。继续增加面积灯无法自动解决这个限制。

本轮将主光的位置、颜色和功率接入人物节点。表面到灯的方向逐像素计算，功率通过有界的艺术曲线影响明暗；肤色的变化幅度小于衣发，眼睛与眼线另行保护。这是**分析式 NPR 灯光联动**，仍不具备真实面积灯积分、反平方衰减、投影或 GI，不能称作完整 PBR，也不是 Blender 的原生 Light Linking。

MME 的做法应按职责迁移：材质层决定受光方式，遮挡层提供接触关系，景深分离背景，泛光增强局部亮点，调色统一整体。许多效果的选择性分配比单纯加大强度更值得借鉴。当前没有把 SSAO 全局加深到脸上，也没有通过全局泛光把白发和毛领一起抹白。

MME 的 `.fx/.x` 属于其自己的执行环境；本项目学习视觉方法，用 Blender 原生节点实现对应试验，不把下载 MME 当作 Blender 已实现该效果。参数也不能直接互抄：本次查看的 LightBloom 源码将控制器值 `p` 转为 `(1-p)/(p+1e-5)` 的阈值；Blender Glare 的阈值含义和输入范围另有定义。

## 本机已完成的试验

源工程：`D:\codex\output\Aksiniya-Frankenstein-Final-v2\production.blend`。成功工作目录：`D:\codex\output\blender-mmd-codex\tutorial-study-v004`。v001/v002 为接口失败记录；v003 为首轮完成但近景头发余量不足的试验，均保留，不作为交付版本。

| 项目 | 实现与检查 | 结论/边界 |
| --- | --- | --- |
| 灯光联动 | 33 个基础/叠层材质读取主灯世界坐标；分区控制颜色和功率影响 | 同姿态测试左右换灯、170 W→0 W；头部区域平均像素变化分别约 8.44、13.48，确认人物确实响应 |
| 分区轮廓光 | 12 个衣发/配件材质使用视角边缘项 × 背光方向项；排除皮肤、眼睛、眼线与重复叠层 | 使用实际灯的位置/颜色/功率作控制，强度较低；这是节点轮廓光，没有调用 PostRimLightToon |
| 细描边 | 复用已安装 MMD Tools 的 `edge_preview_setup`，保留 PMX 的顶点/材质边宽；不同部位使用不同线色 | 关闭透明帽子和重复叠层的边线，避免隐藏部件出现轮廓；这是反向外壳法，不是屏幕空间法线/深度描边 |
| 局部泛光 | 虹膜和配件输出 `TutorialGlow` AOV；遮罩提取高亮后 Fog Glow，再加回原画面 | 眼白、牙齿、皮肤、毛领不参与直接提亮；同姿态 PNG 差异确认效果生效，整体平均差约 0.00170/255，刻意很轻 |
| 两段镜头 | 源帧 421–540 中景，541–660 切近景；65 mm，固定竖向传感器 32 mm，轻微移动机位 | 四秒内只验证一个硬切与两种景别，不等同于完成整首歌分镜，也未对伴奏重新卡点 |
| 构图与景深 | 对头部位置作 11 帧平滑；焦点仍跟随真实头部；f/4；逐帧检查变形后头发包围范围 | 240 帧头部/头发投影检查通过，近景呆毛余量已修正；手势仍会有意裁边，需要镜头美术判断 |

主灯以 170 W、轮廓灯以 100 W 作为本试验的相对基准；功率比钳制到 0–2。主灯关掉后保留部分艺术环境亮度，避免人物突然变成黑色。这些数值依赖本模型尺度和节点设计，不是通用摄影光比。

描边修改器的裸厚度约 `0.0336`，**必须与 MMD Tools 创建的顶点组一起理解**：顶点组还乘上 `0.02 × 材质边宽 × PMX 顶点边宽`，实际外扩远小于裸厚度。不要在其他模型上去掉顶点组后照抄这个数字。

### Blender 5.2 实测接口差异

- EEVEE 的 Render Layers 在本机没有 `IndexMA` 输出，即使启用 Material Index 也不能据此假设存在；改用 VALUE 型 Shader AOV，节点设置 `ShaderNodeOutputAOV.aov_name`。
- 合成树使用 `scene.compositing_node_group`，输出是带 Image 接口的 Group Output。
- 合成中的旧 `CompositorNodeMixRGB` 不存在；本机验证 `ShaderNodeMixRGB` 可用。旧 `CompositorNodeMath` 也不能直接创建。
- Glare 类型、质量、阈值、强度、范围等通过输入插口控制；本机使用 `Type='Fog Glow'`、`Quality='High'`、Threshold 0.8、Strength 0.14、Size 0.08。

这些差异先由 `mmd_tutorial_probe.py` 检查，再由实际渲染验证。不要仅通过算子注册或节点创建来宣称视觉效果正确。

## 复现和交付

```powershell
& 'E:\tools\Blender Foundation\Blender 5.2\blender.exe' --background `
  'D:\codex\output\Aksiniya-Frankenstein-Final-v2\production.blend' `
  --disable-autoexec --python-exit-code 1 --python scripts/mmd_tutorial_lab.py -- `
  --output-dir 'D:\codex\output\blender-mmd-codex\tutorial-study-NEW' --preview

python scripts/review_tutorial_study.py --study-dir '<新研究目录>' --output-dir '<新QA目录>'
```

实验工程按完整 1080×1920、96 采样保存；无声视频是 540×960、60 fps、48 采样、240 帧/4 秒，输出期间临时降分辨率，没有把此预览规格保存回研究工程。视频已全帧解码检查，无黑帧或完全重复帧；硬切两侧另作目视对照。24 项仓库测试、脚本编译及 diff 空白检查通过。

清晰交付目录：`D:\codex\output\MMD-Tutorial-Study-v1`。包括研究工程、无声试样、逐项对照、灯光响应对照、来源记录和 QA。视频 SHA-256：`175504b1342b9eac7816d6df4cf1d5d0cc3f2614a6f859e191eae9334aa74f45`。

## 已学到但还未在本工程实现

球形化/自定义面部法线、面部 SDF、真实各向异性发丝、逐像素金属/布料掩码、屏幕空间深度/法线描边，以及选择性景深合成仍属于候选路线。没有安装并验证的插件不记作已掌握；没有渲染过的方法不升级为默认制作流程。

后续要采用本轮方法制作新成片时，应先选择合适的描边、轮廓光与泛光强度，再完成整段镜头与连续运动验收。四秒研究视频不能替代二十秒完整成片的检查。
