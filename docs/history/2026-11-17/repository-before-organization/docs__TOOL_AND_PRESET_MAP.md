# 工具、预设与知识的职责地图

2026-11-17 [亮肤与发影修订](STAR_RAIL_FACE_HAIR_STUDY_2026_11_17.md)：`prepare_goo_opaque_toon_v11.py`绑定正常v5恢复不透明刘海、精简色带与脸部遮罩；`bake_goo_face_hair_shadows.py`生成双人300帧UV阴影，`finalize_goo_toon_shadow_master.py`保存v13相对路径。v13整段暴露阴影池报满，v14/v15探明容量上限并调整窗影精度，`raise_goo_toon_shadow_budget.py`最终保存v16，原生全局影精度.75、面部序列仍512²。`verify_goo_eye_hair_stage.py --iteration production-v16 --render-controls`核原动作、眼外几何、600图哈希及实际渲染UV／阴影AOV，追加透明因子必须为0。视频入口默认production-v16／quick-5s-v16，并要求高峰预检无报满；旧beauty缓存不复用；打包器须等实际编码结束且长日志无报满。研究／诊断脚本不是对任意工程重复叠加的通用安装器。

2026-11-16 [眼／发／舞台整合](JELLY_EYE_HAIR_STAGE_IMPLEMENTATION.md)：`prepare_goo_eye_hair_stage.py`只接受固定大窗v3 SHA，另存新版本；果冻眼代码仅从私人临时目录读取，不安装偏好。`verify_goo_eye_hair_stage.py`独立重开原生GN、核十时点眼外顶点与头部跟随，近景诊断必须临时解除相机标记。`run_goo_eye_hair_stage_preview.py`启动完整新渲染；父启动器中断后，`complete_goo_eye_hair_stage_preview.py`仅等现有子进程完成再编码，不能重复启动3D渲染。实际PID记在缓存根render-process.json；停止启动器不等于停止其渲染子进程。

2026-11-16 [字幕样式与衣发阴影诊断](HAIR_SHADOW_TOPLIGHT_AND_BORDERLESS_CAPTIONS.md)：猪猪后续要求保留黑边框和投影，`make_portrait_quick_preview.py`默认已恢复原蓝金有边框字幕预设；no-border预设仅留历史对照。`--reuse-cache --profile ...`只重合成字幕，核同一保存工程SHA与缓存帧段，不运行3D渲染。`diagnose_goo_hair_shadow_toplight.py`只渲4290四项控制，不保存生产工程。

2026-11-16 大窗修订入口：[宽幅日光与强衣发轮廓](GOO_BROAD_WINDOW_AND_STRONG_RIM.md)。`prepare_goo_window_wrap.py`绑定Tyndall v7固定SHA；`fix_goo_window_shadow_pool.py`从本轮v1修正阴影预算至最终production-v3。`run_goo_window_wrap_preview.py`重开该最终工程，拒绝覆盖quick-5s-v3；`verify_goo_window_wrap.py`核保存工程，`package_goo_window_wrap.py`在实际编码完成后回写catalog／runtime／项目入口，并核渲染日志无阴影池报满。`--record-revision`只记录用户反馈。

2026-11-16 Goo 后续入口：[白蓝轮廓与窗向体积](GOO_TYNDALL_RIM_PRODUCTION.md)。`run_goo_tyndall_rim_preview.py`从固定 Tyndall production-v7 重开输出原生1080p30五秒，复用既有字幕／原唱编码器，旧输出目录存在即拒绝；不恢复全曲。`verify_goo_tyndall_master.py`只检查独立保存工程，不解码视频。`package_goo_tyndall_rim.py`须等实际编码与保存工程复核完成才运行，会更新catalog／runtime／project入口；不是旧Goo任意版本的通用打包器。`prepare_goo_tyndall_rim.py`至`frame_goo_window_shafts.py`为固定SHA链的本轮一次性制作与失败诊断记录，不在最终工程重复叠加。

2026-11-14补充Clean完整交付及其制作入口。当前最新为Clean production-v2／captions-5s两版完整五秒，婚礼production-v7／captions-5s-v3保留输入历史。保留历史路径，通过入口和输入契约整理，不把大量实验脚本批量搬家。整理前逐文件清单见[仓库审计](REPOSITORY_REVIEW_2026_11.md)及其JSON；脚本数量不是成熟技术数量。

## 先选择正确的工具类别

| 类别 | 已有入口示例 | 输入与副作用 |
| --- | --- | --- |
| 环境与审计 | `blender_detect.py`、`blender_inventory.py`、`*_probe.py` | 先读源码参数；通常输出报告，一些原生探针会临时改场景并渲诊断；独立进程，不保存用户偏好 |
| 素材导入 | `mmd_first_scene.py`、`mmd_camera_check.py` | PMX+原生VMD，比例和根对象选择正确；导入草稿不代表物理／风格完成 |
| 物理与整合 | `mmd_duet_physics.py`、`mmd_physics_bake.py`、`mmd_duet_finish.py` | 绑定特定源工程、骨名和动作时间；只能对对应未构建基线运行，不能给已烘焙最新工程再Build |
| 人物迁移 | `genshin_material_adapt.py`、`aether_look_revision.py`、`prepare_graphic_self_shadows.py` | 依赖当前模型、UV、辅助对象、节点名称和版本标记；一次性迁移，不是任意PMX通用材质转换器 |
| 场景迁移 | `hesperides_reference_rebuild.py`、`prepare_*lighting*`、`prepare_*wedding*` | 场景专用构建可能重置灯光／相机或只接受原始对象数；先读断言，不能任意在双人工程运行 |
| 原生渲染 | `render_duet_chunk.py`、`render_duet_sample.py`、`render_duet_full.py` | 需要已烘焙、固定色彩和输出路由的便携主工程；全曲工具仅在范围明确时运行 |
| 字幕与编码 | `composite_duet_official_captions.py`、`encode_review_cache.py`、`mux_production_audio.py` | 原生PNG16／覆盖率、官方字视频和cue、指定FLAC；需要全新输出目录并实际验证色彩 |
| 实际验证 | `verify_caption_master.py`、`verify_video.py`、`verify_audio_blender.py`、`verify_review_color.py`、`verify_render_seams.py` | 检查技术事实，不给美术相似度或用户认可打自动分数；人工覆盖范围另记 |
| 参考学习 | `video_reference_frames.py`、`study_reference_sequences.py`、`transcribe_tutorial.py`、`extract_tutorial_overlays.py` | 指定合法可读本地媒体；视频不是VMD，转写／OCR不是已核对教程内容 |
| 历史归档器 | `package_*`、`finish_grounded_review.py` | 绑定版本路径，部分复制许可、生成配方并重写catalog；不是通用发布命令，不应重跑后覆盖现行用户评价 |
| 知识与站点 | `audit_knowledge.py`、`build_gallery.py`、`verify_gallery.py` | 审计状态与链接、构建离线内容；历史浏览器QA不自动证明新构建已测，连接不可用时明确降级覆盖范围 |

表格是职责索引，具体命令和输入断言以脚本及对应实验文档为准，不代表示例全部可在当前最新工程直接调用。不同脚本处理fps、范围、相机与缓存的方式不同。

## 预设不是一个平面目录

- `projects`：角色、动作、场景、指定音乐与时间；先选项目。
- `quality`：绑定材质映射与源工程的技术实验；写清模型依赖与已测范围。
- `styles/render`：人物颜色／分色／高光／线条方向；不是作者原始Shader。
- `styles/post`：调色、图形、光点等后期；不改变物理和原生受光事实。
- `styles/packages`：风格×变体×画幅，引用render／post／字幕布局；横竖分别设计。
- `stages`：场景、主次光、局部体积和接收区域；人物与场景可分开控制。
- `typography`：源文字视频、时间映射、cue、前后层、调色与样式。
- `recipes`：已经做过整合的工程配方，保存具体版本、输入和限制；组件各自通过不等于任意组合通过。

原有参数保持路径，新人物层参数与整合配方另行版本化，不生成“游戏级万能预设”。新流程关卡和现行状态属于catalog而非render参数。

## 当前Clean完整交付与制作入口

当前完整工程为`D:/codex/output/MMD-Clean-Game-Characters-v1/production-v2/Franken_Duet_Clean_Game.blend`，SHA256为`0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4`；同根`captions-5s`下的`Franken_Duet_5s_CleanGame_Wedding_REVIEW.mp4`与`Franken_Duet_5s_CleanGame_NoCaptions.mp4`均已完成。材质v1静态321项与去弧v2增量26项、新三轴72帧技术通过；4140–4439的beauty／actor300全部新渲染，两版全解码／音轨／色彩／各自接缝、1200个双人内部覆盖ROI及原唱FLAC独立PCM比对通过。实际人工两版各12时点、32帧边界连续图和7张原生腕部关键帧（另有早期4140／4290）均有范围记录。具体见[Clean制作记录](CLEAN_GAME_CHARACTER_REFINEMENT.md)，参考差距／非零接触及美术未认可状态保留。

- [prepare_clean_game_duet.py](../scripts/prepare_clean_game_duet.py)只接受已完成婚礼v7固定SHA，分别调用[clean_aksiniya_materials.py](../scripts/clean_aksiniya_materials.py)与[clean_ikhor_materials.py](../scripts/clean_ikhor_materials.py)，新目录另存Clean材质v1；绑定[女参数](../presets/quality/aksiniya-clean-game-v1.json)与[男参数](../presets/quality/ikhor-clean-game-v1.json)，男当前`parameter_iteration=2`。不用于任意当前工程，不重复叠加。
- 两个材质模块各有palette／response_ramp／highlight_metal／rim独立旁路；保原MMD Color／Alpha、sphere、原图及几何／Actions。鼻区同图SDF邻采样只适用于阿克西妮娅真实含SDF的`颜`，不能把它套到伊科尔或`颜+`；白布许可是原HSV与金青排除的美术选择，不称游戏控制图。
- [remove_wedding_arcs.py](../scripts/remove_wedding_arcs.py)只接受固定Clean v1 SHA，新目录另存v2，只改两条已知弧的render／viewport四个可见性值；原曲线保留，其他舞台／灯／probe不重烘。
- [verify_clean_game_duet.py](../scripts/verify_clean_game_duet.py)独立只读重开，材质模式严格保留全部网格／UV／权重／shape／rig与11个完整Actions／插值柄、合成／Crypto，并确定性重放SHA绑定的新模块；`--arcs-hidden`为明确去弧增量模式，绑定原321项报告及完整静态摘要。它不渲染、不保存工程，不能由静态通过宣称像素旁路等价或新动态完全稳定。
- [render_clean_game_controls.py](../scripts/render_clean_game_controls.py)在固定v7未保存副本中做同4290控制，1280×720、48 samples，临时关闭DOF／MB并静音继承输出；不是正式beauty。[render_shader_diagnostics.py](../scripts/render_shader_diagnostics.py)与[verify_character_diagnostics.py](../scripts/verify_character_diagnostics.py)用于新候选三轴中性诊断与全解码，原始诊断／实际抽样边界另记。
- [verify_clean_caption_coverage.py](../scripts/verify_clean_caption_coverage.py)只接受固定Clean v2与其321／26报告，沿严格不变的相机／姿态继承v7已标定逐人头／身ROI，在新actor PNG上核覆盖率；不重开Blender，不修改缓存。它检查遗漏人物，不能替代透明轮廓每个像素或最终字幕合成图审。
- [package_clean_game_duet.py](../scripts/package_clean_game_duet.py)只登记本次固定v2与完整新300帧／两版视频，核SHA、静态／动态／音视频／字幕报告及实际人工范围，再复制guide／credits／原创来源账本／许可并更新delivery、catalog及配方；`--dry-run`完全只读。不能把历史基线、已有文件或无实际人工证据的报告当新交付，也不把技术通过写成用户美术批准。

## 前版伊科尔婚礼基线（历史输入）

基线为`D:/codex/output/MMD-Aksiniya-Ikhor-Wedding-v1/production-v7/Franken_Aksiniya_Ikhor_Bold_Wedding.blend`，两版视频在同根`captions-5s-v3`。人物阿克西妮娅＋伊科尔，原帧4140–4439、1080p60、五秒；制作与署名见[婚礼制作记录](IKHOR_BOLD_WEDDING_PRODUCTION.md)、[本轮署名](CREDITS_AKSINIYA_IKHOR.md)。旧production-v4袖穿模、旧captions-v2后台字幕盖伊科尔均已退回。

- [prepare_ikhor_motion.py](../scripts/prepare_ikhor_motion.py)按独立PMX＋完整Hina原生VMD导入、顺序预滚／模拟／视觉烘焙并重定时，产物需独立重开；[integrate_ikhor_wedding.py](../scripts/integrate_ikhor_wedding.py)仅接受固定Bold Wedding v2与已审计portable角色，不在已烘焙双人master重Build、不复用空的缓存。
- 袖修专用[ikhor_sleeve_repair_v1.py](../scripts/ikhor_sleeve_repair_v1.py)仅用已审计native30fps未Build输入；[apply_ikhor_sleeve_repair.py](../scripts/apply_ikhor_sleeve_repair.py)只将固定局部Action＋左单shape合入被拒绝v4的新副本，生成修袖v6。[verify_ikhor_sleeve_repair.py](../scripts/verify_ikhor_sleeve_repair.py)、[audit_ikhor_sleeve_geometry.py](../scripts/audit_ikhor_sleeve_geometry.py)与[render_ikhor_sleeve_review.py](../scripts/render_ikhor_sleeve_review.py)分别作独立差分、实际几何扫描和无模糊双腕诊断；不是任意角色的通用防穿模工具。输入指纹、失败实验与4139–4441边界见[袖口案例](IKHOR_SLEEVE_REPAIR.md)。
- [repair_duet_caption_targets.py](../scripts/repair_duet_caption_targets.py)只接受固定v6 SHA，把字幕专用Cryptomatte旧空名单换为当前实际两人，另存v7；[verify_duet_caption_targets.py](../scripts/verify_duet_caption_targets.py)确认仅名单变化与beauty依赖不变。38项差分支持的是v6→v7这次beauty复用，不能推广到Clean新材质。
- [probe_ikhor_caption_matte.py](../scripts/probe_ikhor_caption_matte.py)只读追踪覆盖率上游与现有PNG；[audit_duet_caption_coverage.py](../scripts/audit_duet_caption_coverage.py)按实际`performer_id`／骨骼投影检查每人头／身体ROI，用明确正确样本固定阈值，并对旧遗漏缓存做负例。全图mask非零不证明双人均存在，ROI也不认证全部边缘像素。
- [package_ikhor_wedding.py](../scripts/package_ikhor_wedding.py)只登记完整、SHA绑定的已验收五秒，要求独立差分、matte来源、视频／音轨／色彩／接缝和人工报告；会写delivery、复制文档／来源／许可、更新配方、项目preset及catalog。已存在delivery会拒绝重跑；不得拿它登记Clean或覆盖用户评价。

## 前版外部技术移植入口（历史输入）

历史交付为`D:\codex\output\MMD-Guanhai-Transfer-v1\production-v3\Franken_Duet_Reference_Transfer.blend`，技术说明见[外部技术移植](REFERENCE_TECHNIQUE_TRANSFER.md)，参数为`presets/quality/duet-guanhai-transfer-v1.json`。该版仍含空，保留原帧4140–4439、1080p60五秒的技术与美术记录，不当作当前人物或最新视频。

- `prepare_reference_transfer.py`仅接受CharacterLayers production-v2的指定SHA256指纹及版本，写入全新目录；不能对其production-v3或当前婚礼／Clean工程重复运行，也不能先重跑Grounded迁移器。
- `transfer_material_response.py`是材质适配模块，处理已有发带许可／受光门控及空的既有布料光泽输入；保留原Color／Alpha和金属闭包，不是任意PMX的通用转换器，也不新增角色专属控制图。
- `verify_reference_transfer.py`在独立进程只读重开源与新工程，核查动作、相机、贴图、节点及控制范围；该历史版本2488项核查通过不等于美术认证。
- `render_reference_transfer_controls.py`在未保存副本渲染完整状态与六种消融，先静音继承File Output；开关不是纯物理render pass，不保存对照状态回工程。
- `package_reference_transfer.py`是本版本登记器，依赖交付报告和实际缓存，写交付索引、配方及catalog现行状态；不是通用发布命令，不应重跑覆盖用户评价。三轴测试与视频验证继续使用已有独立诊断工具，原始证据和人工抽样范围见交付`delivery.json`。

## 前版人物层入口（历史输入）

`prepare_character_layers.py` 仅接受 Grounded production-v3，写新目录并核对九时点动作相机；不是对任意当前工程重复运行的材质按钮。`render_shader_diagnostics.py --neutral` 输出无舞台／后期三轴测试，`verify_character_diagnostics.py`全解码并导出脸条图；`render_character_layer_controls.py`只在未保存副本做同帧开关。`verify_character_layer_master.py`独立重开源与新工程核查节点、透明／PBR、贴图和动作相机。

`validate_chest_secondary_motion.py`只审计原PMX绑定和对应烘焙动作，不添加solver或声称新物理成功。`finish_grounded_review.py`保留旧默认，并支持显式 `--native-sample`、`--caption-dir`、`--review-name` 复用限定300帧后期流程；它不负责更新catalog。`package_character_layers_review.py`绑定前版production-v2及其人工报告，具有登记历史条目和回写现行审片的副作用，不对其他新版本重跑。细则见[人物分层](CHARACTER_LAYER_REFINEMENT.md)。

## 暗场人物重新布光静帧

`prepare_portrait_relight.py`只接受Clean v2固定SHA，分别调用`portrait_key_fill.py`、`portrait_rim_ink.py`与`portrait_fur_control.py`，新目录输出静帧，可保存独立工程。不可在新工程重复安装。`verify_portrait_relight.py`独立重开核完整动作／几何及明确材质许可；`render_saved_portrait.py`仅直接重渲保存候选，不重建Shader。`package_portrait_relight.py`绑定本轮真实产物／QA，登记latest_still与Atlas并保留latest_review视频；不作通用发布器。范围、失败定位和参数见[实现指南](PORTRAIT_RELIGHT_IMPLEMENTATION.md)。

## 调用前的最小契约

`render_portrait_light_controls.py`绑定Clean production-v2指定SHA，只渲4290三种同帧静态消融，不保存blend或更新catalog。加载现有偏好使MMD注册后核相机driver及61.73465mm焦距；每图重新开源，静音File Output，统一关闭DOF／MB，只隐藏两散射盒及修改限定加法HDR rim源，不改Reference SCREEN、face／skin或六发光锥。旧错误factory相机图已判废；正式图与输入协议见[人像布光研究](PORTRAIT_LIGHTING_AND_SHADOW_STUDY.md)，不可直接重跑现有输出目录。

输入工程和源素材存在且版本正确；新输出目录与临时目录明确；确认是否会改相机、灯、材质、偏好或catalog；诊断静音所有继承File Output；先对最小样本验证，后独立重开。脚本有强断言时先理解为什么，不删断言强行套另一版本。

**历史打包回写保护：**现行美术状态来自 `catalog/current_state.json`。网站构建时同步最新条目的用户反馈，避免旧package脚本把“需改进”回写成“待评价”。它只修正展示事实，不修改历史delivery报告。新工程被正式选择时同步更新现行状态，不从文件名里的final／latest自动决定。

## 后续允许的结构演进

先统一输入契约和证据格式，再将重复的安全行为提取公共函数；为有实质风险的迁移建立回归。无需为文案或低风险可逆改动堆测试。清理历史实现时先查引用和真实调用，保留兼容入口与失败记录；本轮没有删除、移动或重命名旧脚本／预设／素材。
