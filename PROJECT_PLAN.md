# blender-mmd-codex 專案規劃書

## 專案概述

`blender-mmd-codex` 是一個專門協助 MMD 使用者在 Blender 中完成模型處理、動作套用、自動化與故障排除的 Codex 外掛，並搭配真正執行功能的 Blender Add-on。

本專案的目標不是取代 Blender，而是讓使用者可以用自然語言描述需求，再由 Codex 協助產生操作步驟、Blender Python 腳本，或直接呼叫 Blender Add-on 執行工作流程。

## 目的

協助 MMD 使用者在 Blender 中完成：

- PMX／PMD 模型匯入、整理與檢查
- VMD 動作、相機與表情套用
- 骨架、權重、材質與貼圖管理
- 剛體、布料、頭髮等物理設定
- Blender Python 腳本生成與執行
- 模型批次整理、轉換與匯出
- Blender 環境檢查與安裝
- 操作教學、錯誤排查與修復建議

## 核心功能

### 1. MMD 模型處理

- PMX／PMD 模型匯入
- 模型結構與骨架基本檢查
- 骨架命名、階層與必要骨骼檢查
- 權重異常、未綁定頂點與變形問題檢查
- 模型尺寸、方向與座標系統檢查

### 2. VMD 動畫與表情

- VMD 動作套用至指定模型
- VMD 相機匯入與套用
- VMD 表情／Morph 套用
- 骨架名稱對應與動作重定向
- 動畫套用結果檢查與錯誤提示

### 3. MMD 參考影片

- 匯入使用者提供的 MMD 渲染影片
- 將影片放入 Blender Video Sequence Editor 作為動作、節奏與鏡頭參考
- 將影片與使用者提供的 PMX／PMD 模型放在同一個工作場景中比較
- 後續可加入姿勢擷取、骨架重定向與近似動作關鍵幀生成
- 只有影片時，不宣稱可以還原原始 VMD、相機或物理資料

### 4. 骨架、材質與貼圖管理

- 骨架結構與控制骨骼檢查
- 權重與頂點群組檢查
- 材質透明度、背面剔除與顯示設定檢查
- 貼圖路徑、遺失檔案與格式檢查
- 外部資源重新連結與路徑整理

### 5. 基礎物理設定

- 剛體與碰撞群組檢查
- 剛體連結與約束檢查
- 頭髮、裙擺與布料的基礎設定建議
- 物理模擬參數檢查
- 常見穿模、抖動與爆炸問題的排查建議

### 6. Blender Python 自動化

- 依照自然語言需求產生 Blender Python 腳本
- 產生可重複執行的批次處理腳本
- 產生模型整理、重新命名、材質修復與匯出腳本
- 執行前檢查目標物件、場景與檔案路徑
- 提供腳本內容預覽、錯誤說明與執行結果

### 7. Blender 環境自動準備

當使用者尚未安裝 Blender 時，外掛應能協助完成以下流程：

1. 偵測 Blender 是否已安裝。
2. 搜尋使用者設定的路徑、系統 PATH 與常見安裝位置。
3. 取得作業系統與 CPU 架構資訊。
4. 從 Blender 官方下載來源取得穩定版或指定 LTS 版本資訊。
5. 在下載前顯示版本、檔案大小、安裝位置與所需權限，要求使用者確認。
6. 下載對應的 Blender 安裝包或免安裝壓縮包。
7. 驗證下載檔案的雜湊值；驗證失敗時停止安裝並提示重新下載。
8. 依作業系統執行安裝，或建立可與其他版本共存的 portable 目錄。
9. 啟動 Blender，確認可以執行 `--version` 與 Blender Python。
10. 安裝或啟用本專案的 Blender Add-on。
11. 執行最小功能測試，確認 Add-on 已成功載入。
12. 將 Blender 執行檔路徑與版本寫入本專案設定，供後續工作流程使用。

#### 安裝策略

- 預設使用 Blender 官方穩定版或專案指定的 LTS 版本，不在程式中硬編碼不可更新的「最新版」網址。
- MVP 優先支援 Windows；之後補上 macOS Intel、macOS Apple Silicon、Linux x64 與 Linux arm64。
- 優先提供 portable 安裝模式，降低管理員權限需求並允許多個 Blender 版本共存。
- 若使用一般安裝程式，需要系統管理員權限時，必須由使用者明確確認。
- 無網路、下載來源不可用、權限不足或硬體不符合需求時，提供可理解的錯誤訊息與官方手動下載連結。
- 不繞過作業系統的安全提示，也不在未經確認的情況下靜默安裝軟體。
- Blender 版本需與 MMD 匯入器、VMD 工具及本專案 Add-on 維持相容；版本不符時應先警告使用者。

#### 安裝模組建議

```text
scripts/
├─ blender_detect.py       # 偵測 Blender 路徑、版本與作業系統
├─ blender_download.py     # 取得官方下載資訊並下載安裝包
├─ blender_install.py      # 執行 portable 或一般安裝流程
├─ blender_validate.py     # 驗證 Blender 與 Add-on 是否可用
└─ blender_bootstrap.py    # 串接完整的偵測、下載、安裝與驗證流程
```

目前第一個垂直切片已完成偵測、SHA-256 驗證下載、portable ZIP／tar.xz 安裝與 Blender 驗證工具。官方版本資訊與雜湊資料的自動取得、一般安裝程式及跨平台完整安裝流程仍需後續實作。

## 外掛組成

### Codex 外掛

負責：

- AI 教學與工作流程規劃
- MMD 問題分析與錯誤排查
- Blender Python 腳本生成
- Blender 安裝與環境準備流程的協調
- 呼叫本機腳本、傳遞參數與整理執行結果
- 引導使用者完成需要人工確認的操作

### Blender Add-on

負責：

- 在 Blender 內實際執行 MMD 模型、VMD 與表情相關功能
- 讀取與修改 Blender 場景、物件、骨架、材質與物理資料
- 提供 Blender 內的操作面板與檢查報告
- 執行 Codex 產生並確認過的 Blender Python 腳本

### GitHub 專案

負責保存：

- Codex 外掛程式碼
- Blender Add-on 程式碼
- 安裝與使用文件
- 測試案例與範例檔案
- 版本紀錄與發行版本

### Marketplace

Codex 外掛可以放到 GitHub，再透過 Codex 的自訂 Marketplace 或其他支援的外掛來源安裝。Blender Add-on 則仍需要另外在 Blender 中安裝或由本專案的環境準備流程安裝。

Codex Marketplace 是 Codex 外掛的發佈與安裝入口，不是 Blender Add-on 商店。實際公開發佈、私人 Marketplace、repo marketplace 與可用平台，需依當時的 Codex 外掛規範確認。

## 建議專案結構

```text
blender-mmd-codex/
├─ .codex-plugin/
│  └─ plugin.json
├─ skills/
│  ├─ mmd-model-check/
│  ├─ vmd-workflow/
│  ├─ blender-setup/
│  ├─ batch-organizer/
│  └─ troubleshooting/
├─ scripts/
│  ├─ blender_detect.py
│  ├─ blender_download.py
│  ├─ blender_install.py
│  ├─ blender_validate.py
│  └─ blender_bootstrap.py
├─ blender_addon/
│  ├─ __init__.py
│  ├─ operators/
│  ├─ panels/
│  ├─ mmd/
│  ├─ vmd/
│  ├─ physics/
│  └─ validation/
├─ assets/
│  ├─ templates/
│  └─ examples/
├─ README.md
├─ LICENSE
└─ .agents/
   └─ plugins/
      └─ marketplace.json
```

## 第一版 MVP

第一版優先製作：

1. MMD 模型匯入與基本檢查
2. VMD 動作套用
3. MMD 參考影片匯入與對照
4. 骨架與表情管理
5. 材質與貼圖檢查
6. 基礎物理設定
7. 一鍵生成 Blender 操作腳本
8. Blender 未安裝時的自動偵測、下載、安裝與驗證
9. MMD 模型批次整理

### MVP 驗收條件

- 能判斷 Blender 是否已安裝，並取得可執行檔路徑與版本。
- 沒有 Blender 時，能在使用者確認後完成官方版本下載與安裝。
- 安裝後能自動驗證 Blender 可啟動，且 Blender Add-on 已載入。
- 能將使用者提供的 MMD 渲染影片加入 Blender 時間軸作為參考。
- 能匯入至少一個 PMX 或 PMD 範例模型並產生檢查報告。
- 能將至少一個 VMD 動作套用至指定模型。
- 能檢查骨架、表情、材質、貼圖與基礎物理資料。
- 能產生一個可在 Blender 中執行的 Python 腳本。
- 失敗時能提供記錄、原因與手動處理方式。

## 建議工作流程

```text
使用者提出 MMD 需求
        ↓
Codex 判斷工作類型與必要資源
        ↓
檢查 Blender、Add-on、模型與 VMD 檔案
        ↓
缺少 Blender？──是──> 使用者確認後下載、安裝與驗證
        │
        否
        ↓
Codex 產生步驟或 Blender Python 腳本
        ↓
Blender Add-on 執行實際操作
        ↓
輸出檢查報告、錯誤說明與下一步建議
```

## 安全與權限要求

- 只使用 Blender 官方下載來源，並保留下載網址、版本與雜湊驗證結果。
- 下載、安裝、啟動 Blender、執行腳本與修改檔案前，清楚顯示即將進行的操作。
- 不在未確認的情況下取得管理員權限或修改系統設定。
- 執行 AI 生成的 Blender Python 腳本前，顯示腳本內容與可能影響的檔案、場景及物件。
- 對模型檔、貼圖檔與 VMD 檔案使用明確的工作目錄，避免誤處理其他資料。
- 保留操作日誌，讓使用者能追蹤安裝、匯入、整理與匯出的結果。
- 任何自動刪除、覆寫或批次轉換操作都應提供預覽、確認與備份選項。

## 發布方式

### Codex 外掛

1. 在 GitHub 建立公開或私有專案。
2. 建立 `.codex-plugin/plugin.json` 與必要的 `skills/`、`scripts/` 等內容。
3. 在本機或 repo marketplace 測試外掛。
4. 確認 Codex 外掛技能、腳本權限與安裝流程。
5. 依官方規範提交或提供 Marketplace 安裝入口。

### Blender Add-on

Blender Add-on 可獨立打包成 ZIP，讓使用者在 Blender 中安裝；也可以由 `blender_bootstrap.py` 在完成 Blender 安裝後協助複製、安裝與啟用。

Codex 外掛與 Blender Add-on 是兩個不同的安裝單位：

| 元件 | 安裝位置 | 主要用途 |
| --- | --- | --- |
| Codex 外掛 | Codex 外掛來源或 Marketplace | AI 教學、腳本生成、工作流程協調 |
| Blender Add-on | Blender 使用者設定中的 Add-ons | 在 Blender 內執行 MMD 功能 |
| Blender 本體 | 使用者作業系統 | 提供 3D、動畫、物理與 Python 執行環境 |

## 目前進度

- [x] 已確認技術上可行
- [x] 已確認外掛可設計成一個專案包
- [x] 已建立本規劃文件
- [x] 已建立 `.codex-plugin/plugin.json`
- [x] 已建立 Blender Add-on 最小骨架
- [x] 已實作 Blender 偵測、下載驗證、portable 安裝與環境驗證工具
- [x] 已實作 MMD 參考影片加入 Blender 時間軸的入口
- [ ] 尚未整合 PMX／PMD 的完整匯入器
- [ ] 尚未實作 VMD 動作、相機與表情解析
- [ ] 尚未實作影片姿勢擷取與骨架重定向
- [ ] 尚未上傳 GitHub
- [ ] 尚未加入或建立 Marketplace 測試來源

## 建議開發順序

1. 定義 Codex plugin manifest 與第一批 skills。
2. 建立 Blender Add-on 最小骨架與版本相容性策略。
3. 實作 Blender 偵測與驗證功能。
4. 實作官方下載、portable 安裝與使用者確認流程。
5. 實作 PMX／PMD 匯入與基本檢查。
6. 實作 VMD 動作、相機與表情套用。
7. 加入材質、貼圖、骨架、權重與基礎物理檢查。
8. 加入腳本生成、批次整理與匯出流程。
9. 建立跨作業系統測試與範例專案。
10. 完成 GitHub、文件與 Marketplace 發布準備。

## 參考資料

- [OpenAI 官方：Package your plugin](https://developers.openai.com/codex/plugins/build)
- [Blender 官方下載頁](https://www.blender.org/download/)
- [Blender 官方系統需求](https://www.blender.org/download/requirements/)
- [Blender 官方版本下載](https://www.blender.org/download/previous-versions/)

## 專案定位總結

`blender-mmd-codex` 是一個「Codex 外掛 + Blender Add-on + Blender 環境準備工具」的整合專案：

- Codex 外掛負責理解需求、教學、腳本生成與流程協調。
- Blender Add-on 負責在 Blender 內執行 MMD 實際功能。
- Blender 環境準備工具負責偵測 Blender；若未安裝，則在使用者確認後從官方來源下載、安裝並驗證。
- GitHub 負責保存程式碼、文件、範例與版本。
- Marketplace 負責提供 Codex 外掛的安裝入口。

最終目標是讓 MMD 使用者即使沒有預先安裝 Blender，也能在清楚、安全且可追蹤的流程下完成環境準備，接著使用 Codex 協助完成模型、動畫、材質、物理與批次自動化工作。
