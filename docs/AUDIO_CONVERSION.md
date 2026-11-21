# NCM 转 FLAC / MP3 与双人全曲 BGM

2026-11-09，猪猪提供本地网易云 NCM，要求在仓库保留可复用转换脚本，并将转换后的原声 FLAC 用于后续 MMD。入口为 `scripts/ncm_convert.py`；后端使用原作者 [taurusxin/ncmdump](https://github.com/taurusxin/ncmdump)，可选转码与完整解码检查使用 FFmpeg。没有把第三方转换核心伪称为本仓库原创算法。

## 本次实际转换

| 项目 | 实测结果 |
| --- | --- |
| 源文件 | `D:\CloudMusic\VipSongsDownload\HIMEHINA - フランケンシュタインの怪物.ncm` |
| 主输出 | `D:\codex\output\Franken-Duet-Full-Audio-v1\HIMEHINA - フランケンシュタインの怪物.flac` |
| NCM 内原音频格式 | FLAC；主输出没有重新编码 |
| 时长 | **198.3158125 秒，约 3 分 18.316 秒** |
| 音频规格 | 96,000 Hz、24-bit、双声道、19,038,318 个采样/声道 |
| 标签 | ARTIST 为 HIMEHINA，TITLE / ALBUM 为 フランケンシュタインの怪物 |
| 验证 | FFmpeg 完整解码通过；声明采样数与实际解码时长一致；源 NCM SHA-256 转换前后保持不变 |
| 主 FLAC SHA-256 | `3e9c3c62f49523ec2959192dd5a4b698edddf8e78829d89b2c7952f7e1a58d52` |
| 源 NCM SHA-256 | `ccb135fd636d695664f06399b2c5f55e7ee37f32384bb4a6d9f8693eafc0ec82` |

原调伴奏 `E:\tools\franken\FrankensteinNoKaibutsu_Audio_Inst±0.wav` 实测 **198.3166667 秒，约 3 分 18.317 秒**。两者长度非常接近，但这不构成与 MV、Full VMD 或字幕已同步的证据。

原声选择来自用户提供的歌曲文件及其标签，不声称做了全曲人声识别或版权来源鉴定。用户已指定此主 FLAC 为后续制作 BGM，伴奏改为参考；无需为了得到 FLAC 从原 MV 再抽取有损音轨。

MP3 分支也实际转换并完整解码通过，位于主输出目录的 `mp3` 子目录，使用 FFmpeg `libmp3lame -q:a 2`；它是另存的有损版本，不是后续 MMD 的默认母版。MP3 支持的采样率与 FLAC 不同，转码可能自动重采样。

## 使用方法

从仓库根目录执行，转换只访问本地文件，不联网获取封面或上传音频：

```powershell
# 保留 NCM 内的原始格式，原本是 FLAC 就输出 FLAC，MP3 就输出 MP3。
python scripts/ncm_convert.py 'D:\CloudMusic\VipSongsDownload\HIMEHINA - フランケンシュタインの怪物.ncm' `
  --output-dir 'D:\codex\output\music-conversion-new'

# 明确要求 FLAC 或 MP3。使用全新输出目录，避免覆盖已转换文件。
python scripts/ncm_convert.py '<歌曲.ncm>' --format flac --output-dir 'D:\codex\output\music-flac-new'
python scripts/ncm_convert.py '<歌曲.ncm>' --format mp3 --output-dir 'D:\codex\output\music-mp3-new'

# 显式选择多个文件，或整目录批量；目录递归需要 --recursive。
python scripts/ncm_convert.py '<歌曲1.ncm>' '<歌曲2.ncm>' --output-dir 'D:\codex\output\music-batch-new'
python scripts/ncm_convert.py '<NCM目录>' --recursive --output-dir 'D:\codex\output\music-recursive-new'
```

没有安装到 PATH 的环境可加 `--ncmdump '<ncmdump.exe>' --ffmpeg '<ffmpeg.exe>'`，也可设置 `NCMDUMP_EXE` / `FFMPEG_EXE`。不需额外安装 Python AES、Mutagen 或其他第三方库。

本机默认找到的工具：

- `D:\codex\temp\ncm-audio-tools\ncmdump-1.5.1\ncmdump.exe`；[原作者正式发布 1.5.1](https://github.com/taurusxin/ncmdump/releases/tag/1.5.1)。Windows amd64 ZIP SHA-256 为 `bb849221c06b8fdbff42aefb86baea9c07256568658d80f4be72a39a2a1632dc`，已与 GitHub 发布资源的 digest 一致性核对。原包、MIT 许可证和来源记录保存在同目录。源码仓库不附带此二进制。
- `D:\codex\temp\blender-mmd-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`，沿用本机已有视频工具。

默认临时解包/转码目录在 `D:\codex\temp\ncm-convert`，可用 `--temp-dir` 指定。每个任务使用独立临时目录，转换完成后清理自身临时文件，不删除 NCM。

`--format flac` 对原本为 MP3 的文件意味着转码到 FLAC 容器，不会恢复被有损编码丢失的音质；报告会明确 `native_format` 和 `transcoded`。默认 `auto` 避免不必要的转码，不按 NCM 大小猜格式。

## 文件保护与输出报告

- 检查 NCM 文件头和提取后音频签名；FFmpeg 全量解码通过后才发布音频到输出目录。
- 源文件只读，转换前后校验 SHA-256；不调用 ncmdump 的删除源文件选项。
- 拒绝覆盖现有 FLAC、MP3、同名报告和歌词；批量中不同文件夹的同名歌曲会报冲突，不静默覆盖另一首歌。
- 每首输出 `<歌曲名>.conversion.json`，记录源/输出校验值、后端路径和校验值、是否转码、解码 PCM 校验值、时长及 FLAC 规格。
- 若源旁有同名 `.lrc`，原样复制到输出目录。此次 LRC 开头含网易云 JSON 元数据行，后续做字幕需解析实际时间标记；“已复制歌词”不等于已完成特效字幕或音乐卡点。

本轮新增八项测试覆盖文件冲突、无效输入、失败不发布、按签名识别格式，以及主 BGM 配置不可默默回退伴奏；加上已有测试共 45 项通过。真实 FLAC 与 MP3 转换、完整音频解码另行完成，不仅依赖模拟测试。

## 后续 MMD 使用原声 FLAC

`presets/projects/franken-duet-full-v1.json` 的 `audio.bgm` 已指向主 FLAC，并记录 SHA-256、时长和规格。`audio.instrumental` 保留作素材来源参考，`instrumental_role` 明确其不再是本项目默认 BGM。

合成脚本新增 `--project` 入口，可直接读取已选择的 `audio.bgm`，校验文件和哈希；没有主 BGM 时会报错，不回退伴奏。旧 `--audio` 显式路径入口仍可用：

```powershell
python scripts/mux_production_audio.py --video '<已渲染的无声视频.mp4>' `
  --project presets/projects/franken-duet-full-v1.json --output '<新成片.mp4>' `
  --audio-start 0 --seconds 198.3158125 --gain 1 `
  --ffmpeg 'D:\codex\temp\blender-mmd-video-tools\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
```

这里的起点/时长仅示范整首音频，不是已审定的全曲影片时间轴。Full 动作到源 6367、现成相机到 6211，与这份约 198.316 秒录音的开头/结尾结构仍需按原 MV 检查；不能简单拉伸或截断。用户允许精细卡点后续手调，来源选择与时间结构检查仍须分开记录。既有旧视频未因为修改配置就被重新混流。
