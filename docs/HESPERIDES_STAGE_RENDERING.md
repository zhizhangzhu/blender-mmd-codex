# 赫斯珀利德斯礼堂：从 Ray 材质说明到 Blender 场景渲染

**最新同机位重建见 [HESPERIDES_REFERENCE_REBUILD.md](HESPERIDES_REFERENCE_REBUILD.md)**：本页 v7 只迁移普通 PBR 参数，后续已查出随包 ToonBased、原始强度 MatCap、白幔副贴图的遗漏，完成独立 1080p 研究及开关对照。本页保留早期参数和验证记录，不把旧 v7 当作当前默认。

核查日期：2026-11-10。本轮是实际场景材质／灯光研究，不是已完成的双人全曲视频。

最新原作者资源核实见 [HESPERIDES_AUTHOR_SETUP.md](HESPERIDES_AUTHOR_SETUP.md)：确认作者原始配布视频、公开网盘、23 份随包 Ray 材质、14 份 MatCap 及源 blend 无灯光／相机；未取得完整作者布光工程。上一版清亮日光方案仍被猪猪认为不足，不能将其提亮成功等同于达到原 Ray 预览质感。后续以原作者材质与预览同机位场景对照为基线。

最新更新：猪猪认为 v7 仍偏暗、光线不自然，要求向随包 Ray 预览靠拢。双人正式工程 v4 因此采用更明亮的窗光／宽幅补光、较轻接触暗化、蓝色窗外云纹，并加入本地修改版 `material_common_2.0.fxsub` 中加算 MatCap 的 Blender 适配。详见 [双人全曲进展](DUET_FULL_PRODUCTION.md)。下文的“未移植 MatCap”和 v7 参数是前一轮研究状态，不代表最新工程；当前仍未移植完整 Ray 管线。

MatCap 新适配读取作者本地扩展：视空间法线 XY 映射至 0–1，使用 `metal1.bmp` 与指定 L 通道遮罩作颜色加算，保留 Principled 光照。Blender 图片坐标与 DirectX 的纵轴语义分别处理，强度采用本项目审看后的 0.65，并非声称与原 Ray 数值 2 完全等价。当前 14 个材质包含此层。新版关闭厚重体积盒，保留高亮泛光、固定建筑探针和补光；人物保持观海子参考卡渲。不能把 v7 的体积效果、旧材质数值与新版混写为同一最终配置。

## 已选素材和视觉目标

猪猪指定 [paierer 的赫斯珀利德斯之馆-礼堂](https://www.aplaybox.com/details/model/uRHK15qUygJZ)，本地根目录：

`E:\tools\franken\【原神】赫斯珀利德斯之馆(礼堂)_by_paierer_08fc2e9ffe6ce8e16fb42e2032c6f401\GI_Hesperides`

实际读取了 `readme.txt`、`Hesperides.blend`、贴图及材质 `.fx`，实际查看了 `Ray渲预览.jpg`。作者预览可见蓝紫冷光、高窗、白色垂幔、蓝白花、金属框架和少量暖色亮点；不能从这张图推断作者的精确灯位、曝光或完整 MME 效果链。作者提供的[演示入口](https://www.bilibili.com/video/BV1xEJe6oEmy/)尚未完成逐镜头观察。

当前主题是**雪＋婚礼＋爱**，至冬般庄严、悲壮之后仍有释然。已选择现成礼堂，不再检索替代，也不自建宫殿。蓝白花、垂幔和礼仪座椅提供婚礼语汇；冷窗光与少量暖烛光承担情绪区分。场景原包没有完成的雪景，当前研究也没有添加落雪或窗外雪山。

随包署名：模型来源 miHoYo；改造 paierer；Ray 材质 Rui_cg／三金络合物／paierer。禁止商用及说明列出的不当用途。随包明确提供 Blender 模型并要求自行处理材质，没有前一份 Aiko 场景的 Blender 最终渲染禁令。原文件保持不变，第三方模型、贴图和材质文件不提交 Git。

## Ray 与 Blender 的关系

[Ray-MMD 官方仓库](https://github.com/ray-cast/ray-mmd)描述的是面向 MikuMikuDance／MME 的 HLSL／DirectX 9 渲染扩展。它包含 PBR 材质、反射、软阴影、体积效果和后期处理，不能把 `.fx` 当作 Blender 插件执行。

本轮迁移的是贴图含义和布光方法：建筑使用 Principled PBR，人物继续保留独立的半兰伯特／卡渲／黑线方案。两者可以在 EEVEE 中共存；角色描边不应不加区分地扩展到全部建筑。人物与环境的明暗、色温及脚底接触仍须合并后验收。

## 素材审计与具体材质映射

独立进程使用 `--disable-autoexec` 打开作者文件，实际统计 103 个对象、23 个材质、1,333,708 个顶点、444,157 个多边形。原始已关联图片包括 22 张颜色贴图和 Render Result；贴图目录中有额外法线和控制图。原 blend 的主要材质只有颜色／透明连接，不能将“能打开”当成 PBR 材质已完成。

`scripts/mmd_hesperides_stage.py` 仅以文本读取包内 `.fx` 的宏与数值常量，不执行 HLSL。依据本地参数，并对照 [Ray 官方材质公共源码](https://raw.githubusercontent.com/ray-cast/ray-mmd/master/Materials/material_common_2.0.fxsub)，执行：

| 输入 | Blender 处理 | 限定 |
| --- | --- | --- |
| 原 D／DA 贴图 | 保留 sRGB 颜色及原透明链 | 不把颜色图当数据图读取 |
| 已配置的 N 图 | Non-Color → Tangent Normal Map | 强度 0.6；未证明跨软件切线基完全一致，不声称逐像素还原 |
| Smoothness 控制 | 按宏选择通道，再计算 `roughness = 1 - smoothness` | 本包 TYPE 0；仅在 APPLY_SCALE 开启时乘标量；其余类型主动报错 |
| Metalness 控制 | 按宏选择通道，本包通常为 L.G；需要时乘标量 | 不把整张 L 图或名字猜测成金属图；花草与布幔另行处理 |
| `mat_115` 烛火 | DA 颜色自发光，强度读取原参数 50 | 亮起来不等于照亮墙壁，另加局部点光源 |
| `mat_89` 窗 | 纯透明闭包 | 无额外窗贴图；当前主动省略玻璃反射／折射，以消除低透明抖动噪点 |
| `mat_103` 假丁达尔 | 隐藏原面片，另建薄体积 | 避免面片遮挡相机或叠加两套光束 |
| 花草 14／54／55／61 | 保留透明、双面，小量次表面 | readme 还列出 13，但本 blend 没有同名材质 |
| `mat_52` 垂幔 | 提高粗糙度下限、小量 Sheen | 原 UV／低面数断层仍在；材质修改不能消除几何折线 |

L 的未确认通道没有擅自当 AO 使用。原 Ray MatCap 加法、完整 G-Buffer／SSAO／色调映射管线未移植。粗糙度下限、冷石材／座椅乘色和局部 AO 是本项目的美术调整，不是作者 Ray 参数。局部 AO 以 0.18 权重作用于颜色、距离 0.35 米，是辅助接触塑形，不代表物理光照求解。

## 布光、反射和后期的实际实现

版本参数见 `presets/stages/hesperides-winter-wedding-v1.json`：

- 四盏面积灯区分冷窗主光、较弱暖补光、祭台层次与前方柔和反弹；没有继续沿用四面均匀强补光。
- 根据原烛火面的世界坐标分组，放置 14 盏局部暖点光源，避免只让火焰贴图发白。
- VOLUME 光照探针覆盖礼堂，分辨率 6×12×6、128 烘焙采样；实际后台 `lightprobe_cache_bake(subset='SELECTED')` 完成。静态环境烘焙只用于固定建筑，不能把运动人物的阴影提前烘入。
- SPHERE 探针为室内反射补充视屏外信息；它不是精确平面镜，不承诺地板拥有镜面倒影。方法参考 Blender 官方[体积探针说明](https://docs.blender.org/manual/en/4.4/render/eevee/light_probes/volume.html)与[球形探针开发文档](https://developer.blender.org/docs/features/eevee/modules/lightprobe_sphere/)，API 和成像以本机 5.2 实测为准。
- 有限体积盒内使用密度 0.0015、各向异性 0.35 的 Volume Scatter；保留建筑细节，不用大雾遮盖问题。
- AgX／Medium High Contrast；Fog Glow 阈值 2.5、Strength 0.1。当前是全图高亮提取，未声称已实现烛光专属 AOV 泛光。

### 本轮实际比较及取舍

早期 v3 四面补光偏平、窗透明抖动明显；v4 降光后过暗；v5 加入探针、烛光和薄体积。v6 试用 Light Path 分离窗外可见亮度与环境照明，EEVEE 对照没有证明它达到预期，因此最终预设移除此控制，采用统一背景强度。不要复用未经验证的分离方案。

另用 v6 同一机位实际渲染 Cycles／OptiX 64 采样／降噪，1280×720，约 38.35 秒。它显示改变引擎没有自动解决曝光和材质层次，花草阴影等也需要另外审看；当前没有将 Cycles 图作为默认成片路线。这里的静帧耗时不用于承诺全曲成本。

v7 进一步区分深色冷石材、蓝色座椅和保留明亮的白幔，加入轻量接触 AO，输出同机位原材质／材质转换／光照气氛三个阶段和另一机位。它是场景研究成果，不是 Gosari542／观海子的原始参数复刻。

## 可复用运行方式

在仓库根目录执行 PowerShell，输出目录必须是新路径：

```powershell
& 'E:\tools\Blender Foundation\Blender 5.2\blender.exe' `
  --background --disable-autoexec `
  'E:\tools\franken\【原神】赫斯珀利德斯之馆(礼堂)_by_paierer_08fc2e9ffe6ce8e16fb42e2032c6f401\GI_Hesperides\Hesperides.blend' `
  --python scripts/mmd_hesperides_stage.py -- `
  --output-dir 'D:\codex\output\Hesperides-Stage-New-Run' `
  --samples 192
```

这是**场景专用脚本**，不要直接打开含人物的双人工程运行：它重建场景灯光和研究相机，并按作者场景材质布局处理数据。后续整合时应载入已处理的场景集合，保留双人原生相对站位、已烘焙动作和とっとこ相机；研究相机不用于替换正式运镜。

审计入口 `scripts/blender_scene_audit.py --output NEW_REPORT.json`，也在 Blender 内执行。脚本以节点类型识别 World Background，不能依赖本机语言下的英文节点名。本机引擎枚举为 `BLENDER_EEVEE`，不能照抄旧例的 `BLENDER_EEVEE_NEXT`。

## 输出与尚未通过的部分

本轮目录：`D:\codex\output\Hesperides-Stage-Study-v1\material-lighting-v7`。

- `baseline.png`：相同研究主灯下的原材质；不是作者原始 Ray 图。
- `material-refined.png`：同镜头材质适配。
- `lighting-refined.png`：加入探针、局部烛光及体积。
- `aisle-refined.png`：另一场景机位。
- `hesperides-stage-refined.blend`：贴图打包的本地研究工程。
- `stage-report.json`：源路径、转换记录、参数、采样与耗时。
- `before-after.png`：原材质与完整适配的同机位对照；由 `scripts/review_hesperides_stage.py` 生成。
- `reopen-report.json`／`verification.json`：独立进程重开与渲染验证，53 张文件贴图全部打包、18 盏灯、两类探针均保留；重开前后同机位图的 8-bit 平均绝对差为 0.0001505。源 blend／PMX／readme 的 SHA-256 同时归档；没有将原素材另存覆盖。

正式双人整合还要校准地坪与表演区域、确认座椅／台阶不穿人物或原相机、检查人物与环境的曝光／色温关系、完成窗外冬季元素以及全曲连续渲染验收。用户暂缓全曲镜头校正，不能以本轮静态场景相机擅自覆盖现成相机。
