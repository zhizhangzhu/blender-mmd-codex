# AI接手任务的知识与制作导航

2026-11-20：长期目标与完成标准先看[项目SPEC](../SPEC.md)，接手工作法用[mmd-studio](../skills/mmd-studio/SKILL.md)。[工作入口](STUDIO_WORKFLOW.md)把能力、偏好、参考和课程接到实际命令；新增reference／learning／orchestration路线。研究、制作和跨项目迁移分别留证，按当前范围验收。

需要实际诊断工程时用[安全静帧试验台](STUDIO_SCENE_BENCH.md)，从有界profile精确选择角色与控制。先检查／计划，再明确执行，不从历史prepare脚本猜通用入口；不能为了渲静帧自动启用或重算物理。

方案制作使用[闭环入口](STUDIO_ITERATION.md)：研究、预测和输入先冻结，再执行、亲看、逐假设结案。经验在`studio.json.lessons`经指纹核对后随context检索；用户后补反馈独立保存。已选静帧另存候选与独立重开使用publish入口，不能让诊断脚本覆盖冻结工程。

本页把已有知识按任务连接起来。先读[现行状态](../catalog/current_state.json)与[AGENTS](../AGENTS.md)，再选择下面的路线；不用把全部历史文档读一遍。源码／旧工程保留原路径，不能根据文件名“latest”“final”判断当前版本。

当前候选从`active_iteration`／`latest_still`追踪；`latest_review`是历史完整视频。运行配置只提供可执行文件、构建与独立CONFIG／SCRIPTS；其中`production_project`等历史启动器默认值不能覆盖现行静帧，不因整理而偷偷改写旧启动器的输入。

## 先分清四件事

1. **用户要改变什么感受或行为？** 将“更好看”展开为焦点、体块、材质、表演或空间问题，参照[设计与美术评审](DESIGN_FOUNDATIONS_AND_REVIEW.md)。已有约定从现行状态读取，不重复询问。
2. **问题属于哪一层？** 输入／骨架／动作／物理／材质／光照／合成分别定位；接收光的变化不能修复错误骨骼，K帧也不应掩盖重复物理驱动。
3. **已有哪份证据适用？** 区分资料阅读、接口清单、空场景实测、人物静帧、动态、重开与生产整合；检查模型、版本、帧段及输入SHA，不能跨级借用。
4. **本轮最小可审阅结果是什么？** 当前默认静帧。动作问题可先比较若干求值姿态与接触关键帧，但这不能认证时序自然；只有明确要求视频时才生成视频。不得因此把动态质量写成通过。

## 按任务进入

| 路线／查询词 | 必读入口 | 先复用什么，怎样判断完成 |
| --- | --- | --- |
| `reference`／参考／风格 | [参考工作入口](STUDIO_WORKFLOW.md)、[参考手册](REFERENCE_AND_LIGHTING_PLAYBOOK.md) | 原帧与时间码→实际观察→假设与预测→视觉目标→自有素材重建；抽帧不等于已看，不猜唯一作者参数 |
| `learning`／长期学习 | [SPEC](../SPEC.md)、[长期课程与能力](../catalog/studio.json) | 项目缺口与系统课程并行，阅读／复现／预测／迁移／组合按需要推进，静帧路径可独立重开和整合 |
| `orchestration`／多模型 | [工作入口](STUDIO_WORKFLOW.md)、[角色配置](../catalog/model_policy.json) | 高推理主控作判断，低档执行明确任务；计划与实际派发分开，单产物单编辑者，异常升级 |
| `model`／模型驱动 | [人物](CHARACTER_NPR_PLAYBOOK.md)、[八项基础](GOO_MMD_EIGHT_FOUNDATIONS_2026_11_18.md)、[局部修形](LOCAL_CORRECTIVE_SHAPES.md) | 保留PMX输入、权重／Morph与辅助骨；区分数据共享、绑定、骨骼求值和修改器问题；明确角色而非默认第一个Armature |
| `motion`／动作／K帧 | [动作数据与K帧](ANIMATION_AND_KEYFRAMING_PLAYBOOK.md)、[物理](PHYSICS_MOTION_PLAYBOOK.md) | 优先原配VMD与既有映射；局部修订有骨骼白名单、接触／节拍和过渡；不破坏未授权动作 |
| `render`／卡渲 | [Goo基础](GOO_FOUNDATIONS_AND_PARAMETERS.md)、[人物](CHARACTER_NPR_PLAYBOOK.md)、[最新近景目标](GOO_REFERENCE_FACE_HAIR_STUDY_2026_11_17.md) | 保Color／Alpha与角色配色，分开形体／遮挡／高光／线条；关闭Glow仍能看清脸、发束、白衣 |
| `fx`／特效 | [光与色彩](LIGHT_SPACE_AND_COLOR_PIPELINE.md)、[字幕分层](DUET_CAPTION_STABILITY_AND_LIGHTING.md)、[设计](DESIGN_FOUNDATIONS_AND_REVIEW.md) | 先说明效果的叙事职责、峰值与退场，再选体积／粒子／几何／合成；眼透仍暂缓，不因旧文实现过而恢复 |
| `stage`／舞台 | [作者装配](HESPERIDES_AUTHOR_SETUP.md)、[场景重建](HESPERIDES_REFERENCE_REBUILD.md)、[参考与灯光](REFERENCE_AND_LIGHTING_PLAYBOOK.md) | 保留指定礼堂，先设计人物活动区、前中后景、走道／窗的引导关系；不擅自换舞台 |
| `lighting`／布光 | [设计](DESIGN_FOUNDATIONS_AND_REVIEW.md)、[分层人像灯光](PORTRAIT_LIGHTING_AND_SHADOW_STUDY.md)、[Goo基础](GOO_FOUNDATIONS_AND_PARAMETERS.md) | 写明主／补／轮廓／环境职责与接收对象；灰阶主次、色彩关系、脸影与接地同时成立，不只增加灯数 |
| `design`／美术设计 | [设计基础](DESIGN_FOUNDATIONS_AND_REVIEW.md)、[作者参考矩阵](AUTHOR_REFERENCE_MATRIX.md) | 先用简报／构图与色彩意图挑选方案，再定参数；参考名字不是验收标准，未知原参数保持未知 |

机器目录为[task_routes.json](../catalog/task_routes.json)。只读查询：`python -m scripts.knowledge_route --task lighting`；用`--list`列路线，`--check`核路径与字段。它**不执行**列出的脚本、不打开工程、不连接网络、不渲染。

## 从知识到执行

每条路线按“主手册→相关案例→具体参数／工具→其输入契约”读取。遇到缺口才查[学习队列](../catalog/learning_queue.json)和[全文件索引](REPOSITORY_FILE_INDEX.md)。新设计来源另在[本轮账本](research/DESIGN_FOUNDATIONS_2026_11_18.json)登记；旧队列没有覆盖全部新知识，不能把队列条数当知识总量。

调用工具前先读[工具地图](TOOL_AND_PRESET_MAP.md)和该脚本参数、SHA断言及保存行为。目录中的工具分为只读查询、独立研究、历史输入绑定三类；列出路径不代表可在当前工程运行。特别注意旧`mmd_sample_pose.py`默认第一个Armature及固定骨名，旧`mmd_physics_bake.py`会静音IK，均不能作为任意双人场景的通用入口。

一次迭代先填写[简报模板](../presets/templates/iteration-brief-v1.json)中的适用字段：源工程／角色、任务范围、可见问题、焦点与情绪、保留项、允许改动、单项假设、控制图／姿态、拒绝条件及未测项。无需为了填表阻碍一个简单修复；缺失且不影响工作的字段可留空并解释。

研究读到的参数不要直接晋升为生产预设。复杂变更先在副本逐层验证，通过后再保存可关闭模块，并记录新输入与影响。实验失败仍保留原因；不把安装、接口枚举、文章读完或脚本返回成功当成艺术质量达标。

## 交接给下一位AI

明确留下：现行源工程与SHA位置、用户反馈、已改与未改、用过的知识／参数、实际产物、核对范围、剩余问题及下一步。状态只更新本轮拥有字段；历史视频、现行静帧和本轮研究分开。当前人物与动态证据不可被仓库整理或设计学习自动改写。
