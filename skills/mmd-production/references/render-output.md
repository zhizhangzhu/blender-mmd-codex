# 预览、正式渲染与视频输出

## 先确认工作量

读取活动相机、分辨率、实际帧率 `fps / fps_base`、起止帧、渲染引擎、采样和设备。时长按 `(end - start + 1) / fps` 计算。先渲染代表帧与有明显动作的短片，再用真实耗时估算完整输出，不把软件能启动理解为足以快速渲染。

Blender 4.5 的 Eevee 引擎标识是 `BLENDER_EEVEE_NEXT`。Cycles 的 GPU 支持和可用显存须从当前机器实际查询；只有验证设备可用后再选 GPU。预览可以降低分辨率与采样，最终质量根据用户目标和预览决定，不固定某种审美或统一采样值。

## 视觉检查

在真正的活动相机下看构图、景深、遮挡和背景。选取动作变化大、双手接触身体、脚落地、头发/裙摆碰撞、相机切换的时间段。静帧正常不能证明运动连续；有播放工具时实际播放，没有时报告检查了哪些帧与技术信息。

优先修正具体可见问题，保存修改前后检查点。连续尝试没有改善时停止同类参数盲调，保留证据并换诊断方向。

## 渲染帧序列

正式渲染优先输出 PNG 或适合后期的 EXR 序列，以便中断后接续及重新编码。相对输出路径 `//` 以当前 `.blend` 所在目录为基准，先保存作品。确认输出目录属于当前作品并避免覆盖其他帧序列。

典型 Blender Python 设置（路径和范围由当前作品确定）：

```python
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.fps = 30
scene.render.fps_base = 1.0
scene.frame_start, scene.frame_end = start_frame, end_frame
scene.render.resolution_x, scene.render.resolution_y = width, height
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = frames_prefix
bpy.ops.wm.save_as_mainfile(filepath=checkpoint_path)
```

调用渲染前确认预计耗时；超过 MCP 单次响应时间的完整渲染可在保存检查点后用 Blender 后台子进程执行，并记录日志、退出码和帧进度。正在被 UI 编辑的文件不要同时由后台进程覆盖。先确认后台环境也能加载该作品需要的扩展、贴图及物理缓存。

## 合成视频与声音

可使用 Blender Video Sequencer 或已有 FFmpeg，把帧序列和有权使用的音频合成为 MP4/H.264/AAC。Blender VSE 的 Python 集合名在不同版本有变化，4.5 先查看 `sequence_editor.strips`，不要直接复制旧的 `sequences` 示例。使用独立的合成 `.blend` 或场景，保持渲染作品可继续编辑。

对已完成色彩显示变换的 PNG 序列，合成场景和解码验证场景应使用与输入相符的色彩管理，例如 sRGB 序列配合 Standard 显示变换；不要在新场景中再次用默认 AgX 处理已经显示变换的画面，否则颜色可能明显变暗、变灰。对线性 EXR 则按其线性色彩流程处理，不能套用 PNG 的做法。编码后比较同一帧，区分正常有损压缩和意外的二次色彩变换。

输出时保持输入帧率、音频起点、人物动作和相机一致。根据用户要求处理音乐前奏、尾帧和静音，不未经请求改变音高、速度或裁剪长度。人物动作和镜头按 30 fps 导入后，若要输出 60 fps，先明确使用相同时间采样的重定时策略，再用短片验证；不能只改 fps 让视频加速。

验证最终文件：渲染/编码进程正常结束，期望帧数完整，视频实际可解码；检查宽高、帧率、时长、音轨和音画同步。交付可编辑 `.blend`、最终视频与资源署名记录。透明素材使用支持 Alpha 的图片序列或明确支持透明的编码，普通 H.264 MP4 不保留透明通道。

来源：[Blender 4.5 渲染手册](https://docs.blender.org/manual/en/4.5/render/index.html)、[动画帧序列工作流](https://docs.blender.org/manual/en/latest/render/output/animation.html)、[Blender 4.5 输出设置](https://docs.blender.org/manual/en/4.5/render/output/properties/output.html)。打开最新手册时核对其版本，新增行为不直接套回 4.5。
