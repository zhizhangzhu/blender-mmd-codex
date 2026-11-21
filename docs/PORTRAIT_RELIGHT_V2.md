# 人像重新打光v2：明亮脸部与蓝灰、桃粉礼堂

2026-11-15。猪猪否定上一版大面积半脸紫影，要求更接近paierer参考中明亮的人物与脸。本轮据此调整了实际灯光、脸部受光和色带，继续保留指定礼堂、角色配色、婚礼主题及去蓝／金细光弧要求。观海子仍为核心方向；参考作者的确切Shader与灯组未知。

当前静帧为[production-v2／complete-4290.png](D:/codex/output/MMD-Portrait-Relight-v2/production-v2/complete-4290.png)，参数见[portrait-relight-v2.json](../presets/lighting/portrait-relight-v2.json)。主任务已实际查看：脸部较前版明亮，撤回了半脸紫暗面的方向；这项观察不等于猪猪认可或参考品质达标。

本轮实际调整：

- 主光在头空间前移，方向为right／forward／up的`[.36,.84,.40]`；伊科尔解析面形曲率从`1.2`降至`.55`。启用强度`.24`的定向脸补光，只抬解析主光暗侧，之后仍经过原综合受光和AO；肤色色带减少紫色。阿克西妮娅保留原SDF及局部鼻修，眼、嘴、Color／Alpha语义不替换。
- 发与衣物亮边转为粉白、桃暖的双侧柔亮过渡，继续与深色描边分开控制；没有恢复蓝／金细光弧或增加雾来制造亮度。
- 关闭v1的舞台中间调压光。配置中原`.6`参数保留，但`stage_midtones.enabled=false`，实际不再执行该后期压暗。
- 增加三盏真实建筑Area灯：桃粉墙面灯位于`(-7,18,9)`朝向`(-6,32,9)`、`700W`；蓝灰墙面灯位于`(7,18,9)`朝向`(6,32,9)`、`650W`；暖祭坛灯位于`(0,22,12)`朝向`(0,36,7)`、`600W`。同时恢复礼堂既有灯组的局部亮度与冷暖关系，使建筑获得实际受光。

第一次建筑灯使用`12000／10000／9500W`造成过曝，已弃用`D:/codex/output/MMD-Portrait-Relight-v2/production-v1`。当前采用上列低功率参数的`production-v2`，两者不能混称为最终版本。

实现入口、原综合Diffuse并非纯投影的边界，以及脸形代理、rim、毛领和物理镜面分工，沿用[本轮实现指南](PORTRAIT_RELIGHT_IMPLEMENTATION.md)。伊科尔解析面形仍是原创受光代理，不是SDF；定向补光也没有加入最终脸色恒亮下限。

本记录编写时，单版1080p30五秒快样片正在渲染；按本次快速审片要求，不做输出后QA。因此不在这里登记视频已完成、完整解码／音轨／字幕／接缝通过，也不把前版静帧或旧动态检查移作本版证据。新灯光、脸补光与较宽亮边的动态稳定性、交叠表现和最终美术评价仍未获认证，猪猪尚未认可v2。

## Quick preview produced

`D:/codex/output/MMD-Portrait-Relight-v2/quick-5s-v1/Franken_Duet_5s_PortraitRelightV2_SUB_1080P.mp4` was produced at 1920x1080, 30fps, 5 seconds, with the existing blue/gold captions and original FLAC BGM. Post-output validation and review were skipped at the user request. The video is pending user art review.
