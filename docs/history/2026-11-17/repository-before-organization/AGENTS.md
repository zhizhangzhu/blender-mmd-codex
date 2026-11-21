# 本仓库的制作目标与工作约定

## 目标与阅读顺序

- 称呼用户「猪猪」；GitHub `zhizhangzhu`。源码在 `D:\codex\workspace\`，交付在 `D:\codex\output\`，临时文件在 `D:\codex\temp\`。
- 核心目标：逐步达到原神／鸣潮风格游戏级三渲二的感知质量，参考Gosari542、观海子，再发展个人风格。当前尚未达标，不把风格名、安装插件或技术样片当成质量认证。
- 先读README、`catalog/current_state.json`、`docs/PRODUCTION_WORKFLOW.md`、`docs/KNOWLEDGE_INDEX.md`、`docs/LOCAL_ENVIRONMENT.md`；按任务读人物／物理／参考手册与相关skills。成片请求使用 `skills/mmd-finish-render/SKILL.md`；相机检索使用 `skills/mmd-camera-search/SKILL.md`。
- 现行状态与用户反馈以 `catalog/current_state.json` 为准；关卡见 `catalog/production_pipeline.json` 和 `docs/QUALITY_GATES.md`。旧文档的“当前”只对应写作日期。整理前约定完整快照在 `docs/history/2026-11-13/AGENTS.snapshot.md`；旧记录不是新任务指令。
- 用户已授权在既定任务内自行判断常规可逆操作和技术选择，不重复索取确认；确需缺失信息或用户连接浏览器时，说明具体原因与最小操作。可并行分配学习、制作、物理核查和独立验收，统一输入版本后再整合，不以子任务完成代替最终交付。
- 学习优先省token／流量：检查既有缓存，图文与字幕优先；打开研究视频先暂停并读状态确认，不默认播放4K，不任其自动连播。只按时间码低清核对必要画面。字幕正文只私人缓存一次，repo写原创总结与来源。后续浏览器常规操作已授权，不重复问同一许可；失败分阶段有限重试。见 `docs/EFFICIENT_RESEARCH_WORKFLOW.md`。
- 参考优先级：观海子首要，Gosari542保留，御手洗板蓝根为原神动画渲染补充；短链 `https://b23.tv/B55DoZl` 尚未解析，不能把检索作品当已确认目标。见 `docs/AUTHOR_REFERENCE_MATRIX.md`。
- 用户所说“持续学习”主要指实际阅读外部MMD教程、图文和技术讲解，优先完成有实质增量的外部阅读；队列和文档维护作为收尾，不能用流程建设代替技术学习。可用 `catalog/learning_queue.json`去重与续接，阅读／假设／静帧／动态／重开／整合分级留证。详见 `docs/EFFICIENT_RESEARCH_WORKFLOW.md`；研究阶段不自动改生产工程或恢复全曲渲染。

## 当前项目约定

- 2026-11-17猪猪明确要求：后续修改默认只看静帧／对照图，不渲染生成样片。除非猪猪后来明确要求视频，不启动片段或全曲视频渲染；旧的五秒默认输出约定在此被覆盖。

- 2026-11-16猪猪明确要求后续改用 Goo。新制作优先 `presets/runtime/goo-v1.json` 的 Goo 5.2.1 **非官方社区移植版**（构建0051aee03764），不要从旧段落继续默认普通5.2。原本地Goo4.3.2实际启动但读不了5.2文件，未作生产降级。独立新工程与插件/动作核查见 `docs/GOO_ENGINE_MIGRATION.md`；用 `scripts/goo_runtime.py` 先注册便携插件再打开，保存偏好只能用独立CONFIG。原工程/Blender保留。当前五秒字幕样片是否完成看current_state和实际preview-info，不从启动命令推断；仍仅一版1080p、5秒、字幕＋指定FLAC，按用户要求不作输出后检查。
- 原生Half Lambert、Cast Shadows、Light Groups已有小场景实渲并接入21项材质；脸部SDF/代理、现有轮廓线/暖边与场景保留。Curvature Scene Rim小测试输出黑，未接成片；不能声称专属Cel/Anime Line存在、原版PowerShader/Ray运行或所有插件功能全通过。优先兼容现成预设，Goo迁移不自动重做物理或恢复全曲。
- 2026-11-16 MME增量：已取得PowerShader/PAToon/tn_PostPointLight/wDark等9个原包并读重点说明与源码，范围及许可见`docs/MME_TO_GOO_LIGHTING_STUDY.md`与对应research账本，不等于全部49位作者效果掌握。tn点光不支持自阴影，wDark不是光源。Goo v2入口为`prepare_goo_daylight_v2.py`和`add_goo_window_gobo.py`，仅新副本；窗外Sun当前被建筑遮挡，窗格光带用镜头外真实gobo模拟，不能称原窗框逐格还原。前1.5秒新增全身开场，后接原MMD相机；原Actions、网格坐标、贴图及五时点姿态独立重开相同。实际样片是否编码完成看current_state及preview-info；不恢复全曲，不补做用户已跳过的输出后检查。

- 2026-11-15静帧增量：`D:\codex\output\MMD-Portrait-Relight-v1\production-v1\Franken_Duet_Portrait_Relight.blend`与同目录`complete-4290.png`已保存/实际渲染4K；新链只验证静帧，独立重开以同目录master-verification.json为准，用户美术待评价。最新完整视频仍是下述Clean五秒，不自动渲染新视频。入口`prepare_portrait_relight.py`仅接受固定Clean v2 SHA，不对新工程重复安装；细则见`docs/PORTRAIT_RELIGHT_IMPLEMENTATION.md`。

- 2026-11-14最新反馈：Clean仍灰蒙、人物与亮边不够明亮；最低局部目标参照用户本地paierer《奥黛塔&沃雅妮莎 _ 愛包ダンスホール》，观海子仍是核心风格。用户允许必要时调整舞台和灯光来突出人物，保持角色配色、婚礼主题及去光弧要求。现行成片美术状态为revision_requested。
- 最新学习见`docs/PORTRAIT_LIGHTING_AND_SHADOW_STUDY.md`：白菜542条字幕全读＋14时点核图、paierer8帧、5篇摄影正文、方向rim／脸影新原作者资料、Node Wrangler本机临时注册。三张4290诊断在`D:/codex/output/MMD-Portrait-Lighting-Study-2026-11-14/controls-v1`：B仅关两散射盒、C再加限定HDR rim gain2；B去灰雾有效，C青边偏抢，不是新生产预设。无新blend或5秒，不能替换下列最新已交付文件。
- Node Wrangler随包4.1.0存在，保存偏好未启用；临时注册／注销已测，GUI启用状态未查。内置材质预览会改接输出，先在副本逐段诊断并恢复Alpha／物理混合。普通EEVEE的Shader to RGB用Combined交叉核验，AOV不自动等于真实shadow pass。
- 新诊断必须注册既有MMD相机RNA并核焦距／driver有效性；factory-only曾得1mm错误相机，已判废。正式同帧三图为61.73465mm，1280×720／48samples，DOF／MB统一关闭。旧不同相机图不能作照明对照。

- 最新完整交付工程 `D:\codex\output\MMD-Clean-Game-Characters-v1\production-v2\Franken_Duet_Clean_Game.blend`，SHA `0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4`；两版在同根`captions-5s`，文件`Franken_Duet_5s_CleanGame_Wedding_REVIEW.mp4`及`Franken_Duet_5s_CleanGame_NoCaptions.mp4`。原帧4140–4439、1080p60、五秒；人物按两份本地参考精修、两条蓝／金细发光弧隐藏。独立材质321项／去弧26项、三轴72帧、全新beauty／actor300、两版全解码／音轨／色彩／各自接缝、1200个双人头身ROI及指定FLAC独立PCM比对通过；人工两版各12时点、32帧边界连续图、7张原生腕部关键帧另记在manual-review，4140／4290此前也已看。参考差距和非零几何接触仍保留，美术未获用户认可，详见`docs/CLEAN_GAME_CHARACTER_REFINEMENT.md`。
- 前版婚礼v7在`D:\codex\output\MMD-Aksiniya-Ikhor-Wedding-v1\production-v7`，旧两版在`captions-5s-v3`，保留作修袖／双人字幕输入历史。v6→v7仅字幕名单的38项差分曾支持该批beauty复用，不能推广到Clean；本次新300帧已全新渲染。旧v4袖穿模帧及遗漏伊科尔的旧actor缓存均不复用。
- 双人全曲未交付，旧长渲染已停止；当前只完成上述五秒，不自动恢复全曲。未来明确要求成片时按约定范围完整输出，不能停在启动后台或试渲染。
- `presets/projects/franken-duet-full-v1.json`：阿克西妮娅→Full HimeTanaka，伊科尔→Full HinaSuzuki，横屏16:9；空仅为历史角色。原生相对站位保留，两人材质和表情独立映射。换动作不能复用旧分轨的物理烘焙。
- 素材根 `E:\tools\franken`；完整VMD位于 `drive-download-20261018T085726Z-1-001`。VMD与FBX不同，优先PMX+原生VMD；FBX另核骨架与重定向。
- 使用用户选定paierer「赫斯珀利德斯之馆-礼堂」，根目录见项目文档。主题雪＋婚礼＋爱，悲壮中有释然与温暖。不要用原创舞台替代；不再主动换场景。Aiko宮殿禁止Blender成片渲染，排除；雪韵仙庭有等级门槛，不绕过。
- 后续需要新素材时优先BowlRoll、DeviantArt、BOOTH与作者配布；用户要求不广泛搜索模之屋，主动指定的链接可核对。许可、署名以随包文件为准。
- BGM固定 `D:\codex\output\Franken-Duet-Full-Audio-v1\HIMEHINA - フランケンシュタインの怪物.flac`，198.3158125秒，96kHz/24bit双声道；不得换回伴奏／MP3。音频转换见 `docs/AUDIO_CONVERSION.md`，不要把音轨加入等同卡点完成。
- 优先现成镜头VMD，现有とっとこ相机保留；用户暂缓全曲校正。横竖屏镜头、排版、字幕和光学效果分别设计，不只裁切。字幕可整组在人物前或后，不默认“不遮人”。

## 环境与安全操作

- 启动器 `E:\tools\Blender Foundation\Blender 5.2\blender-launcher.exe`；脚本用同目录blender.exe，不重复安装。当前实测5.2.2 LTS、Python3.13、MMD Tools扩展4.5.14；模块 `bl_ext.blender_org.mmd_tools`，不同时启用旧mmd_tools。
- 默认独立后台进程、新输出目录；不改偏好、不覆盖原素材和旧视频、不把后台工程说成用户GUI当前场景。诊断脚本静音继承File Output，禁止覆盖旧EXR／缓存。
- 软件／插件状态区分磁盘存在、已启用、进程注册、素材导入、静帧、动态、便携重开。Goo是独立构建，已运行5.2.1社区移植版并迁移，详见上方2026-11-16增量；Malt未验证；Abnormal仅临时注册，不能升级成掌握GUI。优先现有插件，按实际问题决定是否引入新依赖。
- 生产脚本和历史打包器有明确输入约束，先查 `docs/TOOL_AND_PRESET_MAP.md`；不能对任意当前工程全量运行旧场景构建或package_*。历史打包器可回写catalog，运行后复核现行状态和用户反馈。

## 人物与空间

- 保留MMDShaderDev Color/Alpha及贴图／球面／透明语义；避免旧逐通道压缩灰化。先按 `docs/CHARACTER_NPR_PLAYBOOK.md` 拆清底色、SDF、形体、真实遮挡、AO、高光、辅助光、Emission输出与Glow，单项可关闭。
- Emission输出不等于均匀自发光，也不保证角色照亮场景。当前Diffuse探针是多灯／法线／衰减／间接光的综合受光，并非纯投影通道；固定阈值只对当前灯组标定，不每帧自适应。场景灯不一定能控制Emission型NPR。
- 历史入口 `prepare_reference_transfer.py` 只接受CharacterLayers production-v2的指定SHA，不能在最新版重复运行。伊科尔整合／修袖／字幕修复后的基线另见`docs/IKHOR_BOLD_WEDDING_PRODUCTION.md`；实际主光490W参与Diffuse，补灯18W／伊科尔后侧225W／320W镜面宽光不参与Diffuse。一次有效材质色带和短距AO、五官、金属闭包与Alpha继续保留，不把历史空的材料映射直接套给伊科尔。
- 新材质入口`prepare_clean_game_duet.py`与男女`clean_*_materials.py`只接受固定婚礼v7 SHA，新目录另存；四模块为palette／response_ramp／highlight_metal／rim，不能在已改工程重复叠加。阿克西妮娅鼻块定位到原FaceLightmap red局部SDF岛，仅在鼻UV许可内作同图邻采样修形，保留嘴缝、脸侧、主灯综合受光及AO；伊科尔无已验证脸SDF，白外布提亮用原HSV许可＋金青排除＋高光余量，保留深衬和原FaceDiffuse回退。
- 当前自阴影使用面向实际主灯、带相对距离补偿的Diffuse综合受光近似，独立几何形体与阿克西妮娅已有SDF在前，再乘标定的受光响应；不是纯visibility或游戏阴影贴图。原先随头前向平整探针属于前版。不能用最终脸亮度下限抹去阴影，不直接启用失去Goo输入的Catch Shadows。受控Emission亮边不保证照亮场景；局部舞台AOV后期保护人物，不称物理光通道。
- 旧 `prepare_character_layers.py` 只接受Grounded production-v3，不能用于当前版。其正确基线为production-v2，阿克西妮娅嘴缝节点 `Face ink | Mouth crease`；旧production-v1大小写错误及更早几何脸部暗斑方案均不复用。见 `docs/CHARACTER_LAYER_REFINEMENT.md`。
- 黑线保留原PMX/顶点权重，分区控制外壳与五官内线；Clean只另调阿克西妮娅发／毛领线的RGB对比，几何壳宽与权重不改。相对宽度不等于固定像素宽度；头发、脸、毛领和衣物分别验证。嘴缝UV、金属遮罩、HM/HN／Lightmap均须按模型重新映射，不能凭贴图名接线。
- 阴影区分投影、接触AO、自身形体明暗。脚踝骨高度不等于鞋底高度。共享场景材质需要世界高度／法线或明确几何接收区域，不把墙和地面一起压暗。灯光链接是美术控制，作用对象须记录。
- 蓝金婚礼局部体积起点y2.5，避免World雾洗脸；可见体积锥含独立美术Emission，完整体积阴影仍未开启，不称完全物理。Clean v2按要求只把蓝／金两弧的render与viewport可见性关闭，曲线原数据保留，其他舞台／灯／旧probe缓存不重做或重烘。最终Glow改变后同步重接Caption cache beauty。

## 动作、后期与交付

- 物理按 `docs/PHYSICS_MOTION_PLAYBOOK.md`：原生刚体／关节、顺序预滚、连续模拟、骨骼视觉烘焙、独立重开核对。伊科尔原生衣发与局部袖修仅验证4139–4441；8袖骨局部物理／右软限幅及左单corrective另见`docs/IKHOR_SLEEVE_REPAIR.md`，不能称全身纯物理或零交叉。Clean严格保留几何与全部Actions继承这些有界证据，未新模拟。历史胸部适用性审计的动态候选属于披肩／毛领／围巾、空的4个胸先骨零权重，未新增胸部solver或动画，不推广成伊科尔胸部物理通过。见 `docs/CHEST_SECONDARY_MOTION_VALIDATION.md`。
- 30→60fps同时变换关键点和插值柄，检查相同实际时间姿态；改fps不等于重定时。旧全曲11900附近范围不意味着已交付。
- 字幕固定整组层级，前景不按脸部局部挖字，背景用连续双人覆盖率。正确Crypto目标为`阿克西妮娅2_mesh,Ikhor | mesh | Ikhor_mesh`；旧空名单和`captions-5s-v2`会漏伊科尔，不能复用旧actor缓存或只凭全局mask非零判断。每人头／身ROI正例及旧缓存负例另记，边缘Alpha／DOF／MB保持。黑底MP4不是RGBA；凸白牌黑字与字形内孔分别处理；正确源边界4162／4271需保留。
- 桌面审片保持显示sRGB输入，明确709矩阵／709基色／实际sRGB曲线／limited视频电平，编码和混音后实际解码验证。不是BT.1886调色监看母版；不由截图断言PotPlayer设置错误。
- 技术验收、抽帧美术观察与用户认可分开。完整约定片段须实际渲染、全帧解码、检查音轨和接缝，注明人工抽样范围；未完成全曲、未匹配风格等必须说明。

## 学习和知识维护

- 图文原作者／官方优先，视频按字幕／转写／画面互相复核。视频不是原始VMD或Shader，署名与引擎猜测分开。没有看到内容时不编逐镜分析；没有拿到字幕时不称已转写。
- 2026-11-13最新随包26.1111.21308：IAB与本地Chrome均曾实际读到B站正文，后续网络监听／调试仍不稳定。官方脚本已确认Chrome Profile 2扩展启用、native host正确，不能继续建议补权限／重装。未取得完整B站字幕。两个自动连播的代理研究标签已关闭并核实；优先按用户要求使用Chrome。实际边界见 `docs/BROWSER_AUTONOMY.md`。不要绕过登录、等级或付费限制。JiJiDownload路径 `D:\Program Files\JiJiDownForWPF.exe` 未实测自动下载。
- 原创总结写docs，来源账本写docs/research，参数写presets；不提交第三方完整视频／教程字幕／源预设。私人研究帧放交付或临时目录，Atlas只用有权展示的本工程预览。
- `catalog/library.json`管理分类与预览，`site/`为离线站点；更新知识与状态后验证链接、JSON、实际产物。新知识说明阅读范围与已测边界；不以计划或研究冒充实现。
