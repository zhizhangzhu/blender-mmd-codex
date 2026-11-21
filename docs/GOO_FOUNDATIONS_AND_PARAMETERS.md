# Goo 基础功能与参数学习

猪猪已选择继续以Goo为主，并要求先弄清基础功能和参数，再学习高阶卡渲与MME转化。当前顺序是：版本与色彩 → 受光与灯组 → 阴影 → 色带与输出 → 屏幕资源 → 程序纹理 → 高阶组合。先在独立测试场景理解因果，不继续往人物工程叠效果。

本轮完成官方功能清单阅读、13类本机Goo专属节点的接口／默认值／范围／枚举记录，以及一个基础灯组实验。**这不是“所有参数已掌握”**：程序纹理各模式的公式、非渲染界面功能和部分版本差异仍需逐项核对，进度在[基础课程参数](../presets/workflows/goo-foundations-v1.json)中明确区分。

11月18日后续完成[八项基础指南首轮学习](GOO_MMD_EIGHT_FOUNDATIONS_2026_11_18.md)。新增实测：当前Goo的真实网格Normal Edit会改变Half-Lambert，顶点坐标不变；它与下方无响应的Shader Info覆盖插口是两个入口。另验证材质复制仍可共享内部组，以及修改器顺序会改变求值几何。复杂人物与动画仍未覆盖。

## 官方资料与实际版本

[官网](https://www.dillongoostudios.com/gooengine)和[官方功能目录](https://www.dillongoostudios.com/gooengine-features)描述官方Goo 4.4／EEVEE Legacy。[官方GitHub](https://github.com/dillongoostudios/goo-engine)默认`goo-engine-main`并不等于网站对应的发布分支。本轮分别锁定：

- 默认分支：`8457395892beec33d4605ef9d894a1aff4a8d79f`，其Shader Info声明没有Half-Lambert输出。
- `goo-engine-v4.4-release`：`d281a65ebe227cad2726f79255218dcf88d03f92`，声明包含该输出。本轮主要对照此发布分支的短节点定义。
- 当前本机：社区移植Goo 5.2.1、构建`0051aee03764`，后端为EEVEE-Next。官方4.4示例值和Alpha设置不能不加核对直接套用。

源码与软件二进制不是同一个提交；接口来自实际本机构建，官方源文件用于解释。原源码私存`D:/codex/temp/Goo-Official-Basics-2026-11-17/`，没有复制进repo。全部本机参数保存在`D:/codex/output/Goo-Basics-Study-2026-11-17/parameter-inventory-v2.json`，包含模式切换后的可用插口；没有实际连接就不代表已验证生效。

## 第一层 受光与色带

### Shader Info

| 参数／输出 | 基础含义 | 调节时先看什么 |
| --- | --- | --- |
| WorldPosition | 官方接口用于覆盖受光采样的世界位置，不是移动网格 | 本机5.2社区版四路受测输出对偏移无响应；旧4.3对照有效，不能照搬旧教程 |
| Normal | 官方声明中提供受光法线；不接线时使用表面法线 | 本机5.2社区版四路受测输出对朝下法线无响应；普通Diffuse BSDF正对照有效，三个法线入口需分别核对 |
| Diffuse Shading | 漫反射受光信号，含光色／能量等因素 | HDR数值可超过1；不能未经标定就塞进固定0–1阈值 |
| Half-lambert factor | 用光向与法线构造的形体分区信号 | 与亮度／投影分别处理；每个卡通主光组先只放一盏方向主光 |
| Cast Shadows | 来自其他对象的遮挡信号 | 当前旧实验中1为无遮挡、0为遮挡；对象归属决定分类 |
| Self Shadows | 当前对象自己的遮挡信号 | 同mesh内刘海遮脸可能归到这里，不能为了去坏影直接整路删除 |
| Ambient Lighting | 环境受光信号 | 独立安排色彩与补光，不让环境变化无意移动形体阈值 |
| Use Own Light Groups | 节点是否覆盖材质的灯组选择 | 开启后核节点自己的组，不只看材质面板 |

以上输出不是一套已经画好的卡通材质。基础结构应分别检查“形体分区”“真实遮挡”“环境色”和“高光”。Emission可作为受控颜色的输出载体；在其前面做了受光运算，也仍可能保留明暗。问题在于输入的层次和增益，不能只凭Emission节点判断材质有没有光照。

先前[近景目标与Normal基础实验](GOO_REFERENCE_FACE_HAIR_STUDY_2026_11_17.md)现由[11月18日Goo／Blender官方学习与双版本控制](GOO_BLENDER_FOUNDATIONS_2026_11_18.md)扩展：四路Shader Info、WorldPosition偏移、普通Diffuse正对照、真实灯移动和两个版本独立重开均已记录。结论只覆盖该点光／平面场景，Ambient及更复杂情况仍待验证。

### Light Info 与 Light Groups

Light Info选择一个灯对象，读取颜色、功率和感知功率。功率值不等于某片皮肤处的照度；面积／距离／法线等不是这个输出直接给出的量。感知功率的实现与更新方式有版本差异，以本机实测为准，不能混用旧源文件和当前发布文案。

灯组通过同名关联灯和材质；Default组也是有效参与者。材质有受光与投影许可，Shader Info还可单独覆盖。`light_group_bits`等内部位掩码不作为日常调色滑块，先用名称与开关管理。材质`check_shadow_id`关系到Cast／Self拆分；旧实验已证明关闭时两路可能一起变暗。

### Color Ramp 与亮度输出

Fac是待分类的信号，色标位置决定分界，色标颜色决定亮／中／暗区颜色；Constant产生分段，Linear／Ease等改变过渡。改变阈值是在移动形体分区，改变颜色是在设计配色，改变Bloom是在处理成图，三者要分别调。

OKLab Color Ramp使用不同颜色插值方式，但不保证自动更鲜艳；相同端点也可能出现更低饱和中间色。色标顺序、位置、颜色和插值单独记录。本机默认Fac为0.5，默认色标和嵌入设置见参数表，不把一个示例当万能人物预设。

## 新的基础灯组实验

空场景放两个球：左球显示原始Half-Lambert，右球用同一信号驱动固定三段色带。固定相机、曝光、色带和材质，仅改变参与该信号的灯。

| 静帧 | 唯一变化 | 实际结果 |
| --- | --- | --- |
| A 单主光 | 只有顶向主光参与 | 左球连续灰阶；右球有三段明暗 |
| B 相反方向双灯 | 顶光与反向补灯都进入节点组 | 左球大面积趋近1；右球几乎只剩亮色 |
| C 补灯排除 | 场景保留两灯，节点仅选择主光组 | 恢复A；A/C线性RGB最大差为0 |

线性数据来自32-bit EXR，显示PNG不能用于复算HDR数值。保存C的独立研究工程，另一进程重开后重渲并比较；结果见输出目录`light-group-controls/reopen-verification.json`。这些是简单球体／静帧证据，不是人物过亮的完整诊断，也不认证复杂阴影和动画。

这解释了为什么基础组装顺序重要：先保证用于卡通分区的主光信号稳定，再决定补光怎样参与人物；不能只在发白之后不断压全局曝光。

## 第二层 深度与程序边缘

| 节点 | 本机基础参数 | 含义与已知条件 |
| --- | --- | --- |
| Screenspace Info | View Position；输出Scene Color／Scene Depth | 采样可取得的相机缓冲；旧本机实验需场景Ray Tracing及材质raytraced transmission。Depth要按实际距离映射，不直接当0–1颜色 |
| Set Depth | Shader、View Depth | 改写片元深度，不移动网格。旧本机实验中View Depth需要实际连线，单改隐藏默认值无效 |
| Curvature | Samples=8；Sample Radius=1；Thickness=1；Scale=(1,1,0) | 从屏幕邻域构造边缘／rim信号。采样次数、邻域、厚度和坐标缩放职责分开；数值过小看似黑不等于无输出 |

Curvature官网示例的建议调值与节点构造默认值不同。先看默认，再只改一个输入核对；厚度也不能直接解释成恒定的像素线宽。当前5.2旧球体实验放大后会亮到内部，尚不能直接晋升为干净人物轮廓光。

Screenspace与Set Depth属于基础资源机制；学清楚参数不等于恢复眼透制作。用户搁置眼透的约定继续有效。

## 第三层 程序纹理接口

| 节点 | 基础控制 | 当前学习边界 |
| --- | --- | --- |
| SDF Primitive | Mode、Vector、Size、Radius、模式相关Value／Point／Angle、Roundness、Linewidth、Invert | 产生解析距离；Value1等含义随形状变化，不能统一叫“强度”。已提取各枚举的可用插口，尚未逐形状验证公式 |
| SDF Op | Operation、两路Distance、Value、Count、Invert | 组合或修改距离；模式不同控制项不同，先学并／交／差的最小例子 |
| SDF Vector Op | Operation、Axis、Vector、Scale、Angle、Count等 | 变换SDF使用的坐标；不等于修改真实网格 |
| SDF Noise | Position、Distance、Detail、Roughness、Detail Inflation、Detail Blend | 对距离细节作程序处理；具体增减方向尚需配对静帧，不凭名称判定 |
| Hex Grid | Vector、Scale、Size、Radius、Roundness及布局／方向／取值模式 | 六边形图案、格内坐标和ID；图案参数与真实几何分开 |
| Twirl | Vector、Center、Amount | 围绕中心扭转采样坐标；默认Amount=0 |
| Water Ripples | Mode、Vector、Time、Scale、Intensity、Speed、Detail、Bias | 程序波纹与扭曲向量，不是水体模拟；下拉模式驱动隐藏Mode插口，首次只用下拉框 |
| OKLab Ramp | Fac、色标、插值 | 颜色过渡工具，职责与普通色带同类，颜色路径不同 |

这张表是学习次序与参数索引。SDF的占位插口和高级纹理模式保持“接口已核／行为待验证”，不因为能枚举参数就登记为掌握。先完成每个基本模式的读值和开关图，再组合高阶材质。

## 其他官方基础功能也要登记

官方功能目录还列出透明Holdout、View Layer材质／World覆盖、分层采样、GN相机覆盖、Grease Pencil纹理随机化与线条工具、视口线宽、骨骼隔离／约束辅助，以及菜单／相机／World透明等界面改动。这些已列入待核清单，尚未逐项在5.2社区版操作验证；尤其不能把官方4.4的Cycles范围、采样建议和Alpha Blend步骤直接写成当前软件事实。

原生Blender的Base Color、Roughness、Metallic、Alpha、色彩空间、曝光、色调映射、Glare阈值／半径也在前置基础中学习，但不冒称Goo专属新功能。当前优先完成与脸／发／白衣直接相关的部分。

## 每一项怎样才算学会

每个基础项至少写出：位置与用途、输入输出、实际默认值／单位、增减方向、生效开关、同机位单变量对照、保存重开结果、版本差异和常见误用。只有资料阅读／接口记录时标为“待验证”，不直接给“掌握”标签。

达到这些条件后，才研究屏幕空间脸影、复杂发带／材质组合和MME适配插件。短期插件方向是封装已验证的Goo模块及参数面板；原版任意`.fx`执行仍是另一个兼容运行时工程，当前不启动开发。原生MMD主渲方案按用户最新选择搁置，保留作历史可行性评估。
