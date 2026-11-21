# Blender5.3原生作者节点双人试作

猪猪在2026-11-19明确要求后续试作转到Blender5.3：人物真正套用提供的`5.3卡渲节点.zip`，其余礼堂、动作、相机、配色和场景尽量复刻当前Goo。此前Goo方向“暂时看起来不错”，不是本轮原生5.3成图的美术通过。本轮由`gpt-6.1-sol xhigh`负责节点阅读、迁移代码及图审，low只执行固定命令。只做4290静帧，不新模拟物理、不恢复眼透或视频。

## 冻结源与原生运行环境

Goo源是`D:/codex/output/Goo-Duet-SDF-2026-11-19/final-v1/Franken_Duet_SDF_SourceDOF_Still.blend`，SHA256 `829f2d88827320c48a19ed76df4dc70af495455e4a660769c2bb53fe461caa69`，只读保留。作者包私人blend SHA为`d9696f8f165823e17fb542ce4b157351c657c79e958aefb87fe677d4e71f80fe`。不导入芙宁娜网格、骨架或贴图；不向repo复制第三方完整节点库。

官方Blender5.3.0、build`02f0899d78e3`从已校验便携副本复制到`D:/codex/workspace/blender-runtimes/5.3.0/`，没有重复下载。源／目标6999文件、1,003,142,298B；blender.exe两端SHA为`6670c69fbb562c0fd1fae1e35f5413a90781cdf7d44af151ee4c9c3b82a38174`。使用其`portable/config`、`portable/scripts`，不改Goo／全局偏好或系统关联。

只注册验证过的MMDTools源码以保留MMD相机RNA，没有同时注册旧／新MMDTools或启用其余Goo插件。首次注册因缺OpenCC失败，保留失败log；只把原已安装的纯Python OpenCC0.1.7包和MMDTools复制到独立modules／addons，重试成功，没有附加整套Goo site-packages。`scripts/native53_runtime.py`负责先注册相机依赖再打开工程。

## 读取与新增学习

复用[作者包研究](BLENDER53_TOON_PACKAGE_STUDY_2026_11_18.md)的官方四节点正文、私有作者工程和十二个视频抽样时点，不称听完或取得全字幕。这轮继续读取作者主组、Closure签名与角色保存参数，并读官方安装包`startup/bl_operators/node.py`中的Closure输入／输出配对及item创建方法。

作者主光实际为SUN、energy3；髮材质保存受影=true、Roughness1、主光高光强度0，脸受影=false且SDF=true，白目受影=false。参数必须按角色适配，不能把这些数值当通用“最好看”预设。

[官方5.3 Light Linking](https://docs.blender.org/manual/en/5.3/render/lights/light_linking.html)确认EEVEE可限定灯的receiver；它用于重建原Goo default组排除，而不是改场景曝光。新LIGHT标签和允许列表只影响人物shader的逐灯输入，不改变原礼堂灯的位置／功率。

## 双运行时只读审计

`scripts/migrate_duet_to_blender53.py`固定源SHA，关闭autoexec，先分别在Goo和官方53导出原node／socket／link／灯组合同以及动作、UV、权重、Shape、相机与五姿态求值数据。两边相机焦距约61.73465mm，源DOF开启、焦距距离约2.60241556m、f/3.2、8叶；没有factory-only的1mm错误。

原生53有35个ShaderInfo变成undefined，不能据可打开就称兼容。非人物仅两个地面材质中四个Cast出口；其他礼堂／世界／体积／合成保留普通节点。用原Goo导出的连线明确重建selected-light ShadowRaycast／Light Accumulation许可，保留未知原节点但不让它们进入活跃Surface／AOV上游。

桥接的Cast／Self都映射为原生总可见性，没有证明引擎内部遮挡分离完全等价；Half-Lambert是几何法线与选定光向的数学桥接。两盏原head key的Goo use_default=0转为actor-only receiver，避免在53多照礼堂。技术基线实际渲染后，背景／原景深总体对应；旧人物桥接后出现偏色／自影条纹，不能把这张基线当作者shader质量。

## 真正接入作者主组

只Append`新卡渲着色器`及它自动需要的公共子组，并断言新增objects／meshes／armatures／images／actions为空，首轮已实际通过。每个角色复制一份真实主组，只增加LIGHT角色标签与逐灯允许列表。材质实例按face／skin／hair／cloth／fur／trim／iris分区；黑线、隐藏层及原平涂嘴内等工具材质保留原职责。

角色原MMDShaderDev Color／Alpha／sphere语义保留。头饰的输出最外层是金饰物理mix，Alpha在内部；最初以统一外层Alpha形状定位失败，保留该失败。修正为只替换原NPR emission的shader消费者，原透明Factor、金饰物理混合和眼角膜链保留，并逐项核Alpha Factor未变。

头部GN只写`前面`、`人物左侧`、`头顶朝向`和面部方向属性，不改位置／蒙皮。阿克Closure读取自有FaceLightmap R并采用作者传入的左右UV；伊科尔Closure读取自己的512²RG阈值，按当前灯位选左右通道、直接用本脸原UV，不取芙宁娜图。原4290刘海几何采样色层独立保留。

## 已保留的失败与定位

author-trial-v2已实际套原组并出双方近景及双人，xhigh逐图拒收其美术：Aks过暗，人物有黑色斑条。两脸实际受影flag确为false，因此没有只靠该布尔值推断原因。

两项隔离诊断只改一个变量且不保存工程：A把作者主组ShadowRaycast出口置1，条纹消失但暗面仍在；B仅关闭actor Solidify，Aks条纹仍有，故描边壳不是唯一原因，也不将所有人物阴影关闭作最终修复。

进一步沿原组真实连线查到`is_sun→混合.016`：SUN分支才进入主光／SDF选择，AREA即便标主光也走另一分支。下一项有界修正是为每人增加仅照本人的SUN代理，方向继承原head key，原所有灯不改；同时只把作者ShadowRaycast起点沿TrueNormal偏移0.6mm，保留真实发束／衣物遮挡。该项实际图审结果待回填，不把计划写成已成功。

## 结果

当前仍在有界试制；最终新工程、源DOF双人、近景／对照与持久runtime独立重开完成后再登记结果。技术通过、xhigh图审与猪猪美术认可分别记录。没有认证动态、全曲或整体游戏参考质量。
