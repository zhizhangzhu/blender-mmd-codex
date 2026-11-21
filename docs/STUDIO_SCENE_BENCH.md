# 安全开工程、角色语义映射与静帧试验台

2026-11-20，SPEC第二阶段。代码为`studio_scene_contract`、`studio_bench`、`studio_scene_worker`；[配置目录](../catalog/scene_benches.json)连接五个有界配置，包括本轮Goo原源对照与新候选基线。新候选expected对应保存后的值，不可重复套旧源配方。此工具验证制作方法的可执行性，不自动实现人物shader迁移或授予美术通过。

## 运行边界

纯Python契约与计划不启动Blender。实际检查／渲染要显式`--execute`，按profile使用已有官方5.3或精确固定的Goo5.2.1便携进程；不改全局偏好。Goo描述版本字符串另以`version_tuple`校验机器版本，并核构建及必要专用节点。启动顺序为校验源与运行时→注册必要MMD相机RNA→关闭脚本自动执行地打开源文件→静音所有场景及嵌套合成组的File Output→检查映射→执行指定静帧。

每个case重新打开同一指纹源，不累加上一case的姿态或开关。不保存输入工程，不输出动画／视频，不建立或烘焙物理。活动刚体、Cloth、Soft Body、Fluid、Dynamic Paint、粒子修改器及GN Simulation会在求值前被保守拒绝，viewport/render任一启用均算活动；开关之后再检查。检查不声称证明任意新节点／第三方模拟的安全性。

支持当前固定版本的EEVEE，其他引擎拒绝。实际尺寸、samples、DOF和MB写回报告；PNG尺寸也实际解码核对。当前仅PNG诊断图，不以缩略试验代替最终分辨率验收。

## 明确映射而非猜名字

profile的actors逐个声明ID、场景内精确mesh、可选armature及材质角色。声明rig时核实际Armature修改器，允许两人同名骨骼及无关的第一个rig。材质角色来自读过的数据／人工判断；共享材质有冲突角色、材质不属于该人物、控制影响未声明对象时拒绝。

需要控制舞台材质时，舞台也可作为无armature的显式mesh组；本轮`hesperides_stage`声明98个实际使用者。该字段的组数不能当成人物数量，亦不因加一组而重建舞台。

现有native53-duet-v3配置按实际slots、rig和已审计分类写出；脸、眼白、瞳孔、嘴内另作精确覆盖。混合饰件、皮革和水晶保留other及说明，不把历史trim标签冒称纯金属。语义映射不会改材质／UV／贴图，也不会给新角色自动套旧SDF。

## 五类可关闭控制

| kind | 精确定位与验证 |
| --- | --- |
| node_input | material/node/socket标识及expected；拒绝歧义、linked、driven、animated，支持数值／向量／布尔 |
| light_energy | 灯对象与expected功率；拒绝共享Light Data及目标驱动／动画 |
| object_hide | 对象hide_render与expected；拒绝目标驱动／动画 |
| modifier_enabled | 对象／修改器show_render与expected；拒绝目标驱动／动画与触发活动模拟 |
| glow_bypass | 指定场景Glare；Image回接其实际输入，Glare效果出口接RGBA零；不以全体mute替代 |

赋值后及渲染后读回控制；输入类型、有限值、角色归属、目标值或范围不符则停止。Windows大小写相同case不允许覆盖，产物统一`case-<id>`前缀，避免与report/inventory/launch文件冲突。

Map Range等节点的标量与向量插口可能同显示名。此时显式填`socket_match: "identifier"`并用实际RNA identifier；默认仍拒绝显示名歧义。数值比较允许float32存储舍入（相对1e-7、绝对1e-6），并不允许有意义的参数偏差。Glare若有Highlights或额外出口的消费者，不能把仅处理Image/Glare称为完整关闭；本轮Goo源已核Highlights均无消费者，publish还会明确拒绝未声明分支。

相机marker在求值时临时解绑，求值后明确选择约定机位并复查相机及祖先driver。记录完整求值矩阵、焦距、sensor、shift、DOF和driver；不把机位变化说成纯材质对照。mesh_signature是viewport求值网格／世界矩阵的有界签名；完整源文件保护以原字节SHA为准，简短Action摘要不冒充完整动画等价证明。

## 命令

在仓库根目录使用已有解释器：

```powershell
$studioPython = 'D:/codex/workspace/blender-runtimes/5.3.0/blender-5.3.0-windows-x64/5.3/python/bin/python.exe'
& $studioPython -X utf8 -m scripts.mmd_studio benches
& $studioPython -X utf8 -m scripts.studio_scene_contract plan --profile presets/benches/fixture-a.json
& $studioPython -X utf8 -m scripts.studio_bench inspect --profile presets/benches/native53-duet-v3.json --output 'D:/codex/output/New-Inspect' --execute
& $studioPython -X utf8 -m scripts.studio_bench render --profile presets/benches/fixture-a.json --output 'D:/codex/output/New-Bench' --execute
```

省略`--execute`只输出命令计划，既不建输出目录也不启动进程。输出必须是新目录且不能包住源文件。失败保留launch/report/log及已完成case，不覆盖旧结果。`--timeout`限制整个独立进程，未知API明确报错，不静默降级。

profile schema_version1包含source指纹、仓库runtime配置、scene与camera、actors、switches、cases、render及limits。源路径为本机绝对路径；runtime为仓库相对JSON路径。输入profile、源文件、worker和runtime均有指纹，启动器结束再核源与profile不变。

## 独立复测

`verify`需要先有同源、同控制契约的通过run。复制原profile另存新文件，增加：

```json
"verification": {
  "report": "D:/codex/output/Existing-Bench/report.json",
  "sha256": "填写该报告实际SHA256",
  "max_abs": 0.005,
  "mean_abs": 0.0001
}
```

阈值须在复测前声明且说明依据；不得为了通过失败后抬高。再用`studio_bench verify --profile 新profile --output 新目录 --execute`。程序核旧报告、旧图片指纹与契约，独立进程逐case重开源，比较相机、姿态、有效设置与PNG数值。比较空间为Blender解码PNG的float RGBA，不是HDR光照或审美相似度。worker／契约改变时须先建立新的基线。

该复测验证“同一已存输入可以重现指定诊断”，不是验证本工具尚未保存的新生产候选。联系表初始seen=false；只有亲看后才另记审阅范围。

## 原创夹具与真实工程

`create_studio_fixture.py`在新的临时目录生成两套原创双rig代理场景与profile。两人同名骨骼，另有无关first rig、嵌套File Output、frame10相机marker，以及不同材质和机位。A/B用来验证同一工具可适应重命名和变换，不当作高质量MMD画面或跨作品美术迁移。

真实native53-duet-v3只在4290、源相机／DOF做有界控制，源仍是未完成迁移的试作。成功执行不更新现行候选、不表示黑斑已修复或新人物风格已认可。

## 本机构建的新发现

实际读取本机02f0899d78e3的节点接口发现：Glare类型使用`inputs["Type"]`菜单，旧glare_type属性不可用；合成混合可用ShaderNodeMixRGB；合成最终输出为节点组输出；File Output需建立file_output_items。已在原创夹具实跑核对，不把其他版本的同名接口当成本版本保证。

官方API说明用于确认[关闭脚本地开工程](https://docs.blender.org/api/latest/bpy.ops.wm.html)及[求值依赖图](https://docs.blender.org/api/current/bpy.types.Context.html)的职责；本机接口和运行证据决定实际兼容范围。

本轮原创归纳、失败原因、实际run与未测范围保存在[证据账本](research/STUDIO_SCENE_BENCH_2026_11_20.json)。代理夹具成功、真实工程局部执行和用户美术认可分别记录。
