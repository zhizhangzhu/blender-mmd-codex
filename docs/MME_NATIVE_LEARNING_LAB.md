# MME 原生预设学习实验

猪猪已选择继续Goo，原生实验N00–N06暂缓且均未运行；当前先做[Goo基础功能与参数](GOO_FOUNDATIONS_AND_PARAMETERS.md)。下文保留为历史方案。

每次只回答一个视觉问题，并保留能重开的原生对照。优先直接运行已有原包，确认它的主shader、RT、控制器和后期各做什么，再决定是否值得在Goo复用其思想。实验参数集中于[路线参数](../presets/workflows/mmd-mme-goo-v1.json)，当前全部原生实验均为未执行。

## 学习顺序

| 实验 | 固定的内容 | 本次只观察什么 | 通过条件 |
| --- | --- | --- | --- |
| N00 环境 | 独立x64 MMD／MME、简单测试模型 | MME是否加载、效果是否编译 | 实际原生静帧；保存并重开复现 |
| N01 无效果基线 | 原始伊科尔PMX、固定VPD、无物理、固定光与相机 | 原材质、刘海、白衣层次 | 原生模型与参考发型吻合，无缺图或透明异常 |
| N02 PowerShader | N01相同姿势 | Main／Toon与AllShadow／NoShadow各自影响哪一层 | 四种职责可区分，不用Bloom掩盖问题 |
| N03 msTC | 独立PMM、常规Shade与兼容ExcellentShadow | 阴影可见性、影色、边界与描边RT | 刘海投影存在且脸色可独立调；各RT截图与分配记录齐全 |
| N04 轮廓光 | 选定一条主shader、零扩散基线 | 宽度、方向、遮挡、肤发衣分别响应 | 外缘清楚，受光核心仍有层次 |
| N05 扩散 | N04基础曝光不动 | 单套Diffusion或Bloom强度／范围 | 高光外溢增强，白衣褶皱和眼睛仍能读出 |
| N06 双人礼堂 | 固定舞台、两人、同一套主线 | 人物层次与环境主次 | 两人都改善，保存重开一致，再比较Goo v6 |

PowerShader与msTC是分支对照；PAToon可在其中一支效果不足时加入备选。Ray单独作为PBR场景分支，不默认同时覆盖同一人物的主材质。不存在“借物表列了十位作者，就把十套主shader全部挂上”的通用组合。

## 每个原包记录六项

1. 作者／原始URL／版本／SHA与许可阅读范围；私人缓存文件路径不作为公开再分发链接。
2. 本体依赖、位数、额外效果、模型／贴图／控制器和`.fxsub`相对路径。
3. main与各RT的材质分配、勾选状态、绘制顺序；写成表，不只留最终截图。
4. 控制器默认值与本次唯一变化；记录参数实际职责，不把Tr、Si当所有效果相同语义。
5. 无效果基线、效果开启、该功能关闭三张同机位静帧；特殊脸影再看左右三分之四姿势。
6. 保存并重开；注明结果是原版MME运行，还是Goo里的近似实现。只有原生截图／报告存在才晋升状态。

## 与当前人物最相关的原作者细节

msTC随包说明要求Shade.x、Edge.x、ExcellentShadow.x、控制器和default.vmd；main中隐藏ExcellentShadow，ShadeRT中显示它。Base、Shade、ShadeColor、Sublight、Edge诊断视图可以把“脸没影”分解为可见性、影色与合成问题，而不是直接增加全脸Emission。

msTC的Shade_Normal不使用ExcellentShadow投影。为避免重演刘海没有投影，N03先保持常规Shade，再单独测试法线脸影；其“SSS”控制影色边界的饱和度／明度，不等于物理SSS。[作者说明](https://note.com/mashimashi_note/n/n2c2144638054)

PowerShader随包预设把强制全影与无影分开，适合核查白衣亮区是否被误判为永远受光。Diffusion说明把强度Tr与范围Si分开，并指出默认偏强；先关扩散检查头发和脸的基础明暗，再小幅加入，不用全图柔光抵消硬伤。[PowerShader配布](https://bowlroll.net/file/195743)

## 原生实验文件夹

建议私人工作台位于`D:/codex/temp/MMD-MME-Native-Lab/`，通过原生小样后将用户要看的静帧及记录交付到`D:/codex/output/MMD-MME-Native-Lab-v1/`。本次只创建方案与清单，没有创建假PMM或假原生渲染图。

```text
case-N02/
  inputs.json             原模型／姿势／光源／相机版本与哈希
  source-package.json     原配布、许可与原包SHA
  material-assignment.csv 逐材质与各RT分配
  parameters.json         默认值、实验改值与唯一变量
  project/                PMM及实际保存的MME绑定文件
  stills/                 base / enabled / disabled
  observations.md         收益、退化与下一步
```

原包与作者示例不默认放进交付包；优先保留私人缓存和官方下载入口。第三方说明、`.fx`全文不复制进repo。输出文件名里区分native-mme与goo-adaptation。

## 怎样减少反复摸索

先用作者默认值跑通，逐层做开关对照；每轮最多一条主shader、一个轮廓效果、一套扩散。选效果时先查缓存和既有账本，不重复下载整个教程。难点只读对应RT或控制器源码，必要时再核短视频画面。

Codex目前可确定完成的是资料检索、原包／参数审计、输入打包、静帧比较和Goo脚本；本机MMD的可靠UI控制或无界面批处理仍需验证。不要通过生成一个启动命令就把N00记成完成。即使暂时需要一次原生界面装配，也应保存可复现工程，使后续学习从同一基准继续。

记录沿用[现有学习队列](../catalog/learning_queue.json)的证据分级；这份实验清单是路线参数，不是新的后台任务或自动渲染队列。当前用户只要求方案，未运行N00–N06。
