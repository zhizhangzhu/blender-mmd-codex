# 横竖屏动态字幕研究交付

猪猪，本轮将官方文字配布、观海子参考和字幕分层方法落实为两支可播放的四秒样片。两版使用各自的相机与原生画幅文字，按段选择人物前后层，已有衣发烘焙继续使用。

交付根目录：`D:\codex\output\MMD-Advanced-Subtitle-Study-v1`。

| 文件 | 内容 |
| --- | --- |
| `portrait\portrait-typography.mp4` | 4 秒，540×960、60 fps、带伴奏 |
| `landscape\landscape-typography.mp4` | 4 秒，960×540、60 fps、带伴奏 |
| 两个目录的 `typography-source.blend` | 各自相机、人物、舞台、NPR 与 Cryptomatte 输出；字幕另由 Python 合成 |
| `layer-order-comparison.png` | 同一姿态：人物后 / 前景保护脸 / 前景允许遮挡 |
| `caption-contact-sheet.jpg` | 不同时点的实际合成帧 |
| `profile.json` | 每段字幕层级、保护区域、颜色与素材起点，可编辑 |
| `video-qa\`、`audio-qa.json`、`caption-verification.json` | 逐帧解码、实际音轨解码和合成遮罩检查 |
| `alignment-refined-frame-pairs.jpg` | 官方横竖文字的对应帧核对 |
| `references\` | 用户提供的参考视频抽帧联系表与来源元数据 |
| `guides\` | 已写回仓库的技术、素材与参考观察文档副本 |

字幕可以按内容放到人物后、放前面保护脸，或主动遮挡；主样片选择前两种，对照图展示三种。横屏相机为单独设计，竖屏继续使用表情/半身镜头。图形层级和镜头需要一起调整，不能只裁切画幅。

官方横版完整文字已有本地文件，竖版副歌文字本轮从官方配布下载。两份不是同一起点：经字形匹配和对应帧核对，Tall 起点约为 Wide 的 48.783333 秒。本次文字素材对应已校正，但伴奏依然按估计时间截取，尚未精确卡点；使用的是官方伴奏，没有人声。

视频两版均完整解码 240 帧，音轨非静音、48 kHz 双声道。合成保护区域编码前检查通过，前景文字能实际覆盖衣物；28 项单元测试通过。详细证据、命令和教程来源见仓库 `docs\ADVANCED_MMD_SUBTITLES.md`，交付副本在 `guides` 中。

这些是本轮新增能力的四秒研究样片，预览分辨率；尚未重制二十秒新成片，也没有把与 Gosari542 / 观海子的整体材质质量差距宣称为已解决。原二十秒 v2 成片仍保存在 `D:\codex\output\Aksiniya-Frankenstein-Final-v2`。

继续编辑：代码位于 `D:\codex\workspace\blender-mmd-codex`。单改字幕时可以复用 `D:\codex\temp\mmd-caption-portrait-v001` / `mmd-caption-landscape-v001` 的 PNG 缓存；重新渲染应使用新目录。打开 Blend 不会自动执行后续字幕合成，文件输出节点仍指向本机缓存路径。原素材及用户偏好未覆盖，未公开发布或推送。
