# 本机 Blender MMD 环境

配置日期：2026-10-26。真实路径保存在未提交 Git 的 `.blender/local-setup.json`；本仓库的 portable 环境可以搬迁，但搬迁后需要更新 Codex MCP 的绝对执行路径。

| 组件 | 本机版本 | 用途 |
| --- | --- | --- |
| Blender | 4.5.15 LTS | 场景、动画、材质、物理、渲染与视频输出 |
| MMD Tools | 4.5.14 | PMX/PMD、VMD、VPD 导入导出与 MMD 数据编辑 |
| Blender MCP（newo-ether） | 1.19.0 | Codex 与正在运行的 Blender 之间的工具桥 |
| MMD Tools Append | 4.5.13 | 资源目录、材质、骨架和场景辅助 |
| Blender MMD Codex Add-on | 0.1.0 | 本项目原有诊断和参考视频功能 |
| 本项目 Codex Skills | 插件版本 0.2.1 | MMD 制作流程与文字参考 |

Blender 位于 `portable_blender/blender-4.5.15-windows-x64/blender.exe`。其 `portable/` 内保存偏好和扩展，不依赖把 Blender 安装进系统目录。MCP 服务及独立 Python 环境在 `.blender/mcp-source/.venv/`；所有运行环境目录已被 Git 忽略。

## 使用

1. 打开该 portable Blender。BlenderMCP 默认自动连接，可在 3D 视图侧栏 N → BlenderMCP 查看状态。
2. Codex 用户配置已注册 `blender_mcp` 服务。修改服务后重启 Codex，以载入新增 MCP 工具；安装的文件系统 Skills 在后续轮次发现。
3. 可直接要求：“使用 `$mmd-production`，导入这些 PMX、人物 VMD 和相机 VMD，输出短预览。”若没有素材，可以先要求整理某角色/歌曲的配布候选与条款。
4. 多个 Blender 窗口并存时按作品文件精确选择实例。MCP 工具不可见时不要把仅写完脚本说成已操作打开的场景。

已安装 `blender-mcp` 通用 Skill，以及本项目七个 Skills：`mmd-asset-search`、`mmd-production`、`vmd-workflow`、`mmd-model-check`、`mmd-video-reference`、`blender-setup`、`troubleshooting`。项目 Skill 的用户级副本由 `~/.codex/skills/.blender-mmd-local-install.json` 记录来源和文件散列；修改仓库后应同步相应副本。

## 安装来源与配置

MCP 来源固定为 [newo-ether/blender-mcp v1.19.0](https://github.com/newo-ether/blender-mcp/tree/v1.19.0)，提交 `ced81a5a220dd01240e67df2453dffeb8fb51daa`。发布附件下载超时，因此从该固定 tag 的源码构建 Blender Extension，并在独立 venv 中安装服务。没有将源码构建描述为通过发布附件的 SHA256SUMS 校验。

MMD Tools Append 来源固定为 [MMD-Blender/blender_mmd_tools_append v4.5.13](https://github.com/MMD-Blender/blender_mmd_tools_append/tree/v4.5.13)，提交 `d80a7e1fe52efaa597a6934dad37752c9f995af3`。从 Git LFS 完整取得源文件，再用 Blender Extension build 构建。其发布流程额外生成 `asset_jsons/` 并复制 LICENSE；本机也补齐这两项，再加载目录。

Codex 原配置已在同目录备份。只新增 `blender_mcp`：启动独立环境的 `blender-mcp.exe`，工作区指向本仓库，连接本地实例，设置 `BLENDER_MCP_DISABLE_TELEMETRY=1`、UTF-8 输出及较长工具超时。没有配置需要 API Key 的模型生成服务。

Append 目录实际载入 178 条：164 个 MMD 模型、5 个 MMD 动作、3 个 Blender 模型、6 个 Blender World。这是元数据目录，不保证每条原始下载仍有效，也未验证它能覆盖任意歌曲的镜头配布。目录已关闭每次启动自动更新；查找资源时可显式更新。下载资源解压根位于本项目 `.blender/append-assets/`，实际作品建议放进已忽略的 `mmd_projects/`。

## 已观察到的边界

- 本项目自身没有重写 PMX/VMD 解析器；制作使用 MMD Tools 已有能力。通用 MCP 和 Skill 并不自动解决所有模型的权重、材质、穿模或物理。
- MCP 1.19.0 任意 Python 工具在整理“已删除的旧对象”时可能访问失效的 RNA，导致脚本已生效但工具返回错误。本流程采用独立新 Scene，保留已有对象，并在重试前回读状态。详见 troubleshooting Skill。
- Append 在 Blender 后台进程关闭时会出现缓存析构 `NoneType ... path` 警告；本机已能加载插件与资源目录。此警告尚未修复，不能据此推断实际资源下载、物理转换或用户作品全部正常。
- `scripts/blender_detect.py` 当前不搜索本仓库的 portable 子目录。明确传入 `.blender/local-setup.json` 中的 Blender 路径，避免重复安装。
- MMD Tools 旧 Wiki 的 Blender 2.x 界面和安装方式已过时；Skill 的参数以当前 RNA 和 4.5.x 源码核对。

## 验证方式

安装探针检查真实版本和持久启用状态。MCP 验证使用独立隐藏 Blender 进程和原创几何人物，验证 PMX、人物 VMD、相机 VMD、相机关键帧修改、保存、渲染及视频编码/解码。它不包含第三方模型、头发/裙摆刚体、口型或音频；这些需要用具体作品单独检验。

详细结果见本次交付报告与实际 `.blend`/视频。通过技术验证不代表真实角色素材已达到发布质量。

本次验证结果：MCP 63 个工具初始化通过；原创 PMX 与人物/相机 VMD 导入、相机修改、保存和回读通过。60 帧、30 fps、480×270 的两秒 H.264 视频已编码并解码，代表帧颜色对比平均 RGB 差异 0.003717。Skill 格式、引用、安装副本和无关 Codex 配置保留检查均通过。实际 Codex 桌面工具列表仍需重启客户端载入。

2026-10-27：根据用户提供的动作检索 v4.1 提示词增加独立 `mmd-asset-search`，支持模型、人物动作、表情口型与镜头。原始提示词私有备份在 `.blender/skill-sources/`；检索技能无需新增 API 或软件依赖。真实网页核对涉及模型、官方人物动作和已结束配布的镜头；未下载这些素材包，也未验证包内 README 或真实导入。
