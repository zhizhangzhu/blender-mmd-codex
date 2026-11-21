# 良宇喵喵喵教程：半兰伯特、分通道控制与当前实现

研究日期：2026-11-09。用户指定视频：[BV18DJC6dE1S](https://www.bilibili.com/video/BV18DJC6dE1S/)，作者良宇喵喵喵，标题为《小白向！一个视频讲清楚三渲二MMD的流程分享！》，站点时长 17:01。

## 实际读取范围

已读取投稿公开简介、作者置顶评论、接口可返回的热评、公开章节；取得匿名允许的 640×360 播放版本，实际解码并抽取 30 张总览帧和 13 张关键章节帧。没有取得字幕文件，没有声称完整听写旁白，也未从低分辨率画面猜出所有节点参数。

来源与画面证据位于 `D:\codex\output\MMD-Quality-Lab-v1\half-lambert-reference`，其中 `overview/contact-sheet.jpg` 为全片时间分布总览，`keyframes` 为选定演示帧。此匿名版本的 OpenCV 元数据为 30602 帧、约 30.0015 fps / 1020.017 秒，与站点整数时长有差异，不将其当作原始母版精确时间基准。视频 SHA-256：`9acdd2948cd68e6848931fed997875cd255002382480704f18bd4bbce631ff37`。

公开评论 API 当前返回作者置顶和三条热评；其他页返回空。站点评论计数远多于这些，不能称为读完全部评论。评论中关于贴图、RGB 灯和描边的反馈只能说明观众关注点，技术判断仍以可见演示、原作者资料和本机测试为准。

## 简介和评论的资料入口

简介说明资料链接放在评论区。作者置顶列出 Blender、MMD Tools，并推荐 MMD、PBR、Blender 基础和三渲二方向的创作者；其中三渲二入口为 [CG DASH](https://www.youtube.com/@CGDASH)、[神代溪久奈](https://space.bilibili.com/37949446)。PBR 方向列 [RedialC](https://space.bilibili.com/11831050) 和[叫我白菜就好啦](https://space.bilibili.com/175058194)。这些是作者推荐线索，本轮没有把其所有视频当成已看完。

置顶 MMD Tools 指向旧仓库下载页；本机继续使用已经验证的扩展 `bl_ext.blender_org.mmd_tools`，不因教程入口不同而再启用旧 `mmd_tools`。

## 从实际帧中学到的内容

| 时间/章节 | 实际观察 | 当前工程的对应处理 |
| --- | --- | --- |
| 2:17–3:57 | 区分颜色、金属、粗糙度和法线等贴图用途 | 不把颜色贴图、球面贴图当成完整 PBR 贴图组；新材质响应需检查模型实际提供的数据 |
| 3:57–6:50；5:25 帧 | 先做 Shader to RGB 的基础卡渲，再分离颜色通道控制光照；示例绿灯用来控制高光 | 理解 RGB 可充当控制信号，不是要求最终角色被红绿蓝染色；现有分区 NPR 保留独立颜色和效果遮罩 |
| 6:30 / 6:40 帧 | 半兰伯特演示中出现法线/向量运算与光照控制；字幕说明可关联灯的旋转数据 | 本轮独立实现半兰伯特响应与分材质梯度；仍沿用本项目原有的灯位置驱动，没有冒称复制了视频的旋转控制器 |
| 约 10:20 | 面部直接套普通材质出现难看的凹陷阴影 | 脸/眼线/眼睛独立处理；局部 AO 排除脸和眼睛，法线只在副本上做受控试验 |
| 约 12:05 | 头发部分使用法线编辑相关修改器 | 法线设计属于材质之前的输入；仅改色带和灯光并不总能改善明暗边界 |
| 约 12:35 | 光照贴图参与角色的着色控制 | 这是需要具体贴图语义和 UV 的方案，不能把当前模型任意一张图猜成同类控制贴图 |
| 13:32 后；14:00 / 15:10 帧 | 继续调颜色、眼透、辉光，并解释不同版本的入口变化 | 本机 5.2 使用已验证的合成节点/AOV 泛光；不照搬旧界面的辉光开关或旧教程节点名称 |

这是按代表帧阅读到的结构，未将全片每个操作及不可读的小参数还原。贴图/法线/灯光控制/分区着色/后期是一起工作的，不能把整套效果归功于一个半兰伯特公式。

## 半兰伯特为什么适合继续研究

令 `d = dot(normalize(N), normalize(L))`。普通 Lambert 常取 `max(d,0)`；常见线性包裹响应取 `h = clamp(0.5*d+0.5,0,1)`。Valve 的原始技术资料还将此结果平方；它是一种为形体可读性设计的非物理响应，不是光线追踪或 PBR 开关。[Valve：Shading in Source，8.4.4](https://cdn.fastly.steamstatic.com/apps/valve/2006/SIGGRAPH06_Course_ShadingInValvesSourceEngine.pdf)

本轮显式提供 `exponent`：1 是线性版本，2 对应平方响应。之后再接分材质暗部/中间调/亮部梯度。`exponent=1` 不被写成 Valve 平方公式的精确复刻，也未宣称与视频所有节点完全一致。[Riot 的 Gradient Lambert 说明](https://www.riotgames.com/en/news/valorant-shaders-and-gameplay-clarity)同样强调艺术梯度控制明暗与过渡的价值，可作为后续完善方向。

实际实现：`scripts/mmd_half_lambert.py`，参数 `presets/quality/half-lambert-v1.json`。在当前已验证的 `N·L` 与色带之间加入重映射/指数节点，色带扩展为三个区域；保留 MMD Color/Alpha、贴图/球面、透明、局部高光和灯位置驱动。它是现有风格可选的光照响应模块，不新增一个作者风格标签，也不覆盖两类风格的 v1 参数。

半兰伯特会改变亮暗分布，未经校准直接替换可能洗平暗部。当前给皮肤、头发、布料等分别设置梯度；AO 不负责全局压黑，灯光响应也不直接代替投影、皮肤散射或金属反射。

## 本轮真实试验与文件

`D:\codex\output\MMD-Quality-Lab-v1\half-lambert-v001`：

- `baseline`：原有 Gosari 方向基线。
- `half_lambert`：仅改变光照响应及分区梯度。
- `half_detail`：半兰伯特 + 受控面部法线 + 局部 AO；没有给整个人物统一套物理高光。
- `half-lambert-comparison.jpg`：原版/两方案在源帧 421 和 601 的同姿态对照。

每方案实际渲染 421/540/601 三帧，检查顶点位置哈希和各帧全部姿态骨骼矩阵哈希均保持；静帧表明差异集中于发丝/衣料明暗和细微接触关系，没有据此宣称达到电影级或参考作者同等质量。法线单项在本模型上的收益很小，不自动晋升为所有风格默认。

动态样片和最终解码检查位于 `D:\codex\output\MMD-Quality-Lab-v1\half-motion`，以其中报告为准；这轮仅验证四秒片段，尚未重制二十秒成片。画幅仍是竖屏，不将它冒称已验证了新的横屏镜头；现有横竖屏 package 继续保留。

复现静帧：

```powershell
& 'E:\tools\Blender Foundation\Blender 5.2\blender.exe' --background `
  'D:\codex\output\MMD-Style-Presets-v1\clips\gosari-portrait-v1\scene\typography-source.blend' `
  --disable-autoexec --python-exit-code 1 --python scripts/mmd_quality_lab.py -- `
  --output-dir 'D:\codex\output\half-lambert-new' `
  --preset presets/quality/npr-detail-lab-v1.json --variants baseline half_lambert half_detail
```

导入已含 File Output 的派生工程时，必须先移除或重定向指向旧目录的输出节点；本轮在静帧实验与新渲染入口中均处理，避免试验覆盖已交付的 PNG 缓存。

更多插件、AO、金属和体积光验证见 [QUALITY_LIGHTING_LAB.md](QUALITY_LIGHTING_LAB.md)。
