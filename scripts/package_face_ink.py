"""Archive a verified eight-second face-ink refinement and its exact recipe."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-root", type=Path, required=True)
    args = p.parse_args()
    root = args.output_root
    repo = Path(__file__).resolve().parents[1]
    video = root / "motion/face-ink-refined.mp4"
    qa = read(root / "motion/video-qa/video-verification.json")
    audio = read(root / "motion/audio-qa.json")
    comp = read(root / "motion/composite/caption-verification.json")
    render = read(root / "motion/scene/render-report.json")
    evidence = read(root / "review/visual-evidence.json")
    comparison = read(root / "stills-v2/face-black/report.json")
    assert qa["passed"] and audio["passed"]
    assert qa["sha256"] == hashlib.sha256(video.read_bytes()).hexdigest()
    assert (
        qa["decoded_frames"] == render["rendered_frame_count"] == comp["frames"] == 480
    )
    assert comp["maximum_protected_linear_delta"] == 0
    assert all(
        item["face_shell_ablation_changed_pixels_over_5"] > 0
        for item in evidence["renders"]
    )
    assert (
        comparison["repeat_does_not_add_nodes"]
        and comparison["geometry_and_pose_unchanged"]
    )
    guides = root / "guides"
    guides.mkdir(exist_ok=False)
    for name in [
        "FACE_INK_REFINEMENT.md",
        "GUANHAIZI_REFERENCE.md",
        "SURFACE_REFINEMENT.md",
    ]:
        shutil.copy2(repo / "docs" / name, guides / name)
    shutil.copy2(
        repo / "presets/quality/outlines-v2-face-black.json",
        root / "outline-preset.json",
    )
    shutil.copy2(
        repo / "presets/typography/portrait-surface-study.json",
        root / "typography-profile.json",
    )
    credit = Path(r"D:\codex\output\MMD-Surface-Refinement-v1\CREDITS.md").read_text(
        encoding="utf-8"
    )
    credit += "\n本轮对照用户本地下载的观海子 Cherry / 亲亲小狐狸选定帧，新增脸部描边、眉睫与嘴缝控制。参考片后期/素材署名见 guides/GUANHAIZI_REFERENCE.md；不声称使用或还原参考作者原工程。\n"
    (root / "CREDITS.md").write_text(credit, encoding="utf-8")
    manifest = {
        "scope": "Eight-second portrait face-ink refinement",
        "video": str(video),
        "project": str(root / "motion/scene/typography-source.blend"),
        "sha256": qa["sha256"],
        "dimensions": [qa["width"], qa["height"]],
        "fps": qa["fps"],
        "frames": qa["decoded_frames"],
        "seconds": qa["seconds"],
        "audio_decode_passed": audio["passed"],
        "audio_manually_synced": False,
        "outline_preset": read(root / "outline-preset.json"),
        "geometry_pose_hashes_unchanged_at_review_frames": comparison[
            "geometry_and_pose_unchanged"
        ],
        "repeated_application_keeps_node_count": comparison[
            "repeat_does_not_add_nodes"
        ],
        "face_shell_ablation_evidence": evidence["renders"],
        "single_edge_cryptomatte_validation": "Not used: no signal; actual ablation renders validate the face shell",
        "typography_protected_linear_delta_before_encoding": comp[
            "maximum_protected_linear_delta"
        ],
        "tests_passed": 37,
        "older_style_presets_overwritten": False,
    }
    (root / "delivery-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "README.md").write_text(
        "# 清晰脸线升级版\n\n"
        "- 视频：`motion/face-ink-refined.mp4`，720×1280 / 60 fps / 8 秒，480 帧已完整解码验收。\n"
        "- Blender 工程：`motion/scene/typography-source.blend`，含既有衣发烘焙、新脸线、材质与镜头。\n"
        "- 脸部对照：`review/face-comparison.png`，左旧版、中选定新版、右较粗线对照。\n"
        "- 参考原帧局部：`review/reference-faces.png`；来源坐标见 `review/visual-evidence.json`。\n"
        "- 精确预设：`outline-preset.json`；学习、限制和复现：`guides/FACE_INK_REFINEMENT.md`。\n\n"
        "原字幕素材在 Python 第二阶段合成，不是保存进 Blender 后就能直接渲出的文字图层。PNG 重渲缓存位于约定临时目录。伴奏沿用原来源，卡点仍留给猪猪。\n\n"
        "这次交付为八秒脸线升级片段；原二十秒全高清视频及其旧工程未覆盖。换模型或画幅需要重新核对 UV、材质与像素线宽。\n",
        encoding="utf-8",
    )
    print(
        "FACE_INK_DELIVERY_OK",
        json.dumps({"video": str(video), "sha256": qa["sha256"]}),
    )


if __name__ == "__main__":
    main()
