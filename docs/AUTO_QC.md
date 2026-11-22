# 自动 QC 判官、多帧稀疏检查与时序诊断

日期：2026-11-22 · 状态：生效 · 规则配置：[auto-qc-v1.json](../presets/qc/auto-qc-v1.json) · 工具：[auto_qc.py](../scripts/auto_qc.py)

## 1. 定位与红线（QC-01 / ART-01 / SCOPE-01）

- **职责**：在向猪猪交付审图之前，自动筛除明显不合格候选（灰蒙、死白过曝、人物发灰、无轮廓、跨帧漂移、时序闪烁）并对候选排序，减少人工逐轮盯细节的成本。
- **红线 1（ART-01）**：自动 QC 通过、得分高或 VLM 判官通过，**永远不等于用户美术认可**；所有报告强制 `user_approval: false`。
- **红线 2（SCOPE-01）**：跨全曲 8–12 帧稀疏检查与低分辨率 1–2 秒时序诊断属于**标准 QC 证据**，严禁编码为视频样片或当作视频交付（报告强制 `counts_as_video_delivery: false`）。默认交付仍只出静帧／对照板。

## 2. 两层自动质量判官

### 第一层：可测硬指标（源自猪猪历史真实反馈）

| 历史反馈出处 | 转化指标 | 目的 |
| --- | --- | --- |
| 2026-11-14「画面灰蒙、不够明亮」 | `luma_p05`（黑位上限）、`luma_p95`（亮部下限）、`dynamic_range_p95_p05`、`luma_std`、`luma_mean` | 拒绝整体发灰、反差发平、黑位浮灰或过暗 |
| 2026-11-17「伊科尔还是有点太亮了」 | `clipped_white_ratio`、`highlight_ratio`、以及可选主体 ROI/Mask 下的 `subject_luma_mean` 与 `subject_clipped_white_ratio` | 保护白衣与亮肤色层次，防止人物大面积死白 |
| 2026-11-14「明净三渲二与黑线表现」 | `saturation_mean` / `saturation_p90`、`dark_edge_density`、`laplacian_sharpness` | 捕捉全图死灰、过度全屏 Bloom 洗糊、黑线丢失 |
| 2026-11-13/14「人物与场景层次不足」 | `subject_bg_luma_separation`（配合 `--subject-roi` 或 `--subject-mask`） | 检查主体与舞台背景是否具备可读明暗分离 |

### 第二层：校准过的 VLM 判官协议

- 由当前会话高推理主控（`supervisor`）审看 `vlm-packet`（候选图 + 局部 ROI + 参考图 + 偏好清单 + 硬指标摘要），按 5 维（明净度、人物 NPR 层次、黑线与五官、舞台分离、参考方向一致）逐候选输出结构化判断。不调用外部付费 API（SPEC §6）。
- **启用门槛（回测校准）**：必须用含猪猪真实否决案例的标注集运行 `auto_qc.py calibrate`，达到 `min_labeled_cases >= 4`、`reject_recall >= 0.80`（能复现至少 80% 的用户否决）与 `overall_accuracy >= 0.75`，才允许将其作为自动初筛器。
- **提升反馈密度**：向猪猪提交评审时，优先把经硬指标筛过的 4–9 个变体做成对照板让用户排序或标缺陷，以便持续扩充校准集。

## 3. 时间维度标准诊断（L3 必经门槛）

仅靠单帧 4290 无法发现换姿态发影失效、跨段落亮度漂移与 NPR 阴影／描边闪烁。每轮实质性渲染或风格包改动，在进入里程碑评审前应补充两项诊断：

1. **多帧稀疏检查（8–12 帧）**：在全曲或当前有效动作范围内均匀取 8–12 帧（可固定锚定主检查帧如 4290），逐帧跑硬指标，核对 `frame_fail_ratio <= 0.15`、亮度漂移 `luma_mean_drift` 与最坏帧定位。
2. **短片段低分辨率时序诊断（1–2 秒）**：以 640×360（或 960×540）、30fps 渲染 1–2 秒连续帧序列（仅存诊断目录，不编码交付），计算相邻帧亮度二阶差分 `luma_flicker_p95`（过滤平滑渐变，专抓呼吸闪烁）、边缘图逐帧抖动 `edge_jitter_mean` 与突跳比例 `hard_luma_jump_ratio`。

## 4. 命令速查

```powershell
# 1. 单帧／多候选硬指标检测与排序（可选传入人物归一化 ROI x,y,w,h）
python -m scripts.auto_qc eval-still path/to/caseA.png path/to/caseB.png --subject-roi 0.25,0.12,0.50,0.85

# 2. 生成标准 8-12 帧稀疏检查与 1-2 秒低分辨率时序诊断计划
python -m scripts.auto_qc plan-diagnostics --start-frame 1 --end-frame 11899 --fps 60 --anchor-frame 4290

# 3. 对已渲染的 8-12 帧稀疏样本跑聚合 QC
python -m scripts.auto_qc eval-sparse D:/codex/output/.../frame-*.png

# 4. 对已渲染的 1-2 秒低分辨率诊断帧序列跑时序闪烁／抖动分析
python -m scripts.auto_qc eval-temporal D:/codex/output/.../diag-seq-*.png --fps 30

# 5. 生成高推理主控 VLM 判官审图任务包
python -m scripts.auto_qc vlm-packet path/to/caseA.png path/to/caseB.png

# 6. 用猪猪真实历史反馈标注集做回测校准
python -m scripts.auto_qc calibrate --cases path/to/labeled-cases.json
```
