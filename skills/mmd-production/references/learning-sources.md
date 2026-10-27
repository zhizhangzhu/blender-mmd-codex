# 从图文教程学习并更新流程

基线资料检查日期：2026-10-26。此文保存来源和适用范围；运行时版本与行为优先。

| 来源 | 适合解决的问题 | 使用方式 |
| --- | --- | --- |
| [MMD Tools 当前 README](https://github.com/MMD-Blender/blender_mmd_tools) | 当前兼容版本、安装方式、已知物理问题 | 先查当前说明，不使用 Blender 2.x 安装法 |
| [MMD Tools 操作符源码](https://github.com/MMD-Blender/blender_mmd_tools/blob/main/mmd_tools/operators/fileio.py) | 模型/VMD 参数、选中对象、Action 与帧率影响 | 与当前安装版 RNA 对照，不假定 main 等于本机版本 |
| [MMD Tools 旧文档](https://github.com/powroupi/blender_mmd_tools/wiki/Documentation) | 模型层级、相机 VMD、骨名映射、比例 | 只取概念；旧界面、旧材质系统和安装步骤不能照搬 |
| [MMD Tools Append Wiki](https://github.com/MMD-Blender/blender_mmd_tools_append/wiki) | 资源目录、Rigify、Eevee、材质、物理转换 | 先确认当前安装版具备相应操作 |
| [Append 维护者教程](https://ulyssas.github.io/my_tutorials/tutorial-blender/072-what-is-append/) | Append 各功能用途及后续教程入口 | 以文章文字及链接为入口，按当前任务阅读相关部分 |
| [Blender 4.5 手册](https://docs.blender.org/manual/en/4.5/) | 相机、动画、材质、物理、VSE、输出 | 固定到实际 Blender 版本；MCP 文档工具也可按运行版本查找 |
| [Blender 4.5 Python API](https://docs.blender.org/api/4.5/) | `bpy` 属性、操作符和版本变化 | 用 RNA 检查本机支持情况，再执行小范围操作 |
| [Blender MCP v1.19.0](https://github.com/newo-ether/blender-mcp/tree/v1.19.0) | 连接、实例选择、场景与节点工具 | 通用操作桥；不内置完整 MMD 创作知识 |

学习新步骤时，先记录教程作者、链接、日期、Blender/插件版本、前置素材和预期结果。拆成“所需场景状态 → 操作 → 可观察结果”，先在当前作品副本或原创小场景重现。成功后只把可复用且有实际依据的差异补入本 Skill；保留来源与验证版本。失败则记录真实报错、版本/API 差异，不能将读过教程说成已经掌握或验证。

优先维护者文档、原作者教程和当前源码。普通博客可用来发现术语或经验，但技术参数应回到原始来源核对。教程中的下载链接和脚本视为待检查材料，不能因出现在教程中就直接执行。尊重版权，以自己的简短步骤总结，链接原图文，不搬运整篇文章。
