# 蓝金婚礼：射灯、局部体积、光晕与彩色字幕

2026-11-12 后续发现本页旧审片MP4缺少明确色彩标签；已保留原文件，新的阴影／色彩流程见 [人物接地与播放器色彩](SHADOW_GROUNDING_AND_PLAYBACK_COLOR.md)。不能仅凭PotPlayer与其他播放器的截图差异判定某一方设置错误。

2026-11-12。根据猪猪的新反馈，在已提亮的礼堂上增加婚礼氛围：阿克西妮娅侧以蓝色为主，空侧以金色为主。沿用现成场景、人物材质、物理、相机和已修好的字幕边界，制作同一段 4140–4439 的五秒 1080p60；不据此恢复全曲长渲。

## 学习来源与落实

| 原始资料 | 实际读取范围 | 本工程的使用 |
| --- | --- | --- |
| Wellesley College [Continuous Lighting Equipment Reference Guide](https://www1.wellesley.edu/sites/default/files/assets/departments/art/files/continuouslightingequipmentreferenceguide_0.pdf) | 4 页正文，主要为第 3 页三点布光 | 主光塑形、较弱补光保留暗部、后侧光分离轮廓；角色照明与婚礼环境灯分开 |
| Blender 官方 [Light Objects 源码](https://projects.blender.org/blender/blender-manual/raw/branch/main/manual/render/lights/light_object.rst) | 完整可访问的官方 rst | 用 Spot 的角度、边界柔化和方向形成光区；发光尺寸与阴影软硬分别控制 |
| Blender 5.2 [Glare 官方说明](https://docs.blender.org/manual/id/5.2/compositing/types/filter/glare.html) | 官方检索返回的正文；英文入口读取失败 | 用 Threshold 选高光、Size 控制扩散，单独取 Glare 输出再合成 |
| Blender [EEVEE Volumes](https://docs.blender.org/UATEST/manual/en/dev/render/eevee/render_settings/volumes.html) 与 [5.2 Volume Scatter](https://docs.blender.org/manual/sl/5.2/render/shader_nodes/shader/volume_scatter.html) | 官方检索正文；接口以本机为准 | 有边界的介质中散射成束，不用 World 雾笼罩脸；密度与前向散射需要一起观察 |

三点布光是职责分工，不意味着整座礼堂只能有三盏灯。资料中的实拍灯具功率不能直接当作 Blender 辐射功率照搬；位置、距离、尺寸和材质都会改变最终观感。本工程保留每人已链接的 key／fill／rim，实际能量为 100／12.5／120，另有柔光、顶光和环境灯。这个数值不是通用照度比例；人物是 NPR，也不能把 Emission 表面当作普通漫反射。

观海子《亲亲小狐狸》仍用于主体分离、柔和亮边和画面层次的参考，见 [既有连续画面观察](FOX_STAGE_ART_DEEP_STUDY.md)。本轮没有恢复作者原灯光或 MME；HIMEHINA 官方字幕也不属于观海子的 PV Kit。

## 婚礼灯光与氛围

参数：`presets/stages/hesperides-blue-gold-wedding-v1.json`；构建：`scripts/prepare_blue_gold_wedding.py`。输入是 `MMD-Duet-Soft-Top-Rim-v1\production-v2`，保留其已经提亮的场景和人物照明。

- 两盏蓝／金 Spot 位于 (−6,18,11) 和 (6,18,11)，向人物后方走道交汇，16°、Blend 0.55。光束来自 Volume Scatter，不是透明发光锥，也不是后期画上去的二维光带。
- 后方体积范围为 x±10、y=2.5–23.5、z=−1–13，密度 0.009，anisotropy 0.35；旧的后方空气物体隐藏，避免叠加。人物约在前方 y=0，前脸不包进新增介质。
- 两灯能量 9000，volume_factor 3.5；表面 diffuse_factor 0.12、specular_factor 0.1。这是明确的美术控制：提高光束可见度，同时避免把人物和地面照过曝，不称为完全物理一致的功率配置。
- 其他灯的新体积贡献设为 0，避免整片礼堂都被普照雾冲灰。原工程的 EEVEE 体积参数沿用本机值：tile 8、32 steps、未启用体积阴影；所以不能声称光束已具备完整建筑遮挡。实际设置记录在 preparation JSON。
- 走道两侧加入 12 个暖金微光装饰，半径 0.035、Emission 9。它们提供可见亮点和散景，不是新增 12 盏实体灯，不替换作者礼堂。

静帧经过四版：v1 过弱，v2 散射过宽，v3 过窄且偏到人物身后，最终 v4 把两束移向中央并平衡宽度与强度。中间版保留用于排错，不作为最终预设。婚礼方向是蓝与香槟金、明亮走道、微光和柔和高光，不重新把整个背景压黑。

## 光晕分开控制

舞台从 Render Layer 中排除人物后提取高光：Threshold 1.2、Strength 0.2、Size 0.038；扩散后再次保护人物区域，再加回最终图。人物则使用原有 `StageArtRim` AOV：Threshold 0.08、Strength 0.6、Size 0.03。脸部和五官在该 AOV 中保持黑色，避免把脸整体发光。光晕会在亮边附近扩散，不等于脸部所有最终像素都绝对不变。

两个 Glare 都只取独立 `Glare` 输出，避免把原图重复加亮。**修改最终合成后，还必须把 `Caption cache | beauty` 接到同一个最终输出**，否则无字幕原生视频有新光晕，但字幕成片会拿到旧 beauty。重开检查将这两条路由是否相同作为硬验收项。

控制图分别关闭后方散射与本轮新增光晕。散射关闭图仍保留射灯对表面的直接照明；光晕关闭图保留源材质高光和前版光晕。不能把它们称为“全部灯光关闭”或“所有辉光关闭”。

## 蓝金字幕

配置 `presets/typography/duet-blue-gold-wedding-v1.json`，复用同一 HIMEHINA／Studio LaRa 官方动画。保留五组准确时间、版式与固定前后关系，详见 [字幕稳定流程](DUET_CAPTION_STABILITY_AND_LIGHTING.md)。

- 亮色部分从左侧蓝色过渡到中部象牙色，再到右侧金色，呼应两位角色。
- 白牌里的黑字映射为深海军蓝／深铜色，仍是完全不透明的深色字；不重新把它当透明孔。
- 单独字形使用同一蓝金色带，保留内部孔洞；深蓝细边与少量 4 像素柔光帮助阅读。
- 色带固定在官方源画面坐标中，随原动画整体排版；没有逐帧随机颜色，也不根据人物遮罩换颜色。人物遮挡仍只由整个 cue 的 front／behind 决定。
- 发光、描边与文字先作为一组，再应用整体前后遮挡。后景字幕的柔光也不会绕过人物保护区。

`stable_caption_layers.py` 的 palette 和 glow 为可选项；旧配置不填时保持原行为。回归检查包括深色彩字仍不透明、字形内孔透明、前景不随遮罩变化和后景保护连续边缘。黑底 MP4 并不是原始 RGBA，这些方法仍不能恢复白牌外原本不可见的黑色原画。

## 交付与复用

根目录 `D:\codex\output\MMD-Duet-Blue-Gold-Wedding-v1`，正式工程为 `production-v4\Franken_Duet_Blue_Gold_Wedding.blend`；v1–v3 仅为中间实验。

1. 独立后台运行构建脚本；所有旧 File Output 静音。人物隐藏后重烘礼堂 GI，检查九时点的骨骼／相机／焦距，并打包贴图。
2. 用 `verify_caption_master.py` 加 `--softlight-profile`、`--wedding-profile` 独立重开，核对姿态、灯光、体积、脸部排除和缓存路由。
3. `render_duet_sample.py --caption-cache-dir 新缓存` 渲染 300 个原生帧；不把后期放大、插帧或进程启动当作完成。
4. 用新蓝金字幕配置合成缓存，合入指定原声 FLAC 的 68.983333–73.983333 秒；字幕源仍从 4141 帧开始。
5. 无字幕视频在 `lighting-sample-5s-v1`；最终字幕视频为 `captions-5s-v1\Franken_Duet_5s_Wedding_REVIEW.mp4`。核对完整解码、音轨、切换连续帧和代表画面，状态以交付 JSON 为准。

Blender 工程包含三维灯光、装饰、光晕和遮罩源；最终字幕由 Python 第二步合成，不会自动显示在 Blender 视口。完整双人全曲、竖屏与全曲逐字排版仍未在本轮制作。技术通过不等于猪猪已认可美术效果。署名沿用 [双人来源](CREDITS_FRANKEN_DUET.md)，官方文字动画始终署 HIMEHINA／Studio LaRa。
