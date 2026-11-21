# 外部教程实读：人物阴影、Ray环境光与衣料质感

2026-11-13。猪猪明确：持续学习主要是实际阅读外部MMD教程和技术讲解。本轮并行实读了三组新资料，提取计算次序、材质职责和操作方法。所有移植判断仍待本机验证；未修改生产工程或渲染。

## Nilo作者的公开教学Shader：柔化脸部形体，仍保留投影

实读[作者README开头](https://github.com/ColinLeung-NiloCat/UnityURPToonLitShaderExample/blob/master/README.md)及[LightingEquation.hlsl全文](https://github.com/ColinLeung-NiloCat/UnityURPToonLitShaderExample/blob/master/SimpleURPToonLitOutlineExample_LightingEquation.hlsl)。这是面向Unity2022.3LTS的公开简化示例，不能把README中的完整版展示当成已读源码。master未锁定提交。

一个具体方法是**先处理形体明暗，再乘实际遮挡**。示例先用N·L分色并乘occlusion，脸部将该因子映射到0.5–1；随后才乘该灯的阴影接收因子，最后混合明暗颜色。这不是给最终画面设亮度下限，也不是SDF。

按该公式直接计算，假设完全接收该灯阴影：

| 已乘occlusion、尚未脸部映射的形体因子 | 投影可见度 | 脸部最终明暗混合因子 |
| --- | --- | --- |
| 0 | 1 | 0.5 |
| 1 | 1 | 1 |
| 0 | 0 | 0 |
| 1 | 0 | 0 |

所以软化鼻口几何暗区和保留刘海／手臂投影可以同时成立；表中0表示选取阴影色，不一定是纯黑。当前双人工程的Diffuse探针已合并形体、灯、间接光与遮挡，不能在它后面添加同样的0.5下限，否则会抬亮真实遮挡。真正可借鉴的是上游职责与计算次序；分离接口本轮未做。

还读到两个具体合成选择：示例限制每盏灯的距离衰减和灯色，附加灯贡献乘0.25；环境底光与直接光总和按RGB分量取max，而非总是加算。这些是教学美术选择，说明补光预算可以在合成前控制；不能把0.25换成我们灯组的瓦数比例。彩灯下逐通道max也可能改变色相，不能直接替换现有合成。完整事实与移植边界见[阴影来源记录](research/EXTERNAL_TOON_SHADOW_2026_11_13.json)。

## Ray-MMD原作者说明与实作教程：独立控制环境底光和反射

实读[ray-cast原仓](https://github.com/ray-cast/ray-mmd)的中英文Materials说明、环境光及相关遮挡源码，并读Trackdancer的[Ray-MMD 1.5.0实作教程](https://learnmmd.com/http%3A/learnmmd.com/using-ray-mmd-ver-1-5-0-beginners-guide/)Step1–7等正文。前者是效果维护者资料，后者是署名作者的MMD操作经验。

第一种方法：**环境漫反射和环境镜面反射分别调整**。Ray的`EnvDiffLight`与`EnvSpecLight`对应两条环境输入；教程也分别配置Main、EnvLightMap和材质。对礼堂的启发是：白衣和脸被环境洗平时，应先定位环境底光；金属缺少空间反射时，应查镜面路径。整体提曝光会同时改变这些部位，难以解决两种相反的问题。

第二种方法：**毛领／布料使用专属绒面响应**。Ray Cloth的CustomA控制GGX／InvGGX混合，CustomB控制绒毛反射色。它们不是金属度遮罩。手册还区分PMX光泽度、smoothness与roughness输入；例如Ray某些输入类型会转换粗糙度，不能把该转换再套到Blender已正确解释的Roughness上。

第三种方法：**AO强度、范围和真实投影分开排错**。Ray主链分别处理阴影贴图和环境遮挡；材质occlusion设0还会去掉环境反射，不能当作只关闭投影。当前若眼白／毛领脏，应先关一次已有短距AO定位；鞋底漂浮则先核鞋底、地坪和投影，不能靠加大全身AO解决。

Ray依赖MME的G-buffer、资源和控制器，`.fx`不能直接在普通Blender加载。ContactShadow文件虽读到，未确认现行主链调用，不当作默认启用的能力。具体文件范围、提交、参数上下文见[Ray来源记录](research/EXTERNAL_RAY_MMD_2026_11_13.json)。

## Filament作者技术文档：先检查金属反射光场，再调衣料光泽

实读Romain Guy、Mathias Agopian的[Filament技术文档](https://google.github.io/filament/main/filament.html)的相关IBL、材质重映射、亮度诊断节，以及[Materials Guide](https://google.github.io/filament/main/materials.html)的Sheen、Cloth与线性颜色节。没有通读整套文档或运行引擎。

金属诊断可以分两步：固定材质与曝光，先移动中性宽光源／旋转反射环境，观察亮斑方向与覆盖；确认收到镜面光后，再单独改变粗糙度看反射宽度。金属偏黑可能与反射方向或光场覆盖有关，不能立即降低Metallic或提亮全人物。EEVEE须先确认光源、探针或追踪结果确实进入当前PBR分支。

衣料除了Sheen权重，还要分别看**纤维光泽颜色和宽度**：固定底色和混合比例，先选中性或带色光泽，再只调Sheen Roughness观察斜视角软边。普通布、绒面、缎面和皮革分别判断；Filament独立Cloth与其Lit附加Sheen本身也不同，不能当作Blender Principled的同一公式。

另一项诊断是在线性图、显示变换与Glow之前，按已确认的曝光和工作色域制作亮度stop图，定位白衣、高光或礼堂亮源是哪一层过亮。它需要原始线性输入，MP4和截图不能恢复这些信息；0.18参考也不能被当成任意18%材质的实际像素值。方法与本地脚本对应点见[材质来源记录](research/EXTERNAL_MATERIAL_LIGHTING_2026_11_13.json)。

## 对当前制作认识的具体改变

- 脸部继续追求柔和形体，但须保留单独可控制的动态遮挡；不能靠最终提亮同时解决两个职责。
- 环境底光、环境反射与主补光需要分别诊断；礼堂更亮和人物更有层次不是同一个旋钮。
- 布料／毛领的光泽色与宽度值得单独研究；金属先检查反射覆盖，减少无依据地改材质。
- 教程的操作数值与其引擎、场景绑定。现有工程尚未获得上述全部独立输入，本轮学到的方法不能写成已完成的渲染改进。

补充检索中找到目压丶的原神／星铁节点图文线索，但短链正文未取得；No_Tables与小二今天吃啥啊合作页只读到发布说明，未读到Shader细节。Arc System Works官方确认公开GDC2015讲义，但本轮PDF访问／TLS失败，未读取讲义内容。它们都只保留为线索，不计入上面的已学技术。
