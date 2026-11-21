"""Publish local delivery notes only after the full movie passes verification."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-root", type=Path, required=True)
    parser.add_argument("--video-dir", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--integration", type=Path, required=True)
    args = parser.parse_args()
    root = args.production_root
    video_dir = args.video_dir
    movie = video_dir / "Franken_Duet_FULL_FINAL.mp4"
    project = args.project
    video = json.loads(
        (video_dir / "video-qa/video-verification.json").read_text(encoding="utf-8")
    )
    audio = json.loads(
        (video_dir / "audio-verification.json").read_text(encoding="utf-8")
    )
    integration = json.loads(args.integration.read_text(encoding="utf-8"))
    assert movie.is_file() and project.is_file()
    assert Path(video["video"]).resolve() == movie.resolve()
    assert Path(audio["video"]).resolve() == movie.resolve()
    assert video["passed"] and audio["passed"] and integration["passed"]
    assert (
        video["decoded_frames"] == 11899
        and video["width"] == 1920
        and video["height"] == 1080
    )
    summary = {
        "movie": str(movie),
        "project": str(project),
        "status": "rendered; full video and audio decode verified",
        "seconds": video["seconds"],
        "fps": video["fps"],
        "frames": video["decoded_frames"],
        "video_sha256": video["sha256"],
        "audio_rms": audio["rms"],
        "audio_peak": audio["peak"],
        "native_physics": "Both performers baked; runtime simulation removed",
        "characters": "Aksiniya Full HimeTanaka; Aether Full HinaSuzuki",
        "look": "Guanhaizi-inspired characters; user-selected brighter Hesperides hall, supplied Ray preview reference",
        "camera": "Authored Tottoko VMD, motion/lens preserved; full artistic correction deferred by user; shared-head DOF added",
        "audio": "Selected original vocal FLAC used as source; MP4 audio encoded AAC; fine beat adjustment remains user-adjustable",
    }
    (root / "delivery.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    movie_link = movie.relative_to(root).as_posix()
    project_link = project.relative_to(root).as_posix()
    sheet_link = (
        (video_dir / "video-qa/video-contact-sheet.jpg").relative_to(root).as_posix()
    )
    notes = f"""# 双人全曲 MMD

成片已完成渲染，并通过完整视频／音频解码检查。规格：1920×1080，60 fps，{video["seconds"]:.3f} 秒，{video["decoded_frames"]} 帧。

- [播放完整成品]({movie_link})
- [打开 Blender 工程]({project_link})
- [全曲代表帧]({sheet_link})
- [素材署名](CREDITS.md)
- [制作与验收记录](delivery.json)

阿克西妮娅使用 Full HimeTanaka，空使用 Full HinaSuzuki；两人原生衣发物理已视觉烘焙。人物按观海子参考方向做卡渲、清晰深线和分区材质，保留各自发色。礼堂使用指定的赫斯珀利德斯之馆，按用户要求提亮，参考随包 Ray 渲预览，采用 Blender 原生材质及局部 MatCap 适配。

保留とっとこ原相机的轨迹和焦段，按约定未做全曲运镜校正；增加共享头部焦点景深。BGM 使用用户指定的原声 FLAC，MP4 内音轨为 AAC；精细卡点仍可自行调整。参考作者原始 Shader 未取得，本项目不声称恢复其原始节点。

工程已打包 {integration["file_image_count"]} 张文件贴图，并包含原声条带；渲染使用便携的烘焙动作。源素材未覆盖。第三方模型与相机的公开再配布限制见署名文件，工程用于本地继续制作。
"""
    (root / "README.md").write_text(notes, encoding="utf-8")
    credits = root / "CREDITS.md"
    credits.write_text(
        credits.read_text(encoding="utf-8").replace(
            "完整视频尚在渲染；本文件是制作署名，不是公开发布记录。",
            "完整视频已渲染并通过解码验收；本文件是制作署名，不是公开发布记录。",
        ),
        encoding="utf-8",
    )
    recipe_path = (
        Path(__file__).resolve().parents[1]
        / "presets/projects/franken-duet-full-v1.json"
    )
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    recipe["status"] = (
        "full 1080p60 duet movie rendered; video/audio complete decode passed; full camera artistic correction deferred by user"
    )
    recipe["final_delivery"] = summary
    recipe_path.write_text(
        json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
