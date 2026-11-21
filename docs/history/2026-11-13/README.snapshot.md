# blender-mmd-codex

新增 [人物自阴影、描边与播放器色彩](docs/SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md)：地面投影、近地AO、刘海与身体自身遮挡、分区加厚黑线，以及旧MP4漏色彩标记的修正。入口 `D:\codex\output\MMD-Duet-Shadow-Color-v1`，最终工程 `production-v3`／五秒视频 `captions-5s-v2`，状态以 `delivery.json` 为准；PotPlayer具体配置尚未证实。

新增 [蓝金婚礼氛围](docs/BLUE_GOLD_WEDDING_STUDY.md)：学习三点布光职责、局部 Volume Scatter 和分离光晕，在既有柔光礼堂增加蓝金射灯、走道微光，并把官方字幕改为蓝／象牙／金与深蓝／深铜配色。入口 `D:\codex\output\MMD-Duet-Blue-Gold-Wedding-v1`，正式工程 `production-v4`；同段五秒，最终状态以交付 JSON 为准，旧版与已认可基线保留。

猪猪反馈聚焦舞台仍太暗，新增 [柔光、顶光与逆光](docs/SOFT_TOP_RIM_LIGHTING.md)：大尺寸面光提亮走道／花卉，人物补充暖色后侧亮边，保留局部冷暖。入口 `D:\codex\output\MMD-Duet-Soft-Top-Rim-v1`，最终工程 `production-v2`；同段五秒，视频状态以交付 JSON 为准，不代表全曲或用户美术认可。

新增 [双人官方动效字幕与聚焦灯光](docs/DUET_CAPTION_STABILITY_AND_LIGHTING.md)：复用 HIMEHINA 官方字幕，按实际动画整组固定前后层；修复前景脸部遮罩拆字与黑字镂空机制。学习 MiaoBox 灯光教程后，礼堂改用响应灯光的材质及局部冷暖光区。五秒样片与逐帧验收入口 `D:\codex\output\MMD-Duet-Captions-Contrast-v1`；不代表双人全曲已交付，旧认可版保留。

后续 [舞台光影再研究](docs/FOX_STAGE_ART_DEEP_STUDY.md) 已完成第二支五秒 1080p60：实际地面区域、斜向人物投影、亮边专属 AOV／脸部排除和局部空气。交付 `D:\codex\output\MMD-Fox-StageArt-v2`，最终 `production-v5`／`sample-5s-v2`；等待猪猪美术评价，不能把技术验收当作参考风格已匹配。

新增 [小狐狸灯光与镜头学习](docs/FOX_LIGHTING_AND_CINEMA.md)：雪夜礼堂冷暖、双人景深、原生运动模糊已做成独立五秒 1080p60 样片与开关对照，入口 `D:\codex\output\MMD-Fox-Cinema-v1`。这是实际舞台氛围与光学改动，等待用户美术评价；旧样片保留，不代表全曲完成。

本轮受光／稳定／颜色修订已完成五秒 1080p60 样片、三组近景测试及 300 帧线性归档，方法与边界见 [受光与颜色流程](docs/LIGHT_SPACE_AND_COLOR_PIPELINE.md)。旧认可版保留，双人全曲未在本轮渲染。

猪猪的 Blender MMD 制作仓库：实际制作、验证效果，并把学到的知识整理成可复用的预设与流程。

## 先打开预设与知识库

**帧间 · MMD 预设与知识库**：`D:\codex\output\MMD-Atlas-v1\index.html`。双击即可离线使用，支持真实样片、风格／画幅筛选、收藏、效果对照、站内笔记与参数下载。

- [知识与制作总目录](docs/KNOWLEDGE_INDEX.md)：按问题找方法、了解最新状态。
- [网站使用与维护](docs/GALLERY_GUIDE.md)：更新资料、增加预设、构建静态 HTML。
- `catalog/library.json`：条目、预览、分类与验证范围的统一目录。
- `site/`：网站源码；设计参考与规则在 `site/DESIGN.md`。

## 当前制作状态

| 内容 | 实际状态 | 入口 |
| --- | --- | --- |
| 双人明亮礼堂 | 用户近期认可的五秒 1080p60 原声样片，300 帧验收通过 | [原神角色与预设](docs/GENSHIN_CHARACTER_AND_PRESETS.md) |
| 半开放夜景 | 独立静帧与冷暖／薄雾实验，未替换五秒基线 | [舞台美术](docs/STAGE_ART_NIGHT_STUDY.md) |
| 鸣潮渲染 | 节点读取与发丝输入静帧实验，未整体适配双人 | [鸣潮研究](docs/WUWA_TOON_STUDY.md) |
| 风格套装 | Gosari542 soft／观海子 graphic、neon，各有独立横竖版四秒技术样片 | [风格组合](docs/STYLE_PRESETS.md) |
| 双人全曲 | 尚未交付；本轮为网站和知识整理，不启动长片渲染 | [双人制作](docs/DUET_FULL_PRODUCTION.md) |

旧实验、单角色成片和过往状态保留在对应日期的文档中。最新制作不按旧文档中的“当前”字样倒退；风格名称不代表作者原始预设或同等质量。

## 按制作问题进入

| 分类 | 主要入口 |
| --- | --- |
| 人物材质 | [原神](docs/GENSHIN_CHARACTER_AND_PRESETS.md)、[鸣潮](docs/WUWA_TOON_STUDY.md)、[半兰伯特](docs/HALF_LAMBERT_STUDY.md)、[材质分区](docs/SURFACE_REFINEMENT.md)、[脸线](docs/FACE_INK_REFINEMENT.md) |
| 舞台灯光 | [礼堂材质重建](docs/HESPERIDES_REFERENCE_REBUILD.md)、[冷暖夜景](docs/STAGE_ART_NIGHT_STUDY.md)、[去灰与调色](docs/CLEAR_LIGHT_AND_GRADING.md) |
| 后期字幕 | [渲染／后期组合](docs/STYLE_PRESETS.md)、[横竖字幕与前后层](docs/ADVANCED_MMD_SUBTITLES.md) |
| 动作成片 | [工作流程](docs/PRODUCTION_WORKFLOW.md)、[物理与验收](docs/PRODUCTION_TECHNIQUES.md)、[镜头检索](docs/CAMERA_SEARCH.md)、[音乐转换](docs/AUDIO_CONVERSION.md) |
| 参考审美 | [Gosari542](docs/GOSARI_REFERENCE.md)、[观海子](docs/GUANHAIZI_REFERENCE.md)、[下一步提升](docs/KNOWLEDGE_INDEX.md) |
| 环境工具 | [本机环境](docs/LOCAL_ENVIRONMENT.md)、[教程转写与 OCR](docs/TUTORIAL_TRANSCRIPTION.md)、[代理约定](AGENTS.md) |

## 原有插件框架与环境入口

本机已安装 Blender 5.2.2 LTS，不需要再次下载。自定义路径可通过 `python -m scripts.blender_detect --executable "E:\tools\Blender Foundation\Blender 5.2\blender-launcher.exe"` 或 `BLENDER_EXECUTABLE` 指定。`scripts/blender_inventory.py` 在 Blender 内检查真实插件状态，`scripts/mmd_first_scene.py` 创建独立的 PMX + VMD 导入草稿。

下方为原有插件框架说明；其中「尚未实现导入」指本仓库自身尚未实现 PMX/VMD 解析器。当前制作通过本机已安装的 MMD Tools 执行导入。

協助 MMD 使用者在 Blender 中進行模型檢查、參考影片整理、環境準備與自動化工作的 Codex 外掛專案。

本專案由兩個主要部分組成：

- Codex Plugin：提供 skills、操作教學、錯誤排查與工作流程協調。
- Blender Add-on：在 Blender 內執行場景檢查、模型基本檢查與 MMD 參考影片匯入。

完整產品規劃請參考 [PROJECT_PLAN.md](PROJECT_PLAN.md)。

## 目前狀態

目前完成第一個可驗證的垂直切片：

- Codex plugin manifest：`.codex-plugin/plugin.json`
- Blender 執行檔偵測
- Blender 官方下載網址產生
- SHA-256 下載驗證
- ZIP／tar.xz portable Blender 安裝
- Blender 版本、Python API 與 Add-on 載入驗證
- Blender 場景基本檢查
- MMD 模型的 Mesh／Armature 基本檢查
- 將使用者提供的 MMD 渲染影片加入 Blender 時間軸作為參考

以下功能尚未完成：

- PMX／PMD 完整匯入
- VMD 動作、相機與表情解析
- 影片姿勢擷取與骨架重定向
- 完整材質、權重與物理修復
- GitHub 發布與公開 Codex Plugin 提交

## 專案結構

```text
.
├─ .codex-plugin/
│  └─ plugin.json             # Codex Plugin manifest
├─ blender_addon/             # Blender 內的 Add-on
│  ├─ __init__.py
│  ├─ operators/
│  └─ panels/
├─ scripts/                   # Blender 偵測、安裝與驗證工具
├─ skills/                    # Codex 可使用的工作流程
├─ tests/                     # Python 單元測試
├─ PROJECT_PLAN.md            # 專案規劃書
├─ LICENSE
└─ README.md
```

## Codex Plugin 功能

目前包含以下 skills：

- `blender-setup`：偵測、下載、安裝與驗證 Blender
- `mmd-model-check`：規劃 PMX／PMD 模型檢查流程
- `mmd-video-reference`：處理 MMD 渲染影片參考流程
- `vmd-workflow`：規劃 VMD 動作、相機與表情工作流程
- `troubleshooting`：分析 Blender 與 MMD 常見問題

Codex Plugin 與 Blender Add-on 是不同的安裝單位。Codex 負責理解需求與協調流程，Blender Add-on 負責在 Blender 內執行實際操作。

## Blender Add-on 功能

在 Blender 的 `Properties > Scene` 中提供 `Blender MMD Codex` 面板，可執行：

1. 檢查目前場景中的物件、Mesh 與骨架數量。
2. 檢查選取物件是否同時包含 Mesh 與 Armature。
3. 將 `.mp4`、`.mov`、`.mkv`、`.webm` 或 `.avi` MMD 影片加入 Video Sequence Editor。

參考影片是已渲染的 2D 影片，只能作為動作、節奏與鏡頭參考。若要精確套用原始動畫，仍需要原始 VMD、VPD、相機檔或 Blender 專案。

## 開發環境

- Python 3.10 或更新版本
- Blender 3.6 或更新版本（實際 Add-on 相容性仍會依功能調整）
- Codex CLI（若要使用 CLI 管理 Marketplace）
- Git

本專案不將 Blender 安裝包直接提交進 Git；安裝工具會依明確指定的版本與官方下載來源取得檔案。

## 執行環境工具

所有命令都應從專案根目錄執行。

### 偵測 Blender

```bash
python3 -m scripts.blender_detect
```

找不到 Blender 時，命令會回傳非零狀態；這代表需要進入安裝流程，不代表程式本身崩潰。

### 取得官方下載資訊

必須指定完整版本，不在程式內自動猜測不可控的最新版：

```bash
python3 -m scripts.blender_download \
  --version <blender-version> \
  --system <Windows|Darwin|Linux> \
  --machine <x86_64|arm64>
```

### 安裝 portable Blender

下載與安裝需要使用者明確確認，且必須提供官方檔案的 SHA-256：

```bash
python3 -m scripts.blender_bootstrap \
  --version <blender-version> \
  --sha256 <official-sha256> \
  --install-dir ./portable_blender \
  --addon-path ./blender_addon \
  --yes
```

安裝流程會：

1. 先檢查現有 Blender。
2. 確認下載來源為 Blender 官方 HTTPS 網域。
3. 下載並驗證 SHA-256。
4. 解壓縮至指定 portable 目錄。
5. 執行 Blender 版本與 Python API 驗證。
6. 嘗試載入並註冊本專案 Add-on。

不使用 `--yes` 時，不會執行下載或安裝。

## 安裝 Blender Add-on

目前可在 Blender 內使用以下方式安裝：

1. 將 `blender_addon/` 打包成 ZIP。
2. 開啟 Blender。
3. 進入 `Edit > Preferences > Add-ons`。
4. 選擇 `Install...`，指定 Add-on ZIP。
5. 啟用 `Blender MMD Codex`。
6. 到 `Properties > Scene` 找到外掛面板。

正式版本會再提供自動打包與自動啟用流程。

## 執行測試

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts blender_addon tests
```

Codex Plugin manifest 可使用 plugin-creator 提供的驗證工具檢查：

```bash
python3 /path/to/plugin-creator/scripts/validate_plugin.py .
```

目前測試不需要安裝 Blender，會使用測試替身驗證偵測、下載驗證、portable 解壓縮、路徑安全與驗證報告流程。若要確認 Blender Add-on 真正能啟動，仍需在實際 Blender 環境執行測試。

## Git 與 Codex 發布

GitHub repository 用來保存原始碼與版本；GitHub 本身不會自動將專案發佈成 Codex Plugin。

一般流程是：

```text
Git commit
→ 推送 GitHub
→ 本機／Repo Marketplace 測試
→ 準備公開提交資料
→ OpenAI Plugin Submission 審核
```

公開 Codex Plugin 需要準備：

- 有效的 `.codex-plugin/plugin.json`
- 最終版 skills
- 外掛名稱與描述
- Logo、分類、網站與支援網址
- 隱私政策與服務條款
- 測試案例與預期結果
- 已驗證的個人或商業開發者身分

目前本專案尚未設定 GitHub remote，也尚未提交至公開 Codex Plugin 目錄。

## 參考文件

- [專案規劃書](PROJECT_PLAN.md)
- [OpenAI Plugin 建置文件](https://developers.openai.com/plugins/build/plugins)
- [OpenAI Plugin 測試文件](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [OpenAI Plugin 提交文件](https://developers.openai.com/plugins/deploy/submission)
- [Blender 官方下載頁](https://www.blender.org/download/)

## License

本專案採用 [MIT License](LICENSE)。
