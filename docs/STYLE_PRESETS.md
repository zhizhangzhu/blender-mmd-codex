# 多风格渲染、后期与横竖屏预设

2026-11-09，按猪猪的要求建立。当前维护两类参考方向：Gosari542 与观海子；观海子下再分粉色图形和紫红舞台两个变体。后续在这些可验证基线上发展个人风格，不把尚未形成的个人特色预先写成已完成能力。

这里的名字表示**根据用户指定作品观察而制作的参考方向**，不是作者原始预设、参数恢复、作者授权或同等质量保证。参考署名与实际帧证据见 [Gosari542](GOSARI_REFERENCE.md)、[观海子](GUANHAIZI_REFERENCE.md)。观海子小狐狸作品简介特别提到黑煤球后期，Cherry 简介另列 PV Kit 黄白レモ；本项目没有取得或直接使用这些后期工程。

## 选择方式：风格 × 变体 × 画幅

入口是 `presets/styles/catalog.json`。每个组合有自己的 package，不能仅选择一个作者名字后自动裁切成所有画幅。

| 风格 / 变体 | 竖屏 package | 横屏 package | 已实现的视觉方向 |
| --- | --- | --- | --- |
| Gosari542 / soft | `gosari-portrait-v1` | `gosari-landscape-v1` | 暖色实体舞台、轻面部阴影、分区衣发明暗、克制描边、局部泛光、背景景深 |
| 观海子 / graphic | `guanhaizi-graphic-portrait-v1` | `guanhaizi-graphic-landscape-v1` | 较窄卡渲过渡、紫色暗部、粉色菱格平面背景、白色贴纸外轮廓、深紫动态文字、细白边框 |
| 观海子 / neon | `guanhaizi-neon-portrait-v1` | `guanhaizi-neon-landscape-v1` | 较深紫色衣发暗部、粉紫轮廓光、更多局部泛光、现有舞台上的紫红氛围合成、背景光点与细边框 |

`packages/*.json` 中的 id 即上表名称。Neon 只是现有舞台的灯光/合成变体，没有重建参考中的狐狸图案、双人调度或整套舞台。

本轮交付在 `D:\codex\output\MMD-Style-Presets-v1`：`review/style-matrix.jpg` 为同姿态渲染加后期对照，`render-only-matrix.jpg` 只看 Blender 输出；`stills` 保存六套静帧工程，`clips` 保存各组合的四秒带声技术样片、工程和检查报告。样片为竖 540×960 / 横 960×540、60 fps、48 samples，沿用已有衣发烘焙；不是新的二十秒正式成片。

## 预设由三部分组成

```text
presets/styles/
  catalog.json
  render/        材质分区明暗、色带、主光/轮廓光、细描边、AOV 泛光
  post/          颜色微调、背景图形、贴纸外轮廓、背景光点、暗角、字幕配色
  packages/      风格/变体/画幅、镜头、布局、引用的 render/post/typography
```

渲染和后期组件可以分别复用。例如柔光人物配图形背景，可复制 package 后单独换 `post` 引用；需要重新审看整套效果，不因组件各自通过就认定组合也已验收。修改另存新 id / 版本，旧参数和已交付样片不覆盖。

每次渲染将解析后的完整参数写入 `resolved-style.json` 和报告，不只保存一个可能日后变化的预设名字。模型的 Color/Alpha、球面与透明链仍由已有 MMD 节点提供；预设修改下游 NPR 图，不修改骨骼、Morph、物理或用户偏好。

### 渲染参数

三个 render 组件的差别真实应用于 Blender 材质和灯光，后期无法替代这一步：

| 参数 | Soft | Graphic | Neon |
| --- | --- | --- | --- |
| Toon 色带过渡区间 | 0–0.65 | 0.18–0.43 | 0.06–0.55 |
| 轮廓光相对功率 | 100 | 65 | 160 |
| AOV 泛光强度 | 0.14 | 0.055 | 0.22 |
| AOV 泛光阈值 | 0.8 | 0.95 | 0.7 |
| 景深 | f/4 | 关闭，适合平面背景 | f/3.5 |

皮肤、眼睛、眼线、头发、配饰、衣服、毛领各有明/暗色乘数与饱和度。保留银发蓝衣，不把本模型硬改成参考角色的发色/衣色。功率是当前分析式 NPR 输入的相对控制，**不是完整物理面积灯积分、投影或 GI**。面部仍未制作专用法线/SDF；改变色带不能代替这项工作。

描边沿用 MMD Tools 反向外壳、PMX 顶点/材质边宽。脚本使用绝对基线 `0.0336 × edge_width_scale`，必须连同顶点组权重理解，不能去掉权重照抄裸厚度。实际边色写入本机 `mmd_edge_preview` 组的 Color 输入；不假定其中有独立 Emission 节点。

### 后期参数

Graphic 通过 Blender 的实际角色 Cryptomatte 覆盖率将舞台换为程序生成菱格底，再由膨胀遮罩减原遮罩得到白色外轮廓。Neon 保留实体舞台，以角色遮罩限制背景色层和光点；不是把脸、衣服、背景统一染成同一色。轻量 RGB/饱和度微调在 sRGB 执行，主体背景的 alpha 合成在线性空间执行，不冒称电影级 LUT 或完整场景线性调色系统。

光点的运动由时间和固定相位决定，不逐帧随机生成，避免随机噪声式闪烁。背景菱格用等距图像坐标，横屏不会拉成长菱形。字幕填色、细边与少量发光分别来自 post 组件；保护遮罩在整组字幕效果之后应用。

Graphic 的后景字幕保护区会包含白色贴纸外轮廓，避免文字盖掉外缘；前景允许遮挡时仍可盖过它。外轮廓、边框、字幕发光范围与保护距离都在实际输出分辨率换算，低分辨率有至少一像素的取整限制。

遮罩来源与实现已由本机验证。[Blender Cryptomatte 官方文档](https://docs.blender.org/manual/en/latest/compositing/types/mask/cryptomatte.html)说明 Render 来源、Object/Material 名称选择及 Matte 输出；原生对象/材质标识并不等同于通用成片抠图。该页本轮直接访问并读取正文，部分搜索工具读取失败不能当成未存在。本模型的材质名、透明/边缘条件仍需实际检查。

## 横竖屏必须分开的内容

| 项目 | 竖屏 | 横屏 |
| --- | --- | --- |
| 当前取景 | 继承已验证的 65 mm 表情/半身两段镜头 | 独立 50 mm、左右偏心构图，预留横向文字区域 |
| 切镜与轨迹 | 421–540 / 541–660，沿用平滑头部跟随 | 同一切点用于比较，机位、景别、左右偏移独立生成；各变体另有参数 |
| 官方文字源 | 1Sabi Typography(Tall)，从 17.983333 秒起 | Full Typography(Wide)，从 66.766667 秒起 |
| 前后层 | 独立竖版 cue 表 | 独立横版 cue 表；不从竖版比例换算 |
| 外轮廓与边框 | 使用竖版 `layout` 的高度比例 | 使用横版 `layout` 的高度比例与不同留边 |
| 人物保护区 | 按画面高度换算像素 | 使用横版比例；不得照搬竖屏固定像素 |

镜头设计和字幕设计是两个职责，不在更换渲染预设时偷偷修改原动作。为了同姿态 A/B，这次同画幅的三套竖版使用同一已验证轨迹，横版变体有各自偏心和景别参数；没有宣称六套都是全新原创分镜。后续具体内容可以另换导演方案，不把本次四秒镜头当成全曲模板。

以上是旧套装支持的层级。双人新制作按 [整组固定层级](DUET_CAPTION_STABILITY_AND_LIGHTING.md) 处理：前景整组在前，不再用 `front/face` 挖开部分文字；背景整组在后，按连续覆盖率遮挡。遮脸问题通过排版或整组改层解决，避免同一字局部前后穿插。横竖文字起点匹配也不等于完成伴奏卡点。

## 复用命令

在仓库根目录执行，沿用本机已安装 Blender 和现有 FFmpeg。列出入口或展开参数：

```powershell
python -m scripts.style_presets --list
python -m scripts.style_presets --package presets/styles/packages/guanhaizi-graphic-portrait-v1.json
```

批量复现本次已验证的 421–660 帧、60 fps 四秒实验：

```powershell
& .\scripts\render_style_suite.ps1 `
  -OutputRoot 'D:\codex\output\style-suite-new' `
  -CacheRoot 'D:\codex\temp\style-suite-new' `
  -PackageIds @('gosari-portrait-v1','guanhaizi-graphic-portrait-v1')
```

默认包含全部六种组合。可用 `-Percentage 100 -Samples 96` 输出全尺寸，但**当前实际验收是 50% / 48 samples**；全尺寸需重查输出线宽与时间域效果。该实验命令有意固定当前已验证动作范围，不是通用模型/全曲自动重定向入口。换动作、帧范围或模型时重新做对应制作步骤。

单独渲染或仅调整后期：

```powershell
$package = 'presets/styles/packages/guanhaizi-graphic-landscape-v1.json'
& 'E:\tools\Blender Foundation\Blender 5.2\blender.exe' --background `
  'D:\codex\output\MMD-Tutorial-Study-v1\tutorial-study.blend' `
  --disable-autoexec --python-exit-code 1 --python scripts/mmd_caption_render.py -- `
  --style-package $package --aspect landscape `
  --output-dir 'D:\codex\output\style-scene-new' --cache-dir 'D:\codex\temp\style-scene-new'

python scripts/typography_composite.py --style-package $package `
  --cache-dir 'D:\codex\temp\style-scene-new' `
  --typography 'E:\tools\franken\FrankensteinNoKaibutsu_Video_Full_Typography(Wide).mp4' `
  --ffmpeg 'D:\codex\temp\blender-mmd-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe' `
  --output-dir 'D:\codex\output\style-post-new'
```

修改颜色、背景、边框或文字配色可复用对应 beauty/matte/face 序列；改变角色材质、灯光、相机、景深或场景需要重新渲染。Blend 保存渲染预设和通道，Python 执行后期；**只打开 Blend 渲染不会自动生成粉色图形底、贴纸外轮廓和最终字幕**。当前后期也不是可安装到其他软件的通用 MME。

脚本默认拒绝已有输出目录。可在原脚本命令增加 `-Resume`，核对已完成阶段的参数、输入路径、质量、帧范围与缓存完整性，再复用，不覆盖已有视频；音视频检查使用新的报告名。不要在同一源文件路径替换内容后沿用旧缓存。部分生成但未完成报告的阶段会拒绝继续，应保留诊断目录并使用新目录。

Windows PowerShell 5.1 实测：脚本用 `[char]0xB1` 构造伴奏文件名，避免无 BOM 脚本将 `±` 读错；FFmpeg 的正常 stderr 进度不能当成失败，应检查真实进程退出码。首次批处理在此处失败后，实际复用已完成图像与合成缓存，未丢弃重渲。

## 后续发展个人风格

保留两类参考基线。每次只改变有明确意图的一组特征，例如眼睛高光形状、发丝明暗边界、暗部色相、人物/背景对比、文字节奏或转场语言，保存同姿态与同动作对照。选出稳定有效的组合后，复制 render/post/package 为新的 `zhuzhu-...-v1`，在 catalog 增加新的 family，并记录基于哪份版本和为什么改变；不要直接覆盖参考预设。

个人风格也要有 portrait 与 landscape 两个导演/布局入口。可共享材质和颜色组件，但各自选择景别、机位、字幕空间和效果尺度。跨模型复用先建立材质分类和脸部遮罩映射，当前阿克西妮娅的中文材质名称不是所有 PMX 通用接口。

## 验证与边界

本机 Blender 5.2.2 / MMD Tools 4.5.14，EEVEE。六种组合实际渲染静帧并检查图形后期；短视频状态以交付根目录的 `delivery-manifest.json`、各组合视频/音频及合成报告为准。初始 32 项测试通过，新增测试覆盖画幅/镜头不匹配拒绝、每变体双画幅齐备及图形换底对不透明角色的保留；实际渲染、逐帧解码和图像检查另行完成。

最终六支样片全部完成：每支 240 帧、60 fps、4.0 秒，共 1440 帧完整解码，尺寸分别为 540×960 / 960×540；均含实际解码的非静音双声道 48 kHz 伴奏，未检测到全黑或连续静止帧。六套字幕保护区域的编码前最大线性差为 0。最终 32 项测试、编译与 diff 空白检查通过；像素检查不代替所有美术问题的审看。逐项校验值、采用的修订合成目录与报告路径已写入交付清单。

粉色竖屏的初版合成在 `composite`，补查白色外缘后修订为 `composite-outline-v2`，主视频已更新且重新解码检查；初版视频另存 `initial-graphic-portrait.mp4` 供诊断。最终清单记录每套实际采用的合成目录和媒体校验值，不将初版检查混用于修订视频。

当前图形合成的角色是从有背景 beauty 按覆盖率近似分离，复杂透明、景深边缘可能保留背景色，不是精确去污染的 RGBA 重建；没有宣称适用于复杂玻璃、体积或全部运动模糊场景。边框可按美术需要盖在手部；白色贴纸线与原材质描边是两种不同效果。模型分区、法线和更细腻材质仍有改进空间，预设分类完成不等于达到参考作者同等质感。
