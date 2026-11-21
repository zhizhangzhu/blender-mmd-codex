# 制作目标与仓库工作约定

## 阅读入口

- 长期建设与制作遵守根目录`SPEC.md`；接手、技术学习、参考理解与多模型协作先读`skills/mmd-studio/SKILL.md`。用`python -m scripts.mmd_studio context --task reference --query "问题"`取相关经验；默认只读，不启动生产。
- 需要实际角色映射与静帧对照读`docs/STUDIO_SCENE_BENCH.md`，用`mmd_studio benches`选择有界配置；`studio_bench`显式执行。每case重开、不保存源、拒绝活动模拟；原创代理夹具只验证工具，不当MMD美术或迁移完成证据。
- 称呼用户「猪猪」，GitHub `zhizhangzhu`。源码在 `D:/codex/workspace/`，交付在 `D:/codex/output/`，临时与私人第三方缓存在 `D:/codex/temp/`。
- 先读 README、`catalog/current_state.json`与`docs/AI_TASK_PLAYBOOK.md`。再按任务读`docs/PRODUCTION_WORKFLOW.md`、对应主手册和`docs/LOCAL_ENVIRONMENT.md`；检索更多资料用`docs/KNOWLEDGE_INDEX.md`，找工具再读`scripts/README.md`与`docs/TOOL_AND_PRESET_MAP.md`，不默认全量读取历史。
- 接具体任务按`docs/AI_TASK_PLAYBOOK.md`／`catalog/task_routes.json`选择模型驱动、动作/K帧、卡渲、特效、舞台、布光或设计路线；`python -m scripts.knowledge_route --task lighting`只读查询。先读相关主手册与案例，再核脚本输入契约，不从全文件列表猜执行链。
- 视觉迭代先用`docs/DESIGN_FOUNDATIONS_AND_REVIEW.md`明确焦点、情绪、明暗/色彩、舞台与效果职责；动作修订用`docs/ANIMATION_AND_KEYFRAMING_PLAYBOOK.md`先排除输入/绑定/求值问题，再决定局部K帧。设计简报可按`presets/templates/iteration-brief-v1.json`选填，不增加重复许可流程。
- `current_state.json`是唯一现行状态；G0–G8关卡见`catalog/production_pipeline.json`与`docs/QUALITY_GATES.md`。旧文档的“最新”只对应当时日期。
- 目标是逐步达到原神／鸣潮式三渲二感知质量；观海子优先，Gosari542保留，御手洗板蓝根补充。当前尚未达标，插件存在、技术通过和用户美术认可分开。
- 成片请求使用`skills/mmd-finish-render/SKILL.md`；相机检索使用`skills/mmd-camera-search/SKILL.md`。历史脚本可运行不等于应重跑旧生产流程。
- 猪猪偏好（2026-11-18）：指挥、方案、技术判断、官方资料学习和最终验收优先由 `gpt-6.1-sol` 的 `xhigh` 推理档亲自完成；`gpt-6.1-sol low` 仅承担步骤已明确的简单执行，不代替学习或复杂判断。可指定子代理模型与推理档位，不声称能在对话中切换主聊天模型；无需修改用户全局配置。
- 猪猪补充（2026-11-22）：当前会话使用 Claude Opus 5.5 时，主控（指挥、方案、技术判断、学习与验收）由其 `high` 推理档负责，`low` 档仅做步骤已明确的简单执行；当前会话使用 Gemini 4 Neon 时同样由其 `high` 档主控、`low` 档仅做步骤已明确的简单执行。GPT 会话仍按上条 `xhigh`／`low`。
- 2026-11-20长期分工落实：角色偏好在`catalog/model_policy.json`；低档任务须有输入指纹说明、写路径、产物、验收和升级条件，探索／设计／复杂学习交高推理主控。任务包推荐不等于真实派发；实际工具运行、模型与费用如实记录，未知留空。能力／偏好／课程见`catalog/studio.json`，参考观察／假设／目标见`catalog/reference_studies/`，不以结构检查通过晋升美术或迁移能力。

## 当前范围

- 猪猪2026-11-20明确要求继续在当前GooEngine优化双人渲染与舞台。本任务使用`goo-v1`独立副本，覆盖下述5.3默认试作选择的本任务范围；829f冻结源仍只读保留。当前进展读`current_state.goo_artdirection_request`及`docs/GOO_DUET_ARTDIRECTION_2026_11_20.md`，不要因旧“等待评价”停止已授权开发或在失败保存目录冒称新候选完成。

- **2026-11-17起默认只生成静帧／对照图；只有猪猪明确要求视频时才生成片段或全曲。** 旧五秒默认输出约定已被覆盖。
- 当前候选：`D:/codex/output/Goo-Duet-ArtDirection-2026-11-20/final-v3/Candidate.blend`，SHA `fad1fdf5877bec468d1b8d357f9b3dcd8c81b61bda053b86eea2f06cdcd6af8b`，见`docs/GOO_DUET_ARTDIRECTION_2026_11_20.md`。仅4290／1080p64／SourceDOF，完整保护和独立重开PNG阈值通过；用户美术待评。后续检视用`presets/benches/goo-duet-artdirection-candidate-v1.json`，其中expected是保存后的值，不能重复套用原源的配方。原829f及旧5c诊断均保留，无新视频或物理。
- 猪猪2026-11-19的冻结与试作决定（当前Goo任务例外见上）：冻结保留原Goo源工程，SHA `829f2d88827320c48a19ed76df4dc70af495455e4a660769c2bb53fe461caa69`；后续新试作默认使用官方Blender5.3独立副本。人物套用5.3作者shader节点，舞台、相机、动作、灯光与合成复刻Goo源工程；不自动恢复视频、新物理或眼透。下列Goo配置亦用于本轮明确要求的Goo优化。
- Goo配置为`presets/runtime/goo-v1.json`：5.2.1非官方社区移植版、构建0051aee03764。先用`scripts/goo_runtime.py`注册便携插件再打开，仅用独立CONFIG，不改用户偏好。Goo4.3不能读取当前5.2工程，不降级生产文件。
- **眼透已搁置，额外刘海透明关闭。字幕保留黑边和投影。** 伊科尔错误发骨烘焙造成持续错位，现静帧恢复绑定发型；不能称新的头发动态通过。

## 素材与项目

- 阿克西妮娅→Full HimeTanaka、伊科尔→Full HinaSuzuki；横屏16:9，空为历史角色。两人材质／表情分别映射，保留原生相对站位、既有とっとこ相机；暂缓全曲运镜校正。
- 素材根`E:/tools/franken`，优先PMX＋原生VMD；FBX另查骨架／重定向。换动作不能复用旧角色或旧动作的物理烘焙。
- 保留paierer「赫斯珀利德斯之馆-礼堂」，主题雪＋婚礼＋爱，不主动换原创舞台。Aiko宮殿禁止Blender成片，排除；雪韵仙庭等级限制不绕过。
- BGM固定`D:/codex/output/Franken-Duet-Full-Audio-v1/HIMEHINA - フランケンシュタインの怪物.flac`，198.3158125秒、96kHz／24bit双声道；不得换伴奏／MP3。加入音轨不等于卡点完成。
- 新素材优先作者配布、BowlRoll、DeviantArt、BOOTH；不广搜模之屋，用户指定链接可核。许可／署名以随包文件为准，公开下载不等于可再分发或跨工具使用。

## 安全制作与验证

- 用户已授权任务内常规可逆技术选择，不重复索取许可。保留其他未提交改动；使用新目录与独立后台进程，不覆盖原素材／旧视频／缓存，不把后台场景说成用户GUI场景。
- 诊断静音继承的File Output。历史`prepare_*`／`package_*`常绑定固定SHA和输入版本，先读源码与工具地图，不能在最新工程重复安装全部场景／材质／物理。
- 先注册MMD相机RNA并核焦距／driver；factory-only曾得错误1mm相机。对照固定同帧、机位、分辨率、DOF／MB，不跨机位声称纯光照差异。
- 普通Blender位于`E:/tools/Blender Foundation/Blender 5.2/blender.exe`，已测5.2.2；不重复安装。Goo独立环境不同时注册旧mmd_tools与新版扩展。
- 保留MMDShaderDev Color／Alpha、贴图、sphere及透明语义；底色、SDF、形体、几何遮挡、AO、高光、辅助光、Emission与Glow分别检查。Emission不等于均匀自发光或照亮场景。
- Diffuse／Shader to RGB探针含法线、距离、多灯与间接光，不是纯shadow pass；AOV名称不代表物理通道。Goo Half Lambert／Cast Shadows／Light Groups已有局部实测；原生MME.fx未在Goo运行，未测功能不升级为全支持。
- 阿克西妮娅已有脸Lightmap/SDF，伊科尔没有已验证脸SDF，不交换模板。HM／HN按实际节点语义与色彩空间核对。白布提亮保护金青图案，不以最终脸亮度下限抹掉阴影。
- 黑线保留PMX／顶点权重，外壳与五官分开。蓝金细弧保持隐藏、曲线原数据保留。旧建筑probe不因局部材质修改而自动重烘。
- 物理遵守`docs/PHYSICS_MOTION_PLAYBOOK.md`：预滚、连续模拟、骨骼视觉烘焙、独立重开。旧袖／衣发仅4139–4441有界验证；保留局部corrective与非零接触，不称零穿模／全身纯物理。30→60fps同步关键点及柄。
- 字幕按整组前后层设计，不按脸挖字。Crypto同时包含`阿克西妮娅2_mesh`和`Ikhor | mesh | Ikhor_mesh`，核逐人头身ROI；旧漏伊科尔缓存不复用。Glow变更后beauty缓存也须匹配。
- 明确色彩流程和音轨来源。未来明确要求视频时，按约定实际完成片段与必要验证，不能停在启动后台。用户此前跳过的视频输出后检查只适用于其明确范围。

## 学习与维护

- 先查缓存／账本，优先实际阅读原作者图文、官方说明和源码；维护流程只是收尾，不能代替技术学习。见`docs/EFFICIENT_RESEARCH_WORKFLOW.md`与`catalog/learning_queue.json`。
- MME先核原生装配、主shader、RT分工和单参数变化，再考虑Goo适配。借物表作者名不能推断具体预设；主shader不默认全部叠加，Shade_Normal与真实投影等兼容限制须读原说明。
- 图文／字幕优先；视频打开先暂停并确认，不默认4K／自动连播。第三方全文只私人缓存一次，repo存原创归纳、URL、阅读范围与哈希；没有字幕不称已转写，没有原工程不编造参数。
- Chrome扩展与native host已核正常，不重复建议重装／补权限。失败有限重试，遵守`docs/BROWSER_AUTONOMY.md`；偏好Chrome，不绕登录、等级或付费。短链`https://b23.tv/B55DoZl`尚未确认为指定作品。
- 状态区分磁盘存在／注册／导入／原生静帧／动态／重开／整合。九套MME原包重点段落已读，不等于49位作者技术全掌握；tn点光不支持自阴影，wDark不是光源。
- `docs/`放原创总结、`docs/research/`放账本、`presets/`放参数。文件索引用`scripts/repository_index.py`刷新，不移动脚本破坏导入，不删除失败实验冒充整理。
- 整理前完整约定与旧SHA／细则在`docs/history/2026-11-17/repository-before-organization/AGENTS.md`及`docs/history/2026-11-13/AGENTS.snapshot.md`。只按任务追溯，不从快照恢复旧制作指令。
