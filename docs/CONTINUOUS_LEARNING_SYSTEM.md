# 持续学习怎样转化成更好的MMD

2026-11-20增量：顶层方法见[项目SPEC](../SPEC.md)，实际接手与命令见[工作入口](STUDIO_WORKFLOW.md)。新增能力／偏好／课程登记与参考研究。旧队列保留原记录；新卡可用`validation_scope: stills`声明静帧验证，直接still→reopen→integration，motion保持未测。CLI的`plan --scope stills`只调整计划，不改历史卡；统一入口`mmd_studio learn`遵守当前输出政策。

2026-11-13。优先解决当前画面问题，使用原作者图文、官方说明、公开规范和必要源码。参考质量以观海子优先，Gosari542保留，御手洗板蓝根补充；技术来源不限于这些作者，也不限于视频。

猪猪后续澄清：持续学习主要是实际学习外部教程与技术内容。本页工具用于辅助记忆和续接，不能替代正文阅读；最近新增技术见[Nilo／Ray-MMD／Filament实读笔记](EXTERNAL_MMD_TECHNIQUES_2026_11_13.md)。

## 每次任务从同一条队列继续

[学习队列](../catalog/learning_queue.json)把来源和实验分开登记。首批串联9个来源、5个假设，复用旧账本而不重复抓取全文。它只覆盖近期最有关的问题，其余历史知识仍从[知识索引](KNOWLEDGE_INDEX.md)查找。

1. 把用户反馈写成可观察问题，例如“转头后鼻口出现孤立暗块”，指定模型、部位与时间段。
2. 先查询已有来源、失败实验和缓存。相同知识只补证据；版本、依赖或实际问题发生变化才复读。
3. 优先读能回答该问题的一节官方说明、原作者文章或一段实现。写清实际读到的范围、版本、事实、推断、限制和新增量；只读到索引就保留该级别。
4. 形成一个有基线、独立开关、固定变量、接受与拒绝条件的假设。没有新假设或已知内容重复，就结束该资料分支。
5. 制作阶段冻结输入后，依次做同帧消融、短连续动态、独立重开和限定整合。失败保留原因；有收益再形成模型／引擎／画幅绑定的预设。
6. 下一次由工具读出仍可推进的条目、下一阶段和阻塞原因；最新成片与美术反馈继续以`current_state.json`为准。

文字适合核对公式、端口、单位、兼容、约束和故障原因；必要插图适合核对UV、接线及阴影形状。镜头节奏、动态闪烁和最终美感需要实际画面。只有文字不足以回答问题时，才看对应视频短段，操作遵守[低流量流程](EFFICIENT_RESEARCH_WORKFLOW.md)。

## 值得长期复用的文字入口

| 来源 | 能解决什么 | 当前阅读与迁移边界 |
| --- | --- | --- |
| [MooaToon：脸影设计](https://mooatoon.com/en/docs/Tutorial/ControlTheShapeOfShadows) | 区分法线、阈值偏移、AO与角度脸影 | 既有分节文字阅读；UE／Houdini实现未迁移 |
| [MooaToon：头发高光](https://mooatoon.com/en/docs/Tutorial/AddStylizedHairHighlights) | 发带形状、切线和许可遮罩 | 既有阅读；先验证现有发带的遮罩职责 |
| [Unity官方UTS高光](https://docs.unity3d.com/Packages/com.unity.toonshader@0.11/manual/Highlight.html) | 把高光许可与暗部高光强度分开 | 文档标0.11.1-preview；不能当作Blender插件 |
| [VRM Consortium MToon 1.0规范](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_materials_mtoon-1.0/README.md) | 描边单位、分色位置与过渡宽度的明确合同 | 本轮新增文字依据；普通EEVEE实现未验证 |
| [Blender作者VRM插件源码](https://github.com/saturday06/VRM-Addon-for-Blender/blob/main/src/io_scene_vrm/editor/mtoon1/property_group.py) | 定位描边模式、几何节点及Alpha／UV接口 | 只读指定符号；节点图未读，便利MMD转换会重建材质 |
| [MMD Tools维护者项目](https://github.com/MMD-Blender/blender_mmd_tools) | PMX材质语义、兼容表、物理与IK限制 | 不同源码快照与本机4.5.14须核对 |
| [Blender Principled](https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html)／[5.2刚体排错](https://docs.blender.org/manual/ar/5.2/physics/rigid_body/tips.html) | 金属／布料职责，碰撞和约束排错 | 本轮相关记录仅索引正文片段，直开失败；不可声称全文读完 |

新增一条有用的描边知识：MToon把世界米制线宽与屏幕高度比例分开。按后者推导，2px@1080对应比例2/1080，保持比例在2160高会变成4px；跨分辨率恒定2px需要另算比例。这个例子是单位推导，不是作者推荐线宽，也没有改变当前人物描边。详见[本轮NPR来源账本](research/TEXT_NPR_SOURCE_DISCOVERY.json)。

物理分支主要完成去重，只补到Passive刚体Animated和中途启用约束的排错入口；没有得到适用于当前衣发的“万能参数”。6→12子步仅登记为有条件对照，详见[物理来源账本](research/TEXT_PHYSICS_SOURCE_DISCOVERY.json)。

原神／鸣潮专属技术需要继续核对公开实现的作者、贴图语义与许可；现成三渲二预设可提供可运行的对照。社区复刻、规范借鉴、作者原始Shader和本机实测分开登记，避免用风格名称代替技术证据。

## 首批可续接工作

| 优先级 | 问题 | 下一步 |
| --- | --- | --- |
| P0 | 脸影形状与真实遮挡 | 追踪最新版SDF／UV／头轴，确认缺口后做局部阈值图 |
| P0 | 发带许可与暗部强度 | 选一簇发束，仅改变0／1许可，不再叠加第二条高光 |
| P1 | 金属与布料层次 | 先对已有PBR／Sheen／球面贡献做消融 |
| P1 | 黑线近远景与分辨率 | 先声明单位与测量目标，再决定是否研究新的描边实现 |
| P2 | 快速衣发稳定性 | 可重复问题出现后，先查初态与碰撞，再比较子步 |

以上全部保持`hypothesis`，未新增渲染或物理模拟。[原E1–E3](NPR_NEXT_EXPERIMENTS.md)仍保留，其中发束法线实验按实际断裂问题触发。舞台、镜头、字幕和后期继续在各自手册内维护；当前先让人物材质与受光有可归因的改进。

## Codex使用与校验

在仓库根目录执行，工具只做本地查询，不联网、不启动Blender、不执行抓取或实验命令：

```powershell
python -m scripts.learning_queue plan --limit 3
python -m scripts.learning_queue lookup --url "https://mooatoon.com/en/docs/Tutorial/AddStylizedHairHighlights"
python -m scripts.learning_queue check --check-artifacts
```

`plan`最多列出指定数量的可推进卡；未声明scope的历史卡保持静帧→动态→重开的旧计划语义。当前静帧任务使用`--scope stills`或统一工作入口，不能为完成状态自动恢复视频。`blocked`解释依赖未完成／失败的情况。`lookup`在下载前返回既有阅读范围。去重忽略跟踪参数与章节锚点，并合并同版本GitHub raw／blob形式，保留有意义的查询和版本路径。

`check`验证来源、链接、依赖和阶段前置条件。通过状态要求实际实验工程SHA，不能用选材清单代替。复用代码还须固定提交或内容指纹并核对许可。阶段证据是JSON报告，其必要字段如下；正式报告路径及哈希再登记在卡的`evidence`中：

```json
{
  "card_id": "对应卡ID",
  "baseline_sha256": "实际基线工程的64位SHA256",
  "stage": "still",
  "result": "passed",
  "scope": "实际模型、版本、画幅、分辨率、帧号及人工抽样范围",
  "artifacts": [{"path": "实际产物绝对路径", "sha256": "该产物64位SHA256"}]
}
```

后续阶段分别使用`motion`、`reopen`、`integration`。工具核对报告归属、阶段、结果和文件；`--check-artifacts`另核对实际内容哈希。结构与完整性检查不判断报告中的视觉结论是否成立，仍需制作检查与独立验收，美术认可单独保留。

默认每轮只推进最多3张卡，每个问题先选1–2个一手来源。子智能体分别负责来源与去重、一个可关闭实现、独立验收；根线程控制输入版本和整合。同一个生产文件只有一个编辑者。子任务交接只带问题、基线、相关节、假设和验收范围，避免重复读取全库。

第三方全文／图片／视频只私人缓存一次；repo保存原创归纳和来源。遇到付费、等级限制或持续连接失败就记录访问边界，切换可用的一手资料。每轮用[知识审计](../scripts/audit_knowledge.py)验证队列与索引，并更新离线Atlas；研究结果不自动改变生产预设或成片质量状态。
