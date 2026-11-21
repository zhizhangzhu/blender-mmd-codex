# 旧制作状态记录（历史归档）

2026-11-11 从 AGENTS.md 中移出的历史进度，保留排查证据。下列“最新／当前”均指各轮写作时点，不能覆盖 [现行知识目录](KNOWLEDGE_INDEX.md) 和近期已认可五秒基线。

百度网盘原包已完成核验：实际下载路径 `D:\BaiduNetdiskDownload\【原神】赫斯珀利德斯之馆(礼堂).7z`。已通过7-Zip完整性检查并解压到 `D:\codex\temp\Hesperides-Baidu-Original-v1\GI_Hesperides`，121个文件与E盘原素材SHA-256全部一致，无额外灯光／PMM／完整Ray工程；不用重复下载此包。报告 `D:\codex\output\Hesperides-Baidu-Archive-Audit-v1\archive-audit.json`，复用工具 `scripts/audit_stage_archive.py`。源包和旧素材保持不变。

猪猪最新仍不满意场景渲染／打光／质感，要求以随包 Ray 预览为目标并搜索作者现成配置。核实见 `docs/HESPERIDES_AUTHOR_SETUP.md`：作者 paierer、B站 UID1503209807；原视频 BV1xEJe6oEmy 简介提供百度网盘（提取码stpr）。已正常查看公开列表，本地已有23份Ray材质、14份MatCap与14份法线启用配置；源blend无灯光／相机，readme明确仅模型、材质自行处理。尚未找到完整作者布光工程或本场景专门教程。不要把上一版清亮日光／亮度均值提高视为已匹配原预览；先做原材质、同机位场景对照，再回双人样片，不继续全曲长渲。

最新任务：猪猪认为上一版偏暗、灰蒙、场景打光和后期不足，要求先学习对应教程，再仅出 **5 秒新改版**。学习证据、同 HDR 诊断、重打光与人物／场景分开调色见 `docs/CLEAR_LIGHT_AND_GRADING.md`。当前新工程位于 `D:\codex\output\MMD-Clear-Light-Revision-v1\lighting-v4`，样片在 `sample-5s-v1` 已完成，文件 `Aether_Duet_5s_REVIEW.mp4`，源帧 4140–4439、1080p60、指定原声。300帧完整音画解码、接缝与代表帧复看通过。不得因自发光关键词就把角色当成场景照明；本来已有 NPR Emission。只完成本次五秒验收，不继续全曲长渲。

猪猪最新看过空的修订近景，认为略好，要求这轮**先只完成 20 秒样片**；新旧全曲渲染均已停止。当前样片为 `D:\codex\output\Aether-Look-Revision-v1\sample-20s-v1`，使用 `production-v5` 正式镜头源帧 4140–5339、1080p60、所选原声 FLAC；已完成 1200 帧整段音画解码、接缝检查与代表帧目视复看。成片文件为该目录下 `Aether_Duet_20s_REVIEW.mp4`。按这次明确范围完成样片，不继续全曲长渲，也不能把样片当作全曲成品。

当前空的修订见 `docs/AETHER_LOOK_REVISION.md`：猪猪拒绝旧版空的扁平质感、肤色、眼睛和黑线，旧 `full-render-v1` 已停止，不能交付为新版成片。最新研究工程位于 `D:\codex\output\Aether-Look-Revision-v1\look-v5`；阿克西妮娅、指定明亮礼堂、角色动作分配和原声 FLAC 要求继续保留。静帧改善不代表新版全曲已渲染验收。
