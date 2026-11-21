# Goo与Blender官方基础学习：受光输入、阴影与显示转换

2026-11-18。按猪猪要求继续阅读Goo官网／官方GitHub，并补读Blender官方手册。当前人物v6未加载、未修改；没有生成视频。本文中的测试图是独立基础控制，不是人物美术升级。

同日后续：[八项基础指南学习](GOO_MMD_EIGHT_FOUNDATIONS_2026_11_18.md)补充了本文当时尚未验证的真实网格Normal Edit入口，当前Goo球体测试已生效且重开一致；不要把本文覆盖Normal插口的结果扩大为所有法线处理无效。

## 本轮实际阅读

重新针对性阅读[Goo官方功能页](https://www.dillongoostudios.com/gooengine-features)的Shader Info、灯组、自阴影ID、Light Info和屏幕资源说明；官方GitHub阅读[节点声明与默认输入](https://github.com/dillongoostudios/goo-engine/blob/goo-engine-v4.4-release/source/blender/nodes/shader/nodes/node_shader_shader_info.cc)及新增的[GLSL转发入口](https://github.com/dillongoostudios/goo-engine/blob/goo-engine-v4.4-release/source/blender/gpu/shaders/material/gpu_shader_material_shader_info.glsl)。后者把position／normal继续传入`calc_shader_info`，但未取得发布分支中该函数的完整实现，不能把短入口阅读称为完整后端审计。

新增实读Blender 4.4手册：Shader to RGB、Diffuse BSDF、Normal Edit、EEVEE灯设置、采样、限制和色彩管理全文；再对照5.2的Shader to RGB、Normal Edit、灯设置，以及新拆分的Color Spaces、Displays and Views、System Configuration正文。5.2色彩管理首页只有目录，不把它当正文阅读。私人HTML与正文在`D:/codex/temp/Goo-Blender-Official-Study-2026-11-18/`，repo只保留原创笔记与来源账本。

官网说明对应官方4.4／EEVEE Legacy；本机生产使用5.2.1社区移植`0051aee03764`。本轮另用既有4.3.2构建`ba60b2412c76`做对照，没有安装／切换生产版本，也没有用旧版打开5.2工程。官方在线手册的功能存在不等于社区构建全部继承。

## 1. 插口存在，不等于当前后端使用了它

在同一研究脚本内，每个版本从空场景生成五块平面：Half-Lambert、Diffuse、Cast、Self和普通Diffuse BSDF→Shader to RGB正对照。一盏400W点光；Cast使用独立小方块，Self将方块和接收面合并为同对象。固定相机、曝光、几何与32采样。两路Diffuse仅为显示乘0.1，数值报告明确保留这一比例。

| 单变量 | 5.2社区版四路Shader Info | 旧4.3.2四路Shader Info |
| --- | --- | --- |
| 连接法线(0,0,1) | 与默认相同 | 与默认相同；平面原法线就是朝上 |
| 连接法线(0,0,-1) | 四路均无变化 | Half-Lambert／Diffuse变化；Cast／Self不变 |
| WorldPosition接原位置+(3,0,1) | 四路均无变化 | 四路均变化 |
| 移动真实点光 | 四路均变化 | 四路均变化 |

“无变化”在本实验指接收平面ROI的**线性RGB最大绝对差为0**。普通Diffuse BSDF的Normal朝下在两个版本均有变化，最大显示缩放后线性差分别约0.04095；这排除了所有法线连线都无效的解释。旧版Half-Lambert法线反转差约0.86605；位置偏移在两路遮挡信号产生约0.99343／1.0的最大差。两个保存的研究工程均用另一进程重开，重渲与原帧全图线性RGBA最大差均为0。

[复现脚本](../scripts/study_goo_info_input_matrix.py)。实际报告在`D:/codex/output/Goo-Input-Matrix-Study-2026-11-18/goo52/measurements.json`及`goo43/measurements.json`；各自`reopen-verification.json`记录重开。两种渲染器只比较各自的输入效应，不能凭跨版本像素差判定谁更好。

这扩展了[前轮Half-Lambert实验](GOO_REFERENCE_FACE_HAIR_STUDY_2026_11_17.md)，但仍只覆盖简单平面／点光、四路输出及这两个二进制。Ambient、其他灯型、复杂网格和动画未纳入。社区移植源码对position／normal不参与计算的路径提供了解释线索，不能代替同提交源码审计或推广到所有Goo版本。

## 2. 法线与投影是不同控制

Blender的[Normal Edit](https://docs.blender.org/manual/en/5.2/modeling/modifiers/normals/normal_edit.html)操作网格自定义着色法线：Radial从中心向外，Directional朝向目标；Parallel Normals统一方向，Mix Factor／顶点组控制混合，Max Angle限制偏转，锁定项防止不合理翻面。这不等于移动头发，也不能让真实遮挡自然消失。**本轮只读了修改器说明，尚未在当前Goo验证该修改器路线。**

普通[Diffuse BSDF](https://docs.blender.org/manual/en/4.4/render/shader_nodes/shader/diffuse.html)的Normal是着色法线输入；4.4文档将其Roughness标为Cycles专用，不能用它替代EEVEE主光尺寸来调刘海投影。Shader Info Normal、普通BSDF Normal、真实网格自定义法线是三个入口，证据不能互相冒用。

对脸部的后续假设是：先分别检查形体分区、刘海真实投影、接触AO，再设计颜色。当前5.2不依赖未经验证的Shader Info覆盖法线／位置来“修脸”。普通Diffuse路线可改变受光，但仍包含灯光与衰减等综合贡献，不能升级成纯visibility。

## 3. Shader to RGB与Goo拆分的关系

Blender[Shader to RGB手册](https://docs.blender.org/manual/en/5.2/render/shader_nodes/color/shader_to_rgb.html)说明它把BSDF受光转成可继续运算的颜色，适用于EEVEE卡渲，同时提醒它破坏常规PBR管线，与部分屏幕效果／采样／渲染通道存在限制。页面还保留Alpha Clip／Hashed等旧术语，因此这些警告登记为文档边界，不直接声称当前5.2所有对应行为都已实测。

Goo的价值在于分开Diffuse、遮挡与环境，避免换World就无意改变卡通阈值；Half-Lambert按每组一盏主光起步。官网允许丢弃Self不表示我们的角色应该整路关掉：同对象刘海投脸也可能被分入Self。先确认对象ID与影子来源，再决定保留或修形。

## 4. 阴影清晰度不靠一味增加灯数

Blender 5.2的[EEVEE灯设置](https://docs.blender.org/manual/en/5.2/render/eevee/light_settings.html)区分Jitter、Overblur、Filter和Resolution Limit。Limit更小才允许更细的阴影像素；Filter增加会模糊且可能漏光；Overblur不是物理光源尺寸。阴影池不足时增加Limit可以省内存，却会牺牲细节，两者不是同一优化目标。

[4.4采样](https://docs.blender.org/manual/en/4.4/render/eevee/render_settings/sampling.html)中Render Samples、阴影Rays和Steps职责不同；[限制页](https://docs.blender.org/manual/en/4.4/render/eevee/limitations/limitations.html)也说明薄面、重叠投影体和屏幕深度近似的局限。提高总采样不能修复错误的灯组、法线或过大Filter。采样页对Light Threshold性能方向的文字不作为已证实调参规则，本轮未测试它。上述参数尚未在人物场景做新消融。

## 5. 亮度、工作色域与显示转换分开

5.2的[Color Spaces](https://docs.blender.org/manual/en/5.2/render/color_management/color_spaces.html)将文件Working Space、图片解释与输出显示分开。底色按正确颜色空间读取，法线／位移等数值图应使用Non-Color；不是所有名为Lightmap的图都能据文件名定性。工作色域应在项目开头选择，不为了“更高级”临时切换现有工程。

[Displays and Views](https://docs.blender.org/manual/en/5.2/render/color_management/displays_views.html)中Exposure在显示转换前按`2^stops`缩放；Gamma是另一步。Standard仍做目标显示转换，不能称“完全不做色彩管理”；AgX压缩高动态并会使强曝光颜色趋于低饱和；Neutral有自己的设计用途。变换能改变观感，但不能补回材质运算中已被截掉的数值或重新产生脸影。

新增[色彩基础脚本](../scripts/study_goo_color_basics.py)只生成一份线性浮点色块，分别保存Standard／AgX的0与−1档、Neutral的0档，共五张16-bit PNG；**这是图像保存转换实验，没有场景渲染**。同一输入包括0.18／0.5灰、1／2／4白、暖色、蓝色和HDR蓝。五次保存后源浮点RGBA最大变化均为0：输出转换不等于改写原材质／原始缓冲。输出图与8-bit查看采样另见`D:/codex/output/Goo-Blender-Official-Study-2026-11-18/color-controls/`。

在PNG解码后的8-bit查看采样中，Standard零档把线性1／2／4白都显示成255；AgX零档分别约197／218／233，保留了三档区别。Standard减一档后，线性1白降到188，但2／4白仍为255。因此仅凭截图里的纯白无法反推原始亮度；这也不是断言AgX一定更适合当前角色，最终仍要固定一种输出后调材质。

5.2新增的[System Configuration](https://docs.blender.org/manual/en/5.2/render/color_management/system_configuration.html)还区分自动显示仿真与手动匹配显示器。它属于阅读内容，未改本机系统HDR、显示器、Blender偏好或既有视频色彩约定。不能用截图判断用户播放器配置有错。

## 接下来可落地的顺序与边界

先固定显示转换与曝光，用单主光及独立形体／遮挡查看图查明人物问题；再验证网格法线处理是否在本机有效，最后分别调发色带、投影颜色与眼睛局部高光。灯组、法线、材质增益、显示曝光每轮只动一个层级，保留可关闭对照。

本轮证明了版本兼容边界与显示转换机制，未证明角色已经达到参考质感。未恢复眼透、未改头发位置、未改人物／舞台／动作／字幕，也未恢复全曲。完整基础课程仍在学习中。
