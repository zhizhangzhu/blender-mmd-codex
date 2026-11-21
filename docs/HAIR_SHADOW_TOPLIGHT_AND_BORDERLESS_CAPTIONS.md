# 衣发阴影、柔和顶光对照与字幕去黑边

后续决定（2026-11-16）：猪猪要求恢复字幕黑边框和投影。当前重新使用原蓝金预设（1080p描边3像素、投影偏移7×7像素、不透明度.45），当前样片恢复为 `D:/codex/output/MMD-Goo-Window-Wrap-v1/quick-5s-v3/Franken_Duet_5s_GooWindowWrap_SUB_1080P.mp4`。下面的去边框制作记录与产物保留作历史对照；默认制作入口已恢复有边框版。

2026-11-16，猪猪反馈头发阴影不明显，询问顶光是否有帮助，并要求移除字幕黑边。输入为大窗版本 production-v3，SHA `ed81e7325e7ef3f47fe80dd63b53e1e0e713f7d2b93b9dd4e6e296195a350d85`。

## 同帧诊断

入口 `scripts/diagnose_goo_hair_shadow_toplight.py`。输出 `D:/codex/output/MMD-Hair-Shadow-Toplight-Study-v1`，4290帧、同一61.73465mm相机、1280×720、24 samples；继承文件输出已静音，未保存或修改生产工程。

- A-current：当前设置。
- B-no-glow：只关闭合成器Glare，保留表面轮廓与发带高光。
- C-base-shading：另关闭人物HDR轮廓和两人的附加发带高光，保留基础着色及材质本身的镜面响应。
- D-current-plus-top：恢复A后，增加一盏后上方柔光Area，位置(0,.9,4.1)、朝向(0,.4,1.3)、180W、直径2.5、浅冷白、漫反射系数.25、镜面1、体积0。没有改写人物NPR专属灯组。

四张图均实际查看。衣服袖部、胸前、裙褶及发丝之间仍能看到暗部；C比A更容易阅读头发层次。B与A的差异相对小，不能把问题全归因于后期Bloom。当前附加表面高光与宽亮边也在挤占暗部。D主要稍增强部分衣料和饰物亮面，没有明显重建头发明暗；“再加一盏物理灯”不足以保证这套Emission型NPR的头发响应。

节点证据在同目录 `diagnosis.json`：两个人物的头发样本前鬓／鬓.001，其原生Cast Shadows输出下游是rim permission／亮边链，而非基础palette；Self Shadows输出未接。基础发色保留既有形体与综合受光近似，不能称完整原生自阴影。脸部Cast确实进入独立阴影响应，但映射仅.9–1，遮挡暗化本就较弱；衣物对应映射更深。发丝形体、刘海投脸影、衣物投影与AO应分别判断，节点存在也不等于画面层次足够。

本轮结论：保留强轮廓目标，但后续应优先分离发带亮面和发缝暗部，并校准刘海遮挡；柔和后斜顶光可作辅助，尚未整合到生产。诊断只覆盖4290静帧，不代表转头、全段阴影或新布光已验收。

## 字幕去黑边

新预设 `presets/typography/duet-blue-gold-wedding-no-border-v1.json` 从原蓝金版复制，仅关闭额外描边和投影：stroke=0、shadow opacity=0。保留原字幕色块内的字、蓝金palette、轻柔光、全部cue时序、位置、缩放与整组前后层级。

`stable_caption_layers.style_layer` 原先强制至少一像素描边，现支持真正的零描边，并跳过描边颜色合成；没有通过删黑像素处理字幕，避免误伤字形。零描边／零投影／零柔光的数值检查确认半透明抗锯齿与premultiplied输入保持一致。

输入合成对照图4140、4200、4290在 `D:/codex/output/MMD-Goo-Window-Wrap-v1/captions-no-border-v1`。已实际查看4200的前后两张，色块外黑框及偏移暗影消失，字形保持。

`make_portrait_quick_preview.py --reuse-cache --profile ...` 支持字幕独立重合成；复用前核对保存工程路径、SHA、帧段、步长、尺寸和缓存元数据。此次仅复用同一production-v3的有效150帧beauty／双人actor缓存，不运行3D渲染。新视频位于上述目录的 `video` 子目录，1080p30、五秒、指定原唱FLAC。生产blend未改，字幕外部合成参数另存可复现。

按猪猪此前约定，不进行新MP4输出后的解码、播放或审片。输入对照和编码完成记录与视频验收分开；美术待用户评价。
