# 按制作任务组织知识：2026年11月18日

本轮按猪猪要求整理后续AI的知识使用方式，并实际补读官方设计资料。沿用[11月17日文件分类](REPOSITORY_ORGANIZATION_2026_11_17.md)，不搬移生产脚本，不删除旧案例／失败研究，不覆盖其他已存在的未提交改动。

## 具体改动

- 新增[AI制作导航](AI_TASK_PLAYBOOK.md)与[七条机器路线](../catalog/task_routes.json)，覆盖模型驱动、动作/K帧、卡渲、特效、舞台、布光和美术设计。路线列出必读知识、参数、工具适用限制、决策、证据与未测边界。
- 新增只读查询器[knowledge_route.py](../scripts/knowledge_route.py)：只加载导航JSON、校验仓库引用和输出路线，不导入制作脚本、不执行工具。`--task K帧`可查局部动作路线。
- 新增[动作数据与K帧](ANIMATION_AND_KEYFRAMING_PLAYBOOK.md)：先区分输入／绑定／IK／物理与表演需求，再考虑局部修订；明确白名单、Action／Slot／NLA、接触／边界与静帧验收限制。
- 新增[设计与美术评审](DESIGN_FOUNDATIONS_AND_REVIEW.md)及[可选填简报](../presets/templates/iteration-brief-v1.json)：把焦点、情绪、明暗、色彩、空间、灯光和效果职责接到技术选择。
- 将AGENTS、README、仓库／知识导航、制作流程、工具地图和质量关卡接到新入口。保留旧文历史事实，明确历史视频、现行静帧和运行配置中的历史启动默认值不同。
- 为新指南和近期Goo基础资料补上现有资料库分类，保留唯一归属。当前源码导航已更新；旧生成的离线站点没有在本轮重建。
- 将路线检查加入知识审计，新增回归测试防止重复别名、失效／越界路径和未标工具适用范围。

## 本轮实际学习

阅读Pixar与波士顿科学博物馆合作教育页面的故事／概念、镜头／舞台、表演和灯光正文；Epic构图、景别、运镜与灯色设计；Adobe色彩对比的可读正文；Riot特效教育入门正文。补读Blender NLA Sidebar完整正文，关键帧／F-Curve部分访问失败，仅相应检索片段，未冒充完整阅读。没有播放研究视频。

新内容补的是统一设计简报与审美判断方式，不能替代既有作者参考或直接认证参考质感。部分官方来源也有媒介／引擎限制与不严谨描述，未直接采用数值和一刀切规则；失败链接与真实读取层级见[来源账本](research/DESIGN_FOUNDATIONS_2026_11_18.json)。

## 范围和验证

执行任务路由与现有知识工具的24项相关回归测试、Ruff、路线引用／索引一致性和知识／实际产物审计。详细报告与可读副本在`D:/codex/output/MMD-Repo-Knowledge-Design-2026-11-18/`；检查成功不等于逐行审查所有脚本。

本轮修改前入口原文在`D:/codex/temp/Repo-Task-Routing-2026-11-18/before/`私人快照。状态比对确认`active_iteration`、`latest_still`、`latest_production_increment`、`latest_review`和`project_contract`保持；没有打开／保存人物工程、修改骨架／动作／材质／舞台、模拟或渲染。当前候选仍需实际美术迭代，眼透继续暂缓，默认仍仅静帧。
