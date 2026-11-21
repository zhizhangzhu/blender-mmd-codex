# 进阶 MMD 学习与横竖屏动态字幕合成

**2026-11-12 修订入口：** 下文记录初版单人实验，`front/face` 与硬阈值遮罩会造成同组字的局部前后层和边缘跳变，不再作为双人项目默认做法。最新五秒流程见 [官方字幕稳定性修订](DUET_CAPTION_STABILITY_AND_LIGHTING.md)：按实际动画整组固定层级，前景不挖脸，后景使用 PNG16 连续人物覆盖；单张白牌重建实心黑字。旧报告中的“保护区误差为零”只验证所选遮罩，不能证明视觉没有闪烁。

2026-11-09。交付目录：`D:\codex\output\MMD-Advanced-Subtitle-Study-v1`。本轮是两支带伴奏的 **4 秒技术样片**，不是替换既有二十秒成片的正式新版。已有烘焙衣发动作继续使用；本轮新增的是画幅设计、字幕素材检索、分层合成和验证能力。

## 学习来源及验证边界

| 原作者资料 | 实际读到的内容 | 本轮落地 / 尚未实现 |
| --- | --- | --- |
| ましまし：[msToonCoordinator v1.1](https://note.com/mashimashi_note/n/na1bc7c72e511) | 完整文字说明；将阴影、补光与边缘等信号分开，再由协调层控制颜色和区域 | 借鉴分层职责；没有在 Blender 运行其 MME，也没有照抄参数 |
| 同作者：[msToonCoordinator 2.1](https://note.com/mashimashi_note/n/n2c2144638054) | 完整文字说明；面部细节遮罩、法线/头骨权重的准备要求、阴影输入限制 | 保留为下一轮面部明暗研究依据。没有修改本模型法线，没有完成该着色器移植；其 Shade_Normal 路径不能直接与 ExcellentShadow 混称兼容方案 |
| SaraKale：[MMT_Subtitle_Editor 中文 README](https://github.com/SaraKale/MMT_Subtitle_Editor/blob/main/README_SC.md) | 原作者说明：时间指令、动画样式、图像输出及 MikuMikuTelop 工作流 | 学习时间段和 PNG 序列桥接方式；未安装/运行编辑器，未实现 `.mmt` 解析；本轮直接使用官方动态文字视频 |
| Psyop：[Cryptomatte 原始项目](https://github.com/Psyop/Cryptomatte)；[Blender 渲染通道](https://docs.blender.org/manual/en/latest/render/layers/passes.html) | 对象/材质标识与覆盖率遮罩的用途 | 在本机 Blender 5.2.2 EEVEE 实际生成 Object 和 Material 通道，完成两套各 240 帧合成；不是用 AI 从成片抠人 |

[msToonCoordinator 汉化介绍](https://www.bilibili.com/video/BV1Ep4y1b7Pn/)和[MMT 字幕编辑器介绍](https://www.bilibili.com/video/BV1U79CBMEb3/)保留为视频学习入口，本轮未声称完整观看。原作者链接中的旧中文文章有失效情况，不能将访问失败当成已读教程。MME 的 `.fx/.x` 不在 Blender 中原生执行；下载和读说明不等于插件兼容性通过。

观海子两支本地参考已实际抽帧，署名、画面证据和横竖屏差别见 [GUANHAIZI_REFERENCE.md](GUANHAIZI_REFERENCE.md)。

## 官方配布优先：已经有动态文字

[官方简介配布](https://larainc.link/Franken)实际指向 [Studio LaRa / HIMEHINA 的公开 Drive 目录](https://drive.google.com/drive/folders/1XQNzKCcTsYx7Dwu8Y9wM8pw-IMQ5ZpfW?usp=sharing)。本次核实 19 个文件，除动作 FBX/VMD、三份伴奏、歌词 PDF、动作说明外，还包括：

| 官方文件 | 本机实际信息 | 用途 |
| --- | --- | --- |
| `FrankensteinNoKaibutsu_Video_Full_Typography(Wide).mp4` | `E:\tools\franken`；1920×1080、60 fps、196.600 秒 | 横屏完整动态文字；已存在于用户素材目录 |
| `FrankensteinNoKaibutsu_Video_1Sabi_Typography(Tall).mp4` | 本轮从官方公开文件下载到 `D:\codex\output\blender-mmd-codex\franken-caption-assets-v001`；1080×1920、60 fps、30.067 秒 | 竖屏副歌专用排版；不是横版裁切 |
| `FrankensteinNoKaibutsu_Video_1Sabi_DanceBB-HMEHINA.mp4` | 官方目录中核实存在，未下载/导入 | 舞蹈参考素材；不能因此当作相机或骨骼数据 |

Tall 的[官方文件入口](https://drive.google.com/file/d/1JmTdMptFolttNt9EeKPpir7VN9T63o9l/view)。本次文件 SHA-256：Wide `9a2fe3ddf442e06103555731771c423314423dd1ad545a391663912930b0e724`；Tall `500c34e5140e53f8bf9939ed7f34fa14c726fd66afebfda81426307fd6adf9f3`。这是下载记录，不是作者独立发布的校验值。

素材来源署名 HIMEHINA / Studio LaRa；当前不把官方文字动画署为自己制作。动作说明不自动覆盖所有视频素材的授权条款，公开发布前按配布方当时的使用要求处理。参考观海子的画面不等于借用了其 PV Kit。

### 先核对时间轴，不能沿用动作文件偏移

初版错误地把 Tall 起点按动作 `[f1794] / 30 = 59.8 秒` 推断，字幕因而偏早约 11 秒。已修正。`align_typography.py` 将文字前景包围框归一化，比较横竖版字形；先 10 fps 粗搜，再在 48.7–48.9 秒用 60 fps 细搜。

本轮最佳 Tall→Wide 起点为 **48.783333 秒**，1212 个非空采样，余弦相似度中位数 0.94023。该分数是字形相似度，不是置信概率。最终对应帧对已检查：Wide 66.766667 / Tall 17.983333，68.766667 / 19.983333，70.750000 / 21.966667 秒呈现对应字形，原生布局仍不同。

本次四秒样片：横版从 Wide 66.766667 秒开始，竖版从 Tall 17.983333 秒开始。报告在官方素材目录的 `alignment-refined-report.json`；交付根目录有 `alignment-refined-frame-pairs.jpg`。这只验证两份文字视频的对应关系，**未完成原唱、人声、动作与伴奏的精确卡点**；伴奏按同一源时间估计切片，用户仍可自行调整。

## 横竖屏分别设计，字幕按段选层

竖版沿用前轮独立设计的 65 mm 表情/半身镜头；横版新增 50 mm、竖向传感器 24 mm 的两段镜头。第一段将角色放左侧，为右侧图形留空；第二段换三分之四角度及景别。均使用实际头部焦点、f/4，源帧 541 切镜。横版检查 240 帧头部投影，另以图像检查肩、手和文字关系；头部点在框内不等于全身构图合格。

样片实际输出为竖 540×960、横 960×540、60 fps、48 samples；项目保存为 50% 分辨率。它们没有冒充全高清成片。改成最终分辨率后需要重查线宽、文字保护边距和渲染结果，不能只改输出尺寸就视为验收通过。

`presets/typography/*.json` 的每段 cue 可选：

| `order` / `protect` | 表达 |
| --- | --- |
| `behind` / `character` | 字在整个人物后，人物轮廓挡字 |
| `front` / `face` | 字可盖衣服和手势，脸部留出可读区域 |
| `front` / `none` | 前景文字可以有意遮挡角色，包括脸；由当前内容决定 |
| `front` / `character` | 仍可把整个人物保护起来，供特殊布局使用 |

这次主样片的大字与重复字阵多放后面，小型强调字部分放前面；三种主要选择另有同一姿态的对照图。没有将“不遮挡”固化为硬约束。当前按段人工选择层级，不是人物一靠近文字就每帧自动跳层。

## 实际合成方式与限制

1. Blender 输出已完成 NPR/景深/局部泛光的 beauty，以及真实角色 Object Cryptomatte 和脸部 Material Cryptomatte。已有 425 刚体对应的烘焙动作保持，后台场景没有实时刚体世界。
2. Python 将官方黑底文字的 max-RGB 提取为覆盖率，按原生画幅缩放，做淡紫填充、细深紫边和少量泛光。黑底 MP4 不是原始 RGBA：白卡内黑字也会成为镂空，不能声称恢复了原始透明通道。
3. 将 sRGB 转线性后做预乘 alpha 合成，再转回 sRGB 编码。对整组文字、描边和泛光一起施加保护遮罩，避免边缘效果越过脸部遮罩。
4. 对象遮罩扩 3 像素、脸部遮罩扩 8 像素，阈值后作为硬保护区。它是本次样片的图形留边，可能有可见空隙；不是透明发丝、体积、景深边缘的精确三层重建。

脸部材质依据本模型的 `颜/眉/睫/目/白目/口/舌/齿/mmd_edge.颜` 筛选，换模型必须重新核实，不能靠名称猜出完整脸遮罩。本轮景深通道实际渲染通过；没有额外验证运动模糊、体积或复杂透明叠层场景。

Blender 5.2.2 本机接口：`scene.compositing_node_group`；`CompositorNodeCryptomatteV2` 的 `source='RENDER'`、`scene`、`layer_name='ViewLayer.CryptoObject'` / `CryptoMaterial`、`matte_id`。File Output 先设 `format.media_type='IMAGE'` 再设 `file_format='PNG'`，目录用 `directory`、文件名用 `file_name`、插口用 `file_output_items.new(...)`。旧版 `file_slots` 示例不能直接照搬。先 probe，再实际检查遮罩图，不能仅凭节点创建成功判断正确。

## 复现

在仓库根目录执行。以下目录必须是新目录；FFmpeg 使用已有运行时，不重复下载安装。

```powershell
$ffmpeg = 'D:\codex\temp\blender-mmd-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
$tall = 'D:\codex\output\blender-mmd-codex\franken-caption-assets-v001\FrankensteinNoKaibutsu_Video_1Sabi_Typography(Tall).mp4'
$wide = 'E:\tools\franken\FrankensteinNoKaibutsu_Video_Full_Typography(Wide).mp4'
python scripts/align_typography.py --full $wide --excerpt $tall --ffmpeg $ffmpeg --search-start 48.7 --search-end 48.9 --sample-fps 60 --output 'D:\codex\output\alignment-new.json'

& 'E:\tools\Blender Foundation\Blender 5.2\blender.exe' --background `
  'D:\codex\output\MMD-Tutorial-Study-v1\tutorial-study.blend' `
  --disable-autoexec --python-exit-code 1 --python scripts/mmd_caption_render.py -- `
  --aspect portrait --output-dir 'D:\codex\output\caption-portrait-new' `
  --cache-dir 'D:\codex\temp\caption-portrait-new'

python scripts/typography_composite.py --cache-dir 'D:\codex\temp\caption-portrait-new' `
  --typography $tall --profile presets/typography/portrait-study.json --ffmpeg $ffmpeg `
  --output-dir 'D:\codex\output\caption-portrait-composite-new'
```

横屏另行渲染 `--aspect landscape`，合成改用 `$wide` 和 `landscape-study.json`，不要复用竖屏 beauty/遮罩去裁切。只改文字或前后层时可复用已缓存的 PNG，不必重新渲染人物。

`typography-source.blend` 保存相机、人物和遮罩输出，但**字幕在第二阶段 Python 合成**，直接打开 Blend 渲染不会自动得到最终字幕。文件节点目前仍指向报告内的本机临时缓存；不要直接覆盖已有序列，重渲染时改为新的输出路径。交付副本保留 profile、渲染/合成/视频/音频报告；大型逐帧缓存位于 `D:\codex\temp`，没有复制进 Git 或交付包。

音频合成使用 `mux_production_audio.py --audio-start 66.7666666667 --seconds 4 --gain 0.75`；音频源为本地官方 `Inst±0.wav`，这不是人声原唱。`verify_video.py` 支持 `--width/--height/--fps/--seconds`；`verify_audio_blender.py` 新增 `--seconds 4`，默认仍为旧成片的 20 秒。

## 验收结果

- 两版实际完整解码各 240 帧，60 fps、4.0 秒，MP4 含视频和音频轨，无全黑帧或连续静止帧；音轨实际解码为双声道 48 kHz，RMS 约 0.192，峰值约 0.753。
- 两套合成逐帧检查保护区域，线性浮点合成前后最大差为 0；这是编码前检查，不代表有损 H.264 编码后像素严格一致。前景字幕确实改变了衣服区域，保护脸部不等于保护整个人物。
- 28 项单元测试通过，包含前/后层、允许遮挡、保护脸但允许盖衣服、非法 cue 拒绝；编译与 `git diff --check` 通过。实际渲染和视频解码另行完成，不用单测代替美术验收。

竖版带声视频 SHA-256：`914611899c1b0668344572cece8b244f731e7e65b63b4128506557c6687a20c1`；横版：`ac8111cdc9f491dc5640062953a7b911494bc4f3f314cd1c46ecf53d98cbca96`。

本轮验证了字幕分层、独立画幅镜头和官方素材复用，尚未完成新的二十秒版本、逐词卡点、完整歌曲分镜、msToonCoordinator 式面部法线/阴影方案或与参考同水平的整体材质重制。已有正式成片状态仍以 [FINAL_DELIVERY.md](FINAL_DELIVERY.md) 为准。
