"""Archive completed surface refinement media and the exact reviewed controls."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-root", type=Path, required=True)
    args = p.parse_args()
    root = args.output_root
    repo = Path(__file__).resolve().parents[1]
    video = root / "motion/surface-refined.mp4"
    qa = json.loads(
        (root / "motion/video-qa-v2/video-verification.json").read_text(
            encoding="utf-8"
        )
    )
    audio = json.loads((root / "motion/audio-qa-v2.json").read_text(encoding="utf-8"))
    comp = json.loads(
        (root / "motion/composite-v2/caption-verification.json").read_text(
            encoding="utf-8"
        )
    )
    prep = json.loads(
        (root / "prepared-motion/preparation-report.json").read_text(encoding="utf-8")
    )
    assert (
        qa["passed"]
        and audio["passed"]
        and qa["sha256"] == hashlib.sha256(video.read_bytes()).hexdigest()
    )
    assert (
        qa["decoded_frames"] == comp["frames"] == 480
        and prep["camera"]["head_and_hair_projection_checks"] == 480
    )
    guides = root / "guides"
    guides.mkdir(exist_ok=False)
    for name in ["SURFACE_REFINEMENT.md", "HALF_LAMBERT_STUDY.md", "STYLE_PRESETS.md"]:
        shutil.copy2(repo / "docs" / name, guides / name)
    shutil.copytree(repo / "presets/quality", root / "quality-presets")
    shutil.copy2(
        repo / "presets/typography/portrait-surface-study.json",
        root / "typography-profile.json",
    )
    credit = Path(r"D:\codex\output\MMD-Quality-Lab-v1\CREDITS.md").read_text(
        encoding="utf-8"
    )
    credit += "\n本轮新增学习：Juan Salice 原作者 NPR 拆解、Project Studio Q 制作文章。新制图集控制图、方向性发束高光、材质分配与描边调整由本项目完成；未使用上述作者的角色、原始贴图或工程。\n"
    (root / "CREDITS.md").write_text(credit, encoding="utf-8")
    manifest = {
        "scope": "Eight-second portrait surface refinement; not a replacement 20-second final",
        "video": str(video),
        "sha256": qa["sha256"],
        "dimensions": [qa["width"], qa["height"]],
        "fps": qa["fps"],
        "frames": qa["decoded_frames"],
        "seconds": qa["seconds"],
        "audio_rms": audio["rms"],
        "audio_manually_synced": False,
        "surface_preset": prep["surface_settings"],
        "outline_preset": json.loads(
            (repo / "presets/quality/outlines-v1.json").read_text(encoding="utf-8")
        ),
        "head_hair_projection_checks": 480,
        "geometry_pose_hashes_unchanged": prep["geometry_and_pose_hashes_unchanged"],
        "typography_protected_linear_delta_before_encoding": comp[
            "maximum_protected_linear_delta"
        ],
        "existing_style_presets_overwritten": False,
        "tests_passed": 37,
    }
    with (root / "delivery-manifest.json").open("x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    readme = f"""# 阿克西妮娅材质与轮廓精修

猪猪，本轮精修了发束高光、金边/布料的不同反光响应、舞台明暗和可见深色轮廓。原两类风格六套预设保留，新控制图按本模型制作，没有把它们当作原游戏 PBR/ILM 贴图。

- [八秒带声精修片段]({video.as_posix()})：720×1280、60 fps、480 帧、64 samples。
- [关闭 / 原细线 / 增强近黑描边]({(root / "outline-comparison.jpg").as_posix()})，同姿态原渲染对照。
- [逐项材质与灯光对照]({(root / "surface-comparison.jpg").as_posix()})；控制图审看见 control-maps/atlas-mask-review.jpg。
- [精修与复用指导]({(guides / "SURFACE_REFINEMENT.md").as_posix()})，含用户补充的十位创作者学习入口。

工程在 motion/scene/typography-source.blend，准备过程及构图报告在 prepared-motion；新控制图已打包进材质工程。图形字幕仍由 Python 第二阶段合成，直接渲染 Blend 不会自动执行字幕后期。源帧 421–900，逐帧 PNG 缓存在 D:\\codex\\temp\\mmd-surface-motion-v1。

衣发动作沿用原有烘焙；材质静帧与扩展镜头均检查顶点/姿态哈希保持，480 帧头部和保守头发范围检查通过。最终视频完整解码与音轨解码通过，37 项测试通过。人工卡点仍留给用户。最终字幕合成与验收以 motion/composite-v2、video-qa-v2、audio-qa-v2.json 为准；初次四秒范围误用的文件仅保留作诊断。

stills-v001 为逐项隔离实验，stills-v002 为材质校准，outline-study 为描边对照及采用的近黑线版本，质量参数副本在 quality-presets。金属只在衣物/配饰遮罩区域混合，不给脸或虹膜套金属。

本轮是八秒竖屏精修片段，尚未重制二十秒全高清版或验证全部横屏组合；整体材质仍可继续打磨。代码与完整指导保存在 D:\\codex\\workspace\\blender-mmd-codex，未公开发布。
"""
    (root / "README.md").write_text(readme, encoding="utf-8")
    print("SURFACE_DELIVERY_OK", qa["sha256"])


if __name__ == "__main__":
    main()
