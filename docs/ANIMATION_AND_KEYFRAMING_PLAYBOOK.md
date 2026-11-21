# 动作数据、模型驱动与局部K帧

本页连接MMD输入、Blender动作机制与表演设计，供后续AI选择处理层级。2026-11-18新增指南，不表示当前双人的动作已重新制作或全曲通过。基础与插件阅读见[八项学习](GOO_MMD_EIGHT_FOUNDATIONS_2026_11_18.md)，模拟细则见[物理手册](PHYSICS_MOTION_PLAYBOOK.md)。

## 先查数据，再决定是否K帧

| 现象 | 先查什么 | 适合的处理 |
| --- | --- | --- |
| 全程头发／肢体错位 | Rest／Pose、导入比例、骨名映射、父子关系、辅助约束、错误Action或重复驱动 | 修数据与绑定；不要用每帧偏移掩盖根因。参考[伊科尔发型修复](IKHOR_HAIR_ALIGNMENT_STILL_REPAIR.md) |
| 脚滑、手未接触、双人触碰不准 | 根运动、IK目标／Pole、角色比例、动作时序、接触对象 | 保留主体动作，局部约束或白名单骨骼修订；进出接触都要核 |
| 手势／视线／口型缺少表达 | 原VMD是否含Morph、选中根对象导入是否完整、目标与节拍 | 数据完整后局部K帧；先明确角色意图和看向哪里 |
| 关节塌陷、单一姿态袖穿 | 权重、蒙皮算法、修改器顺序、形态键组合 | 权重／局部corrective，不能把全部几何问题推给动作。参考[局部修形](LOCAL_CORRECTIVE_SHAPES.md) |
| 衣发持续抖动、停止后弹飞 | 初始互穿、碰撞体、关节自由度、双重求解、预滚 | 在物理输入副本修求解，不在已烘焙工程重复Build |

## 统一的动作数据记录

记录源PMX／VMD／FBX、模型根和骨架的明确名字、缩放、fps／fps_base、源帧段与实际秒、Action与Slot、NLA条带、Morph入口、IK状态、骨骼／对象空间、当前模拟或烘焙状态。换动作、骨架、时序或缩放后重新评估物理，不能复用旧角色缓存。

MMD Tools导入与本机RNA为准。默认根对象可扩展到骨架与Morph，只有骨架不等于含全部表情；30→60fps需同时处理关键点与柄，单改输出fps不等于重定时。现成相机优先；修改动作会影响原相机适配时，只记录所需核查，不自动替换用户保留的镜头。

## K帧的设计顺序

[Pixar合作教育页面](https://sciencebehindpixar.org/pipeline/animation)把动画解释为角色表演，关键姿态和中间运动共同表达情绪。这给本项目的启示是：先写“角色想做什么、何时发生转折”，再改曲线；平滑本身不是表演目标。

1. **标记动作意图与事件。** 起势、主要姿态、接触、重心转移、收势；舞蹈另记拍点／歌词，优先保留原编舞。
2. **检查关键姿态的可读性。** 看剪影、手脸遮挡、视线、双人关系与支撑；当前以静帧组审阅，不宣称已经判断整段节奏。
3. **定义局部修订范围。** 骨骼／Morph白名单、帧窗、改动原因和进出边界，保留原Action。不能未经校准直接把已有动画骨架重绑为MMR。
4. **检查过渡与轨迹。** 记录中间姿态、腕部／脚部轨迹和关节转向；不要把所有关键帧统一变成Bezier、统一加缓动或逐帧打满键。
5. **最后处理次级运动与修形。** 不让毛领、袖摆或眼部形变夺走主要手势；动作变更后更新受影响的接触、物理和投影证据。

## 曲线、Action与NLA

官方入口：[Keyframes](https://docs.blender.org/manual/en/5.2/animation/keyframes/introduction.html)、[F-Curve Properties](https://docs.blender.org/manual/en/5.2/editors/graph_editor/fcurves/properties.html)、[Actions／Slots](https://docs.blender.org/manual/en/5.2/animation/actions.html)、[NLA Sidebar](https://docs.blender.org/manual/en/5.2/editors/nla/sidebar.html)。Actions全文已在前轮读；本轮新增关键帧、插值及NLA资料，实际获取层级见[账本](research/DESIGN_FOUNDATIONS_2026_11_18.json)。

- Constant用于保持／离散切换，Linear用于明确匀变，Bezier通过柄设计速度变化；插值与帧外外推是不同问题。自动柄不能保证无过冲或接触稳定。
- 修改哪些通道就核对哪些通道；动画旋转表示、IK切换和已有约束可能影响插值结果，不能只看一个Euler分量曲线就判断轨迹。
- Action及Slot绑定要对应真实数据块；NLA的Action源帧与场景Strip帧不同，Scale／Influence／Blend／Extrapolation也分别起作用。直接改源Action可能影响其他使用者。
- 不把“使用NLA”自动当安全非破坏流程。新修订需要验证Replace／Add／Combine等混合方式适合具体通道；没有验证叠加语义时，先在独立Action副本做有限修订。
- IK、约束、实时物理与骨骼烘焙不应重复施加同一运动。静态矩阵吻合只证明抽样姿态，不能替代连续运动检查。

## 最小交付与拒绝条件

交付源动作身份、变更通道／帧窗、关键姿态及边界对照、未改通道保持结果、接触／穿插说明、保存重开结果。只输出静帧时明确速度、抖动、过渡尚未验收；用户以后要求动态时再做对应范围核查，不自动生成样片。

遇到根运动漂移、IK跳变、视线乱转、表情重复、接触滑动、双人物理交叉污染或动作出边界，回到数据／驱动层查原因。不能用更多关键帧、更强平滑或重新烘焙代替诊断。
