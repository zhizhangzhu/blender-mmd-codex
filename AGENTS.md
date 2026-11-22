# 仓库工作约定

本文件只放长期原则、猪猪偏好与入口。作品现行事实只在 `catalog/current_state.json`；当前双人作品的专属规则在 `docs/PROJECT_FRANKEN_DUET_RULES.md`，处理该作品时同等必须遵守。2026-11-22 精简前全文见 `docs/history/2026-11-22/AGENTS.before-slimming.md`，更早见 `docs/history/2026-11-17/`、`docs/history/2026-11-13/`；只按任务追溯，不从快照恢复旧制作指令。

## 最终目标

- AI 全自动使用 GooEngine 产出符合需求的高质量 MMD；感知质量目标为原神／鸣潮式三渲二，观海子优先，Gosari542 保留，御手洗板蓝根补充。
- 进度按 `SPEC.md` 自动化阶梯 L0–L4 衡量，现级别见 `current_state.automation`。当前尚未达标；插件存在、技术通过、自动 QC、AI 图审与用户美术认可分开。

## 阅读入口

- 顺序：`SPEC.md` → `catalog/current_state.json` → `skills/mmd-studio/SKILL.md` → `docs/AI_TASK_PLAYBOOK.md`／`catalog/task_routes.json`。`python -m scripts.mmd_studio context --task <路线> --query "问题"` 只读取相关经验，不启动生产。
- 工具找 `scripts/README.md` 与 `docs/TOOL_AND_PRESET_MAP.md`；资料找 `docs/KNOWLEDGE_INDEX.md`；`python -m scripts.knowledge_route --task lighting` 只读查询。先读主手册与案例，再核脚本输入契约，不从文件列表猜执行链，不默认全量读历史。
- 运行时 `docs/GOO_RUNTIME_POLICY.md`；静帧试验台 `docs/STUDIO_SCENE_BENCH.md`（`mmd_studio benches` 选配置，`studio_bench` 显式执行）；迭代闭环 `docs/STUDIO_ITERATION.md`；自动 QC `docs/AUTO_QC.md`；关卡 `docs/QUALITY_GATES.md`。原创代理夹具只验证工具，不当美术或迁移证据。
- 视觉迭代先用 `docs/DESIGN_FOUNDATIONS_AND_REVIEW.md` 明确焦点、情绪、明暗／色彩、舞台与效果职责；动作修订按 `docs/ANIMATION_AND_KEYFRAMING_PLAYBOOK.md` 先排除输入／绑定／求值问题。设计简报可选填 `presets/templates/iteration-brief-v1.json`。
- 成片用 `skills/mmd-finish-render/SKILL.md`，相机检索用 `skills/mmd-camera-search/SKILL.md`。历史脚本可运行不等于应重跑旧生产流程。

## 猪猪与路径

- 称呼用户「猪猪」，GitHub `zhizhangzhu`。源码 `D:/codex/workspace/`，交付 `D:/codex/output/`，临时与私人第三方缓存 `D:/codex/temp/`。

## 模型分工

- 按当前会话模型族分档：GPT 会话由 `gpt-6.1-sol` 的 `xhigh` 主控；Claude Opus 5.5 会话由其 `high` 主控；Gemini 4 Neon 会话由其 `high` 主控。三者的 `low` 档都只做步骤已明确的简单执行，不代替学习或复杂判断。
- 主控亲自负责指挥、方案、技术判断、官方资料学习和最终验收。映射只在 `catalog/model_policy.json` 维护；低档任务包须有输入指纹、写路径、产物、验收与升级条件。
- 可指定子代理模型与推理档位，不声称能在对话中切换主聊天模型，不改用户全局配置。任务包推荐不等于真实派发；实际模型、耗时与费用如实记录，未知留空。

## 运行时

- GooEngine 是主线：`presets/runtime/goo-v1.json`（5.2.1 非官方社区移植、构建 0051aee03764）。先用 `scripts/goo_runtime.py` 注册便携插件再打开，仅用独立 CONFIG，不改用户偏好；不同时注册旧 mmd_tools 与新版扩展。Goo 4.3 不能读当前 5.2 工程，不降级生产文件。
- 官方 Blender 5.3 为对照／备选；普通 Blender 在 `E:/tools/Blender Foundation/Blender 5.2/blender.exe`（已测 5.2.2），不重复安装。风险、已测功能与回退见 `docs/GOO_RUNTIME_POLICY.md`。

## 交付与 QC

- 默认只交付静帧／对照图；视频片段或全曲只在猪猪明确要求时交付。
- 每轮标准 QC 包括：硬指标、多帧稀疏检查（跨全曲 8–12 帧）、低分辨率 1–2 秒时序诊断（`docs/AUTO_QC.md`）。诊断产物只作 QC 证据，不编码为样片、不当作视频交付。
- 自动 QC 只负责筛除与排序；用户美术认可必须有明确反馈出处，AI 与程序不能代填。

## 安全制作与验证

- 用户已授权任务内常规可逆技术选择，不重复索取许可。保留其他未提交改动；使用新目录与独立后台进程，不覆盖原素材／旧视频／缓存，不把后台场景说成用户 GUI 场景。
- 每轮有效改动在本地 git 提交；推送远端只在猪猪要求时进行。
- 诊断静音继承的 File Output。历史 `prepare_*`／`package_*` 常绑定固定 SHA 和输入版本，先读源码与工具地图，不能在最新工程重复安装全部场景／材质／物理。
- 先注册 MMD 相机 RNA 并核焦距／driver；factory-only 曾得错误 1mm 相机。对照固定同帧、机位、分辨率、DOF／MB，不跨机位声称纯光照差异。
- 保留 MMDShaderDev Color／Alpha、贴图、sphere 及透明语义；底色、SDF、形体、几何遮挡、AO、高光、辅助光、Emission 与 Glow 分别检查。Emission 不等于均匀自发光或照亮场景。
- Diffuse／Shader to RGB 探针含法线、距离、多灯与间接光，不是纯 shadow pass；AOV 名称不代表物理通道。Goo 未测功能不升级为全支持；原生 MME.fx 未在 Goo 运行。
- 黑线保留 PMX／顶点权重，外壳与五官分开。脸 SDF 等模板不跨角色交换，除非已验证。
- 物理遵守 `docs/PHYSICS_MOTION_PLAYBOOK.md`：预滚、连续模拟、骨骼视觉烘焙、独立重开；换动作不复用旧烘焙；30→60fps 同步关键点及柄。不称零穿模／全身纯物理，除非有对应证据。
- 字幕按整组前后层设计，不按脸挖字。明确色彩流程和音轨来源。明确要求视频时，按约定实际完成片段与必要验证，不能停在启动后台。

## 素材

- 优先 PMX＋原生 VMD；FBX 另查骨架／重定向。新素材优先作者配布、BowlRoll、DeviantArt、BOOTH；不广搜模之屋，用户指定链接可核。许可／署名以随包文件为准，公开下载不等于可再分发或跨工具使用。

## 学习与维护

- 先查缓存／账本，优先实际阅读原作者图文、官方说明和源码；维护流程只是收尾，不能代替技术学习。学习成果优先沉淀为可执行资产（风格包、节点组、QC 规则、管线阶段），见 `docs/EFFICIENT_RESEARCH_WORKFLOW.md` 与 `catalog/learning_queue.json`。
- MME 先核原生装配、主 shader、RT 分工和单参数变化，再考虑 Goo 适配。借物表作者名不能推断具体预设；主 shader 不默认全部叠加，Shade_Normal 与真实投影等兼容限制须读原说明。tn 点光不支持自阴影，wDark 不是光源。
- 图文／字幕优先；视频打开先暂停并确认，不默认 4K／自动连播。第三方全文只私人缓存一次，repo 存原创归纳、URL、阅读范围与哈希；没有字幕不称已转写，没有原工程不编造参数。
- Chrome 扩展与 native host 已核正常，不重复建议重装／补权限。失败有限重试，遵守 `docs/BROWSER_AUTONOMY.md`；偏好 Chrome，不绕登录、等级或付费。
- 状态区分磁盘存在／注册／导入／原生静帧／动态／重开／整合。`current_state.json` 只保留现行事实，历史移入 `docs/history/`。
- `docs/` 放原创总结、`docs/research/` 放账本、`presets/` 放参数。文件索引用 `scripts/repository_index.py` 刷新，不移动脚本破坏导入，不删除失败实验冒充整理。
