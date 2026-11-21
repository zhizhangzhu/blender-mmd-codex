# B站字幕：合法采集后的离线整理

2026-11-13。入口：[ingest_bilibili_subtitles.py](../scripts/ingest_bilibili_subtitles.py)。本工具只整理用户或已授权浏览器合法保存的字幕 JSON，不负责联网采集。初版提供合成输入回归测试；**尚未对本轮真实B站全文验证**。工具存在、测试通过或取得字幕 URL，都不能写成“已读取本轮教程全文”。

## 先区分拿到了什么

在正常、已授权的视频页面选定分P与字幕轨，按页面提供的权限启用字幕。若通过 F12 Network 或正式浏览器工具查看响应，应只保存对应字幕正文 JSON。不要导出整个 HAR、Cookies、账号 profile 或请求凭据；无需把 signed URL 交给离线整理器。

- **URL／轨道清单**：只证明发现了某条字幕线索。没有 `from`、`to`、`content` 正文，不能当作全文。
- **正文 JSON**：能按条校验时间与文本。仍需核对选定视频、分P、轨道、首末片段及中间内容。
- **播放核对**：用实际声音与画面核实识别错误、遗漏和术语，记录核对范围。自动识别文本不直接等于作者原话，字幕也不能代替逐镜观看。

页面需要登录、等级、付费或其他作者限制时沿正常权限操作，不绕过。这个脚本不读 Cookies、不运行 JavaScript、不访问网络、不跟随字幕 URL，也不自动下载带签名的链接。

## 支持的本地输入

输入文件为 UTF-8 JSON，可带 UTF-8 BOM。接受以下明确容器，每次只处理一轨：

| 容器 | 示例 |
| --- | --- |
| 根数组 | `[{"from": 0, "to": 1.5, "content": "合成字幕"}]` |
| `body` | `{"body": [...]}` |
| `data.body` | `{"data": {"body": [...]}}` |
| `subtitle.body` | `{"subtitle": {"body": [...]}}` |
| `data.subtitle.body` | `{"data": {"subtitle": {"body": [...]}}}` |

不会在任意对象中猜测正文位置；出现多个支持的正文容器会停止，须先分别保存。空数组、URL清单、HTML、JavaScript、重复 JSON 对象键或格式错误均不能成功导出。多个字幕轨道分别指定新目录。

每条必须有数值型 `from`、`to` 与字符串型 `content`。时间必须有限、非负且 `to > from`；布尔值与数值字符串不作时间使用。任意条无效时整份导出停止，不把其余条伪装成完整成功。只含空白的文本会保留，并在报告中列出。

## 命令与产物

在仓库根目录运行，Python 仅使用标准库。输入与临时研究文件放 `D:\codex\temp\`，完整字幕产物放用户明确指定的 `D:\codex\output\` 新目录。脚本拒绝仓库内的输出位置；任何已存在的输出文件或目录都会报错，没有覆盖选项。

```powershell
python -m scripts.ingest_bilibili_subtitles `
  --input 'D:\codex\temp\bilibili-selected-track.json' `
  --output-dir 'D:\codex\output\Bilibili-Subtitle-Study-v1\selected-track-v1' `
  --source-url 'https://www.bilibili.com/video/BV1Synthetic/?p=2' `
  --source-label 'AI字幕；实际轨道待核对' `
  --expected-duration 123.4
```

示例视频编号与时长是占位数据，运行时换成实际选定页面与分P时长。`--source-url`、`--source-label`、`--expected-duration` 均可省略；不传来源 URL 不影响正文整理。来源 URL 仅接受 B站 HTTPS `/video/` 页面和可选的正整数 `p` 参数，拒绝 signed subtitle URL 与其他查询参数，片段定位信息不保存。时长仅用于报告末尾间隙或超出范围，不能授予“完整”状态。

| 文件 | 内容与用途 |
| --- | --- |
| `subtitles.normalized.json` | 仅保留标准化的 `from`／`to`／`content`、来源与 schema 版本。原识别文字逐字保留，顺序与重复条保持。 |
| `subtitles.srt` | 可供字幕播放器使用的显示导出。按原输入顺序编号，不自动重排。 |
| `subtitles.md` | 按条带时间码的阅读稿，文本使用代码块，避免识别内容变成 Markdown 或 HTML 指令。 |
| `report.json` | 原输入字节数、SHA-256、正文容器位置、时序统计、导出规则和待核对事项，不含整份正文。 |

原输入 SHA-256 对文件的原始字节计算，包含 BOM 和空白差异；不会把原 JSON 中其他账号、请求或页面元数据复制到产物。脚本不修改原输入、不另存原始响应。CLI 日志只打印产物路径、条数与 SHA，不输出全文，避免把整份字幕重复送入上下文。

SRT 采用毫秒四舍五入（半毫秒向上）。原本有正时长、舍入后为零的条目只在 SRT 中延长到 1ms，并在 `srt_export.extended_to_one_millisecond_input_indices` 记录；标准 JSON 的时间不变。SRT 的 CRLF／CR 统一为 LF，其余识别内容保留。原文空行会在 `statistics.srt_content_with_blank_lines_indices` 标记，因为部分 SRT 播放器会将空行误作字幕块结束；遇到这类输入，以标准 JSON 为保真依据，另行核实播放表现。

## 怎么读报告

所有输入条目原样保留，统计时才另建按起始时间排序的视图；不会用排序掩盖采集问题。报告索引从 **1** 开始，对应原输入顺序。

- `input_first_start_seconds`／`input_last_end_seconds` 是原序列首条与末条；`minimum_start_seconds`／`maximum_end_seconds` 是整轨时间边界，乱序时两组值可能不同。
- `start_regression_input_indices` 列出起始时间比上一输入条更早的位置；`exact_duplicate_groups` 列出时间与文本均完全相同的重复条索引，重复条不删除。
- `initial_gap_from_zero_seconds`、`internal_gaps` 与可选的 `trailing_gap_to_expected_seconds` 供人工定位检查。静音可能形成正常间隙，间隙本身不等于遗漏。
- `covered_seconds` 是各时间区间并集的总秒数，`coverage_span_seconds` 是最早到最晚边界跨度；重叠时不累计成多倍覆盖。
- `overlap_witnesses` 对每条与先前覆盖重叠的字幕记录一个证据：与此前结束最晚的条目比较。它覆盖所有这类后续条目，但**不是所有重叠配对的穷举**。边界恰好相接不算重叠。
- `end_beyond_expected_seconds` 提示结束时间超出指定分P时长，可能需要核对分P、时长或轨道。不会自动截断。

`completeness` 始终为 `unassessed`。首条从0开始、末条等于视频时长、没有间隙，都不能证明全部发言已识别。至少核对视频ID／分P／轨道、开头／结尾与内部间隙，再按任务所需记录实际播放核对范围；未核对内容不得称完整转写。

完整第三方字幕只留在明确的用户输出目录，仓库研究文档写自己的总结、来源、时间码和短引文，不提交整份字幕或完整教程。完成读取后，再把相关技术假设转换为本工程的可控实验；识别到一个参数或术语，不等于本机实现或美术验收通过。

## 合成测试与验证边界

合成测试位于 [test_subtitle_ingest.py](../tests/test_subtitle_ingest.py)，不依赖B站、浏览器或外网，所有正文均为测试自写。主线程可运行：

```powershell
$env:CODEX_TEST_TEMP_DIR = 'D:\codex\temp'
python -m unittest tests.test_subtitle_ingest -v
```

临时根目录须已存在；每项测试用独立子目录并清理。测试覆盖明确容器、URL清单拒绝、无效时间整份失败、重复／乱序保留、重叠与区间并集、哈希、原文保真、毫秒舍入、禁止覆盖、禁止仓库输出、来源 URL 限制、异常 JSON 与简短日志。**合成测试通过只验证整理逻辑；不证明本轮真实字幕已采集、完整或准确。**
