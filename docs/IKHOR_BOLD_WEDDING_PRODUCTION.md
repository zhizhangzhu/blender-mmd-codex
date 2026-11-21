# 阿克西妮娅×伊科尔：蓝金婚礼五秒制作记录

2026-11-14，`franken-ikhor-bold-wedding-v1`。本轮把Hina分轨的空替换为伊科尔，重新准备伊科尔原生动作与局部物理，并在猪猪选定的赫斯珀利德斯礼堂上加强蓝金婚礼照明。阿克西妮娅继续使用Hime分轨，主题仍为雪、婚礼、爱；不是更换舞台或完整原神Shader的实现。

**修袖与双人字幕基线已完成：最终工程为production-v7，字幕版与无字幕版均在captions-5s-v3。** v6已用新缓存完整重渲300帧beauty；v7只修正字幕Cryptomatte中遗漏伊科尔的名单，独立38项差分确认beauty依赖不变，故沿用该批v6 beauty，重新渲染完整300帧双人actor覆盖率。两版各300帧全解码、音轨、色彩及分片接缝检查通过，实际图审范围见同根`manual-review.json`。全曲未交付，美术未获猪猪认可。

猪猪指出4290帧袖子穿模后的production-v4仍明确退回，其旧`native-5s`帧未复用。旧`captions-5s-v2`虽通过格式／解码检查，后台字幕仍会盖住伊科尔，也已退回。猪猪随后要求根据两份本地参考做更干净明亮的人物，并移除身后蓝／黄细光弧；后继[Clean production-v2](CLEAN_GAME_CHARACTER_REFINEMENT.md)已全新渲染beauty／actor300并完成字幕／无字幕两版，当前最新交付在`D:/codex/output/MMD-Clean-Game-Characters-v1/captions-5s`。本篇保留婚礼v7的历史输入与验收范围，不代表最新美术获认可。

## 已完成基线、退回版本与约定范围

交付根目录：`D:\codex\output\MMD-Aksiniya-Ikhor-Wedding-v1`。

| 内容 | 本轮约定 |
| --- | --- |
| 完成基线工程 | `production-v7\Franken_Aksiniya_Ikhor_Bold_Wedding.blend`；修袖与字幕名单均已保存 |
| v7工程SHA256 | `f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692` |
| 完整beauty来源 | `production-v6\Franken_Aksiniya_Ikhor_Bold_Wedding.blend`；SHA256 `201e2632befaf0a16f17b931963626a91bbc6b8f7e58d148d5047298a530de01`；v7严格差分支持复用，未使用被拒绝v4帧 |
| 被拒绝候选 | `production-v4\Franken_Aksiniya_Ikhor_Bold_Wedding.blend`；因4290帧袖子穿模退回，仅作修复基线，不是最终主工程 |
| v4工程SHA256 | `283acdf2f1063fae32b0ed49caed07952706ff4d7b9ed1675490fa7ad021a0c1`，仅作失败版本追溯 |
| 人物／动作 | 阿克西妮娅→官方Full HimeTanaka；伊科尔→官方Full HinaSuzuki |
| 输出范围 | 原帧4140–4439，300帧，1920×1080，60fps，横屏16:9，五秒 |
| BGM | `D:\codex\output\Franken-Duet-Full-Audio-v1\HIMEHINA - フランケンシュタインの怪物.flac`；198.3158125秒，96kHz／24bit／双声道，不换回伴奏或MP3 |
| 相机 | 保留原とっとこ相机及DOF、原生相对站位；未另做全曲镜头校正 |
| 旧原生输出 | `native-5s`已停止，beauty／actor旧缓存为`D:\codex\temp\MMD-Ikhor-v1\final-cache`；已有帧不复用 |
| 完整原生输出 | `native-5s-v2`已完成300帧；beauty来自`D:\codex\temp\MMD-Ikhor-v1\final-cache-v2\beauty`；该缓存旧actor遗漏伊科尔，不作为最终遮罩 |
| 正确双人覆盖率 | `D:\codex\output\MMD-Ikhor-Caption-Matte-v1\full-v1\actor`；由固定v7重新渲染300帧，48 samples，保留原Alpha、DOF与运动模糊 |
| 已完成字幕版 | `captions-5s-v3\Franken_Duet_5s_Ikhor_Wedding_REVIEW.mp4`；SHA256 `feeaefdef7477ed57c947122844207159e7aa4a84e75f5d24fd3d8580aff549a` |
| 已完成无字版 | `captions-5s-v3\Franken_Duet_5s_Ikhor_NoCaptions.mp4`；SHA256 `d49279776e39149ab6e5a60632b3f27e7a4299372af2da5b8c9ac4421ecbe089` |

本工程保留全曲身体／Morph动作，不等于全曲次级物理或全曲成片已验证。来源及使用限制见[本轮署名](CREDITS_AKSINIYA_IKHOR.md)。

## 输入与脚本契约

制作先从[外部技术移植版](REFERENCE_TECHNIQUE_TRANSFER.md)建立Bold Wedding灯光副本，再追加独立准备的伊科尔。`prepare_bold_wedding.py`接受该轮指定输入指纹，建立双弧、光点、灯组和选择性Glow；不能在最新工程上再次叠加。

`prepare_ikhor_motion.py`在独立工程中导入PMX与完整Hina原生VMD，审计、顺序模拟、视觉烘焙、重定时并独立重开。生产使用的是`D:\codex\output\MMD-Ikhor-Model-v1\motion-v1\physics-v3\Ikhor_Hina_Portable.blend`及其`append-verification.json`，不是上层目录的早期零参与刚体候选。

`integrate_ikhor_wedding.py`只接受已核Bold Wedding v2源工程SHA及验证清单匹配的伊科尔集合。它移除空及对应辅助对象，追加`Ikhor | character`，新建伊科尔灯光接收集合与材质映射；不在双人工程重新Build、不复用空的物理、不再次重定时。`refine_ikhor_skin.py`仅接受其指定的整合版指纹，在新目录保存两块肤色阴影端点校准。本轮production-v4由此得到，原工程和PMX文件保留。

所有准备、诊断副本先静音继承File Output，不覆盖旧EXR／缓存，不改用户偏好。正式300帧已从固定v6与新缓存完整重渲，beauty与Caption cache beauty保持同源；v7的字幕名单专用修复另存新工程与actor缓存。不混入被拒绝v4的旧帧，旧打包器不作为本轮通用发布命令。

## 伊科尔原生动作与局部物理

PMX使用比例0.08，SHA256为`ebba744cee847c16cfe5be037e7464d4f701c8edb2f5033e7de5730bd6654a52`。按实际骨名与Morph导入完整Full Hina，不全局关闭原有IK。源骨`A`的追加变换指向自身，形成生成约束循环；只在独立候选中取消这一处无效自继承，未修改原PMX或普遍删除追加变换。

实际参与的原生刚体为514个，其中33个跟随骨骼、481个动态；源PMX关节924个。Build后的27013个约束包含额外非碰撞约束，不能称作新增27013个源关节。采用30fps，顺序模拟Blender源帧2279–2550；前120帧预滚，导出2399–2550的骨骼视觉动作，再移除实时刚体世界及驱动，保留可独立追加的角色集合。

时间映射为：

```text
output60 = 1 + 2 × (sourceVMD30 - 329)
         = 1 + 2 × (importedBlender30 - 330)
```

即输出第1帧对应源VMD第329帧。关键点及左右插值柄同时变换，完整源动作保留，包括映射后的负帧。实际新物理只认证输出4139–4441（含保护帧）；4140–4439对应VMD2398.5–2548。独立重开／追加核对了九个时点的姿态与Morph，并在300帧检查动态骨坐标有限性；这不是完整逐帧穿模或自然度验收，区间外物理外推不视为全曲模拟。

本轮没有新增胸部solver。不能把模型有动态刚体、骨骼数值稳定或局部烘焙通过升级成全部身体次级运动通过。

## v6局部袖物理与受限修形

v4的袖口问题没有通过改手部动作或扩大全部材质遮罩处理。局部重算实际包含14个刚体：8个动态袖体、2个前臂锚与4个随皮肤动作的接触凸壳，34个约束；仍按30fps顺序预滚、连续模拟和视觉烘焙，再映射到60fps保护帧4139–4441。只有`Bone_Sleeve01/02_L/R`及各自`錘`这8骨可改；01／02为并列骨，不当成父子链。右袖在局部物理后加明确软限幅，所有手骨、非袖身体动作与原Morph轨保持不变。

左腕最大弯曲处另加一个`Sleeve repair | L wrist flex clearance`。允许范围从固定v4的左袖01／02原权重独立重建：总权重`>0.001`与`>0`均为同一573个原顶点，无微权重集合差；实际398点有非零修形，最大rest位移约12.028mm。Basis、原有全部shape、UV、权重、材质和原PMX不变。新shape在4210／4218／4225／4233取0／1／1／0，使用已固定的BEZIER／FREE插值柄与常量外推，逐帧检查进出单调、窗外为0。

`apply_ikhor_sleeve_repair.py`只接受固定v4指纹，追加完整修袖Action及上述受限shape，另存v6；不能对最新工程重复追加。独立`verify_ikhor_sleeve_repair.py`重新打开源与候选，绑定两端SHA和修复数据SHA，比较所有保留曲线、插值柄、原形状、材质、灯、相机及场景。303帧非袖骨矩阵与原Morph严格零差；诊断中仅临时关闭双方原描边Solidify以证明29959个原顶点对应，固定8骨原权重支持共1146点以外的28813个实际变形顶点逐帧SHA一致，随后恢复modifier且不保存。49项通过是新增差分证据，没有把旧1049项改为跳过差异或声称重新完整跑过1049项。

原始袖／皮肤三角相交与ray提示仍非零，包含袖口尖包边、内衬与掌根接触。独立及根任务实际查看的关键beauty材质诊断图未见原矩形侧壁皮肤破口或袖壁翻折，故保留v6这一shape，不为raw pair归零继续追加过度修形；这不等于证明所有几何互不相交。

## 26块材质与透明语义

`ikhor_character_materials.py`按源材质逐项映射脸、肌肤、发、布料、皮革、金属分区、蓝晶及独立五官；保留`MMDShaderDev.Color/Alpha`、贴图及sphere语义，包括眼层原加算球面。这里的Color是MMD合成色，不是已提取的纯游戏Albedo。五官不经过全身色带重复压暗，非五官仅接一次有效材质色带、一次短距AO及相应发带／亮边。

伊科尔没有已验证的脸部SDF。脸用随姿态的头部前向形体法线，先软化形体，再乘面向实际主灯且带相对距离补偿的Diffuse响应。标定0.055–0.34只适用当前灯组；该探针仍含间接光、灯形及综合遮挡，不是纯visibility或游戏阴影贴图。没有把阿克西妮娅或空的控制图套到伊科尔，也没有给最终脸亮度加下限抹掉遮挡。

原改版脸图`y1.png`缺失，显式回退到随包同角色`Avatar_Boy_Undefined_Purusa_Tex_Face_Diffuse.png`，并核对实际UV与脸／眼孔／嘴布局。这不是恢复了缺失的y1。另一个游戏资产ZIP被Cloudflare阻挡，未取得其中SDF；不能把网页文件清单当成本工程已有贴图。未验证Lightmap／法线图通道不接入着色。

衣饰金属与蓝饰发光按原颜色图做HSV美术选择，不冒称游戏Metallic／Emission／Lightmap数据。金属与布料分别使用受控Principled闭包；HDR边缘和局部蓝饰经颜色输出及AOV送Glow，不保证照亮邻近物体。

production-v4仅将`首`、`手`两块skin色带的阴影端由约`(0.67,0.49,0.48)`校准为`(0.78,0.63,0.61)`，保留形体与真实受光响应。脸与手原本使用不同底图，残余色差仍待猪猪观看，不能称统一肤色已解决。

婚礼版把任务部件`环`、`灯`的有效Alpha从1改为0，同时禁用其描边壳；角色覆盖率、StageArtRim和BoldWeddingEmission均遵循源Alpha，避免部件消失后留下黑壳或发光。原PMX保留，可在独立后续版本恢复；这不是原素材本来透明。描边保留原PMX启用状态及顶点权重，局部调整宽度／颜色，不能解释成固定像素线宽。

## 礼堂三层照明与可见光束

原paierer礼堂不替换。三层分别服务人物可读性、礼堂光区与后方婚礼光装置：

- 人物保留各自主光预算与独立接收集合。伊科尔实际主光490W参与Diffuse；18W补灯、225W后侧灯、320W宽反射灯均不参与Diffuse，保留镜面贡献，减少把卡渲响应洗平。阿克西妮娅由`bold_wedding_materials.py`增加蓝饰HDR与方向化窄亮边，不给整张脸或整件衣服统一加光。
- 礼堂重分冷窗、暖祭坛、地面光池与局部补光，前景空间遮罩增益0.56保护人物。原后方局部空气与新散射盒均限制在演员后方；原完整体积阴影仍关闭，不称全物理。
- 新建一蓝一金两条开放式婚礼弧、32个可复现缓慢运动光点，以及每侧3个共6个真实spot。初版spot／散射盒未形成足够清楚的可见束，因此最终另加6个沿初始灯轴放置、径向与轴向柔化的Volume Emission锥体。真实spot仍负责场景照明，可见锥体是独立美术光束，不是完整物理散射或恢复体积投影。

人物`BoldWeddingEmission`与装置`BoldWeddingFX`分别送选择性Glow，背景装置辉光用人物覆盖率保护大部分人物区域。它们是PBR混合之前的美术源AOV，不是完整物理Emission pass；灯光、颜色输出和Glow分别说明，不把存在亮边等同空间受光已经真实融合。

以上为已完成婚礼基线的舞台记录。猪猪后续要求移除蓝／黄两弧，已在最终[Clean v2](CLEAN_GAME_CHARACTER_REFINEMENT.md#两条身后光弧的可逆移除)将两CURVE的render与viewport可见性关闭，原数据保留；新成片实际抽样已确认两细光弧消失，没有据此重做礼堂、灯组或间接光缓存。

## 已完成检查与失败记录

`production-v4\master-verification.json`：1049项技术检查通过。核对源阿克西妮娅与相机完整Actions、九时点姿态／焦距／DOF、伊科尔动画、材质与Alpha例外、描边AOV、六个美术体积、已打包且渲染使用的贴图、固定FLAC、File Output静音及有限物理范围；核验为只读，不保存工程。该检查未认证无穿模，不能覆盖猪猪已指出的4290帧袖子穿模，也不能代替修复后的重新验证。

`diagnostic-review\diagnostics-verification.json`：转头、移主灯、相机绕拍各24帧，共72帧原生诊断全解码通过。该中性试验为24fps，不替代正式60fps动作；根agent当时人工查看每组0／4／9／14／19／23六个时点脸条图，未记录critical新脸部错误。这不认证袖子无穿模或完整连续画面无闪烁。本子任务另看production-v2四张67%试图时未指出该袖子问题，抽样结论不能外推为整个人物通过；曾指出手掌偏粉褐与4439脸手偏软，前者促成v4有限校准，后者仍需最终分辨率与动态复核。

v6的新证据位于同交付根：

| 证据 | 已完成范围与边界 |
| --- | --- |
| `production-v6\master-verification.json` | 独立49项差分通过，绑定v4与v6 SHA；原1049项及72帧诊断仍按原版本追溯，不重新命名成v6全量检查 |
| `sleeve-review\geometry-verification.json` | 实际工程4139–4441全部303帧，无缺帧／重复帧；实际变形几何、骨矩阵及记录数值有限，每帧29959顶点。通过范围仅扫描完整性和技术一致性，raw相交／ray提示保留，不构成零交线认证 |
| `sleeve-review\visual-review.json` | 双腕4140–4439共600张480×480无DOF／MB诊断图，300帧并排视频全解码；根任务查看每手33时点联系表及若干关键原图，未以解码代替人工图审 |
| `sleeve-review\independent-visual-review.json` | 独立实际看每手33个重点时点及24个等间隔时点，去重每手54点；另逐张看18张480px关键原图及左4221–4225五张800px图。结论仅为同段诊断抽样可进入beauty渲染，`user_art_approval=false`、`geometry_collision_certified=false`，未声称人工逐像素看完600图或连续视频 |

双腕原始诊断图及并排视频在`D:\codex\output\MMD-Ikhor-Sleeve-Repair-v1\continuous-v6`。诊断保留角色生产材质与角色灯，隐藏礼堂／后期，使用从原相机位置方向重构的正交腕部近景；它不是最终1920×1080透视beauty。几何ray仅提供可能可见候选，不包括真实Alpha、描边、礼堂、另一人和最终合成，不能把提示数直接当成画面破口或要求清零。

早期失败与排错边界应一起保留：导入物体存在但Bullet集合为空时曾出现零参与刚体，已拒绝作为物理结果；清理时删除顺序曾导致Bullet引用崩溃，改为先删约束、移除世界、再清其余物体，并从视觉烘焙检查点恢复；字段误用须按实际PMX／RNA更正，不以报告里一个“baked”代替参与与重开证据。透明任务部件曾有描边壳残留，需同时检查源Alpha、壳和AOV。上述都是失败经验，不是通用适配能力认证。

## v7双人字幕修复与完成的五秒

`Caption | both performers native object coverage`曾保留`空_mesh,阿克西妮娅2_mesh`，导致替换后的伊科尔没有进入后台字幕覆盖率。v7只把名单改为实际两人`阿克西妮娅2_mesh,Ikhor | mesh | Ikhor_mesh`。`production-v7/master-verification.json`独立38项差分通过：所有几何、材质、灯、镜头、完整Actions及beauty依赖图不变，Cryptomatte仅连actor cache，不进入beauty／Composite。因此复用完整v6 beauty有明确同源依据；不是用旧画面掩盖新材质变化。

正确遮罩由v7重渲300帧1920×1080、48 samples、16bit灰度PNG；另外生成两人各300帧核对，保留源材质与描边Alpha、原DOF和运动模糊。总报告在`D:/codex/output/MMD-Ikhor-Caption-Matte-v1/full-v1/matte-verification.json`。没有用一律不透明的覆盖材质填平透明部件，也没有把Alpha=0的`bq`／`灯`／`环`重新带回。

同根`caption-matte-review/coverage-positive.json`沿实际骨骼投影，在完整300帧对两人的头／身体各取一处内部ROI，1200个ROI均为1；固定阈值来自明确的正确样本，没有逐帧自适应。`coverage-negative-old-v2.json`对旧actor缓存做同样负例，伊科尔600处全部为0而阿克西妮娅仍为1，成功复现遗漏。全图mask mean非零只能说明有人存在，不能证明双人均存在；内部ROI也不能代替每个透明边缘像素的认证。

`captions-5s-v3`两版均完成300帧全解码、1920×1080／60fps／5秒及音轨核对，字幕版分片接缝检查通过。颜色合同为709矩阵／709基色／实际sRGB曲线／limited电平，属于电脑审片输出，不称BT.1886调色母版。正确源字幕边界4162／4271及整组前后层级保留；前景组仍按设计在人物前，后台组使用修复后的连续双人覆盖率。

实际人工检查记录在同根`manual-review.json`：两版各12个抽样时点（4146、4171、4196、4221、4246、4271、4296、4321、4346、4370、4395、4420），另看四处字幕边界各8帧、共32帧连续图，以及4190／4220／4290／4318的原生腕部beauty。后台牌面4244及4307–4309的文字不再盖住伊科尔；抽样未见原侧壁皮肤破口或大片反折。这不是人工逐帧看完300帧，也不是零几何相交或用户美术认可。衣发及袖修复的新物理认证范围仍仅4139–4441，全曲未交付。
