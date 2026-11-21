# Goo、MMD Tools与插件协作：八项基础的第一轮指南学习

2026-11-18，按猪猪要求完成上一轮列出的八个方向的基础阅读。新增实读25篇Blender 5.2官方手册正文，另读MMR作者图文教程、本机Paper随包README，并针对MMD Tools／咖啡工具／Paper的相关源码段落补证。既有Goo官方功能页、Normal Edit、灯组与色彩资料复用前轮笔记，不重复计为新增全文阅读。

这是八个方向的第一轮知识覆盖，**不是全部功能熟练、全部插件验证或人物质量达标**。本轮没有打开生产工程、修改角色、重做物理或生成视频。两张新球体静帧和数值实验只用于核实基础机制。

## 1. 坐标空间与法线

官方指南：[Geometry](https://docs.blender.org/manual/en/5.2/render/shader_nodes/input/geometry.html)、[Vector Transform](https://docs.blender.org/manual/en/5.2/render/shader_nodes/vector/transform.html)、[Normal Map](https://docs.blender.org/manual/en/5.2/render/shader_nodes/vector/normal_map.html)；[Normal Edit](https://docs.blender.org/manual/en/5.2/modeling/modifiers/normals/normal_edit.html)复用前轮已读正文。

- Geometry的Position／Normal等使用世界空间；Normal是着色法线，True Normal是实际面方向。两个输出不能当作同一种“模型法线”。
- 点的位置、方向向量、法线分别选Vector Transform的Point／Vector／Normal；方向不应带平移。涉及非均匀缩放时尤其不能用普通方向变换代替法线变换。
- 切线法线贴图需使用匹配的UV与Non-Color解释；Object／World法线的跟随条件不同。法线图约定和本机节点是否提供对应选项要核实，不凭贴图名猜。
- Normal Edit的Radial／Directional、目标、Parallel、Mix Factor、顶点组和偏转限制要分别理解。面部法线只控制受光方向，不会移动刘海，也不能代替刘海真实投影。

**新增本机证据：** Goo 5.2.1社区构建`0051aee03764`中，两个球分别输出原始Half-Lambert和世界着色法线RGB。只添加Directional Normal Edit，Mix=0.65，目标方向约(0,-4,4)，Parallel开启。左右输出的线性RGB最大差分别为0.538208／0.505493；两球求值后的顶点坐标最大差均为0。独立进程重开后全图线性RGBA最大差0。

因此，前轮“Shader Info覆盖Normal插口无响应”不等于整个Goo不能用修改后的网格法线。新实验确认的是另一个入口。演示有意使用较强法线偏转，球体明显趋平，不能直接套到人物。随头部旋转、骨骼变形、局部顶点组和复杂发束的效果仍待验证。

## 2. 对象数据与修改器

官方指南：[Linked Duplicate](https://docs.blender.org/manual/en/5.2/scene_layout/object/editing/duplicate_linked.html)、[Apply](https://docs.blender.org/manual/en/5.2/scene_layout/object/editing/apply.html)、[Modifier Stack](https://docs.blender.org/manual/en/5.2/modeling/modifiers/introduction.html)、[Node Groups](https://docs.blender.org/manual/en/5.2/interface/controls/nodes/groups.html)。

对象、Mesh、Material、内部Node Group和Action是不同数据层。对象能独立移动，不代表网格、材质或动画独立。材质复制后，组节点仍可引用同一节点组；需要按编辑意图决定哪些共享、哪些复制，不能统一“全部独立化”。

修改器通常按从上到下求值，视口与渲染可见性也独立。Apply把结果写入数据，不能当普通显示开关；在已绑定／动画的骨架上随手应用变换，并不会自动修正全部动画与约束。中途Apply非首个修改器也可能改变语义。

**新增本机证据：** 对象复制确实共享Mesh和Material；再分别复制Mesh与Material，内部Node Group仍共享；显式复制该组后才独立。另用一个全权重立方体、一根Y轴转60°的骨骼、X向0.5位移，对比`Displace→Armature`与`Armature→Displace`，对应求值顶点最大距离约0.500000。实验说明顺序重要，不表示人物应该采用其中某个固定次序。

节点组接口的显示范围不自动等于数据Clamp，嵌套组也不是复制外层后必然独立。界面滑块、链接数据、内部数学节点三个层级分别检查；前者是本轮官方阅读结论，未新增所有组类型的本机测试。

## 3. MMD材质与贴图语义

官方／作者来源：[MMD Tools README](https://github.com/MMD-Blender/blender_mmd_tools#readme)，配合本机4.5.14的`core/material.py`、`operators/fileio.py`相关段落；Blender补充[Image Texture](https://docs.blender.org/manual/en/5.2/render/shader_nodes/textures/image.html)。MMD作者链接的Wiki未能读取，未把它登记为已读指南。

必须保留底色、材质Alpha、贴图Alpha、Toon、球面加算／乘算、双面和材质Morph的关系。当前源码中球面模式有不同默认色、混合与坐标路径；SubTex也不是普通Sphere UV。不能用一张主贴图代替全部输入，再用Bloom补回丢失细节。

当前MMDShaderDev的Color输出位于贴图／Toon／球面颜色组合之后、BSDF受光之前；Alpha另行组合。它适合作为保留原材质语义的接口，但**并非未经处理的原始albedo**：源码也包含Ambient／Diffuse组合与Clamp。迁移前要看实际工程组内部，保留原来与Morph相关的连接，不反复执行全材质转换。

Image Texture的Vector、UV、Interpolation、Extension和图片颜色空间都会改变采样。Repeat／Extend／Clip不是同一种边界处理；Alpha的解释和使用也要与输出链一致。控制图依据通道含义设置，不能按Lightmap等文件名决定。

## 4. Goo受光与阴影

来源：[Goo官方功能指南](https://www.dillongoostudios.com/gooengine-features)复习；新增[Blender Light Objects](https://docs.blender.org/manual/en/5.2/render/lights/light_object.html)，EEVEE灯影参数复用[前轮官方学习](GOO_BLENDER_FOUNDATIONS_2026_11_18.md)。

先分清形体信号、投影、环境和镜面，再决定各灯参与哪一部分。Half-Lambert每组先用一盏主光；灯组的受光与阴影选择、材质的自阴影ID分别核对。同对象中的刘海投脸可能归到Self，不能整路删除。

光源Exposure、场景显示Exposure和材质增益处在不同位置。Sun由旋转定方向，移动位置不会像点光那样改变光向与距离；Spot的Angle／Blend决定光锥覆盖与边缘，不能用来代替物体投影软硬；Area尺寸也不能与功率混为一谈。官方Normalize说明同样需要先核本机开关。

实践顺序是关后期看单主光，分别输出形体与遮挡，再加环境／补光／轮廓光。头发投影过宽先查方向、发脸距离和投影精度；脸发平先查形体／法线与补光贡献，不先加总曝光。本轮没有新增人物布光试验。

## 5. 卡通材质的基础设计

官方指南：[Color Ramp](https://docs.blender.org/manual/en/5.2/render/shader_nodes/converter/color_ramp.html)、[Map Range](https://docs.blender.org/manual/en/5.2/render/shader_nodes/converter/map_range.html)、[Layer Weight](https://docs.blender.org/manual/en/5.2/render/shader_nodes/input/layer_weight.html)、[Principled](https://docs.blender.org/manual/en/5.2/render/shader_nodes/shader/principled.html)。色带Widget的独立详情页本轮获取失败，只有检索片段，未计入25篇全文。

阈值决定分界位置，软过渡决定边界宽度，颜色决定阴影的色相／亮度，强度决定混合比例。Map Range的输入域、目标域、插值和Clamp分别控制；不能将HDR综合受光不经标定就当固定0–1形体值。色带Alpha也需要单独保留。

Facing／Fresnel依赖观察角度，用于边缘权重，不会自动生成来自指定灯的方向轮廓光。若要有光向，应另结合光向与遮挡；本轮未新制作该组合。发束高光也要有分区与方向依据，不能让整个头顶都变成自发光白块。

Principled中Roughness主要控制反射分布；Metallic=1取消普通漫反射并以底色影响金属反射。皮肤、布料、金属、宝石应各保留适合的响应。Sheen／Coat／SSS与Emission承担不同职责，官方注明Cycles Only的项不能直接搬到Goo。学过接口不等于这些完整层次已经在本机测试。

## 6. MMD骨架与动画求值

官方指南：[Armature](https://docs.blender.org/manual/en/5.2/modeling/modifiers/deform/armature.html)、[Bone Relations](https://docs.blender.org/manual/en/5.2/animation/armatures/bones/properties/relations.html)、[IK](https://docs.blender.org/manual/en/5.2/animation/constraints/tracking/ik_solver.html)、[Shape Keys Workflow](https://docs.blender.org/manual/en/5.2/animation/shape_keys/workflow.html)、[Actions／Slots](https://docs.blender.org/manual/en/5.2/animation/actions.html)。

- 同名骨与顶点组建立变形关系；Preserve Volume改变蒙皮算法，不是无代价的“质量开关”。空权重、骨集合与骨的变形职责要区分。
- 静置骨方向、Pose、父骨继承和非均匀缩放会共同影响结果。Connected、Local Location、Inherit Rotation／Scale不应随意统一。
- IK影响整条链；Chain Length=0并非不影响骨，而是扩展到祖先。Pole控制弯曲方向，Stretch需要额外条件；IK还有特殊求值顺序，不能按普通约束列表位置推断。
- Basis新增键与New Shape from Mix不同；多个形态键会组合。修形前保留拓扑与reference，不能把当前表情再烘进corrective重复叠加。
- Action内有Slot；对象、相机数据、Shape Keys等可使用不同Slot。只看Action名字或全局关键帧数不能确认正确绑定，NLA里的使用也要另查。

MMD Tools本机源码确认：选模型根导入可覆盖骨骼和Morph；只选骨架不包含全部表情。PMX骨名映射、缩放、Treat Current Pose as Rest、Create New Action／NLA、Update Scene Settings分别核对，后者会更新30fps。MMD追加变换还使用辅助骨／约束，不能把它们当重复项清理。此处是源码核对，未重新导入当前人物或更改fps。

## 7. 刚体、关节与缓存

官方指南：[Rigid Body World](https://docs.blender.org/manual/en/5.2/physics/rigid_body/world.html)、[Collisions](https://docs.blender.org/manual/en/5.2/physics/rigid_body/properties/collisions.html)、[Dynamics](https://docs.blender.org/manual/en/5.2/physics/rigid_body/properties/dynamics.html)、[Generic Spring](https://docs.blender.org/manual/en/5.2/physics/rigid_body/constraints/types/generic_spring.html)；另对照MMD Tools作者已知问题。

碰撞体是否参加World的Collection／Constraints、使用什么形状与源几何，比单纯提高求解次数更先检查。Sphere／Capsule／Hull／Mesh在稳定性、精度和margin上不同；凹Mesh不是总比简单碰撞体好。碰撞分组也不等于人物所在的普通集合。

刚体线性／角阻尼和关节弹簧阻尼不是同一控制。弹簧与平移／旋转限位要配合，不能把阻尼推到最大当通用修复。Substeps是每帧内步进精度，Iterations是每步约束求解；Speed／fps／缓存范围则关系到时序。

保存文件、顺序预滚和计算、缓存烘焙、骨骼视觉烘焙及独立重开是不同步骤。换动作或改碰撞体后旧缓存不能自动有效；烘焙后还要避免实时求解与动作重复驱动。MMD Tools作者说明其IK／Bullet并非与MMD完全等价，因此当前既有局部物理证据不能推广到全曲。本轮只读指南，没有新增物理模拟或动态认证。

## 8. 合成与插件协作

官方指南：[Alpha Over](https://docs.blender.org/manual/en/5.2/compositing/types/color/mix/alpha_over.html)、[Alpha Convert](https://docs.blender.org/manual/en/5.2/compositing/types/converter/alpha_convert.html)、[Glare](https://docs.blender.org/manual/en/5.2/compositing/types/filter/glare.html)、Node Groups；显示转换复用前轮五张控制图。

渲染层通常使用预乘Alpha。Straight／Premultiplied必须与实际RGB一致；为调色暂时转Straight后应正确转回，不能反复乘Alpha造成黑边，也不能把RGB黑背景视频当RGBA。前景／背景顺序和Factor需要明确。

Glare的Threshold负责选亮部，Smoothness负责提取过渡，Strength调效果量，Size调扩散范围，Clamp限制输入高亮，三个输出分别是合成图／效果／高亮。辉光不会产生物体投影或真实轮廓受光；Sun Beams也不能直接宣称是完整体积光。这些新接口以在线5.2文档为阅读范围，具体社区版逐项行为仍需核验。

| 工具 | 本轮来源与学到的边界 | 使用前实际检查 |
| --- | --- | --- |
| MMD Tools | 作者README＋本机4.5.14源码；负责MMD输入与语义，不能期待任意Rigify／Link流程天然兼容 | 模型根、Morph、材质、辅助骨、动作／Slot、版本 |
| 咖啡工具 | [作者README](https://github.com/kafeijk/mmd_kafei_tools/blob/master/README.md)及本机1.9.2迁移源码；语雀详情需要登录，本轮未读到 | PMX→PMX／PMX→ABC路线、比例与静置拓扑；材质是关联，UV／权重／法线／修改器有独立开关 |
| Paper助手 | 本机2.5.0随包README及Toon Shadow源码段落，不把随包说明当独立官网认证 | 输出直接连接Principled等适用条件；现有复杂NPR可能被跳过；记录原Surface与World，核对添加／移除范围 |
| MikuMikuRig | [作者基础图文](https://www.bilibili.com/opus/1167803398842482693)正文已读，未播放视频、未核对全部图片 | 当前重构版与旧0.56不同；按骨名映射和顺序匹配，先检查／调整元骨骼；约束设置决定原骨如何跟随控制器 |

咖啡源码的材质迁移使用关联操作，不等于复制后互不影响；部分PMX→ABC路径包含比例假设。Paper的Toon Shadow使用普通Diffuse→Shader to RGB综合受光，并要求其支持的Surface结构，不能当作通用Goo Shader Info替换器。MMR作者指南也没有保证任意角色都无需校准。

## 学完后怎样用于项目

现在可以更有依据地安排：先保留MMD输入语义和数据关系，再在副本分别测试局部法线、真实刘海影和材质响应；确认每项有效后才封装参数。真实角色还需做固定光下转头、固定头移光及不同相机的静帧组，检查法线是否抹平体积、影子是否脱离发束、共享材质是否误改另一人。

本轮实测入口为[基础机制脚本](../scripts/study_goo_mesh_normal_foundations.py)，产物在`D:/codex/output/Goo-MMD-Eight-Foundations-2026-11-18/`。正文阅读／源码推断／球体验证／人物静帧／动态／用户美术认可保持分级。眼透继续搁置，字幕黑边与投影保留，人物v6及既有生产文件未改。
