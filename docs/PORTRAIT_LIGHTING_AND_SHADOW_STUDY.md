# 明亮人物与暗场层次：逐层布光、亮边和脸影

2026-11-14。猪猪反馈Clean五秒灰蒙、轮廓光不足，提供白菜教程的完整字幕及本地视频、paierer《奥黛塔&沃雅妮莎 _ 愛包ダンスホール》，并补充Zack Arias、Joe McNally及闪卓博识。观海子仍是核心MMD方向；新参考用于人物与暗场的关系，不改变阿克西妮娅／伊科尔的配色，也不恢复已移除的蓝金光弧。

本轮已完成外部实读、用户字幕全读、必要视频帧核对和三个同帧诊断。**没有新五秒成片、没有修改已交付工程，也没有把诊断C作为美术通过预设。** 现行工程仍是[Clean制作记录](CLEAN_GAME_CHARACTER_REFINEMENT.md)中的production-v2，SHA为`0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4`。

## 参考里真正值得迁移的关系

paierer本地4K视频实际抽看18／50／85／105／120／160／178／195秒，覆盖近景、全身和俯仰机位，没有完整背面或连续观看。主任务另外亲看18／120／195秒。画面可见：浅亮肤色旁保留粉紫颈影、肩影和手指暗面；白衣有灰紫层叠；深色结构线与细窄桃色亮边同时存在；深蓝远景前，沙发、桌面等局部仍明亮。具体Shader、灯数、光强和描边实现未知，不能从不同角色截图推曝光差或相似度分数。见[参考账本](research/PAIERER_DARK_STAGE_PORTRAIT_2026_11_14.json)。

因此验收目标应同时包含：脸与眼可读、暗面有设计、衣料保持固有色、边缘获得局部高亮、背景留出对比，以及线条不被Glow吞没。单独提亮皮肤无法证明这些目标都完成。

## 摄影经典怎样用于这套NPR

实际读了David Hobby的三篇正文及Joe McNally的两篇原文。Zack的OneLight与Nikon的Joe页面只取得课程／视频简介，没有看完整课程。知乎问题页曾识别到登录标签，IAB正文两次连接超时，改用Chrome创建研究标签也超时，公开读取403；最后清单未见知乎标签，未确认创建成功，也未关闭用户原标签。没有把用户提供的推荐清单写成网页全文实读。范围见[摄影账本](research/PHOTOGRAPHIC_LAYERED_LIGHTING_2026_11_14.json)与[连接记录](research/ZHIHU_LIGHTING_ACCESS_2026_11_14.json)。

| 可复用光型 | 学到的职责 | 当前双人的适配检查 |
| --- | --- | --- |
| 斜上柔主光＋近镜轴弱柔补光 | 补光先保证暗部细节，主光负责形体。来自[Strobist Shape and Detail](https://strobist.blogspot.com/2016/07/lighting-102-shape-and-detail.html) | 先让深蓝衣褶和眼窝可读，再确定脸颊／下颌方向；保留颈影，不把主光移到镜轴冲平所有表面 |
| 脸与白衣分区照明 | 近脸主光与较远补光可分别控制脸和白衣。来自[Distance and Two Lights](https://strobist.blogspot.com/2016/07/lighting-102-combining-distance-and-two.html) | 不为抬阿克西妮娅深蓝布而同时推白伊科尔袖子；先核灯光链接、材质分区及现有距离补偿，再测试衰减；双人移动时检查泵亮 |
| 主体曝光基准＋独立环境 | 以主体建立明暗参考，环境另定。来自[Twilight](https://strobist.blogspot.com/2007/09/lighting-102-balancing-light-twilight.html) | 保留礼堂、婚礼与冷暖气氛，让人物背后的区域安静；摄影快门控制环境的方法不能直接照搬，Blender快门会影响运动模糊 |
| 局部冷暖背光与受限染色 | 每盏彩光有明确落区。来自Joe的[城市照明](https://joemcnally.com/2021/04/20/light-and-color-in-the-big-city/)与[凝胶塑形](https://joemcnally.com/2023/06/12/sculpting-with-gels-in-the-studio/) | 暖主光、较弱冷补光和后侧亮边各自负责区域；避免所有补光都染蓝，以及全场增雾；不照抄示例灯数 |

蝴蝶光适合正面柔美近景，环形／短侧光适合增加脸部方向感，经典三点布光适合作为逐层检查顺序。这些是选型起点；二次元脸的鼻影与眼周仍须按角色设计，不能强求写实伦勃朗三角。摄影曝光档差只作实验尺度，灯的瓦数比不等于脸上照度比，照度比也不等于最终显示明暗比。

## 白菜教程：字幕与操作互相核实

用户提供的542条字幕全部读完，覆盖00:00.08–22:21.82；实际查看14个视频时间点，13处有效，05:34是空Render Result；另核4处原生UI裁图。主任务亲看07:26／10:50／17:45。作者画面使用Blender4.5.2，插入色彩段4.5.3；作者称本系列为PBR材质教程收尾，不能把它当成原神SDF专门课。完整正文与研究帧只留私人目录，repo保存[原创教程账本](research/BAICAI_LAYERED_LIGHTING_TUTORIAL_2026_11_14.json)。

有效步骤是：压住无关环境 → 暖主光确定形体 → 弱冷补光抬暗侧 → 后侧轮廓灯分离 → 限制体积影响 → 用渲染样张检查Glare高亮来源。画面核到初始主光100、尺寸0.75m；补光30.9、尺寸1m；17:45轮廓灯1200、Volume影响0。这是不同操作阶段的PBR场景值，不是本工程配方或已核最终主辅比。

教程先显示Glare高亮分量再调阈值，很适合排查灰雾。17:08的平滑0.1／强度1，在20:09已为1／3；不把某中间帧当最终值。教程强Glow、色散0.030、静态正面背灯和f/2不是本项目默认。插入段虽题为ACES，所看转换节点是sRGB→线性Rec.709且右侧仍Filmic，未认证完整ACES流程。脸上加权法向也不能不检查现有编辑法线就照搬。

## 当前图为什么不能只加灯瓦数

只读最新参数、构建源码、保存工程SHA和既有321／26报告，得到下列可核事实；它们不替代新受光数值采样：

- Clean没有降低真实主灯、补灯、背灯、World或曝光。继承人物key为490W；fill18W、rim225W、reflection320W，后三者的`diffuse_factor=0`。它们主要进入保留的物理分支。
- 材质亮边另外计算，不读取真实rim灯瓦数。上一轮阿克西妮娅Reference hair/body乘0.58／0.52，Bold head/body乘0.32／0.24，并加入方向许可；伊科尔hair由0.80到0.38、白布0.60到0.28，power由5.5到7。更干净的同时确实收弱了这条信号。
- 当前主色不是所有历史节点连续相乘。有效路径为保留的MMD Color→一次有效palette→一次短AO→高光／边缘→Emission及保留的物理混合。MMD Color仍不等于纯游戏Albedo。
- 阿克脸是`(0.38+0.62×SDF)×综合受光→palette`，鼻区做局部修复；伊科没有生产SDF。综合Diffuse含法线、衰减、间接光及灯形，并带当前距离补偿，**不是独立投影通道**。是否饱和需另采样，不能仅凭图树断言。

下一轮先分别看MMD Color、SDF/form、原始Diffuse灰度、补偿后灰度、标定response、form×response、palette、AO与rim；固定曝光后再决定改灯、标定区间或材质色带。

## 亮边、深线与面部阴影分别设计

[Unity UTS官方Rim Light](https://docs.unity3d.com/Packages/com.unity.toonshader@0.11/manual/Rimlight.html)与选定源码显示，亮边颜色、覆盖、羽化、方向和遮罩应拆开。名为Power／Level的参数不一定是纯增益：所读源码有参数进入指数。历史Reference分支的amount接SCREEN混合Fac，也不是HDR光强。已有形状固定后，优先在真正线性加法源上测试相对gain；Glare前后各看一次，源宽度不变仍可能因显示和Glow显得更宽。深度rim需要深度／法线等专门输入，增强当前Facing不能取得同样算法。详见[方向性亮边账本](research/DIRECTIONAL_RIM_LIGHT_2026_11_14.json)。

paierer的深色内部结构线与外缘亮光是不同职责。后续如需加深线色／加粗外壳，应另作开关和近远景检查，保留五官内线与PMX分区权重；不能靠Glow同时解决两者。

面部新读4篇原作者文章，见[脸影账本](research/FACE_SHADOW_DESIGN_2026_11_14.json)。重要增量：

1. SDF负责美术边界，真实刘海投影负责动态遮挡；发影应作为mask进入同一肤色明暗调色，避免另一层纯棕色覆盖脸纹理。普通EEVEE没有本轮已验证的URP额外Stencil/pass等价接口，偏移发影暂留后续分支。
2. 阈值图生成代码须核通道与数值编码。实读文章片段存在RGB写距离／A恒1与后段读A的差异，并出现`pow(...,0.45)`；不能原样当作线性数据图生成器。
3. 头部前／上／右构成完整姿态；仅用前向与世界轴造基会丢失歪头roll。正脸、yaw／pitch／roll、移灯、绕拍和手过脸分别测试，保留眉眼、颈部与发影。

## 本轮三张实际诊断

目录：`D:/codex/output/MMD-Portrait-Lighting-Study-2026-11-14/controls-v1`；报告`control-report.json`。独立进程每图重开同一SHA，4290帧、原相机61.73465mm、1280×720／48samples；三图统一关闭DOF／MB、保留原合成、静音全部File Output，不保存blend。源文件与userpref前后SHA一致，临时控制恢复后受检摘要一致；这是有界保护检查，不是再执行321项生产验收。

| 图 | 唯一递进变化 | 主任务与子任务实际观察 |
| --- | --- | --- |
| A-current | 当前状态 | 人物背后存在较大灰亮散射区 |
| B-scattering-off | 只隐藏两个VolumeScatter盒；六个独立发光锥及灯保留 | 中央灰雾显著减少，深色后景开口更清楚；人物亮面保持，此图没有重做面部阴影 |
| C-scattering-off-rim-gain2 | B上只将限定hair／cloth的既有加法HDR rim源乘2，保留方向／宽度／颜色／白布许可，face／skin不变，Reference SCREEN不变 | 发侧、毛领及袖侧亮边更明显，青色也更抢眼；深蓝衣大面没有同步变亮，尚不选为最终美术方案 |

隐藏的仅是`Wedding | bounded rear scattering`与`Bold wedding | bounded beam fan air`。C覆盖阿克12块、伊科6块限定材质，beauty／AOV消费者一起跟随；这不是新增全局光源。没有更改SDF、几何、物理、动作、灯功率或已移除的光弧。

首轮factory-only未注册MMD相机RNA，焦距错误为1mm，实际图审后判废，留在本轮temp；正式三图已读现有偏好使MMD注册，并验证相机driver及焦距。以后诊断也必须核相机驱动，不能只核对象名／变换。

## Node Wrangler的实际作用

本机随Blender带Node Wrangler4.1.0；保存偏好中未启用，临时注册／注销成功，userpref不变，未声称用户GUI当前已启用。它提高接线、整理与检查效率，本次没有渲染提速或画质增益测试。详见[实测账本](research/NODE_WRANGLER_LIGHTING_2026_11_14.json)及[官方5.2手册](https://docs.blender.org/manual/en/5.2/addons/node_wrangler.html)。

5.2里Shader的Ctrl-Shift-LMB预览由内置`node.connect_to_output`提供，会改接最终材质输出；Compositor同键接Viewer，NW的O连接最终输出。只在诊断副本逐段看信号并恢复Alpha／物理闭包。AOV另需定义和连接；Shader to RGB在EEVEE仅保证Combined正确，须以Combined旁路图交叉核实，不能把AOV命名为Shadow就当成独立真实阴影。

## 后续采用关卡

[参数与检查协议](../presets/lighting/portrait-layer-study-v1.json)只绑定本次输入，状态为静帧研究。优先从B的空间清理方向继续，按材质分别确定暖／冷亮边的颜色、窄度与强度；脸部再单独设计颈肩暗面和主辅关系。随后同姿态消融、转头／移灯／绕拍及双人交错必须通过，才另存候选工程和同段成片。

拒绝：深蓝变灰、白衣夹白、眼与内线消失、鼻口孤立脏块、整圈边光、遮挡处漏亮、人物换位泵亮，或只有增加Glow／雾才显得有光。当前没有新的动态、胸部物理或全曲验收；paierer最低视觉目标与观海子核心风格仍待实际制作和用户评价。
