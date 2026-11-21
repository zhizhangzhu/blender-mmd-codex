"""Archive a completed six-package style study after actual media verification."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from style_presets import ROOT, load_package


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-root", type=Path, required=True)
    args = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    clips = []
    for family in catalog["families"].values():
        for packages in family["variants"].values():
            for package_path in packages:
                recipe = load_package(ROOT / package_path)
                target = args.output_root / "clips" / recipe["id"]
                video = target / (recipe["id"] + ".mp4")
                qa_paths = sorted(target.glob("video-qa*/video-verification.json"))
                audio_paths = sorted(target.glob("audio-qa*.json"))
                if not qa_paths or not audio_paths:
                    raise ValueError("Missing completed media checks: " + recipe["id"])
                qa = json.loads(qa_paths[-1].read_text(encoding="utf-8"))
                audio = json.loads(audio_paths[-1].read_text(encoding="utf-8"))
                composite_dir = target / "composite-outline-v2"
                if not composite_dir.exists():
                    composite_dir = target / "composite"
                comp = json.loads(
                    (composite_dir / "caption-verification.json").read_text(
                        encoding="utf-8"
                    )
                )
                render = json.loads(
                    (target / "scene" / "render-report.json").read_text(
                        encoding="utf-8"
                    )
                )
                digest = hashlib.sha256(video.read_bytes()).hexdigest()
                assert qa["passed"] and audio["passed"] and digest == qa["sha256"]
                assert qa["decoded_frames"] == comp["frames"] == 240
                assert render["style_package"] == recipe == comp["style_package"]
                clips.append(
                    {
                        "id": recipe["id"],
                        "family": recipe["family"],
                        "aspect": recipe["aspect"],
                        "video": str(video),
                        "sha256": digest,
                        "dimensions": [qa["width"], qa["height"]],
                        "fps": qa["fps"],
                        "frames": qa["decoded_frames"],
                        "seconds": qa["seconds"],
                        "video_qa": str(qa_paths[-1]),
                        "audio_qa": str(audio_paths[-1]),
                        "audio_rms": audio["rms"],
                        "max_protected_typography_delta_before_encoding": comp[
                            "maximum_protected_linear_delta"
                        ],
                        "resolved_style": str(target / "scene" / "resolved-style.json"),
                        "composite_dir": str(composite_dir),
                    }
                )
    # Preserve the exact component tree, including external typography references.
    shutil.copytree(repo / "presets", args.output_root / "presets")
    shutil.copytree(repo / "docs", args.output_root / "guides")
    previous = Path(r"D:\codex\output\MMD-Advanced-Subtitle-Study-v1")
    if (previous / "CREDITS.md").is_file():
        credit = (previous / "CREDITS.md").read_text(encoding="utf-8")
        credit += "\n本轮增加两类参考方向、六个风格/画幅组合。程序菱格、外轮廓、光点和边框为本项目生成，未使用观海子参考的原始 PV Kit。作者名只表示参考方向，不代表原作者参数或同等质量。\n"
        (args.output_root / "CREDITS.md").write_text(credit, encoding="utf-8")
    lines = [
        "# MMD 多风格与横竖屏预设 v1",
        "",
        "猪猪，本轮交付两类参考方向：Gosari542 柔光舞台；观海子粉色图形 / 紫红舞台变体。每个变体有独立横竖屏 package，渲染、后期、镜头和字幕布局分开保存，后续可另建个人风格。",
        "",
        "同姿态对照见 review/style-matrix.jpg，只有 Blender 画面的对照见 review/render-only-matrix.jpg。预设选择、复现和扩展方法见 guides/STYLE_PRESETS.md。",
        "",
        "| 组合 | 四秒带声样片 |",
        "| --- | --- |",
    ]
    for clip in clips:
        link = Path(clip["video"]).as_posix()
        lines.append(f"| {clip['id']} | [播放样片]({link}) |")
    guide_link = (args.output_root / "guides" / "STYLE_PRESETS.md").as_posix()
    lines += ["", f"[预设选择、复现与个人风格扩展指导]({guide_link})"]
    lines += [
        "",
        "六套样片均实际完整解码 240 帧、60 fps、4 秒，含非静音伴奏。竖屏 540×960，横屏 960×540；当前验收为预览分辨率，未重制二十秒全高清新版或完成伴奏卡点，也未宣称达到参考作者同等材质质量。",
        "",
        "各 clips 子目录：scene/typography-source.blend、scene/resolved-style.json、composite/、video-qa*、audio-qa*.json。Blend 保存渲染、相机、人物和遮罩输出；Python 执行最终图形背景、贴纸外轮廓、边框与字幕合成。",
        "",
        "逐帧 PNG 缓存位于 D:\\codex\\temp\\mmd-style-presets-v1-animation，工程中的输出路径仍指向本机缓存。换模型需重新核对材质分类和遮罩；重渲染使用新目录，保留源素材与旧版本。",
        "",
        "代码与指导：D:\\codex\\workspace\\blender-mmd-codex。参考作品署名见 CREDITS.md，实际媒体状态及校验值见 delivery-manifest.json。",
    ]
    (args.output_root / "README.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    manifest = {
        "scope": "Two reference families, three variants, both aspects; 4-second technical studies",
        "not_original_author_settings": True,
        "audio_sync_manually_completed": False,
        "clips": clips,
    }
    with (args.output_root / "delivery-manifest.json").open(
        "x", encoding="utf-8"
    ) as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    print("STYLE_SUITE_ARCHIVED", len(clips), "clips", args.output_root)


if __name__ == "__main__":
    main()
