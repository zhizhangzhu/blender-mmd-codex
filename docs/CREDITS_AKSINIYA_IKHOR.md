# 阿克西妮娅×伊科尔《フランケンシュタインの怪物》来源与署名

2026-11-14。用于本机非商业的阿克西妮娅＋伊科尔五秒制作；范围原帧4140–4439、1920×1080、60fps、16:9。当前完成的Clean工程为`D:\codex\output\MMD-Clean-Game-Characters-v1\production-v2\Franken_Duet_Clean_Game.blend`，SHA256为`0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4`；两版视频在同根`captions-5s`，分别为`Franken_Duet_5s_CleanGame_Wedding_REVIEW.mp4`与`Franken_Duet_5s_CleanGame_NoCaptions.mp4`。新材质／去弧后已全新渲染beauty／actor300帧，完成两版全解码、音轨、色彩、两版接缝与1200个逐人内部覆盖ROI验证；实际查看两版各12时点、32帧字幕边界连续图及7张原生腕部关键帧，详见[Clean制作记录](CLEAN_GAME_CHARACTER_REFINEMENT.md)及交付根`manual-review.json`。全曲未交付，美术仍有参考差距、未获猪猪认可。

历史修袖／双人字幕输入基线为`D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/production-v7/Franken_Aksiniya_Ikhor_Bold_Wedding.blend`，SHA256为`f9442577a61a2c1cc4f39442e4468d42f13d42311fdd9f9e9616d165d40ea692`，旧两版在其`captions-5s-v3`。v6完整重渲beauty，v7仅修字幕名单的38项差分支持其beauty复用；这一例外不用于Clean，新版300帧均重渲。被拒绝v4袖穿模帧未复用，旧`captions-5s-v2`因后台字幕盖伊科尔退回。raw几何交线仍保留，物理仅认证4139–4441；新材质保几何／全部Actions继承原有界证据，没有新增物理或零交叉认证。旧过程保留在[婚礼基线记录](IKHOR_BOLD_WEDDING_PRODUCTION.md)，下列来源署名与许可边界不变。

## 实际采用来源

| 内容 | 署名与来源 |
| --- | --- |
| 原曲／演唱 | HIMEHINA《フランケンシュタインの怪物》；[官方MV](https://www.youtube.com/watch?v=J66gqneY518)、[官方素材入口](https://larainc.link/Franken) |
| 词曲／编曲 | 作词Gohgo；作曲Fty & Gohgo；编曲Fty，沿用用户提供的官方MV简介署名 |
| 本地BGM | 固定`D:\codex\output\Franken-Duet-Full-Audio-v1\HIMEHINA - フランケンシュタインの怪物.flac`，用户提供NCM后提取原生FLAC，96kHz／24bit／双声道；使用原唱，不换回历史伴奏。完成MP4使用AAC 48kHz双声道并实际解码核对，不能称最终MP4音轨为无损FLAC |
| 双人动作 | 官方Full HimeTanaka／Full HinaSuzuki配布，入口同上；本轮阿克西妮娅使用Hime，伊科尔使用Hina。完整动作与Morph保留，局部物理由本项目重新模拟和烘焙，不杜撰未核动作制作者名单 |
| 相机 | とっとこ；[BowlRoll 359108](https://bowlroll.net/file/359108)，173cm版；允许改造、禁止再配布。继承现有轨迹、焦距及DOF，本轮完整保留，不冒称新原创全曲相机 |
| 阿克西妮娅模型 | 版权miHoYo；模型编辑神秘会员日；模型委托徐九星，以随包`RM.txt`为准。沿用既有模型，不把文件夹账号写法替代正式署名 |
| 伊科尔模型编辑与原配布 | 版权miHoYo；模型编辑神秘会员日；[作者配布页《伊科尔【模型配布】》](https://www.aplaybox.com/details/model/L6PalbSZMmTW)，发布账号神秘会员卡、UID411902800，审核时间2026-08-23 00:39:31 |
| 伊科尔本机输入 | 实际二进制来自[Phoshco/gi固定提交目录](https://github.com/Phoshco/gi/tree/87f103389bb8cdfd4cc3a6e1ca9909a394744458/chars/Ikhor)，commit`87f103389bb8cdfd4cc3a6e1ca9909a394744458`；这是社区镜像，不称官方配布或已授权镜像。作者再分发许可及与原作者包逐字节等价尚未证明 |
| 礼堂 | 版权／来源miHoYo；改造paierer；[猪猪指定的赫斯珀利德斯之馆-礼堂](https://www.aplaybox.com/details/model/uRHK15qUygJZ)。本轮保留该场景，不以新光弧替换礼堂 |
| 场景原Ray材质 | Rui_cg／三金络合物／paierer，依据随包readme及本地fxsub；本项目做Blender适配，未运行Ray／MME，也未将其整套渲染器移植 |
| 继承着色资料／组件 | festivities的[Blender-miHoYo-Shaders](https://github.com/festivities/Blender-miHoYo-Shaders)，历史读取v3.4、记录GPL-3.0；下载预设署名“着色器：三一七片的谎言”。实际兼容与采用边界见[原神角色与预设记录](GENSHIN_CHARACTER_AND_PRESETS.md)，保留对应源码／许可证来源，不把第三方组件改署为本项目原创；不称伊科尔已获得原游戏脸部SDF |
| MMD材质与制作工具 | Blender 5.2.2 LTS、MMD Tools 4.5.14、FFmpeg；MMDShaderDev Color／Alpha接口源自[MMD Tools](https://github.com/MMD-Blender/blender_mmd_tools)，本项目在其现有语义上做材质、描边、物理、灯光与输出适配 |
| 外部技术阅读 | Nilo公开教学Shader、Ray-MMD资料、Filament文档提供部分分层原则，阅读与本机移植边界见[实读](EXTERNAL_MMD_TECHNIQUES_2026_11_13.md)及[前版移植](REFERENCE_TECHNIQUE_TRANSFER.md)；未把示例引擎、BRDF或源码整体移植 |
| 视觉参考与本轮制作 | 观海子为首要人物／舞台质量参考，保留Gosari542；未取得其原始Shader、灯光或后期工程。本项目新增婚礼双弧、光点、受控HDR亮边与美术体积光束，不冒称恢复作者实现或达到同等质量 |

本项目在原动作与模型上新增受限局部修袖：仅8个原袖骨的局部物理／软限幅，以及左袖原573个权重顶点范围内的单一corrective shape；Basis、原Morph、UV、权重和原PMX保留，所有手骨动作不变。此加工说明不改变模型、动作、音乐或相机的原作者署名与许可，也不把社区镜像未知的再分发授权变为明确授权。

后续人物修订参考猪猪提供的两份本地竖屏MP4，第一份为伊科尔、第二份为用户称“沃雅妮莎”的女性角色；第二份正式角色名与原作者身份未独立核定。两份各实际观察四张清晰渲染抽帧，另将分享卡／尾标排除出材质判断；没有取得作者Shader或工程，也没有完整连续观看。第一份在线原页为神秘会员日[《哪来这么帅的小王子》](https://www.bilibili.com/video/BV1UauH6AEw8/)，实际署名与本地观察范围见[男参考账本](research/IKHOR_PRINCE_REFERENCE_2026_11_14.json)及[女参考账本](research/FEMALE_CLEAN_NPR_REFERENCE_2026_11_14.json)。参考视频和私人抽帧不作为本项目素材再配布，也不放入Atlas。

## 伊科尔原页、随包说明与版本边界

原作者页需要正常登录、Lv2、关注作者、点赞、收藏，并有角色知识密码。此次追源只读公开页，没有代替猪猪进行互动、猜密码或调用下载接口；未绕等级。该页标注MMD，但原作者压缩包未取得，不能仅凭同署名把本机社区镜像认定为同版本原包。

本机下载清单为`D:\codex\output\MMD-Ikhor-Model-v1\download-manifest.json`；PMX位于`source\Ikhor\Ikhor.pmx`，SHA256为`ebba744cee847c16cfe5be037e7464d4f701c8edb2f5033e7de5730bd6654a52`。其`RM.txt`署名神秘会员日／miHoYo，允许改造、优化骨骼和刚体及重制UV，二次配布须联系编辑；原作者页许可选项则为禁商用、禁二配、允许修改、须完整信息及禁其他用途。两处规则不构成已知镜像获作者许可的证据，不把未知再分发授权写成明确授权。

简介与本机RM另有成人／极端宗教／血腥恐怖猎奇／人身攻击／恶搞抹黑等内容限制，禁止米提亚及潘塔罗涅右向／右位CP，并列黑名单与人品相关条件。具体适用以原说明和作者解释为准，不自行扩写成所有CP通用规则。来源账本见[伊科尔追源](research/GRAY_EYED_PRIMORDIAL_MODEL_2026_11_14.json)。

本轮缺失的改版脸图`y1.png`未恢复，使用同一社区包已有的原角色FaceDiffuse显式回退。原作者图与社区输入的来源关系、Blender具体用途没有额外个别授权证据。模型仍按本机私人制作资料处理；没有公开上传或再次配布模型包。

## 未采用与公开展示边界

大型[《原初之人【模型配布】》](https://www.aplaybox.com/details/model/5eSouS8HksfA)为猪猪未来第二场景的巨像线索，同账号神秘会员卡、编辑神秘会员日／版权miHoYo。当前仅核原页及私人预览，模型未下载、未进本工程，不能列为本片已使用背景。见[巨像账本](research/PRIMORDIAL_ONE_BACKGROUND_MODEL_2026_11_14.json)。

空及其观海改造模型不再作为本轮人物；保留[前版双人署名](CREDITS_FRANKEN_DUET.md)的历史记录，不把旧人物或旧伴奏自动写入新片简介。用户禁止Blender成片的Aiko宮殿未采用。

本地blend供猪猪本机继续制作，不等于允许随工程公开上传第三方模型、贴图、相机或下载预设。GPL着色组件与模型／音乐各自保留来源和许可边界，不混为同一授权。仓库只保存原创说明、脚本、参数及来源账本；不提交第三方完整教程字幕、模型或预设原件。Atlas只使用有权展示的本工程自产预览，原作者封面／私人研究图不放入Atlas。
