# 受光、动态稳定与线性合成：双人修订 v1

2026-11-11。最终交付位于 `D:\codex\output\MMD-Quality-Integration-v1`。本轮完成五秒 1080p60 原声样片、三组近景动态诊断和可重开的主工程；用户原认可版本保留，不自动将新美术方向视为已获用户认可。双人全曲仍未交付。

## 修复了什么

| 问题 | 已实现的方法 | 证据 |
| --- | --- | --- |
| 礼堂灯／探针导入后重合 | 先链接全部追加对象，更新依赖图，再保存世界矩阵并设父级；修复现有工程的 22 个灯光／探针变换并重烘静态 GI | 通用导入回归的五盏主灯位置误差为 0 |
| 头部方向不随实际骨骼正确变化 | 用骨骼父级的辅助点和 WORLD_SPACE 变换变量求向量，替代原来的 RNA 矩阵分量索引 | 多时点及 72 帧诊断最大方向误差约 1.23e-07 |
| 面部光照与场景主灯脱节 | 从实际主灯与摆动头部锚点求方向；本机适配的 festivities Face Factor 采用 incoming，模型自带 FaceLightmap 求解采用 toward-key | 空的正反向静帧对照，以及最终近景移灯测试 |
| NPR 形体与接触偏平 | 保留上游贴图／透明，叠加有下限的 EEVEE Diffuse → Shader to RGB 标量响应和短距离 AO | 58 个材质适配；真实投影开关对照，暗部不靠全图压黑 |
| 线宽随景别波动 | 在原有 PMX 权重外对两个人物的 Solidify 厚度做距离／焦距补偿，限制到 0.75–1.35 | 原动作、相机保留；近景转头和绕拍观察 |

恢复的是**本仓库礼堂重建工程**中的灯位，不是找到了作者原始 Ray 布光。身体明暗仍是受控 NPR 适配，短程 AO 不是完整间接光；真实投影的增量较克制，不能把它称作 Ray 或 Goo 的完整物理管线。黑线保留原 PMX 顶点／材质权重，像素宽度补偿是有限范围近似。

## 动态验收范围

- 正式片段为源帧 4140–4439，1920×1080、60 fps、300 个独立渲染帧、五秒；原声仍为指定 FLAC 的对应片段。
- 独立控制测试：固定灯转头 ±35°、固定头移灯 ±90°、相机绕拍 ±15°，各 24 帧、24 fps，合计 72 帧／三秒无声技术视频。取景使用无父级、无原相机约束的近景相机；诊断改动不保存进主工程。
- 原骨骼与现成相机在五个全局时点相对烘焙源工程误差为 0，95 张文件贴图均已打包，无实时物理；没有重做动作或衣发烘焙。
- 最终视频全部解码通过、最大静止帧连段为 0；原声解码与第 150 帧分段接缝通过。实际看过 12 个全段代表帧、接缝帧和近景角度表。
- 光流补偿的脸部变化量仅用于找可疑跳变，不等于证明所有角度／全曲绝无闪烁。本轮未验收新动作、新模型和全曲。

## 真正的分层数据

主工程保留原生人物 RGBA 和干净舞台两个辅助场景，使用集合 holdout／排除，不从已压成一张图的 beauty 反推人物。辅助场景须设置 `use_fake_user=True`，否则可能在保存重开时丢失。

五个时点 4140、4200、4290、4420、4439 导出人物 premultiplied RGBA、干净舞台和全场景 raw beauty。原生层之间的投影、反射与遮挡耦合用带符号交互层保存：

```text
over = actors.rgb + stage.rgb × (1 − actors.alpha)
interaction = raw_beauty.rgb − over
reconstructed = over + interaction
```

交互层存 32-bit float EXR，不能把负值裁掉，也不能当独立 shadow catcher。重组后读取校验的最大误差为 0；这证明文件保存／重组没有丢失当前 raw 数据，不证明任意调色或换背景后物理仍完全正确。改动作、几何或灯光需重渲交互层。换黑、白、洋红背景用于看边缘，不代表模拟了这些背景的新环境光。

五秒全序列另保留 300 个 multipart EXR，约 4.15 GB：

| 部分 | 内容 | 实际存储 |
| --- | --- | --- |
| RawBeauty | 创意合成前的场景线性 Combined | RGBA half／16-bit float |
| FinalLinear | 已做创意调色、尚未应用显示变换的颜色 | RGBA half／16-bit float |
| ActorMask | 人物覆盖率／保护区 | FLOAT／32-bit float |

本机文件输出节点的颜色深度 16 不会把 FLOAT 插口强制降成 half，须读实际 EXR 通道头。全部 300 帧头部与帧号检查通过；FFmpeg 独立解码整个 RawBeauty 序列。通用视频解码转换可能将 HDR 截到 0–1，所以不能凭其转换成 float 的输出证明原文件动态范围。另用 OpenEXR 3.5.2 原生读取全部 300 帧的三个部分，验证每个通道均有限、数据类型正确、遮罩在 0–1 范围，并确认大于 1 的原始数值保留。完整原生人物／舞台分离目前只验证五个时点，不能称为全 300 帧均已导出人物 RGBA 独立序列。

## 颜色管理

工作空间为 Linear Rec.709。EXR 不烘入显示 TRC；观看输出使用 Standard、Look None、Exposure 0、Gamma 1。不要把观看 MP4 当调色母版，也不要把 FinalLinear 再当显示编码图片处理。

实测线性 0.18 在 half EXR 中读回 0.18005371，HDR 4.0 保留；Standard PNG 的编码值为 0.46135652，符合 sRGB 预期 0.46135613。Blender 将该 16-bit PNG 以 sRGB 读回时，`Image.pixels` 可能已经解码成约 0.18；检查磁盘编码值应使用 Non-Color 读回或原始像素解码，不能把这两个数混为一次／两次显示变换。

## 输出隔离与可复用入口

诊断脚本必须禁用加载工程中的 File Output 节点，即使没有保存 blend，也可能对磁盘造成输出。首次发现 4200 帧被测试机位覆盖，已用正式主工程补回；之后重新校验完整序列，并通过六帧诊断前后的 SHA-256 一致性验证。正式序列的文件名必须显式使用 `duet_####`，防止单帧调用覆盖同名 EXR。

- `integrate_reference_duet.py`：修复追加对象的依赖图／世界矩阵顺序。
- `genshin_material_adapt.py`：世界辅助点头部轴和此适配库的光向约定。
- `integrate_light_space.py`：从旧认可基线建立独立质量分支、接入材质响应、GI 和线宽控制；禁止重复叠加。
- `export_linear_pipeline.py`：原生分层、颜色补丁、交互重组与 EXR 归档。已验证分层仅可按同源 SHA-256 复用。
- `render_shader_diagnostics.py`：隔离输出的近景连续控制测试。
- `verify_linear_archive.py`：multipart 结构、实际通道位深、独立浮点与全序列解码。
- `render_duet_sample.py`：分段渲染、指定原声混流、视频／音频／接缝验收。

后续用 `render_duet_sample.py` 复现时，质量归档节点默认重定向到新样本目录的 `linear/`，可用 `--linear-archive-dir` 指定全新路径。继承旧片段时仍需另外验证归档完整性；不能仅凭视频片段复用就声称 EXR 全齐。直接在 Blender 手动渲染时也应先另设 File Output 目录。

原生 EXR 复核工具安装在临时目录 `D:\codex\temp\mmd-exr-tools`。将其放进 PYTHONPATH 后，对 `verify_linear_archive.py` 加 `--native-pixels` 才会读取原始全部浮点通道；安装的 OpenEXR 为 3.5.2，不改变 Blender 插件。API 参考 [OpenEXR 官方 Python 文档](https://openexr.com/en/latest/python.html)。

新预设为 `presets/quality/duet-light-space-v1.json`，工程配方为 `presets/recipes/duet-light-space-v1.json`。它们绑定当前角色与工程，不是任意 PMX 自动转换器。`finalize_face_contract.py` 是本轮中间工程的一次性迁移，不应对已经使用正确 incoming 的新工程再次取反。

来源仍继承交付 CREDITS 与第三方许可。EEVEE／File Output 以本机 RNA 与实际渲染为准；参考 [Blender File Output API](https://docs.blender.org/api/main/bpy.types.NodeCompositorFileOutputItems.html)。原有风格套装与用户认可五秒版本保留；新夜景、鸣潮全套、个人风格及全曲不因本次技术验收自动完成。
