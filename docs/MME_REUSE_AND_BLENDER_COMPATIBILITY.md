# MME 复用与本机 Blender 兼容边界

2026-11-17更新：猪猪提出评估原生MMD／MME制作、Goo补充。下一步优先建立[原生效果基准](MME_NATIVE_LEARNING_LAB.md)，工具分工及迁移条件见[方案](MMD_MME_GOO_WORKFLOW.md)。下列11月16日预设复用顺序是当时Blender任务的选择，不覆盖本轮原生路线试验；仍不表示已经安装或运行原生MME。

2026-11-16。猪猪要求优先使用现成预设，在其基础上调光与材质，避免重复实现；本轮只读核查，没有替换生产材质、安装插件或启动新视频渲染。

## 本机事实

独立后台 Blender 5.2.2 读取当前保存的用户偏好，报告：`D:/codex/temp/blender-addon-inventory-2026-11-16-mme.json`。这不是用户当前 GUI 进程盘点，也不覆盖其他 Blender 版本。

| 已启用插件 | 版本 | 已核对的职责 |
| --- | --- | --- |
| MMD Tools | 4.5.14 | PMX/PMD、VMD、VPD；MMD 材质和贴图数据 |
| MikuMikuRig | 5.2.2 | 绑定与动画辅助 |
| mmd_kafei_tools | 1.9.2 | Blender 中已有模型间的材质等预设迁移；PMX→ABC / PMX→PMX 配对 |
| Paper Anime Render Helper | 2.5.0 | Blender 原生卡渲、描边、高光、Glow、天空与环境图 |

旧 mmd_tools 4.1.0 在磁盘但未启用。以上四套源码未检索到 PowerShader、tn_PostPointLight、HLSL、`.emm/.emd` 或 `.fx` 导入过滤器。结合当前导入源码与作者说明，未发现原生 MME 执行器或通用 MME→Blender 转换器，不能把“预设迁移”解释成 `.fx` 着色器转换。Paper Helper 明确使用 Eevee/Blender 节点，并对复杂已有材质有跳过限制。

## 已核对的配布入口

2026-11-16 后续增量：已通过公开配布正常下载取得 PowerShader、tn_PostPointLight、wDark 等 9 个原包，并读取重点说明与源码；下列“尚未取得”是较早阶段的记录，现以[原包学习与 Goo 实作](MME_TO_GOO_LIGHTING_STUDY.md)和对应来源账本为准。tn_PostPointLight 不支持自阴影、wDark 不是光源，均已从原说明确认。

- [用户提供的 MME 推荐整理](https://www.bilibili.com/opus/844214760220131363)：实际读取第 9、10、13 项及相邻推荐；这是线索，不能代替随包许可和兼容测试。
- [角砂糖 PowerShader v3.2](https://bowlroll.net/file/195743)：原作者账号 443942、公开页及公开下载状态已核对；ZIP 与随包说明尚未取得，不宣称许可已读或在 Blender 已运行。
- [呉石 tn_PostPointLight 0.30](https://bowlroll.net/file/188141) 与 [wDark 0.51a](https://bowlroll.net/file/149977)：原作者账号 237883、文件名及公开下载状态已核对；尚未取得包内说明/源码，不宣称支持真实投影、已适配或已组合成功。
- [Ray-MMD](https://github.com/ray-cast/ray-mmd)：README 明确为 MMD / MME / HLSL / Direct3D 9 环境；MIT 许可要求保留版权与许可文本。当前 Blender 场景是参考 Ray 配置的适配，不是原生 Ray-MMD。
- [Ray 子模块声明](https://github.com/ray-cast/ray-mmd/blob/master/.gitmodules)：实际目录是 `Extension/LightBloom`、`Extension/FXAA`，指向独立仓库；不能假设下载不含子模块的主仓库 ZIP 就带齐扩展。
- [LightBloom 作者 README](https://github.com/MikuMikuShaders/LightBloom)：实际读完说明；阈值提取、屏幕宽度比例半径、各层 HSV、全局 Bloom HSV 分工明确，运行要求仍是 MMD/MME/D3D9。此前已读过，不能登记为首次掌握。
- [FXAA 作者 README](https://github.com/MikuMikuShaders/FXAA)：实际读完说明；后期抗锯齿不能完全解决时间闪烁，非灯光或投影来源。
- [MMD Tools 当前官方说明](https://github.com/MMD-Blender/blender_mmd_tools)及[当前导入源码](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/mmd_tools/operators/fileio.py)：列出模型、动作、姿态格式。[旧分支功能表](https://github.com/powroupi/blender_mmd_tools/wiki/MMD_TOOLS-LIST-OF-FEATURES-AND-BRIEF-TUTORIAL-INFORMATION-FOR-FEATURES)明确写 `.fx` 不支持；旧说明只作补充，结论同时依据本机当前源码。

## 可行的复用方式

1. **留在 Blender：直接追加现成 Blender 材质/节点组和合成预设。** 本机 `D:/BaiduNetdiskDownload/三渲二预设` 已有 `A-原神版预设.blend`、`通用脸部sdf.blend`、`几何实体化描边.blend`、`hair高光(wuwa3.0).blend`。优先按[既有实测](GENSHIN_CHARACTER_AND_PRESETS.md)复用兼容部分，不能再从零重写同功能组件。操作是 File→Append→Material/NodeTree，按说明绑定底色、控制图、头轴/光向；需要相同模型/ABC 材质迁移时用咖啡工具。追加节点不等于任意角色自动适配；现有描边不可重复叠加。
2. **保留 MME 原版行为：在 MMD/MME 运行原配布。** Blender 可以继续做模型/动作准备和后期；在原生环境用 PowerShader/Ray/灯光 MME 才能避免移植着色器。两套主渲混合、通道分配、透明、深度与投影需先小样验证，不能保证直接同时挂载就成功。没有因此擅自迁移现有生产工程。
3. **数据可部分复用，执行效果不能等同。** Toon/sphere/普通纹理可以作为图像资源使用，格式受支持的 PMX 控制器或 VMD 参数动画可读取其数据；缺少对应执行器时不会产生原 MME 的着色、后期或阴影。数值也不保证与 Blender 一一对应。

复用优先顺序：已经验证的本地 Blender 预设 → 作者提供的兼容 Blender 版本/移植版 → 原生 MMD/MME 原版小样 → 确认无可用实现后才写最小适配。不能因下载了 `.fx` 就说 Blender 效果完成。

## 当前制作约束

保持指定礼堂、双人、动作、相机与原声；目标仍是明亮蓝天礼堂、柔和人脸、分区轮廓光和可读的真实落地投影。wDark 的压远景方向不作为当前提亮礼堂的默认处理。光晕/亮边不代替投影。

上述1080p五秒快样约定属于历史。2026-11-17起默认只看静帧，明确要求视频时才进入视频流程；不从旧预设复用说明恢复片段或全曲渲染。
