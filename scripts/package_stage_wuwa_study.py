"""Package original notes and rendered comparisons; preserve the accepted movie."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.output_dir
    review = root / "review"
    review.mkdir(exist_ok=False)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    cases = {
        "night": [
            ("night-v1/baseline-4200.png", "已满意版本：明亮礼堂基线"),
            ("night-v1/night-atmosphere-4200.png", "独立实验：冷色夜景＋局部暖光"),
        ],
        "hair": [
            ("wuwa-hair-v1/native-inputs.png", "原连接"),
            ("wuwa-hair-v1/control-neutral-HM.png", "HM 组输入置零"),
            ("wuwa-hair-v1/control-neutral-HN.png", "HN 组输入中性值"),
        ],
    }
    report = {}
    for key, entries in cases.items():
        width = 640 if key == "night" else 360
        canvas = Image.new("RGB", (width * len(entries), 420), "#111722")
        draw = ImageDraw.Draw(canvas)
        arrays = []
        for index, (path, label) in enumerate(entries):
            with Image.open(root / path) as source:
                frame = source.convert("RGB")
                arrays.append(np.asarray(frame, dtype=np.float32))
                frame = frame.resize((width, 360), Image.Resampling.LANCZOS)
                canvas.paste(frame, (width * index, 60))
            draw.text((width * index + 12, 16), label, font=font, fill="white")
        canvas.save(review / f"{key}-comparison.jpg", quality=95)
        report[key] = {
            "mean_absolute_rgb_difference_0_to_255": [
                float(np.abs(a - arrays[0]).mean()) for a in arrays[1:]
            ],
            "interpretation": "Difference only, not a quality score",
        }
    repo = Path(__file__).resolve().parents[1]
    for name in [
        "STAGE_ART_NIGHT_STUDY.md",
        "WUWA_TOON_STUDY.md",
        "TUTORIAL_TRANSCRIPTION.md",
    ]:
        (root / name).write_bytes((repo / "docs" / name).read_bytes())
    accepted = Path(
        r"D:\codex\output\MMD-Ray-Hall-Genshin-Revision-v1"
        r"\sample-5s-v1\Aether_Duet_5s_REVIEW.mp4"
    )
    digest = hashlib.sha256(accepted.read_bytes()).hexdigest()
    assert digest == "6058192cbcdd8e5a12aba480303e1ca26cba939639e0ddd9f8fbbfaa3984a42a"
    report["accepted_video_sha256_unchanged"] = digest
    report["scope"] = "Research and still experiments; not a new motion render"
    (review / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "README.md").write_text(
        "# 舞台美术与鸣潮三渲二学习\n\n"
        "猪猪，本轮保留已满意的五秒基线，完成教程研究与独立静帧实验。"
        "这不是新的五秒影片或全曲成品。\n\n"
        "- review/night-comparison.jpg：同机位基线／夜景对照。\n"
        "- review/hair-comparison.jpg：原连接／两个组输入控制对照。\n"
        "- night-v1/Moonlit_Vows_Study.blend：独立礼堂夜景工程。\n"
        "- wuwa-hair-v1/WuWa_Hair_Input_Study.blend：独立发丝测试工程。\n"
        "- 三份学习文档记录来源、复现命令、观察与局限。\n\n"
        "夜景色池不具备真实遮挡；薄雾不代表已完成月光束。"
        "鸣潮发丝只使用预设匹配数据，未移植到双人角色。"
        "转头、高光运动、全曲灯光和动态遮挡尚未验收。\n\n"
        "原场景／角色／动作／相机的署名与条款继承基线目录的 CREDITS.md。"
        "额外着色器：三一七片的谎言。教程作者 Biscuit-773、Weytant；"
        "实验不是其原工程。发丝示例模型的独立署名尚未核实，"
        "仅作用户提供素材的本地技术研究，不作为对外发布成片。\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
