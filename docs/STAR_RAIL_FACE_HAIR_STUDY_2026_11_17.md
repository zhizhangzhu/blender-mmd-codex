# 崩铁参考：明亮肤色与可读发影

猪猪于2026-11-17明确搁置眼透，先落实面部／头发阴影和明亮通透皮肤，其他已授权的果冻眼、眼睛高光、强轮廓泛光、舞台材质、带黑边字幕与原唱继续保留。v4五秒虽已编码，但眼透与发影被指出不达标，不能当作本轮美术完成；v6发黑、v8透得刻意均被否定。

## 实际外部阅读

原作者公开的 [StarRailNPRShader](https://github.com/stalomeow/StarRailNPRShader) 是民间Unity URP复现，非游戏官方源码。读了其面部核心、头发核心、共享照明中Ramp／高光／Emission段落、头发深度采样接口，以及作者的[材质说明](https://srshader.stalomeow.com/latest/character/material/)、[头骨同步控制](https://srshader.stalomeow.com/latest/character/rendering-controller/)、[渲染流程](https://srshader.stalomeow.com/latest/advanced/rendering-flowchart/)。另读[Nilo公开例子的照明方程](https://github.com/ColinLeung-NiloCat/UnityURPToonLitShaderExample/blob/master/SimpleURPToonLitOutlineExample_LightingEquation.hlsl)。没有把Unity插件安装到Goo，未取得或宣称官方Shader。

实读来源和Git blob SHA：

- `Shaders/Character/CharFaceCore.hlsl`，`a168e702fbfcc9b065d63dc4d56a727c287885c4`。
- `Shaders/Character/CharHairCore.hlsl`，`07b4f9e69015eaca9ead51b007674ed7f83c21e0`。
- `Shaders/Character/Shared/CharRenderingHelpers.hlsl`，`a5e58837f77740c7548e82171789055e79e50663`；重点GetRampUV、GetRampDiffuse、GetSpecular、GetEmission。
- `Shaders/Character/Shared/CharHairDepthTexture.hlsl`，`06d403559641fbe89f092daff5794e5a84f60e03`。

面部源码把头部方向和水平投影光向用于SDF比较，另外采样头发深度形成刘海遮挡；鼻部线条和受控发光分别处理。头发使用主灯方向、LightMap许可和冷暖Ramp取得漫反射，再独立叠高光、rim和Emission。原作者没有用简单均匀加灯替代这些职责。

Nilo示例则说明分离基础色、受光、阴影和Emission的重要性：脸部避免直接套普通法线硬分段；额外灯贡献受限，间接光有下限，发光最后加入。它是教学示例，不等同商用NiloToon全部功能。

上述公开实现所需FaceMap／Hair LightMap／Ramp不能假定当前两个MMD模型都有。阿克西妮娅有自身已核实的FaceLightmap；伊科尔没有已验证同类SDF。本轮保留原输入和既有SDF，新增部分明确记作自制近似，不把别的角色游戏图直接错接。

## 失败诊断与停止范围

v5导出的BangPeek通道全黑，证明相机坐标蒙版没有实际覆盖；常量85%透明正例证明透明闭包本身可工作。v6相机视线蒙版生效后，又露出了不透明MMD描边外壳，造成刘海黑脏。v8同时淡化头发和描边后能看见眼睛，但大块透明范围太刻意。猪猪已明确搁置此项，后续关闭发片与描边的新透明处理，不继续用它充当阴影。

## 当前实现方向

**当前保留的是production-v16，v9/v10黑银发实验无效。** 从v5正常颜色链重新制作后，新增色带改用已存在的主光受光值，简化节点并同步Goo灯组，银发已恢复。v9/v10组合为何使银发归黑尚未单独隔离，不将猜测当已确认根因。新色带在最终NPR颜色边界乘入，区间.32–.72；银发暗部乘(.62,.68,.85)，金发乘(.72,.58,.43)，保持原角色配色。

v13虽然150帧及视频编码完成，但长渲染日志出现421次8192页阴影池报满，峰值8439页，未通过交付前置检查，不能称技术完成。v14探明本机构建最大只能2048，无法增加到4096；v15限制三盏大窗灯的阴影纹素：平行窗光5mm→8mm，两盏大面窗灯10mm→15mm，两人斜上人物灯保持3mm，但高峰预检仍有少量报满。v16进一步将原生全局shadow_resolution_scale设为.75；新增面部512²遮罩序列精度不变。灯能量、位置、材质节点、动作及600张脸部阴影图均不改。4234／4250／4438原生1080p16samples和DOF预检完整退出、无报满；4250实际图已观察，随后独立重开核查并重渲全150帧。长渲染期间监测报满，不把被弃用的v13视频登记为最终样片。最新完成情况看current_state。

面部保留v5受控亮肤1.16和各自原有形体／SDF，再乘独立暖色刘海投影；鼻影缩小为按本模型鼻尖局部位置定位的UV遮罩，暖色乘(1,.74,.60)，幅度.60。主灯是两人各175W、.30m的斜上人物灯组；没有把额外正面补光无限叠加，也没有用均匀自发光亮度下限抹掉全部阴影。脸的明亮外观属于NPR计算颜色后Emission输出，不保证照亮邻近物体。

`bake_goo_face_hair_shadows.py`已对4140–4439共300源帧、双人各一组512²图，共600张进行实际变形发片BVH遮挡计算。每面部顶点向主光三个位置发射射线，仅保留55mm内局部头发遮挡，并以眼高附近的平滑高度许可限制大块颊影，最大附加遮蔽.88；它包含美术限制，不称纯物理或游戏原生头发深度图。鼻影静态随UV变形，刘海遮挡序列逐帧更新。

`finalize_goo_toon_shadow_master.py`修复Blender另存时将新相对路径重新指向旧目录的问题：序列位于production-v13/hair-shadows，保存时relative_remap=False。便携时必须将该目录与blend一起保留。`ImageUser.frame_current`在原数据块可能为0，渲染使用求值副本，不能据原数据块的filepath_from_user断言渲染冻帧；新增`check_goo_rendered_shadow_aovs.py`直接导出实际材质的UV与Visibility原始EXR，与正确源帧的阴影PNG做双线性采样比较，同时记录冻结第一帧负例误差。最终结果与样片状态看current_state及同目录报告。

`prepare_goo_toon_face_hair_study.py`以v5的保留工程为输入，显式恢复头发原PMX Alpha闭包，不启用新眼透，描边保持原版。

头发在原底色与原高光之间增加自制色带：银发暗部偏冷蓝灰，金发暗部偏暖金棕，依据实际斜上方主灯方向区分亮暗。高光和rim在色带之外处理；不再依靠眼周黑色透明块制造“发影”。

面部刘海投影另做几何核对：对真实变形后的面部顶点向人物斜上主光的三个采样点发射射线，以实际发片BVH判断遮挡，再按实际面部UV插值成遮罩。该路线与作者的屏幕头发深度实现不同，属于本地几何采样近似；它能独立证明哪些脸部位置被刘海挡光。暖色阴影通过独立色乘处理，不直接把脸乘成灰黑。

鼻部形体使用本模型鼻尖顶点定位的自制UV遮罩，保留原鼻口线、表情及Aksiniya既有SDF。它不是原游戏FaceMap，也不冒充真实鼻子投影。

v9只生成4290静帧且出现银发黑块，已判废；v11先恢复正常材质并核图，再扩展为上述动态序列。视频当前状态以current_state为准，不能用这份研究记录代替实际渲染完成证据。
