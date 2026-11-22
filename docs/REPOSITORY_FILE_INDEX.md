# 仓库全文件索引

自动生成；刷新用`python -m scripts.repository_index --write`。分类只用于导航，不表示逐行审计或可以直接运行。

[仓库导航](REPOSITORY_GUIDE.md) · [脚本分类](../scripts/README.md)

## .codex-plugin（1）

| 文件 | 用途 |
| --- | --- |
| [.codex-plugin/plugin.json](../.codex-plugin/plugin.json) | JSON data |

## blender_addon（7）

| 文件 | 用途 |
| --- | --- |
| [blender_addon/__init__.py](../blender_addon/__init__.py) | Blender-side runtime for the blender-mmd-codex plugin. |
| [blender_addon/operators/__init__.py](../blender_addon/operators/__init__.py) | Blender operators exposed by the Add-on. |
| [blender_addon/operators/health.py](../blender_addon/operators/health.py) | Scene-level Blender environment and object-count checks. |
| [blender_addon/operators/model_check.py](../blender_addon/operators/model_check.py) | Minimal MMD-shaped model checks for the first Add-on slice. |
| [blender_addon/operators/reference_video.py](../blender_addon/operators/reference_video.py) | Import rendered MMD videos into Blender's Video Sequence Editor. |
| [blender_addon/panels/__init__.py](../blender_addon/panels/__init__.py) | Blender UI panels exposed by the Add-on. |
| [blender_addon/panels/main.py](../blender_addon/panels/main.py) | Main Blender Properties panel for the first MMD Codex slice. |

## catalog（11）

| 文件 | 用途 |
| --- | --- |
| [catalog/current_state.json](../catalog/current_state.json) | JSON data |
| [catalog/learning_queue.json](../catalog/learning_queue.json) | 问题驱动、文字优先、证据分级的续接队列；不是后台进程或能力认证 |
| [catalog/library.json](../catalog/library.json) | JSON data |
| [catalog/model_policy.json](../catalog/model_policy.json) | JSON data |
| [catalog/production_pipeline.json](../catalog/production_pipeline.json) | mmd-quality-pipeline-v2 |
| [catalog/reference_studies/fox-event-sampling.json](../catalog/reference_studies/fox-event-sampling.json) | fox-event-sampling |
| [catalog/reference_studies/gosari-portrait-relations.json](../catalog/reference_studies/gosari-portrait-relations.json) | gosari-portrait-relations |
| [catalog/repository_index.json](../catalog/repository_index.json) | Generated machine-readable repository index |
| [catalog/scene_benches.json](../catalog/scene_benches.json) | JSON data |
| [catalog/studio.json](../catalog/studio.json) | 经验索引与学习路线；不替代原始阅读、实际制作或美术认可 |
| [catalog/task_routes.json](../catalog/task_routes.json) | Read-only task-to-knowledge routing; no permission to execute listed production scripts and no certification of art quality |

## docs（109）

| 文件 | 用途 |
| --- | --- |
| [docs/ADVANCED_MMD_SUBTITLES.md](../docs/ADVANCED_MMD_SUBTITLES.md) | 进阶 MMD 学习与横竖屏动态字幕合成 |
| [docs/AETHER_LOOK_REVISION.md](../docs/AETHER_LOOK_REVISION.md) | 空：礼堂双人版材质重建 |
| [docs/AI_TASK_PLAYBOOK.md](../docs/AI_TASK_PLAYBOOK.md) | AI接手任务的知识与制作导航 |
| [docs/ANIMATION_AND_KEYFRAMING_PLAYBOOK.md](../docs/ANIMATION_AND_KEYFRAMING_PLAYBOOK.md) | 动作数据、模型驱动与局部K帧 |
| [docs/AUDIO_CONVERSION.md](../docs/AUDIO_CONVERSION.md) | NCM 转 FLAC / MP3 与双人全曲 BGM |
| [docs/AUTHOR_REFERENCE_MATRIX.md](../docs/AUTHOR_REFERENCE_MATRIX.md) | 作者参考优先级与证据矩阵 |
| [docs/AUTO_QC.md](../docs/AUTO_QC.md) | 自动 QC 判官、多帧稀疏检查与时序诊断 |
| [docs/BILIBILI_SUBTITLE_WORKFLOW.md](../docs/BILIBILI_SUBTITLE_WORKFLOW.md) | B站字幕：合法采集后的离线整理 |
| [docs/BLENDER53_DUET_TOON_MIGRATION_2026_11_19.md](../docs/BLENDER53_DUET_TOON_MIGRATION_2026_11_19.md) | Blender5.3原生作者节点双人试作 |
| [docs/BLENDER53_TOON_PACKAGE_STUDY_2026_11_18.md](../docs/BLENDER53_TOON_PACKAGE_STUDY_2026_11_18.md) | 作者5.3卡渲节点：原生语义与Goo迁移边界 |
| [docs/BLUE_GOLD_WEDDING_STUDY.md](../docs/BLUE_GOLD_WEDDING_STUDY.md) | 蓝金婚礼：射灯、局部体积、光晕与彩色字幕 |
| [docs/BROWSER_AUTONOMY.md](../docs/BROWSER_AUTONOMY.md) | 浏览器自主使用：连接与验收 |
| [docs/CAMERA_SEARCH.md](../docs/CAMERA_SEARCH.md) | 《フランケンシュタインの怪物》镜头与音乐来源记录 |
| [docs/CHARACTER_LAYER_AUDIT.md](../docs/CHARACTER_LAYER_AUDIT.md) | 双人人物受光与材质层独立审计 |
| [docs/CHARACTER_LAYER_REFINEMENT.md](../docs/CHARACTER_LAYER_REFINEMENT.md) | 人物受光与材质分层：双人礼堂实测 |
| [docs/CHARACTER_NPR_PLAYBOOK.md](../docs/CHARACTER_NPR_PLAYBOOK.md) | 人物三渲二制作手册：从“有阴影”到有设计的角色受光 |
| [docs/CHEST_SECONDARY_MOTION_VALIDATION.md](../docs/CHEST_SECONDARY_MOTION_VALIDATION.md) | 胸部次级运动：当前两模型的适用性验证 |
| [docs/CITLALI_WARM_FRINGE_SHADOW_STUDY.md](../docs/CITLALI_WARM_FRINGE_SHADOW_STUDY.md) | 观海子茜特拉莉参考：贴近刘海的暖色投影 |
| [docs/CLEAN_GAME_CHARACTER_REFINEMENT.md](../docs/CLEAN_GAME_CHARACTER_REFINEMENT.md) | 阿克西妮娅×伊科尔：干净明亮人物材质修订 |
| [docs/CLEAR_LIGHT_AND_GRADING.md](../docs/CLEAR_LIGHT_AND_GRADING.md) | 去灰、窗光与人物／场景分开调色 |
| [docs/CONTINUOUS_LEARNING_SYSTEM.md](../docs/CONTINUOUS_LEARNING_SYSTEM.md) | 持续学习怎样转化成更好的MMD |
| [docs/CREDITS.md](../docs/CREDITS.md) | 署名与来源 |
| [docs/CREDITS_AKSINIYA_IKHOR.md](../docs/CREDITS_AKSINIYA_IKHOR.md) | 阿克西妮娅×伊科尔《フランケンシュタインの怪物》来源与署名 |
| [docs/CREDITS_FRANKEN_DUET.md](../docs/CREDITS_FRANKEN_DUET.md) | 《フランケンシュタインの怪物》双人版来源与署名 |
| [docs/DESIGN_FOUNDATIONS_AND_REVIEW.md](../docs/DESIGN_FOUNDATIONS_AND_REVIEW.md) | 设计基础、舞台布光与美术评审 |
| [docs/DUET_CAPTION_STABILITY_AND_LIGHTING.md](../docs/DUET_CAPTION_STABILITY_AND_LIGHTING.md) | 双人官方动效字幕与聚焦灯光 |
| [docs/DUET_FULL_PRODUCTION.md](../docs/DUET_FULL_PRODUCTION.md) | 双人全曲：阿克西妮娅 × 空 |
| [docs/EFFICIENT_RESEARCH_WORKFLOW.md](../docs/EFFICIENT_RESEARCH_WORKFLOW.md) | 低流量、可核验的MMD持续学习 |
| [docs/EXTERNAL_MMD_TECHNIQUES_2026_11_13.md](../docs/EXTERNAL_MMD_TECHNIQUES_2026_11_13.md) | 外部教程实读：人物阴影、Ray环境光与衣料质感 |
| [docs/FACE_INK_REFINEMENT.md](../docs/FACE_INK_REFINEMENT.md) | 对照观海子：清晰的脸部描边与五官内线 |
| [docs/FACE_SHADOW_DESIGN_STUDY.md](../docs/FACE_SHADOW_DESIGN_STUDY.md) | 脸影设计与几何遮挡共存：局部修形的算子位置 |
| [docs/FACE_SHADOW_DESIGN_STUDY_2026_11_18.md](../docs/FACE_SHADOW_DESIGN_STUDY_2026_11_18.md) | 脸部影形研究：解析SDF、阈值图与真实遮挡 |
| [docs/FINAL_DELIVERY.md](../docs/FINAL_DELIVERY.md) | 阿克西妮娅《フランケンシュタインの怪物》副歌成片 |
| [docs/FIRST_TRIAL.md](../docs/FIRST_TRIAL.md) | 阿克西妮娅单角色导入草稿：2026-11-09 |
| [docs/FOX_LIGHTING_AND_CINEMA.md](../docs/FOX_LIGHTING_AND_CINEMA.md) | 《亲亲小狐狸》：舞台明暗、景深与运动模糊 |
| [docs/FOX_STAGE_ART_DEEP_STUDY.md](../docs/FOX_STAGE_ART_DEEP_STUDY.md) | 小狐狸再研究：从夜色滤镜走向舞台光影 |
| [docs/GALLERY_GUIDE.md](../docs/GALLERY_GUIDE.md) | 帧间资料库：使用与维护 |
| [docs/GENSHIN_CHARACTER_AND_PRESETS.md](../docs/GENSHIN_CHARACTER_AND_PRESETS.md) | 原神角色着色、下载预设与新版礼堂五秒样本 |
| [docs/GOO_BLENDER_FOUNDATIONS_2026_11_18.md](../docs/GOO_BLENDER_FOUNDATIONS_2026_11_18.md) | Goo与Blender官方基础学习：受光输入、阴影与显示转换 |
| [docs/GOO_BROAD_WINDOW_AND_STRONG_RIM.md](../docs/GOO_BROAD_WINDOW_AND_STRONG_RIM.md) | 大窗宽幅日光与强衣发轮廓光 |
| [docs/GOO_CHARACTER_LOOKDEV_2026_11_18.md](../docs/GOO_CHARACTER_LOOKDEV_2026_11_18.md) | 双人人物静帧：法线、脸影与材质分层 |
| [docs/GOO_DUET_ARTDIRECTION_2026_11_20.md](../docs/GOO_DUET_ARTDIRECTION_2026_11_20.md) | Goo双人礼堂：从无效调参到舞台层次对照 |
| [docs/GOO_DUET_SDF_IMPLEMENTATION_2026_11_19.md](../docs/GOO_DUET_SDF_IMPLEMENTATION_2026_11_19.md) | 阿克西妮娅／伊科尔：作者脸部影形思路的Goo静帧重建 |
| [docs/GOO_ENGINE_MIGRATION.md](../docs/GOO_ENGINE_MIGRATION.md) | Goo 制作入口与首次迁移 |
| [docs/GOO_FEATURES_AND_MME_MECHANISMS.md](../docs/GOO_FEATURES_AND_MME_MECHANISMS.md) | Goo 与 MME：节点机制、源码增量与独立实验 |
| [docs/GOO_FOUNDATIONS_AND_PARAMETERS.md](../docs/GOO_FOUNDATIONS_AND_PARAMETERS.md) | Goo 基础功能与参数学习 |
| [docs/GOO_MMD_EIGHT_FOUNDATIONS_2026_11_18.md](../docs/GOO_MMD_EIGHT_FOUNDATIONS_2026_11_18.md) | Goo、MMD Tools与插件协作：八项基础的第一轮指南学习 |
| [docs/GOO_REFERENCE_FACE_HAIR_STUDY_2026_11_17.md](../docs/GOO_REFERENCE_FACE_HAIR_STUDY_2026_11_17.md) | 新近景参考与 Goo 法线基础验证 |
| [docs/GOO_RIM_GLOW_REVISION.md](../docs/GOO_RIM_GLOW_REVISION.md) | Goo 人物亮边、高光与场景泛光加强 |
| [docs/GOO_RUNTIME_POLICY.md](../docs/GOO_RUNTIME_POLICY.md) | GooEngine 主线运行时政策与风险管控 |
| [docs/GOO_TYNDALL_RIM_PRODUCTION.md](../docs/GOO_TYNDALL_RIM_PRODUCTION.md) | 白蓝轮廓光、窗向体积与高光泛光 |
| [docs/GOSARI_REFERENCE.md](../docs/GOSARI_REFERENCE.md) | Gosari542《Pretty Girl》本地视频观察 |
| [docs/GUANHAIZI_REFERENCE.md](../docs/GUANHAIZI_REFERENCE.md) | 观海子：横屏舞台与竖屏图形排版参考 |
| [docs/HAIR_SHADOW_TOPLIGHT_AND_BORDERLESS_CAPTIONS.md](../docs/HAIR_SHADOW_TOPLIGHT_AND_BORDERLESS_CAPTIONS.md) | 衣发阴影、柔和顶光对照与字幕去黑边 |
| [docs/HALF_LAMBERT_STUDY.md](../docs/HALF_LAMBERT_STUDY.md) | 良宇喵喵喵教程：半兰伯特、分通道控制与当前实现 |
| [docs/HESPERIDES_AUTHOR_SETUP.md](../docs/HESPERIDES_AUTHOR_SETUP.md) | 礼堂原作者的现成 Ray 配置：检索与核实 |
| [docs/HESPERIDES_REFERENCE_REBUILD.md](../docs/HESPERIDES_REFERENCE_REBUILD.md) | 礼堂 Ray 预览的同机位重建 |
| [docs/HESPERIDES_STAGE_RENDERING.md](../docs/HESPERIDES_STAGE_RENDERING.md) | 赫斯珀利德斯礼堂：从 Ray 材质说明到 Blender 场景渲染 |
| [docs/IKHOR_BOLD_WEDDING_PRODUCTION.md](../docs/IKHOR_BOLD_WEDDING_PRODUCTION.md) | 阿克西妮娅×伊科尔：蓝金婚礼五秒制作记录 |
| [docs/IKHOR_HAIR_ALIGNMENT_STILL_REPAIR.md](../docs/IKHOR_HAIR_ALIGNMENT_STILL_REPAIR.md) | 伊科尔头发错位：静帧修复 |
| [docs/IKHOR_SLEEVE_REPAIR.md](../docs/IKHOR_SLEEVE_REPAIR.md) | 伊科尔袖口：从穿模定位到局部修正 |
| [docs/JELLY_EYE_HAIR_STAGE_IMPLEMENTATION.md](../docs/JELLY_EYE_HAIR_STAGE_IMPLEMENTATION.md) | 果冻眼、眼部高光、眼透、发影与舞台材质 |
| [docs/KNOWLEDGE_INDEX.md](../docs/KNOWLEDGE_INDEX.md) | 知识、预设与制作入口 |
| [docs/LEARNING_ROUND_2026_11_13.md](../docs/LEARNING_ROUND_2026_11_13.md) | 持续学习本轮增量：先补人物质量，再验证 |
| [docs/LIGHT_SPACE_AND_COLOR_PIPELINE.md](../docs/LIGHT_SPACE_AND_COLOR_PIPELINE.md) | 受光、动态稳定与线性合成：双人修订 v1 |
| [docs/LOCAL_CORRECTIVE_SHAPES.md](../docs/LOCAL_CORRECTIVE_SHAPES.md) | 局部 corrective：变形顺序与修复边界 |
| [docs/LOCAL_ENVIRONMENT.md](../docs/LOCAL_ENVIRONMENT.md) | 本机环境与插件学习记录 |
| [docs/LOOK_REFINEMENT.md](../docs/LOOK_REFINEMENT.md) | 阿克西妮娅渲染改进：从灰化调色到分区 NPR |
| [docs/MATERIAL_RESPONSE_STUDY.md](../docs/MATERIAL_RESPONSE_STUDY.md) | 材质响应续读：球面反射色与布料纤维光 |
| [docs/MMD_MME_GOO_WORKFLOW.md](../docs/MMD_MME_GOO_WORKFLOW.md) | MMD MME 与 Goo 分工方案 |
| [docs/MME_NATIVE_LEARNING_LAB.md](../docs/MME_NATIVE_LEARNING_LAB.md) | MME 原生预设学习实验 |
| [docs/MME_REFERENCE_LIGHT_STILLS_2026_11_17.md](../docs/MME_REFERENCE_LIGHT_STILLS_2026_11_17.md) | 新借物表与蓝白人物光影静帧 |
| [docs/MME_REUSE_AND_BLENDER_COMPATIBILITY.md](../docs/MME_REUSE_AND_BLENDER_COMPATIBILITY.md) | MME 复用与本机 Blender 兼容边界 |
| [docs/MME_TO_GOO_LIGHTING_STUDY.md](../docs/MME_TO_GOO_LIGHTING_STUDY.md) | MME 卡渲与灯光：原包阅读及 Goo 实作 |
| [docs/NEXT_QUALITY_REVIEW.md](../docs/NEXT_QUALITY_REVIEW.md) | 下一轮质感学习与双人全曲优先级 |
| [docs/NPR_NEXT_EXPERIMENTS.md](../docs/NPR_NEXT_EXPERIMENTS.md) | 人物 NPR 下一轮三个实验 |
| [docs/NPR_PRIMARY_STUDY_2026_11_13.md](../docs/NPR_PRIMARY_STUDY_2026_11_13.md) | 2026-11-13 一手图文续读：发丝高光的形状与阴影策略 |
| [docs/PHYSICS_MOTION_PLAYBOOK.md](../docs/PHYSICS_MOTION_PLAYBOOK.md) | 衣发与身体次级运动：物理制作手册 |
| [docs/PORTRAIT_LIGHTING_AND_SHADOW_STUDY.md](../docs/PORTRAIT_LIGHTING_AND_SHADOW_STUDY.md) | 明亮人物与暗场层次：逐层布光、亮边和脸影 |
| [docs/PORTRAIT_RELIGHT_IMPLEMENTATION.md](../docs/PORTRAIT_RELIGHT_IMPLEMENTATION.md) | 双人人像重新打光：本轮实现、定位与复用步骤 |
| [docs/PORTRAIT_RELIGHT_V2.md](../docs/PORTRAIT_RELIGHT_V2.md) | 人像重新打光v2：明亮脸部与蓝灰、桃粉礼堂 |
| [docs/PRODUCTION_HISTORY_CONTEXT.md](../docs/PRODUCTION_HISTORY_CONTEXT.md) | 旧制作状态记录（历史归档） |
| [docs/PRODUCTION_TECHNIQUES.md](../docs/PRODUCTION_TECHNIQUES.md) | 衣发物理、参考风格与成片：已验证的制作方法 |
| [docs/PRODUCTION_WORKFLOW.md](../docs/PRODUCTION_WORKFLOW.md) | 高质量MMD制作流程 |
| [docs/PROJECT_FRANKEN_DUET_RULES.md](../docs/PROJECT_FRANKEN_DUET_RULES.md) | 《フランケンシュタインの怪物》双人作品专属约定 |
| [docs/QUALITY_GATES.md](../docs/QUALITY_GATES.md) | 高质量MMD的质量关卡 |
| [docs/QUALITY_LIGHTING_LAB.md](../docs/QUALITY_LIGHTING_LAB.md) | 进阶质感：插件学习、材质与光影实测 |
| [docs/REFERENCE_AND_LIGHTING_PLAYBOOK.md](../docs/REFERENCE_AND_LIGHTING_PLAYBOOK.md) | 参考研究、舞台灯光与后期的制作手册 |
| [docs/REFERENCE_TECHNIQUE_TRANSFER.md](../docs/REFERENCE_TECHNIQUE_TRANSFER.md) | 外部技术移植：人物阴影、材质与礼堂层次 |
| [docs/REPOSITORY_FILE_INDEX.md](../docs/REPOSITORY_FILE_INDEX.md) | Generated complete file navigation |
| [docs/REPOSITORY_GUIDE.md](../docs/REPOSITORY_GUIDE.md) | 仓库导航与维护 |
| [docs/REPOSITORY_ORGANIZATION_2026_11_17.md](../docs/REPOSITORY_ORGANIZATION_2026_11_17.md) | 仓库整理记录 2026年11月17日 |
| [docs/REPOSITORY_ORGANIZATION_2026_11_18.md](../docs/REPOSITORY_ORGANIZATION_2026_11_18.md) | 按制作任务组织知识：2026年11月18日 |
| [docs/REPOSITORY_REVIEW_2026_11.md](../docs/REPOSITORY_REVIEW_2026_11.md) | 仓库复审：从实验记录到高质量 MMD 制作指导 |
| [docs/SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md](../docs/SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md) | 人物自阴影、描边与播放器色彩 |
| [docs/SOFT_TOP_RIM_LIGHTING.md](../docs/SOFT_TOP_RIM_LIGHTING.md) | 柔光、顶光与逆光：提亮礼堂而保留层次 |
| [docs/STAGE_ART_NIGHT_STUDY.md](../docs/STAGE_ART_NIGHT_STUDY.md) | 半开放夜景：舞台美术学习与礼堂静帧实验 |
| [docs/STAGE_SEARCH.md](../docs/STAGE_SEARCH.md) | MMD 背景场景检索、选景与 Blender 验证 |
| [docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md](../docs/STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md) | 崩铁参考：明亮肤色与可读发影 |
| [docs/STUDIO_ITERATION.md](../docs/STUDIO_ITERATION.md) | 从参考到作品经验 |
| [docs/STUDIO_SCENE_BENCH.md](../docs/STUDIO_SCENE_BENCH.md) | 安全开工程、角色语义映射与静帧试验台 |
| [docs/STUDIO_WORKFLOW.md](../docs/STUDIO_WORKFLOW.md) | 长期制作与学习的实际工作入口 |
| [docs/STYLE_PRESETS.md](../docs/STYLE_PRESETS.md) | 多风格渲染、后期与横竖屏预设 |
| [docs/SUBTITLE_DELIVERY.md](../docs/SUBTITLE_DELIVERY.md) | 横竖屏动态字幕研究交付 |
| [docs/SURFACE_REFINEMENT.md](../docs/SURFACE_REFINEMENT.md) | 发丝、金属遮罩与可见描边：质感精修 |
| [docs/TOOL_AND_PRESET_MAP.md](../docs/TOOL_AND_PRESET_MAP.md) | 工具、预设与知识的职责地图 |
| [docs/TUTORIAL_STUDY.md](../docs/TUTORIAL_STUDY.md) | 卡渲、打光、镜头和 MME：教程研究与本机试验 |
| [docs/TUTORIAL_TRANSCRIPTION.md](../docs/TUTORIAL_TRANSCRIPTION.md) | 教程学习：本地语音转写与屏幕说明 OCR |
| [docs/WUWA_TOON_STUDY.md](../docs/WUWA_TOON_STUDY.md) | 鸣潮三渲二：资料、预设审计与发丝对照 |

## history（16）

| 文件 | 用途 |
| --- | --- |
| [docs/history/2026-11-13/AGENTS.snapshot.md](../docs/history/2026-11-13/AGENTS.snapshot.md) | 本仓库的制作目标与工作约定 |
| [docs/history/2026-11-13/KNOWLEDGE_INDEX.snapshot.md](../docs/history/2026-11-13/KNOWLEDGE_INDEX.snapshot.md) | 知识、预设与制作入口 |
| [docs/history/2026-11-13/PRODUCTION_WORKFLOW.snapshot.md](../docs/history/2026-11-13/PRODUCTION_WORKFLOW.snapshot.md) | 从单角色试作到可复用 MMD 制作流程 |
| [docs/history/2026-11-13/README.snapshot.md](../docs/history/2026-11-13/README.snapshot.md) | blender-mmd-codex |
| [docs/history/2026-11-17/repository-before-organization/.gitignore](../docs/history/2026-11-17/repository-before-organization/.gitignore) | Repository source or supporting file |
| [docs/history/2026-11-17/repository-before-organization/AGENTS.md](../docs/history/2026-11-17/repository-before-organization/AGENTS.md) | 本仓库的制作目标与工作约定 |
| [docs/history/2026-11-17/repository-before-organization/README.md](../docs/history/2026-11-17/repository-before-organization/README.md) | blender-mmd-codex |
| [docs/history/2026-11-17/repository-before-organization/catalog__current_state.json](../docs/history/2026-11-17/repository-before-organization/catalog__current_state.json) | JSON data |
| [docs/history/2026-11-17/repository-before-organization/docs__KNOWLEDGE_INDEX.md](../docs/history/2026-11-17/repository-before-organization/docs__KNOWLEDGE_INDEX.md) | 知识、预设与制作入口 |
| [docs/history/2026-11-17/repository-before-organization/docs__LOCAL_ENVIRONMENT.md](../docs/history/2026-11-17/repository-before-organization/docs__LOCAL_ENVIRONMENT.md) | 本机环境与插件学习记录 |
| [docs/history/2026-11-17/repository-before-organization/docs__PRODUCTION_WORKFLOW.md](../docs/history/2026-11-17/repository-before-organization/docs__PRODUCTION_WORKFLOW.md) | 高质量MMD制作流程 |
| [docs/history/2026-11-17/repository-before-organization/docs__TOOL_AND_PRESET_MAP.md](../docs/history/2026-11-17/repository-before-organization/docs__TOOL_AND_PRESET_MAP.md) | 工具、预设与知识的职责地图 |
| [docs/history/2026-11-17/repository-before-organization/git-status-before.txt](../docs/history/2026-11-17/repository-before-organization/git-status-before.txt) | Repository source or supporting file |
| [docs/history/2026-11-22/AGENTS.before-slimming.md](../docs/history/2026-11-22/AGENTS.before-slimming.md) | 制作目标与仓库工作约定 |
| [docs/history/2026-11-22/current_state.before-slimming.json](../docs/history/2026-11-22/current_state.before-slimming.json) | JSON data |
| [docs/history/2026-11-22/state_history.json](../docs/history/2026-11-22/state_history.json) | JSON data |

## presets（91）

| 文件 | 用途 |
| --- | --- |
| [presets/benches/fixture-a.json](../presets/benches/fixture-a.json) | studio-fixture-a |
| [presets/benches/fixture-b.json](../presets/benches/fixture-b.json) | studio-fixture-b |
| [presets/benches/goo-duet-artdirection-candidate-v1.json](../presets/benches/goo-duet-artdirection-candidate-v1.json) | goo-duet-artdirection-candidate-v1 |
| [presets/benches/goo-duet-stage-response-v1.json](../presets/benches/goo-duet-stage-response-v1.json) | goo-duet-stage-response-v1 |
| [presets/benches/native53-duet-v3.json](../presets/benches/native53-duet-v3.json) | native53-duet-v3-static |
| [presets/lighting/citlali-fringe-contact-still-v1.json](../presets/lighting/citlali-fringe-contact-still-v1.json) | JSON data |
| [presets/lighting/goo-daylight-v2.json](../presets/lighting/goo-daylight-v2.json) | goo-daylight-v2 |
| [presets/lighting/goo-eye-hair-stage-v1.json](../presets/lighting/goo-eye-hair-stage-v1.json) | goo-eye-hair-stage-v1 |
| [presets/lighting/goo-tyndall-rim-v1.json](../presets/lighting/goo-tyndall-rim-v1.json) | goo-tyndall-rim-v1 |
| [presets/lighting/goo-wedding-v1.json](../presets/lighting/goo-wedding-v1.json) | goo-wedding-v1 |
| [presets/lighting/goo-window-wrap-v1.json](../presets/lighting/goo-window-wrap-v1.json) | goo-window-wrap-v1 |
| [presets/lighting/mme-reference-light-still-v1.json](../presets/lighting/mme-reference-light-still-v1.json) | JSON data |
| [presets/lighting/mme-reference-light-still-v2.json](../presets/lighting/mme-reference-light-still-v2.json) | JSON data |
| [presets/lighting/mme-reference-light-still-v3.json](../presets/lighting/mme-reference-light-still-v3.json) | JSON data |
| [presets/lighting/portrait-daylight-v3.json](../presets/lighting/portrait-daylight-v3.json) | portrait-daylight-v3 |
| [presets/lighting/portrait-face-fill-v2.json](../presets/lighting/portrait-face-fill-v2.json) | portrait-face-fill-v2 |
| [presets/lighting/portrait-layer-study-v1.json](../presets/lighting/portrait-layer-study-v1.json) | portrait-layer-study-v1 |
| [presets/lighting/portrait-relight-v1.json](../presets/lighting/portrait-relight-v1.json) | portrait-relight-v1 |
| [presets/lighting/portrait-relight-v2.json](../presets/lighting/portrait-relight-v2.json) | portrait-relight-v2 |
| [presets/lighting/portrait-rim-v2.json](../presets/lighting/portrait-rim-v2.json) | portrait-rim-v2 |
| [presets/lighting/portrait-sunlit-v4.json](../presets/lighting/portrait-sunlit-v4.json) | portrait-sunlit-v4 |
| [presets/projects/franken-duet-full-v1.json](../presets/projects/franken-duet-full-v1.json) | franken-duet-full-v1 |
| [presets/qc/auto-qc-v1.json](../presets/qc/auto-qc-v1.json) | auto-qc-v1 |
| [presets/quality/aether-hall-surface-v1.json](../presets/quality/aether-hall-surface-v1.json) | aether-hall-surface-v1 |
| [presets/quality/aksiniya-clean-game-v1.json](../presets/quality/aksiniya-clean-game-v1.json) | aksiniya-clean-game-v1 |
| [presets/quality/duet-bold-wedding-emission-v1.json](../presets/quality/duet-bold-wedding-emission-v1.json) | duet-bold-wedding-emission-v1 |
| [presets/quality/duet-character-layers-v1.json](../presets/quality/duet-character-layers-v1.json) | duet-character-layers-v1 |
| [presets/quality/duet-graphic-self-shadow-v1.json](../presets/quality/duet-graphic-self-shadow-v1.json) | duet-graphic-self-shadow-v1 |
| [presets/quality/duet-guanhai-transfer-v1.json](../presets/quality/duet-guanhai-transfer-v1.json) | duet-guanhai-transfer-v1 |
| [presets/quality/duet-light-space-v1.json](../presets/quality/duet-light-space-v1.json) | duet-light-space-v1 |
| [presets/quality/goo-character-lookdev-2026-11-18-v1.json](../presets/quality/goo-character-lookdev-2026-11-18-v1.json) | JSON data |
| [presets/quality/half-lambert-v1.json](../presets/quality/half-lambert-v1.json) | half-lambert-gradient-v1 |
| [presets/quality/ikhor-character-v1.json](../presets/quality/ikhor-character-v1.json) | ikhor-character-v1 |
| [presets/quality/ikhor-clean-game-v1.json](../presets/quality/ikhor-clean-game-v1.json) | ikhor-clean-game-v1 |
| [presets/quality/ikhor-native-motion-v1.json](../presets/quality/ikhor-native-motion-v1.json) | ikhor-native-motion-v1 |
| [presets/quality/ikhor-sleeve-repair-v1.json](../presets/quality/ikhor-sleeve-repair-v1.json) | ikhor-sleeve-repair-v1 |
| [presets/quality/npr-detail-lab-v1.json](../presets/quality/npr-detail-lab-v1.json) | JSON data |
| [presets/quality/outlines-v1.json](../presets/quality/outlines-v1.json) | aksiniya-readable-ink-v1 |
| [presets/quality/outlines-v2-face-black.json](../presets/quality/outlines-v2-face-black.json) | aksiniya-readable-face-ink-v2 |
| [presets/quality/surface-refinement-v1.json](../presets/quality/surface-refinement-v1.json) | aksiniya-surface-refinement-v1 |
| [presets/quality/surface-refinement-v2.json](../presets/quality/surface-refinement-v2.json) | aksiniya-surface-refinement-v2 |
| [presets/quality/winter-wedding-clear-light-v1.json](../presets/quality/winter-wedding-clear-light-v1.json) | winter-wedding-clear-light-v1 |
| [presets/recipes/duet-blue-gold-wedding-v1.json](../presets/recipes/duet-blue-gold-wedding-v1.json) | duet-blue-gold-wedding-v1 |
| [presets/recipes/duet-captions-focused-v1.json](../presets/recipes/duet-captions-focused-v1.json) | duet-captions-focused-v1 |
| [presets/recipes/duet-character-layers-v1.json](../presets/recipes/duet-character-layers-v1.json) | duet-character-layers-v1 |
| [presets/recipes/duet-clean-game-v1.json](../presets/recipes/duet-clean-game-v1.json) | duet-clean-game-v1 |
| [presets/recipes/duet-grounded-color-v1.json](../presets/recipes/duet-grounded-color-v1.json) | duet-grounded-color-v1 |
| [presets/recipes/duet-guanhai-transfer-v1.json](../presets/recipes/duet-guanhai-transfer-v1.json) | duet-guanhai-transfer-v1 |
| [presets/recipes/duet-light-space-v1.json](../presets/recipes/duet-light-space-v1.json) | duet-light-space-v1 |
| [presets/recipes/duet-soft-top-rim-v1.json](../presets/recipes/duet-soft-top-rim-v1.json) | duet-soft-top-rim-v1 |
| [presets/recipes/franken-ikhor-bold-wedding-v1.json](../presets/recipes/franken-ikhor-bold-wedding-v1.json) | franken-ikhor-bold-wedding-v1 |
| [presets/recipes/genshin-duet-hall-v3.json](../presets/recipes/genshin-duet-hall-v3.json) | genshin-duet-hall-v3 |
| [presets/recipes/hesperides-fox-cinema-v1.json](../presets/recipes/hesperides-fox-cinema-v1.json) | hesperides-fox-cinema-v1 |
| [presets/recipes/hesperides-stageart-v2.json](../presets/recipes/hesperides-stageart-v2.json) | hesperides-stageart-v2 |
| [presets/recipes/wuwa-hair-lab-v1.json](../presets/recipes/wuwa-hair-lab-v1.json) | wuwa-hair-lab-v1 |
| [presets/runtime/goo-v1.json](../presets/runtime/goo-v1.json) | goo-v1 |
| [presets/runtime/native53-v1.json](../presets/runtime/native53-v1.json) | native53-v1 |
| [presets/stages/hesperides-blue-gold-wedding-v1.json](../presets/stages/hesperides-blue-gold-wedding-v1.json) | hesperides-blue-gold-wedding-v1 |
| [presets/stages/hesperides-bold-wedding-v1.json](../presets/stages/hesperides-bold-wedding-v1.json) | hesperides-bold-wedding-v1 |
| [presets/stages/hesperides-bright-ray-reference-v2.json](../presets/stages/hesperides-bright-ray-reference-v2.json) | hesperides-bright-ray-reference-v2 |
| [presets/stages/hesperides-focused-light-v3.json](../presets/stages/hesperides-focused-light-v3.json) | hesperides-focused-light-v3 |
| [presets/stages/hesperides-fox-cinema-v1.json](../presets/stages/hesperides-fox-cinema-v1.json) | hesperides-fox-cinema-v1 |
| [presets/stages/hesperides-grounded-shadows-v1.json](../presets/stages/hesperides-grounded-shadows-v1.json) | hesperides-grounded-shadows-v1 |
| [presets/stages/hesperides-moonlit-vows-v1.json](../presets/stages/hesperides-moonlit-vows-v1.json) | hesperides-moonlit-vows-v1 |
| [presets/stages/hesperides-ray-reference-v1.json](../presets/stages/hesperides-ray-reference-v1.json) | hesperides-ray-reference-v1 |
| [presets/stages/hesperides-soft-top-rim-v1.json](../presets/stages/hesperides-soft-top-rim-v1.json) | hesperides-soft-top-rim-v1 |
| [presets/stages/hesperides-stageart-v2.json](../presets/stages/hesperides-stageart-v2.json) | hesperides-stageart-v2 |
| [presets/stages/hesperides-winter-wedding-v1.json](../presets/stages/hesperides-winter-wedding-v1.json) | hesperides-winter-wedding-v1 |
| [presets/styles/catalog.json](../presets/styles/catalog.json) | JSON data |
| [presets/styles/packages/gosari-landscape-v1.json](../presets/styles/packages/gosari-landscape-v1.json) | gosari-landscape-v1 |
| [presets/styles/packages/gosari-portrait-v1.json](../presets/styles/packages/gosari-portrait-v1.json) | gosari-portrait-v1 |
| [presets/styles/packages/guanhaizi-graphic-landscape-v1.json](../presets/styles/packages/guanhaizi-graphic-landscape-v1.json) | guanhaizi-graphic-landscape-v1 |
| [presets/styles/packages/guanhaizi-graphic-portrait-v1.json](../presets/styles/packages/guanhaizi-graphic-portrait-v1.json) | guanhaizi-graphic-portrait-v1 |
| [presets/styles/packages/guanhaizi-neon-landscape-v1.json](../presets/styles/packages/guanhaizi-neon-landscape-v1.json) | guanhaizi-neon-landscape-v1 |
| [presets/styles/packages/guanhaizi-neon-portrait-v1.json](../presets/styles/packages/guanhaizi-neon-portrait-v1.json) | guanhaizi-neon-portrait-v1 |
| [presets/styles/post/gosari-soft-v1.json](../presets/styles/post/gosari-soft-v1.json) | gosari-soft-post-v1 |
| [presets/styles/post/guanhaizi-graphic-v1.json](../presets/styles/post/guanhaizi-graphic-v1.json) | guanhaizi-graphic-post-v1 |
| [presets/styles/post/guanhaizi-neon-v1.json](../presets/styles/post/guanhaizi-neon-v1.json) | guanhaizi-neon-post-v1 |
| [presets/styles/render/gosari-soft-v1.json](../presets/styles/render/gosari-soft-v1.json) | gosari-soft-render-v1 |
| [presets/styles/render/guanhaizi-graphic-v1.json](../presets/styles/render/guanhaizi-graphic-v1.json) | guanhaizi-graphic-render-v1 |
| [presets/styles/render/guanhaizi-neon-v1.json](../presets/styles/render/guanhaizi-neon-v1.json) | guanhaizi-neon-render-v1 |
| [presets/templates/iteration-brief-v1.json](../presets/templates/iteration-brief-v1.json) | iteration-brief-v1 |
| [presets/typography/duet-blue-gold-wedding-no-border-v1.json](../presets/typography/duet-blue-gold-wedding-no-border-v1.json) | duet-blue-gold-wedding-no-border-v1 |
| [presets/typography/duet-blue-gold-wedding-v1.json](../presets/typography/duet-blue-gold-wedding-v1.json) | duet-blue-gold-wedding-v1 |
| [presets/typography/duet-official-locked-v2.json](../presets/typography/duet-official-locked-v2.json) | duet-official-locked-v2 |
| [presets/typography/landscape-study.json](../presets/typography/landscape-study.json) | JSON data |
| [presets/typography/portrait-study.json](../presets/typography/portrait-study.json) | JSON data |
| [presets/typography/portrait-surface-study.json](../presets/typography/portrait-surface-study.json) | JSON data |
| [presets/workflows/goo-foundations-v1.json](../presets/workflows/goo-foundations-v1.json) | goo-foundations-v1 |
| [presets/workflows/goo-mmd-foundations-v1.json](../presets/workflows/goo-mmd-foundations-v1.json) | goo-mmd-foundations-v1 |
| [presets/workflows/mmd-mme-goo-v1.json](../presets/workflows/mmd-mme-goo-v1.json) | mmd-mme-goo-workflow-v1 |

## research_ledgers（48）

| 文件 | 用途 |
| --- | --- |
| [docs/research/AUTHOR_REFERENCE_MATRIX.json](../docs/research/AUTHOR_REFERENCE_MATRIX.json) | 登记用户最新作者参考优先级、已有观察范围与新增署名线索，不替代现行工程状态 |
| [docs/research/BAICAI_LAYERED_LIGHTING_TUTORIAL_2026_11_14.json](../docs/research/BAICAI_LAYERED_LIGHTING_TUTORIAL_2026_11_14.json) | baicai-layered-lighting-tutorial-2026-11-14 |
| [docs/research/BILIBILI_SESSION_STUDY_2026_11_13.json](../docs/research/BILIBILI_SESSION_STUDY_2026_11_13.json) | JSON data |
| [docs/research/BLENDER53_TOON_PACKAGE_STUDY_2026_11_18.json](../docs/research/BLENDER53_TOON_PACKAGE_STUDY_2026_11_18.json) | blender53-toon-package-study-2026-11-18 |
| [docs/research/BROWSER_ACCESS_VALIDATION.json](../docs/research/BROWSER_ACCESS_VALIDATION.json) | JSON data |
| [docs/research/CHARACTER_LAYER_SOURCES.json](../docs/research/CHARACTER_LAYER_SOURCES.json) | JSON data |
| [docs/research/CHARACTER_SOURCE_LEDGER.json](../docs/research/CHARACTER_SOURCE_LEDGER.json) | 人物三渲二质量复审；记录读取范围、事实与推断，不将阅读或静帧实验晋升为生产兼容或参考级质量 |
| [docs/research/CITLALI_FRINGE_2026_11_17.json](../docs/research/CITLALI_FRINGE_2026_11_17.json) | JSON data |
| [docs/research/DESIGN_FOUNDATIONS_2026_11_18.json](../docs/research/DESIGN_FOUNDATIONS_2026_11_18.json) | JSON data |
| [docs/research/DIRECTIONAL_RIM_LIGHT_2026_11_14.json](../docs/research/DIRECTIONAL_RIM_LIGHT_2026_11_14.json) | 回应猪猪希望打光与轮廓光更明亮、人物层次更突出：学习如何分别控制边缘亮度、覆盖宽度、方向、材质许可与暗侧保留。 |
| [docs/research/EXTERNAL_MATERIAL_LIGHTING_2026_11_13.json](../docs/research/EXTERNAL_MATERIAL_LIGHTING_2026_11_13.json) | 给现有三渲二的金属和布料闭包补充诊断方法，不替换主要NPR色带，也不改成写实渲染。 |
| [docs/research/EXTERNAL_RAY_MMD_2026_11_13.json](../docs/research/EXTERNAL_RAY_MMD_2026_11_13.json) | JSON data |
| [docs/research/EXTERNAL_TOON_SHADOW_2026_11_13.json](../docs/research/EXTERNAL_TOON_SHADOW_2026_11_13.json) | external-toon-shadow-2026-11-13 |
| [docs/research/FACE_SHADOW_DESIGN_2026_11_14.json](../docs/research/FACE_SHADOW_DESIGN_2026_11_14.json) | face-shadow-design-2026-11-14 |
| [docs/research/FACE_SHADOW_DESIGN_STUDY.json](../docs/research/FACE_SHADOW_DESIGN_STUDY.json) | face-shadow-design-study-2026-11-13 |
| [docs/research/FACE_SHADOW_DESIGN_STUDY_2026_11_18.json](../docs/research/FACE_SHADOW_DESIGN_STUDY_2026_11_18.json) | face-shadow-design-study-2026-11-18 |
| [docs/research/FEMALE_CLEAN_NPR_REFERENCE_2026_11_14.json](../docs/research/FEMALE_CLEAN_NPR_REFERENCE_2026_11_14.json) | JSON data |
| [docs/research/GOO_BLENDER_FOUNDATIONS_2026_11_18.json](../docs/research/GOO_BLENDER_FOUNDATIONS_2026_11_18.json) | JSON data |
| [docs/research/GOO_CHARACTER_LOOKDEV_2026_11_18.json](../docs/research/GOO_CHARACTER_LOOKDEV_2026_11_18.json) | JSON data |
| [docs/research/GOO_DUET_SDF_IMPLEMENTATION_2026_11_19.json](../docs/research/GOO_DUET_SDF_IMPLEMENTATION_2026_11_19.json) | goo-duet-sdf-implementation-2026-11-19 |
| [docs/research/GOO_ENGINE_2026_11_16.json](../docs/research/GOO_ENGINE_2026_11_16.json) | JSON data |
| [docs/research/GOO_FEATURE_MME_MECHANISMS_2026_11_16.json](../docs/research/GOO_FEATURE_MME_MECHANISMS_2026_11_16.json) | JSON data |
| [docs/research/GOO_FOUNDATIONS_2026_11_17.json](../docs/research/GOO_FOUNDATIONS_2026_11_17.json) | JSON data |
| [docs/research/GOO_MMD_EIGHT_FOUNDATIONS_2026_11_18.json](../docs/research/GOO_MMD_EIGHT_FOUNDATIONS_2026_11_18.json) | JSON data |
| [docs/research/GOO_REFERENCE_NORMAL_2026_11_17.json](../docs/research/GOO_REFERENCE_NORMAL_2026_11_17.json) | JSON data |
| [docs/research/GRAY_EYED_PRIMORDIAL_MODEL_2026_11_14.json](../docs/research/GRAY_EYED_PRIMORDIAL_MODEL_2026_11_14.json) | JSON data |
| [docs/research/IKHOR_PRINCE_REFERENCE_2026_11_14.json](../docs/research/IKHOR_PRINCE_REFERENCE_2026_11_14.json) | JSON data |
| [docs/research/JELLY_EYE_2026_11_16.json](../docs/research/JELLY_EYE_2026_11_16.json) | JSON data |
| [docs/research/MATERIAL_RESPONSE_STUDY.json](../docs/research/MATERIAL_RESPONSE_STUDY.json) | JSON data |
| [docs/research/MMD_MME_GOO_ROUTE_2026_11_17.json](../docs/research/MMD_MME_GOO_ROUTE_2026_11_17.json) | JSON data |
| [docs/research/MME_DEEP_STUDY_2026_11_16.json](../docs/research/MME_DEEP_STUDY_2026_11_16.json) | JSON data |
| [docs/research/MME_REFERENCE_LIGHT_2026_11_17.json](../docs/research/MME_REFERENCE_LIGHT_2026_11_17.json) | JSON data |
| [docs/research/NODE_WRANGLER_LIGHTING_2026_11_14.json](../docs/research/NODE_WRANGLER_LIGHTING_2026_11_14.json) | JSON data |
| [docs/research/NPR_NEXT_EXPERIMENTS.json](../docs/research/NPR_NEXT_EXPERIMENTS.json) | 下一轮脸影、发束法线与控制图的三个可独立关闭实验；不改变当前渲染输入。 |
| [docs/research/NPR_PRIMARY_STUDY_2026_11_13.json](../docs/research/NPR_PRIMARY_STUDY_2026_11_13.json) | JSON data |
| [docs/research/PAIERER_DARK_STAGE_PORTRAIT_2026_11_14.json](../docs/research/PAIERER_DARK_STAGE_PORTRAIT_2026_11_14.json) | paierer-dark-stage-portrait-2026-11-14 |
| [docs/research/PHOTOGRAPHIC_LAYERED_LIGHTING_2026_11_14.json](../docs/research/PHOTOGRAPHIC_LAYERED_LIGHTING_2026_11_14.json) | 按猪猪提出的摄影布光方向，学习可用于双人MMD的逐层多灯分工；当前重点为深蓝女装与白衣男装同场的暗部可读、主光塑形、白衣控制、环境及背光分离。 |
| [docs/research/PHYSICS_SOURCE_LEDGER.json](../docs/research/PHYSICS_SOURCE_LEDGER.json) | JSON data |
| [docs/research/PRIMORDIAL_ONE_BACKGROUND_MODEL_2026_11_14.json](../docs/research/PRIMORDIAL_ONE_BACKGROUND_MODEL_2026_11_14.json) | JSON data |
| [docs/research/REFERENCE_REVIEW_LEDGER.json](../docs/research/REFERENCE_REVIEW_LEDGER.json) | JSON data |
| [docs/research/REPOSITORY_AUDIT.json](../docs/research/REPOSITORY_AUDIT.json) | JSON data |
| [docs/research/SLEEVE_CORRECTIVE_EXTERNAL_2026_11_14.json](../docs/research/SLEEVE_CORRECTIVE_EXTERNAL_2026_11_14.json) | 区分相对ShapeKey、Armature求值顺序、Corrective Smooth、权重与刚体的修复边界，解释伊科尔袖口局部corrective的可复用条件。 |
| [docs/research/STAR_RAIL_FACE_HAIR_2026_11_17.json](../docs/research/STAR_RAIL_FACE_HAIR_2026_11_17.json) | JSON data |
| [docs/research/STUDIO_ITERATION_2026_11_20.json](../docs/research/STUDIO_ITERATION_2026_11_20.json) | Original record of implemented reference-experiment-review-lesson-save/reopen workflow and real Goo use |
| [docs/research/STUDIO_SCENE_BENCH_2026_11_20.json](../docs/research/STUDIO_SCENE_BENCH_2026_11_20.json) | Original implementation/review evidence for reusable native53 static diagnostics; no full third-party source copied |
| [docs/research/TEXT_NPR_SOURCE_DISCOVERY.json](../docs/research/TEXT_NPR_SOURCE_DISCOVERY.json) | 以现有人物质量缺口筛选可持续复读的一手文字来源；本轮集中补描边单位、分色参数语义和Blender迁移边界。 |
| [docs/research/TEXT_PHYSICS_SOURCE_DISCOVERY.json](../docs/research/TEXT_PHYSICS_SOURCE_DISCOVERY.json) | 复用已有物理台账，只保留两个一手文字入口和一个有界对照；不把重复知识计作制作能力增长。 |
| [docs/research/ZHIHU_LIGHTING_ACCESS_2026_11_14.json](../docs/research/ZHIHU_LIGHTING_ACCESS_2026_11_14.json) | JSON data |

## root（5）

| 文件 | 用途 |
| --- | --- |
| [.gitignore](../.gitignore) | Repository source or supporting file |
| [AGENTS.md](../AGENTS.md) | 仓库工作约定 |
| [LICENSE](../LICENSE) | Repository source or supporting file |
| [README.md](../README.md) | blender-mmd-codex |
| [SPEC.md](../SPEC.md) | AI MMD 长期创作体系：项目顶层规范 |

## scripts（327）

| 文件 | 用途 |
| --- | --- |
| [scripts/README.md](../scripts/README.md) | Generated script navigation and side-effect hints |
| [scripts/__init__.py](../scripts/__init__.py) | Local command-line helpers for blender-mmd-codex. |
| [scripts/abnormal_probe.py](../scripts/abnormal_probe.py) | Temporarily register a pinned Abnormal source in an isolated process. |
| [scripts/add_goo_window_gobo.py](../scripts/add_goo_window_gobo.py) | Add an off-camera physical window-pattern lighting accessory to Goo v2. |
| [scripts/aether_look_revision.py](../scripts/aether_look_revision.py) | Rebuild Aether's own face, eyes, hair and masked outfit surfaces. |
| [scripts/aether_material_audit.py](../scripts/aether_material_audit.py) | Inspect Aether's actual source materials and export supplied packed textures. |
| [scripts/align_caption_audio.py](../scripts/align_caption_audio.py) | Measure a typography video's audio offset against the selected original BGM. |
| [scripts/align_duet_audio.py](../scripts/align_duet_audio.py) | Estimate the MV-intro offset from original vocal/inst audio and VMD mouth tracks. |
| [scripts/align_typography.py](../scripts/align_typography.py) | Estimate a typography excerpt's origin in a longer typography video. |
| [scripts/apply_fox_cinema.py](../scripts/apply_fox_cinema.py) | Build an independent lighting, focus and shutter study from the repaired master. |
| [scripts/apply_fox_stageart.py](../scripts/apply_fox_stageart.py) | Develop the reviewed fox study into a shadowed, spatially coherent stage. |
| [scripts/apply_ikhor_sleeve_repair.py](../scripts/apply_ikhor_sleeve_repair.py) | Apply only a separately tested sleeve Action to the rejected v4 master. |
| [scripts/assemble_render_chunks.py](../scripts/assemble_render_chunks.py) | Join independently rendered, contiguous video chunks without recompression. |
| [scripts/audit_chest_binding.py](../scripts/audit_chest_binding.py) | Read full model/rigid bindings to identify supported chest motion chains. |
| [scripts/audit_duet_caption_coverage.py](../scripts/audit_duet_caption_coverage.py) | Read-only semantic head/body ROI audit for a duet caption actor cache. |
| [scripts/audit_ikhor_sleeve_geometry.py](../scripts/audit_ikhor_sleeve_geometry.py) | Read-only geometric audit of Ikhor's wrist/cuff relationship. |
| [scripts/audit_knowledge.py](../scripts/audit_knowledge.py) | Validate current production facts, knowledge links and offline packaging. |
| [scripts/audit_review_color.py](../scripts/audit_review_color.py) | Compare actual compositor RGB with explicitly decoded video color matrices. |
| [scripts/audit_stage_archive.py](../scripts/audit_stage_archive.py) | Test/extract a downloaded stage archive and compare it with existing assets. |
| [scripts/auto_qc.py](../scripts/auto_qc.py) | Automated hard-metric QC, sparse multiframe checks, low-res temporal diagnostics and judge calibration. |
| [scripts/bake_goo_face_hair_shadows.py](../scripts/bake_goo_face_hair_shadows.py) | Bake the two actors' actual animated bang occlusion to portable face-UV sequences. |
| [scripts/benchmark_bold_wedding.py](../scripts/benchmark_bold_wedding.py) | Unsaved 1080p benchmark of constant-one palette bypass pruning only. |
| [scripts/blender_bootstrap.py](../scripts/blender_bootstrap.py) | Coordinate Blender detection, verified portable installation, and validation. |
| [scripts/blender_detect.py](../scripts/blender_detect.py) | Detect installed Blender executables without modifying the host system. |
| [scripts/blender_download.py](../scripts/blender_download.py) | Build official Blender release URLs and download files with SHA-256 verification. |
| [scripts/blender_install.py](../scripts/blender_install.py) | Install Blender portable archives with path-traversal protection. |
| [scripts/blender_inventory.py](../scripts/blender_inventory.py) | Read installed/enabled MMD add-ons and registered APIs inside Blender. |
| [scripts/blender_scene_audit.py](../scripts/blender_scene_audit.py) | Inspect a supplied scene without executing embedded scripts or saving it. |
| [scripts/blender_validate.py](../scripts/blender_validate.py) | Validate Blender, its Python API, and optionally this project's Add-on. |
| [scripts/bold_wedding_materials.py](../scripts/bold_wedding_materials.py) | Selective HDR motifs and narrow directional edges for Reference Transfer v3. |
| [scripts/bowlroll_public_download.py](../scripts/bowlroll_public_download.py) | Download an author-published BowlRoll package only when open and password-free. |
| [scripts/brightness_scene_probe.py](../scripts/brightness_scene_probe.py) | Inspect reachable emission, lighting and color transforms on the same HDR frame. |
| [scripts/build_gallery.py](../scripts/build_gallery.py) | Build the offline MMD Atlas from curated metadata and real local renders. |
| [scripts/build_goo_duet_sdf.py](../scripts/build_goo_duet_sdf.py) | Pinned duet face-SDF adaptation; isolated stills, no motion or physics edits. |
| [scripts/cache_mme_study_text.py](../scripts/cache_mme_study_text.py) | Privately decode author archive text; do not execute or redistribute effects. |
| [scripts/check_goo_rendered_shadow_aovs.py](../scripts/check_goo_rendered_shadow_aovs.py) | Verify actual shader texture sequence sampling using raw face UV/value AOVs. |
| [scripts/cinema_scene_probe.py](../scripts/cinema_scene_probe.py) | Read camera, lighting and motion controls without modifying the source file. |
| [scripts/clean_aksiniya_materials.py](../scripts/clean_aksiniya_materials.py) | Four reversible Aksiniya material modules for the pinned caption-fixed v7. |
| [scripts/clean_ikhor_materials.py](../scripts/clean_ikhor_materials.py) | Four reversible Ikhor-only NPR refinements for an unsaved pinned v7. |
| [scripts/compare_look_frames.py](../scripts/compare_look_frames.py) | Create an unretouched same-pose look comparison and a scene QA contact sheet. |
| [scripts/compare_mme_actor_stills.py](../scripts/compare_mme_actor_stills.py) | Build labelled equal-camera crops from our rendered stills for visual review. |
| [scripts/complete_goo_eye_hair_stage_preview.py](../scripts/complete_goo_eye_hair_stage_preview.py) | Wait for the existing orphaned render, then encode its completed native cache. |
| [scripts/complete_goo_tyndall_production.py](../scripts/complete_goo_tyndall_production.py) | Explicit volume light groups for the actual Goo direct-light packing path. |
| [scripts/composite_duet_official_captions.py](../scripts/composite_duet_official_captions.py) | Composite official caption groups onto native duet beauty/matte caches. |
| [scripts/configure_goo_portable.py](../scripts/configure_goo_portable.py) | Save only the dedicated Goo preferences, after a factory-startup bootstrap. |
| [scripts/create_studio_fixture.py](../scripts/create_studio_fixture.py) | Build original two-rig static test fixtures, not production MMD characters. |
| [scripts/diagnose_actor_light.py](../scripts/diagnose_actor_light.py) | Measure the actual unclipped native actor illumination and material classes. |
| [scripts/diagnose_goo_hair_shadow_toplight.py](../scripts/diagnose_goo_hair_shadow_toplight.py) | Read current shadow routing and render isolated glare/highlight/toplight controls. |
| [scripts/diagnose_goo_production_beams.py](../scripts/diagnose_goo_production_beams.py) | Separate geometry visibility and final compositing from direct volume rendering. |
| [scripts/diagnose_goo_volume_shader.py](../scripts/diagnose_goo_volume_shader.py) | Factory-only positive control for Goo direct volume light support. |
| [scripts/diagnose_opaque_hair.py](../scripts/diagnose_opaque_hair.py) | Compare opaque closures and isolate a silver-hair regression in fresh renders. |
| [scripts/diagnose_projected_eye_alpha.py](../scripts/diagnose_projected_eye_alpha.py) | Measure actual eye-peek, native head shadows and raw/final alpha response. |
| [scripts/duet_engine_benchmark.py](../scripts/duet_engine_benchmark.py) | Measure full-frame EEVEE variants without changing animation or source file. |
| [scripts/duet_region_probe.py](../scripts/duet_region_probe.py) | Compare native full and cropped renders before considering local revisions. |
| [scripts/duet_render_benchmark.py](../scripts/duet_render_benchmark.py) | Measure full-resolution animation cost before the full-song render. |
| [scripts/duet_source_preflight.py](../scripts/duet_source_preflight.py) | Read duet source data using the installed MMD Tools PMX/VMD readers. |
| [scripts/encode_review_cache.py](../scripts/encode_review_cache.py) | Encode native display-sRGB beauty caches with an explicit SDR color contract. |
| [scripts/export_linear_pipeline.py](../scripts/export_linear_pipeline.py) | Validate native RGBA layers, a signed interaction pass and linear archives. |
| [scripts/extract_tutorial_overlays.py](../scripts/extract_tutorial_overlays.py) | Read colored on-screen annotations from a local tutorial at sampled times. |
| [scripts/fetch_public_bilibili_study.py](../scripts/fetch_public_bilibili_study.py) | Retrieve normally accessible public tutorial metadata/media for private study. |
| [scripts/finalize_citlali_fringe_still.py](../scripts/finalize_citlali_fringe_still.py) | Combine the observed actor-specific fringe settings and render only stills. |
| [scripts/finalize_face_contract.py](../scripts/finalize_face_contract.py) | Fix the adapted Face Factor's incoming-vector contract in a new master. |
| [scripts/finalize_goo_character_lookdev.py](../scripts/finalize_goo_character_lookdev.py) | Finalize the pinned v3 character still and independently reopen it. |
| [scripts/finalize_goo_preview.py](../scripts/finalize_goo_preview.py) | Record a successfully encoded preview, without decoding or inspecting the output video. |
| [scripts/finalize_goo_toon_shadow_master.py](../scripts/finalize_goo_toon_shadow_master.py) | Relocate the baked shadow sequences without Blender remapping them to the source folder. |
| [scripts/finalize_goo_tyndall_look.py](../scripts/finalize_goo_tyndall_look.py) | Fix volume collection visibility and compress highlights with a fixed Reinhard shoulder. |
| [scripts/finalize_mme_light_hero_stills.py](../scripts/finalize_mme_light_hero_stills.py) | Protect original trim masks and compare restrained versus stronger diffusion. |
| [scripts/finish_goo_window_shafts.py](../scripts/finish_goo_window_shafts.py) | Remove broad air illumination and use a bounded constant-density control for shafts. |
| [scripts/finish_grounded_review.py](../scripts/finish_grounded_review.py) | Composite, encode and verify a bounded 300-frame duet SDR review. |
| [scripts/fit_reference_camera.py](../scripts/fit_reference_camera.py) | Match architectural texture features and estimate a research camera pose. |
| [scripts/fit_stage_grade.py](../scripts/fit_stage_grade.py) | Fit global, monotonic RGB grading curves from a stage render and reference. |
| [scripts/fix_goo_blended_eye_peek.py](../scripts/fix_goo_blended_eye_peek.py) | Remove the failed dark eye-region result and test smooth alpha-blended bangs. |
| [scripts/fix_goo_eye_peek_outline.py](../scripts/fix_goo_eye_peek_outline.py) | Fade the MMD inverted-hull outline together with the eye-occluding hair. |
| [scripts/fix_goo_eye_ray_and_shadow.py](../scripts/fix_goo_eye_ray_and_shadow.py) | Use world-space camera rays for eye peek and observable NPR shadow controls. |
| [scripts/fix_goo_window_shadow_pool.py](../scripts/fix_goo_window_shadow_pool.py) | Increase the inherited full shadow pool; keep the revision's art graph unchanged. |
| [scripts/frame_goo_window_shafts.py](../scripts/frame_goo_window_shafts.py) | Frame the rear shafts and keep their real shadow dividers outside the camera. |
| [scripts/genshin_character_probe.py](../scripts/genshin_character_probe.py) | Inventory actual duet material inputs before adapting game-style shading. |
| [scripts/genshin_library_probe.py](../scripts/genshin_library_probe.py) | Read festivities' downloaded node library without executing embedded code. |
| [scripts/genshin_material_adapt.py](../scripts/genshin_material_adapt.py) | Adapt downloaded shader components to the duet's actual MMD inputs. |
| [scripts/goo_runtime.py](../scripts/goo_runtime.py) | Initialize the isolated Goo 5.2 runtime, without changing global preferences. |
| [scripts/hesperides_camera_geometry.py](../scripts/hesperides_camera_geometry.py) | Render textured geometry or ray-cast feature positions for reference fitting. |
| [scripts/hesperides_reference_probe.py](../scripts/hesperides_reference_probe.py) | Read camera-ray intersections and render the world alone for sky diagnosis. |
| [scripts/hesperides_reference_rebuild.py](../scripts/hesperides_reference_rebuild.py) | Stage-only reconstruction of the supplied Ray preview; never run on a duet. |
| [scripts/ikhor_character_materials.py](../scripts/ikhor_character_materials.py) | Rebuild Ikhor's own NPR/material contract without touching motion or physics. |
| [scripts/ikhor_sleeve_repair_v1.py](../scripts/ikhor_sleeve_repair_v1.py) | Diagnose and isolate Ikhor's sleeve bake without rebuilding the entire rig. |
| [scripts/ingest_bilibili_subtitles.py](../scripts/ingest_bilibili_subtitles.py) | Normalize a legally saved Bilibili subtitle JSON, entirely offline. |
| [scripts/inspect_blender53_toon_package.py](../scripts/inspect_blender53_toon_package.py) | Read a pinned private toon package with scripts disabled; never render/save it. |
| [scripts/inspect_character_lookdev.py](../scripts/inspect_character_lookdev.py) | Read the fixed current Goo still before making isolated look-development copies. |
| [scripts/inspect_ikhor_hair_alignment.py](../scripts/inspect_ikhor_hair_alignment.py) | No module description; read source before use |
| [scripts/integrate_ikhor_wedding.py](../scripts/integrate_ikhor_wedding.py) | Replace the Hina slot with an independently baked Ikhor in a new hall copy. |
| [scripts/integrate_light_space.py](../scripts/integrate_light_space.py) | Repair fixture transforms and head axes, then connect bounded real shading. |
| [scripts/integrate_reference_duet.py](../scripts/integrate_reference_duet.py) | Integrate the tested hall and bounded character study; preserve animation. |
| [scripts/inventory_goo_basic_parameters.py](../scripts/inventory_goo_basic_parameters.py) | Capture actual Goo node parameters in an empty process; never open production. |
| [scripts/inventory_goo_features.py](../scripts/inventory_goo_features.py) | Inventory real shader RNA in an empty factory process, without loading production. |
| [scripts/knowledge_route.py](../scripts/knowledge_route.py) | Read task knowledge routes without importing production code or starting tools. |
| [scripts/learning_queue.py](../scripts/learning_queue.py) | Check and resume the MMD learning queue offline; never run experiments or fetch URLs. |
| [scripts/make_aether_look_review.py](../scripts/make_aether_look_review.py) | Arrange faithfully rendered before/after portraits for material review. |
| [scripts/make_aether_masks.py](../scripts/make_aether_masks.py) | Derive reviewed, Aether-specific artistic controls from supplied textures. |
| [scripts/make_clear_light_review.py](../scripts/make_clear_light_review.py) | Compare true same-camera renders and measure actor/background brightness. |
| [scripts/make_face_ink_review.py](../scripts/make_face_ink_review.py) | Build aspect-preserving crops from reference and actual A/B renders. |
| [scripts/make_portrait_quick_preview.py](../scripts/make_portrait_quick_preview.py) | Produce only one captioned 1080p five-second review; skip post-output QA. |
| [scripts/make_surface_masks.py](../scripts/make_surface_masks.py) | Create explicitly heuristic control maps from the model's actual atlases. |
| [scripts/migrate_duet_to_blender53.py](../scripts/migrate_duet_to_blender53.py) | Pinned Goo-to-native5.3 duet migration; audits and static-only conversion. |
| [scripts/migrate_goo_wedding.py](../scripts/migrate_goo_wedding.py) | Migrate the pinned daylight wedding to Goo, reusing the existing look and native Goo outputs. |
| [scripts/mmd_camera_check.py](../scripts/mmd_camera_check.py) | Import an authored camera VMD into an existing draft and audit sample frames. |
| [scripts/mmd_caption_probe.py](../scripts/mmd_caption_probe.py) | Inspect locally supported compositor matte and text-output APIs. |
| [scripts/mmd_caption_render.py](../scripts/mmd_caption_render.py) | Render aspect-specific picture and Cryptomatte sequences for typography. |
| [scripts/mmd_clear_light_revision.py](../scripts/mmd_clear_light_revision.py) | Relight the selected hall and create a controlled SDR toon finish. |
| [scripts/mmd_duet_finish.py](../scripts/mmd_duet_finish.py) | Build the full-song duet from portable physics and the selected existing hall. |
| [scripts/mmd_duet_layout_probe.py](../scripts/mmd_duet_layout_probe.py) | Import the assigned full duet and an authored camera for draft layout QA. |
| [scripts/mmd_duet_physics.py](../scripts/mmd_duet_physics.py) | Bake both performers' native physics for the full source choreography. |
| [scripts/mmd_duet_polish.py](../scripts/mmd_duet_polish.py) | Apply the user's brighter Ray-preview hall and Guanhaizi character direction. |
| [scripts/mmd_face_ink.py](../scripts/mmd_face_ink.py) | Selective facial strokes; source texture/UV/alpha and expression stay intact. |
| [scripts/mmd_final_scene.py](../scripts/mmd_final_scene.py) | Art direct the physics-baked Aksiniya project with pastel stage and NPR materials. |
| [scripts/mmd_first_scene.py](../scripts/mmd_first_scene.py) | Create a new, explicitly labeled PMX + VMD import draft in Blender. |
| [scripts/mmd_half_lambert.py](../scripts/mmd_half_lambert.py) | A named Half-Lambert response followed by per-material artistic gradients. |
| [scripts/mmd_hesperides_stage.py](../scripts/mmd_hesperides_stage.py) | Adapt Hesperides' supplied Ray texture controls to Blender and render QA. |
| [scripts/mmd_look_upgrade.py](../scripts/mmd_look_upgrade.py) | Rebuild the Aksiniya look on a portable baked scene, preserving MMD layers. |
| [scripts/mmd_outlines.py](../scripts/mmd_outlines.py) | Readable MMD inverse-hull ink, retaining model edge/vertex weights. |
| [scripts/mmd_physics_bake.py](../scripts/mmd_physics_bake.py) | Build PMX rigid bodies, simulate sequentially, and export portable pose keys. |
| [scripts/mmd_production_inspect.py](../scripts/mmd_production_inspect.py) | Print production-relevant material, rig, and physics facts inside Blender. |
| [scripts/mmd_production_qa.py](../scripts/mmd_production_qa.py) | Reopen verification and representative-frame QA for a baked production file. |
| [scripts/mmd_quality_lab.py](../scripts/mmd_quality_lab.py) | Isolate normal design, local AO, metallic trim and real volumetric light. |
| [scripts/mmd_quality_probe.py](../scripts/mmd_quality_probe.py) | Read local NPR/AO/normal/plugin compatibility before changing a scene. |
| [scripts/mmd_sample_pose.py](../scripts/mmd_sample_pose.py) | Export selected evaluated bone matrices for before/after integration checks. |
| [scripts/mmd_studio.py](../scripts/mmd_studio.py) | Read-only entry to studio knowledge, current scope, reference studies and learning. |
| [scripts/mmd_style_apply.py](../scripts/mmd_style_apply.py) | Apply a versioned NPR style to the validated local tutorial scene. |
| [scripts/mmd_surface_probe.py](../scripts/mmd_surface_probe.py) | Inspect actual source maps, material regions and head space for refinement. |
| [scripts/mmd_surface_refine.py](../scripts/mmd_surface_refine.py) | Model-adapted hair sheen, masked metal and restrained cloth/stage response. |
| [scripts/mmd_tutorial_lab.py](../scripts/mmd_tutorial_lab.py) | Validate selected toon-lighting, outline, glow and camera tutorial concepts. |
| [scripts/mmd_tutorial_probe.py](../scripts/mmd_tutorial_probe.py) | Read local Blender APIs needed by the tutorial lighting/outline lab. |
| [scripts/mux_production_audio.py](../scripts/mux_production_audio.py) | Mix a selected BGM segment into an existing video without rerendering. |
| [scripts/native53_runtime.py](../scripts/native53_runtime.py) | Register the isolated native5.3 MMD camera dependency before opening a project. |
| [scripts/ncm_convert.py](../scripts/ncm_convert.py) | Convert local NCM files with ncmdump; preserve native FLAC/MP3 by default. |
| [scripts/package_blue_gold_wedding.py](../scripts/package_blue_gold_wedding.py) | Package verified wedding lighting and blue/gold official typography. |
| [scripts/package_character_layers_review.py](../scripts/package_character_layers_review.py) | Register an actually rendered and reviewed character-layer study in Atlas. |
| [scripts/package_clean_game_duet.py](../scripts/package_clean_game_duet.py) | Validate and register only the completed clean-character, no-arc five seconds. |
| [scripts/package_duet_captions.py](../scripts/package_duet_captions.py) | Package the verified official-caption study and add its offline Atlas entry. |
| [scripts/package_duet_delivery.py](../scripts/package_duet_delivery.py) | Publish local delivery notes only after the full movie passes verification. |
| [scripts/package_face_ink.py](../scripts/package_face_ink.py) | Archive a verified eight-second face-ink refinement and its exact recipe. |
| [scripts/package_fox_cinema.py](../scripts/package_fox_cinema.py) | Publish only the verified five-second cinema study and its real comparisons. |
| [scripts/package_fox_stageart.py](../scripts/package_fox_stageart.py) | Archive and catalog the verified second fox lighting study. |
| [scripts/package_goo_daylight_v2.py](../scripts/package_goo_daylight_v2.py) | Package the v2 study and preservation evidence; finalize only after encoding. |
| [scripts/package_goo_eye_hair_stage.py](../scripts/package_goo_eye_hair_stage.py) | Finalize only an actually encoded eye/hair/stage sample; no MP4 decoding. |
| [scripts/package_goo_feature_study.py](../scripts/package_goo_feature_study.py) | Collect existing isolated research evidence; does not load Blender or production media. |
| [scripts/package_goo_rim_glow.py](../scripts/package_goo_rim_glow.py) | Finalize the actual encoded rim/glow review sample without post-output video QA. |
| [scripts/package_goo_tyndall_rim.py](../scripts/package_goo_tyndall_rim.py) | Register the finished actual encoded sample; never decode or watch output media. |
| [scripts/package_goo_window_wrap.py](../scripts/package_goo_window_wrap.py) | Record the user's revision request, or finalize the actual encoded window-wrap sample. |
| [scripts/package_goo_working_project.py](../scripts/package_goo_working_project.py) | Write local user launchers and migration facts; never claim video completion before encoding. |
| [scripts/package_grounded_review.py](../scripts/package_grounded_review.py) | Package the verified shadow/color review without replacing accepted baselines. |
| [scripts/package_ikhor_sleeve_review.py](../scripts/package_ikhor_sleeve_review.py) | Encode the diagnostic wrists and make explicitly sampled contact sheets. |
| [scripts/package_ikhor_wedding.py](../scripts/package_ikhor_wedding.py) | Register only the completed, hash-bound Aksiniya/Ikhor five-second review. |
| [scripts/package_portrait_relight.py](../scripts/package_portrait_relight.py) | Register the completed portrait still, never replacing the latest video. |
| [scripts/package_quality_upgrade.py](../scripts/package_quality_upgrade.py) | Publish a verified local quality revision into the reusable offline catalog. |
| [scripts/package_reference_transfer.py](../scripts/package_reference_transfer.py) | Register the completed bounded reference-transfer review, preserving history. |
| [scripts/package_soft_top_rim.py](../scripts/package_soft_top_rim.py) | Archive a verified soft-top/rim revision with actual lighting comparisons. |
| [scripts/package_stage_wuwa_study.py](../scripts/package_stage_wuwa_study.py) | Package original notes and rendered comparisons; preserve the accepted movie. |
| [scripts/package_style_suite.py](../scripts/package_style_suite.py) | Archive a completed six-package style study after actual media verification. |
| [scripts/package_surface_refinement.py](../scripts/package_surface_refinement.py) | Archive completed surface refinement media and the exact reviewed controls. |
| [scripts/place_goo_window_air_inside_hall.py](../scripts/place_goo_window_air_inside_hall.py) | Place actual scattering lights below the hall ceiling and remove volume linking ambiguity. |
| [scripts/portrait_day_sky.py](../scripts/portrait_day_sky.py) | Restore a blue/cyan procedural daytime World in the pinned duet copy. |
| [scripts/portrait_day_stage.py](../scripts/portrait_day_stage.py) | Reversible daylight base for the two audited Hesperides duet files. |
| [scripts/portrait_fur_control.py](../scripts/portrait_fur_control.py) | Original Normal/key fur palette on the pinned Clean v2 Aksiniya material. |
| [scripts/portrait_key_fill.py](../scripts/portrait_key_fill.py) | Reversible portrait key/fill and single-palette experiment for Clean v2. |
| [scripts/portrait_rim_ink.py](../scripts/portrait_rim_ink.py) | Reversible narrow warm rims and existing inverse-hull ink for Clean v2. |
| [scripts/prepare_aether_production.py](../scripts/prepare_aether_production.py) | Save the revised Aether scene as a fresh, explicitly recorded production file. |
| [scripts/prepare_blue_gold_wedding.py](../scripts/prepare_blue_gold_wedding.py) | Add wedding shafts, luminous aisle accents and isolated highlight halos. |
| [scripts/prepare_bold_wedding.py](../scripts/prepare_bold_wedding.py) | Create a fingerprint-bound, independently saved bold wedding-lighting revision. |
| [scripts/prepare_character_layers.py](../scripts/prepare_character_layers.py) | Unify one actor color/lighting/AO/highlight contract in an independent copy. |
| [scripts/prepare_clean_game_duet.py](../scripts/prepare_clean_game_duet.py) | Build a new, character-only clean NPR revision from the caption-fixed v7. |
| [scripts/prepare_duet_caption_lighting.py](../scripts/prepare_duet_caption_lighting.py) | Build responsive stage lighting and native matte/beauty caches for captions. |
| [scripts/prepare_goo_daylight_v2.py](../scripts/prepare_goo_daylight_v2.py) | Revise only the pinned Goo v1 copy after the MME lighting study. |
| [scripts/prepare_goo_eye_hair_stage.py](../scripts/prepare_goo_eye_hair_stage.py) | Build bounded eye animation, eye shading/peek, hair shadows and stage surfaces. |
| [scripts/prepare_goo_opaque_toon_v11.py](../scripts/prepare_goo_opaque_toon_v11.py) | Restore original opaque hair and add compact toon ramps with face shadow masks. |
| [scripts/prepare_goo_toon_face_hair_study.py](../scripts/prepare_goo_toon_face_hair_study.py) | Opaque hair, toon value ramps and geometry-derived face hair-shadow study. |
| [scripts/prepare_goo_tyndall_rim.py](../scripts/prepare_goo_tyndall_rim.py) | Continue the requested rim/glow revision with bounded shadowed window air. |
| [scripts/prepare_goo_window_wrap.py](../scripts/prepare_goo_window_wrap.py) | Replace the rejected narrow shafts with surveyed-window daylight and a stronger NPR rim. |
| [scripts/prepare_graphic_self_shadows.py](../scripts/prepare_graphic_self_shadows.py) | Refine native hull ink and connect readable geometric self-shadow to NPR. |
| [scripts/prepare_grounded_shadows.py](../scripts/prepare_grounded_shadows.py) | Restore visible cast/contact shadows and bounded actor self-shadow response. |
| [scripts/prepare_ikhor_motion.py](../scripts/prepare_ikhor_motion.py) | Import Ikhor's native Hina VMD and prepare a separately audited motion candidate. |
| [scripts/prepare_mme_reference_light_stills.py](../scripts/prepare_mme_reference_light_stills.py) | MME-inspired light/palette/diffusion adaptation; native Goo stills only. |
| [scripts/prepare_portrait_relight.py](../scripts/prepare_portrait_relight.py) | Build a new hash-bound portrait relight and render bounded stills only. |
| [scripts/prepare_quality_render.py](../scripts/prepare_quality_render.py) | Reopen the integrated master, validate scene persistence and archive naming. |
| [scripts/prepare_reference_transfer.py](../scripts/prepare_reference_transfer.py) | Port bounded NPR/light/material principles into a new Character Layers copy. |
| [scripts/prepare_soft_top_rim.py](../scripts/prepare_soft_top_rim.py) | Add broad soft fill, overhead illumination and a controlled rear rim. |
| [scripts/prepare_surface_motion.py](../scripts/prepare_surface_motion.py) | Extend the reviewed surface scene to an eight-second portrait camera study. |
| [scripts/probe_actor_ink_shadow.py](../scripts/probe_actor_ink_shadow.py) | Inspect the current actor hull and the preset's actual shadow sockets. |
| [scripts/probe_bold_wedding.py](../scripts/probe_bold_wedding.py) | Read-only inventory for the bounded bold-wedding lighting revision. |
| [scripts/probe_character_layer_contract.py](../scripts/probe_character_layer_contract.py) | Read live character shader paths without rendering or saving the source. |
| [scripts/probe_current_stage_surfaces.py](../scripts/probe_current_stage_surfaces.py) | Identify real stage surfaces by rays through the delivered camera. |
| [scripts/probe_face_direction.py](../scripts/probe_face_direction.py) | Compare Face Factor light-direction conventions in independent stills. |
| [scripts/probe_fox_stage.py](../scripts/probe_fox_stage.py) | Audit real ground surfaces, existing light linking and compositor routing. |
| [scripts/probe_goo_addon_functions.py](../scripts/probe_goo_addon_functions.py) | Exercise selected add-on operations in a disposable Goo scene, without rendering. |
| [scripts/probe_goo_daylight.py](../scripts/probe_goo_daylight.py) | Read-only light, material and sky inventory for the next Goo study. |
| [scripts/probe_goo_migration.py](../scripts/probe_goo_migration.py) | Read-only Goo runtime/add-on and project compatibility probe; no preferences saved. |
| [scripts/probe_goo_shadow_budget.py](../scripts/probe_goo_shadow_budget.py) | Read the current build's actual shadow budget controls. |
| [scripts/probe_goo_sun_direction.py](../scripts/probe_goo_sun_direction.py) | Find architectural openings from the performance floor by geometric rays. |
| [scripts/probe_goo_volume_visibility.py](../scripts/probe_goo_volume_visibility.py) | Read actual volume toggles and view-layer visibility without rendering or saving. |
| [scripts/probe_goo_window_wrap.py](../scripts/probe_goo_window_wrap.py) | Read real window mesh islands and existing hair/rim controls, without rendering. |
| [scripts/probe_ikhor_caption_matte.py](../scripts/probe_ikhor_caption_matte.py) | Read-only inventory of the active caption matte graph and PNG coverage. |
| [scripts/probe_ikhor_hair_morphs.py](../scripts/probe_ikhor_hair_morphs.py) | No module description; read source before use |
| [scripts/probe_jelly_eye_compatibility.py](../scripts/probe_jelly_eye_compatibility.py) | Exercise the user's privately cached add-on without installing preferences. |
| [scripts/probe_mme_reference_relight.py](../scripts/probe_mme_reference_relight.py) | No module description; read source before use |
| [scripts/probe_shadow_grounding.py](../scripts/probe_shadow_grounding.py) | Read actual light, material, foot and floor data before grounding changes. |
| [scripts/probe_stage_focal_targets.py](../scripts/probe_stage_focal_targets.py) | Locate actual rendered surfaces under image-space lighting targets. |
| [scripts/probe_toon_hair_routes.py](../scripts/probe_toon_hair_routes.py) | No module description; read source before use |
| [scripts/quality_layer_capability.py](../scripts/quality_layer_capability.py) | Small native EEVEE test for sky suppression and collection holdout. |
| [scripts/quality_pipeline_probe.py](../scripts/quality_pipeline_probe.py) | Audit current light/shader/layer capabilities without saving the source blend. |
| [scripts/raise_goo_toon_shadow_budget.py](../scripts/raise_goo_toon_shadow_budget.py) | Increase only the inherited shadow memory budget and preflight peak frames. |
| [scripts/read_goo_official_basics.py](../scripts/read_goo_official_basics.py) | Cache selected official Goo source files privately for parameter study. |
| [scripts/record_citlali_fringe_stills.py](../scripts/record_citlali_fringe_stills.py) | Record completed warm-fringe stills and the user's standing still-only policy. |
| [scripts/record_goo_blender_foundations.py](../scripts/record_goo_blender_foundations.py) | Record the bounded input/display experiments and official reading, not production gains. |
| [scripts/record_goo_foundation_study.py](../scripts/record_goo_foundation_study.py) | Record actual Goo foundation reading and isolated controls, not full mastery. |
| [scripts/record_goo_reference_normal_study.py](../scripts/record_goo_reference_normal_study.py) | Record reference observations and the bounded Normal-input experiment. |
| [scripts/record_goo_toon_candidate.py](../scripts/record_goo_toon_candidate.py) | Record the verified opaque-toon candidate without claiming a new video exists. |
| [scripts/record_ikhor_brightness_v6.py](../scripts/record_ikhor_brightness_v6.py) | Record the second user-requested Ikhor brightness reduction, stills only. |
| [scripts/record_ikhor_hair_still.py](../scripts/record_ikhor_hair_still.py) | Publish only completed stills; retain the old video as rejected hair alignment history. |
| [scripts/record_mme_balanced_stills.py](../scripts/record_mme_balanced_stills.py) | Record the observed overbright feedback and bounded still correction. |
| [scripts/record_mme_reference_light_stills.py](../scripts/record_mme_reference_light_stills.py) | Publish the observed native-Goo MME-inspired still candidate; never encode video. |
| [scripts/record_repository_organization.py](../scripts/record_repository_organization.py) | Record organization and route research; never execute or modify a scene. |
| [scripts/reference_study.py](../scripts/reference_study.py) | Prepare local reference evidence, separate observations from hypotheses, and build a design brief. |
| [scripts/refine_goo_character_lookdev.py](../scripts/refine_goo_character_lookdev.py) | Fixed-v6, reversible character look development. Static 4290 only; no video. |
| [scripts/refine_goo_opaque_toon.py](../scripts/refine_goo_opaque_toon.py) | Repair legacy ramp insertion and refine the face-shadow footprint. |
| [scripts/refine_goo_tyndall_visibility.py](../scripts/refine_goo_tyndall_visibility.py) | Make the requested window shafts readable with explicit art-directed light linking. |
| [scripts/refine_ikhor_skin.py](../scripts/refine_ikhor_skin.py) | Compare a bounded skin-shadow calibration and save only a new review copy. |
| [scripts/refine_mme_reference_light_stills.py](../scripts/refine_mme_reference_light_stills.py) | Remove failed global grading; retain restrained light and material changes. |
| [scripts/refine_reference_duet.py](../scripts/refine_reference_duet.py) | Refine the NPC SDF mapping and shadow cost before the 5-second render. |
| [scripts/remove_wedding_arcs.py](../scripts/remove_wedding_arcs.py) | Hide the two user-rejected wedding light arcs in a new saved revision. |
| [scripts/render_blender53_author_face_controls.py](../scripts/render_blender53_author_face_controls.py) | Pinned author-Furina diagnostic stills, primary face SDF on/off; never save blend. |
| [scripts/render_camera_preview.py](../scripts/render_camera_preview.py) | Render the open draft's frame range as a small, silent H.264 camera preview. |
| [scripts/render_character_layer_controls.py](../scripts/render_character_layer_controls.py) | Render bounded same-frame layer ablations without saving the production file. |
| [scripts/render_clean_game_controls.py](../scripts/render_clean_game_controls.py) | Unblurred, same-pose material controls; never save the production scene. |
| [scripts/render_duet_chunk.py](../scripts/render_duet_chunk.py) | Render one recoverable production chunk and expose progress as JSON. |
| [scripts/render_duet_full.py](../scripts/render_duet_full.py) | Render full-song chunks, validate/join them, mux selected FLAC, then verify. |
| [scripts/render_duet_sample.py](../scripts/render_duet_sample.py) | Render a bounded duet review clip, reuse verified matching chunks, and verify. |
| [scripts/render_ikhor_duet_matte.py](../scripts/render_ikhor_duet_matte.py) | Render native duet Cryptomatte and Alpha from pinned v6/v7, without saving. |
| [scripts/render_ikhor_sleeve_review.py](../scripts/render_ikhor_sleeve_review.py) | Render both wrists continuously from a saved, portable repair candidate. |
| [scripts/render_portrait_light_controls.py](../scripts/render_portrait_light_controls.py) | Render three fingerprint-bound portrait controls without saving a blend. |
| [scripts/render_portrait_quick_cache.py](../scripts/render_portrait_quick_cache.py) | Render the saved portrait look directly to new caption caches; no QA pass. |
| [scripts/render_production.py](../scripts/render_production.py) | Render a saved production project to a new H.264 picture master. |
| [scripts/render_reference_transfer_controls.py](../scripts/render_reference_transfer_controls.py) | Render same-frame ablations of the new reference transfer without saving. |
| [scripts/render_saved_portrait.py](../scripts/render_saved_portrait.py) | Render the saved portrait candidate in a fresh process without rebuilding it. |
| [scripts/render_shader_diagnostics.py](../scripts/render_shader_diagnostics.py) | Render three controlled motion probes on an unsaved independent scene copy. |
| [scripts/render_style_suite.ps1](../scripts/render_style_suite.ps1) | Source or configuration; read before use |
| [scripts/render_sunlit_floor_study.py](../scripts/render_sunlit_floor_study.py) | Temporary full-body framing to make the requested floor shadows visible. |
| [scripts/reopen_goo_basic_light_groups.py](../scripts/reopen_goo_basic_light_groups.py) | Independently reopen the basic experiment and compare its linear pixels. |
| [scripts/reopen_goo_feature_study.py](../scripts/reopen_goo_feature_study.py) | Reopen one isolated study blend and compare its linear render; no production input. |
| [scripts/repair_duet_caption_targets.py](../scripts/repair_duet_caption_targets.py) | Repair stale character names in the caption-only Cryptomatte selection. |
| [scripts/repair_ikhor_hair_alignment.py](../scripts/repair_ikhor_hair_alignment.py) | Isolate baked hair translation errors; render still-only controls. |
| [scripts/repair_quality_archive_frame.py](../scripts/repair_quality_archive_frame.py) | Rerender an explicitly requested master frame and its native linear archive. |
| [scripts/repository_index.py](../scripts/repository_index.py) | Index repository files without importing or executing production scripts. |
| [scripts/restrain_ikhor_mme_still.py](../scripts/restrain_ikhor_mme_still.py) | Reduce Ikhor's added palette gain without changing Aksiniya or global exposure. |
| [scripts/review_face_ink.py](../scripts/review_face_ink.py) | Same-camera face ink comparison and face-shell ablation renders. |
| [scripts/review_hesperides_reference.py](../scripts/review_hesperides_reference.py) | Package actual stage renders into labeled reference and switch comparisons. |
| [scripts/review_hesperides_stage.py](../scripts/review_hesperides_stage.py) | Create a labeled stage comparison and compare independent reopen renders. |
| [scripts/review_ikhor_sleeve_controls.py](../scripts/review_ikhor_sleeve_controls.py) | Render unsaved, unblurred wrist geometry controls with the production shader. |
| [scripts/review_reference_transfer.py](../scripts/review_reference_transfer.py) | Measure real native ablations and package same-frame comparison images. |
| [scripts/review_shader_diagnostics.py](../scripts/review_shader_diagnostics.py) | Create visual inspection sheets and motion-compensated face-change metrics. |
| [scripts/review_style_presets.py](../scripts/review_style_presets.py) | Build same-pose style matrices from actual Blender beauty/matte outputs. |
| [scripts/review_tutorial_study.py](../scripts/review_tutorial_study.py) | Decode the four-second tutorial study and lay out unretouched comparisons. |
| [scripts/review_video_color.py](../scripts/review_video_color.py) | Explicit SDR desktop-review color contract for sRGB compositor pixels. |
| [scripts/revise_goo_projected_eye_shadow.py](../scripts/revise_goo_projected_eye_shadow.py) | Correct eye peek in camera space and establish a directional head-light response. |
| [scripts/revise_goo_rim_glow.py](../scripts/revise_goo_rim_glow.py) | Inspect or revise the pinned Goo v2 light response in a new output directory. |
| [scripts/run_goo_daylight_v2_preview.py](../scripts/run_goo_daylight_v2_preview.py) | One-shot Goo daylight v2 captioned sample entry. |
| [scripts/run_goo_eye_hair_stage_preview.py](../scripts/run_goo_eye_hair_stage_preview.py) | Render the saved eye/hair/stage revision as one captioned original-vocal sample. |
| [scripts/run_goo_rim_glow_preview.py](../scripts/run_goo_rim_glow_preview.py) | Render the saved rim/highlight/glow revision as one captioned five-second sample. |
| [scripts/run_goo_tyndall_rim_preview.py](../scripts/run_goo_tyndall_rim_preview.py) | Render the final window-air / white-blue rim look from its saved Goo master. |
| [scripts/run_goo_wedding_preview.py](../scripts/run_goo_wedding_preview.py) | Explicit one-shot entry: Goo 1080p30, five seconds, captions and original vocal audio. |
| [scripts/run_goo_window_wrap_preview.py](../scripts/run_goo_window_wrap_preview.py) | Render the broad-window, stronger-rim revision from the saved Goo master. |
| [scripts/save_ikhor_aligned_hair_still.py](../scripts/save_ikhor_aligned_hair_still.py) | Restore original hair bind pose in a still-only, independently saved project. |
| [scripts/snapshot_goo_scene.py](../scripts/snapshot_goo_scene.py) | Compact migration evidence: complete curve data/geometry and sampled evaluated poses. |
| [scripts/stable_caption_layers.py](../scripts/stable_caption_layers.py) | Whole-group caption compositing with explicit layer order and continuous masks. |
| [scripts/stage_night_art_lab.py](../scripts/stage_night_art_lab.py) | Test moonlight, localized warmth and thin volume on a separate duet copy. |
| [scripts/studio_bench.py](../scripts/studio_bench.py) | Opt-in, bounded Blender scene benchmark launcher (stdlib only). |
| [scripts/studio_iteration.py](../scripts/studio_iteration.py) | Explicit, bounded reference experiments; no visual judgments are inferred. |
| [scripts/studio_lessons.py](../scripts/studio_lessons.py) | Explicit registration and integrity-checked retrieval of single-case lessons. |
| [scripts/studio_publish.py](../scripts/studio_publish.py) | Explicit isolated candidate publication and independent reopen launcher (stdlib). |
| [scripts/studio_publish_worker.py](../scripts/studio_publish_worker.py) | Pinned Blender worker for a new, bounded still candidate and its reopen. |
| [scripts/studio_registry.py](../scripts/studio_registry.py) | Read-only studio evidence registry. Structural checks are not art approval. |
| [scripts/studio_review_board.py](../scripts/studio_review_board.py) | Offline, pinned iteration review boards; never records visual approval. |
| [scripts/studio_scene_contract.py](../scripts/studio_scene_contract.py) | Read-only bounded scene benchmark contract (stdlib only). |
| [scripts/studio_scene_worker.py](../scripts/studio_scene_worker.py) | Blender-only isolated scene inspection and explicitly mapped static controls. |
| [scripts/studio_tasks.py](../scripts/studio_tasks.py) | Planning-only model recommendations and bounded task packets (stdlib only). |
| [scripts/study_cinema_reference.py](../scripts/study_cinema_reference.py) | Extract targeted full frames and consecutive bursts from a supplied reference. |
| [scripts/study_citlali_fringe_shadow.py](../scripts/study_citlali_fringe_shadow.py) | Still-only narrow warm hair contact-shadow study from the supplied reference. |
| [scripts/study_goo_basic_light_groups.py](../scripts/study_goo_basic_light_groups.py) | Test the basic one-key-per-group rule in isolated spheres, not production. |
| [scripts/study_goo_color_basics.py](../scripts/study_goo_color_basics.py) | Save fixed linear patches through existing Goo display transforms, without rendering. |
| [scripts/study_goo_daylight_v2.py](../scripts/study_goo_daylight_v2.py) | Render the saved v2 opening frame and a full-body lighting diagnostic. |
| [scripts/study_goo_feature_mechanisms.py](../scripts/study_goo_feature_mechanisms.py) | Isolated Goo mechanism experiments; never load or edit a production project. |
| [scripts/study_goo_info_input_matrix.py](../scripts/study_goo_info_input_matrix.py) | Compare actual Shader Info inputs across existing Goo builds in empty scenes. |
| [scripts/study_goo_mesh_normal_foundations.py](../scripts/study_goo_mesh_normal_foundations.py) | Bounded Blender/Goo foundation controls in factory scenes; never load production. |
| [scripts/study_goo_nodes.py](../scripts/study_goo_nodes.py) | Render a small actual Goo shader/light-group study, separate from production. |
| [scripts/study_goo_normal_input_basics.py](../scripts/study_goo_normal_input_basics.py) | Check Shader Info Normal input against explicit normal-dot-light controls. |
| [scripts/study_goo_window_visibility.py](../scripts/study_goo_window_visibility.py) | Diagnose actual exterior-sun visibility on the saved floor only; never save. |
| [scripts/study_jelly_eye_inputs.py](../scripts/study_jelly_eye_inputs.py) | Inventory the saved duet's eye geometry and shading without modifying it. |
| [scripts/study_reference_sequences.py](../scripts/study_reference_sequences.py) | Sample multi-second reference sequences for temporal art-direction review. |
| [scripts/style_post.py](../scripts/style_post.py) | Aspect-aware graphic post effects using real Blender character mattes. |
| [scripts/style_presets.py](../scripts/style_presets.py) | Load independent render, post and aspect-specific direction recipes. |
| [scripts/transcribe_tutorial.py](../scripts/transcribe_tutorial.py) | Create a private, timestamped ASR study draft from local tutorial media. |
| [scripts/transfer_material_response.py](../scripts/transfer_material_response.py) | Opt-in material controls for the audited Character Layers production-v2. |
| [scripts/typography_composite.py](../scripts/typography_composite.py) | Composite native-aspect typography with cue-specific front/back placement. |
| [scripts/validate_chest_secondary_motion.py](../scripts/validate_chest_secondary_motion.py) | Audit anatomical chest support in source PMX and current baked motion. |
| [scripts/verify_audio_blender.py](../scripts/verify_audio_blender.py) | Decode the finished MP4 audio using Blender's Audaspace/FFmpeg runtime. |
| [scripts/verify_caption_master.py](../scripts/verify_caption_master.py) | Reopen the focused-light master and verify motion and cache isolation. |
| [scripts/verify_character_diagnostics.py](../scripts/verify_character_diagnostics.py) | Decode bounded three-axis tests and export face strips for honest visual QA. |
| [scripts/verify_character_layer_master.py](../scripts/verify_character_layer_master.py) | Read-only native audit of a source and rebuilt character-layer master. |
| [scripts/verify_clean_caption_coverage.py](../scripts/verify_clean_caption_coverage.py) | Check current actor PNGs at SHA-bound, inherited identical-camera/pose ROIs. |
| [scripts/verify_clean_game_duet.py](../scripts/verify_clean_game_duet.py) | Read-only independent audit of the pinned v7 character-material refinement. |
| [scripts/verify_duet_caption_targets.py](../scripts/verify_duet_caption_targets.py) | Read-only, static v6-to-v7 audit of a caption-only Cryptomatte target fix. |
| [scripts/verify_duet_integration.py](../scripts/verify_duet_integration.py) | Compare both baked skeletons and authored camera across the time transform. |
| [scripts/verify_gallery.py](../scripts/verify_gallery.py) | Exercise the delivered gallery through a fresh, headless system Chrome. |
| [scripts/verify_goo_eye_hair_stage.py](../scripts/verify_goo_eye_hair_stage.py) | Reopen and verify bounded eye geometry, preserved motion and saved shader routes. |
| [scripts/verify_goo_tyndall_master.py](../scripts/verify_goo_tyndall_master.py) | Independently reopen the master and compare original motion/geometry, never video QA. |
| [scripts/verify_goo_window_wrap.py](../scripts/verify_goo_window_wrap.py) | Independently reopen the saved window-wrap master; no output-video QA. |
| [scripts/verify_hesperides_reference.py](../scripts/verify_hesperides_reference.py) | Reopen the independent hall study, verify switches/packing, and re-render. |
| [scripts/verify_ikhor_sleeve_repair.py](../scripts/verify_ikhor_sleeve_repair.py) | Read-only delta audit: v4 versus eight sleeve bones and one fixed corrective. |
| [scripts/verify_ikhor_wedding.py](../scripts/verify_ikhor_wedding.py) | Independently reopen the bounded Aksiniya/Ikhor integration; never render/save. |
| [scripts/verify_light_space_repairs.py](../scripts/verify_light_space_repairs.py) | Native regression check of reusable head-axis and stage-import repairs. |
| [scripts/verify_linear_archive.py](../scripts/verify_linear_archive.py) | Verify numbered multipart EXRs and independently decode their color data. |
| [scripts/verify_portrait_relight.py](../scripts/verify_portrait_relight.py) | Read-only CPU reopen audit of a Clean-v2 portrait-relight still project. |
| [scripts/verify_reference_transfer.py](../scripts/verify_reference_transfer.py) | Independently reopen and audit the bounded reference transfer; never render/save. |
| [scripts/verify_render_seams.py](../scripts/verify_render_seams.py) | Inspect decoded frames around known render boundaries for visible jumps. |
| [scripts/verify_review_color.py](../scripts/verify_review_color.py) | Require explicit decoded SDR review metadata, including after audio muxing. |
| [scripts/verify_stageart_master.py](../scripts/verify_stageart_master.py) | Reopen a stage-art master and verify motion, output isolation and ground scope. |
| [scripts/verify_video.py](../scripts/verify_video.py) | Decode every output frame; verify timing, image dimensions, and MP4 streams. |
| [scripts/video_reference_frames.py](../scripts/video_reference_frames.py) | Extract timestamped local reference frames and a contact sheet (OpenCV/Pillow). |
| [scripts/wuwa_hair_input_lab.py](../scripts/wuwa_hair_input_lab.py) | Render the user's WuWa hair example and controlled HM/HN input removals. |

## site（4）

| 文件 | 用途 |
| --- | --- |
| [site/DESIGN.md](../site/DESIGN.md) | 帧间 · FRAME ATELIER |
| [site/app.js](../site/app.js) | Source or configuration; read before use |
| [site/index.html](../site/index.html) | Source or configuration; read before use |
| [site/styles.css](../site/styles.css) | Source or configuration; read before use |

## skills（8）

| 文件 | 用途 |
| --- | --- |
| [skills/blender-setup/SKILL.md](../skills/blender-setup/SKILL.md) | Blender 環境準備 |
| [skills/mmd-camera-search/SKILL.md](../skills/mmd-camera-search/SKILL.md) | 镜头 VMD 检索与验收 |
| [skills/mmd-finish-render/SKILL.md](../skills/mmd-finish-render/SKILL.md) | 从导入工程推进到成片 |
| [skills/mmd-model-check/SKILL.md](../skills/mmd-model-check/SKILL.md) | MMD 模型檢查 |
| [skills/mmd-studio/SKILL.md](../skills/mmd-studio/SKILL.md) | 接手与成长 |
| [skills/mmd-video-reference/SKILL.md](../skills/mmd-video-reference/SKILL.md) | MMD 參考影片工作流程 |
| [skills/troubleshooting/SKILL.md](../skills/troubleshooting/SKILL.md) | MMD 故障排除 |
| [skills/vmd-workflow/SKILL.md](../skills/vmd-workflow/SKILL.md) | VMD 工作流程 |

## tests（33）

| 文件 | 用途 |
| --- | --- |
| [tests/__init__.py](../tests/__init__.py) | Unit tests for the local Blender preparation helpers. |
| [tests/test_auto_qc.py](../tests/test_auto_qc.py) | Tests for automated QC hard metrics, sparse multiframe, temporal flicker and calibration. |
| [tests/test_blender_detect.py](../tests/test_blender_detect.py) | No module description; read source before use |
| [tests/test_blender_download.py](../tests/test_blender_download.py) | No module description; read source before use |
| [tests/test_blender_install.py](../tests/test_blender_install.py) | No module description; read source before use |
| [tests/test_blender_inventory.py](../tests/test_blender_inventory.py) | Ensure reading plugin metadata never executes plugin source. |
| [tests/test_blender_validate.py](../tests/test_blender_validate.py) | No module description; read source before use |
| [tests/test_bowlroll_public_download.py](../tests/test_bowlroll_public_download.py) | Test access restrictions and archive boundaries without external requests. |
| [tests/test_knowledge_registry.py](../tests/test_knowledge_registry.py) | Protect current art feedback and portable research links from regressions. |
| [tests/test_knowledge_route.py](../tests/test_knowledge_route.py) | Keep task navigation scoped and prevent stale or executable-looking references. |
| [tests/test_learning_queue.py](../tests/test_learning_queue.py) | Protect deduplication, bounded resumption and evidence-based stage claims. |
| [tests/test_mmd_studio.py](../tests/test_mmd_studio.py) | Integration contracts for current context, evidence and read-only studio entry. |
| [tests/test_ncm_convert.py](../tests/test_ncm_convert.py) | Protect original music and reject ambiguous or invalid conversion outputs. |
| [tests/test_reference_study.py](../tests/test_reference_study.py) | Reference preparation must not fabricate inspection, causal proof, or approval. |
| [tests/test_render_chunks.py](../tests/test_render_chunks.py) | Catch dropped/duplicated frame ranges before concatenating a long render. |
| [tests/test_repository_index.py](../tests/test_repository_index.py) | Check that navigation covers files and never executes scanned Python. |
| [tests/test_review_video_color.py](../tests/test_review_video_color.py) | Exercise the actual encoder/filter/mux path that previously lost color tags. |
| [tests/test_stable_caption_layers.py](../tests/test_stable_caption_layers.py) | Regression cases for the reported split-order and black-letter cutout issues. |
| [tests/test_studio_bench.py](../tests/test_studio_bench.py) | No module description; read source before use |
| [tests/test_studio_iteration.py](../tests/test_studio_iteration.py) | Bounded iteration adversarial checks; no Blender process is started. |
| [tests/test_studio_lessons.py](../tests/test_studio_lessons.py) | No module description; read source before use |
| [tests/test_studio_publish.py](../tests/test_studio_publish.py) | Publication launcher isolation and provenance tests, without Blender. |
| [tests/test_studio_publish_worker.py](../tests/test_studio_publish_worker.py) | Pure worker guard checks; these do not establish Blender artwork quality. |
| [tests/test_studio_registry.py](../tests/test_studio_registry.py) | No module description; read source before use |
| [tests/test_studio_review_board.py](../tests/test_studio_review_board.py) | No module description; read source before use |
| [tests/test_studio_scene_contract.py](../tests/test_studio_scene_contract.py) | No module description; read source before use |
| [tests/test_studio_scene_worker.py](../tests/test_studio_scene_worker.py) | Pure-Python checks for worker guards; real Blender cases are separate evidence. |
| [tests/test_studio_tasks.py](../tests/test_studio_tasks.py) | No module description; read source before use |
| [tests/test_style_presets.py](../tests/test_style_presets.py) | No module description; read source before use |
| [tests/test_subtitle_ingest.py](../tests/test_subtitle_ingest.py) | Synthetic-only checks; these do not validate any real Bilibili transcript. |
| [tests/test_surface_masks.py](../tests/test_surface_masks.py) | No module description; read source before use |
| [tests/test_typography_composite.py](../tests/test_typography_composite.py) | Keep the editorial front/behind choice distinct from protection policies. |
| [tests/test_video_verification.py](../tests/test_video_verification.py) | Exercise MP4 stream inspection independently of Blender and video encoding. |
