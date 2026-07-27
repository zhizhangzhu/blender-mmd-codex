---
name: blender-setup
description: 檢查 Blender 是否已安裝，必要時在使用者確認後從官方來源下載、安裝並驗證。
---

# Blender 環境準備

## 使用時機

當使用者要執行 Blender、安裝 Blender Add-on、匯入 MMD 檔案，或回報找不到 Blender 時使用。

## 工作規則

1. 先使用 `scripts/blender_detect.py` 搜尋既有 Blender，不要直接下載。
2. 優先使用使用者明確指定的 Blender 路徑與版本。
3. 需要下載或安裝時，先顯示版本、來源、檔案大小、安裝位置與權限需求，取得使用者確認後再執行。
4. 只接受 Blender 官方下載來源；下載後應驗證 SHA-256。
5. 優先使用 portable 安裝，避免不必要的系統寫入與管理員權限。
6. 安裝完成後使用 `scripts/blender_validate.py` 驗證 Blender、Blender Python 與本 Add-on。
7. 失敗時回報實際原因與官方手動下載連結，不繞過作業系統安全提示。

## 不可宣稱的結果

- 沒有執行驗證前，不得宣稱 Blender 或 Add-on 已安裝成功。
- 沒有原始下載雜湊資料時，不得宣稱檔案已完成雜湊驗證。
- 不得把「找到 Blender 執行檔」說成「Add-on 已啟用」。
