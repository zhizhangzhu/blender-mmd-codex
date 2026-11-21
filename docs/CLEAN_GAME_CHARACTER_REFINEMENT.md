# 阿克西妮娅×伊科尔：干净明亮人物材质修订

2026-11-14，`duet-clean-game-v1`。猪猪提供两份本地参考，要求人物更干净、明亮、更接近游戏NPR观感，随后明确要求去掉身后的蓝／黄光弧。本轮从已经完成修袖和双人字幕的婚礼v7另存，保留两人的角色配色、动作、袖修复、相机、指定礼堂与原唱FLAC；全曲不在本轮范围。

**本轮五秒已完整输出：最终工程为production-v2，字幕版与无字幕版均在captions-5s。** 新beauty／actor完整300帧来自固定v2和全新缓存；两版各300帧全解码、音轨、色彩、接缝与双人字幕覆盖率通过。主任务实际查看两版各12个时点、4处字幕边界共32帧连续图及7张原生腕部关键帧，抽样未见阻断退化。美术仍有参考差距，未获猪猪认可，不宣称游戏质量或作者Shader还原；全曲未交付。旧婚礼v7保留历史输入，现行状态以[current_state.json](../catalog/current_state.json)为准。

## 固定输入与版本

本轮输出根为`D:/codex/output/MMD-Clean-Game-Characters-v1`。同段仍是原帧4140–4439，1920×1080、60fps、300帧／5秒；动作分配为阿克西妮娅→Full HimeTanaka、伊科尔→Full HinaSuzuki。

| 版本 | 文件与SHA256 | 实际职责 |
| --- | --- | --- |
| 完成的输入基线 | `D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/production-v7/Franken_Aksiniya_Ikhor_Bold_Wedding.blend`；`f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692` | 保留已完成袖修复、双人正确字幕名单；旧两版视频在同根`captions-5s-v3`，见[基线制作记录](IKHOR_BOLD_WEDDING_PRODUCTION.md) |
| 新材质v1 | `production-v1/Franken_Duet_Clean_Game.blend`；`8425c1827fd296fe19e17225e5e1e748de249bf11cae25ff888c6b010242f993` | 只适配两人材质；独立321项静态检查通过 |
| 最终去光弧v2 | `production-v2/Franken_Duet_Clean_Game.blend`；`0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4` | 在v1上只隐藏蓝、金两条弧的render与viewport可见性；独立26项增量检查通过，完整新beauty／actor300与两版视频均已完成 |

输出根内的`production-v1/preparation.json`记录源工程、两个模块与两个preset的实际SHA；两级`master-verification.json`各自绑定对应工程，不把材质版321项与去弧26项相加冒充同一次全量检查。

| 已完成视频 | 相对输出根路径与SHA256 |
| --- | --- |
| 字幕版 | `captions-5s/Franken_Duet_5s_CleanGame_Wedding_REVIEW.mp4`；`f0e2a8053244cbc09dc16e55a4dadcfe5f94c09fcfede25e9acc66de2061e107` |
| 无字幕版 | `captions-5s/Franken_Duet_5s_CleanGame_NoCaptions.mp4`；`e2bab89e41e3b1e4c53574888c28a3729632be27097b996c04a26e096bfe93d0` |

## 实际读到的参考与适配边界

第一份本地MP4为伊科尔，SHA256为`ef140e1a20d1678442d2b1dbfac80b8592932dfb22bc2b1070eaecd89559a608`；第二份为用户称“沃雅妮莎”的女性角色，SHA256为`c5688ae46358740bf4d909c1ece8d7b8397bd5d15d5fad855c2c8210f5056ef7`。第一份可追溯至神秘会员日的[《哪来这么帅的小王子》](https://www.bilibili.com/video/BV1UauH6AEw8/)；第二份只确认画面水印，正式角色名与原作者身份未独立核定。

两份都是720×1280竖屏，分别实际查看四张清晰渲染抽帧：男参考约4.177／7.485／10.826／14.168秒，女参考约3.609／6.517／9.425／12.299秒。分享卡、二维码和B站尾片没有用于材质判断；未完整连续观看、未取得字幕或作者工程。时间沿用抽帧元数据的近似值，不称精确PTS。来源、观察及当时尚未实施的建议分别保存在[男参考账本](research/IKHOR_PRINCE_REFERENCE_2026_11_14.json)和[女参考账本](research/FEMALE_CLEAN_NPR_REFERENCE_2026_11_14.json)，本篇记录其后的本机实施，不回写成作者原参数。

参考的近白背景、高键构图、柔亮后期与RGB错位彩边共同参与观感。鼻线、下颌／颈部暖或灰紫阴影、发侧褐影和深袖内衬仍可见，不能解释为所有部位无影或全材质均匀自发光。参考的具体Shader、MME效果、法线、曝光和粗糙度未知。这里借鉴明暗职责与材质分区，保留阿克西妮娅银白发／金瞳／深蓝衣及伊科尔奶金／金饰／青饰；没有复制参考青发、白背景或RGB色差。

参考视频与抽帧只在私人输出目录作研究，不复制进仓库，也不放入Atlas。模型、音乐、动作、相机和继承着色组件的署名及社区镜像许可未知状态继续见[本轮署名](CREDITS_AKSINIYA_IKHOR.md)。

## 四个独立材质模块

两人均提供`palette`、`response_ramp`、`highlight_metal`、`rim`四个独立开关。保留原MMDShaderDev Color／Alpha、贴图与sphere语义，改变的是下游已标定的美术响应；数值为现有线性着色域的乘数或参数，不是将参考显示RGB直接当作BaseColor。

| 模块 | 阿克西妮娅 | 伊科尔 |
| --- | --- | --- |
| `palette` | 分hair／fur／cloth／trim重设明暗职责，抬深蓝衣的可读中间层；只调整毛领描边RGB对比，不改壳宽／权重 | 脸与手朝浅粉而非红棕调整，发侧暗带改浅奶金；外白布用独立逐像素许可，保留深内衬／金青饰 |
| `response_ramp` | 只在真实含SDF的`颜`鼻区修复孤立暗块来源；`颜+`没有原SDF，不新增伪SDF | 独立调整脸／肌肤／头发／许可白布的色带位置；保持原形体、受光标定与一次短距AO，不新增脸部SDF |
| `highlight_metal` | 克制已有发束亮带，沿既有Blue通道调制许可；保留原金属闭包并有界调整其粗糙度，降低发内线RGB对比 | 发带指数44→28、强度0.08→0.05；金分区roughness 0.27→0.39、physical mix 0.62→0.44，Metallic维持0.80，减轻金面局部白亮 |
| `rim` | 将原Reference及Bold Wedding亮边同时收窄／减弱，并加法线朝向许可；不让整圈青边持续抢脸 | rim指数5.5→7；hair强度0.80→0.38，许可白布0.60→0.28，skin／face 0.015→0.008；保留原青宝石与装饰分支 |

阿克西妮娅的开关设为0时重新接回原socket链接／默认值；伊科尔开关设为0时选择保留的原节点分支。后者仍有浮点混合计算，不能未经像素检查就称逐位相等。已有伊科尔iteration 1的baseline／all-off由FFmpeg读取后，再用Pillow＋NumPy独立核对：最大差1个8bit码值、MAE约0.0044618码值，没有超出1码值像素；它是首轮旁路证据，不能推广成iteration 2或阿克西妮娅的逐位等价认证。

### 鼻部暗块：修SDF局部岛，保留其后的遮挡

实际检查的阿克西妮娅`FaceLightmap` red通道鼻部局部岛，经原动态SDF阈值、`0.38 + 0.62×SDF`形体响应、实际主灯综合受光链进入材质，造成孤立棕色泪滴。FaceDiffuse本身只有较浅鼻痕。新模块没有用最终脸亮度下限盖住问题：复用同一张SDF图，在原镜像映射后的UV左右各偏移0.070取样并平均，经原动态阈值重建低频场，仅在原UV中心(0.50, 0.445)、半径(0.055, 0.075)的小椭圆内按0.62强度柔化混合。

鼻区外脸侧SDF、原0.38形体下限、主灯综合受光、短距AO和`Face ink | Mouth crease`嘴缝保持；不改UV、形态键或法线，不把其他角色控制图接入。脸颊的新几何塑形／专属控制图并未制作，不能把缩小孤立鼻块写成完整面部SDF重建。固定4290同帧开关图及三轴代表脸序列已由主任务实际查看；这是同帧与诊断抽样，正式60fps编舞中的鼻影连续性仍须从新beauty另审。

### 男角色iteration 2：给白布留高光余量

首轮七张4290 GPU对照中，浅粉手／金面变化有用，但正面白袖本已落在旧色带亮端，只抬暗端不会让该处更干净，且首轮亮端略降会让白袖稍暗。iteration 2因此保留材质分区，进一步抬奶金发侧带，并只对许可的白布中间层增加有高光余量控制的乘法增益；没有全图增曝、固定白色下限、gamma重映射或新增Emission闭包。

白布许可读取原base texture的HSV：低彩度S≤0.12完整许可、S≥0.28归零，明度V≤0.40归零、V≥0.66完整许可，再排除原gold／cyan美术mask。范围只覆盖源`衣`、`衣2`、`衣领`、`带子`、`裙`中的许可像素，不按衣服材质名把整片内衬抬白。新增最大RGB乘数为(1.38, 1.30, 1.22)，随原已着色NPR亮度0.45–1.0逐渐退去，亮部增益更少；位于原AO之前，由`palette`开关控制。原physical BaseColor及12% cloth闭包未改，金甲、青饰、深内衬保留原分支。

它是原贴图当前线性域内的原创颜色许可，不称恢复游戏Lightmap；高明度低彩细节也可能进入许可，必须看实际UV与画面。缺失的作者编辑脸图`y1.png`仍未恢复，仍显式使用包内同角色FaceDiffuse回退，不能把下游校色称恢复原作者纹理。

## 两条身后光弧的可逆移除

按猪猪追加要求，v2只将`Bold wedding | blue vow arc`与`Bold wedding | gold vow arc`各自的`hide_render`、`hide_viewport`由False改True，合计四个可编辑可见性布尔值。原CURVE、材质及动画数据保留；礼堂几何、其他光点／光束、实际灯组、曝光、World、相机与人物材质相对v1不再变更。

`production-v2/arc-removal.json`记录四项变化；独立26项增量核查另外比较光照probe／cache-file的RNA设置，未重烘旧间接光缓存，也不把未暴露的引擎缓存内部负载称重新认证。隐藏viewport的曲线会呈现未求值的fallback dimensions，初次核查曾因此报错；保留原失败记录，再在独立内存中只恢复四个可见性标志，重求值确认包括dimensions在内的全部物体字段与v1一致。完整曲线几何与保存的loc／rot／scale始终严格比较，没有把derived bounds异常放宽成任意变换例外。

## 已完成证据与交付边界

| 证据 | 实际范围与限制 |
| --- | --- |
| `aksiniya-controls-v1/control-records.json` | 同4290的baseline／all-on／all-off与四个独立off，共7图；1280×720、48 samples，诊断关闭DOF与MB，源工程不保存；主任务已实际查看对照 |
| `ikhor-controls-v1/control-records.json` | iteration 1同条件7图；其旁路独立像素核对在`ikhor-analysis-v1/pillow-bypass-verification.json`；不能据此认证最终iteration 2 |
| `ikhor-controls-v2/control-records.json` | iteration 2同4290的baseline／all-on／all-off／off-palette共4图，已生成并由主任务实际查看；不是四模块全部消融的第二轮 |
| `production-v1/master-verification.json` | 独立重开321项静态通过，保留全部mesh／UV／权重／shape／rig、11个完整Actions及插值柄、灯／相机／场景／声音／合成与双人Crypto；38块选中材质的受限变化并按SHA绑定脚本／preset在内存确定性重放；不是像素等价或美术认证 |
| `production-v2/master-verification.json` | 独立26项去弧增量通过，绑定v1与v2及原321项报告；除四个可见性值外静态摘要一致，没有重新执行整轮shader重放或303帧几何扫描 |
| `diagnostic-review/diagnostics-verification.json` | `verify_character_diagnostics.py`将转头／移主灯／绕拍三片各24帧全解码并核轴向，均24个独立帧、24fps，技术通过；原片1280×720，中性试验、临时源姿态4200。主任务实际抽看全部三组的0／4／9／14／19／23索引双人脸条图。不是人工逐帧看完72帧，也不替代正式60fps编舞或认证全部时域稳定 |
| `native-5s/sample-report.json`与`native-5s/chunks.json` | 固定v2在全新`D:/codex/temp/MMD-Clean-Game-Characters-v1/final-cache`完整重渲4140–4439的300帧beauty／actor；不复用旧婚礼beauty，不混旧actor缓存 |
| `caption-coverage-final.json` | 实际新300帧actor PNG16上，两人头／身共1200个内部ROI全部通过；投影位置仅因完整几何／动作／相机严格相同而继承固定v7正例，原Alpha、DOF、MB保留；检查遗漏人物，不认证所有透明轮廓像素 |
| `captions-5s`内两套video／audio／seam与color报告 | 两版实际各解码300帧、1920×1080／60fps／5秒；音轨非空有限，字幕／无字幕两版分片接缝均通过；709矩阵／709基色／sRGB实际曲线／limited电平，属于电脑审片输出，不称BT.1886调色母版 |
| `audio-source-comparison.json` | 两版最终AAC独立解码PCM，对固定原唱FLAC的68.983333秒起段、gain=0.87独立重采样比对；两版correlation均0.995694、relative RMS error约0.092913，通过。确认使用指定原唱及片段，不等同音乐卡点或主观混音完成 |
| `manual-review.json` | 主任务实际查看两版各12个时点联系表、四处字幕边界各8帧共32帧连续图；另看原生4186／4190／4218／4220／4225／4317／4318七张腕部关键全图，4140／4290此前已看。不是人工逐帧审完300帧 |

因为几何、袖修形和全部动画数据与v7严格一致，本次继承原v6→v7的4139–4441袖／动作证据及原抽样限制；没有重算物理、没有新的303帧碰撞认证。正式五秒已从固定v2全新渲染并完成后期／全解码／字幕验证，后台组同时在两人后，前景组仍保留整组在前的设计，4162／4271源边界保持。

实际成片与原生抽样中，两条新增蓝／金细发光弧已消失，礼堂顶部原有弯曲垂帘与斜体积束仍保留。阿克西妮娅孤立鼻块弱化，眼与发束线仍可读；伊科尔白布、金面与青饰有区分，脖子、衣褶和发侧阴影未被整体提亮抹除。重点腕部的掌根处于原袖口开口内，未见原外袖不透明侧壁皮肤破口或大片反折；原非零几何交线仍保留，不认证清零。独立抽审另实际查看4140／4290全图与两份参考联系表，结论仅限这两个时点，也未发现阻断退化。

参考差距仍在：中央灰亮空气与蓝金斜束较强，阿克西妮娅大面积深蓝衣的层次相对压低，伊科尔白衣更抢眼；局部青亮边／尾饰仍醒目，银发冠顶白峰较宽、发侧内线较重，男发侧偏赭金、部分金边仍有较白镜面。参考近白高键背景、柔淡金面及细线的整体观感未匹配，不把模仿解释成技术还原。以上是有明确抽样的技术验收与画面观察，用户美术评价独立保留；全曲、游戏级质量与原作者Shader复原均未据此完成。

## 可复用入口及输入契约

- [clean_aksiniya_materials.py](../scripts/clean_aksiniya_materials.py)与[阿克西妮娅参数](../presets/quality/aksiniya-clean-game-v1.json)：只接受固定caption修复v7，拒绝重复叠加；只做本角色限定材质适配。
- [clean_ikhor_materials.py](../scripts/clean_ikhor_materials.py)与[伊科尔参数](../presets/quality/ikhor-clean-game-v1.json)：同样绑定v7 SHA，当前`parameter_iteration=2`；仅可在builder另存前的同一未保存副本中实施。
- [prepare_clean_game_duet.py](../scripts/prepare_clean_game_duet.py)：固定v7输入，分别调用两人模块，新目录另存材质v1与准备清单；不能对任意最新工程运行。
- [remove_wedding_arcs.py](../scripts/remove_wedding_arcs.py)：只接受固定Clean v1 SHA，新目录另存v2；不是任意对象批量删除器。
- [verify_clean_game_duet.py](../scripts/verify_clean_game_duet.py)：静态独立核查与明确的去弧增量模式；执行过的报告保留版本与原SHA，不改写旧报告或将静态核查冒充渲染。
- [package_clean_game_duet.py](../scripts/package_clean_game_duet.py)：只登记本次固定v2与已实际完成的两版五秒，验证新缓存、SHA绑定报告和人工范围，复制本篇／署名／原创来源账本及许可，再更新交付索引／catalog／配方；`--dry-run`只读。不是任意工程通用打包器，不覆盖现行用户评价。

以上阶段使用独立后台进程，不改用户偏好，不把后台工程称用户GUI当前场景，不覆盖旧工程／缓存。复现时必须用新目录，不能对已固定的production-v1／v2重复运行输出。
