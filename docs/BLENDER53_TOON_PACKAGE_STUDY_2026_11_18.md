# 作者5.3卡渲节点：原生语义与Goo迁移边界

2026-11-18启动，11月19日续读。猪猪补充两个本地节点包和作者教学视频，允许必要的独立静帧试套；本研究并入[面部影形学习](FACE_SHADOW_DESIGN_STUDY_2026_11_18.md)。`gpt-6.1-sol xhigh`亲自阅读正文、源码和图像并作技术判断，低档代理只执行固定采集／提取／原生命令。当前Goo人物候选不因研究自动替换。

## 输入及实际阅读范围

| 输入 | 已确认事实 | 证据范围 |
| --- | --- | --- |
| `D:/BaiduNetdiskDownload/5.3卡渲节点.zip` | SHA256 `bbfb8d2ee4840ef10b4278e0ed10d2a2c9071d7ff27e476b7d0b3b81156ad6d5`，只有一个约16.2MB blend条目 | 私人别名`package53/author-toon.blend`，SHA `d9696f8f165823e17fb542ce4b157351c657c79e958aefb87fe677d4e71f80fe`。现已在官方5.3和Goo5.2分别只读审计，并完成两张5.3静帧；没有保存修改后的blend |
| `D:/BaiduNetdiskDownload/一些或许有用的节点.zip` | 264302334B，SHA `b2d6d8bb1170952bf0208f0a099e51036c193fc8ff641878df1c033284669b4a`，16项 | 只读清单、原名编码候选和唯一231B TXT；未把全部blend或嵌套插件称为已读／已验证 |
| `D:/JiJiDownload/blender5.3三渲二节点分享/1.blender5.3三渲二节点分享(Av117620598639649,P1).mp4` | SHA `d5633274b5511f57896f8c5ec4bf34609f5f92083bd7e7f2b2d17367e71c0978`，283.65秒、1920×1080／60fps、H264与AAC，无字幕流 | 亲看8、55、105、155、205、255、275秒七张原尺寸静帧；能读到部分画面字幕。未播放整段、未听写音频、未取得完整字幕 |

原包内名字按ZIP实际解码存档，另以CP437字节转GB18030给出中文候选，二者不混同为原始编码保证。包内Text已实际读到模型署名：提供miHoYo、改造观海，联系名为B站观海子；包含非商业、禁止再配布和拆件等限制。**这不是节点作者的身份／许可证明。** 本轮不重新分发第三方完整blend、节点库、模型或教学文件。

第二包清单中有独立5.3子目录、较简单且文件名提示仅推荐一盏平行光的方案、旧模块化节点及嵌套`fast_toon_shader.zip`。其中一个文件名明确提示旧发影方法在5.3失效；这是作者的文件名提示，尚未做原生复核。231B说明文字表示旧插件现在主要用于视图层主光绑定、旧节点使用较卡。本轮不安装该插件，也不因文件名相似就把第二包的“新卡渲节点”当成与第一包相同内容。

## 七张作者画面的具体所得

| 视频时点 | 实际所见 | 不应作的推断 |
| --- | --- | --- |
| 00:08 | 标题栏Blender5.3.0；芙宁娜与遮挡方块，画面字幕说明物体投影 | 不能从截图得出脸材质的完整连接或包内数据完整性 |
| 00:55 | 当前编辑的是灯的Emission→Light Output；画面说明自定义灯光属性用途 | 不能把灯节点当成人物shader，或当作普通恒亮人物Emission |
| 01:45 | 实际材质图中可见输出位置、范围、阴影、Power、灯色、方向等的“光照”组件和闭包相关节点 | 须原生读取组内实际bl_idname／接口，不能只凭中文组名识别底层机制 |
| 02:35 | 脸材质的法向接入“面部法线”组，SDF开关未勾选 | 此时预览不能称SDF开启效果 |
| 03:25 | SDF开关勾选，鼻部影形与未启用时不同，另有柔和阴影／UV翻转／忽略仰角等接口 | 两帧相隔50秒，其他设置也可能改变；这不是只改SDF的受控对照，接口存在也不证明每项适合另一张脸 |
| 04:15、04:35 | 作者继续调人物主光／辅助灯，脸、发、服饰随之变化；编辑器仍有灯Emission链 | 不从两帧反推唯一最终灯光参数、完整阴影实现或动态稳定性 |

这些画面支持一个学习次序：先保真读取作者原工程，分清脸法线方案与SDF可选方案，再检查各灯如何进入材质。作者预览的明快感同时受到模型、材质、灯和背景影响，不把所有差异归给一个SDF节点。

## 已实读的官方5.3新机制

[官方5.3 EEVEE说明](https://developer.blender.org/docs/release_notes/5.3/eevee/)正文和下列四篇手册均已实际读取。发布主页的本地全文采集返回403，未绕过；官方搜索摘要只用于定位发布版本，不当作整页学习。

| 官方节点／机制 | 本轮确认的语义 | 与当前Goo比较时要保留什么 |
| --- | --- | --- |
| [Light Accumulation](https://docs.blender.org/manual/en/5.3/render/shader_nodes/shader/light_accumulation.html) | 对影响表面点的每盏灯求值其输入，按对应光照影响累加；各类Light输入还可成为对应合成pass | 不能用先把所有灯求和后再套一次色带，声称等价逐灯的非线性分色 |
| [Light Info](https://docs.blender.org/manual/en/5.3/render/shader_nodes/input/light_info.html) | 无输入或对象选择参数，读取当前正在求值的灯；Color、Power、世界Position。Power的定义含除以pi | 它与Goo中选择指定灯对象的同名节点不是相同契约；实际功率单位和补偿须核 |
| [Light Evaluation](https://docs.blender.org/manual/en/5.3/render/shader_nodes/input/light_evaluation.html) | 可提供Position／Normal／Roughness，输出反射Factor、Mask、Direction、Distance；Sun的方向和距离有专门约定，Factor含乘pi | Mask表示距离截断／聚光锥许可，不能冒称几何投影。方向、距离与阴影分别核；本机Goo旧Normal插口实验不能移作5.3证明 |
| [Shadow Raycast](https://docs.blender.org/manual/en/5.3/render/shader_nodes/input/shadow_raycast.html) | 当前灯的遮挡mask：1无遮挡、0完全遮挡；可设评估位置与柔度，偏出物体包围盒可能需要调整材质Max Distance | 它是独立阴影入口；名称本身不证明使用硬件光追、角色ID隔离或自动排除面部自阴影 |

这些Material Lighting节点必须处在Light Accumulation输入树中，才能处于逐灯求值上下文。官方功能列表还列出Light模式Attribute及Light Space的Vector Transform；本轮尚未以完整手册或源码核清这两项全部细节，不称全部掌握。

这说明“5.3新增NPR节点”确有官方基础，但并不意味着可以把新节点直接Append进Goo5.2.1。原生节点、相似名称组、图中单灯近似和实际EEVEE实现要逐项比较。优先复用影形设计、UV数据和已理解的数学模块，保留当前Goo相机、MMD Color／Alpha与当前角色独立数据。

## 原生只读审计与最小实验约定

实际采用官方Blender5.3.0 Windows便携版，build `02f0899d78e3`，ZIP为425299259B，SHA256 `3ac567a63d59d9934f7b9213bfb27ba05760e1fb366f8f55c381573ec3eabfa8`，与[官方校验清单](https://download.blender.org/release/Blender5.3/blender-5.3.0.sha256)匹配。安装在本轮私人临时目录，独立CONFIG／SCRIPTS，不改全局软件关联、用户偏好或Goo生产默认运行时。初次慢速下载停止后保留前160432128B；其余采用四个不重叠的官方HTTP Range，逐段206／Content-Range校验，合并后才核最终SHA和解压，没有另下载第二份重叠全文件。

`scripts/inspect_blender53_toon_package.py`以输入SHA保护，关闭脚本自动执行并用`use_scripts=False/load_ui=False`打开包；静音继承File Output，导出实际节点、插口、连线、图片、模型与文本，不渲染、不保存。初版JSON以tree.name作键，多个Material内部的同名树会覆盖；已修为含所有者的唯一键，保留初版，**v2才是本轮材质追线依据**。

实际模型为`【芙宁娜_荒】_mesh`，基础29989顶点／37255面；原生求值含描边为59978顶点。刚体world为停用，表面修改器为Armature、头部定位GN和描边，没有本轮新物理。作者保存帧16064、相机输出竖屏1080×1920，Standard、曝光0。

20张image数据块中含两个Viewer；18个FILE里17个已打包。唯一未打包零尺寸的`未命名.png.001`只在`Material/材质`的孤立图像节点出现，**没有任何输出连接**，不在本实验主脸链；未硬补白图。不能把它改写为“所有数据块贴图齐全”。

## 真正连到脸的分支

本轮亲读`Material/颜`的完整连线、`面部sdf`和头部法线／定位相关组，以及大组中相应控制、灯与输出路径；没有把大组283个节点的所有支路、第二包所有方案登记为精通。

- 主脸Surface来自`新卡渲着色器`；底图`颜.png`经原有皮肤渐变进入，法向来自实际连上的`面部法线`组。另一个名为`面部法线2`的组节点在该主脸材料中没有接到输出，不能因名字更复杂就认定当前在用。
- `头部定位`GN存储`面部法线`、`头顶朝向`、`人物左侧`、`前面`等命名属性；主脸法线组读取后按Normal从Object转World。它是着色用的方向数据流程，不表示把脸网格变成球。
- SDF接口是闭包：传入选择后的UV，采样已打包、Non-Color的`Avatar_Girl_Sword_LittleIdolGirl_Tex_Face_SDF.png`的R。组内读当前Light Evaluation方向，结合前／左属性选择左右UV，以`0.5-0.5*dot`构造阈值；柔和分支是半宽0.025的SMOOTHSTEP。这些是该包的具体设置，不是通用脸参数。
- “忽略日光仰角”的实际候选分支将光向的Z置0后归一化，坐标约定仍要核；不能由此推广为任意含roll头姿都已正确处理。
- 主光角色由LIGHT模式Attribute的`主光`读取灯Data标签；保存的`人物主光`Data有该值1。灯名本身不能替代标签协议。
- **保存的主脸`使用SDF阴影=true`，`受到阴影=false`。** 作者场景中身体受方块投影、包里有Shadow Raycast，不等于主脸已接收真实刘海影。这个保存值也不是要求所有风格化脸都关闭几何阴影。

## Goo5.2能复用到什么程度

原生5.3审计无undefined节点；相同源文件在Goo5.2.1构建0051aee03764只读打开后，出现22个undefined：`新卡渲着色器`19个、`面部sdf`1个、测试`Material/材质`2个。日志明确提示较新503.31文件有数据丢失风险；这里的文件版本元组不能当作软件“5.3.31”版本。

更关键的是**同名节点会变义且丢链接**：原生`ShaderNodeLightInfo`的可用输出为Color／Power／Position，在Goo读回为Light Color／Light Power／Perceptual Power；原生Color已有链接，Goo对应记录已变未链接。原生有一个禁用的内部LightIndex插口，不是可供用户指定灯对象的等价输入。LIGHT属性枚举也不能在该Goo接口中保留。

| 分类 | 具体范围 | 本轮证据边界 |
| --- | --- | --- |
| 可作为复用候选的数学／数据流程 | 头部坐标、局部法线属性、UV左右选择、阈值与颜色职责 | 例如面部法线／头部定位／球型法线组三组在Goo中节点数与链接数仍分别为3/2、8/12、21/26；这里只证明相应结构保留，尚未在Goo人物渲染认证 |
| 必须按当前角色重建契约 | 当前主光选择、世界光向、完整头轴、face数据通道／极性、局部许可与几何发影组合 | FaceSDF组自身含一个丢失的Light Evaluation；阿克应保自有FaceLightmap，伊科尔应制作／核自己的影形，不能换用芙宁娜图 |
| 不能原样用于当前Goo | 新Light Accumulation／Light Evaluation／Shadow Raycast、LIGHT属性的逐灯语境，以及整套新shader | 删除未定义节点、绕过丢失链接、或仅因文件exit0就称兼容，均不成立。通用闭包节点没有一律落在undefined清单里，也不能反向声称全部闭包都不支持 |

## 本轮实际完成的两张静帧

交付为`D:/codex/output/Goo-Face-Shadow-Study-2026-11-18/author53-face-ab-v1/`中的`author53-face-sdf-off.png`和`author53-face-sdf-on.png`，由`scripts/render_blender53_author_face_controls.py`在原生5.3实渲，xhigh逐张看过原PNG。

同一作者frame16064、同一新诊断相机／灯／姿态、850×900、64 samples、PNG16、Standard曝光0，仅切主脸`Socket_29`的SDF布尔值。相机按该脸几何建立近景；作者合成后期与序列器关闭、DOF／MB关闭。**这是隔离材质的对照，不是作者视频或完整成片的还原。** 受真实阴影开关false保持不变，没有加入眼透。

实际可见差异集中在鼻部棕色泪滴状影块：开启出现，关闭消失；脸的大面、发束、服饰和姿态保持。原PNG解码RGB最大差0.3603555、平均差0.00020566，差>0.001的像素约0.279%。求值几何和灯指纹保持，源blend SHA未改；没有交付修改后的第三方工程。

判断为**分支生效得到验证，艺术质量提升未得到证明**。在这个保存灯向下，不能仅凭鼻部多一块颜色便说SDF版更好，也没有验证完整脸颊分区、左右扫光、仰角、转头或动态。本轮就此收敛，不增加更多3D渲染。

原生还保留三个`fast_toon_sun_angle`的旧Scene driver无效警告。选定主脸SDF的方向来源已追到5.3 Light Evaluation，但未完整证明这些旧driver对全场景所有分支均无影响；因此不称作者整套工程已完全复原。两张对照图共同保持这些状态，不安装旧插件来消警告。

## 对当前两人的下一步

先只读核`final-v1`保留SDF与新增NoL是否使用同一实际主光、光向正负和完整头轴，再决定影形修订。阿克已有匹配图，先分离原SDF、暖form和4290发影定位重复压暗；伊科尔没有已验证SDF，先在自身UV设计有序影形，不复制芙宁娜或阿克的图。作者包的脸受影false不作为当前两人禁用真实发影的依据。

本轮没有修改当前Goo候选、当前runtime配置或既有动作／物理，没有把两张芙宁娜研究图登记为两人生产质量提升；当前角色仍待猪猪美术评价，参考质量未达到。
