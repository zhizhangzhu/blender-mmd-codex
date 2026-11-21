# 教程学习：本地语音转写与屏幕说明 OCR

已实测于 2026-11-11，安装位置仅在临时目录，不修改 Blender 插件或系统偏好。优先尝试平台正常提供的字幕；不可用时，对可正常访问的公开媒体或用户提供的本地媒体进行研究。

## 有旁白的教程

脚本 `scripts/transcribe_tutorial.py` 使用 FFmpeg 解码 16 kHz 单声道，sherpa-onnx 2.0.1 / SenseVoice INT8 在 CPU 上离线识别。模型来自 [sherpa-onnx 官方发布](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models)。输出为分段 JSONL、TXT、SRT 和进度报告；输出目录必须全新。

```powershell
$env:PYTHONPATH = 'D:\codex\temp\mmd-asr-tools'
python scripts/transcribe_tutorial.py --input 'D:\codex\temp\Stage-Art-Wuwa-Study-v1\stage-audio.m4s' --model-dir 'D:\codex\temp\mmd-asr-models\sensevoice-study-v1\sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17' --output-dir 'D:\codex\temp\Stage-Art-Wuwa-Study-v2\asr' --ffmpeg 'D:\codex\temp\blender-mmd-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe' --threads 4
```

可用 `--start-seconds` 和 `--duration` 只研究某章节。约 20 秒切窗，靠近静音处切分；**时间是粗粒度分段，不是逐词对齐**。低音量、音乐、长停顿、英文插件名可能误识；机器完成标记只证明处理完成。学习笔记必须以原视频、画面或实际代码复核。

本次半开放夜景全音轨 7761.365 秒识别为 398 段，约 164 秒处理完成；不是完整人工字幕。后续复用无需再次下载同一模型。

## 以屏幕文字为主的教程

脚本 `scripts/extract_tutorial_overlays.py` 使用 OpenCV 与 RapidOCR，按时间采样，提取红／粉色说明文字。这是针对当前教程的颜色筛选，不是任意字幕通用识别器。

```powershell
$env:PYTHONPATH = 'D:\codex\temp\mmd-ocr-tools'
python scripts/extract_tutorial_overlays.py --video 'D:\BaiduNetdiskDownload\三渲二预设\c-鸣潮渲染#着色器Pro Max 版\教程视频#着色器Pro Max 版.mp4' --output-dir 'D:\codex\temp\Stage-Art-Wuwa-Study-v2\ocr' --period 30
```

本次 2951.382 秒视频采样 99 帧，完成约 116 秒；可定位脸／眼／头发／身体／描边章节。ASR 对此视频没有得到可靠旁白，已弃用该文字。OCR 也会识别界面快捷键、漏掉否定词或短句，必须查看原画面，不能直接生成逐字稿或参数处方。

完整自动草稿与参考画面留在临时目录用于个人学习；仓库保存原创总结、定位、工具和实际实验，不提交完整第三方教程文字、视频、预设或带签名的媒体 URL。对外只展示本工程新渲染的实验画面。
