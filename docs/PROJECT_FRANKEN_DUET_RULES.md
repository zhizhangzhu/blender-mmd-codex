# 《フランケンシュタインの怪物》双人作品专属约定

2026-11-22 从 `AGENTS.md` 迁出（原文快照：[AGENTS.before-slimming.md](history/2026-11-22/AGENTS.before-slimming.md)）。处理本作品时与 `AGENTS.md` 同等必须遵守；作品现行事实（候选路径、SHA、状态）只以 `catalog/current_state.json` 为准，本文只保存规则与已作出的用户决定。

## 当前范围与冻结源

- 猪猪 2026-11-20 明确要求继续在当前 GooEngine 优化双人渲染与舞台。本任务使用 `goo-v1` 独立副本；829f 冻结源（SHA `829f2d88827320c48a19ed76df4dc70af495455e4a660769c2bb53fe461caa69`）只读保留。进展读 `current_state.goo_artdirection_request` 与 [GOO_DUET_ARTDIRECTION_2026_11_20.md](GOO_DUET_ARTDIRECTION_2026_11_20.md)；不要因旧“等待评价”停止已授权开发，不在失败保存目录冒称新候选完成。
- 当前候选的检视用 `presets/benches/goo-duet-artdirection-candidate-v1.json`，其中 expected 是保存后的值，不能重复套用原源配方。原 829f 及旧 5c 诊断均保留。
- 2026-11-19 的“后续试作默认官方 Blender 5.3 独立副本、人物套 5.3 作者 shader、其余复刻 Goo”决定，自 2026-11-22 起降为对照／备选路线（见 [GOO_RUNTIME_POLICY.md](GOO_RUNTIME_POLICY.md)）；不自动恢复视频、新物理或眼透。
- **眼透已搁置，额外刘海透明关闭。字幕保留黑边和投影。** 伊科尔错误发骨烘焙造成持续错位，现静帧恢复绑定发型；不能称新的头发动态通过。

## 素材与项目

- 阿克西妮娅→Full HimeTanaka、伊科尔→Full HinaSuzuki；横屏 16:9，空为历史角色。两人材质／表情分别映射，保留原生相对站位、既有とっとこ相机；暂缓全曲运镜校正。
- 素材根 `E:/tools/franken`，优先 PMX＋原生 VMD。换动作不能复用旧角色或旧动作的物理烘焙。
- 保留 paierer「赫斯珀利德斯之馆-礼堂」，主题雪＋婚礼＋爱，不主动换原创舞台。Aiko 宮殿禁止 Blender 成片，排除；雪韵仙庭等级限制不绕过。
- BGM 固定 `D:/codex/output/Franken-Duet-Full-Audio-v1/HIMEHINA - フランケンシュタインの怪物.flac`，198.3158125 秒、96kHz／24bit 双声道；不得换伴奏／MP3。加入音轨不等于卡点完成。

## 角色与材质专属事实

- 阿克西妮娅已有脸 Lightmap/SDF，伊科尔没有已验证脸 SDF，不交换模板。HM／HN 按实际节点语义与色彩空间核对。白布提亮保护金青图案，不以最终脸亮度下限抹掉阴影。
- 伊科尔白衣与亮肤色须保留层次，避免局部版本人物过亮（用户 2026-11-17 反馈）。
- 蓝金细弧保持隐藏、曲线原数据保留。旧建筑 probe 不因局部材质修改而自动重烘。
- 旧袖／衣发仅 4139–4441 有界验证；保留局部 corrective 与非零接触，不称零穿模／全身纯物理。
- Crypto 同时包含 `阿克西妮娅2_mesh` 和 `Ikhor | mesh | Ikhor_mesh`，核逐人头身 ROI；旧漏伊科尔缓存不复用。Glow 变更后 beauty 缓存也须匹配。

## 参考与资料

- 短链 `https://b23.tv/B55DoZl` 尚未确认为指定作品。
- 九套 MME 原包重点段落已读，不等于 49 位作者技术全掌握。
- 用户此前跳过的视频输出后检查只适用于其明确范围。
