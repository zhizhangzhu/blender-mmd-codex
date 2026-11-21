# 双人人像重新打光：本轮实现、定位与复用步骤

2026-11-15。本轮把已读的逐层布光、分类亮边与脸影原则，实际接入Clean双人工程并进行静帧迭代。目标是让深蓝衣亮面更清楚、肤色保留粉紫暗面、白衣与金属保持层次，并减少人物背后的灰雾；观海子仍为核心方向，paierer本地《奥黛塔&沃雅妮莎 _ 愛包ダンスホール》18／120／195秒是本轮局部观察目标。没有取得参考作者的Shader、灯组或工程。

本文记录实现与已定位的问题，不把CPU图检查、单帧渲染或参数移植称为艺术达标。

| 项目 | 实际状态 |
| --- | --- |
| 最终候选工程 | `D:/codex/output/MMD-Portrait-Relight-v1/production-v1/Franken_Duet_Portrait_Relight.blend`；SHA256 `5381cf656108ec9b2eb72d241a684c6836a8a181eb84bfeaf88616b19f117044` |
| 最终静帧 | 同目录`complete-4290.png`；3840×2160、128samples、原相机／DOF，MB关闭；SHA256 `66dafe63a1e75451d0f188bc518d7758c349adfc6a1d92636a10320cadbc9ea6` |
| 独立保存／重开QA报告与结果 | 同目录`master-verification.json`：338项通过；11个Actions、193个mesh对象／273个对象、3个armature、134块材质、8736个旧节点、95张已打包贴图，零missing unpacked文件 |
| 人工观察范围与尚存问题 | 主任务实际查看v2／v5／灰度与无镜面诊断／v6／v8、最终4K的1920预览与原生伊科尔脸裁图；独立QA另看原生双人头部及金带。阿克脸仍偏柔平，伊科举手粉紫暗面较重；非逐像素全图人工检查 |
| 猪猪美术认可 | 待评价，未宣称达到参考或游戏品质 |

本轮不包含新的五秒视频、全曲渲染或物理模拟，也没有增加动作、几何与动态质量的认证范围。源工程所继承的袖修与物理边界继续按[原制作记录](IKHOR_BOLD_WEDDING_PRODUCTION.md)追溯。

## 输入与入口

固定源为`D:/codex/output/MMD-Clean-Game-Characters-v1/production-v2/Franken_Duet_Clean_Game.blend`，SHA256为`0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4`。每轮从该源独立打开，使用新输出目录；不在已经追加模块的工程上再次安装，不重跑历史场景builder。礼堂、角色配色、婚礼主题与两条细光弧已隐藏的要求继续保留。

| 文件 | 本轮职责 |
| --- | --- |
| [prepare_portrait_relight.py](../scripts/prepare_portrait_relight.py) | 总入口；核源SHA、注册MMD相机、处理舞台／真实灯、调用人物模块、诊断或静帧渲染；可另存新候选工程 |
| [portrait-relight-v1.json](../presets/lighting/portrait-relight-v1.json) | 本轮版本化参数；实际使用值以各次输出的`preparation.json`快照及SHA为准 |
| [portrait_key_fill.py](../scripts/portrait_key_fill.py) | 21块精确白名单材质的主辅形体与一次有效palette；伊科尔主脸可选解析代理 |
| [portrait_rim_ink.py](../scripts/portrait_rim_ink.py) | 18块分类rim、限定既有描边颜色；beauty与原AOV消费者一起接入 |
| [portrait_fur_control.py](../scripts/portrait_fur_control.py) | 阿克西妮娅`毛领`共享材质的独立形体／palette链，覆盖颈毛领及腕部同材质区域 |
| [verify_portrait_relight.py](../scripts/verify_portrait_relight.py) | 独立只读打开源与保存候选，按明确差分许可核对完整Actions、几何、相机、材质、图像与合成；不重放生产builder |
| [render_portrait_light_controls.py](../scripts/render_portrait_light_controls.py) | 前轮A／B／C控制图及相机driver／File Output保护工具；不是本轮通用发布器 |

例如，在已授权的独立后台进程中，以新目录调用总入口：

```powershell
& 'E:/tools/Blender Foundation/Blender 5.2/blender.exe' --background --python-exit-code 1 `
  --python 'D:/codex/workspace/blender-mmd-codex/scripts/prepare_portrait_relight.py' -- `
  --output-dir 'D:/codex/output/MMD-Portrait-Relight-v1/新的静帧目录' `
  --variant complete --frame 4290 --width 1280 --samples 48
```

`--save-project`只用于另存候选；信号诊断选项`--diagnostic face-and-no-specular`禁止与保存工程组合。诊断图把伊科尔原NPR Emission临时接为解析soft form灰度，并关闭角色灯的镜面贡献、绕过该脸物理混合，用于定位信号，不可作为美术交付图。

`production-v1/reproduce`保存本次实际运行脚本、模块和JSON，SHA对应`preparation.json`；随后仓库builder只整理了import顺序，渲染数学未变。4K原图未用图像生成或绘图工具修补，预览／细节图只缩放／裁切。最终图与原版1080p64samples、相同4290／镜头／DOF／显示变换的整套修改对照分别留存；这不是单变量实验。

独立检查严格比较原Actions及关键帧／插值柄、几何／UV／权重／shape／material slots、旧节点与Alpha及相机。灯位改变引起363处旧driver求值变化：完整driver曲线、表达式和targets仍相同，并按当前灯／头世界坐标独立复算，而非笼统豁免全部socket。隐藏8体积后暂停求值的派生矩阵，在不保存副本临时unhide并更新depsgraph后与源一致；保存的隐藏状态另核为true。核查没有精确重放或认证全部新增Shader数学，也不认证动态。

另用`render_saved_portrait.py`在新进程直接重开保存工程，不运行迁移模块，实际重渲1920×1080／64samples。相对保存前v8同规格图，逐通道最大误差均为1/255，平均绝对误差为`.005616/.003960/.004985`个8bit级；见`verification/reopen-render.json`。这是本帧保存／重开渲染一致性，不是全动画稳定性。重跑归档builder时须显式`--settings <归档目录>/portrait-relight-v1.json`，其默认参数路径原本针对repo布局。

## 先分清真实灯与NPR信号

保留链仍以MMDShaderDev `Color/Alpha`为输入。这里的Color包含原贴图与球面等合成语义，并非已经提取出的游戏Albedo。人物由计算后的颜色经Emission输出，同时保留原有物理闭包；Emission输出本身不保证照亮场景。

真实主灯参与原Diffuse综合探针。该探针带相对距离补偿，并含灯形、衰减、法线、间接光及几何遮挡，**不是独立visibility或游戏投影贴图**。`response_range`仍采用固定标定，默认保留源`.055–.34`，没有逐帧自适应；换灯后必须看实际信号，不能从节点名字推断未饱和。

真实fill／rim原有`diffuse_factor=0`继续保留。因此把fill瓦数提高不等于抬起Emission型NPR的暗面。本轮另在身体形体信号中使用真实fill对象的位置作为艺术方向：

```text
keyForm = smoothstep(keyNoL区间, N·Lkey)
fillForm = smoothstep(fillNoL区间, N·Lfill)
form = keyForm + fillStrength × fillForm × (1 - keyForm)
paletteFactor = form × combinedResponse
NPR颜色 = 保留的MMD颜色 × 一次有效palette → 原有一次短AO → 高光／rim
```

fill仅补key暗侧，仍处于原综合响应和原AO之前；没有增加第二个AO、Diffuse探针、Emission闭包或最终颜色亮度下限。深蓝布、皮肤与白布分别选色带和辅光量；伊科尔白布沿用已存在的HSV许可与金／青排除，不把深衬、饰物一起抬白。默认参数和本轮preset覆盖值须分开记录。

## 主光必须核头空间，而非只看相机空间数值

使用已有`Quality | actor | head origin/forward/up`对象构造完整姿态基：

```text
F = normalize(headForward - headOrigin)
R = normalize(cross(F, headUp - headOrigin))
U = normalize(cross(R, F))
headDirection = normalize(R × x + F × y + U × z)
```

`key_direction_head`分量顺序为**right／forward／up**；相机空间则为right／up／朝向观察者，二者不能混用。保留当前灯到头部的实际距离，再放置灯并朝向该头部位置。当前总入口只在构建静帧时据该帧头姿态放灯一次，没有给灯新增逐帧追头动画。

本轮曾把主光在相机空间向侧面移动，伊科尔头空间forward分量却从约`.6522`增加到`.7301`，脸反而更正受光。之后改用头空间`[.67,.54,.50]`，并同步重标脸形体区间。教训是记录实际`L·R / L·F / L·U`，不可只用相机坐标中X更大来证明脸部已形成侧光。完整forward与up共同参与，可保留歪头roll；不能以世界Z轴临时拼一张始终朝前的脸影贴片。

## 两个人的脸保留不同输入条件

阿克西妮娅继续使用模型原FaceLightmap red的动态SDF阈值、既有局部鼻UV许可内同图邻采样修复，以及原嘴缝。原`.38 + .62 × SDF`形体再乘综合受光；本轮调整有效palette和灯向，没有用新解析代理替换她的原SDF，也没有给`颜+`叠层伪造SDF。

伊科尔没有已验证的生产SDF。其原soft face form使用头前向受光再加`.60`形体软底，在当前光位常接近同一个亮值，不能通过调整很低位置的palette点自然出现半脸阴影。本轮为精确主脸材质`颜.001`新增可关闭的原创解析代理，眉眼、嘴与其他features不进入该替换。

```text
x = dot(PositionWorld - headOriginWorld, R) - centerOffset
u = clamp(x / halfWidth, -1, 1)
Nproxy = normalize(F + R × u × curvature + U × upBias)
proxyNoL = dot(Nproxy, normalize(keyPositionWorld - PositionWorld))
proxyForm = formFloor + (1 - formFloor) × smoothstep(NoL区间, proxyNoL)
paletteFactor = 选定的新／旧form × combinedResponse
```

它是头空间光滑曲面法线近似，避免直接把鼻口网格Normal硬分段放大成脏块；不称SDF、真实曲面法线、真实投影或偏移发影实现。`formFloor`只位于综合响应与AO之前；不是最终脸色的恒亮下限。真实遮挡近似和原AO仍在后续链中，也仍保留各自的技术局限。

接口为`actors.ikhor.face.analytic_form`，模块默认`enabled=false`，本轮preset显式开启。原soft form分支保留；`set_face_proxy_gain(scene, 0)`直接接回原form输入，`set_gain(scene, 0)`直接接回本模块拦截前的原palette输入。关闭默认时，新旧模块所有有效上游图已做逐项相等检查；这项检查证明可复现性，不证明美术改进。

### 以实际可见脸部校准区间

4290帧的伊科尔主脸材质有1126个实际评估顶点。已从变形后的网格取局部点，只乘一次evaluated对象`matrix_world`进入世界空间，再减实际头原点并投到R轴；此帧原对象与evaluated对象矩阵均为单位矩阵。旧审计并未混用源local与posed world。

- 全主脸横向范围为`[-.079423,.085137]m`，中心约`.002857m`，半宽约`.082280m`；本轮采用`half_width=.0823`、`center_offset=.002857`。
- 全材质范围还包括被头发遮住或不可见的侧部；用非描边角色多边形BVH初次命中近似筛选相机可见点，得到585点。此近似没有完整Alpha／描边／GPU可见性语义，不能认证所有像素。
- 初始相机空间主光加`range=[.18,.72]、floor=.45`时，可见点proxyNoL中位`.75645`，soft form中位`1`，`72.82%`可见点大于`.95`；真正暗的外侧大部分被发或侧面遮住。GPU灰图近白与该分布相符。
- 改用头空间主光及`range=[.40,.78]、floor=.40`后，同一585点proxyNoL的p25／中位／p75为`.37164/.57577/.76896`，soft form为`.40/.66635/.99851`；大于`.95`的比例降为`30.77%`。这是区间校准证据，最终外观仍须实际渲染判断。

CPU审计保存在私人临时目录`D:/codex/temp/MMD-Portrait-Relight-v1/`：`ikhor-face-dimension-audit.json`、`ikhor-face-posedworld-proxy-audit.json`及`ikhor-face-posedworld-proxy-audit-headkey-v1.json`。后两项包含逐顶点坐标、NoL、soft form与近似可见性，避免只保留成功的平均值。

## 分类rim、深线与毛领分开调

新rim替换已审计的加法HDR RGB源，保留所有beauty与原AOV消费者。主要信号是`(1 - abs(N·V))^power`，再乘左右方向许可、复用的短AO接触抑制及高亮余量，最后加暖色HDR。发、深色衣、白衣和毛领各有参数；power控制覆盖窄度，HDR gain控制源强，色相、方向与接触许可另调。

阿克西妮娅另有历史SCREEN rim，模块在其自己的Fac处衰减；SCREEN Fac不当作线性HDR强度。伊科尔白布替换继续使用原白布许可与金青排除，许可外保留原rim。相机空间rim方向在安装时转换为固定世界方向，不是每帧随相机转动的自动描边灯。短AO不能代替背光可见性或depth rim，重叠处是否漏亮仍需审图。

ink只替换精确白名单中既有`mmd_edge_preview.Color`，保留Alpha、PMX描边权重、几何外壳宽度与全部独立五官节点。黑线与发光边有不同职责；本轮没有通过加粗壳体、统一黑线或扩大Glow来替代分区控制。相关依据见[方向rim账本](research/DIRECTIONAL_RIM_LIGHT_2026_11_14.json)。

毛领不能仅靠cloth参数或rim增益处理。`毛领`是颈部和腕部共享的独立fur材质，原MMD Color及其色度处理、palette、AO、rim各有实际入口；通用keyfill白名单没有包含它。新增fur模块只接其原palette输入，以当前几何Normal与实际主灯的逐点NoL塑形，可乘保留的综合响应，再让原MMD Color乘一次新palette。原贴图、球面、Alpha、物理闭包和两条rim链均保留；这不是新毛发几何或毛发散射Shader。颈毛领与腕毛领必须分别看，不能由一个颈部ROI推广到全部共享区域。

## 把物理镜面峰与NPR亮边隔离

本轮曾出现白金／衣饰亮峰，关闭角色key／fill／rim／reflection的镜面贡献后峰值消失，说明不能把所有高亮都归到rim或Glow。诊断只用于归因；正式设置分别调整真实灯的`specular_factor`，并在精确伊科尔金色HSV许可内调整既有金属roughness与physical mix端点，保留白布物理端点和原遮罩。

最终key／fill／rim／reflection镜面系数分别为`.22/.25/.30/.70`。伊科尔只在`带子、裙.001、衣领、衣.001、衣2`五块既有金许可内，把金端roughness`.39→.54`、物理混合`.44→.28`；白布端点仍是`.70/.12`。`衣饰、靴饰`有不同的源基底，未纳入此次修改，不能按文件名将七块金材质盲套同一基底。这是保留底色／metallic遮罩的定向调整，非整个人物关掉镜面。

这些控制与NPR palette、HDR rim是三条职责不同的链。总入口的`physical_highlights()`只操作已核Clean金色delta节点，不新建或全局替换闭包；具体材质名单、端点与旧值由`preparation.json`及独立重开报告核实。只关全部spec得到的诊断图，不是最终材质设置。

## 舞台中间调、空气与辉光

本轮保留指定礼堂，隐藏两个实际Volume Scatter盒与六个独立美术发光锥；已移除的蓝／金细光弧继续隐藏。先前A／B／C对照已显示中央散射造成灰亮区，单把限定rim乘2又使青边过抢，因此本轮沿减少灰雾、分类窄暖边和降低无关Glare源的方向推进。这里只针对列出的对象处理，不宣称场景已经实现完整物理体积投影，也不把关雾等同所有环境光归零。

舞台midtones属于场景线性合成美术控制：先从当前beauty亮度生成有界中间调许可，再乘`1 - 双人Crypto`，按amount混入乘色。深暗和高亮端分别留出，不做全图统一曝光变化。Crypto必须是`阿克西妮娅2_mesh,Ikhor | mesh | Ikhor_mesh`两人，并保持原透明语义；不能因全局Matte非零就认定两人都受到保护。新的grade同时连接最终Image和`Caption cache | beauty`，避免后续beauty消费者继续读旧画面。

这一后期不是物理灯或真实投影通道。最终仍须检查两人轮廓、半透明边缘及高亮附近有无蒙版边；静帧Crypto名单正确不能直接继承成新五秒字幕覆盖验收。

## 已定位的失败与复用顺序

| 现象／误判 | 实际定位 | 后续操作 |
| --- | --- | --- |
| 增加fill瓦数却难以改变NPR暗面 | 真实fill的Diffuse参与为0，Emission颜色有独立形体链 | 分别调真实物理贡献与NPR方向fill，核有效palette输入 |
| 相机空间“更侧”的主灯仍使脸平亮 | 实际头forward受光分量增大 | 记录完整头basis分量，按right／forward／up放灯 |
| 新CombineXYZ inputs刚建完为0，怀疑driver失效 | 首次depsgraph evaluation后即与目标世界位置相符，最大误差`1.49e-8` | 渲前统一`frame_set(current)`与`view_layer.update()`，核evaluated输入；不把原始零默认当失效证据 |
| 解析脸影节点存在，却仍担心没有进入beauty | 已沿主Emission活链反查，gain为1时新palette与proxy确实被选中 | 从active Material Output与具体闭包回查，不能只在整个NodeTree找可达节点 |
| raw proxy灰图近白 | 可见脸NoL区间大部分超过上限，并非world/local错误 | 同时统计全部／可见点分位、投影ROI，再调灯与band；不能只看全脸min/max |
| 白金亮峰与rim混淆 | specular-off诊断使峰值消失 | 灯的镜面因素、金色闭包端点、rim、Glow逐项隔离 |
| cloth参数不足以处理毛领层次 | fur是独立共享材质，且有独立上游palette | 单独形体／palette模块，复核颈与腕两个区域 |
| factory-only试图使用原MMD镜头 | 缺失MMD相机RNA，曾读到1mm及driver除零 | 注册已有MMD Tools再开源，核镜头、driver变量和表达式 |

可复用的执行顺序为：固定SHA与参考观察目标 → 注册MMD并打开源 → 静音所有继承File Output → 固定帧／相机／DOF／MB／samples → 分开核MMD Color、form、combined灰度、response、palette、AO、rim与物理镜面 → 先处理空气和光位，再调分区色带 → 做信号灰图与spec隔离 → 同帧beauty比较 → 另存候选 → 独立重开与人工观察。

相机不能只核对象名。正式4290源镜头为约`61.734649658mm`；使用保存偏好读取和临时`bpy.ops.preferences.addon_enable(module='bl_ext.blender_org.mmd_tools')`注册既有扩展，不保存用户偏好。沙箱内曾因扩展cache访问问题仍落入1mm，授权进程显式临时注册后恢复正确；这不是重新安装插件的理由。

本轮CPU还对完整头basis做了4140／4290／4439三个姿态各±40°roll的代理法线协变检查，以及整体旋转平移后NoL不变检查；它们证明数学实现没有误用固定世界轴，不是动作连贯性、动态阴影稳定或全片美术的验收。独立重开脚本核实际候选差分，另结合实际静帧观察；不得以模块自报的`graph_only`成功替代这些步骤。

## 本轮沿用的外部阅读依据

不重复下载教程、视频或字幕。前轮已读范围、原作者URL与未读边界分别记录在：

- [逐层摄影布光账本](research/PHOTOGRAPHIC_LAYERED_LIGHTING_2026_11_14.json)：David Hobby三篇、Joe McNally两篇正文；用于主辅分工、人物／白衣分区和主体／环境比例；课程简介不算完整课程。
- [白菜教程账本](research/BAICAI_LAYERED_LIGHTING_TUTORIAL_2026_11_14.json)：542条用户字幕全读及限定时点画面；用于逐层开灯、体积影响与Glare源检查，不把教程PBR瓦数照搬成当前NPR参数。
- [方向rim账本](research/DIRECTIONAL_RIM_LIGHT_2026_11_14.json)：亮度、宽度、方向、颜色与许可拆分；没有据此声称普通EEVEE已经取得游戏depth rim或独立阴影通道。
- [脸影设计账本](research/FACE_SHADOW_DESIGN_2026_11_14.json)：完整头轴、阈值图与真实发影职责；解析代理是本工程原创近似，未复制未验证的生成器通道或伪造伊科尔SDF。
- [paierer本地观察账本](research/PAIERER_DARK_STAGE_PORTRAIT_2026_11_14.json)：8张稀疏静帧，重点迁移浅亮肤色旁的粉紫暗面、白布灰紫分层、深线与窄暖边关系；没有连续观看或认证参考的动态稳定性。

本轮以前的三张控制图、Node Wrangler边界及研究结论见[逐层人像布光研究](PORTRAIT_LIGHTING_AND_SHADOW_STUDY.md)。
