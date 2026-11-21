# 发丝、金属遮罩与可见描边：质感精修

2026-11-09，继续猪猪认可的半兰伯特方向，针对发丝高光、材质专属遮罩、人物与舞台关系逐项修改；制作中猪猪指出轮廓黑线不足，已加入分部位描边对照与精修。交付根目录 `D:\codex\output\MMD-Surface-Refinement-v1`。原两类风格、六套 v1 预设保留，本轮另存模型适配参数。

## 为什么这次要做模型专属控制图

实际检查当前 16 张打包图与材质引用。深蓝布料、金边、纽扣和部分饰件共用服装图集，仅按整个材质标为 cloth/trim 无法区分其内部反光职责。原贴图已有绘制高光，因此继续加统一白色高光容易混在一起。

本轮提取打包图的原字节到临时目录，没有改写源素材；从实际 Body / Item / Hair 三张 1024 图集生成控制图，R 为金色候选，G 为美术粗糙度，B 为原绘制亮部候选。它们是根据颜色和当前 UV 审看的**新制美术控制图**，不是下载到或恢复出的原游戏 ILM/PBR 数据。

着色时仅在已核实的 cloth/trim 材质上启用金属 R，排除皮肤、虹膜、眼白、眉睫；服装图集虽含眼睛与肤色，这些区域不会因共享图片而自动获得金属效果。图集识别依赖当前配色，换模型需重新审看，不能只改路径批量套用。

参考学习：[Juan Salice 的原作者 NPR 拆解](https://juansalice.artstation.com/projects/LR5y6R)讲述分区控制高光、AO、内线、头发反射和法线的职责；本轮据此拆分控制，未使用其角色或原贴图。[Project Studio Q 的 Blender 制作文章](https://cgworld.jp/regular/studio-q-02.html)也介绍高光、阴影和部位遮罩的组织。本轮沿用本项目已验证的 5.2 节点，没有把旧版本节点直接当兼容保证。

## 已实现的精修

| 环节 | 实际实现 | 保留的边界 |
| --- | --- | --- |
| 银发高光 | 头部姿态驱动的 up 方向投影到法线切平面，形成近似发束方向；与视角/光方向构成的半程向量计算带状高光，再由贴图亮部控制打散；Screen 混合限制过亮 | 是艺术方向性高光，不是原生各向异性 BSDF或完整毛发散射。没有改变角色发色或复制其他模型的发丝贴图 |
| 头发层次 | 适度降低底色光照增益，分开亮带和暗部；替换原先较泛化的头发小高光，叠层保留原透明语义 | 控制图不能取代所有法线/发束设计；动态时仍需检查高光游动和闪烁 |
| 金边与纽扣 | R 遮罩限制混合原生 Principled 金属响应，G 控制粗糙度；启用本机 EEVEE ray tracing 辅助反射 | 属于原 NPR 与受限物理材质混合；不把 EEVEE 的选项称为 Cycles 路径追踪，也未把全部布料改成金属 |
| 蓝色布料 | 排除金属区后保留宽而克制的分析式光泽；调整衣发中间调和暗部 | 没有制作高频织物纹理或声称完成微结构布料模拟，避免在预览尺寸引入摩尔纹 |
| 舞台关系 | 保持人物主光响应，降低部分舞台补光与环境亮度，让舞台稍退后 | 不靠全局曝光压暗人物；同姿态图片不另加调色 |
| 脸与物理 | 沿用上轮已通过的脸、眼睛和衣发动作 | 上轮单独面部椭球法线的收益小，本轮没有为了技术清单重复大改脸部法线；新头部方向控制的是发束高光 |

初步逐项静帧在 `stills-v001`，校准后在 `stills-v002`；各方案均检查顶点位置和三个姿态的全部骨骼矩阵哈希保持一致。材质/灯光效果变化不等于动作或物理被重新制作。v1/v2 参数分别在 `presets/quality/surface-refinement-v1.json`、`surface-refinement-v2.json`；后者加强了亮带与中间调区分。

`control-maps/atlas-mask-review.jpg` 可审看原图、R 金属候选与 B 绘制亮部；`SurfaceGold` / `SurfaceHair` AOV 输出表明效果实际作用的位置。首帧高光信号有非零带状分布，金属信号落在金边/纽扣/饰件，不仅凭节点创建成功宣称生效。

## 关于猪猪指出的黑色轮廓

此前已经有 MMD Tools 反向外壳描边，但使用较亮蓝紫色、部分透明，宽度又较细。在小尺寸预览下，与蓝衣/蓝灰发色混合后不够明显；不能把“存在修改器”当成“最终画面有清楚黑线”。

本轮 `presets/quality/outlines-v1.json`：头发/衣服使用近黑色、提高不透明度和宽度；配饰略收，毛领使用较柔和的深灰，脸使用较细的暖暗线。眉眼嘴的绘制内线继续保留，不给它们再套一层厚外壳。参数为场景线性颜色，不能把 0.25 直接当作显示器上的深灰。

后续猪猪明确要求脸也应有观海子参考里清晰可读的深色线。v1 的暖细脸线因此仅保留作旧版本；新 `outlines-v2-face-black.json` 单独加强脸外壳、眉睫与嘴缝，实际对照和复现见 [脸部描边精修](FACE_INK_REFINEMENT.md)。MMD Tools 原边节点还含内部 Gamma，预设参数应以实际渲染判断，不直接当作最终显示值。

保留 PMX 材质/顶点边宽，用部位系数调整 `mmd_edge_preview` 顶点组，不直接去掉权重后增大 Solidify 裸厚度。本机 MMD Tools 的 `update_edge_weight` 不会自动重算预览组，因此只改面板边宽不一定更新实际线条；脚本保存原组权重并据此重算，避免重复运行叠乘。

`outline-comparison.jpg` 对照三种状态：关闭外扩描边、原细线、增强近黑线。关闭外壳后原贴图中的眉眼/衣物绘线仍在，不能称为“关闭全部线条”。源帧 601 的原细线 Crypto 覆盖率 >0.5 约 1023 像素，增强后约 6121；满覆盖线条的平均显示 RGB 约 37–39，说明暗线确实渲染出来，非画在预览图上。这些数字来自 540×960 静帧，不是所有机位的统一线宽保证。

方法是反向外壳，不是深度/法线 Edge Detection。后者可作为未来单独路线，不能改名代替实现。横屏和竖屏最终构图下需分别检查输出像素宽度，不因材质共享就认为线条尺度相同。

通用渲染入口可另加 `--outline-preset presets/quality/outlines-v1.json`，在风格材质设置之后应用描边，避免风格组件又把线色改回较亮蓝紫。此入口要求先有 MMD Tools 描边修改器/权重；没有时会报错，不将空操作当成功。它不默认覆盖六套已交付 v1，而是后续项目的明确选择项。

## 八秒动态验证与复用

选择 v2 材质 + 近黑描边，准备源帧 421–900、60 fps 的八秒竖屏片段，目标 720×1280 / 64 samples。头部高光方向按新范围重烘焙，镜头按八秒范围重新计算中景/近景，不沿用四秒轨迹在结尾冻结。头部与保守变形后头发包围范围逐帧投影检查；检查不包括保证所有手部、脚部都完整入镜。

新增 `portrait-surface-study.json` 覆盖八秒文字前后层；沿用官方 Tall 文字与伴奏来源，卡点仍留给用户。项目保存渲染、材质、相机和遮罩输出；动态文字仍由 Python 第二阶段合成。大型 PNG 缓存在 `D:\codex\temp\mmd-surface-motion-v1`。

实际完成/解码状态和校验值以本轮交付 `delivery-manifest.json` 为准；本轮不是新二十秒全高清成片，也没有把竖屏验证冒称所有横屏组合已升级。

首次后期调用漏传结束帧，沿用旧四秒默认值，视频验收按八秒目标拒绝通过。随后用完整 421–900 PNG 缓存重做 `motion/composite-v2`，保留首次文件与失败报告作诊断；最终以 `video-qa-v2` / `audio-qa-v2.json` 为准。合成器的默认结束帧现改为读取实际缓存，另有防止八秒被静默截短的回归测试；显式 `--end-frame` 仍可选择子片段。

最终八秒版已完整解码 480 帧、720×1280 / 60 fps，音轨实际解码 48 kHz 双声道、8 秒、非静音；无全黑帧或连续静止帧，字幕保护区编码前最大线性差为 0。37 项测试、编译与 diff 空白检查通过。新增独立描边入口另用观海子 graphic 横屏完成单帧实际测试，不冒称完整横屏精修版已交付。

```powershell
# 从上轮半兰伯特场景执行独立精修实验；所有输出使用新目录。
& 'E:\tools\Blender Foundation\Blender 5.2\blender.exe' --background `
  'D:\codex\output\MMD-Quality-Lab-v1\half-lambert-v001\half_detail\quality-study.blend' `
  --disable-autoexec --python-exit-code 1 --python scripts/mmd_surface_refine.py -- `
  --output-dir 'D:\codex\output\surface-new' --preset presets/quality/surface-refinement-v2.json `
  --masks 'D:\codex\output\MMD-Surface-Refinement-v1\control-maps\mask-manifest.json'

# 在审看通过的精修副本上单独比较轮廓。
& 'E:\tools\Blender Foundation\Blender 5.2\blender.exe' --background '<精修副本.blend>' `
  --disable-autoexec --python-exit-code 1 --python scripts/mmd_outlines.py -- `
  --preset presets/quality/outlines-v1.json --output-dir 'D:\codex\output\outline-new'
```

换角色时先用 `mmd_surface_probe.py` 核对材质/图集，用 `make_surface_masks.py` 的思路重新制作和审看控制图，不能把阿克西妮娅的颜色阈值或图集名称当作所有角色的标准。发束方向假设、金属遮罩、轮廓细度和舞台亮度应分别验证，再写入对应风格/画幅的新版本。

## 用户补充的创作者入口

以下按用户粘贴内容及此前取得的作者置顶评论整理链接，修复连在一起的标点与截断。它们是学习目录，不表示本轮已看完这些创作者的课程；本轮实际阅读的技术正文列在前文。

| 方向 | 创作者入口 |
| --- | --- |
| MMD | [miaobox](https://space.bilibili.com/32690910)、[小二今天吃啥啊](https://space.bilibili.com/437528440)、[克里斯提亚娜](https://space.bilibili.com/322607631) |
| PBR | [叫我白菜就好啦](https://space.bilibili.com/175058194)、[RedialC](https://space.bilibili.com/11831050) |
| Blender 基础 | [只剩一瓶辣椒酱](https://space.bilibili.com/35723238)、[KurTips](https://space.bilibili.com/225179867)、[Blender Guru](https://www.youtube.com/@blenderguru) |
| 三渲二 | [CG DASH](https://www.youtube.com/@CGDASH)、[神代溪久奈](https://space.bilibili.com/37949446) |

用户粘贴的 Blender 下载与旧 MMD Tools 入口作为来源记录；继续使用本机已安装 Blender 与扩展，不重复下载安装。出处范围见 [半兰伯特阅读记录](HALF_LAMBERT_STUDY.md)，模型/动作/音乐等署名沿用交付说明。
