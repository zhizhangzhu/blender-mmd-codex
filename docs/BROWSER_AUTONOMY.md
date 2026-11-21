# 浏览器自主使用：连接与验收

最新复测：2026-11-13。**内置浏览器和本地Chrome都曾成功读取B站正文，但连接仍不稳定，字幕全文尚未取得。** Chrome扩展与native host已确认正常，用户已授权后续常规浏览器操作，不需要再按旧记录要求补权限或重装。

## 最新实测，优先于下方历史记录

- 随包已更新为 `26.1111.21308`。内置浏览器新建B站标签成功，实际读到登录首页、观海子《亲亲小狐狸》简介、良宇喵喵喵教程简介，以及Yume_Lyra基础三渲二教程的简介和单条字幕。没有读到完整评论或字幕全文。
- 通过正式CDP入口尝试网络监听时超时，之后内置浏览器绑定也再次超时。用户明确要求先停内置浏览器，改用本地Chrome；后续优先遵守这一选择。
- 沙箱外运行随包官方只读检查：Chrome已安装；native host名称、注册路径与允许扩展origin均正确；Codex扩展在 `Profile 2` 中已安装、注册且启用。此前的沙箱拒绝访问不能用来判定组件缺失。
- 当时Chrome进程未运行；按用户授权运行官方 `open-chrome-window.js --browser chrome` 后，Chrome扩展出现在浏览器清单。用正式Browser API创建受控标签并读取DOM，成功取得良宇喵喵喵教程的标题、简介与播放器状态。
- 后续控制已有标签仍遇到 `Debugger unattached`，因此不能标记“持续稳定可用”或“已经抓到字幕”。没有修改native host、注册表、扩展权限或安全设置。
- 发现研究标签自动连播后，已通过正式management接口关闭两个由代理创建的标签，并确认它们不再出现，以停止该流量。它们是临时研究标签，可通过Chrome正常的恢复关闭标签功能找回。

用户明确要求高效、省token和流量：默认文字学习，打开视频先暂停并核实状态，按需低清看图，完整字幕只私人缓存一次。流程见[高效学习](EFFICIENT_RESEARCH_WORKFLOW.md)，字幕整理见[离线工具](BILIBILI_SUBTITLE_WORKFLOW.md)。

## 下方为早先故障记录，已被最新实测覆盖

早先状态为“只能发现内置标签、尚未接通Chrome”。旧安装／权限检查步骤仅作排查历史，**不适用于本机已确认正常的最新安装状态**。版本变化与一次读取成功同时发生，不能据此断言某个升级修复了具体bug。

## 本轮实际结果

用户已授权优先使用内置浏览器，必要时通过 computer use 使用电脑上的 Chrome。用户在内置 B 站登录成功与代理能控制该标签是两件独立的事，不需要因此退出或重新登录现有账号。

- 最新主线程 CUA `getState` 能发现 B 站首页的一个标签：浏览器 `2`、标签 `2`、URL `https://www.bilibili.com/`。
- 随后 `getTab({url: 'https://www.bilibili.com/'}, {browser: '2'})` 等待约 30 秒后超时并重置运行环境。**未读到页面主体，也未取得新的简介、评论、字幕或教程内容。** 本阶段已按 CUA 要求提交完成摘要。
- 本轮 Chrome 后备请求返回 `Browser is not available: chrome`。当前 CUA 的原生电脑 API 明确禁用，因此不能靠桌面点击替代缺失的浏览器连接。
- 更新后的随包浏览器版本是 `26.1106.51428`。该目录的 `scripts/browser-client.mjs` 与 `scripts/browser-service.mjs` 都存在。旧 `26.1103.32239` 缺文件属于历史故障，不能继续用它解释当前故障。
- 更新后的 Node 浏览器运行时曾初始化成功，但当时发现列表为 `[]`，选择 `iab`、`chrome` 均不可用。这是当时该运行时的结果；晚于它的 CUA 发现结果已恢复到一个标签，不应混写成“现在没有浏览器”。
- 只读程序检查确认 Chrome 安装于 `C:\Program Files\Google\Chrome\Application\chrome.exe`，版本 `157.0.8103.51`。此前一次进程检查未发现 Chrome；它不是持续状态。

沙箱内官方 `check-native-host-manifest.js --browser chrome --json` 报告对应注册键和 manifest 不存在。由于后续沙箱外核对被中断，该结果仅作为**待复核线索**，不能断言用户没有安装扩展。官方进程检查中的 `tasklist` 被沙箱拒绝，也不能据此判断 Chrome 未运行。未读取 Chrome profile、Cookies、密码或账号数据；未安装、卸载扩展，未修改注册表、安全设置或偏好。

## 用户一次性连接检查

以下来自 [OpenAI 的 Chrome 连接说明](https://learn.chatgpt.com/docs/chrome-extension.md)，只需检查实际呈现的入口：

1. 在桌面应用打开 **Settings → Computer Use → Chrome**；若 Chrome 折叠在 **More browsers** 下，先展开。
2. 若显示 **Install**，按应用提供的流程安装插件和浏览器扩展，并由用户查看、确认浏览器权限提示。若已显示 **Manage**，不要重复安装。
3. 打开装有该扩展的 Chrome 用户窗口，在其中打开 B 站；只有该窗口确实需要时才登录 B 站。内置浏览器的登录状态不代表 Chrome 已登录。
4. 在聊天中选择或提及 **@Chrome** 的 B 站标签，让代理进行下面的最小复测。

如果已是 Manage 仍无法连接，可依官方说明重启浏览器和桌面应用后复测。若诊断最终确认原生连接组件缺失，应由应用设置中的正式安装／重装流程修复；代理不自行复制模块、写注册表或制作 native host。当前没有可用的原生电脑控制入口，代理也不能在用户界面中替用户点通这一步。

用户授权使用浏览器，允许后续在连接正常时导航、搜索、读取教程；它不使代理获得自行授予扩展权限或更改安全设置的能力。不要为此导出 Cookies、复制账号 profile、开启远程调试端口或建立替代登录会话。

## 最小复测与成功标准

连接调整后只做一次有界验证：

1. 重新获取可用浏览器清单，选择实际存在的 `iab` 或用户指定的 `chrome`，不凭旧标签 ID 推断连接。
2. 读取 B 站标签的可见页面主体，记录页面标题、URL 和读取范围。
3. 导航到 [Gosari542](https://space.bilibili.com/3493265460431074) 或 [观海子](https://space.bilibili.com/17466365) 的页面或具体作品，并实际读取简介或一篇可用教程。
4. 若成功，记录所见内容与实际来源；只有看到字幕／转写才称已取得字幕。若仍超时，记录失败阶段并停止反复初始化，不以网页搜索或本地参考代替“登录浏览器已恢复”。CUA 阶段结束按工具要求提交一次完成摘要。

发现标签通过、页面读取通过、导航通过、研究内容通过应分别记录。当前只通过第一项；MMD 制作可继续使用本地参考和公开可读资料，浏览器连接失败不代表制作任务完成。

## 只读诊断边界

当前随包官方故障说明允许检查运行状态、安装路径与 native host。需要时由主线程在正确权限上下文运行以下命令，而不是子代理反复等待审批：

```powershell
node scripts/check-native-host-manifest.js --browser chrome --json
node scripts/chrome-is-running.js --browser chrome --json
```

工作目录为 `C:\Users\Administrator\.codex\plugins\cache\openai-bundled\browser\26.1106.51428`。版本号随应用更新变化，先确认实际目录。未做扩展 profile 扫描；扩展是否安装和启用应先由 Settings／Chrome 可见 UI 确认。诊断失败不得触发自行安装 host 或修改配置。

官方阅读范围：[Chrome 连接说明](https://learn.chatgpt.com/docs/chrome-extension.md) 的连接与故障排查部分；[浏览器说明](https://learn.chatgpt.com/docs/browser)；随包 `bootstrap-troubleshooting.md`、`chrome-troubleshooting.md` 与只读诊断脚本。以上用于连接排查，**不算本轮新学到的 MMD 教程**。结构化证据见 [BROWSER_ACCESS_VALIDATION.json](research/BROWSER_ACCESS_VALIDATION.json)。
