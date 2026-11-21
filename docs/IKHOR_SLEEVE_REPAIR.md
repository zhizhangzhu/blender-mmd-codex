# 伊科尔袖口：从穿模定位到局部修正

2026-11-14，记录定位、失败实验及 **production-v6修袖／production-v7字幕修复后的历史完成基线**。后继[Clean production-v2](CLEAN_GAME_CHARACTER_REFINEMENT.md)两版五秒现已全新渲染并完整输出，原袖几何与动作严格保留，没有新模拟或扩大零碰撞认证；当前交付以[current_state.json](../catalog/current_state.json)为准。

v6已完成独立delta核查、303帧几何扫描，以及双腕各300张诊断图的生成；并排诊断片已实际解码300帧。Root与独立复核已看左右同一组33时点的联系表、手部参考表及关键800×800生产shader图，未见原先皮肤钻出灰蓝不透明侧壁的破口或大片反折。掌根与金色内衬尖口仍有原始交线记录，不能称完全零交叉，也不因统计非零继续扩大袖形。

**该历史基线的1080p原生beauty300已从v6完整重渲，两版视频在其captions-5s-v3。** v7仅修正遗漏伊科尔的字幕Cryptomatte名单，38项严格差分确认beauty依赖不变；完整v6 beauty可据此复用，正确双人actor覆盖率则从v7重新渲染。该基线两版各300帧全解码／音轨／色彩与字幕版接缝检查通过，人工查看两版各12时点、四处字幕边界共32帧连续图及原生腕部关键帧，见旧交付根`manual-review.json`。物理与几何证据仍保留原范围和非零接触，不由成片完成升级为零交叉；全曲未完成，美术未获猪猪认可。

## 固定输入与候选

| 角色 | 文件／SHA256 |
|---|---|
| 不修改的原PMX | `D:/codex/output/MMD-Ikhor-Model-v1/source/Ikhor/Ikhor.pmx`；`ebba744cee847c16cfe5be037e7464d4f701c8edb2f5033e7de5730bd6654a52` |
| 原生30fps基线 | `D:/codex/output/MMD-Ikhor-Model-v1/motion-v1/native-import-30fps.blend`；只用这份未Build基线，读取SHA另入物理报告 |
| 原便携角色 | `D:/codex/output/MMD-Ikhor-Model-v1/motion-v1/physics-v3/Ikhor_Hina_Portable.blend`；`f864ad0efa936e3e1dde9462bdf42a0245d00158180b3b3c49ee5acf79cc5a4f` |
| 拒绝的v4／差分基准 | `D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/production-v4/Franken_Aksiniya_Ikhor_Bold_Wedding.blend`；`283acdf2f1063fae32b0ed49caed07952706ff4d7b9ed1675490fa7ad021a0c1` |
| v6修袖与完整beauty源 | `D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/production-v6/Franken_Aksiniya_Ikhor_Bold_Wedding.blend`；`201e2632befaf0a16f17b931963626a91bbc6b8f7e58d148d5047298a530de01` |
| v7完成基线工程 | `D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/production-v7/Franken_Aksiniya_Ikhor_Bold_Wedding.blend`；`f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692`；只修字幕名单，完整继承v6袖形／动作 |

动作仍为Full HinaSuzuki原生VMD，导入scale=0.08，原相对站位、手／前臂主动作不改。审查范围为4140–4439、1080p60、300帧／5秒；guard为4139–4441共303帧。全曲body／morph轨保留，不代表全曲物理已验证。

## 问题与定位

猪猪指出4290帧抬掌时，皮肤从外层蓝色喇叭袖侧面露出。最初的1049项工程核查、72帧转头／移灯／绕拍并未覆盖这处服装故障。骨骼有限、烘焙等价、可重开都不能代替网格穿模检查。

分开检查两种结构：衣物子网焊接位置后取得的12点窄内袖／前臂接口环，位于腕后约4.5cm，仍与腕轴大致对齐；它不是外侧喇叭袖的可见出口，不能用这个环证明外袖没有穿。4290帧右接口环的轴线偏差约3.06°、轴交点距环心约2.91mm；外袖烘焙后相对原生最多位移8.34cm。外袖出口可能有封闭内外衬，需用真实衣－手交线与画面核对。青色外观包含受光与边缘光，不能把几何反折误判为发光材质问题，也不能靠降低发光遮掩。

每侧 `Bone_Sleeve01`、`Bone_Sleeve02` 是共同父级下的并列分支，各带一个 `錘` 子骨，不是01→02的链。局部修复的骨白名单共8根。原生袖子刚体是mode1，跟随手首胶囊的关节参考；袖骨父级则在前臂。实际源码确认碰撞忽略mask的True表示“不碰撞”；原袖组4忽略组0，原腕／臂属于组0，单独加粗这些胶囊不会产生需要的接触。

## 三种检查必须互相补充

1. **原生动作、原物理、局部候选同帧对照。** 只切换袖子Action，保留生产材质与灯；关闭DOF、运动模糊、后期和舞台遮挡。`review_ikhor_sleeve_controls.py`用于这一步，不保存生产工程。
2. **真实网格交线。** 对求值后的袖面与手部三角形求交，并沿手腕轴区分腕后与掌前；相机射线用于筛选可能可见的交线。总三角形对数会重复计数，不能等同穿模面积。原设计的尖袖口、包边可能与掌侧发生局部接触，不应为追求全模型零交线而破坏服装。
3. **整段连续画面。** `render_ikhor_sleeve_review.py`输出双腕各300张无模糊近景；`package_ikhor_sleeve_review.py`编码左右并排诊断并生成明确选帧的联系表。帧全数生成／解码不等于人工逐像素看过所有画面，人工范围必须另记。

脚本时间基准为输出60fps的4140–4439。对本次固定片段，`VMD30 = 329 + (F60 - 1)/2`，导入的Blender30帧再加1；例如4290对应VMD2473.5／导入2474.5。不要把60fps帧号直接送进30fps求解器。

## 已完成的实验与失败边界

| 实验 | 实际改变 | 观察与结论 |
|---|---|---|
| 原生袖参考 | 仅8袖骨恢复无物理姿态 | 4290袖根大片穿透改善；全300扫描仍发现左侧4219–4225可见腕后交叉，不能直接作为修复 |
| 只恢复平移／只恢复01 | 分离平移与分支贡献 | 单帧仍有明显外袖反折，均未采用 |
| 局部物理v1 | 8动态袖、2前臂锚、4皮肤接触体；主袖mode1 | 4290右腕后仍52对交叉，袖根可被推离约4–5cm；退回 |
| 局部物理v2 | 4主袖改mode2 Physics+Bone、4錘仍mode1 | 4290右腕后0／左交线0；但全300右17帧腕后、7帧可能可见，左12帧腕后、8帧可能可见；退回整段 |

v2真实局部求解包含14刚体／8动态／34约束，源30fps顺序模拟2279–2550，120帧预滚，导出2399–2550，再映射为输出60fps的4139–4441。皮肤接触体按模型实际手／前臂顶点建立收缩凸包，不以小圆柱代表整只手。仅替换8袖通道，其他骨骼303帧保留误差为0；这项等价检查仍不能证明袖子不穿。

关节坐标必须实测。v2实际Build后的关节world frame与原PMX rest经前臂pose/rest映射的误差约1.19e-6，四关节启用且加入世界，01角限±2°、02±8°。骨骼相对其父级的24°不能直接解释成关节超出±2°，两者参考坐标不同。

L4220手掌相对前臂弯曲约99.36°。进一步定位后，坏面并不在12点内接口环，而在强混肘的外袖根面：相关点的肘权重约75–92%，8袖骨总权重仅约8–25%。例如21146点按最近皮肤面法线估算内陷约4.94mm，21077约1.91mm，21148／21169约0.99mm；这是定位估算，不是全三角形的精确最大穿深。大幅转动低权重袖骨会先破坏整片外形，原生形状又同样碰掌，减小物理幅度并不足以解决。

面内抽样进一步发现，4221的部分袖三角形内部估算可达约8.88mm，端点却多数已在skin外；只推内陷顶点会留下面横切弯掌的问题。UV缝重复点如21148／21169、21078／21170又具有相同rest位置与骨权重，必须同步修正，不能推开一侧造成开缝。这些都说明应检查真实边／三角面，而非只看顶点与skin的距离。

## v6实际采用：局部物理＋右限幅＋左单shape

这三层各有明确作用，不能合称全身纯物理求解。参数入口是 [ikhor-sleeve-repair-v1.json](../presets/quality/ikhor-sleeve-repair-v1.json)，生产器是 [ikhor_sleeve_repair_v1.py](../scripts/ikhor_sleeve_repair_v1.py)。

### 真实局部物理

- 实际14刚体：8袖动态、2前臂参考锚、4掌部／前臂skin接触体；34约束，未重建全514体。4根有网格权重的主袖使用MMD原生mode2（位置由父级骨架保持、旋转来自物理）；4个无直接网格权重的錘仍mode1。
- 锚16／20由手首改为`Bone_ForearmTwistA01_R/L`；01角限±2°，02±8°，保持原袖质量／阻尼，去掉跨左右的`補`辅助环。固定8骨为两侧`Bone_Sleeve01/02_L/R`及各自`錘`，不是手骨或前臂骨。
- 新接触体是原`手`材质皮肤顶点的凸包，分掌部与前臂，96%缩放、1mm margin。掌部选取腕轴-15至60mm、腕权≥0.25的皮肤点；前臂从肘内缩15mm至腕前6mm。新组6与加权袖组4双方不忽略；它们是有限的kinematic接触近似，不认证全部手指／皮肤碰撞。
- 30fps连续模拟2279–2550、预滚120帧、视觉导出2399–2550；12 substeps、60 iterations、time_scale=1。清理实时world／刚体／约束后按原时间映射转60fps。模拟到导出的矩阵误差约`1.01e-6`。

实际参数与坐标证据分别在`D:/codex/output/MMD-Ikhor-Sleeve-Repair-v1/local-v2/local-physics-report.json`和同目录`rest-frame-audit.json`。后者验证了前臂native pose/rest映射与实际Build关节frame，不能用bone basis角替代这个检查。

### 明确的物理后右袖限幅

仅右侧加权01／02相对native作平滑角幅限制：`angle_out = limit × tanh(angle / limit)`，01 limit=4°、02 limit=10°，保留模拟旋转轴与时间信号；左侧维持上述Mode2结果。其余衣发旧物理和全部主手动作保留，303帧非袖骨矩阵误差为0。

**未采用wrist-follow。** `windows=[]`；25°转袖／gain网格搜索是失败诊断记录，没有把跟满腕转、额外开袖平移或其窗口接入v6。3shape跨姿态union也在执行前停止，未生成生产数据。不能把这些曾讨论的方案当作当前参数。

固定BodyAction输入为`D:/codex/output/MMD-Ikhor-Sleeve-Repair-v1/corrective-L-preview-v1/Ikhor_Sleeve_Diagnostic_fitted_repair.blend`，SHA256为`eeb88de34d39e65be66fcdb0f741f4e81498d2b2d7901ef7932ba3a06c664779`，Action名为`Ikhor | sleeve diagnostic | fitted_repair`。

### 左侧唯一新增corrective

固定名为`Sleeve repair | L wrist flex clearance`。白名单从源mesh独立重建：`sum(Bone_Sleeve01_L、Bone_Sleeve02_L权重)>0.001`，共573点，其中398点有非零差分。Basis、拓扑、UV、权重、原有shape坐标、材质、皮肤和手势不改。

拟合使用skin最近面法线、相交面内部与边上的采样，在邻域平滑后同步同rest／同权重的UV缝点，不焊接拓扑。最大rest差分12.02794mm，4220最大实际位移12.00006mm，单独应用该shape时573点以外的求值点位误差为0。4220原型可见腕后交线16→0，是单帧结果，不能推广为全段零交叉。

| 输出帧 | value | 插值与handles |
|---:|---:|---|
| 4210 | 0 | BEZIER；两端FREE水平柄，位于相邻区间1/3处 |
| 4218 | 1 | 同上 |
| 4225 | 1 | 同上 |
| 4233 | 0 | 同上；区间外CONSTANT外插为0 |

这是C1平滑进入／离开与中间平台；原Morph Action复制后仅增加这条value曲线，旧曲线／handles保留。

固定数据为`D:/codex/output/MMD-Ikhor-Sleeve-Repair-v1/corrective-L-preview-v1/corrective-data.json`，SHA256为`0ea6bf3741c7c18be36902da5b574aae7cefc7027ce39e29761cc0457b97bea7`。同目录`corrective-export-report.json`绑定导出、原型与actor；原型在`corrective-L-prototype-v3/corrective-prototype.json`。这些JSON／report和blend落盘后固定，后续变更必须新目录／新版本，不能原位更新。

## 实际验收范围与判断

独立 [verify_ikhor_sleeve_repair.py](../scripts/verify_ikhor_sleeve_repair.py) 对v6的49项delta检查通过，报告为v6目录的`master-verification.json`。源v4独立重建左573白名单、8袖任意正权重支持集1146点；原29959点中的28813个非袖base求值点逐303帧SHA一致，非袖骨／旧Morph误差0。新增398点坐标、固定shape名、四关键点及handles逐项对固定JSON一致。原Basis、UV、权重、旧shape、渲染可达材质、灯、镜头严格保留；仅明确的无用户孤立Aether图／组清理有单独追溯例外。

Solidify生成的壳不能混入29959点白名单。验证器在独立内存中暂禁双方`mmd_edge_preview`后比较base求值点，另严格比modifier状态，不保存工程。不能假设生成壳索引取模就是原顶点。

`D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/sleeve-review/geometry-verification.json`绑定实际v6 SHA并完成303帧完整／finite几何扫描；raw flag全部保留。raw扫描中的L4221–4225仍有交线及“可能可见”标记。Root与独立人工随后看原shader图，判断其位于掌根与金内衬尖形开口接触处，未见皮肤越过灰蓝侧壁／银环或大片反折，因此不再仅为pair数0继续扩形。这是画面观察与统计解释，**不是宣称几何完全无交叉**。

连续证据位于`D:/codex/output/MMD-Ikhor-Sleeve-Repair-v1/continuous-v6/`：左右各300张480×480／16 samples、合计600张无模糊诊断图；`Both_Wrists_Unblurred_5s.mp4`实际解码300帧、960×480、60fps。它临时关闭舞台、DOF、MB及后期，不是1080p最终beauty。`wrist-video-verification.json`列出33个选帧时点，左右各取同一组33帧；已查看联系表、手部参考表及关键800图，不把这些抽样称为人工逐像素审过600张。后续正式beauty的原生4190／4220／4290／4318腕部也已抽看，未见原先侧壁皮肤破口或大片反折；最终用户美术认可与这些抽样验收分开。

## 复用命令与输入契约

所有命令均用独立后台进程；不改偏好、不停GUI、不把后台工程称为GUI当前场景。`--output-dir`必须换新目录，以下是命令结构，**不要对现存v6／固定输出重跑或覆盖**。

```powershell
$blender = 'E:/tools/Blender Foundation/Blender 5.2/blender.exe'
$repo = 'D:/codex/workspace/blender-mmd-codex'
$profile = "$repo/presets/quality/ikhor-sleeve-repair-v1.json"
$replay = 'D:/codex/output/MMD-Ikhor-Sleeve-Repair-Replay-NEW'
$replayTemp = 'D:/codex/temp/MMD-Ikhor-Sleeve-Repair-Replay-NEW'
& $blender --background --disable-autoexec --python-exit-code 1 --python "$repo/scripts/ikhor_sleeve_repair_v1.py" -- --profile $profile --phase local-rebake --output-dir "$replay/local-v2" --temp-dir "$replayTemp/local-v2"
& $blender --background --disable-autoexec --python-exit-code 1 --python "$repo/scripts/ikhor_sleeve_repair_v1.py" -- --profile $profile --phase rest-audit --output-dir "$replay/local-v2" --temp-dir "$replayTemp/local-v2"
& $blender --background --disable-autoexec --python-exit-code 1 --python "$repo/scripts/ikhor_sleeve_repair_v1.py" -- --profile $profile --phase rig-samples --physics-dir "$replay/local-v2" --output-dir "$replay/actor"
& $blender --background --disable-autoexec --python-exit-code 1 --python "$repo/scripts/ikhor_sleeve_repair_v1.py" -- --profile $profile --phase candidate --mode fitted_repair --physics-dir "$replay/local-v2" --output-dir "$replay/actor"
```

生产器只用于这里审计过的native30fps未Build基线；不能把60fps portable或舞台master当作它的输入。PMX／portable有固定SHA约束，native文件实际读取SHA写入报告。`rig-samples`读取preset的`output_dir/native-sleeve-303.json`作为无物理参考，`--output-dir`只改当前阶段输出，不会同步改这个参考根。若重建参考，应先用`--phase audit`输出到新根，并在任务副本preset中明确绑定该新根；不得误用旧时间轴或旧缓存。

该native基线原有`A`骨自追加变换循环。工具复用已审计的`repair_self_inheritance`，只在独立内存副本中去掉这条无效生成约束并记录原值，保留其余IK；不修改原PMX。打开时的旧依赖循环提示与修正后的求值状态应分开记录，不能用旧全场物理脚本的“全部mute IK”处理替代。

复现固定v6接线时，应优先使用上面已冻结的BodyAction与JSON，不用重新拟合冒充同一结果。接线器 [apply_ikhor_sleeve_repair.py](../scripts/apply_ikhor_sleeve_repair.py) **只接受被拒绝的v4 SHA**，会新建工程；不能对v6重复迁移。

```powershell
$v4 = 'D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/production-v4/Franken_Aksiniya_Ikhor_Bold_Wedding.blend'
$fixed = 'D:/codex/output/MMD-Ikhor-Sleeve-Repair-v1/corrective-L-preview-v1'
& $blender --background $v4 --disable-autoexec --python-exit-code 1 --python "$repo/scripts/apply_ikhor_sleeve_repair.py" -- --actor "$fixed/Ikhor_Sleeve_Diagnostic_fitted_repair.blend" --actor-sha256 eeb88de34d39e65be66fcdb0f741f4e81498d2b2d7901ef7932ba3a06c664779 --action 'Ikhor | sleeve diagnostic | fitted_repair' --repair-report "$fixed/corrective-export-report.json" --corrective-data "$fixed/corrective-data.json" --output-dir "$replay/production"
```

不要用带shape的`Ikhor_Sleeve_Corrective_Preview.blend`替代上述`--actor`：它供几何预览，固定JSON绑定的actor_source是无shape的fitted-repair文件。接线只替换Ikhor的指定Action、复制原Morph Action并追加固定shape／value曲线，不append整个actor scene或重做材质。

独立核查及无模糊连续审查分别运行，报告路径也必须新建。下列使用既有v6作只读输入；诊断渲染不保存源工程。

```powershell
$v6dir = 'D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/production-v6'
$v6 = "$v6dir/Franken_Aksiniya_Ikhor_Bold_Wedding.blend"
& $blender --background --disable-autoexec --python-exit-code 1 --python "$repo/scripts/verify_ikhor_sleeve_repair.py" -- --source $v4 --current $v6 --repair-report "$v6dir/sleeve-integration.json" --output "$replay/master-verification.json"
& $blender --background --disable-autoexec --python-exit-code 1 --python "$repo/scripts/audit_ikhor_sleeve_geometry.py" -- --candidate $v6 --frames '4139:4441' --output-dir "$replay/raw-geometry"
& $blender --background $v6 --disable-autoexec --python-exit-code 1 --python "$repo/scripts/render_ikhor_sleeve_review.py" -- --output-dir "$replay/continuous" --start 4140 --end 4439 --size 480
```

几何脚本接受带相机master；对无相机portable需显式`--camera-reference`同时间轴生产master，否则可见性必须为`null`，不能把0理解成不可见。并排打包器 [package_ikhor_sleeve_review.py](../scripts/package_ikhor_sleeve_review.py) 读取完整左右300PNG，以`--root 新连续目录 --frames 明确选帧列表`编码和解码；它是普通Python／FFmpeg诊断打包，不是Blender生产构建器，不登记新成片。

## 重新进入生产的条件与本次完成结果

- 使用新master，独立重开核对：除固定8袖通道及明确的局部corrective shape／其value曲线外，原动作曲线和插值柄、303帧非袖姿态、原Morph、Basis、UV、权重、材质、灯与镜头保持不变。shape只能修改从源袖组独立重建的顶点白名单，其他求值顶点不动。新脚本 `verify_ikhor_sleeve_repair.py` 与原1049项基线证据分别保存。
- 全300帧网格扫描标出最差帧；看双腕无模糊近景、窗口前后连续帧，再看正式beauty。v6已有600张连续腕图与300帧诊断片，不把33时点抽样扩大为人工逐帧全部审过，也不只验证截图4290。
- 已退回v4的原生帧、缓存、分片与排队后期一律不复用；最终300帧已从v6和全新`final-cache-v2`完整重渲，v5只是中间候选。最终v7仅改字幕名单的38项严格差分，支持复用该批v6 beauty；后续材质变化不能再借此复用旧beauty。
- 交付报告记录修复范围、真实物理与后修正的区别、人工抽样和残留接触。未实际完成的新视频不得更新为最新交付。

本次完成结果位于`D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/captions-5s-v3/`：`Franken_Duet_5s_Ikhor_Wedding_REVIEW.mp4`与`Franken_Duet_5s_Ikhor_NoCaptions.mp4`。`captions-5s-v2`因旧actor cache遗漏伊科尔、后台字幕盖人而退回，不能因它技术解码通过而当正确结果。v7重新渲染的300帧actor保留原Alpha、DOF、MB，逐人头／身ROI全300帧正例及旧缓存负例均已核对，详见[制作记录的字幕修复](IKHOR_BOLD_WEDDING_PRODUCTION.md#v7双人字幕修复与完成的五秒)。这解决字幕名单故障，不增加新的袖物理认证范围。

制作与来源仍见 [伊科尔婚礼制作记录](IKHOR_BOLD_WEDDING_PRODUCTION.md)；一般物理原则见 [自然动态手册](PHYSICS_MOTION_PLAYBOOK.md)。
