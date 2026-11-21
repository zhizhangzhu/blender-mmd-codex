# 双人人物静帧：法线、脸影与材质分层

2026-11-18。本轮把已经学习的 Goo／Blender 基础用于真实双人人物。按猪猪最新要求，由 `gpt-6.1-sol` 的 `xhigh` 总监亲自复核技术方案、阅读本轮官方资料和验收图像；`low` 执行代理仅运行已明确的命令。当前仅静帧，用户美术评价仍待定，尚未达到原神／鸣潮参考的感知质量。

## 输入、设计意图与范围

唯一输入为 `D:/codex/output/MMD-MME-Reference-Light-v1/production-v6/Franken_MME_Balanced_Light_Still.blend`，SHA256 `65766b3befc9031f5c27efb25f91b1516cd2a0cd195b4ea98125bab93c07bf7a`。继续使用 Goo 5.2.1 非官方社区构建 `0051aee03764`，独立 CONFIG／SCRIPTS，先注册便携 MMD 相机 RNA，再打开工程。

保留指定礼堂、角色配色、原生相对站位、既有相机、动作、模型形状与字幕约定；眼透仍搁置，不改新物理或 K 帧。目的为：脸眼作为焦点，暖脸影具有选择性，发束亮暗与冷暖明确，强轮廓光有主次，白衣暗面及金青饰纹仍可读。发色不照参考统一改蓝，不从参考图片推断作者参数。

交付目录 `D:/codex/output/Goo-Character-Lookdev-2026-11-18/`。`trial-v1`／`trial-v2`／`trial-v3` 是试验，不能仅凭最高版号称为已验收。最终工程和静帧证据由 `final-v*/finalization.json` 及独立 `reopen-verification.json` 追踪；未完成重开和图审前，不晋升为通过。

## 亲自补读的官方资料与所得

本轮使用已有私人缓存，没有重复抓取第三方全文。接管后的 `xhigh` 总监实际阅读四份针对性缓存，并在诊断阶段补读 Glare 正文，核对五份缓存的磁盘字节哈希。哈希和阅读范围见[本轮账本](research/GOO_CHARACTER_LOOKDEV_2026_11_18.json)。仅将原创总结写入仓库。

| 官方资料 | 本轮实际学习与应用 | 不能由此声称什么 |
| --- | --- | --- |
| [Blender 5.2 Drivers Panel](https://docs.blender.org/manual/en/5.2/animation/drivers/drivers_panel.html) | 驱动依赖应通过变量声明；Transform Channel 能纳入父级／约束，Single Property 的 location 通常是原属性。实际主光世界位置用三路 `TRANSFORMS/WORLD_SPACE/LOC_X,Y,Z` 读入节点，不用硬编码一份静态世界向量。简单表达式 `position` 保持可跟踪依赖 | 不能只因 driver 存在便称更新有效；还要在独立重开后比对实际 world 位置与节点值。本轮既有历史无效驱动单独记录，不能假称全工程零无效驱动 |
| [Blender 5.2 Normal Edit](https://docs.blender.org/manual/en/5.2/modeling/modifiers/normals/normal_edit.html) | 它生成／混合 custom normals，不移动顶点。Radial 以参考中心构造法线，Directional 含目标汇聚与平行两种语义；Mix Factor、Vertex Group、Max Angle 各有职责。本轮仅侧脸许可组、混合 0.23、最大32度，目标跟随各自头骨 | 不能把全脸法线全改成球面或把接口可用当成人物有效。本轮需实际 NormalEdit 关闭对照，且检查求值坐标无差；修改器顺序依赖当前模型，不作为通用角色预设 |
| [Blender 5.2 Tangent](https://docs.blender.org/manual/en/5.2/render/shader_nodes/input/tangent.html) | Tangent 是各向异性的方向输入，可从径向或特定 UV 导出；有方向不等于有正确发束高光 | 没有仅因读完就换掉当前绘制发束高光，没有取得游戏发丝方向贴图或声称当前 EEVEE 各向异性路线已实装 |
| [Blender 5.2 Principled BSDF](https://docs.blender.org/manual/en/5.2/render/shader_nodes/shader/principled.html) | 重点复读 Layers、Roughness、Metallic、Normal、Specular／Tangent、Coat、Sheen、Emission。金属反射与漫反射布料职责不同，降低粗糙度是改变反射分布，不能补足缺少的金属许可图。文中多项各向异性标为 Cycles Only | 不能把修改某个 roughness 值称为整套 PBR 材质完成；本轮仍保 MMD Color／Alpha、纹理和 sphere 的既有语义，局部美术近似如实标记 |
| [Blender 5.2 Glare](https://docs.blender.org/manual/en/5.2/compositing/types/filter/glare.html) | Image 是原图加效果，Glare 是效果本身；先追踪实际使用的输出，再做关闭控制。最终控制将活动节点的 Image 分支接回输入、Glare 分支接 RGBA 零，保留既有停用状态 | 不能将所有节点一律 mute 后称去辉光：本轮实际发现它会把源图透传到效果专用叠加分支，形成错误增亮。该错误图已拒收并保留 |

此前本机构建的 Shader Info Normal／Position 覆盖入口无响应，与真实网格 Normal Edit 生效是两件事；不因找到后者就改写前者的实验结论。显式 `Geometry.Normal · normalize(actual_key_position − Position)` 用于这次新增脸部形体调制，仍不是 Goo 原生 Cast／Self Shadows 或 SDF。

## 已实装的有界模块

`scripts/refine_goo_character_lookdev.py` 绑定上面的输入 SHA，在新目录制作试验副本，不重复运行旧生产安装链。

- 法线：两人各自脸材质顶点建立许可组，鼻口中心及下颌尖端逐步排除，头骨目标的 Radial Normal Edit 保留原模型位置。它在当前 Solidify 后，必须以坐标差及实际消融确认；不代表其他修改器顺序同效。
- 脸影：保留阿克西妮娅已有 FaceLightmap／SDF；伊科尔没有已验证 SDF，不交换模板。新增显式法线与真实主光位置的暖色乘法，单独可关闭。几何刘海 UV 遮罩重新按4290帧、当前灯位采样，512²、三个窄域光源采样；遮罩是静态图，不是动态阴影通过。
- 主光：双人的指定 key／head key 按各自头部空间重定位，功率不增加；只用该方向解释这轮形体与刘海投影，不用整图曝光掩盖人物分区。
- 头发：调整原有 compact ramp，把亮暗色块收束；窄化既有亮带，保留角色原发色、绘制细节及不透明刘海。
- 衣发轮廓：主要轮廓保留，次侧增益降为原来的0.64；减少宽域 Bloom，不以总减亮替代轮廓设计。
- 白衣：冷色暗部、较克制的亮区，保留原有金青排除；金饰仍使用已存在的局部许可，不将颜色阈值误称原始金属度贴图。

## 实际图审与最后修正依据

接管后的 `xhigh` 总监逐张查看了 `trial-v3` 的 `before/after-ikhor-4290.png`、`before/after-aksiniya-4290.png` 和 `before/after-duet-4290.png`，共六张，并亲自审阅 finalize 脚本及其 render／hero_camera／snapshot 依赖。

伊科尔的头发亮暗更集中，刘海与侧脸较基线增加暖影，蓝眼图案及白衣金青装饰仍可读。阿克西妮娅的冷白发及蓝紫暗部更清楚，脸部从近乎平涂变得有明确暖影。双人原机位的变化仍主要在人脸与头发，建筑构图、动作和人物关系没有被替换。

v3 仍有需要克制之处：阿克西妮娅鼻侧至嘴边的新增软影偏浓，把几何鼻口强调成较写实的体块，弱化了参考的平整概括。最后只把她新增 faceform 的乘法力度从0.78减为0.52，伊科尔保留0.78；不继续加灯、扩大法线影响或增强 Glow。这个数值是本轮可复审的美术选择，不是官方推荐参数。

白衣仍有亮面较宽、金属反射形状未够精确的问题；脸部专用设计边界、线条材质分级和两人眼睛高光也未因此自动达到游戏标准。它们保留为差距，不靠提高采样量或技术检查数目宣称解决。

## 最终制作与验收契约

`scripts/finalize_goo_character_lookdev.py` 的三个主模式每次使用独立后台进程；另外两项修正／复测模式不修改保存的工程。现行状态由根任务统一整合，不由该脚本直接改 catalog。

1. `preflight`：只读核固定v6与v3 SHA；完整 Actions 曲线／柄摘要、Action Slot绑定、NLA与骨骼约束、基础网格、两人UV／原权重／Shape、原纹理／ColorAlpha链，以及五时点骨骼／相机／Morph和求值顶点。既有无效driver源／候选同集，新加的六路主光位置driver另核。
2. `prepare`：减弱阿克新增faceform，恢复源相机完整 DOF 参数、保留相机标记、静音全部继承 File Output，保存限定4290帧的1080p64samples工程。实渲同设置的源／候选原机位、每人0／±0.19m三观察角度、去Glow控制，以及逐人NormalEdit关闭控制。侧向相机相对0.78m前距只偏约14度；这不是正侧脸、仰俯头或转头测试。三视角只改相机，不改头姿态、动作或表情。
3. `reopen`：新进程重新注册插件再打开保存工程，重新核保护摘要、相机DOF／markers、眼透为0、 packed4290发影、法线目标头骨绑定、六路world driver与输出禁用。复渲原相机1080p，记录与保存前实际像素差；不以“可打开”代替渲染可复现。本轮严格像素阈值未通过，后续独立复测与有界结论见下。

最终图审必须看每人三个角度、无Glow、NormalEdit消融及原机位成图。消融有差只说明该模块实际影响输出，不自动说明它更好看；必须确认没有鼻口脏斑、面部破碎、虹膜丢失、大片发白或双侧等强白边。

本轮无视频、音轨重混、物理重算、全曲运镜校正、眼透恢复或新的伊科尔发骨动态。五个抽样姿态及相同Action不能认证动作节奏、头发动态或全曲稳定性。

## 当前证据状态

最终候选为 `D:/codex/output/Goo-Character-Lookdev-2026-11-18/final-v1/Franken_Character_Lookdev_Still.blend`，SHA256 `66a030e52f93f373f009cd4308ad6b6bc6504387346ce4ca4adc43851357928a`。保存范围仅4290，原机位1920×1080、64 samples、16-bit PNG，原DOF开启、f/3.2，4290焦距为61.73464966mm。六张人物近景及两个Normal Edit关闭控制为850×900、48 samples、无DOF。

预检10项全部通过；两人五个抽样姿态的求值位置最大差均为0。保存后两次独立重开均保持Action、几何、相机／骨骼／Morph抽样、UV／原权重／Shape、绑定／约束、保护纹理／Alpha和色彩摘要。眼透额外因子六项均为0，六路新增灯位driver与真实世界坐标一致，两张4290发影512²均已打包。继承File Output保持停用。

`xhigh` 总监逐张审看11张有效静帧：同设置的原机位源／候选、每人三个小角度观察、每人Normal Edit关闭控制，以及修正后的去辉光图；还审看两张独立重开原机位和差异放大16倍图。因原16-bit PNG超工具显示体积，图审使用同分辨率、quality95／subsampling0的临时JPEG；所有像素数值来自原PNG，未以JPEG进行像素验证。

判断：阿克0.52较v3减轻鼻口软影，脸眼仍是焦点；伊科尔保留0.78暖影、蓝眼图案与金青分区。发束暗面较集中、主要强轮廓保留，关闭Glow后脸、发束和衣褶仍可读。局部法线效果较轻，不把它描述成整个改善的唯一来源。白衣亮区仍宽、金属反射形状和脸部图形概括仍有差距；接受为新的静帧候选，用户美术仍待评价，参考质量未达到。

### 本轮发现并保留的诊断问题

第一轮重开仅因相机标记的内存tuple与JSON读回list比较而失败，记录已保留为 `reopen-verification-failed-01.json`。检查器改成JSON原生列表后，marker、DOF及其他保存保护实际全部通过；没有改工程来绕过断言。

最初的 `final-duet-no-glow-4290.png` 因全体Glare mute导致效果分支重复加入源图，明显过亮，已在finalization报告列为拒收控制。`repair-controls` 只在独立进程改诊断输出连接，补渲有效的 `final-duet-glare-off-4290.png`；原错误图保留，不作为有效证据，工程SHA保持不变。

修正检查器后的首次重开仍未达到原设 `mean<1e-5/max<0.003` 的严格像素要求。没有直接改阈值重跑到过；另用 `repeat-reopen` 开独立进程再渲一次，比较三对原PNG：

| 比较 | 最大RGB差 | 平均RGB差 | RGB差99.9百分位 | 任一通道差>0.003的像素数 |
| --- | ---: | ---: | ---: | ---: |
| 保存前／首次重开 | 0.003177911 | 0.000032059 | 0.000991583 | 1 |
| 保存前／第二次重开 | 0.004387021 | 0.000034853 | 0.001462579 | 3 |
| 两次独立重开 | 0.004387021 | 0.000024513 | 0.000980496 | 2 |

数值空间为Blender解码PNG的RGB，并非原始HDR AOV；每张共2073600像素，三对均无RGB差>0.01的像素。差异图只见极低幅度变化，正常图审未见结构变化；两次重开之间也有这种差，支持当前渲染存在轻微非确定性的判断，**尚未定位具体算子原因**。严格失败报告 `reopen-verification.json` 保持 `passed:false`，独立复测留在 `reopen-repeat-verification.json`。总监据保护摘要、重复证据与图审接受为“静帧有界验证通过，存在轻微像素差”，不声称位级一致或扩大到动态／全曲。
