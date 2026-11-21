"""Archive and catalog the verified second fox lighting study.

This reports technical checks and reviewed samples, not user art approval.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import cv2
import numpy as np
from package_fox_cinema import frame, panel, read, write
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]


def controls(root):
    production = root / "production-v5"
    review = root / "review"
    review.mkdir(exist_ok=True)
    definitions = [
        (
            "shadow",
            "02-stage-wide.png",
            "control-no-projector-shadow.png",
            "主投影关",
            "主投影开",
        ),
        (
            "air",
            "02-stage-wide.png",
            "control-no-rear-air.png",
            "后方空气关",
            "后方空气开",
        ),
        (
            "rim",
            "03-stage-close.png",
            "control-no-rim-glow.png",
            "亮边溢光关",
            "亮边溢光开",
        ),
    ]
    measures = []
    for key, actual, control, before, after in definitions:
        a = np.asarray(Image.open(production / actual).convert("RGB"), np.float32)
        b = np.asarray(Image.open(production / control).convert("RGB"), np.float32)
        difference = np.abs(a - b)
        measure = {
            "effect": key,
            "mean_absolute_rgb_difference_255": float(difference.mean()),
            "maximum_rgb_difference_255": float(difference.max()),
            "fraction_pixels_over_1": float((difference.max(2) > 1).mean()),
        }
        assert measure["mean_absolute_rgb_difference_255"] > (
            0.003 if key == "rim" else 0.05
        ), measure
        measures.append(measure)
        panel(
            [(production / control, before), (production / actual, after)],
            review / f"{key}-control.jpg",
        )
    write(
        review / "effect-controls.json",
        {
            "measurements": measures,
            "meaning": "Effect presence in native same-frame counterfactuals; not a quality or similarity score",
            "passed": True,
        },
    )
    return measures


def review_transition(movie, destination):
    cap = cv2.VideoCapture(str(movie))
    contact = Image.new("RGB", (1440, 3 * 232), "#171a26")
    draw = ImageDraw.Draw(contact)
    frames = list(
        range(120, 132)
    )  # global 4260..4271, actual consecutive 60 fps frames
    for n, index in enumerate(frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, pixels = cap.read()
        assert ok
        picture = Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB)).resize(
            (360, 202)
        )
        x, y = n % 4 * 360, n // 4 * 232
        contact.paste(picture, (x, y))
        draw.text(
            (x + 6, y + 207), f"global {4140 + index} / {index / 60:.3f}s", fill="white"
        )
    cap.release()
    contact.save(destination, quality=95)
    return [4140 + index for index in frames]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--controls-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    measurements = controls(root)
    if args.controls_only:
        print("STAGEART_EFFECT_CONTROLS_PASSED", json.dumps(measurements), flush=True)
        return
    production, sample = root / "production-v5", root / "sample-5s-v2"
    study = read(production / "stageart-study.json")
    master = read(root / "master-verification.json")
    assert master["passed"] and master["target"] == study["project"]
    movie = sample / "Aether_Duet_5s_REVIEW.mp4"
    video = read(sample / "video-qa/video-verification.json")
    audio = read(sample / "audio-verification.json")
    seam = read(sample / "seam-qa/seam-verification.json")
    assert all(r["passed"] for r in (video, audio, seam))
    assert video["decoded_frames"] == 300
    previous = Path(
        "D:/codex/output/MMD-Fox-Cinema-v1/sample-5s-v1/Aether_Duet_5s_REVIEW.mp4"
    )
    assert (
        hashlib.sha256(previous.read_bytes()).hexdigest()
        == "92efb60488a0c05b3cfd12be59cc28223faf0a05fc53f370c1a1b166cf50b984"
    )
    preserved = Path(
        "D:/codex/output/MMD-Quality-Integration-v1/linear-sequence-v2/duet_4200.exr"
    )
    assert (
        hashlib.sha256(preserved.read_bytes()).hexdigest()
        == "bb3a0e66e2b29bf912181e26bd21a645ded0796ca5111c88657985190b0c4529"
    )
    review = root / "review"
    before = frame(previous, 110, review / "before-4250.png")
    after = frame(movie, 110, review / "after-4250.png")
    panel(
        [(before, "前版夜誓 · 第 4250 帧"), (after, "本次舞台 · 同相机同动作")],
        review / "before-after.jpg",
    )
    transition = review_transition(movie, review / "transition-consecutive.jpg")
    write(
        review / "manual-review.json",
        {
            "reviewer": "Codex",
            "user_art_approval": False,
            "inspected": [
                "12 final video representative frames",
                "seam frames 148..152",
                "12 consecutive global frames 4260..4271",
                "native same-frame shadow/air/rim controls",
                "96 sampled reference frames over four six-second spans and 16 full-size reference images",
            ],
            "observations": [
                "Diagonal performer shadows are visible in the wide shot; near-ground material changes do not blacken the altar",
                "Faces and eyes remain readable in reviewed samples after excluding all 13 named face/feature materials",
                "Rear air and rim halation remain subtle; the reference's colored overexposure transition and solo shot design have not been matched",
            ],
            "scope": "Manual sample review plus technical decode checks; not user approval or full-song validation",
        },
    )
    recipe = {
        "id": "hesperides-stageart-v2",
        "status": "verified-five-second-study",
        "user_art_approval": False,
        "engine": "Blender 5.2.2 EEVEE",
        "input": study["source"],
        "project": study["project"],
        "settings": "presets/stages/hesperides-stageart-v2.json",
        "video": str(movie),
        "frames": [4140, 4439],
        "fps": 60,
        "resolution": [1920, 1080],
        "physical_ground_regions": study["physical_ground_materials"],
        "pose_camera_lens_unchanged_samples": master["motion_samples"],
        "limits": [
            "Only five seconds, not a finished full song or author original MME",
            "Art-directed light/shadow linking; wall NPR pools and added rims are not fully physical",
            "Air and rim halation deliberately modest; no matching large colored overexposure transition",
            "Auxiliary RGBA scenes and full linear sequence not validated for this variant",
        ],
    }
    write(REPO / "presets/recipes/hesperides-stageart-v2.json", recipe)
    catalog_file = REPO / "catalog/library.json"
    catalog = read(catalog_file)
    entry = {
        "id": recipe["id"],
        "title": "入光 · 舞台光影再研究",
        "subtitle": "从光区、脚下投影到发丝溢光，让人物与礼堂建立更明确的关系。",
        "collection": "STAGE ART / FOX II",
        "category": "stage",
        "family": "guanhaizi",
        "aspect": "landscape",
        "status": "motion",
        "image": str(after),
        "video": str(movie),
        "duration": 5,
        "fps": 60,
        "docs": ["FOX_STAGE_ART_DEEP_STUDY.md", "FOX_LIGHTING_AND_CINEMA.md"],
        "configs": [
            "presets/stages/hesperides-stageart-v2.json",
            "presets/recipes/hesperides-stageart-v2.json",
        ],
        "project": study["project"],
        "look": [
            "可见地面与斜向投影",
            "局部冷暖与玫瑰侧光",
            "亮边专属 AOV 溢光",
            "随景别收放光圈",
        ],
        "evidence": [
            "300 原生帧／1080p60／指定原声与接缝验收通过",
            "投影、后方空气、亮边溢光原生同帧开关对照",
            "独立重开十时点骨骼／相机／焦距精确相同，13 块脸部与五官材质排除",
        ],
        "limits": [
            "猪猪反馈后继续研究，尚未获美术认可",
            "局部空气与辉光有限，未还原参考的强光转场和特写调度",
            "仅本段五秒，辅助分层及竖屏未验收",
        ],
        "compatibility": "固定双人与现成礼堂；Blender 5.2.2 EEVEE，物理地面区域按高度／法线筛选。",
        "command": f"python scripts/render_duet_sample.py --blend '{study['project']}' --output-dir 'D:\\codex\\output\\Stage-Art-New-Sample' --logs 'D:\\codex\\temp\\Stage-Art-New-Sample' --start 4140 --frames 300 --workers 2",
    }
    catalog["entries"] = [entry] + [
        r for r in catalog["entries"] if r["id"] != entry["id"]
    ]
    pairs = [
        {
            "id": "stageart-before-after",
            "title": "前版夜誓 / 舞台光影再研究",
            "subtitle": "两支实际视频同一 4250 帧；原动作、相机和焦距相同。",
            "before_label": "前版夜誓",
            "after_label": "舞台再研究",
            "before": str(before),
            "after": str(after),
            "doc": "FOX_STAGE_ART_DEEP_STUDY.md",
        }
    ]
    for key, image, control, label in [
        (
            "shadow",
            "02-stage-wide.png",
            "control-no-projector-shadow.png",
            "人物主投影",
        ),
        ("air", "02-stage-wide.png", "control-no-rear-air.png", "后方局部空气"),
        ("rim", "03-stage-close.png", "control-no-rim-glow.png", "亮边专属溢光"),
    ]:
        pairs.append(
            {
                "id": "stageart-" + key,
                "title": label + " / 原生开关",
                "subtitle": "同帧只切换此项。控制参数存在与可见影响分开验收。",
                "before_label": label + "关",
                "after_label": label + "开",
                "before": str(production / control),
                "after": str(production / image),
                "doc": "FOX_STAGE_ART_DEEP_STUDY.md",
            }
        )
    catalog["comparisons"] = pairs + [
        p for p in catalog["comparisons"] if p["id"] not in {v["id"] for v in pairs}
    ]
    group = next(g for g in catalog["knowledge_groups"] if g["id"] == "lighting")
    group["docs"] = ["FOX_STAGE_ART_DEEP_STUDY.md"] + [
        d for d in group["docs"] if d != "FOX_STAGE_ART_DEEP_STUDY.md"
    ]
    write(catalog_file, catalog)
    shutil.copyfile(
        REPO / "docs/FOX_STAGE_ART_DEEP_STUDY.md", root / "FOX_STAGE_ART_DEEP_STUDY.md"
    )
    source = Path("D:/codex/output/MMD-Fox-Cinema-v1")
    shutil.copyfile(source / "CREDITS.md", root / "CREDITS.md")
    for original in (source / "licenses").glob("*"):
        if original.is_file():
            (root / "licenses").mkdir(exist_ok=True)
            shutil.copyfile(original, root / "licenses" / original.name)
    (root / "README.md").write_text(
        "# 入光 · 舞台光影再研究\n\n"
        + f"五秒视频：`{movie}`\n\n工程：`{study['project']}`\n\n"
        + "继续研究观海子《亲亲小狐狸》的光区、投影、轮廓与镜头节奏。当前为独立五秒 1080p60 原声样片；全曲未在本轮渲染，等待猪猪美术评价。\n\n`review` 含前后、投影／空气／亮边开关和连续转场采样。以 production-v5／sample-5s-v2 为准，其他版本为中间试验。学习记录见 FOX_STAGE_ART_DEEP_STUDY.md。\n",
        encoding="utf-8",
    )
    write(
        root / "delivery.json",
        {
            "movie": str(movie),
            "movie_sha256": video["sha256"],
            "project": study["project"],
            "video_audio_seam_verified": True,
            "frames": 300,
            "seconds": 5,
            "source_movie_and_exr_preserved": True,
            "transition_review_global_frames": transition,
            "effect_controls": measurements,
            "full_song_complete": False,
            "user_art_approval": False,
        },
    )
    print("FOX_STAGEART_PACKAGED", str(movie), flush=True)


if __name__ == "__main__":
    main()
