# blender-mmd-codex

協助 MMD 使用者在 Blender 中進行模型檢查、參考影片整理、環境準備與自動化工作的 Codex 外掛專案。

本專案由兩個主要部分組成：

- Codex Plugin：提供 skills、操作教學、錯誤排查與工作流程協調。
- Blender Add-on：在 Blender 內執行場景檢查、模型基本檢查與 MMD 參考影片匯入。

MMD 制作 Skill 設計與驗證範圍見 [設計文件](docs/superpowers/specs/2026-10-26-mmd-production-design.md)。本機安裝位置與使用方式見 [本機環境](docs/LOCAL_SETUP.md)。

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

本版增加 `mmd-production` 工作流程：透過另外安裝的 Blender MCP 與官方 MMD Tools 操作模型、人物／相機 VMD、場景與渲染。MMD Tools Append 為可選的資源目錄與場景輔助工具；詳細範圍見 [MMD Skill](skills/mmd-production/SKILL.md)。

本專案自身仍未實作以下功能：

- 自行解析 PMX／PMD（實際制作使用 MMD Tools 現有匯入器）
- 自行解析 VMD（實際套用使用 MMD Tools 現有匯入器）
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
├─ docs/                      # 本機環境、設計與實施記錄
├─ LICENSE
└─ README.md
```

## Codex Plugin 功能

目前包含以下 skills：

- `mmd-asset-search`：独立的模型／动作／镜头配布检索，核对作者、版本、获取条件和当前状态
- `mmd-production`：資源配布檢索、模型／動作／相機套用、場景調整、預覽與影片輸出
- `blender-setup`：偵測、下載、安裝與驗證 Blender
- `mmd-model-check`：規劃 PMX／PMD 模型檢查流程
- `mmd-video-reference`：處理 MMD 渲染影片參考流程
- `vmd-workflow`：透過 MMD Tools 套用 VMD 動作、相機與表情，檢查映射、比例與時間
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
- Blender 4.2 或更新版本 + MMD Tools 4.x；本機目標為 Blender 4.5 LTS
- Blender MCP：操作打開的 Blender 場景；服務端依賴安裝在獨立環境
- MMD Tools Append：可選，提供資源目錄、材質與骨架等輔助功能
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

本機安裝不代表已提交至公開 Codex Plugin 目錄。Skill 可從本機檔案系統載入；Blender MCP 必須另行完成服務註冊。

## 參考文件

- [MMD 工作流程 Skill](skills/mmd-production/SKILL.md)
- [圖文來源與版本核對](skills/mmd-production/references/learning-sources.md)
- [本機安裝與驗證](docs/LOCAL_SETUP.md)
- [OpenAI Plugin 建置文件](https://developers.openai.com/plugins/build/plugins)
- [OpenAI Plugin 測試文件](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [OpenAI Plugin 提交文件](https://developers.openai.com/plugins/deploy/submission)
- [Blender 官方下載頁](https://www.blender.org/download/)

## License

本專案採用 [MIT License](LICENSE)。
