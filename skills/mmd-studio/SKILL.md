---
name: mmd-studio
description: Continue this repository's long-term MMD learning and production method; retrieve scoped capabilities and visual preferences, analyze reference images or video, and delegate bounded execution with a high-reasoning supervisor. Use for this project's development and MMD tasks, following the current project scope.
---

# 接手与成长

先读仓库 [SPEC](../../SPEC.md)、[现行状态](../../catalog/current_state.json)及[任务导航](../../docs/AI_TASK_PLAYBOOK.md)。长期方法与当前作品分开；当前作品约定优先，旧案例不自动成为输入。本机先按工作入口选择已有解释器并启用`-X utf8`；下文`python`表示该解释器。命令和数据格式见[实际工作入口](../../docs/STUDIO_WORKFLOW.md)。

## 取用经验

用 `python -m scripts.mmd_studio context --task <路线> --query "可见问题"` 取适用能力、偏好、课程和参考；没有命中时查看路线，不猜已有能力。只阅读与本轮有关的主手册、证据及脚本输入契约。登记表的 passed 是指定范围的记录，不能推断新版本或新角色已通过。

## 主控与执行

按[角色配置](../../catalog/model_policy.json)组织：高推理主控亲自负责目标、技术学习、参考理解、方案和图审。低推理模型仅执行有明确输入、写入路径、产物、验收和升级条件的任务。主控须在 inputs 中写清源文件路径和内容指纹；CLI 首期不解析自由文本中的指纹。

`studio_tasks packet` 生成的是未派发任务包。主控核对实际可用模型后，使用会话提供的 collaboration 工具真实派发；指定模型／档位时使用工具要求的上下文模式。交接最小上下文，独立文件可并行，同一产物一个编辑者。输入偏离、需要判断或达到上限时交回主控，不能无限让执行者重试。

审查实际结果后再更新 execution。未知模型、费用和耗时保留未知；推荐配置不能充当运行证据。没有对应工具时保留为计划，不声称已运行。

## 技术学习与参考

需要实际场景诊断时，先读[安全静帧试验台](../../docs/STUDIO_SCENE_BENCH.md)，用`mmd_studio benches`选匹配的有界profile。主控核场景、角色/rig、语义映射、expected与控制职责；先plan/bind，再派发明确的inspect/render任务。活动模拟、共享数据或驱动冲突交回主控，不自动关闭物理来凑通过。逐case重开输入，不保存源；verify必须指定前次报告及事先阈值。原创代理夹具通过仅证明工具，不晋升人物美术。

学习以真实作者内容、原理理解和练习为主。选项目缺口或课程中的一个主题，按需要复现、预测、迁移和组合；收尾只保存有用增量。

参考用 `reference_study init` 建草稿，明确借鉴维度与保留项。用 `extract` 对本地源取指定帧／联系表，再亲看原图；工具输出 seen=false 不得直接改成“已理解”。将可见观察、待证假设和可执行目标分开。视频针对切镜、主体／对焦交接和效果变化查看连续证据，音频和字幕阅读另记实际范围。

先重建构图、明暗和色彩关系，再细化材质、线条及效果。提出预测，保留同条件对照；换素材验证适用范围。只看单帧不能确定作者唯一 shader，也不能证明动态稳定。当前静帧交付不因研究参考视频而扩大。

进行真实方案迭代时用[参考到作品闭环](../../docs/STUDIO_ITERATION.md)：先冻结study/profile/plan及代码运行时，再执行受控对照。主控亲看后逐目标、逐假设记录结果和代价，图审不能只剩选图。AI review与用户feedback分开；结案经验经现有studio登记和context检索。需要保存所选作品时走独立publish/reopen，不能让诊断worker改写源。

## 验收和收尾

程序先检查输入、引用和产物；主控审阅关键代码与实际画面。说明改善、代价和未测范围，用户认可必须有反馈出处。失败经验保留，拒绝一个艺术方案不等于否定全部技术。

有增量时更新对应能力／偏好／参考记录，避免复制全文。运行 `mmd_studio check`、相关测试和知识审计；文件增删后刷新仓库索引。报告已实现功能与尚需作品练习的能力，不能把管理工具完成当作渲染风格进步。
