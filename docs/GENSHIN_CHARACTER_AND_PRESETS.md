# 原神角色着色、下载预设与新版礼堂五秒样本

2026-11-11 后续复核：早期 RNA 矩阵分量驱动与真实头部朝向不一致，且本机 Face Factor 适配采用 incoming 光向；骨骼／相机对照通过不能证明 shader 空间正确。已修复并完成新动态验收，后续优先读 [受光与颜色流程](LIGHT_SPACE_AND_COLOR_PIPELINE.md)，不照抄旧驱动。

实测：2026-11-10 至 11。猪猪要求导出新版礼堂双人五秒样本，并学习原神角色渲染；指定参考 festivities，同时提供 `D:\BaiduNetdiskDownload\三渲二预设`。本轮完成 **1920×1080、60fps、300 帧、5 秒**，不是双人全曲成片。

样本：`D:\codex\output\MMD-Ray-Hall-Genshin-Revision-v1\sample-5s-v1\Aether_Duet_5s_REVIEW.mp4`。

工程：同根目录 `production-v3\Franken_Duet_Reference_Genshin.blend`。素材仍使用阿克西妮娅 Hime／空 Hina、用户指定的原声 FLAC，正式相机轨迹与烘焙物理不变。

## 从模型实际具备的数据出发

原神模型不等于原游戏 Shader 和全部控制图也已包含。实际目录检查与材质检查发现：

| 模型 | 已有数据 | 本轮采用 |
| --- | --- | --- |
| 阿克西妮娅 | `Avatar_Lady01_Tex_FaceLightmap.png`，NPC 脸颜色、头发／身体／服饰 Lightmap、MMD 球面与叠层贴图 | 使用随模型 FaceLightmap 做头部朝向驱动的面部 SDF；头发 Lightmap 接入下载预设的高光门控，保留原 MMD 透明叠层 |
| 空 | `面.png`、`发.png`、`服.png`、表情及 MMD toon／sphere；未找到配套游戏身体／头发 Lightmap | 采用 festivities 的 Boy 面部模板作适配，保留已验证的身体图集金属遮罩、发丝与眼睛处理；不把颜色图冒称游戏 Lightmap |

`NPC_Crowd_Female_Face_01_Tex_Lightmap.png` 与 `Avatar_Lady01_Tex_FaceLightmap.png` 内容不同，不能只因都带 Lightmap 名称就替换。控制图以 Non-Color 读取；颜色图与 MMD alpha 链继续保留。没有把原神 Lightmap 冒充鸣潮 HM／HN。

## festivities：实际读库后的兼容结论

来源：[Blender-miHoYo-Shaders](https://github.com/festivities/Blender-miHoYo-Shaders)，本轮下载 `HoYoverse - Genshin Impact v3.4.blend`、README、GPL-3.0 许可证到临时目录。库 SHA-256：`0a0809dfa495188b057a0144070d7bdedb2213356b4b849e6468dd459180bba2`。

作者 README 明确主要面向原游戏素材，MMD 版不保证直接适用；预览还经过较多后期，不能把宣传图等同于节点默认输出。作者希望衍生 Shader 参考注明来源，本轮保留来源并在交付目录附 GPL 许可证。

在本机 Blender 5.2.2 中只读打开、实际枚举节点后，发现四个 Goo 专用节点无法识别：

- `Depth-based Rim / Curvature`。
- `Face Factor / Shader Info.002`。
- `HoYoverse - GI Body / Ramps Cast Shadows`。
- `HoYoverse - GI Body / AO Cast Shadows`。

所以没有把整套旧库原样换到角色上。本轮只复制面部 `Face Factor`，在副本中去掉不支持的 Cast Shadows 节点、禁用 Catch Shadows，以明确的世界光向与跟随头部的前／上向量替换原属性输入；这不等于复现了 Goo 的投影捕获或完整原游戏渲染。

角色类型选择器是 **1 起算**：Loli／Boy／Girl／Male／Lady 对应 1／2／3／4／5；通过库内阈值节点核对，不能当成 0 起算。本轮空选择 Boy=2。

## NPC 模板错位的实测与修正

首轮给阿克西妮娅直接套 Lady=5，在 4200／4420 帧出现了不合适的鼻眼亮区和分界。它是 NPC 的 UV／脸型与通用头像修正不匹配的表现，不能把“能连接”当成“适配成功”。该版只保留为研究过程，没有用于最终视频。

最终阿克西妮娅改用模型自带 FaceLightmap 的 R 通道，保留面部原色、嘴线和原透明链；根据头部平面内的光向决定左右 UV 镜像，使用 `(1-dot(headForward, projectedLight))/2` 作为阈值、`.035` 作为过渡半宽。这样不再把通用模板的额外鼻眼修正硬套到 NPC 上。

头部向量由 `armWorld × posedHead × inverse(restHead)` 转换得到。MMD 头骨的局部轴因模型而异，不能把局部 +Z 当所有模型的前向，也不能让光影只跟世界坐标、忽略转头。驱动是简单矩阵属性表达式，可在禁用自动脚本的后台进程正常求值。

实现：`genshin_material_adapt.py`、`refine_reference_duet.py`。当前向量、模板与过渡宽度是这两个模型的实例设置；使用新模型仍须检查 UV、左右光与转头动态。

## 用户下载的预设：学习、读取与采用分开记录

以下四个原始文件均在 `--disable-autoexec` 下由本机 Blender 5.2.2 实际打开，节点组中没有发现 `NodeUndefined`。这只证明读取与节点类型兼容，不自动证明任意模型已套用、已渲染通过。

| 预设 | 实际内容／输入 | 本轮状态 |
| --- | --- | --- |
| `hair高光(wuwa3.0).blend` | 24 个节点，HM、HN、D 和两组位置／变量参数 | 已读节点结构；两位原神 MMD 缺配套鸣潮 HM／HN，没有盲套，也未声称完成其渲染验证 |
| `几何实体化描边.blend` | 45 个几何节点；描边权重、宽度、名称、相机动态宽度，以及材质映射对 | 已读结构与教程代表帧；本轮保留现有经过面部／材质权重精修的 MMD 反壳黑线，避免叠两套描边 |
| `通用脸部sdf.blend` | 头部 f／r 与光向 dg，投影到头部平面、左右 UV 采样、原神／鸣潮模板和过渡参数 | 实际读图与节点；核对了需要正确绑定头部与选择模板。最终采用模型自带 NPC SDF 与已适配 Boy 模板，未原样使用其默认鸣潮女角色输出 |
| `A-原神版预设.blend` | 25 组，包括脸、头发、衣肌、金属、AOV／后期和发高光 | 实际导入其中 `发高光` 到阿克西妮娅头发，接入已有 Lightmap 并把强度从试验 `.08` 降为 `.025`；其余组没有整套替换 |

下载预设随附使用说明要求标明 **“着色器：三一七片的谎言”**，已加入交付署名。不提交预设、第三方模型或教学视频到仓库。

原神预设还提供深度、灯、脸部遮罩、眼透与透明值 AOV，以及屏幕刘海阴影／眼透合成。这些需要透明设置、完整 AOV 和正确相机视角；**本轮没有启用该整套刘海阴影／眼透后期**，不能只追加一个节点组便声称效果链已完成。

实际从本地 SDF 教程（约 705 秒）和描边教程（约 654 秒）各抽取六个时间点并查看画面，能看到模板选择、光向黑白测试、头部控制和描边权重／名称接口。它们是抽样观看，没有听写完整教程或宣称逐秒观看。原神预设说明文字也已实际读取。

## Goo Engine 的定位

[Goo 官方仓库](https://github.com/dillongoostudios/goo-engine)说明它是修改 Blender 源码的独立构建，提供额外 Eevee NPR 节点与 Light Groups，**不是装进 Blender 5.2 的普通插件**。festivities 库的未识别节点正说明这种差别。

用户目录里有 Goo 3.6／4.x 的压缩包，但本轮没有运行或安装这些二进制，也没有将 5.2 动作工程降级保存；不能把“压缩包存在”写成“引擎安装／兼容／渲染通过”。本轮在已验证的 5.2 中完成适配与视频，当前缺少 Goo Cast Shadows 等专用能力。以后若研究独立 Goo 路线，应对副本核对动作槽、驱动、透明与合成器兼容，不能直接替换唯一的制作工程。

原神 [GDC 2021 演讲资料](https://media.gdcvault.com/GDC%2B2021/2021GDC%2B_%2BHaoyu%2BCai%2B_%2Bpresentation%2Bfile.pdf)的搜索索引提到面部动态光照图和角色／场景分离控制，但全文读取返回 403；本轮不把索引内容说成完整演讲学习，更不把开源近似说成 miHoYo 原始实现。

## 礼堂合并、性能与五秒验收

`integrate_reference_duet.py` 替换旧礼堂根对象及其后代，只引入新版礼堂对象和 World，不引入研究相机。沿用地板平移 `[0,15,-.02776420675]`，人物与现成相机不动。背景采用礼堂参考曲线，人物用 `ReferenceDuetActor` AOV 保护肤色／黑线，各自独立控制；人物补光通过 Light Linking 限定到相应模型。

静态 GI 烘焙时隐藏演员，避免把某一舞姿的阴影或发光烘进建筑。保留 Screen 光线追踪、球形／平面反射与已烘焙体积探针。最终 32 采样，只有窗主光和两个人物主光开启投影；14 盏烛光及补光不重复计算无必要阴影，屏幕反射仍保留。

同机位首轮第二张图约 32 秒；减少无必要投影后，实测两个关键帧约 8.85／6.81 秒。这是单进程本地静帧数据，不用于承诺整曲成本。五秒使用两个 150 帧工作进程完成，分别约 1028／1082 秒，均标记完整，不复用旧材质片段。

源帧 4140–4439，对应原声约 68.983–73.983 秒；使用用户指定的原声 FLAC，MP4 内为 AAC。已完整解码 300 帧，1920×1080／60fps／5 秒；音频约 5.013 秒（AAC 尾部填充），RMS .259、峰值 .894；150 帧分段接缝检查通过。

五时点全部骨骼与相机／焦距误差均为 0，运行时刚体不存在，150 张文件图片全部打包。已审看 12 张成片代表帧与关键帧，技术检查不等于用户美术验收或全曲验收。相机原切换保留；粒子仍为静态微光点，未宣称完成落雪动画；场景与作者预览仍有差异。

## 复用入口

- `genshin_character_probe.py`：读取本机人物实际材质、贴图、骨骼与 UV 层清单。
- `genshin_library_probe.py`：在独立 Blender 中读取下载预设的接口、运算、属性及未定义节点；不会执行内嵌脚本。
- `genshin_material_adapt.py`：面部向量／SDF 与本轮发高光适配。
- `integrate_reference_duet.py`：礼堂整合、背景／人物分开调色、静态 GI 与保存。
- `refine_reference_duet.py`：修正 NPC 模板、限制高光并设置最终投影配置。
- `render_duet_sample.py --start 4140 --frames 300 --workers 2`：渲染、混入指定原声并验证视频／音频／接缝。

先整合到新目录，再执行 refine 到另一个新目录，最后以 refine 工程导出；不要覆盖源素材、原预设或旧交付，不要将本轮样本写成全曲已完成。
