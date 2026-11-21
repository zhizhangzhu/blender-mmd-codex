# 局部 corrective：变形顺序与修复边界

2026-11-14，外部文字阅读笔记，服务伊科尔弯腕袖口故障。实际制作、固定SHA、失败候选及检查范围见 [伊科尔袖口修复](IKHOR_SLEEVE_REPAIR.md)；本页不修改工程、预设或当前制作状态。

本轮读完四个官方手册主题的正文，共五页（Shape Keys引言及Workflow、Armature、Smooth Corrective、Rigid Body引言），另核对Blender `v5.2.2`的一处源码函数。网页标题实际为 **Blender 5.3 Manual**，本机为5.2.2；手册内容属于版本有差异的阅读证据，源码顺序核对属于5.2.2证据，均不等于本轮运行验证。没有播放视频、看图推断效果或启动Blender。来源、读取方法、版本与正文指纹见 [来源账本](research/SLEEVE_CORRECTIVE_EXTERNAL_2026_11_14.json)。

## 相对形态键是位移叠加，稀疏的是我们的数据

Relative Shape Key按其reference key计算加权位移，reference通常是Basis，也可以是其他键。多个键会累计；value超过1或小于0也可外插。因此“两个键各自不超过1”并不保证组合幅度不增大，也不保证两键互不抵消。[Shape Keys Introduction](https://docs.blender.org/manual/en/latest/animation/shape_keys/introduction.html)

若所有新增键都明确相对Basis，可写成下式；这是对手册的记法归纳，不能套给任意reference链：

```text
x_mix = x_Basis + Σ value_k × (x_key_k - x_Basis)
```

Blender标准shape key存储已有顶点的位置，所有键包含同样的顶点集合。Workflow也建议先固定拓扑。**本案JSON只导出398个非零delta，不表示Blender内部只存398点，更没有证明节省渲染时间。** 稀疏导出的价值是限制编辑区域、便于审计和复制；导入时仍需在原拓扑上建立完整键。[Shape Keys Workflow](https://docs.blender.org/manual/en/latest/animation/shape_keys/workflow.html)

Workflow区分了从Basis新增键与New Shape from Mix：后者包含现有键的混合。由此得到本案的操作约束：专用corrective从Basis开始，只写新增delta；不把带表情的当前混合结果当作另一个独立修形再叠上去。该页对Mix的说明也不能作为“自动逆解Armature”的依据。[Shape Keys Workflow](https://docs.blender.org/manual/en/latest/animation/shape_keys/workflow.html)

## 针对姿态做修形，不代表在Armature之后求值

Blender `v5.2.2`的`BKE_modifiers_get_virtual_modifierlist`先取得对象modifier链，最后把mesh的虚拟ShapeKey modifier放到链首；它也位于该函数建立的旧式虚拟Armature之前。对本案普通mesh链，可据此确认：**相对形态键先混合，随后Armature把结果蒙皮到姿态**。这不是读取面板列表顺序得出的猜测。[官方源码 modifier.cc，620–661行](https://github.com/blender/blender/blob/v5.2.2/source/blender/blenkernel/intern/modifier.cc#L620-L661)

```text
Basis + 原Morph + 专用corrective
                ↓
           Armature蒙皮
                ↓
      后续modifier／生成描边壳
```

这解释了一个实际风险：在弯腕后的世界空间找到“向外推12mm”的方向，不能直接把这个向量写到rest／mesh-local键坐标里。骨骼和对象变换会再次作用于它。对权重固定的普通线性混合蒙皮，可在某一参考姿态把单点写成`y = Jx + t`，目标位移满足`Δy = JΔx`；因而需要把目标位移映回`Δx`。这是结合源码顺序的数学推论，`J`必须包含有效骨权重及对象坐标变换，不是只逆乘手首骨矩阵。

本案原型代码确实先断言Armature未开`use_deform_preserve_volume`，再构造加权蒙皮的逆映射；见 [corrective_prototype](../scripts/ikhor_sleeve_repair_v1.py)。它是特定LBS、固定权重和参考帧的实现。官方手册说明Preserve Volume使用四元数保体积；**本轮未验证该开关开启时的逆解，也未验证多Armature、额外非线性modifier或任意缩放下的复用**。[Armature Modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/armature.html)

若将来复用，应先核对实际求值链、蒙皮方式和坐标空间，检查逆映射的病态情况，再用实际求值点验证目标位移；不能把`inverted_safe()`有返回值当作拟合正确。条件数筛查是后续建议，本轮未新增这一检查。

## Corrective Smooth修畸变，不替衣袖做接触约束

官方用途是借助rest参考平滑高畸变，典型位置在Armature之后。可用vertex group限制区域；Only Smooth用于预览内部平滑，Pin Boundaries保护边界。它也可能损失体积，手册提供Scale等控制，而不是承诺自动恢复服装设计。[Smooth Corrective Modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/corrective_smooth.html)

Rest Source有两条不同路线：Original Coordinates依赖原网格与输入具有相同顶点数；若前面有Subdivision或Mirror等构造型modifier，手册要求使用Bind Coordinates。由此推导，绑定参考是输入状态的一部分，换stack或拓扑不能只照搬旧bind数据。Solidify生成的壳也不能直接当作原29959点的索引集合。[Smooth Corrective Modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/corrective_smooth.html)

该页没有提供袖布对手部的碰撞目标或最小间隙约束。对本次“弯掌切过少数袖面”的故障，平滑可能改善折痕，也可能收缩或把邻面拉入皮肤；这是需要对照验证的推断，不能据名字把它当作防穿模工具。**v6没有新增Corrective Smooth，本轮也没有做其静帧、绑定或连续测试。**

## 骨权重、刚体和局部shape分别解决什么

| 故障特征 | 优先检查 | 方法边界 |
|---|---|---|
| 原生无物理姿态也在同类关节弯曲中失形 | 顶点跟随哪些骨、权重、rest形状 | 权重决定骨对点的影响，会影响整条动作；更改后要扩大姿态回归范围 |
| 原生正常，物理后袖口整片偏移／翻折 | 刚体绑定、关节参考、碰撞筛选、预滚、骨驱动模式 | 刚体解算产生位姿，不能凭更大碰撞体自动得到所需袖面形状 |
| 大形与动态已稳定，极端弯腕仍有小片接触失配 | 局部rest delta、过渡区域、驱动范围 | corrective可补指定形状；固定帧窗只覆盖该段，不是通用姿态空间解 |
| 主要是蒙皮后的局部扭曲或收缩 | Armature方式、有限区域平滑 | Corrective Smooth值得单项试验，但需另查体积、缝、边界和接触 |

上表是方法选择的归纳。其官方依据是：Armature按同名骨vertex group的权重影响点；Preserve Volume改变变形方式；刚体只改变物体位置和方向，本身不使物体变形。[Armature Modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/armature.html)、[Rigid Body Introduction](https://docs.blender.org/manual/en/latest/physics/rigid_body/introduction.html)

在MMD衣袖中，刚体经骨骼间接驱动加权网格，这是本机案例的结构，不是刚体手册对MMD模式的承诺。v6先修参考与接触并真实局部重算，再保留右侧有限旋转、补左侧小片shape；不能把三者统称纯物理。左侧坏面约75–92%跟肘、袖骨影响较低，解释了为什么硬转袖骨要很大角度才推动该小片。此处几何和权重数值来自 [本机案例](IKHOR_SLEEVE_REPAIR.md)，不来自官方教程。

## 把一次修形限制在可验证的范围

以下是对本案可复用方法的整理，不是Blender官方给出的通用预设：

1. **固定输入再归因。** 锁PMX、动作、fps、相机、旧Morph与modifier；同帧比较原生、原物理和局部候选。把侧壁大翻折与设计内衬尖口接触分开定位。
2. **独立重建顶点范围。** v6从源权重重建左573点，只398点有非零delta；Basis／UV／weights不动。同rest、同骨权重的UV缝重复点同步，不能只推一侧，也不自动合并本来分离的结构。
3. **检查面，不只检查点。** 本案存在顶点在skin外、边和三角面内部仍横切弯掌的情况。最近面法线可作候选方向；要加边／面内采样、邻域平滑和真实三角求交，不能把单点signed距离当全袖穿透深度。
4. **限制幅度及组合。** v6最大rest差分约12.028mm；多shape若未来确有必要，应检查每帧叠加后的实际位移与表面，不只查各shape单独的最大值。权重和不超过1可作设计约束，但不构成碰撞保证。
5. **限制时间或姿态域。** v6只有一个左键，4210/4218/4225/4233对应0/1/1/0，水平Bezier柄平滑进入退出。它是这段动作的时间窗；改变剪辑、重定时或换VMD必须复核。pose driver／多姿态插值仅为未来候选，本轮未制作或测试。
6. **分开技术证据与画面判断。** 独立重开核旧曲线／handles、原Morph、非袖骨和白名单外求值点；连续扫描作为定位，再看原shader、原相机的无模糊近景及最终beauty。raw可能可见交线并不等于不透明侧壁可见破口，统计清零也不等于自然。

## 本轮获得的知识与尚未实测项

新增阅读把三个容易混用的概念分清了：**稀疏delta文件与全点shape存储；姿态下拟合与Armature前求值；变形后平滑与接触避让。** 新核实了5.2.2链首ShapeKey源码顺序，也读到Corrective Smooth的rest／bind条件和潜在体积损失。

本机已测仅引用 [v6袖口案例](IKHOR_SLEEVE_REPAIR.md)：14体真实局部物理、右tanh限幅、左1键／398点、49项独立差分、303帧技术扫描，以及600张腕部诊断图和并排片300帧解码；Root与独立复核看过每侧33时点联系表及关键生产shader图。它没有证明全段零交线、全曲适用、多shape体系、Preserve Volume逆解或Corrective Smooth已掌握。

截至本页记录时，新原生300帧beauty仍在重新渲染，不能将无模糊腕部诊断片称为新成片。最新交付状态以 [current_state.json](../catalog/current_state.json) 及最终交付报告为准；本页不因研究完成推进生产关卡。
