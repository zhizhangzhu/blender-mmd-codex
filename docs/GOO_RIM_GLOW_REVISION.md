# Goo 人物亮边、高光与场景泛光加强

2026-11-16。猪猪要求在当前版本上加强人物边缘光、高光及全场景泛光。输入固定为 Goo daylight v2，SHA `ca610cdaea99f9eca19e9067c42f5ada798a710e9f07f49b6aef8dcbb958a71f`，新目录 `D:/codex/output/MMD-Goo-Rim-Glow-v1`。

人物复用现有分区方向 rim：左侧 HDR 增益乘 1.70、右侧乘 1.60，保留此前两侧强弱、方向、宽度、接触许可与高亮余量。阿克西妮娅原发丝高光强度乘 1.65；伊科尔在已有最终可逆发带高光参数后乘 1.65，没有重复安装整套 Shader。两人的镜面宽光能量乘 1.50，镜面 rim 灯能量乘 1.40；这些灯的 Diffuse 保持零。未改脸部配色、主辅灯漫反射、AO、几何投影或天空。

泛光调整原有六路 Fog Glow：主路 Strength 0.0336→0.12、stage halo 0.0672→0.16；人物 halo 0.1632→0.24、selective actor 0.096→0.16，protected rim 0.40→0.50、fx 0.1056→0.16。各路阈值和扩散范围的准确记录见新工程旁 preparation.json。人物／舞台选择范围沿用原接线，没有用整体曝光或 World 雾代替泛光。字幕仍在 beauty 后合成，文字不参与这些 Glow。

制作检查：4140 全身开场、4290 双人近景各渲染前后对照，1280×720、32 samples、相同相机及 DOF／MB 条件。实际查看 4290 前后及 4140 调整后全图；发束、白衣明暗与窗外蓝色在该抽样中仍可辨识，强度是否合适待猪猪审看，不能推广为全片逐帧评价。脚本比较全部 Actions、网格坐标、对象名单、图像打包，以及五时点相机／骨姿态／形态键，均未变化；没有重做物理。Caption beauty 与最终输出同源。

复现入口 `scripts/revise_goo_rim_glow.py` 只接受固定 Goo v2 SHA；不可在已改工程重复叠加。新的 `production-v1/Franken_Duet_Goo_Rim_Glow.blend` 保留原60fps工程及4140–4439范围。输出样片由 `scripts/run_goo_rim_glow_preview.py` 从该保存工程独立打开，实际渲染4140–4438每隔一帧、150帧、1080p30五秒、单版字幕与指定原唱。视频是否完成看 current_state 和交付目录 delivery.json；编码成功后才登记完成。

沿用猪猪既定快速样片约定：不做输出后的解码、审片或音轨复验，不称新视频技术验收通过。保留上一版工程／视频供回退。本次不是新 MME 执行、Curvature rim 方案或全曲交付。
