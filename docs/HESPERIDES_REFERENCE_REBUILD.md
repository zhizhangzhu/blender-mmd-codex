# 礼堂 Ray 预览的同机位重建

后续双人导入复核发现：追加对象尚未更新依赖图时读取 matrix_world，会使灯和探针重合在舞台根节点。独立礼堂中的灯位本身不受该错误影响；修复及回归见 [受光与颜色流程](LIGHT_SPACE_AND_COLOR_PIPELINE.md)。

实测日期：2026-11-10。目标是靠近猪猪提供的 `Ray渲预览.jpg`，不是提高全图亮度。本轮为独立场景静帧和可重渲工程，没有改双人动作、物理或现成相机，没有输出新全曲视频。

输出目录：`D:\codex\output\Hesperides-Ray-Reference-Rebuild-v1`，当前版本 `final-study`。模型 miHoYo，改造 paierer，Ray 材质 Rui_cg／三金络合物／paierer。第三方资源和参考图不提交 Git。

## 查到的关键遗漏

仅把颜色、法线、光滑度和金属度搬到 Principled，不能保留这套配置的全部语义。实际读取随包 23 份 `.fx` 后确认：

| 随包配置 | 含义与本轮处理 |
| --- | --- |
| 23 份均为 `CUSTOM_ENABLE 9` | 选择 ToonBased；多数 `customA=.6` 同时开启反转，实际硬度 `.4`，阴影色 `.85`。本轮分开实现受控漫反射与真实 GGX 镜面。 |
| 14 份加算 MatCap | 13 份为 `metal1.bmp`，白幔另用 `0000018E0955C320.png`。按各自遮罩、通道和强度采样，不能统一削弱到 `.12`。强度多数为 2，另有 1.5、.1、.3。 |
| MatCap 没有 `srgb2linear` | 本地 HLSL 先把基础色转至线性，却直接取 MatCap 强度再加算。颜色贴图读 sRGB，MatCap 和控制图读 Non-Color；不能把加算移到编码色域。 |
| 白幔启用副贴图乘算 | `ALBEDO_SUB_ENABLE 1`，蓝紫副贴图增益 2、重复 2、绕 UV 中心旋转。本轮恢复该层及 60fps 旋转驱动；静帧为相位零，作者截图时间未知。 |
| 自定义材质 G-buffer 保存镜面亮度 | `EncodeGbuffer` 对镜面取 luminance，本轮用灰度 F0 近似以减少有色高光。当前 Blender RGBToBW 与 Ray 原函数的权重略有差别。 |

公开依据：[Ray 材质说明](https://github.com/ray-cast/ray-mmd/blob/master/Materials/README_chs.md)、[官方 BRDF 实现](https://github.com/ray-cast/ray-mmd/blob/master/Shader/BRDF.fxsub)。作者的 MatCap／旋转副贴图细节以随包修改后的 `material_common_2.0.fxsub` 为准，不用官方旧版本覆盖作者功能。

配置选择 ToonBased 是确定的；作者完整 `ray.conf` 没取得，不能据此证明截图时全局 `TOON_ENABLE` 的具体状态。作者灯光／天空盒／后期工程仍缺失。

## 本轮实现和技术边界

入口为 `scripts/hesperides_reference_rebuild.py`，参数为 `presets/stages/hesperides-ray-reference-v1.json`。脚本只允许原始 103 对象、无相机的场景，避免在双人工程中直接运行。

1. 保留原贴图与透明，读取法线和 Smoothness／Metalness 的真实通道，数据图用 Non-Color。Principled 输入 `roughness=1-smoothness`，由其内部转换微表面参数，不再盲目平方。粗糙度下限和局部 AO 是本地美术设置。
2. 实际 20 个普通表面采用 `clamp(N·L*hardness+1-hardness)` 混合阴影色和亮部，再乘原颜色、材质分区颜色及漫反射比例。GGX 保留真实灯光、粗糙度和反射。窗口透明、原假光束面隐藏、烛火保留发光。
3. 这不是完整 Ray BRDF 移植。方向为本地估计，没有作者太阳阴影图／SSDO，也没逐项复现 Fresnel 漫反射扣减及 IBL 能量积分；用 Emission 表达可控漫反射还会影响探针捕获，不能称为作者原始着色器。
4. 五盏矩形窗光补细高光；14 个暖烛点光由源火焰面坐标分组。程序化蓝天和近地平线云层。VOLUME 探针 6×12×6／128 采样完成烘焙，SPHERE 补屏外信息，PLANE 位于地板上方 `.025`，EEVEE 开启 `SCREEN` 追踪。参照 [Blender 平面探针说明](https://docs.blender.org/manual/en/latest/render/eevee/light_probes/plane.html)，API 以本机 5.2.2 为准。
5. 后期为 Standard／None、曝光 0、有限 Fog Glow 和全局单调 RGB 曲线。`scripts/fit_stage_grade.py` 根据参考／未调色渲染匹配通道分布，不投影参考图或替换细节。分布接近不代表质感通过；换灯光／材质后应重新评估。合入人物时必须限定背景 AOV，避免重调肤色、眼睛和黑线。
6. 固定种子的 600 个三维冷暖微光点用于空间气氛研究；当前是静态光点，没有完成落雪运动，也不是作者粒子数据。

## 先匹配机位，再比较材质

`hesperides_camera_geometry.py` 渲染不受照明影响的原纹理几何，对特征像素投射射线取真实三维点。`fit_reference_camera.py` 使用 RootSIFT、互相匹配、PnP RANSAC 和固定主点的焦距校准。

本轮为 99 个互相匹配、76 个有效世界点、18 个内点；内点重投影中位误差约 `.68` 像素（1280×720），估计焦距 36.84mm，矩阵已保存到预设。该误差只针对内点，不是全图几何误差或相似度；幔布等位置仍不同，没有恢复作者原相机。正式双人继续使用原 VMD，研究相机不能覆盖正式运镜。

## 已完成的开关实验

`final-study` 全部为 1920×1080／128 采样：

- `reference-rebuild.png`：当前研究结果。
- `control-ordinary-pbr.png`：只把 20 个表面切回普通 Principled，保留同样的贴图、MatCap、灯光、探针和调色。顶部白幔与建筑明显变暗，说明补灯不能代替着色响应。
- `control-no-matcap.png`：只将 14 个 MatCap 的强度置零。
- `control-no-raytracing.png`：只关闭 Screen 追踪和平面探针，球形反射探针仍存在；不能叫作“关闭所有反射”。
- `control-no-grade.png`：只把背景参考曲线 Fac 设零。
- `Hesperides_Reference_Rebuild.blend`：恢复全部开关后保存，56 张文件图片已打包。
- `rebuild-report.json`：完整参数、材质、机位估计及局限。

过程目录 `study-v1` 过曝、`study-v2` 仍按普通 PBR、`study-v3` 尝试编码色域 MatCap 后经源码核对排除，均不能作为默认预设。`study-v5` 的有／无 Screen 追踪 8-bit 平均差约 1.29，有可见贡献，但不是这轮最大的变化来源。不同参数版本不能照搬该数值。

独立进程重开完成：`verify_hesperides_reference.py` 检查 56 张文件图片全部打包、20 个 ToonBased 开关、14 个 MatCap、背景曲线及三类探针，并实际重渲。结果在 `reopen-verification`。这只验证可重现性，不代表动画或用户美术验收通过。

## 复用命令

输出必须为新目录；源文件也可使用 E 盘原素材，两份包的 121 个文件已校验一致：

```powershell
& 'E:\tools\Blender Foundation\Blender 5.2\blender.exe' `
  --background --disable-autoexec --threads 6 `
  'D:\codex\temp\Hesperides-Baidu-Original-v1\GI_Hesperides\Hesperides.blend' `
  --python-exit-code 1 --python scripts/hesperides_reference_rebuild.py -- `
  --preset presets/stages/hesperides-ray-reference-v1.json `
  --output-dir 'D:\codex\output\Hesperides-New-Reference-Study' `
  --width 1920 --samples 128 --controls
```

## 与原图尚有差距

白幔有硬折和局部亮斑，部分金属框架偏暖；窗外云形、空间柔化、花坛明暗、光点大小和光晕仍不同。完整作者布光、太阳阴影、天空盒和后期参数缺失，不能承诺逐像素还原。合回人物前应精修这些局部；这轮静帧也不能代替运动高光／阴影闪烁验收，没有启动新的全曲渲染。
