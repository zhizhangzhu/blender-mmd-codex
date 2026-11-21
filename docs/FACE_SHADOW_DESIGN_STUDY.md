# 脸影设计与几何遮挡共存：局部修形的算子位置

记录日期：2026-11-13。状态：**一手文字／源码研究；没有实装或渲染验证**。目标仍是改善原神／鸣潮式的面部图形可读性，本次没有获得这两款游戏的原始着色器，也没有据此认证风格质量。

本轮先读了 [人物手册](CHARACTER_NPR_PLAYBOOK.md)、[已有三个实验](NPR_NEXT_EXPERIMENTS.md)、[同日一手续读](NPR_PRIMARY_STUDY_2026_11_13.md) 和 `presets/quality/duet-character-layers-v1.json`。没有打开当前 `.blend`、读取新贴图或审看新帧；当前节点状态采用任务提供的基线：随头轴的平整脸部 Diffuse 探针与上游 SDF 在一次 palette 前取 MIN，身体保留原法线。阿克西妮娅有 FaceLightmap；空缺配套游戏控制图。本次不重复把旧 E1 的左右阈值图、E2 法线包络列作新方案。

## 新增证据及其边界

仅使用下列三个作者来源。页面访问于 2026-11-13；分支／网页会变化，**没有锁定提交版本**。GitHub 提交 API 访问失败；Raw 与 HTML 返回的文件行数也不同，因此以下用函数／变量定位，不把网页行号当成稳定版本证据。来源与失败记录见 [账本](research/FACE_SHADOW_DESIGN_STUDY.json)。没有下载完整仓库、视频或字幕。

| 一手来源 | 本轮实际核对 | 能支持什么／不能支持什么 |
| --- | --- | --- |
| [xSnowFlakesx：Genshin_Face_Render.shader](https://github.com/xSnowFlakesx/GenShinAvatarRender/blob/main/Genshin_Face_Render.shader) | Raw 中头轴投影、镜像采样、局部遮罩和 `shadowAttenuation` 的赋值顺序。 | 作者自己的复现实现，非米哈游源码。局部 SDF 提亮位于遮挡相乘之前；但这里同名遮挡量实际来自屏幕深度偏移。 |
| [congyuxiaoyoudao：EndfieldLighting.hlsl](https://github.com/congyuxiaoyoudao/Endfield_Character_Rendering/blob/master/Assets/Shaders/Library/EndfieldLighting.hlsl) | Raw 中 `LightningFaceSDF` 的 SDF、`mainLight.shadowAttenuation`、下巴区域与 ramp 顺序。 | 作者把场景阴影和局部形体分色在 ramp 前合并，并用单独区域限制下巴形体响应。它是另一作品的社区实现，不能证明原神／鸣潮采用同法。 |
| [MooaToon 作者：Control the Shape of Shadows](https://mooatoon.com/en/docs/Tutorial/ControlTheShapeOfShadows#custom-hair-shadow) | Self／Other IDs、Shadow Bias、Screen Space Hair Shadow 的文字说明。 | 作者明确区分按材质 ID 控制的遮挡和依赖当前视角的屏幕发影；未检查网页插图或运行 UE 示例。 |

**本轮新增点是局部修形的接入位置，以及对“发影”输入真实性的核查。** 没有发现可以直接替换现有 SDF、且已证明更好的新算法。

## 光向与左右切换：公式决定控制方式，美术决定边界

第一份源码先从头部前、右方向构造上轴，把光向投影到头部水平面，再用其与右轴的夹角决定镜像采样；角度到阈值还经过三次曲线。由此可见，**阈值图必须与生成时的角度曲线配对**；不能把其中的曲线直接接到阿克西妮娅原 FaceLightmap，并假设相同角度对应相同鼻影。[作者源码](https://raw.githubusercontent.com/xSnowFlakesx/GenShinAvatarRender/main/Genshin_Face_Render.shader)

以下是本工程的数学推断，不是作者宣称已经解决的问题：若光几乎平行头部上轴，水平投影长度趋近零，直接归一化／求夹角会失去稳定的左右依据。将点积 clamp 到 [-1,1] 只处理 acos 的数值域，不能给零向量恢复方位。未来检查顶光、仰头时应记录这个长度；不要通过逐帧记住上一次左右来遮掩问题，以免同一帧因求值顺序得到不同结果。本轮不新增顶光模型，也不重写现有左右算法。

在正前方过零时，还要区分“UV 左右选错”和“左右图本来不连续”。前者修坐标约定，后者修同一正面角度的美术输入；增加灯能量不能修复两者。现有两角色的 incoming／toward-key 光向约定须各自保持，不统一取反。

## 鼻口眼周：先定位是哪条链造成斑块

第一份源码允许局部遮罩将 SDF 响应推向亮区，然后才施加它的遮挡量。这提供了可借鉴的**上游局部修形**位置，不等于应给五官统一免阴影。第二份源码另外使用下巴区域控制形体响应，说明区域设计是独立输入；它不能成为恢复本工程失败的全脸几何法线方案的依据。[SDF 修形源码](https://raw.githubusercontent.com/xSnowFlakesx/GenShinAvatarRender/main/Genshin_Face_Render.shader)、[下巴区域源码](https://raw.githubusercontent.com/congyuxiaoyoudao/Endfield_Character_Rendering/master/Assets/Shaders/Library/EndfieldLighting.hlsl)

下面是本工程提出的美术检查标准，**不是对游戏或参考作者工作流的事实描述**：

| 区域 | 需要美术决定的内容 | 不能交给公式自动决定的内容 |
| --- | --- | --- |
| 鼻梁／鼻翼 | 侧光时鼻影是否并入脸颊大暗面，哪些窄区需要保留转折。 | 由底图肤色阈值猜出“正确鼻影”，或把鼻部所有暗处抹平。 |
| 嘴周 | 嘴周分色是否产生与表情无关的黑岛；修形图避开口腔与嘴缝内线。 | 将阿克西妮娅 `Face ink | Mouth crease` 当作脸影一起提亮，或用肤色盖住口腔。 |
| 眼窝／眉侧 | 眉眼图形与大块脸影的边界关系，左右及表情极值是否一致。 | 让眼周恒亮、让刘海透明，或把真实刘海遮挡删除。 |
| 下颌／颈部 | 下颌形体暗面与下巴向脖子的投影是否各自清楚。 | 把示例的 G 通道语义套到本模型未知通道，或恢复全脸原法线硬分段。 |

若孤立黑岛只存在于 SDF 调试值，可尝试下面的小样；若它已经出现在原生综合 Diffuse，下面的修形不能修复，应该记录为另一条链的问题。不能从最后肤色截图反推责任输入。

## “发影”的三种证据不能混写

`Genshin_Face_Render.shader` 在片元函数里把 `shadowAttenuation` 初始化为 1，开启宏后用偏移屏幕深度计算它；该处并未取 `mainLight.shadowAttenuation`。因此不能因为名字或它在 SDF 后相乘，就称其是原生灯光投影；该段也没有作者页面中 MooaToon 那样的 Face／Hair ID 筛选。[实际赋值](https://raw.githubusercontent.com/xSnowFlakesx/GenShinAvatarRender/main/Genshin_Face_Render.shader)

MooaToon 的屏幕发影则还要求脸／头发 ID，作者明确说明它依赖当前视角的头发轮廓；其光线追踪 ID 控制与此是不同功能。加大 Shadow Bias 会按距离排除近处遮挡，并可能突现，不能拿它当“只去鼻口自影、保留全部发影”的通用开关。[作者说明](https://mooatoon.com/en/docs/Tutorial/ControlTheShapeOfShadows)

当前普通 Blender 的综合 Diffuse 已能响应某些真实遮挡，但仍混有法线、灯数、衰减与间接光；它不是纯主灯可见性。屏幕空间发影和 UE 的材质 ID 射线能力也不是加一个普通 Shader 节点便已获得。本轮继续使用现有路径，不增加屏幕发影，不叠第二份刘海暗层。

## 一个可关闭的小样：只在 SDF 上做局部修形，随后保留原 MIN

实验名 `exp_face_design_relief`。**仅是未执行的方案**：将来在独立诊断副本中只选阿克西妮娅脸部皮肤分支，保持现有 FaceLightmap、轴向、灯组、一次 palette、AO、五官／金属／Alpha 分支。空不同时套用。

定义 `S` 为当前进入 MIN 的 SDF 亮部响应，`D` 为同一 MIN 的原生综合 Diffuse 响应，二者范围 [0,1]；`E` 是新画的局部修形许可图，Non-Color，0 为不修、1 为允许修形。`e` 为总开关，`k` 为固定强度：

```text
S_art = S + e * k * E * (1 - S)
F_test = min(S_art, D)
最终仍只用现有 palette(F_test)
```

这是本工程的试验表达式，不复制作者 Shader。`e=0` 或 `k=0` 回到原 SDF；`E=0` 的像素保持原响应。`E` 不能从 Color 亮度自动提取，也不能将未知 FaceLightmap 通道改名冒充它。开始只画一处已确认属于 SDF 的窄小问题区；具体鼻、嘴或眼旁哪处需要修改，应由未来调试图和美术观察决定，不能本轮预判成片有缺陷。

**关键约束是 `F_test ≤ D`。** 即使局部放宽 SDF 暗面，原 MIN 已捕获的原生暗部仍会限制结果；这比在 MIN 后提亮或把 `form_bias` 加进综合 Diffuse 更有明确边界。但它只保护这个现有信号，不能消除补光淹没遮挡的问题，也不能证明分离出纯几何可见性。若 `D` 本来就是斑块来源，小样应无效，而不是再提升 `D` 的下限。

将来最小验收顺序：

1. 在相同输入上单独预览 `S／E／S_art／D／F_test`；总开关关态须对齐原图，只比较 `k=0／0.25／0.5`。这些是诊断档位，不写进生产预设。
2. 固定姿态与灯，只添加／移走一块独立代理遮挡，比较同一 `D` 下开关前后结果，检查修形不会越过原生暗部限制。代理测试不是头发动画验收。
3. 再检查真实刘海边界与手过脸、左右灯光过零、仰俯头和张嘴连续段。嘴缝、眉睫与口腔不能被该图改变；未修改的皮肤区域应无差异。
4. 若原 SDF 明暗大形被掏碎、左右不一致、遮罩随表情暴露接缝，或只靠提亮才好看，淘汰该图。通过后仍须正式动态检查和用户美术评价，不能由不等式代替观感。

本轮完成的是源码职责核对与这个单开关提案。没有节点实现、贴图制作、Blender 静帧／动态测试或工程重开结果；没有改当前质量参数，也没有恢复 Goo 或取得空缺失的游戏输入。
