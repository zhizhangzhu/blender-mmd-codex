# Goo 制作入口与首次迁移

2026-11-16。猪猪明确要求迁移至 Goo，并在后续制作中优先使用 Goo；目标仍是明亮蓝天礼堂、柔和明亮人像、冷暖轮廓光、可读投影，以及原双人、动作、相机、字幕和指定原唱 FLAC。此次为五秒样片，不恢复全曲。

## 实际选择与保留范围

本地教程包中有 Goo 3.6、4.0、4.1、4.2 和 4.3.2。已解压并实际启动 4.3.2，确认为 Goo、可创建专属节点，但无法直接读取当前 5.2 文件，报 incomplete header / newer version。[Blender 官方兼容说明](https://developer.blender.org/docs/release_notes/5.0/core/)说明 5.x 底层文件格式需要至少 4.5 读取；不能通过改扩展名安全解决。

本轮选择[NaMgAl-Studio 公开发布的 Goo 5.2.1 移植版](https://github.com/NaMgAl-Studio/goo-engine-5.2.0/releases/tag/GooBlender5.2.1_2026.9.12)，构建 `0051aee03764`。这是 **DillonGoo Goo Engine 的非官方社区移植版**，不是原作者原版二进制；其部分节点/通道仍有移植边界。压缩包 SHA256：`c43ea4c16ef8eefa768379b3b0c3b8e65f0be445fa7e8d886d04aa4f4ebfc343`。

- 工具：`D:/codex/workspace/goo-engine/5.2.1-community/blender-5.2.1-git.0051aee0-windows64/blender.exe`。
- 输入：`D:/codex/output/MMD-Sunlit-Wedding-v4/production-v2/Franken_Duet_Portrait_Relight.blend`，SHA `758cc2238da87e1a8849d1e5a84e4173eb0a2861acacd1637f98265b090cdd2c`。
- 新工程：`D:/codex/output/MMD-Goo-Wedding-v1/production-v1/Franken_Duet_Goo_Wedding.blend`。
- 实际同帧图：同目录 `complete-4290.png`，1080p、24 samples、DOF，主线程已查看。
- 原 Blender 工程、用户偏好与教程压缩包均未覆盖。Goo 使用独立 CONFIG 环境变量；不能直接保存原用户偏好作为便携配置。

启动入口复测发现：若独立 USER_SCRIPTS 目录不存在，启动时会回退找到原 Blender 的旧4.1同名插件，产生 ActionFCurves / 相机1mm错误。已将验证后的四个插件复制到真实的独立 `portable/scripts/addons`，只在独立 CONFIG 保存新偏好，并实测交付启动顺序：无重复注册异常，MMD Tools 实际从 portable 目录读取，4290焦距61.734649658、11个Actions。新的后台 Goo 样片入口强制 factory-startup 后显式注册插件，避免隐式读取其他配置。原渲染任务是在创建这份新偏好前启动，未被中途改动。

Goo 与原 Blender 读入相同输入，以及保存后独立重开新 Goo master，全部动作曲线/关键点与控制柄哈希、网格坐标哈希、对象清单、贴图清单一致；4140/4218/4290/4370/4438 的全部骨骼矩阵、表情值、相机矩阵和焦距一致。记录在输出根 `migration-preservation.json`，详细私人快照在 `D:/codex/temp/goo-migration-v1`。这不是全曲动态或美术质量认证。

## 本轮实际学习与接入

[Goo 原作者说明](https://github.com/dillongoostudios/goo-engine)确认专门的 Shader 节点与 Light Groups；本轮又读了[Shader Info](https://github.com/NaMgAl-Studio/goo-engine-5.2.0/blob/main/source/blender/nodes/shader/nodes/node_shader_shader_info.cc)与[GLSL 入口](https://github.com/NaMgAl-Studio/goo-engine-5.2.0/blob/main/source/blender/gpu/shaders/material/gpu_shader_material_shader_info.glsl)。在线 main 可能晚于当前下载构建，最终以本机 RNA 和实际渲染为准。

实际新建四球遮挡测试并渲染：`studies/Goo_Native_Node_Study.blend` 与 `studies/native-shader-info-curvature.png`。

| 功能 | 证据与采用范围 |
| --- | --- |
| Shader Info / Half-lambert factor | 球体柔和明暗已渲；衣物将既有形体与原生输出混合 35%，脸部 SDF/代理保留 |
| Shader Info / Cast Shadows | 球体上方遮挡的投影已渲；替换 21 项既有 palette 的综合受光响应为有界的原生 Cast Shadows 输出，肤/脸暗部作用较轻；未认证所有场景条件下的 Cast/Self 阴影分离 |
| Light Groups | 原生 Shader Info 按两位人物各自 key 组取光；既有实际灯的默认组保留，避免改变场景原材质受光 |
| Curvature / Scene Rim | 节点可创建，但本轮球体测试为黑，尚未证明可用于当前管线；不接入成片，保留原分区方向 rim 和 PMX 反壳线 |
| Toon/Cel/Anime Line | 本机存在标准 Toon BSDF，但没有 `ShaderNodeCel` 或 `ShaderNodeAnimeLine`；不能把其他模型的回答当作 Goo 实际接口，也不把 Toon BSDF 的创建视为 EEVEE 卡渲验证 |

复用原工程已有材质与贴图、原生 Goo 节点和随附 Light Groups 实现；新代码仅做角色专用接线和启动适配，没有重写 MME 运行时。原 Principled/GGX、短程 AO、金属许可、MMD Alpha、原有 Bloom/DOF/字幕遮罩保留。角色色带设计不是 PowerShader 原版，也不是原生 Ray-MMD。窗口轮廓投影的精确还原仍未认证。

关于 Scene Rim 黑输出的后续假设：所读社区版 Shader Info 明确设置 forward/Shader-to-RGB 和 RAYCAST 标志以取得引擎资源，而原版 Curvature 声明仅设置 diffuse 标志；球体测试的 Curvature 材质没有连接 Shader Info。屏幕纹理资源路径可能是原因之一，这是代码阅读后的推断，尚未做对照验证，不能据此判断 Goo 的深度边缘整体不可用。Half-lambert factor 在本次社区版实际存在，也不能推广到所有原版 Goo 版本。

2026-11-16 后续独立实验纠正：原始线性 Scene Rim 最大值为 0.001437187，乘 500 可见；额外接 Shader Info 的控制组没有改变本组最大值。因此本组证据不支持上述资源路径猜测。放大后仍有宽广内部亮区，未成为生产细轮廓方案；详见[节点机制与 MME 增量](GOO_FEATURES_AND_MME_MECHANISMS.md)。前表黑图保留为历史观察，不再等同于数值零输出。

## 插件边界

已复制到 Goo 的独立目录，未覆盖原插件：MMD Tools 4.5.14、咖啡工具 1.9.2、Paper Anime Render Helper 2.5.0、MikuMikuRig 5.2.2。四者均实际注册成功；MMD Tools 最初缺 OpenCC，已复用随包 wheel 的纯 Python 依赖修复。MMD 相机 RNA、全部动画/表情求值与工程重开已测。

又在独立空场景实际导入原阿克西妮娅 PMX（未构建物理），复制为两个测试模型，用咖啡工具 PMX→PMX 迁移材质，确认目标材质确实链接至源材质。Paper 的描边、Toon Shadow、高光、Glow、色彩、天空盒六组添加/撤销均返回 FINISHED，无异常；这些是算子操作测试，不是全部视觉效果验收。MMR 仅注册与算子可用性核对，没有重绑定已烘焙人物。结果：输出根 `plugin-function-probe.json`。仍不能称所有插件的全部功能通过。

本轮又检索了 Blender/Goo 原生 MME 插件、`.fx` 导入与转换器，没有找到可据作者说明和本机实测确认的通用运行插件。[MMDX12](https://mmdx.codingbot.kr/en/docs/mme/)声称具备自己的 MME 兼容层，但它是独立应用，不是 Goo 插件，且作者列出了兼容分级；本轮没有安装。MME NodeEditor 为独立节点编辑器，仓库简介不能证明 Blender/Goo 可执行 MME。后续继续优先已有兼容 Blender/Goo 预设，只有剩余缺口才适配。

另按 BowlRoll 原页公开下载表单尝试获取 PowerShader/tn_PostPointLight/wDark 的三个包，原站均返回 fail，未取得包内内容，未重试绕过任何限制。因此这三者仍只有配布页核对，不能登记成已读随包许可或已移植。

## 五秒入口与状态

入口：`scripts/run_goo_wedding_preview.py`，调用既有字幕/原唱编码器；150 帧、源4140–4438步2、1920×1080、30fps、16 samples、DOF、无 MB，只生成一个字幕 MP4。输出后按猪猪要求跳过检查；生产过程仍核对渲染与编码进程成功结束。

首次启动命令两次遭自动审批服务 `Bad Request`，未执行；这不是不安全判定。将固定参数明确写进入口后重新走正常审批，已通过并开始实际渲染。最终是否完成，以 `quick-5s-v1/preview-info.json` 和 `catalog/current_state.json` 的 `latest_quick_preview` 为准，不由入口文件存在推断成片完成。

本轮最终已实际完成：150帧渲染结束、字幕/指定原唱编码进程以0退出，输出 `D:/codex/output/MMD-Goo-Wedding-v1/quick-5s-v1/Franken_Duet_5s_GooWeddingV1_SUB_1080P.mp4`。1080p30、五秒、仅此一版字幕视频；按猪猪要求，没有再解码、抽看或运行输出后视频检查。当前为Goo首版审片，美术待猪猪评价，非原版PS/Ray复刻认证。
