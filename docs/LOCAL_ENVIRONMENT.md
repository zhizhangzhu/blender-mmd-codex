# 本机环境与插件学习记录

2026-11-17原生路线核查：递归检查`E:/tools`中的MikuMikuDance／MMEffect文件名与相关exe，并查看常见目录顶层，未发现MMD本体或MME运行库；这不是全盘未安装证明。原包私人缓存已有9套，不能与运行库安装混为一谈。本轮未安装或启动MMD，未验证本机DX9与原生MME编译。入口见[分工方案](MMD_MME_GOO_WORKFLOW.md)和[研究账本](research/MMD_MME_GOO_ROUTE_2026_11_17.json)。Goo v6静帧工程保留。

2026-11-16 复查当前 Blender 5.2.2 保存偏好与磁盘源码：启用 MMD Tools 4.5.14、MikuMikuRig 5.2.2、咖啡工具 1.9.2、Paper Anime Render Helper 2.5.0；旧 MMD Tools 4.1.0 未启用。未发现原生 MME `.fx` 执行器或通用转换器；咖啡工具的预设迁移针对 Blender 内已有材质等数据。具体可复用路径与核查边界见 [MME 与 Blender 预设](MME_REUSE_AND_BLENDER_COMPATIBILITY.md)。独立后台进程报告：`D:/codex/temp/blender-addon-inventory-2026-11-16-mme.json`，未改偏好或生产工程。

2026-11-11 补充：已实测 5.2 文件输出接口 `file_output_items.new`、`directory`、`file_name`；必须显式帧号。RGBA half 与 FLOAT 遮罩的实际位深不同；未被窗口引用的辅助场景需 fake user。动态诊断要禁用继承的文件输出，避免覆盖正式归档。验证与入口见 [受光与颜色流程](LIGHT_SPACE_AND_COLOR_PIPELINE.md)。

核查日期：2026-11-09（Asia/Shanghai）。机器相关路径仅用于本机，换机器后重新运行检查。

## 已核实

2026-11-16更新：后续默认制作运行时按用户要求切换至 `presets/runtime/goo-v1.json` 的 Goo 5.2.1社区移植版；原普通5.2.2保留用于历史回退。Goo 4.3.2与5.2.1均已实际启动，只有后者读入当前工程；四个插件注册、PMX导入、咖啡材质迁移、Paper六组添加/撤销已测。MMR未重绑定，Curvature Scene Rim测试黑，完整边界见 [Goo迁移](GOO_ENGINE_MIGRATION.md)。

2026-11-11 补充：用户下载的 hair高光(wuwa3.0)、几何实体化描边、通用脸部 SDF、A-原神版预设已在 5.2.2 中只读打开，四份节点组均无未定义节点；这不是全部效果已套用。festivities v3.4 库则有四个 Goo 专用未识别节点，本轮只适配可用组件，未安装或运行 Goo 独立引擎。完整兼容边界与实际五秒视频见 [原神角色与下载预设](GENSHIN_CHARACTER_AND_PRESETS.md)。

使用 `scripts.blender_validate` 对指定执行文件验证成功：Blender 5.2.2 LTS、Python API、仓库 Add-on 的临时 register/unregister。仓库 Add-on 没有因此永久安装到用户偏好。

运行 `scripts/blender_inventory.py`（保留用户偏好，独立后台进程）得到：

| 插件 | 本机版本 | 状态 | 用途与边界 |
| --- | --- | --- | --- |
| MMD Tools 扩展 | 4.5.14 | 已启用、已注册 | PMX/PMD、VMD/VPD 导入，MMD 材质、Morph、刚体；优先入口 |
| MMD Tools 旧分支 | 4.1.0 | 磁盘存在，未启用 | 不需要删除，不与新版同时启用 |
| MikuMikuRig | 5.2.2 | 已启用、已注册 | 骨骼优化和动作辅助；先保留原始导入基线，再试它的修改 |
| mmd_kafei_tools | 1.9.2 | 已启用、已注册 | 模型预处理、预设转移、骨骼/材质/权重工具；只按具体问题使用 |
| Paper Anime Render Helper | 2.5.0 | 已启用、已注册 | 描边、高光、Toon 阴影、Glow、色彩与天空盒；不是自动复刻目标风格 |

已注册算子数量：`mmd_tools` 118、`mmr` 65、`mmd_kafei_tools` 47、`paper_helper` 13。数量和参数清单仅代表该次进程的 API 可用性。

Cycles 设备查询发现 RTX 5070 Ti 的 OPTIX/CUDA 设备，以及 i5-13600KF CPU。这不等于 GPU 成片渲染已验证；不从 Win32 的 AdapterRAM 字段推断实际显存。

## 已学到的调用规则

MMD Tools 源码 `operators/fileio.py`：导入 VMD 时选模型根 Empty 可同时处理骨骼与 Morph；仅选 Armature 只导骨骼，仅选 Mesh 只导 Morph。PMX 与 VMD 都使用一致缩放（本次为 0.08），按 PMX 日文骨名映射。

```python
bpy.ops.mmd_tools.import_model(filepath=model_path, scale=0.08,
                                clean_model=False, remove_doubles=False,
                                save_log=False)
# 选中该模型根 Empty，并设为 active，再调用：
bpy.ops.mmd_tools.import_vmd(filepath=motion_path, scale=0.08,
                              bone_mapper='PMX', create_new_action=True,
                              update_scene_settings=True, save_log=False)
```

VMD 导入器的 `update_scene_settings` 会设为 30 fps 并更新帧范围。完整动作文件名的 `[f0]` 与片段 FBX 的 `[f1794]` 表示相对官方 MV 的时序，不要把 1794 当作完整 VMD 必须添加的偏移。

纸片人助手的 `materials.py` 中高光实现使用 `ShaderNodeShaderToRGB`，`operators.py` 可按设置切换 EEVEE，且会调整色彩管理。当前先走 EEVEE 试样；切换 Cycles 前需要替换不兼容节点并重新验收。`apply_skin` 要求兼容的 Principled BSDF 材质，不能假设原生 MMD 材质直接适用。

后续实测发现，MMD Tools 4.5.14 的 `MMDShaderDev` 自带 `Color/Alpha` 输出，可以保留上游贴图、球面与透明链，再单独实现 NPR 光照。本轮渲染改进采用此接口，避免首版 Shader to RGB 后逐通道压缩导致的灰化。接口必须以本机实际节点组为准，具体对照和限制见 [LOOK_REFINEMENT.md](LOOK_REFINEMENT.md)。

调用算子前检查 RNA 参数及 `poll()`；依赖界面的工具不保证能在后台执行。不要一口气对全模型套全部修复、材质或骨架转换。

## 复查命令（PowerShell，仓库根目录）

```powershell
$env:BLENDER_EXECUTABLE = 'E:\tools\Blender Foundation\Blender 5.2\blender.exe'
python -m scripts.blender_detect
python -m scripts.blender_validate --executable $env:BLENDER_EXECUTABLE --addon-path .\blender_addon
& $env:BLENDER_EXECUTABLE --background --disable-autoexec --python-exit-code 1 --python .\scripts\blender_inventory.py -- --output 'D:\codex\output\blender-mmd-codex\environment-new.json'
```

报告采用 UTF-8。Windows PowerShell 用 `Get-Content -Raw -Encoding UTF8` 读取 JSON，避免默认编码破坏中文。检查脚本拒绝覆盖旧报告；每次指定新文件名。不要给插件盘点命令加 `--factory-startup`，否则得到的是工厂偏好。

来源：本机插件源码、上述实测报告；公开资料为 [MMD Tools 官方扩展](https://extensions.blender.org/add-ons/mmd-tools/)、[咖啡工具作者仓库](https://github.com/kafeijk/mmd_kafei_tools)。本机版本优先于在线最新版。

2026-11-14 Node Wrangler补测：随包`addons_core/node_wrangler`版本4.1.0；读取保存偏好时未启用，在独立进程临时register／unregister成功，userpref SHA前后一致。没有查询当前GUI启用状态或保存偏好；Ctrl-Shift-LMB的当前材质／Compositor预览由Blender内置算子承担，不能笼统归为NW独有。功能、限制和报告见[本机账本](research/NODE_WRANGLER_LIGHTING_2026_11_14.json)与[逐层诊断](PORTRAIT_LIGHTING_AND_SHADOW_STUDY.md)。

2026-11-13浏览器补测：随包26.1111.21308，Chrome Profile 2扩展与native host经官方只读脚本确认正常；曾实际读取登录B站正文，后续调试仍不稳定，完整字幕未取得。用户要求后续优先本地Chrome、文字模式默认暂停并核实，不重复申请已给权限。完整时间顺序与失败边界见[浏览器记录](BROWSER_AUTONOMY.md)及[高效学习](EFFICIENT_RESEARCH_WORKFLOW.md)。
