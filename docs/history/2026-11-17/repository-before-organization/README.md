# blender-mmd-codex

猪猪的高质量MMD制作与知识仓库。目标是逐步达到原神／鸣潮风格游戏级三渲二的感知质量，参考 Gosari542 与观海子，并形成可复用的材质、物理、导演和验收流程。

2026-11-17最新人物修订：[崩铁参考的亮肤与发影学习／实现](docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md)。眼透已按猪猪要求搁置，刘海恢复不透明；独立制作冷暖发束色带、亮肤暖鼻影，以及双人300帧实际发片遮挡序列，保留果冻眼、眼部高光、强轮廓泛光、舞台材质和黑边字幕。当前工程及五秒视频是否已编码看`catalog/current_state.json`，美术尚待猪猪评价；下文旧日期交付均保留作历史。

2026-11-16制作入口已按猪猪要求迁移至 **Goo 5.2.1社区移植版**：[迁移、插件与原生节点实测](docs/GOO_ENGINE_MIGRATION.md)，[运行配置](presets/runtime/goo-v1.json)。原Blender工程保留；最新样片以 `catalog/current_state.json` 为准。下文旧版本的“最新”按对应日期理解。

**当前尚未达到该目标。** 阿克西妮娅＋伊科尔的Clean五秒已完整输出：两人材质按本地参考精修、身后蓝／黄细光弧移除，固定production-v2完整新渲染300帧，两版音视频／字幕及限定人工抽样验收完成。中央雾光、青亮边与双人明暗主次仍有参考差距，美术未获猪猪认可。旧版认可、插件安装和视频解码通过，都不等于最新美术达标。

最新静帧实现：[暗场婚礼重新布光](docs/PORTRAIT_RELIGHT_IMPLEMENTATION.md)。已把白菜教程、paierer本地参考及逐层布光知识接入独立工程，输出4290帧4K静帧：减少灰雾、重标脸部形体、分区暖边、毛领与金饰高光，并压低礼堂中高亮。人物仍有参考差距，待猪猪评价；本轮只做静帧，最新完整五秒仍是Clean。

## 从哪里开始

- [制作总流程](docs/PRODUCTION_WORKFLOW.md)：从素材到人物、物理、舞台与成片的执行顺序。
- [当前Clean五秒](docs/CLEAN_GAME_CHARACTER_REFINEMENT.md)：两份本地参考、四个可旁路模块、去光弧与完整交付的验收范围。
- [前版婚礼基线](docs/IKHOR_BOLD_WEDDING_PRODUCTION.md)：伊科尔替换、袖修复、双人字幕与历史版本追溯。
- [知识地图](docs/KNOWLEDGE_INDEX.md)：按制作问题查阅全部经验。
- [持续学习与队列](docs/CONTINUOUS_LEARNING_SYSTEM.md)：图文／官方资料优先，来源去重，按证据推进小实验。
- [人物三渲二手册](docs/CHARACTER_NPR_PLAYBOOK.md)：脸眼、发丝、材质、法线、自阴影、Emission与描边。
- [物理与自然动态](docs/PHYSICS_MOTION_PLAYBOOK.md)：衣发、披肩、胸部等次级运动的不同处理与验收。
- [参考、舞台与学习方法](docs/REFERENCE_AND_LIGHTING_PLAYBOOK.md)：两位作者的实际画面观察、灯光设计和教程学习闭环。
- [质量关卡](docs/QUALITY_GATES.md)：明确如何通过小样验证，何时扩展到长片。
- [本轮仓库复审](docs/REPOSITORY_REVIEW_2026_11.md)：现有能力、历史冲突和仍未验证的项目。

离线预设库：`D:\codex\output\MMD-Atlas-v1\index.html`。支持真实样片、效果对照、参数下载和笔记阅读；“技术样片”和美术评价分开显示。

## 当前制作事实

唯一现行状态表：[catalog/current_state.json](catalog/current_state.json)。版本化关卡：[catalog/production_pipeline.json](catalog/production_pipeline.json)。不要从历史文档的“最新／正在渲染”恢复旧任务。

2026-11-16：后续制作已切到 Goo 5.2.1 社区移植版；最新快速审片与技术验收过的历史 Clean 五秒分开记录。[本轮 MME 原包与灯光研究](docs/MME_TO_GOO_LIGHTING_STUDY.md)包含 PowerShader、PAToon、tn_PostPointLight、wDark、两类 Rim 等的实际阅读范围及 Goo v2 参数。

| 内容 | 当前状态 |
| --- | --- |
| 最新完整五秒 | `D:/codex/output/MMD-Clean-Game-Characters-v1/production-v2/Franken_Duet_Clean_Game.blend`；两版在同根`captions-5s`；原帧4140–4439、1080p60、300帧、五秒；见[Clean制作记录](docs/CLEAN_GAME_CHARACTER_REFINEMENT.md) |
| 历史修袖／字幕基线 | `D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/production-v7/Franken_Aksiniya_Ikhor_Bold_Wedding.blend`与`captions-5s-v3`；保留输入与对照，新材质未复用其beauty |
| 历史认可方向 | `genshin-duet-hall-v3` 明亮礼堂，保留作回退与对照 |
| 双人全曲 | 未交付，旧全曲渲染已停止；本轮只完成同段五秒，不自动恢复全曲 |
| 人物与动作 | 阿克西妮娅→Full HimeTanaka；伊科尔→Full HinaSuzuki；16:9；现成相机VMD；空仅保留历史记录 |
| 场景与音乐 | 指定赫斯珀利德斯之馆-礼堂；指定原声FLAC；主题雪、婚礼、爱 |
| 鸣潮／Goo | 鸣潮组件局部实验；Goo 5.2.1社区移植版已迁移并交付首版快样片，当前进展看current_state；[Goo实测](docs/GOO_ENGINE_MIGRATION.md) |

最新输出根为`D:\codex\output\MMD-Clean-Game-Characters-v1`。字幕版为`captions-5s\Franken_Duet_5s_CleanGame_Wedding_REVIEW.mp4`，无字幕版为`captions-5s\Franken_Duet_5s_CleanGame_NoCaptions.mp4`。321项材质静态、26项去弧增量和72帧三轴诊断通过；beauty／actor300帧全新渲染，两版各300帧全解码、音轨、色彩及各自接缝通过，1200个双人头／身内部覆盖ROI均通过。最终AAC还与指定原唱FLAC片段独立PCM比对，确认来源正确，不等同音乐卡点完成。

主任务实际查看两版各12个时点、四处字幕边界共32帧连续图，另看4186／4190／4218／4220／4225／4317／4318七张原生腕部关键全图（4140／4290此前已看），抽样未见阻断退化。具体见输出根`delivery.json`与`manual-review.json`；这是限定人工抽样，未认证全片逐帧美术、零几何交线或用户认可。此前婚礼v7、[外部技术移植](docs/REFERENCE_TECHNIQUE_TRANSFER.md)与[人物分层](docs/CHARACTER_LAYER_REFINEMENT.md)保留历史。

详细工程、来源和音频约定见[婚礼制作记录](docs/IKHOR_BOLD_WEDDING_PRODUCTION.md)、[阿克西妮娅／伊科尔署名](docs/CREDITS_AKSINIYA_IKHOR.md)；[双人项目](docs/DUET_FULL_PRODUCTION.md)与[原双人署名](docs/CREDITS_FRANKEN_DUET.md)保留历史。旧MP4缺色彩标签等问题见[自身阴影与色彩](docs/SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md)。

## 仓库分工

- `catalog/`：现行状态、关卡、资料库分类与学习队列；`library.json`继续管理预设和预览，不替代用户反馈。
- `docs/`：可复用指南与历次研究；`docs/research/`为来源账本，`docs/history/`保存整理前入口快照。
- `presets/`：项目／人物实验／舞台／字幕／渲染与后期／风格×画幅／工程配方，各自分层。
- `scripts/`：环境、导入、诊断、生产、合成、验证和历史打包工具。职责与副作用见 [工具地图](docs/TOOL_AND_PRESET_MAP.md)。
- `skills/`：Codex任务指导；`blender_addon/`：Blender辅助插件；`site/`：离线知识库；`tests/`：有意义的工具回归测试。

历史文件保留原路径，不重排源素材或旧工程。整理前README／AGENTS／流程／目录快照位于 `docs/history/2026-11-13/`。原README引用的PROJECT_PLAN.md当前不存在，不将其作为可用入口；旧框架说明保留在快照中。

## 环境与使用约定

Blender已安装：`E:\tools\Blender Foundation\Blender 5.2\blender.exe`，不重复下载安装。当前已实测5.2.2 LTS与MMD Tools扩展4.5.14，其他插件状态见 [本机环境](docs/LOCAL_ENVIRONMENT.md)。新进程仍须按当前本机核实。

源码放在 `D:\codex\workspace\`，交付物放在 `D:\codex\output\`，临时产物放在 `D:\codex\temp\`。默认独立后台进程、新目录、不改用户偏好、不覆盖源素材。先做同条件小样，记录实际效果与失败，再提炼预设；请求成片时持续完成约定范围。

当前完整交付见[Clean记录](docs/CLEAN_GAME_CHARACTER_REFINEMENT.md)，继承的舞台／物理／字幕历史见[婚礼制作记录](docs/IKHOR_BOLD_WEDDING_PRODUCTION.md)。外部技术实读见[Nilo／Ray-MMD／Filament](docs/EXTERNAL_MMD_TECHNIQUES_2026_11_13.md)，此前只移植其中部分原则；前轮研究见[学习增量](docs/LEARNING_ROUND_2026_11_13.md)，省流量与字幕缓存见[高效流程](docs/EFFICIENT_RESEARCH_WORKFLOW.md)。持续学习以实际外部阅读为主，资料维护收尾；观海子仍为首要参考，御手洗板蓝根为补充。

IAB与Chrome均曾实际读到B站正文，连接仍有调试异常；Chrome扩展及native host已验证正常，尚未取得完整B站字幕。见 [实际浏览器记录](docs/BROWSER_AUTONOMY.md)。
