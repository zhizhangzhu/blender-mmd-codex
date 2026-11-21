# 长期制作与学习的实际工作入口

2026-11-20。顶层约定见[项目SPEC](../SPEC.md)，接手技能见[mmd-studio](../skills/mmd-studio/SKILL.md)。首期将既有知识接入可运行检索、参考准备和多模型任务包，不改变当前制作工程。

## 运行与接手

首期登记／检索工具均为 Python 标准库；无需 Blender 后台进程或新的 Python 安装。第二阶段实际场景检查与静帧执行见[试验台](STUDIO_SCENE_BENCH.md)，使用已有Blender且须显式执行。当前机器可用的解释器如下；已有可用 `python` 时也可直接执行相同模块。

```powershell
$studioPython = 'D:/codex/workspace/blender-runtimes/5.3.0/blender-5.3.0-windows-x64/5.3/python/bin/python.exe'
& $studioPython -X utf8 -m scripts.mmd_studio status
& $studioPython -X utf8 -m scripts.mmd_studio context --task reference --query '白衣 发束'
& $studioPython -X utf8 -m scripts.mmd_studio context --task render --query '脸影'
& $studioPython -X utf8 -m scripts.mmd_studio learn --limit 3
& $studioPython -X utf8 -m scripts.mmd_studio check --check-artifacts
```

`status`同时显示冻结候选、正在试作和输出政策；`context`结合路线给出最多数条相关能力、用户偏好、课程和参考简报。未命中时返回空能力，不捏造结论。`learn`遵守现行静帧政策规划下一项验证，并保留历史卡原状态。`check`仅核结构／出处，`--check-artifacts`另外读本机产物和源工程SHA。

实际制作继续用[参考到作品闭环](STUDIO_ITERATION.md)：冻结预测后跑bench、生成等比例局部对照、记录AI观察与假设结论、独立保留用户反馈、结案为可检索经验。`context`同时读经校验的`lessons`；无效记录报告错误。安全另存与独立重开另由`studio_publish`完成，诊断worker保持只读源。

旧学习队列未覆盖后来所有进展，`learn`同时提供能力的下一练习并标记必须先核当前缺口；主控不得把旧hypothesis状态当成近期工作从未发生。

## 能力、偏好与课程

编辑[studio.json](../catalog/studio.json)中的相关条目，再运行检查。记录解决的问题、适用和避免条件、方法、工具与主手册、实际证据、下一项练习。证据的 reading/still/motion/reopen/integration/transfer 彼此独立，默认没有“通用掌握”状态。

通过证据必须有范围、出处与产物哈希。结构检查能发现丢失和篡改，无法证明某张图真的好看；主控须核实际正文和图像。`cross_project`需要迁移证据和不同产物，具体是否换过角色／场景仍需人工核查。

用户反馈保存具体作品、部位和条件。首批“伊科尔太亮”反例只约束当时v5情境，不能推广为全局压暗规则。课程定义独立练习与迁移验收；已关联记录不代表课程已完成。

## 参考研究与实际媒体准备

```powershell
& $studioPython -X utf8 -m scripts.reference_study init --source 'D:/codex/temp/reference.png' --kind image --title '人物参考' --id portrait-study --output 'D:/codex/output/New-Reference/study.json'
& $studioPython -X utf8 -m scripts.reference_study check --study 'D:/codex/output/New-Reference/study.json' --check-artifacts
& $studioPython -X utf8 -m scripts.reference_study extract --study 'D:/codex/output/New-Reference/study.json' --output 'D:/codex/output/New-Reference/frames'
& $studioPython -X utf8 -m scripts.reference_study brief --study 'catalog/reference_studies/gosari-portrait-relations.json'
```

草稿中 observations/hypotheses/targets 初始为空，不编造图像理解。亲看后填写：

- observations：`id, dimension, locator, description, seen`，定位原尺寸区域或时间码。
- hypotheses：`id, observation_ids, explanation, test, prediction, status, evidence_refs`；未测试为 untested。
- targets：`id, observation_ids, priority, visual_goal, controls, check, reject_if`。
- 视频 shots：`id, start_seconds, end_seconds, sample_times, events, review`；事件含 `time_seconds, description`，连续审阅含 `continuous, scope`。
- media_review：audio 和 transcript 各自记录 `status: not_reviewed|reviewed, scope`。
- implementation：独立保存 recipe_refs、evidence、实际重建和迁移范围；review 单独保存美术状态。

视频 `extract` 另传已有的本地 `--ffmpeg`；默认最多24帧，上限64帧，逐个指定时间点，不输出新视频。它产出原尺寸帧、带SHA与未审看标记的 `extraction.json` 和离线 `contact.html`。连续视频、音轨和字幕是否看过均不由抽帧成功推断。失败保留已有结果和失败清单；输出目录必须是新目录。

首批Gosari条目沿用已有原帧和账本，仅完成观察到目标的转换；实现假设和跨素材重建仍为未测。原帧私人引用，不复制入仓库。

## 多模型任务包

```powershell
& $studioPython -X utf8 -m scripts.studio_tasks recommend --kind reference_analysis
& $studioPython -X utf8 -m scripts.studio_tasks recommend --kind frame_extraction
& $studioPython -X utf8 -m scripts.studio_tasks recommend --kind bounded_implementation --uncertainty exploratory
& $studioPython -X utf8 -m scripts.studio_tasks packet --title '执行已有输入契约检查' --kind run_checks --input '准确源路径及SHA256由主控填写' --allow 'D:/codex/temp/new-check' --deliverable '检查JSON' --accept '错误明确返回非零；不修改源工程' --context-ref SPEC.md --output 'D:/codex/output/New-Task/check-task.json'
```

任务类型与角色是[model_policy.json](../catalog/model_policy.json)中的配置。重复失败达到2次、探索性问题或复杂判断交主控。当前命令生成未派发包，不调用模型；真实派发由主控通过可用会话工具执行，再如实登记 execution。无需安装新服务或提供 API key。

输入指纹目前由主控写在 inputs 中，CLI验证其非空而不解析文件指纹。allowed_paths是任务所有权声明，真正文件权限由运行环境控制；主控仍须核任务是否越界。推荐模型不能被当作实际执行模型，未知费用保持null。

## 本轮收尾与维护

只更新本轮拥有记录，不覆盖正在进行的其他工程。可先按问题 lookup，再补一条知识修正、证据或反例。必要检查：

```powershell
& $studioPython -X utf8 -m unittest tests.test_studio_registry tests.test_studio_tasks tests.test_reference_study tests.test_mmd_studio tests.test_learning_queue
& $studioPython -X utf8 -m scripts.audit_knowledge
& $studioPython -X utf8 -m scripts.repository_index --write
& $studioPython -X utf8 -m scripts.repository_index --check
```

首期之后按真实作品提取共享执行组件、多姿态试验台和风格配方。功能清单见SPEC第9节，不能把后续路线写成已经实现。
