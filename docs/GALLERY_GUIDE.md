# 帧间资料库：使用与维护

2026-11-13更新：状态表为 `catalog/current_state.json`，构建时同步最新用户美术反馈，避免历史打包器覆盖成旧评价；motion标签改为“技术样片”。新增综合指南、来源账本与制作关卡，JSON账本及状态文件随下载目录打包。整理前快照不混入顶层知识卡片。新构建须核对链接、下载和现行状态；若浏览器连接模块不可用，仅声明静态检查覆盖范围，不沿用旧浏览器通过报告。

## 使用

双击 `D:\codex\output\MMD-Atlas-v1\index.html` 或同目录 `打开预设库.cmd`，无需服务器或联网。整个目录可移动，预览／视频／文档／JSON 都使用相对路径；大体积 Blender 工程保持原位置，详情可复制工程路径。

- 画廊支持关键词、类别、风格、画幅和状态组合筛选。每张卡片可收藏、查看详情、加入两项对照。
- 详情中能播放真实样片，查看适用条件和限制、阅读关联笔记、下载 JSON。存在已验证命令的项目提供复制操作。
- “效果对照”保存同机位受控实验，用拖动分界看变化；任意两项另用并排比较，保留完整画幅。
- “知识地图”可站内阅读全文；搜索匹配标题和正文。文内已收录的 Markdown 链接在站内跳转。
- “参数组件”收录全部 `presets/**/*.json`，可以展开原始参数或下载。
- 收藏保存在当前浏览器，可在“我的收藏”导出／导入 JSON。浏览器限制剪贴板时显示可手动复制的文本框。按 `/` 聚焦搜索；模态层支持 Escape 和关闭按钮。

## 更新内容

编辑 `catalog/library.json`：

1. `entries` 为专题预设／实验，填写唯一 id、分类、风格、画幅、验证状态、真实图片或视频路径、关联文档、参数文件、适用条件、验收记录和限制。
2. `style_packages` 对应六个已有风格组合，构建器读取各 package 的 render／post／typography 引用；不要再写一份重复参数。
3. `comparisons` 的 before／after 必须是真正可比的原始渲染，尺寸一致。不要用不同机位冒充受控 A/B。
4. `knowledge_groups` 为文档的唯一主分类；新文档未分配时自动进入维护类。所有文档会重新嵌入网站。
5. `roadmap` 记录尚待加强的问题、当前依据和明确验收条件。

新增底层参数放进既有职责目录；改变预设另存新 id／版本。第三方预设和源素材继续留在用户素材目录，仓库只存自己的配置、学习总结与来源说明。

## 构建

本机构建依赖位于 `D:\codex\temp\mmd-gallery-tools`：Markdown 3.9、bleach 6.2.0；Pillow 为现有环境。Playwright 1.60.0／greenlet 3.1.1 仅用于网站验收，不是浏览网站的依赖。临时依赖丢失时可用 `python -m pip install --target <临时目录> Markdown==3.9 bleach==6.2.0 Pillow` 重新准备；不要安装到 Blender。

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = 'D:\codex\temp\mmd-gallery-tools'
python scripts/build_gallery.py --output-dir 'D:\codex\output\MMD-Atlas-v2' --temp-dir 'D:\codex\temp\MMD-Atlas-v2'
```

输出目录默认要求全新。开发中可加 `--refresh` 更新同一个已由本项目生成、带正确标记的目录；不递归删除任何目录。预览从真实渲染转为 WebP；视频仅复制已有短样片，不启动 Blender。没有图像的样片由 FFmpeg 抽取真实帧。`build-manifest.json` 记录素材来源与 SHA-256，不修改任何源素材。

纯静态运行使用本地 `data.js`，没有 fetch、CDN、外部字体、账号、遥测或后端。Markdown 在构建时转换并清理 HTML；浏览时无需 Python。页面不会执行复现命令，也不会自动打开或保存 Blender 工程。

## 设计与验证

用户指定参考为 [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)。已实际读取 Runway 与 Linear 的 DESIGN.md，按本任务重新设计；来源版本、配色、排版及交互规则见 `site/DESIGN.md`。

浏览器验收脚本 `scripts/verify_gallery.py` 应覆盖 file:// 直开、实际媒体、筛选、详情、收藏持久化及导入／导出、对照、参数下载、文档路由、浅色／移动端、键盘与错误日志。结果和截图留在交付目录 `qa/`，不能仅凭 HTML 文件存在就声称功能通过。

2026-11-11 首版实际验收：15 项预设／实验、31 份参数、35 篇笔记、3 组受控对照。独立无头 Chrome 157 已执行八组浏览器检查，包含真实 1920×1080 五秒视频播放与 JSON／收藏下载；页面脚本错误和远程请求均为零。实际查看了深色／浅色桌面、手机、样片详情截图。后续改动需按影响范围复核，不把此结果永久套用于新版本。
