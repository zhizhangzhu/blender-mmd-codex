---
name: mmd-model-check
description: 檢查使用者提供的 PMX／PMD 模型、骨架、材質、貼圖與基本場景狀態。
---

# MMD 模型檢查

## 使用時機

當使用者提供 PMX／PMD，或詢問模型匯入、骨架、權重、材質、貼圖與物理問題時使用。

## 第一版工作流程

1. 確認 Blender 與本專案 Add-on 已通過環境驗證。
2. 確認輸入檔案存在，並保留模型旁的貼圖相對路徑。
3. 在 Blender 中檢查是否有 Mesh、Armature、材質、Image Texture 與 Shape Keys。
4. 將結果分成通過、警告與錯誤，不把警告誤報成錯誤。
5. 提供可重現的修正步驟；需要覆寫或刪除資料時先取得確認。

## 報告最低欄位

- 輸入檔案與檔案類型
- Blender 版本
- Mesh 與 Armature 數量
- 材質數量與遺失貼圖數量
- Shape Keys／Morph 可用性
- 權重或骨架異常
- 建議的下一步
