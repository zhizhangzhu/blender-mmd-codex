# 知识、预设与制作入口

## 当前导航

- [参考到作品闭环](STUDIO_ITERATION.md)与[Goo礼堂实践](GOO_DUET_ARTDIRECTION_2026_11_20.md)：先冻结预测、实际对照、逐假设评审，再带范围检索经验；包括改善不足的真实反例。

- **具体任务先查[AI制作导航](AI_TASK_PLAYBOOK.md)／[机器路线](../catalog/task_routes.json)**，再读对应主手册和案例；下面按日期的研究不是推荐执行顺序。
- [设计基础与美术评审](DESIGN_FOUNDATIONS_AND_REVIEW.md)：焦点、明暗/色彩、构图/空间、动作表演和特效克制；官方资料实际阅读范围另记账本。
- [动作数据与局部K帧](ANIMATION_AND_KEYFRAMING_PLAYBOOK.md)：先排绑定/求值问题，再选择IK、接触、局部修形或K帧；保留原动作和证据边界。

- [八项基础官方指南首轮学习](GOO_MMD_EIGHT_FOUNDATIONS_2026_11_18.md)：25篇Blender正文、MMR作者图文与本机插件源码；真实网格Normal Edit已在Goo生效，另验数据共享与修改器顺序；未改人物。

- [Goo与Blender官方基础增量](GOO_BLENDER_FOUNDATIONS_2026_11_18.md)：新增Blender法线／灯影／色彩管理实读；Goo双版本输入对照及重开，五张显示转换控制图，未改人物。

- [新近景参考与Normal基础验证](GOO_REFERENCE_FACE_HAIR_STUDY_2026_11_17.md)：将三张参考拆为脸／发／眼／线／材质目标；当前5.2社区版Half-Lambert对Normal连接未响应，五项基础控制与独立重开已验证，未改人物。

- [Goo基础功能与参数](GOO_FOUNDATIONS_AND_PARAMETERS.md)：用户最新选择，先基础再高阶；官方4.4发布分支对照本机5.2，13节点参数清单与单主光灯组新实验。下列原生MMD路线暂缓。

- [MMD MME与Goo分工方案](MMD_MME_GOO_WORKFLOW.md)：原生主渲、Goo资产加工、跨引擎合成的选择与交接条件。
- [MME原生预设实验](MME_NATIVE_LEARNING_LAB.md)：按主shader、RT、轮廓、扩散逐项学习，N00–N06尚未运行。
- [仓库导航](REPOSITORY_GUIDE.md)／[全文件索引](REPOSITORY_FILE_INDEX.md)／[整理记录](REPOSITORY_ORGANIZATION_2026_11_17.md)：当前入口与历史路径分开。

## 近期实验与历史记录

2026-11-17：[新借物表与MME式蓝白光影静帧](MME_REFERENCE_LIGHT_STILLS_2026_11_17.md)。实际复读PowerShader、Diffusion和msTC原包段落；v3被反馈伊科尔过亮、阿克西妮娅变化小，v5仍偏亮后，最新v6进一步单独收敛伊科尔表面辐射，保留阿克西妮娅v3，并提供同机位裁切对照；仅静帧、美术待评。

2026-11-17：[茜特拉莉参考的暖色刘海投影](CITLALI_WARM_FRINGE_SHADOW_STUDY.md)。复用本地视频8秒核图，尝试逐像素、窄方向采样的暖橙影边；保留修复后的头发。猪猪最新要求：后续默认只看静帧，明确要求时才做视频。

2026-11-17：[伊科尔头发错位静帧修复](IKHOR_HAIR_ALIGNMENT_STILL_REPAIR.md)。猪猪要求只看静帧；隔离错误发骨烘焙，恢复原绑定发型，重算4290面部发影。未重新验证头发物理或输出视频，不用旧五秒代替修复结果。

2026-11-17：[崩铁参考的明亮肤色与发影](STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md)。实际阅读民间StarRailNPRShader和Nilo公开源码，区分SDF、头发深度、色带、高光与Emission；本地以不透明头发、冷暖色带及双人300帧几何刘海投影近似，眼透已搁置。新样片状态看current_state，不把v4被指出的问题写成达标。

2026-11-16：[果冻眼、眼高光、局部眼透、原生发影与舞台材质](JELLY_EYE_HAIR_STAGE_IMPLEMENTATION.md)。本地1.3.6插件已在普通／Goo5.2完成注册、烘焙与独立重开；原生GN接入两人独立眼区。新制作与五秒输出状态看current_state，第三方源代码仅私人缓存。

2026-11-16：[衣发阴影、顶光对照与字幕样式记录](HAIR_SHADOW_TOPLIGHT_AND_BORDERLESS_CAPTIONS.md)。四张同帧诊断区分表面高光与Bloom；顶光未整合。曾制作去黑边对照，猪猪后续要求保留黑边框和投影，当前预设与样片已恢复原有边框版。

2026-11-16 后续美术修订：[大窗宽幅日光与强衣发轮廓](GOO_BROAD_WINDOW_AND_STRONG_RIM.md)。用户明确否定旧两束细锥；新链按真实窗面尺度布光，并加强rim宽度、专用辉光与发带。输出状态看current_state，不能继续把旧光柱版视为已获认可。

2026-11-16 参考补充后的制作：[白蓝轮廓光、窗向体积、高亮泛光与固定Reinhard肩部](GOO_TYNDALL_RIM_PRODUCTION.md)。温和中间视频已停止；最终工程为 Tyndall 根 production-v7，视频完成与否看 current_state/delivery.json。

2026-11-16 制作增量：[Goo 人物亮边、高光与场景泛光加强](GOO_RIM_GLOW_REVISION.md)。固定 Goo daylight v2 输入、独立副本、4140／4290 制作对照；五秒输出状态看 current_state，不重复使用旧版视频。

2026-11-16 后续学习：[Goo 相对 Blender 的节点机制与 MME 深读](GOO_FEATURES_AND_MME_MECHANISMS.md)。三运行时清单、13 类增量节点、28 张独立机制图；补读五个 BeamMan 原包、HAToon HLSL 与 msTC 影边。研究没有改生产工程／视频，节点存在、源码阅读、静态实测和生产可用分开记录。

2026-11-16 增量：[MME 原包卡渲与灯光学习](MME_TO_GOO_LIGHTING_STUDY.md)。已取得 9 个原包并读重点说明/源码，区别配色、形体阴影、真实遮挡、后期点光与边缘光；Goo v2 新窗格光带和全身落地影制作图已实渲。新视频是否完成看 current_state；不把索引49位作者等同全部效果深入掌握。

2026-11-14更新当前完整交付。现行任务和最新美术反馈只保存在`catalog/current_state.json`，制作关卡在`catalog/production_pipeline.json`。目标是原神／鸣潮式高质量三渲二，观海子为首要参考，保留Gosari542。[阿克西妮娅＋伊科尔Clean五秒](CLEAN_GAME_CHARACTER_REFINEMENT.md)已全新渲染300帧、完成两版技术与限定人工验收，仍有参考差距、美术未获猪猪认可；前版[婚礼修袖／双人字幕基线](IKHOR_BOLD_WEDDING_PRODUCTION.md)保留历史。

2026-11-15静帧增量：[暗场婚礼重新布光实现](PORTRAIT_RELIGHT_IMPLEMENTATION.md)，包括实际4K图、新工程、材质分支、主灯头轴、脸影形体、窄暖边和独立重开证据。仅静帧，新动态与用户美术评价分开；下述Clean仍是最新完整五秒。

## 建议阅读顺序

2026-11-16当前入口：[Goo迁移与原生节点实测](GOO_ENGINE_MIGRATION.md)。已移植独立工程、核对动作与相机、实际测试插件与Half Lambert/投影/光组；Goo4.3无法读5.2，采用公开5.2.1社区移植版。最新成片状态仍看current_state。

1. [制作流程](PRODUCTION_WORKFLOW.md)：确定输入、范围和执行顺序。
2. [质量关卡](QUALITY_GATES.md)：确定这一轮怎样才算有进步。
3. [人物手册](CHARACTER_NPR_PLAYBOOK.md)：角色颜色、法线、SDF、几何遮挡、材质高光、Emission和线条。
4. [物理手册](PHYSICS_MOTION_PLAYBOOK.md)：衣发、服装和身体次级运动；[伊科尔袖口案例](IKHOR_SLEEVE_REPAIR.md)记录实际穿模定位与连续检查，[官方变形资料复习](LOCAL_CORRECTIVE_SHAPES.md)区分形态键、蒙皮、纠正平滑和刚体的适用边界。
5. [参考与舞台学习](REFERENCE_AND_LIGHTING_PLAYBOOK.md)：参考证据、布光、镜头和教程学习方法。
6. [工具与预设地图](TOOL_AND_PRESET_MAP.md)：哪些能复用、哪些只是一次性迁移或历史归档。
7. [仓库复审](REPOSITORY_REVIEW_2026_11.md)：历史状态冲突、现有证据与后续优先级。

离线资料库 `D:\codex\output\MMD-Atlas-v1\index.html` 可看真实预览、样片、对照、参数和所有顶层笔记。源码 `site/`，维护方法见 [GALLERY_GUIDE](GALLERY_GUIDE.md)。

## 当前制作与能力边界

最新完整工程为`D:\codex\output\MMD-Clean-Game-Characters-v1\production-v2\Franken_Duet_Clean_Game.blend`，同根`captions-5s`已输出`Franken_Duet_5s_CleanGame_Wedding_REVIEW.mp4`与`Franken_Duet_5s_CleanGame_NoCaptions.mp4`：原帧4140–4439、300帧、1080p60、五秒，人物阿克西妮娅＋伊科尔。两版全新beauty／actor、全解码／音轨／色彩／各自接缝、1200个双人头身内部ROI与指定FLAC独立PCM比对均通过。人工查看两版各12时点、32帧字幕边界连续图和7张原生腕部关键全图（另有4140／4290早期抽看），见同根`delivery.json`与`manual-review.json`；不是人工逐帧审完、零交叉或用户美术认可。

本次按两份本地参考做palette／response_ramp／highlight_metal／rim四模块，阿克西妮娅鼻区同图SDF邻采样、伊科尔浅粉肤／奶金／高光余量白布有同帧对照；两条蓝／黄细光弧隐藏。独立321项材质静态＋26项去弧增量与新72帧三轴技术通过，每组6时点双人脸图已实际查看；完整新300帧成片已完成，没有复用旧婚礼beauty。中央雾光／青亮边、深蓝衣层次及双人主次仍有差距，不宣称参考Shader还原或游戏质量。

当前方向化Diffuse综合受光对准实际主灯，身体几何形体与阿克西妮娅已有SDF另行控制；伊科尔没有已验证的脸部SDF，它仍非纯阴影可见度。前版[外部技术移植](REFERENCE_TECHNIQUE_TRANSFER.md)、[人物分层](CHARACTER_LAYER_REFINEMENT.md)及随头部前向的探针实现按原版本追溯。伊科尔袖／衣发证据仅4139–4441，Clean保留几何与Actions继承有界证据，未新模拟或认证零交叉。全曲未交付，不自动恢复；历史胸部适用性不能升级为新增胸部模拟通过；完整鸣潮人物、Goo生产适配仍未验证。

状态分别看：读过资料／本地存在／进程注册／导入通过／静帧实验／限定动态通过／整合通过／用户美术认可。不能把这些合并为一个“掌握”或“已完成”。同模型五秒通过也不等于换角色、全曲或竖屏通过。

## 按问题查原始实验

| 问题 | 综合指导 | 原始记录与已知限制 |
| --- | --- | --- |
| 当前Clean完整五秒 | [Clean材质修订](CLEAN_GAME_CHARACTER_REFINEMENT.md) | 两份本地参考、四模块／鼻区／白布高光余量、321＋26静态边界、72帧诊断、新beauty／actor300与两版交付；保留参考差距及抽样限制 |
| 前版伊科尔婚礼基线 | [婚礼制作记录](IKHOR_BOLD_WEDDING_PRODUCTION.md) | 原生Hina动作、修袖v6、字幕名单v7、旧actor300与captions-v3两版；[袖口案例](IKHOR_SLEEVE_REPAIR.md)保留非零接触限制 |
| 前版技术移植 | [外部技术移植](REFERENCE_TECHNIQUE_TRANSFER.md) | Nilo／Ray-MMD／Filament部分原则的本地适配、原production-v3五秒及其2488项／六种消融；人物含空，保留历史 |
| 脸、眼睛、受光与材质 | [人物手册](CHARACTER_NPR_PLAYBOOK.md) | [原神与下载预设](GENSHIN_CHARACTER_AND_PRESETS.md)、[空的修订](AETHER_LOOK_REVISION.md)、[保色NPR](LOOK_REFINEMENT.md)、[半兰伯特](HALF_LAMBERT_STUDY.md) |
| 发束、材质与黑线 | [人物手册](CHARACTER_NPR_PLAYBOOK.md) | [表面精修](SURFACE_REFINEMENT.md)、[脸线](FACE_INK_REFINEMENT.md)、[鸣潮研究](WUWA_TOON_STUDY.md)、[进阶实验](QUALITY_LIGHTING_LAB.md) |
| 自阴影、AOV与颜色 | [质量关卡](QUALITY_GATES.md) | [自身阴影／色彩](SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md)、[受光与线性合成](LIGHT_SPACE_AND_COLOR_PIPELINE.md)、[去灰](CLEAR_LIGHT_AND_GRADING.md) |
| 舞台与光照 | [参考与灯光](REFERENCE_AND_LIGHTING_PLAYBOOK.md) | [夜景](STAGE_ART_NIGHT_STUDY.md)、[小狐狸镜头](FOX_LIGHTING_AND_CINEMA.md)、[舞台再研究](FOX_STAGE_ART_DEEP_STUDY.md)、[柔光](SOFT_TOP_RIM_LIGHTING.md)、[蓝金婚礼](BLUE_GOLD_WEDDING_STUDY.md) |
| 场景来源与材质 | [制作流程](PRODUCTION_WORKFLOW.md) | [选景](STAGE_SEARCH.md)、[作者配布](HESPERIDES_AUTHOR_SETUP.md)、[礼堂研究](HESPERIDES_STAGE_RENDERING.md)、[预览重建](HESPERIDES_REFERENCE_REBUILD.md) |
| 物理、动作和镜头 | [物理手册](PHYSICS_MOTION_PLAYBOOK.md) | [制作技术历史实例](PRODUCTION_TECHNIQUES.md)、[双人项目](DUET_FULL_PRODUCTION.md)、[相机搜索](CAMERA_SEARCH.md) |
| 字幕、后期和画幅 | [参考与灯光](REFERENCE_AND_LIGHTING_PLAYBOOK.md) | [组合预设](STYLE_PRESETS.md)、[进阶字幕](ADVANCED_MMD_SUBTITLES.md)、[整组字幕与灯光](DUET_CAPTION_STABILITY_AND_LIGHTING.md)、[字幕交付](SUBTITLE_DELIVERY.md) |
| 作者与教程 | [参考学习方法](REFERENCE_AND_LIGHTING_PLAYBOOK.md) | [Gosari](GOSARI_REFERENCE.md)、[观海子](GUANHAIZI_REFERENCE.md)、[教程研究](TUTORIAL_STUDY.md)、[ASR/OCR](TUTORIAL_TRANSCRIPTION.md) |
| 环境、音乐、署名 | [工具地图](TOOL_AND_PRESET_MAP.md) | [本机环境](LOCAL_ENVIRONMENT.md)、[音乐转换](AUDIO_CONVERSION.md)、[阿克西妮娅／伊科尔署名](CREDITS_AKSINIYA_IKHOR.md)；[原双人署名](CREDITS_FRANKEN_DUET.md)与[原署名](CREDITS.md)保留历史 |

## 文件职责

`catalog/current_state.json`管现行事实，`production_pipeline.json`管关卡，`library.json`管展示与分类。`presets/styles/render`、`post`、`packages`分别管角色风格、后期和风格×画幅；`quality`是绑定输入的实验，`recipes`是整合配方，`stages`与`typography`独立。组件存在不等于新组合验证通过。

`docs/research`保存来源账本与审计JSON。完整第三方视频、字幕、预设和私人参考帧不提交仓库。`docs/history/2026-11-13`保留整理前入口快照，历史具体实验继续保留原路径。全体脚本的整理前盘点见 [审计](REPOSITORY_REVIEW_2026_11.md)，脚本按职责登记而不是批量搬目录。

## 当前修订与后续学习

最新优先学习为[明亮人像与暗场层次](PORTRAIT_LIGHTING_AND_SHADOW_STUDY.md)：摄影主辅／分区／冷暖、白菜字幕与实际UI、paierer亮边与深线、脸影新资料，以及Node Wrangler本机状态。三张4290同帧消融已有实际观察，用户要求的明亮人物及观海子风格尚未达标；当前成片保留Clean供回退，美术为revision_requested。协议位于`presets/lighting/portrait-layer-study-v1.json`，不是通用人物光配方。

当前[Clean同段五秒](CLEAN_GAME_CHARACTER_REFINEMENT.md)已完成；后续以猪猪实际评价决定改进方向，不自动恢复全曲。[男参考](research/IKHOR_PRINCE_REFERENCE_2026_11_14.json)与[女参考](research/FEMALE_CLEAN_NPR_REFERENCE_2026_11_14.json)各实际观察4清晰帧，未完整连续看，Shader未知；研究账本保留当时“观察／建议未实施”的时间边界，之后的实现与测试写在制作记录，不改成作者已公开原参数。本次以完整新300帧、音视频／字幕及明确人工范围作为交付依据，不由工程文件存在或渲染启动自动升级。

猪猪强调持续学习以实际外部技术阅读为主。[Nilo人物阴影、Ray-MMD环境／材质、Filament反射与衣料实读](EXTERNAL_MMD_TECHNIQUES_2026_11_13.md)保留当时未改生产工程的研究边界；后续部分原则已在[本轮移植](REFERENCE_TECHNIQUE_TRANSFER.md)实测，不代表全部技术已实现。后续继续读有增量的教程，资料维护收尾即可。

持续学习先读[执行方法与首批队列](CONTINUOUS_LEARNING_SYSTEM.md)：9个文字来源、5个待验证假设；`python -m scripts.learning_queue plan`给出下一步。来源去重、阶段证据与失败原因统一维护，原始研究账本继续留存。文字阅读未自动升级为已实现能力。

续读已新增[发带算子与暗部策略](NPR_PRIMARY_STUDY_2026_11_13.md)、[脸影局部设计](FACE_SHADOW_DESIGN_STUDY.md)、[材质贡献消融](MATERIAL_RESPONSE_STUDY.md)及[作者证据矩阵](AUTHOR_REFERENCE_MATRIX.md)。这些均是研究，未改生产工程。文字获取与缓存见[字幕工具](BILIBILI_SUBTITLE_WORKFLOW.md)、[高效流程](EFFICIENT_RESEARCH_WORKFLOW.md)，本轮验证范围见[学习汇总](LEARNING_ROUND_2026_11_13.md)。

此前[外部技术移植五秒](REFERENCE_TECHNIQUE_TRANSFER.md)、[人物分层](CHARACTER_LAYER_REFINEMENT.md)、[独立审计](CHARACTER_LAYER_AUDIT.md)、[胸部适用性](CHEST_SECONDARY_MOTION_VALIDATION.md)保留原始范围；当前已交付基线及其后继修订以上方入口为准。后续以用户看过新片的意见为先；[三个有界实验](NPR_NEXT_EXPERIMENTS.md)仍是各自未验证的研究方案，不因某次局部实现整体升级，也不自动改当前工程。

这是有具体输入和验收的制作顺序；新文档并不表示新增效果已经实装。旧的 [NEXT_QUALITY_REVIEW](NEXT_QUALITY_REVIEW.md) 是当时八秒脸线版的优先级，现行顺序以本页、人物手册和状态表为准。

2026-11-18：[Goo双人人物有界静帧优化](GOO_CHARACTER_LOOKDEV_2026_11_18.md)。`inspect_character_lookdev.py`检查、`refine_goo_character_lookdev.py`固定源试验、`finalize_goo_character_lookdev.py`固定 production-v6／trial-v3 输入及SHA，模式为 preflight／prepare／repair-controls／reopen／repeat-reopen；仅本轮4290静帧，不是通用安装器。

- [脸影设计研究](FACE_SHADOW_DESIGN_STUDY_2026_11_18.md)：3新来源族10文件，解析SDF／图像阈值／头部空间，未用于阿克或伊科尔；状态 `research-read-and-bounded-static-tested-not-integrated`。
- [Blender5.3作者卡渲包研究](BLENDER53_TOON_PACKAGE_STUDY_2026_11_18.md)：5.3官方5页、作者视频7帧、原生53与Goo52 v2只读审计、2张SDF控制；Goo22未定义并有同名LightInfo丢链接，不能直接兼容；状态 `research-read-and-bounded-static-tested-not-integrated`。

- [Goo双人SDF静帧实施](GOO_DUET_SDF_IMPLEMENTATION_2026_11_19.md)：两人4290有界静帧，SourceDOF正式图及有限重开通过，用户美术待评；无新视频或物理，旧无DOF仅诊断。
