# 衣发物理、参考风格与成片：已验证的制作方法

2026-11-13复审提示：下文单角色／旧伴奏／原创舞台／竖屏为历史实测实例，保留用于复现技术，不覆盖当前双人、指定礼堂、原声FLAC与16:9选择。现行指导见 [制作流程](PRODUCTION_WORKFLOW.md)、[人物手册](CHARACTER_NPR_PLAYBOOK.md)、[物理手册](PHYSICS_MOTION_PLAYBOOK.md)，项目状态见 `catalog/current_state.json`。

本记录基于 Blender 5.2.2 LTS、MMD Tools 4.5.14 和阿克西妮娅 PMX。目的是保留有效方法及可复现证据，不把本机问题或模型数值泛化到所有版本和角色。

## 这次制作规格

采用 Full HinaSuzuki 动作的源帧 1794–2394；制作 20 秒副歌竖屏短片，与用户给的约 18.42 秒 Gosari542 参考属于相近长度的展示形式。最终时间轴为 1–1200 帧、60 fps、1080×1920。保留银发蓝衣角色身份，靠拢参考的明亮人物、清楚的材质分区、暖色舞台、半身/大腿景别和柔化背景。

原曲与素材来源见 [CAMERA_SEARCH.md](CAMERA_SEARCH.md)，参考画面见 [GOSARI_REFERENCE.md](GOSARI_REFERENCE.md)。音轨是原调伴奏片段，依据源动作时序截取；用户已明确将人工卡点留给自己，不应宣称人声或精确卡点已完成。整曲原始 VMD 和此前导入工程保留，20 秒成片不等于已完成整首歌的美术与物理验收。

## 原生物理到便携动画

模型原有 425 个刚体：34 个跟随身体、391 个动态；有 18,712 个原生和辅助约束。按配布说明关闭膝盖与脚踝的四个 IK 约束，使用原生 FK 动作。不是对所有 MMD 动作一律关闭 IK。

先用 480 帧、4 substeps、20 iterations 验证了模拟可用；正式片段用 6 substeps、30 iterations，从源第 1674 帧开始构建与模拟，到 2394 帧结束。副歌开始前有 120 帧（4 秒）预滚，减少刚体从初始状态进入片段时的震荡。

`scripts/mmd_physics_bake.py` 的核心流程：在模拟起点组装 PMX 物理，连续烘焙内存缓存，选择有 `mmd_tools_rigid_track` 的 390 根骨骼，以 visual keying 把位置和旋转写入原身体动作的副本，再停用物理驱动。一个动态刚体未绑定可导出的骨骼，因此刚体数不等于导出骨骼数。

本机两次磁盘缓存切换崩溃的栈位于 `BKE_ptcache_toggle_disk_cache` / `ptcache_filepath`；先保存项目或补上下文也未解决。有效路径是避开该开关，使用内存缓存并导出骨骼 Action。内存缓存不会成为交付依赖；正式工程清除刚体世界、物理跟踪约束和辅助物体，保留烘焙运动。不要仅凭缓存的 `is_baked` 标志交付，也不要把这次问题写成所有 Blender 的必现缺陷。

Blender 5.2 选择姿态骨使用 **`PoseBone.select`**，而不是旧版的 `Bone.select`。本机随附 `bpy_extras/anim_utils.py` 也使用前者。先做 API 检查，避免完成长模拟后才在导出步骤失败。

实际对照：原生模拟的第 1854 帧与导出 Action 的裙摆、披肩、头发骨骼位置最大误差约 `1.3e-7` Blender 单位。正式工程去除实时物理并重新打开后，再对六个时点的八根身体/衣发骨骼作比较，共 48 组；重定时前后位置和四元数误差为零。

## 材质和灯光

本模型有基础材质、`+` 叠层、球面贴图、透明帽子/腮红等结构。逐张读取 diffuse 并新建普通材质没有等价保留这些语义；早期试样出现不正确的黑色区域，因此没有采用该转换路线，也没有将未经验证的原因归咎于 RGB 文件或 UV。

首版使用完整 `mmd_shader` 转 **Shader to RGB**，再逐通道压缩 `C/(C+0.45)`。用户复审认为质感不足；后续同姿态对照确认该映射使蓝衣、银发与配件偏灰，已从新版中撤下。保留此记录用于解释旧工程，不能再作为默认推荐。

新版保留 MMD 贴图、球面及透明输入链，直接使用节点组 **Color/Alpha** 输出，再按皮肤、眼睛、银发、蓝衣、毛领与配件分别做 NPR 明暗与少量高光。实际参数、原理、资料、复现命令和限制见 [LOOK_REFINEMENT.md](LOOK_REFINEMENT.md)。这也修正了早期「必须完整 Shader 转 RGB」的过强结论：至少本机 4.5.14 的 Color/Alpha 接口可有效复用 MMD 语义。

进一步的教程研究验证了灯位置/颜色/功率驱动 NPR、按材质限制轮廓光、原生 MMD Tools 细描边、Shader AOV 局部泛光与两种景别试验，见 [TUTORIAL_STUDY.md](TUTORIAL_STUDY.md)。这些保存在独立研究工程，尚未替换 v2 正式成片；当前分析式光照仍不等同于真实面积灯投影与 GI。

本片灯光为三盏大面积灯：主光 200 W、补光 140 W、舞台光 350 W，暖主光配轻微冷补光；Standard 色彩管理、曝光 0。EEVEE 渲染采样 48。当前相机景深 f/2、8 片光圈叶片，焦点随头部移动。不同模型比例与灯距需要重新做静帧对照，数值不能脱离场景照搬。

参考的发色与服装属于哥伦比娅；这次不改掉阿克西妮娅的银发与蓝衣。相似方向主要体现在人物明亮、材质清楚、暖色背景和构图，而非完全相同的模型、色板或光学参数。

## 舞台与镜头

舞台由 `scripts/mmd_final_scene.py` 生成，是原创程序化几何：奶油/玫瑰色棋盘地面、粉色褶帘、香槟金拱形饰线、立柱和心形装饰。无需新增第三方舞台素材，避免下载后仍缺贴图或不清楚授权。

保留水瀬ミナ原镜头作为 FOV/节奏参考，生成新的单人竖屏相机。原版双人构图不直接裁切到竖屏；正式相机跟随角色头部，以近中景为主，限制过远/过近景别，使用轻微侧向运动。角色自身转身时仍会出现侧面和背部，属于动作内容，不由镜头强行锁住脸朝向。

镜头作者允许改造、禁止改造后再配布；作者数据和本地工程都不加入 Git，也未公开发布。视频或配套说明中署名水瀬ミナ。

## 30 fps 源动作到 60 fps 视频

不能只将项目 fps 从 30 改成 60；那会让同一组关键帧的动作速度加倍。对本片，先在源时间轴完成物理和相机，再将**所有相关 Action** 中关键点与两侧柄的时间坐标变换为：

```text
output_frame = (source_frame - 1794) × 2 + 1
```

Blender 5.2 的分层 Action 从 `action.layers → strips → channelbags → fcurves` 访问。对 `co`、`handle_left`、`handle_right` 一并修改并更新曲线。60 fps 的中间姿态由动画曲线插值产生，衣发模拟基于 30 fps 求解，不应称为原始 60 Hz 动捕或 60 Hz 物理求解。

本片输出帧 1200 对应源时间 2393.5；额外烘焙的源第 2394 帧为最后一个半帧提供插值数据。源动作的其他帧仍保留在工程中，但成片播放范围只有选定片段。

## 渲染与验收脚本

| 脚本 | 实际职责 |
| --- | --- |
| `mmd_production_inspect.py` | 查看模型材质、节点、物理、IK 和版本相关 API |
| `mmd_physics_bake.py` | 原生衣发物理、预滚、visual bake 导出 Action |
| `mmd_final_scene.py` | 保留 MMD 材质的 NPR 调色、程序舞台、单人镜头、60 fps 重定时、打包贴图 |
| `mmd_look_upgrade.py` | 从首版便携工程升级为分区 Color/Alpha NPR，保留相机与物理 |
| `compare_look_frames.py` | 不调色的同姿态整体/脸部对照与 20 帧联系表 |
| `mmd_sample_pose.py` | 导出骨骼矩阵作源模拟/便携工程/重定时对照 |
| `mmd_production_qa.py` | 重新打开工程后检查依赖与代表帧，并生成 QA 报告 |
| `render_production.py` | 完整所选片段的 H.264 画面母版渲染，拒绝覆盖既有文件 |
| `assemble_render_chunks.py` | 校验独立渲染段范围连续及帧数/尺寸/fps，复制码流拼接 |
| `verify_render_seams.py` | 检查分段边界邻帧差异与联系表，辅助连续性目视验收 |
| `mux_production_audio.py` | FFmpeg 无损复制画面流，截取伴奏并编码 AAC，独立于 3D 渲染 |
| `verify_audio_blender.py` | 实际解码成片音频，检查时长、非静音、RMS 与峰值 |
| `verify_video.py` | 逐帧解码、容器音视频流检查、帧数/fps/时长/黑帧/冻结检查及联系表 |

Blender 5.2 的视频输出需要先设置 `image_settings.media_type='VIDEO'`，再选择 `file_format='FFMPEG'`。本机的相机渲染 `use_sequencer=False` 即使设置 AAC 并存在声音条带，实际生成的仍是静音 AAC。有效流程是先出画面母版，再用 FFmpeg `-c:v copy` 和原伴奏单独混流；不重新压缩画面。最终伴奏起点 59.7666667 秒、长度 20 秒，增益 0.75，为 AAC 编码留峰值余量；这不是人工卡点。实际解码检查通过：48 kHz 双声道、约 20.01 秒、RMS 约 0.195、峰值约 0.962。

仅有 `soun` 容器轨道不代表有声音，必须解码检查非零样本和 RMS。本片先发现静音轨，再发现未留余量时的 AAC 峰值溢出，均在交付前修正。不要以「FFmpeg 命令成功」或「音轨存在」替代音频验收。

正式交付应包含 MP4、可重渲 blend、署名和来源、制作参数、工程与视频 QA 报告。20 张代表帧的几何与构图检查有助于发现问题，但不保证所有细微穿模都被自动识别，仍需目视检查最终解码帧及连续运动。

## 一次资料学习与本机验证的关系

- [MMD Tools 原作者代码：模型组装](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/mmd_tools/operators/model.py)：理解 Build/Clean 和物理骨骼的职责，最终以本机 4.5.14 源码为准。
- [Blender 原作者代码：Shader to RGB](https://github.com/blender/blender/blob/main/source/blender/nodes/shader/nodes/node_shader_shader_to_rgb.cc)：明确此转换是 EEVEE 的材质路径。
- [Blender 文档：Shader to RGB](https://docs.blender.org/UATEST/manual/en/dev/render/shader_nodes/color/shader_to_rgb.html)：说明非写实着色用途和与 PBR/渲染通道的差别；实际采用与效果仍须本机渲染验证。
- [Wiggle Bones 官方扩展](https://extensions.blender.org/add-ons/wiggle-bones/)与 [Spring Bones 作者仓库](https://github.com/artellblender/springbones)：作为原生 MMD 物理不可用时的候选方案。本片最终使用原生 Bullet 物理，没有安装或宣称使用这些替代插件。

阅读和查找到资料不等于掌握或验证。以后新增方法也应同时留下输入、版本、命令、产物、目视比较和失败边界。

本轮正式输出及验收汇总见 [FINAL_DELIVERY.md](FINAL_DELIVERY.md)，署名与来源见 [CREDITS.md](CREDITS.md)。
