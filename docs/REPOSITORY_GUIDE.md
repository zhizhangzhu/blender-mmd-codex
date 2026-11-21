# 仓库导航与维护

日常从README进入，当前工程与反馈只看[现行状态](../catalog/current_state.json)。[全文件索引](REPOSITORY_FILE_INDEX.md)按职责列出源码与资料；分类用于检索，不是已审计或可直接执行的认证。

2026-11-18新增[AI任务制作导航](AI_TASK_PLAYBOOK.md)与[机器路线目录](../catalog/task_routes.json)。先选任务再读知识、案例与输入契约；[设计评审](DESIGN_FOUNDATIONS_AND_REVIEW.md)负责“为什么这样做”，[动作/K帧](ANIMATION_AND_KEYFRAMING_PLAYBOOK.md)补齐导入后如何判断与局部修订。只读查询`python -m scripts.knowledge_route --task motion`，不会执行路线内的脚本。

## 按任务查找

| 任务 | 主要入口 |
| --- | --- |
| 当前优先学习 | [Goo基础功能与参数](GOO_FOUNDATIONS_AND_PARAMETERS.md)：先基础，后高阶；MMD主渲暂缓 |
| 当前双人人物改图 | [本轮光影](MME_REFERENCE_LIGHT_STILLS_2026_11_17.md)、[头发修复](IKHOR_HAIR_ALIGNMENT_STILL_REPAIR.md)、[刘海窄影](CITLALI_WARM_FRINGE_SHADOW_STUDY.md) |
| 原生MMD／MME路线 | [工具分工](MMD_MME_GOO_WORKFLOW.md)、[原生实验](MME_NATIVE_LEARNING_LAB.md)、[兼容边界](MME_REUSE_AND_BLENDER_COMPATIBILITY.md) |
| Goo环境 | [本机环境](LOCAL_ENVIRONMENT.md)、[迁移记录](GOO_ENGINE_MIGRATION.md)、[运行配置](../presets/runtime/goo-v1.json) |
| 人物／物理／灯光制作 | [制作流程](PRODUCTION_WORKFLOW.md)、[人物手册](CHARACTER_NPR_PLAYBOOK.md)、[物理手册](PHYSICS_MOTION_PLAYBOOK.md)、[参考与灯光](REFERENCE_AND_LIGHTING_PLAYBOOK.md) |
| 资料来源与续接 | [知识索引](KNOWLEDGE_INDEX.md)、[学习队列](../catalog/learning_queue.json)、[来源账本](research/MMD_MME_GOO_ROUTE_2026_11_17.json) |
| 查脚本能否用于当前工程 | [脚本分类](../scripts/README.md)、[输入契约](TOOL_AND_PRESET_MAP.md)，然后读脚本参数与SHA断言 |
| 历史视频／旧技术验证 | `catalog/current_state.json`中的历史字段，及各日期制作文档，不从文件名“latest”推断 |

## 目录边界

`catalog`存现行状态和索引；`presets`存运行参数；`docs`存原创归纳，`docs/research`存来源与证据，`docs/history`存快照。`scripts`中的版本迁移仍保留原路径，避免破坏同目录导入、历史命令与固定输入约束。`tests`只验证工具／约定，不自动评判美术质量。`site`是离线站点源码，生成站点要单独构建和检查。

当前`latest_review`字段承载历史Clean完整视频验收，`active_iteration`与`latest_still`承载现行静帧；两者语义不同，暂不重命名破坏历史打包器。新工具优先读取后两者，不能把旧视频字段当现行制作任务。

## 新增和更新

新研究先写原创技术结论与原始来源，证据落在`docs/research`，有可复现参数才放`presets`。只修改用户指定或本轮拥有的字段，保留其他未提交改动。一次性脚本写清固定源、输出、副作用与限制。

```powershell
python -m scripts.repository_index --write
python -m scripts.repository_index --check
python -m scripts.knowledge_route --check
python -m scripts.audit_knowledge
```

索引扫描不导入或执行仓库脚本，不调用渲染器。带`--write`时只更新三个索引文件，`--check`只检查索引是否过期。副作用提示来自文本启发式，不是完整安全审计；运行前仍须读源码。

## 本次整理保留了什么

没有批量搬动脚本或重编号预设，没有删除失败实验、原素材、历史输出或其他未提交改动。入口旧文和现行状态在`docs/history/2026-11-17/repository-before-organization/`保存完整快照；它们用于追溯，不能变成新任务指令。详见[整理记录](REPOSITORY_ORGANIZATION_2026_11_17.md)。
