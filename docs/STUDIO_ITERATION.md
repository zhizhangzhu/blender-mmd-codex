# 从参考到作品经验

2026-11-20。沿用[SPEC](../SPEC.md)、[场景试验台](STUDIO_SCENE_BENCH.md)和[长期工作入口](STUDIO_WORKFLOW.md)。这一层连接实际制作，不增加用户重复确认；`--execute`是命令行防误运行开关，当前任务已授权时由AI执行。

## 冻结预测后再渲染

先亲看参考，按`reference_study`记录观察、原因假设、可调整目标与拒绝条件。可用内部基线研究一个具体缺陷，但须明确不是外部作者风格复原。视频参考先提取明确时间点、亲看图像，图审板目前接收本地图片研究。

`studio_iteration.prepare`接收JSON方案：`schema_version,id,title,study:{path,sha256},profile:{path,sha256},baseline_case,target_ids,preserve,experiments,limits`。profile是精确绑定的bench配置；baseline须无override。每轮1–2个实验，每个含`id,compare_to,hypothesis_id,target_ids,prediction,change_kind,overrides`。`change_kind`为`ablation`或`design_option`；消融只改一项，或明确命名同一逻辑组。每个实验与baseline同帧，实际相机、DOF、色彩、采样与尺寸也须一致。

可选`review_regions`含`id,label,reference:[x,y,w,h],cases:[x,y,w,h]`，均为0–1归一化坐标。区域按原图片比例显示，不拉伸为同一正方形；不同素材的语义区域不冒充像素对齐。

```powershell
python -m scripts.studio_iteration prepare --plan D:/codex/output/New-Study/plan.json --output D:/codex/output/New-Study/iteration
python -m scripts.studio_iteration check --iteration D:/codex/output/New-Study/iteration
python -m scripts.studio_iteration run --iteration D:/codex/output/New-Study/iteration
python -m scripts.studio_iteration run --iteration D:/codex/output/New-Study/iteration --execute --timeout 1800
python -m scripts.studio_review_board --iteration D:/codex/output/New-Study/iteration
```

无`--execute`仅预览派发。实际运行必须用新目录；源、参考媒体、研究、方案、配置和代码有指纹。失败保留日志与已有图片，失败或不完整运行不能图审结案。修改预测或输入须新开一轮，不能对旧运行倒填计划。

## 图审、反馈与结案

主控实际看全图和关键区域后，写独立JSON图审。字段为`schema_version:1,iteration_id,run_report_sha256,reviewer:{kind:ai,identity,scope},seen_cases,targets,selection,reasons,next_action,user_approval:false,user_feedback_provenance:null,hypothesis_outcomes`。

每个target含`target_id,verdict:improved|unchanged|regressed|inconclusive,observations:[文字],tradeoffs:[文字]`。每个experiment必须有`experiment_id,hypothesis_id,outcome:supported|rejected|inconclusive,reason`；不能只选最好看的一张就称原因已验证。选择方案须亲看baseline和该方案；声称改善须看全部候选。模型身份填实际已知身份，不从配置推荐反推。

```powershell
python -m scripts.studio_iteration review --iteration D:/codex/output/New-Study/iteration --review D:/codex/output/New-Study/ai-review.json
python -m scripts.studio_iteration close --iteration D:/codex/output/New-Study/iteration
python -m scripts.studio_lessons register --iteration D:/codex/output/New-Study/iteration --expected-sha256 <studio.json当前SHA> --route lighting --tags 轮廓光 白衣 礼堂
python -m scripts.mmd_studio lessons --task lighting --query 白衣
```

结案固定图审、对照板、HTML与图片，经验仅为`single_case`。写入现有`studio.json.lessons`时核登记表原SHA并原子替换；检索重新核经验和运行来源，损坏记录显示错误，不直接带入下次判断。经验数量不代表美术质量或跨项目能力。

用户后续反馈用独立`user-feedback`命令及完整图审结构，`reviewer.kind=user`，另有`user_feedback_provenance`绝对文件路径与`user_feedback_provenance_sha256`，包括否定反馈也保留出处。AI不能代填认可。后补反馈不改写既有lesson；下一轮结合它重新评估。程序只能校验出处完整性，不能认证人类身份。

## 保存作品

诊断worker仍不保存源。选定方案通过后用`studio_publish`的`publish`命令、独立新目录和显式`--execute`保存新候选；只允许已图审选择的材质输入、灯能量和明确辉光分支变更。`reopen`另起进程读取新SHA，核保护项、控制读回与同条件PNG差异，不能以保存成功代替重开验证。

Goo双人本轮仍限定4290，1920×1080、64采样、源DOF、无MB；不重算物理、不输出视频、不恢复眼透。新候选可供用户评价，程序通过与AI选图均不等于用户美术认可。

```powershell
python -m scripts.studio_publish publish --iteration D:/codex/output/New-Study/iteration --case strong_stage --output D:/codex/output/New-Study/final --execute
python -m scripts.studio_publish reopen --iteration D:/codex/output/New-Study/iteration --case strong_stage --publish-report D:/codex/output/New-Study/final/publish-report.json --output D:/codex/output/New-Study/reopened --execute
```

case须替换为该轮实际选择；所有输出目录须是新目录。正式PNG实测16位RGBA；重开误差阈值在request预声明为max_abs=.005、mean_abs=.0001，不能看到结果后放宽。发布worker当前正式实测范围为Goo双人4290，诊断夹具通过不能自动认证它在别的工程的保存适用性。
