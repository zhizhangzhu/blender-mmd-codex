# 《フランケンシュタインの怪物》镜头与音乐来源记录

核查日期：2026-11-09。当前模型阿克西妮娅，动作沿用官方 Full HinaSuzuki VMD，单角色；没有自行替换成 Solo 副歌动作。伴奏卡点由用户后续处理，本轮不调整。

后续新目标为**双人全曲：阿克西妮娅用 Full Hime，空用 Full Hina**，旧单人默认不适用于新项目。已另找到とっとこ的[公开镜头包 359108](https://bowlroll.net/file/359108)，下载、读说明并用 173 cm 版与双人 Full 动作完成实际导入及十帧草稿检查；每版 400 个相机关键帧、0–6211。四个身高版本与开头左右口型保存在本地输出；允许改造、禁止再配布。具体证据、尚未通过的全曲构图/物理/时间轴项目见 [双人全曲制作](DUET_FULL_PRODUCTION.md)。

## 原曲与官方素材

- [原曲 MV：HIMEHINA](https://www.youtube.com/watch?v=J66gqneY518)。Vocal：HIMEHINA；Lyric：Gohgo；Compose：Fty & Gohgo；Arrangement：Fty。简介信息由用户提供。
- [官方舞蹈演示](https://www.youtube.com/watch?v=XapkJAHKdOo)。镜头作者的原页确认引用这套 Studio LaRa 动作。
- [官方配布短链](https://larainc.link/Franken) 已实测重定向至 [Google Drive 公开目录](https://drive.google.com/drive/folders/1XQNzKCcTsYx7Dwu8Y9wM8pw-IMQ5ZpfW?usp=sharing)。公开目录共有 19 个可见文件。
- 伴奏为 `Inst±0`、`Inst+1`、`Inst+6`；[原调伴奏文件页](https://drive.google.com/file/d/1yZpXntMZfx6mqn9sbp2VZ8U8A25QdIqZ/view)。本地已有 `E:\tools\franken\FrankensteinNoKaibutsu_Audio_Inst±0.wav`。这些是伴奏，未确认官方目录含有人声 WAV；需要原唱时保留原曲 MV/官方发行入口，不把伴奏写成人声原曲。
- 目录同时有 FBX 和原生 VMD，包含 Full 的 HimeTanaka/HinaSuzuki，以及 1Sabi 的 HimeTanaka/HinaSuzuki/Solo。[Solo 原生 VMD 文件页](https://drive.google.com/file/d/1_lytQMw1Wi6dC1ut-26de46ZNJFgBCVu/view) 已核实存在。
- 后续重新核对目录，还确认有 Full Typography(Wide)、1Sabi Typography(Tall) 和 1Sabi DanceBB-HMEHINA 视频。前两份已实际用于横竖字幕合成；Tall 的起点不能套用动作 `[f1794]`，详见 [动态字幕与官方素材复用](ADVANCED_MMD_SUBTITLES.md)。
- 官方可见目录没有命名为 camera 的镜头文件；当前本地 Full HinaSuzuki VMD 已解析为 0 个相机关键帧。第三方镜头须另找，不由「官方动作可下载」推断附赠相机。

`[f0]` 与 `[f1794]` 表示相对官方 MV（30 fps）的放置时序。导入器是否将源第 0 帧移到 Blender 第 1 帧，需要记录实测；不要把文件名偏移再重复加到已经位于 1794 的相机上。音频已找到与卡点已完成是不同状态。

## 已核实镜头候选

| 镜头作者 | 作者配布 | 已核实内容 | 当前状态 |
| --- | --- | --- | --- |
| 水瀬ミナ | [BowlRoll 357649](https://bowlroll.net/file/357649)；[演示](https://www.nicovideo.jp/watch/sm46642142) | 包内有 Full 约 160 cm、Full 185 cm、Short 185 cm；无需密码 | 已下载、读说明、导入测试；Full 160 cm 有 365 个相机关键帧，源帧范围 0–6221 |
| ひな | [BowlRoll 357702](https://bowlroll.net/file/357702)；[作者频道演示](https://www.youtube.com/watch?v=V8a5ecaqFco)；[作者主页](https://bowlroll.net/user/570402) | 配布页说明 2026-08-26 增加 Full 版，另有 Short 演示；对应官方动作 | 原页和作者已核实，未下载/导入；按配布页所链作者说明获取密码，不在本仓库转贴 |
| Herdubreid | [BowlRoll 358036](https://bowlroll.net/file/358036)；[演示](https://www.youtube.com/shorts/d809XJxYpGY) | 明确为副歌 short 镜头，文件名 `フランケンシュタインの怪物サビカメラH.zip`，无需密码 | 候选，不当成 Full 整曲镜头；未下载/导入 |
| おナスの沼漬け | [BowlRoll 358056](https://bowlroll.net/file/358056)；[演示](https://www.nicovideo.jp/watch/sm46639702) | 镜头及开头台词口型 | 候选，下载密码按作者演示说明获取；未下载/导入 |

作者身份、访问条件和包说明由配布原页的公开 HTML 和该页面调用的 `/api/file/<id>/message` 核实。搜索结果仅用作定位，不据此承诺全部候选都适合当前单角色。ひな的[在线使用说明](https://privatter.net/p/9891536)应在采用前阅读，包含密码不得传播和数据不得再配布等要求。

## 水瀬ミナ镜头的实际测试

原包保存在 `D:\codex\output\blender-mmd-codex\camera-mina-357649-v001`。ZIP 的 SHA-256：`8ef974d037fff71c8ecc4a8eb29ef8acc1012d29a96e4975804765f638b2317b`，这是本次下载记录，不是作者独立发布的校验值。

readme：Short 镜头从源第 1794 帧开始；Full 远景有可能穿过舞台，需要调整。160 cm 版以 Sour 式 Miku 制作。使用时署名水瀬ミナ及其他借用作者；Niconico 发布需登记相关内容树；允许镜头改造，禁止改造后镜头再配布。不要把联系用账号代替署名。

原样导入 Full 160 cm、缩放 0.08，保留原角色骨骼 Action，通过三个时点的头部投影检查。第 1884/1944 帧头部在框内，第 2004 帧在框外；肉眼检查也确认竖屏裁切严重。因此不能直接交为「已适配单人竖屏镜头」。

在 `camera-mina-single-check-v001` 中新增相机组父级的构图位移，对 1794–2034 帧逐帧烘焙，让头部约在画面的 x=0.5、y=0.7。三处检查头部均在框内，但实际 8 秒视频抽帧发现第 1862 帧仍有过近的肩部大特写，说明只检查头部点是否在框内不足以验收构图。

检索阶段的第二版测试为 **`camera-mina-single-check-v002`**：保留作者的相机旋转、焦段和关键帧时序，在单人构图偏移中增加最小竖向取景范围 1.1 Blender 单位，过近时沿相机视线拉开距离。第 1862/1944/2004 帧的构图测试均通过头部投影检查，极近景已修正；有意的半身镜头仍可裁脚。它是局部跟随与景别测试，尚未做完整分镜美术验收。

原始导入对照在 `camera-mina-import-check-v001`；单人测试项目为 `camera-mina-single-check-v002\camera-import-check.blend`，镜头预览为同目录 `camera-preview.mp4`，360×640、30 fps、241 帧、约 8.03 秒、无声。它保留初稿材质，尚未构建/烘焙衣发物理，不是成片。这是本地制作使用，未把作者 VMD 或改造后的相机数据加入 Git 仓库。

**后续正式成片另用了程序生成的相机。** `mmd_final_scene.py` 只读取水瀬ミナ源相机的焦段影响景别；最终机位、朝向、头部跟随和竖屏构图在 Blender 内另写关键帧，没有保留原作者的旋转机位，也没有制作新的 VMD 文件。不能将上述测试项目与正式成片相机混为一谈。当前渲染改进轮保持此程序相机不变，详见 [LOOK_REFINEMENT.md](LOOK_REFINEMENT.md)。

## 可复用执行方式

先使用公开下载脚本（只支持无密码开放包）取得新目录，再在 Blender 已有项目上运行：

```powershell
python scripts/bowlroll_public_download.py --file-id 357649 --output-dir 'D:\codex\output\blender-mmd-codex\camera-download-new'
& 'E:\tools\Blender Foundation\Blender 5.2\blender.exe' --background '<已有项目.blend>' --disable-autoexec --python-exit-code 1 --python scripts/mmd_camera_check.py -- --camera-vmd '<镜头.vmd>' --output-dir 'D:\codex\output\blender-mmd-codex\camera-check-new'
```

按需增加 `--follow-range 1794 2034 --min-vertical-span 1.1` 做本模型的局部跟随测试；最小取景范围是本次副本参数，不是其他模型的通用数值。视频预览可在加载该项目后运行 `scripts/render_camera_preview.py -- --output '<新预览.mp4>'`，脚本在独立进程里设置无声 H.264 输出，不保存源项目设置。使用新输出目录，保留原包、readme、来源和原始项目。外部配布变化时重新核实，不把这次检索结论写死为永久结果。

本轮 17 项单元测试通过，含匿名下载访问限制、ZIP 越界拒绝和日文 URL 编码；新增镜头检索 skill 通过 `skill-creator` 的校验器；实际导入、渲染与预览解码另行验证。

Blender 5.2 实测：导出视频需先设 `scene.render.image_settings.media_type = 'VIDEO'`，再设 `file_format = 'FFMPEG'`，随后配置 `scene.render.ffmpeg`。仅设置旧版 `file_format='FFMPEG'` 会因当前媒体类型而报枚举错误。
