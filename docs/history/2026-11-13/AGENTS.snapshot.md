# 本仓库的制作目标与工作约定

- 2026-11-13 接地分支后续增加人物自阴影与加粗黑线，最终工程为 `MMD-Duet-Shadow-Color-v1/production-v3`、最终视频目录 `captions-5s-v2`，状态以交付JSON为准。`production-v2` 是脸部几何明暗放大后出现斑块的弃用试验；`lighting-sample-5s-v1` 已因用户追加要求中止，不能当最终。人物预设 `presets/quality/duet-graphic-self-shadow-v1.json` 在实际受光AOV校准后，用随头部前向的平整Diffuse探针法线接收刘海投影，SDF保留；身体用原法线。不要直接开启失去Goo输入的Catch Shadows接口，也不要把脸保护回0.95抹掉遮挡。黑线只相对当前顶点权重分区增加，保留眉睫眼口内线，旧线宽控制仍保留新边色。完整学习记录见 `docs/SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md`。

- 人物接地与播放器色彩见 `docs/SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md`、`presets/stages/hesperides-grounded-shadows-v1.json`。阴影须区分实际投影、近地AO与人物受光；骨骼高度不等于鞋底高度，不据脚踝坐标移动人物。新增地面AO必须限制世界高度和朝上法线，防止共享材质墙面变脏。旧婚礼MP4色彩标签缺失；新桌面审片输出用显式709矩阵、709基色、实际sRGB曲线和limited视频电平，使用 `review_video_color.py`、`verify_review_color.py` 验证编码及混音后标签。不能把sRGB数值直接谎标成BT.709曲线，不能由截图断言PotPlayer配置错误。新入口 `MMD-Duet-Shadow-Color-v1`，仅原段五秒；动态及交付以JSON为准。

- 最新婚礼分支见 `docs/BLUE_GOLD_WEDDING_STUDY.md`：用户要求蓝金主题、射灯／体积光与光晕，以及蓝金字幕。入口 `D:\codex\output\MMD-Duet-Blue-Gold-Wedding-v1`，正式 `production-v4`；旧 v1–v3 为试验。局部体积 y 起点 2.5，不加 World 雾；射灯体积／表面贡献为美术分配，沿用未开启体积阴影，不能称为完全物理遮挡。最终合成新增光晕后必须同步重接 `Caption cache | beauty`。字幕预设 `duet-blue-gold-wedding-v1.json` 保留固定分组及4162／4271正确源边界，深色字仍不透明。仅同段五秒，待美术评价，勿据此自动开启全曲。

- 猪猪反馈聚焦舞台太暗，并要求参考《亲亲小狐狸》尝试顶光、逆光。最新柔光分支见 `docs/SOFT_TOP_RIM_LIGHTING.md`、`presets/stages/hesperides-soft-top-rim-v1.json`；入口 `D:\codex\output\MMD-Duet-Soft-Top-Rim-v1`，正式工程 `production-v2`，v1 地面偏亮为中间实验。保留字幕正确边界与原相机／烘焙物理，只做同段五秒，不自动恢复全曲；角色边缘为真实高光与 NPR 补充组合，脸部和五官不加补充亮边。柔光关闭图保留新 GI，不能称为全部提亮手段关闭。

- 最新字幕与灯光流程见 `docs/DUET_CAPTION_STABILITY_AND_LIGHTING.md`。当前五秒使用官方 Wide 字幕源，固定整组前后层；前景不能再按脸部遮罩局部挖开。`plate` 仅用于单张凸牌，不是黑底视频通用 RGBA 恢复。灯光源工程 `MMD-Duet-Captions-Contrast-v1/production-v3`，最终字幕需独立 Python 合成；不把其 Blender 视口说成含最终字幕。保持旧认可版，不宣称全曲或用户美术认可。

- 猪猪继续认为第一支夜誓缺感染力，第二轮见 `docs/FOX_STAGE_ART_DEEP_STUDY.md`。最终 `D:\codex\output\MMD-Fox-StageArt-v2\production-v5`／`sample-5s-v2` 已完成五秒 1080p60；技术与抽帧检查通过，仍待美术评价。地面仅替换世界高度／法线筛选的 2393 个多边形，勿全局改共享材质；Shadow Blocker Collection 为美术控制。亮边 AOV 必须排除 `面1`／`面2` 等完整脸部面片，不能仅按“颜／肌”判断；十时点原骨骼／相机／焦距精确一致、95 图打包。中间 v1–v4 与 sample-v1 不作为最终结果；大面积彩色转场和单人调度仍未实现。

- 新增小狐狸灯光／光学学习见 `docs/FOX_LIGHTING_AND_CINEMA.md`，实际五秒在 `D:\codex\output\MMD-Fox-Cinema-v1\sample-5s-v1`、工程在同根 `production-v2`。用修复后的质量主工程重排冷夜建筑／局部暖走道，原生 DOF 与运动模糊已在连续视频通过；原骨骼、相机轨迹和焦段保留。不是作者原始 MME 或用户已认可的新基线；只设计原帧 4140–4439，不自动扩展全曲。该实验 File Output 静音，辅助分层场景未随光学研究校准。

- 最新技术修订见 `docs/LIGHT_SPACE_AND_COLOR_PIPELINE.md`；主工程 `D:\codex\output\MMD-Quality-Integration-v1\production-v4\Franken_Duet_Quality_Master.blend`，最终样片 `sample-5s-v2`。修复了灯位导入依赖图顺序、头部世界坐标、适配 Face Factor 的 incoming 约定；五秒／72 帧控制测试／原生五时点分层／300 帧 EXR 已验收。后续技术迭代优先沿用该修订，旧用户认可画面仍保留作对照。诊断脚本必须禁用 File Output，正式 EXR 使用显式帧号；勿据此自动恢复全曲长渲。

- 当前入口为 `docs/KNOWLEDGE_INDEX.md`；分类元数据 `catalog/library.json`，静态预设库源码 `site/`，构建与验收见 `docs/GALLERY_GUIDE.md`。交付网站 `D:\codex\output\MMD-Atlas-v1\index.html`。新增知识／参数先归类，预览必须使用真实渲染，明确样片、静帧和研究状态。不要搬动旧预设／文档路径破坏已有脚本。
- 当前制作以用户认可的 `MMD-Ray-Hall-Genshin-Revision-v1` 五秒样本为基线；夜景／鸣潮为独立研究。历史进度归档于 `docs/PRODUCTION_HISTORY_CONTEXT.md`，不据旧段落自动恢复全曲长渲染。

- 称呼用户为「猪猪」；GitHub 用户为 `zhizhangzhu`。
- 2026-11-11 舞台美术／鸣潮研究：先读 `docs/STAGE_ART_NIGHT_STUDY.md`、`docs/WUWA_TOON_STUDY.md`、`docs/TUTORIAL_TRANSCRIPTION.md`。半开放夜景取得完整自动 ASR 草稿（非平台字幕）；鸣潮教程以画面为主，改用采样 OCR。独立实验在 `D:\codex\output\Stage-Art-Wuwa-Study-v1`，不替换已满意五秒版本；夜景 NPR 色池无真实遮挡，鸣潮 HM/HN 插口与文件后缀存在反向命名，不能据名称混接原神贴图。Goo 未运行，整套鸣潮管线与动态验收均未完成。
- 源码默认位于 `D:\codex\workspace\`；项目、预览图、视频、检查报告等交付物放在 `D:\codex\output\`；临时产物放在 `D:\codex\temp\`。
- 主要任务是让 Codex 实际完成 Blender MMD 制作，并将验证过的经验整理成可复用流程。近期参考 Gosari542 与观海子，分别维护可复用的渲染/后期及横竖屏方案，之后发展自己的风格。
- 优先阅读 README、`docs/PRODUCTION_WORKFLOW.md`、`docs/LOCAL_ENVIRONMENT.md`，按任务读取相关 `skills/*/SKILL.md`。
- 用户已安装 Blender，指定启动器为 `E:\tools\Blender Foundation\Blender 5.2\blender-launcher.exe`。脚本使用同目录 `blender.exe`；不要重复下载安装。
- 版本、插件、API 以本机实测为准。区分已安装、偏好已启用、进程已注册、素材导入通过、渲染通过；不能相互替代。
- 默认使用独立后台进程和新输出目录；不覆盖源素材，不保存用户偏好，不将后台场景当成当前 GUI 场景。
- 参考视频是视觉目标，不是骨骼、相机或材质原始数据。没有读到画面时，不能编造逐镜头分析。作者署名和引擎推测必须分开记录。
- 优先复用已安装插件。MMD Tools 新扩展模块为 `bl_ext.blender_org.mmd_tools`；旧模块 `mmd_tools` 未启用，不要同时启用两版。
- VMD 与 FBX 是不同格式。原生 PMX + VMD 优先走 MMD Tools；FBX 需要另外核实骨架和重定向，不能因动作名称相似就当成同一数据。
- 当前试作素材根目录 `E:\tools\franken`；模型选阿克西妮娅2；完整 VMD 位于 `drive-download-20261018T085726Z-1-001`。HinaSuzuki 和 HimeTanaka 是两个动作分轨，单角色只应用其中一个；当前默认试 HinaSuzuki。
- 导入草稿、物理未烘焙、静态测试镜头、未完成风格匹配，都必须在交付说明中明确。素材授权以随附说明为准。
- 用户当前允许将伴奏卡点留给自己处理；流程只需找到并记录原曲/伴奏来源，不把自动加入音频说成同步完成。
- 镜头检索使用 `skills/mmd-camera-search/SKILL.md`，当前实测及下载结果见 `docs/CAMERA_SEARCH.md`。Gosari542 本地参考已提供，路径和实际观察见 `docs/GOSARI_REFERENCE.md`；优先读取该视频。
- 用户已授权为完成成片自主学习技术、研究插件与寻找素材，并将实际验证的方法写入本仓库。请求「成片」时使用 `skills/mmd-finish-render/SKILL.md`，不能停在试渲染或继续事项清单。具体物理、材质、重定时和验收经验见 `docs/PRODUCTION_TECHNIQUES.md`。
- 渲染复审及新默认路线见 `docs/LOOK_REFINEMENT.md`：本机 MMDShaderDev 的 Color/Alpha 输出可保留贴图/球面/透明语义；首版逐通道高光压缩导致偏灰，不默认沿用。成片相机是 Blender 中脚本生成的关键帧，外部 VMD 仅提供焦段参考，不能称为原样套用或新制作的 VMD。
- 后续卡渲、灯光联动、细描边、AOV 局部泛光与镜头试验见 `docs/TUTORIAL_STUDY.md`。区分教程简介、完整正文阅读和本机实测；四秒无声研究试样不作为新成片。MME 的视觉方法需转换为 Blender 的实现，不能把 `.fx` 下载或教程参数直接当作 Blender 已验证能力。
- 用户已下载观海子两支参考，证据和署名见 `docs/GUANHAIZI_REFERENCE.md`。字幕遮挡是逐段美术选择，可在人物前、后或保护脸部；横屏和竖屏独立设计镜头/排版，不能默认裁切适配。
- 优先核对官方配布中的文字视频、伴奏和舞蹈参考。进阶教程、Cryptomatte 字幕合成和已验证命令见 `docs/ADVANCED_MMD_SUBTITLES.md`；Tall/Wide 文字时间对应不等于动作 `[f1794]` 或音频同步。两支四秒带声样片不替代已有正式成片，也不代表完成参考级材质匹配。
- 渲染/后期维护 Gosari542 与观海子两类参考预设；观海子分 graphic/neon 变体。入口 `presets/styles/catalog.json`，指导 `docs/STYLE_PRESETS.md`。渲染、后期、画幅导演/布局分别保存，使用明确的风格 × 画幅 package；横竖屏不得只裁切适配。继续项目沿用记录的 package，新增项目根据目标内容选择并说明，不从作者名字推断画幅。
- 用户希望以后发展个人特色。保留参考基线，基于版本化组件逐步试验，再增加个人 family；不提前宣称个人风格已完成。换模型需重新映射材质/遮罩，预设名不代表原作者参数或同等质量。
- 用户中意 BV18DJC6dE1S 的半兰伯特方向，阅读范围、评论来源及可调响应模块见 `docs/HALF_LAMBERT_STUDY.md`；进阶插件/材质/局部 AO/体积光实测见 `docs/QUALITY_LIGHTING_LAB.md`。实验参数位于 `presets/quality`，不覆盖已认可的风格 v1。区分线性包裹与 Valve 平方公式，RGB 控制信号不等于最终彩色打光；Abnormal 仅临时注册测试通过，GUI 操作未验证，Malt/Goo 未安装。
- 用户指出原预览黑色轮廓不足。后续按 `docs/SURFACE_REFINEMENT.md` 区分可见外壳描边与贴图内线，分别控制衣发/脸/毛领的线色与宽度，不以修改器存在代替画面验收。模型专属控制图、头骨方向高光与精修参数在 `presets/quality`，生成图不是原始游戏 PBR/ILM 贴图；换角色必须重映射和审看。
- 用户进一步要求脸部也有观海子参考中清晰的深色线，不能默认沿用几乎不可见的暖细脸线。新模型适配项为 `outlines-v2-face-black.json`，分别控制鼻颌外壳、眉睫和嘴缝；实际参考裁切、反壳开关对照及限制见 `docs/FACE_INK_REFINEMENT.md`。换角色需重查嘴缝 UV，单个描边 Cryptomatte 全零不作为验收凭据。
- 后续双人全曲角色分配固定为阿克西妮娅→Full HimeTanaka、空→Full HinaSuzuki；详见 `presets/projects/franken-duet-full-v1.json` 与 `docs/DUET_FULL_PRODUCTION.md`。优先用现成相机，とっとこ 359108 已下载/读说明/双人实际导入十帧检查，未完成全曲验收。阿克西妮娅换动作后不能复用旧 Hina 衣发烘焙；两人材质/表情独立映射，保留原生相对站位。猪猪已确认本次正式画幅为横屏 16:9，镜头、舞台、字幕和后期按横屏设计。
- 猪猪已提供 `D:\CloudMusic\VipSongsDownload\HIMEHINA - フランケンシュタインの怪物.ncm`，并指定后续 MMD 使用提取后的原声 FLAC 作 BGM。已验证主文件 `D:\codex\output\Franken-Duet-Full-Audio-v1\HIMEHINA - フランケンシュタインの怪物.flac` 为原生 FLAC、96 kHz/24-bit 双声道、198.3158125 秒。读取双人项目的 `audio.bgm`，不得默默换回伴奏或 MP3；转换入口 `scripts/ncm_convert.py`，说明 `docs/AUDIO_CONVERSION.md`，混流可用 `--project` 校验主 BGM。卡点与全曲时间结构未因此自动完成。
- 本轮猪猪要求完成双人全曲，**暂不做全曲镜头校正**，保留现成相机运镜。场景选择改为参考至冬雪国，皇宫／城堡均可，氛围“悲壮但有释然”；撤下暖粉沙龙提案。背景场景检索与实际访问状态见 `docs/STAGE_SEARCH.md`，优先正常作者配布，未下载/未导入不能称为已采用。
- 猪猪明确要求现成场景，**不要原创舞台作为替代**，并否决「天空の城」「聖堂前ステージ」「玉座の間」的视觉方向；已下载 Aiko 宮殿ステージ禁止 Blender 成片渲染，本项目排除，不再反复推荐。
- 猪猪再次强调选景仍要以**原神至冬形象**为主；有实体地板不等于视觉适合，不能只按通用欧洲城堡、免费或 Blender 文件便利选定。当前已看《冬夜愚戏》一张大厅参考帧，记录与证据范围见 `docs/STAGE_SEARCH.md`；未完成完整 PV 逐镜头观察。
- 最新主题为**雪＋婚礼＋爱**，悲壮之中有释然和温暖。最终由猪猪指定 paierer 的「赫斯珀利德斯之馆-礼堂」：`https://www.aplaybox.com/details/model/uRHK15qUygJZ`，本地 `E:\tools\franken\【原神】赫斯珀利德斯之馆(礼堂)_by_paierer_08fc2e9ffe6ce8e16fb42e2032c6f401\GI_Hesperides`。已读随包 readme、实际查看 Ray 预览并完成 Blender 场景审计/试渲染；后续适配此场景，不继续搜替代。场景研究不代表双人全曲成片完成。
- 猪猪要求不再广泛检索模之屋；正常寻找素材优先 BowlRoll、DeviantArt、BOOTH 与作者配布页。用户主动指定的模之屋链接可以核对。「雪韵仙庭」因等级门槛仅作视觉参考，不绕过限制。
- 礼堂渲染实测见 `docs/HESPERIDES_STAGE_RENDERING.md`，预设 `presets/stages/hesperides-winter-wedding-v1.json`。场景专用脚本 `mmd_hesperides_stage.py` 会重建研究灯光／相机，不能直接在双人工程运行。Ray `.fx` 只读参数，场景以 Blender PBR／探针／有限体积实现，人物保留独立卡渲与黑线；v7 场景贴图打包及独立进程重渲检查通过，落雪与正式双人整合仍待完成。
- 最新双人工程已整合为 `D:\codex\output\Franken-Duet-Full-Final-v1\production-v4\Franken_Duet_Full.blend`；上条“待整合”是旧 v7 研究状态。猪猪要求人物统一参考观海子，礼堂更明亮、靠近随包 Ray 预览；v4 加入亮窗／补光、作者本地扩展加算 MatCap 适配和窗外稀疏雪点，保留原相机轨迹。五时点全部骨骼与相机对照误差为 0，82 张图已打包。完整 1080p60 渲染已启动在 `full-render-v1`；最终视频与音频验收完成前，不称双人全曲成品已交付。继续监控实际进程，不停在预览或后台任务启动。

- 礼堂预览重建方法见 `docs/HESPERIDES_REFERENCE_REBUILD.md`，当前参数 `presets/stages/hesperides-ray-reference-v1.json`：23 份随包材质均选择 ToonBased（作者全局 TOON_ENABLE 未知），14 份加算 MatCap 和白幔旋转副贴图需要保留。已完成独立 1080p 场景及开关对照，56 张图打包、20 个表面／14 个 MatCap 重开验证通过；尚未合回双人或完成新视频。场景专用脚本会拒绝含相机或非原始对象数的工程。背景调色不能直接套到人物；局部硬折／亮斑和框架偏暖仍待精修，不宣称复刻成功。
- 2026-11-11 更新：新版礼堂已合回双人并完成 `D:\codex\output\MMD-Ray-Hall-Genshin-Revision-v1\sample-5s-v1\Aether_Duet_5s_REVIEW.mp4`，300 帧／1080p60／原声、音频和接缝通过；工程使用同根目录 `production-v3`，五时点骨骼／相机误差 0、150 张图打包。原神角色／预设学习见 `docs/GENSHIN_CHARACTER_AND_PRESETS.md`：空采用 festivities Boy Face Factor 适配，阿克西妮娅改用本模型 FaceLightmap，轻量发高光来自三一七片的谎言。用户预设在 `D:\BaiduNetdiskDownload\三渲二预设`；区分已读与真正用于渲染，不能把鸣潮 HM/HN 和原神 Lightmap 混用。Goo 是独立 Blender 构建，本轮未安装／运行，旧库有专用未识别节点；全曲仍未交付，不自动开启全曲渲染。
