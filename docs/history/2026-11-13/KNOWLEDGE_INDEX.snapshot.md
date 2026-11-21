# 知识、预设与制作入口

新增 [人物自阴影、描边与播放器色彩](SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md)：人物投影、脚底接触和卡渲真实受光分开调；后续追加刘海／身体自身投影及分区加厚黑线，脸部平整受光法线与SDF组合，最终 `production-v3`／`captions-5s-v2`。修正旧MP4的未知色彩标签，核对实际编码／混音后的矩阵、曲线、电平。入口 `MMD-Duet-Shadow-Color-v1`，五秒状态以交付JSON为准，旧版保留；PotPlayer具体设置尚未确定。

最新 [蓝金婚礼](BLUE_GOLD_WEDDING_STUDY.md)：三点布光职责、人物后方蓝金局部散射、分开的场景／人物光晕、走道微光和官方字幕主题色。只做原段五秒；人物前后层和准确字幕边界保持，不能因加柔光重新启用脸部挖字。

猪猪指出聚焦舞台过暗，最新分支为 [柔光、顶光与逆光](SOFT_TOP_RIM_LIGHTING.md)：使用真实大尺寸面光和重烘 GI 提亮场景，人物 NPR 补充边缘与真实灯光明确区分，字幕沿用固定分组。交付 `MMD-Duet-Soft-Top-Rim-v1`，最终 `production-v2`，只做同段五秒，等待美术评价。

最新 [官方动效字幕与聚焦灯光](DUET_CAPTION_STABILITY_AND_LIGHTING.md)：整组固定前后层、保留牌面黑字、PNG16 连续人物遮罩；完整教程音频自动转写与关键画面核对后，使用响应灯光的礼堂材质、局部冷暖与明暗光区。五秒横屏样片为独立研究，仍待猪猪美术评价；全曲与竖屏未扩展。

继续学习见 [小狐狸舞台再研究](FOX_STAGE_ART_DEEP_STUDY.md)：增加跨数秒连续采样、真实地面区域与投影、专属亮边 AOV、脸部面片排除、后方局部空气，并完成独立五秒样片。网站「入光 · 舞台光影再研究」可看四组对照；未获用户美术认可，不替换已认可基线。

新增 [小狐狸灯光与镜头](FOX_LIGHTING_AND_CINEMA.md)：在修好空间的双人工程上实际整合雪夜冷暖、双人对焦与原生运动模糊，五秒视频通过。与先前仅恢复灯位的技术修订区分；预设「夜誓 · 灯光与镜头」等待猪猪评价。

新增 [受光、动态稳定与线性合成](LIGHT_SPACE_AND_COLOR_PIPELINE.md)：已完成本轮五秒技术修订与原生分层／归档，旧用户认可版本仍保留。请优先阅读该文中的最终工程与适用范围。

2026-11-11 整理。最新入口是“帧间”静态资料库：`D:\codex\output\MMD-Atlas-v1\index.html`。双击即可离线浏览真实预览、样片、对照、全部笔记和 JSON。源码在 `site/`，资料目录在 `catalog/library.json`，更新方法见 [资料库维护](GALLERY_GUIDE.md)。

## 当前状态

猪猪已认可的近期基线为双人明亮礼堂五秒样片，工程为 `D:\codex\output\MMD-Ray-Hall-Genshin-Revision-v1\production-v3`。舞台夜景和鸣潮发丝是之后的独立研究，未替换该版本。双人全曲尚未交付；本轮只整理知识与网站，不开启长片渲染。

旧文档中的“当前”“最新”“待完成”指其写作日期。保留实验历史，使用时先看本入口、网站条目的验收范围，再查对应方法。风格方向不表示原作者原始参数或同等质量。

## 分类地图

| 类别 | 主要内容 | 入口 |
| --- | --- | --- |
| 人物与着色 | 原神 SDF、鸣潮研究、半兰伯特、分区材质、眼睛、发丝和黑线 | [原神与预设](GENSHIN_CHARACTER_AND_PRESETS.md)、[鸣潮研究](WUWA_TOON_STUDY.md)、[表面材质](SURFACE_REFINEMENT.md)、[脸线](FACE_INK_REFINEMENT.md) |
| 舞台与灯光 | 明亮礼堂、ToonBased／MatCap、夜景冷暖、体积与反射 | [夜景学习](STAGE_ART_NIGHT_STUDY.md)、[礼堂材质重建](HESPERIDES_REFERENCE_REBUILD.md)、[去灰与打光](CLEAR_LIGHT_AND_GRADING.md) |
| 后期与字幕 | 多风格 render／post、遮罩、图形、文字前后层与横竖布局 | [风格套装](STYLE_PRESETS.md)、[字幕与合成](ADVANCED_MMD_SUBTITLES.md) |
| 动作与成片 | PMX／VMD、物理、镜头、双人、原声转换和最终验收 | [制作流程](PRODUCTION_WORKFLOW.md)、[制作技术](PRODUCTION_TECHNIQUES.md)、[双人项目](DUET_FULL_PRODUCTION.md)、[音频](AUDIO_CONVERSION.md) |
| 参考与审美 | 实际观察的 Gosari542、观海子与教程证据 | [Gosari542](GOSARI_REFERENCE.md)、[观海子](GUANHAIZI_REFERENCE.md)、[教程研究](TUTORIAL_STUDY.md) |
| 工具与环境 | 已安装／启用／导入／渲染的不同状态，ASR／OCR | [本机环境](LOCAL_ENVIRONMENT.md)、[教程转写](TUTORIAL_TRANSCRIPTION.md) |
| 署名与素材 | 原曲、模型、动作、相机、舞台和效果来源 | [双人署名](CREDITS_FRANKEN_DUET.md)、[原有署名](CREDITS.md) |

完整文档的唯一分类保存在 `catalog/library.json` 的 `knowledge_groups`。未手工归类的新文档在构建时进入“目录与维护”，不会因漏填目录而从网站消失。原文件保留稳定路径，已有复现脚本和文档链接继续使用。

## 预设分层

```text
catalog/library.json      人看得懂的条目、状态、来源、预览、关联文档
presets/
  styles/render/          人物 NPR、色带、灯光响应和描边
  styles/post/            调色、背景图形、光点和字幕外观
  styles/packages/        风格 × 变体 × 画幅的组合
  typography/            横／竖字幕 cue、层级与保护范围
  stages/                场景灯光与材质参数
  quality/               绑定特定模型或工程的效果实验
  recipes/               当前工程配方、受控研究配方；不是万能转换器
  projects/              角色／动作／原声／画幅等制作项目配置
site/                    离线网站源文件与设计规则
scripts/build_gallery.py 将真实预览、视频、文档、JSON 构建到交付目录
```

这轮新增两份配方：`genshin-duet-hall-v3` 对应当前双人基线，`wuwa-hair-lab-v1` 对应发丝静帧研究。它们记录依赖与状态，没有冒充新的材质算法；底层参数继续引用已有文件。

## 状态怎么读

- **样片通过**：有现存且已按原记录检查的短片。不是任意模型都可用，也不是双人全曲已验收。
- **静帧实验**：实际渲染和观察过静帧；动态稳定性仍需验证。
- **研究待适配**：读过资料或在专用示例测试；尚未适配当前双人角色。
- **当前基线**：用户近期认可的具体版本，额外标记，不随研究项自动变化。

预设、参数组件、工程配方与知识笔记各司其职。把一篇教程归档不等于已实现；把两个可用模块组合也不等于新组合通过。

## 最值得继续加强的能力

1. **人物与舞台的受光关系**：现有部分 Emission／NPR 色池不产生真实遮挡。优先解决下巴与领口、手指与掌面、鞋底与地面的可控接触层次，避免靠整图压暗或 AO 变脏。
2. **动态稳定性**：转头、移灯、绕拍分别验收 SDF、发丝亮带、眼睛／刘海和描边；再检查双人交叠。静帧好看不能替代这些检查。
3. **分层与颜色流程**：逐步验证人物／舞台／线条的独立输出、浮点中间格式与预乘 Alpha，明确显示变换顺序，再进行合成和调色。
4. **复现与适配**：给预设写清模型、通道、版本、输入工程、画幅和小样验收条件，形成固定测试片段，减少每次从临时脚本猜状态。
5. **个人美术语言**：围绕雪、婚礼、爱和释然，选择有目的的冷暖、节奏与视觉落点。保留参考风格，个人方案另开版本。

上述为改进方向，不是本轮新增验证的渲染能力。网站“下一步提升”提供当前依据和验收条件。
