# blender-mmd-codex

猪猪的 MMD 制作与技术学习仓库。现行版本、历史交付和实验记录分开管理；目标是逐步改善三渲二质量，当前尚未达到参考作品的感知质量。

## 当前入口

| 要做什么 | 从哪里开始 |
| --- | --- |
| 项目长期目标与最高层规范 | [SPEC](SPEC.md)：能力成长、参考理解、美术经验、多模型分工、完成标准与分阶段建设 |
| 接手长期制作与学习 | [工作入口](docs/STUDIO_WORKFLOW.md)／[mmd-studio技能](skills/mmd-studio/SKILL.md)；`python -m scripts.mmd_studio status`与`context` |
| 实际角色映射与静帧对照 | [安全试验台](docs/STUDIO_SCENE_BENCH.md)／[有界配置](catalog/scene_benches.json)；`python -m scripts.mmd_studio benches`，执行须显式指定 |
| 参考到作品、图审与经验复用 | [制作闭环](docs/STUDIO_ITERATION.md)：冻结预测→真实对照→逐假设图审→经验检索；选定方案另存并独立重开 |
| AI接手具体任务 | [任务制作导航](docs/AI_TASK_PLAYBOOK.md)／[机器路线目录](catalog/task_routes.json)：模型、动作/K帧、卡渲、特效、舞台、布光、设计 |
| 确认当前工程、反馈与输出范围 | [现行状态](catalog/current_state.json) |
| 查看最新Goo人物与舞台静帧 | [礼堂层次优化](docs/GOO_DUET_ARTDIRECTION_2026_11_20.md)；`D:/codex/output/Goo-Duet-ArtDirection-2026-11-20/final-v3/Candidate.blend`；仅4290，SourceDOF／完整保护／独立重开通过，用户美术待评；原829f冻结保留 |
| 当前学习方向 | [Goo基础功能与参数](docs/GOO_FOUNDATIONS_AND_PARAMETERS.md)／[基础课程](presets/workflows/goo-foundations-v1.json) |
| 最新基础发现 | [八项基础指南与法线实测](docs/GOO_MMD_EIGHT_FOUNDATIONS_2026_11_18.md)／[双版本输入与色彩](docs/GOO_BLENDER_FOUNDATIONS_2026_11_18.md)／[近景目标](docs/GOO_REFERENCE_FACE_HAIR_STUDY_2026_11_17.md) |
| 已评估的原生路线，现暂缓 | [MMD MME 与 Goo 分工方案](docs/MMD_MME_GOO_WORKFLOW.md) |
| 找文档、源码、参数和历史版本 | [仓库导航](docs/REPOSITORY_GUIDE.md)／[全文件索引](docs/REPOSITORY_FILE_INDEX.md) |
| 选择脚本 | [脚本入口](scripts/README.md)／[输入与副作用约定](docs/TOOL_AND_PRESET_MAP.md) |
| 设计与动作修订 | [设计基础与美术评审](docs/DESIGN_FOUNDATIONS_AND_REVIEW.md)／[动作数据与局部K帧](docs/ANIMATION_AND_KEYFRAMING_PLAYBOOK.md)／[迭代简报](presets/templates/iteration-brief-v1.json) |

**后续默认只看静帧。** 只有猪猪明确要求视频时才渲染片段或全曲。眼透暂缓；字幕保留黑边和投影。本轮 final-v3 仅4290有界静帧，仍待用户美术评价，不把技术通过写成用户认可。

## 当前制作与研究

11月20日按猪猪新要求，在Goo5.2.1独立副本优化双人及指定礼堂，已交付正式1080p静帧和独立重开验证的新候选。11月19日原829f仍冻结；[官方5.3迁移](docs/BLENDER53_DUET_TOON_MIGRATION_2026_11_19.md)保留为另一条试作。当前实际工程与范围仍读现行状态。原生MMD主渲方案暂缓，MME通用兼容插件不立即开发。

学习以[官网](https://www.dillongoostudios.com/gooengine)及官方GitHub发布分支为主，区分原版4.4与社区5.2接口。已完成13类专属节点参数清单和独立灯组基础静帧；其他基础项继续按证据推进，不称全部掌握。人物工程未因此修改。

人物仍为阿克西妮娅＋伊科尔，保留原生 VMD、现成相机、指定赫斯珀利德斯礼堂、雪／婚礼主题及原声 FLAC。伊科尔发型修复和窄刘海影目前只有静帧证据，不能直接继承为新动态通过。

## 仓库结构

| 目录 | 内容 |
| --- | --- |
| `catalog/` | 唯一现行状态、资料库、学习队列、自动生成的文件索引 |
| `docs/` | 操作指南和技术总结；`research/`为来源账本，`history/`为整理前快照 |
| `presets/` | 运行时、实验参数、项目／材质／后期／字幕配方 |
| `scripts/` | 可查询工具与绑定历史版本的制作脚本，分类见目录内 README |
| `tests/` | 工具与数据约定的回归检查 |
| `skills/`、`blender_addon/` | 工作技能与 Blender 辅助插件源码 |
| `site/` | 离线资料库源码；旧生成站点不是最新工程入口 |

源码放 `D:/codex/workspace/`，交付放 `D:/codex/output/`，临时／第三方私人缓存放 `D:/codex/temp/`。第三方完整预设、教程、模型和软件不提交本仓库。

## 常用检查

在仓库根目录执行，以下命令不启动渲染，需要本机可用的 Python。

```powershell
python -m scripts.repository_index --check
python -m scripts.knowledge_route --list
python -m scripts.knowledge_route --task lighting
python -m scripts.knowledge_route --check
python -m scripts.audit_knowledge
python -m scripts.mmd_studio check
python -m scripts.mmd_studio context --task reference --query "白衣 发束"
python -m scripts.learning_queue plan --limit 3
```

新增或删除源码文件后用 `python -m scripts.repository_index --write` 更新索引。版本专用 `prepare_*`、`package_*`、`complete_*` 不是通用入口，不从最新工程随意重跑。

本机没有裸`python`命令时，用[工作入口](docs/STUDIO_WORKFLOW.md)列出的已有便携Python执行；无需重新安装。能力、情境偏好、课程、参考准备与任务包可检索；角色映射、真实对照、逐假设评审、经验检索和安全另存／重开均已有实际入口。本轮176项相关回归通过；登记数量与工具通过均不代表渲染质量或课程完成。

## 历史与整理记录

[11月17日整理记录](docs/REPOSITORY_ORGANIZATION_2026_11_17.md)说明实际修改范围。之前的入口、完整约定与状态保存在 `docs/history/2026-11-17/repository-before-organization/`。

旧 Clean 两版五秒、Goo v16 快样等保留于原路径；最新视频记录看现行状态中的历史字段。它们不代表 v6 静帧已有对应视频。更早资料见[11月13日复审](docs/REPOSITORY_REVIEW_2026_11.md)。
