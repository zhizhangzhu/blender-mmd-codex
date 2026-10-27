# 素材检索与作品目录

模型、人物动作、表情/口型及镜头配布统一使用同级 [mmd-asset-search](../../mmd-asset-search/SKILL.md)。该技能负责视频借物表、作者身份链、跨站检索、获取状态和动作/镜头版本关系；此处保留制作阶段的目录与 Append 用法。

## 落地整理

制作任务已授权下载素材时，保留原压缩包、包内 README 和相对贴图目录，记录实际下载/解压/导入状态。按作者和资源名分开存放，避免覆盖同名贴图。原始说明页、获取页、公开密码或提示来源、条款、署名、版本及下载文件哈希保存到作品的 `sources` 目录。

推荐目录：`assets/models`、`assets/motions`、`assets/cameras`、`assets/stages`、`assets/audio`、`sources`、`blends`、`renders`、`exports`。真实作品可放在项目已忽略的 `mmd_projects/作品名/`，不要将第三方素材提交到代码仓库。

## MMD Tools Append 资源目录

Append 提供已登记条目的搜索、下载、解压和导入，支持 PMX/PMD、VMD、VPD、Blender 集合和 World 等导入动作。它的目录不能代替全网检索，条目的 Official 标记不能代替当前用途的条款检查。

使用条目前核对原始说明、作者关系和下载/导入动作；只执行当前任务需要的操作。不要为了增加结果数量启用文档标为未调试的全部条目。7z/RAR 解压需要相应工具时先检查已有环境。与网页一样，目录元数据存在不证明当前文件可获取。

来源：[Append Wiki](https://github.com/MMD-Blender/blender_mmd_tools_append/wiki)、[资源条目与支持操作](https://github.com/MMD-Blender/blender_mmd_tools_append/wiki/How-to-add-a-new-asset)。
