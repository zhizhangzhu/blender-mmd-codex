# GooEngine 主线运行时政策与风险管控

日期：2026-11-22 · 状态：生效 · 配置文件：[goo-v1.json](../presets/runtime/goo-v1.json)

## 1. 运行时定位

- **主线运行时**：GooEngine（面向动画／三渲二的 Blender 分支）是本仓库实现“AI 全自动产出高质量 MMD”的唯一默认生产主线。
- **对照与备选运行时**：官方 Blender 5.3（`02f0899d78e3`）与本机普通 Blender 5.2（`E:/tools/Blender Foundation/Blender 5.2/blender.exe`，已测 5.2.2）保留为**对照、回归或紧急回退**，不再作为默认生产主线；普通 Blender 安装保持原样不重复安装。
- 2026-11-19 针对双人工程的“默认迁往官方 Blender 5.3”决定，自 2026-11-22 起降为对照／备选路线；829f Goo 冻结源继续只读保留。

## 2. 版本锁定与启动契约

| 项目 | 现行锁定值 |
| --- | --- |
| 配置 ID | `goo-v1`（`presets/runtime/goo-v1.json`） |
| 可执行文件 | `D:/codex/workspace/goo-engine/5.2.1-community/blender-5.2.1-git.0051aee0-windows64/blender.exe` |
| 版本与构建 | Blender 5.2.1 LTS 社区移植 Goo，构建 `0051aee03764`（EEVEE-Next 后端） |
| 来源与校验 | `NaMgAl-Studio/goo-engine-5.2.0` Release `GooBlender5.2.1_2026.9.12`；压缩包 SHA256 `c43ea4c16ef8eefa768379b3b0c3b8e65f0be445fa7e8d886d04aa4f4ebfc343` |
| 隔离配置 | 独立 `portable/config` 与 `portable/scripts/addons`（通过 `scripts/goo_runtime.py` 启动） |
| 随包已注册插件 | MMD Tools 4.5.14（含纯 Python OpenCC 依赖修复）、咖啡工具 1.9.2、Paper Anime Render Helper 2.5.0、MikuMikuRig 5.2.2 |

**强制启动约束**：
1. 始终经 `scripts/goo_runtime.py`（或声明 `presets/runtime/goo-v1.json` 的 `studio_bench` / `studio_publish`）启动，使用独立 `BLENDER_USER_CONFIG` / `BLENDER_USER_SCRIPTS`，绝不污染全局用户偏好。
2. 禁止同时注册旧 `mmd_tools` 与新版扩展；开工程前先注册 MMD 相机 RNA 并核对焦距／driver（factory-only 曾出现 1mm 错误焦距）。
3. Goo 4.3（及 4.4 官方旧版）**无法读取 5.2 工程文件**（5.x 文件格式不向后兼容 4.3）；严禁通过改扩展名或降级破坏生产工程。

## 3. 风险登记与缓解策略

本机主线构建是 **DillonGoo Goo Engine 的非官方社区移植版（5.2.1 / EEVEE-Next）**，不是官方原版二进制，存在以下明确风险：

| 风险 ID | 风险描述 | 触发征兆 | 缓解与应对 |
| --- | --- | --- | --- |
| GOO-R1 | **节点移植不完整**：部分官方 4.4 节点插口在社区 5.2.1 上无响应或数值量级不同 | 例如 `Shader Info` 的 `WorldPosition` / `Normal` 覆盖插口无响应、`Curvature` 原始线性值极小 | 严禁直接照搬官方 4.4 教程值；任何新节点进入生产前必须先做独立最小场景对比验证并记录真实 EXR/PNG 读值 |
| GOO-R2 | **上游社区停更或二进制失链** | GitHub Release 下架或新版本破坏接口 | 保留本地完整二进制、便携配置目录及安装包 SHA256；升级任何新构建必须新建 `goo-v2.json`，不覆盖 `goo-v1.json` |
| GOO-R3 | **非官方 5.2 工程锁定** | 未来官方 Goo 5.x 或官方 Blender 5.3+ 若改变专属节点结构，旧工程专属节点可能失效 | 管线设计采用“可替换声明式配方（风格包／灯光包／bench profile）+ 标准材质保护（保留 MMDShaderDev 底色/Alpha/贴图）”，确保可从干净 PMX+VMD 重建，不把知识锁死在单个 `.blend` 补丁里 |
| GOO-R4 | **插件冲突与回退路径误读** | `USER_SCRIPTS` 缺失时回退加载旧 4.1 同名插件导致 ActionFCurves / 相机异常 | `goo_runtime.py` 启动前显式核验独立 `portable/scripts/addons` 存在，并对关键资产（动作、相机、保护材质）跑重开校验 |

## 4. 本机构建已测功能矩阵（截至 2026-11-22）

遵守 EVID-01：接口存在 ≠ 行为生效 ≠ 生产可用；未测项不升级为全支持。

| 能力／功能 | 本机 5.2.1 实测状态 | 已知边界与注意事项 |
| --- | --- | --- |
| `Shader Info`：`Half-lambert factor` / `Cast Shadows` / `Self Shadows` / `Ambient Lighting` | **已实测可用**（静帧 & 独立重开） | `Diffuse Shading` 为 HDR 值可超 1；`Use Own Light Groups` 需核节点与材质面板两处；`check_shadow_id` 影响 Cast/Self 拆分 |
| `Shader Info`：`WorldPosition` / `Normal` 覆盖插口 | **实测无响应（不可用）** | 社区 5.2.1 四路受测输出对这两插口偏移无响应；需改法线时走真实网格 Normal Edit 修改器或材质前置法线，不依赖该插口 |
| `Light Groups` | **已实测可用**（单灯／双灯隔离线性差为 0） | 角色主光组先只放单方向主光，补光另行分组控制，避免洗平形体分区 |
| `Curvature` / `Scene Rim` | **接口存在，未获生产认证** | 原始线性值极小（~0.0014），放大后存在宽内部亮区；当前人物细轮廓继续使用受控方向 rim 与 PMX 描边 |
| `Screenspace Info` / `Set Depth` | **基础机制已测，当前搁置** | 需 Ray Tracing 与 raytraced transmission；`Set Depth` 须实际连线；眼透功能按用户决定搁置 |
| `Color Ramp` / `OKLab Ramp` | **已实测可用** | OKLab 不保证自动更鲜艳；阈值、配色与 Bloom 分开调节 |
| `SDF Primitive / Op / Vector Op / Noise`、`Hex Grid`、`Twirl`、`Water Ripples` | **仅参数枚举，行为待逐项实测** | 不可凭节点名称直接投入生产 |
| `mmd_tools` / 动作 / 表情 / 相机 / 重开 | **已实测可用**（含双人 4140–4438 矩阵与焦距一致性核验） | 须经 `goo_runtime.py` 注册便携插件后再读工程 |
| 原生 MME `.fx` 运行 | **不支持** | Goo 内无已验证通用 MME 运行时；按先读原生装配再最小化 Goo 节点适配处理 |

## 5. 回退到官方 Blender 5.3 的触发条件与路径

仅在满足以下任一条件时，由主控决定切回官方 Blender 5.3 备选路线并向猪猪说明：
1. 社区 Goo 5.2.1 出现阻断性崩溃、渲染错误或显卡驱动不兼容且无法绕过；
2. 官方 Goo Engine 发布了支持 5.x/EEVEE-Next 的正式版（此时优先升级为 `goo-v2.json`）；
3. 某项必需能力（如稳定官方 NPR 节点或时序阴影）经同条件对照证实官方 Blender 5.3 显著优于 Goo 5.2.1。

回退时遵循 SAFE-01：不覆盖现有 Goo 冻结源与候选工程，在新输出目录用独立 runtime profile 重建并跑同等重开与自动 QC 检查。
